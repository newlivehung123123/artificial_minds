"""
The scoring harness.

    python -m scoring.run models                     confirm every model on OpenRouter
    python -m scoring.run records                    render all 122 records to disk
    python -m scoring.run run --stub --countries pilot
    python -m scoring.run run --countries pilot --out runs/stage_b.jsonl
    python -m scoring.run batch-submit --countries pilot --out runs/stage_b.jsonl
    python -m scoring.run batch-collect --out runs/stage_b.jsonl
    python -m scoring.run report runs/stage_b.jsonl

One call writes one line to a JSONL ledger. A run is resumable, because the ledger
is keyed by the cell a line answers, and a cell already answered is skipped unless
--retry-failed is passed. Nothing is overwritten and nothing is deleted, so a
ledger is an append-only record of every attempt, which is what the deposit needs.

A model on the sync route is called by `run`, one call at a time. A model on the
batch route is sent by `batch-submit` and written to the ledger by
`batch-collect`, because a batch is answered within 24 hours and not at once.
Every batch submitted is recorded in a manifest beside the ledger, named
<ledger>.batches.jsonl, which is append-only like the ledger, so a submitted
batch is never lost before collection and a cell inside an open batch is never
submitted twice. Both routes write the same row schema into the same ledger.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from . import config as C
from . import instruments as I
from . import parse as P
from . import providers as V
from . import record as R


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def cell_id(instrument, condition, model_key, iso3, replicate, temperature, template) -> str:
    return "|".join([instrument, condition, model_key, iso3, str(replicate),
                     f"{temperature:g}", template])


def read_ledger(path: Path) -> dict[str, dict]:
    done: dict[str, dict] = {}
    if not path.exists():
        return done
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "cell" in row:
                done[row["cell"]] = row
    return done


def manifest_path(ledger: Path) -> Path:
    return ledger.with_suffix(".batches.jsonl")


def read_manifest(path: Path) -> dict[str, dict]:
    """Every batch in a manifest, keyed by batch ID, with "closed" set once closed."""
    batches: dict[str, dict] = {}
    if not path.exists():
        return batches
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if event["event"] == "submitted":
                batches[event["batch_id"]] = event | {"closed": None}
            elif event["event"] == "closed" and event["batch_id"] in batches:
                batches[event["batch_id"]]["closed"] = event
    return batches


# --- subcommands -----------------------------------------------------------


def _taken_price(pricing: dict) -> tuple[float, float] | None:
    """The price the rule in scoring/config.py takes from one endpoint listing.

    The rule takes the highest price that could apply to a prompt of this study,
    before any discount the listing marks. A price tier keyed on prompt length
    counts only where the tier starts below C.PROMPT_TOKEN_CEILING, and a price
    for reasoning tokens counts as an output price.
    """
    keep = 1 - float(pricing.get("discount") or 0)
    if keep <= 0:
        return None
    tiers = [pricing] + [t for t in pricing.get("overrides") or []
                         if (t.get("min_prompt_tokens") or 0) < C.PROMPT_TOKEN_CEILING]

    def top(*fields):
        found = [float(t[f]) for t in tiers for f in fields if t.get(f) is not None]
        return round(max(found) * 1e6 / keep, 6) if found else None

    taken_in, taken_out = top("prompt"), top("completion", "internal_reasoning")
    if taken_in is None or taken_out is None:
        return None
    return taken_in, taken_out


def _check_route(model: C.Model, route: str) -> tuple[str, list[str]]:
    """The endpoint name and the problems for one model on one route."""
    listing = V.endpoints(model.api_id, batch=(route == "batch"))
    found = listing.get("endpoints") or []
    hits = [e for e in found if e.get("tag") == model.pin]
    if not hits:
        tags = ", ".join(e.get("tag", "?") for e in found) or "nothing"
        return "", [f"no endpoint is tagged {model.pin}, and the listing serves {tags}"]
    endpoint = hits[0]
    problems = []
    params = set(endpoint.get("supported_parameters") or [])
    if "max_tokens" not in params:
        problems.append(f"the endpoint lists no max_tokens, so the cap of "
                        f"{C.MAX_OUTPUT_TOKENS} output tokens could be dropped")
    if ("temperature" in params) != model.takes_temperature:
        problems.append(
            f"the endpoint {'lists' if 'temperature' in params else 'lists no'} "
            f"temperature, and scoring/config.py sets takes_temperature="
            f"{model.takes_temperature}")
    taken = _taken_price(endpoint.get("pricing") or {})
    held = C.price(model.key, route)
    if taken is None:
        problems.append("the listing gives no price the rule can read")
    elif (held.get("input") is None or held.get("output") is None
          or abs(held["input"] - taken[0]) > 1e-9
          or abs(held["output"] - taken[1]) > 1e-9):
        problems.append(
            f"scoring/config.py prices the {route} route at ${held.get('input')} and "
            f"${held.get('output')}, read {held.get('read_on')}, and the rule takes "
            f"${taken[0]:g} and ${taken[1]:g} from the listing today")
    return endpoint.get("name", ""), problems


def cmd_models(args) -> int:
    """Confirm every confirmatory model against the public listing of OpenRouter.

    The listing is public, so the check needs no key and spends nothing. For each
    model the check confirms that the endpoint the pin names serves the model,
    that the endpoint takes max_tokens, that the endpoint takes a temperature
    exactly where scoring/config.py says so, and that the price in
    scoring/config.py is the price the rule in scoring/config.py takes from the
    listing today. A model on the batch route is checked on the batch listing as
    well. Any problem ends the check with exit status 1 and names what to repair
    by hand in scoring/config.py.
    """
    failed = 0
    for model in (C.MODELS[k] for k in C.CONFIRMATORY):
        routes = ["sync", "batch"] if model.route == "batch" else ["sync"]
        for route in routes:
            try:
                name, problems = _check_route(model, route)
            except Exception as exc:                   # noqa: BLE001
                name, problems = "", [f"the listing could not be read, "
                                      f"{type(exc).__name__}: {exc}"]
            verdict = "CONFIRMED" if not problems else "PROBLEM"
            print(f"{model.key:16} {route:5} {model.pin:22} {verdict:9} "
                  f"{name or model.api_id}")
            for problem in problems:
                print(f"{'':16}   {problem}")
            failed += bool(problems)
    for key in C.PILOT_MODELS:
        print(f"{key:16} pilot, called through Anthropic directly. 600 real calls in "
              f"Stage A confirmed the identifier, so the identifier is not "
              f"checked here.")
    print()
    if failed:
        print(f"{failed} problem(s). Repair scoring/config.py by hand from the "
              f"listing, with the date read, and rerun.")
        return 1
    print("Every confirmatory model is served at its pin, takes the parameters the "
          "harness sends, and is priced as the listing prices the model today.")
    return 0


def cmd_records(args) -> int:
    C.RECORDS.mkdir(parents=True, exist_ok=True)
    index = R.eligible()
    written, failed = 0, []
    for iso3 in index.index:
        try:
            text = R.render(iso3)
        except Exception as exc:                       # noqa: BLE001
            failed.append((iso3, f"{type(exc).__name__}: {exc}"))
            continue
        (C.RECORDS / f"{iso3}.txt").write_text(text)
        written += 1
    print(f"{written} records written to {C.RECORDS}")
    for iso3, why in failed:
        print(f"  FAILED {iso3}: {why}")
    return 1 if failed else 0


def _countries(spec: str) -> list[str]:
    if spec == "pilot":
        import csv
        if not C.PILOT_COUNTRIES.exists():
            sys.exit(f"{C.PILOT_COUNTRIES} is absent. Run scripts/00_select_pilot.py first.")
        with C.PILOT_COUNTRIES.open() as fh:
            return [r["ISO3"] for r in csv.DictReader(fh)]
    if spec == "all":
        return list(R.eligible().index)
    return [c.strip().upper() for c in spec.split(",") if c.strip()]


def _plan(args, route: str) -> tuple[Path, dict, list[str], list[tuple]]:
    """The ledger, the rows already in the ledger, the models and the cells of a run.

    Shared by `run` and `batch-submit`, so the two routes refuse the same mistakes
    in the same words.
    """
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = read_ledger(out)

    countries = _countries(args.countries)
    models = (args.models.split(",") if args.models
              else [k for k in C.CONFIRMATORY if C.MODELS[k].route == route])
    unknown = [m for m in models if m not in C.MODELS]
    if unknown:
        sys.exit(f"no such model: {', '.join(unknown)}. Choose from "
                 f"{', '.join(C.MODELS)}.")
    # A model runs on one route, named in scoring/config.py, so the price a ledger
    # row is costed at is the price the call was actually sent at.
    elsewhere = [m for m in models if C.MODELS[m].route != route]
    if elsewhere:
        other = "batch-submit" if route == "sync" else "run"
        verb = "runs" if len(elsewhere) == 1 else "run"
        sys.exit(f"no call was made and no line was written, because "
                 f"{' and '.join(elsewhere)} {verb} on the "
                 f"{C.MODELS[elsewhere[0]].route} route. Send the cells of "
                 f"{' and '.join(elsewhere)} with `python -m scoring.run {other}`.")
    # Pre-flight, before anything is printed or written. A key missing from .env is
    # a fault in the environment and says nothing about a model, so the run stops
    # here. An earlier version caught the missing key once per call and wrote 20
    # lines reading transport_error, which put 20 rows into an append-only research
    # record to report that a key had not been pasted into a file.
    if not args.stub and not args.dry_run:
        absent = sorted({
            f"{C.PROVIDERS[C.MODELS[m].provider].env_var} for {C.MODELS[m].label}"
            for m in models
            if not os.environ.get(C.PROVIDERS[C.MODELS[m].provider].env_var)
        })
        if absent:
            sys.exit(
                "no call was made and no line was written, because these keys are "
                "absent from the environment:\n  " + "\n  ".join(absent)
                + f"\n\nPaste the key into {C.ENV_FILE} after the equals sign and "
                  "save the file, then run this command again. Add --stub to test "
                  "the harness with no key and no spending."
            )

    # A spend cap counts dollars, and a dollar figure exists only for a model whose
    # price has been filled in by hand. With no price the running total stays at
    # zero, the cap never binds, and a run that looked capped would have run to the
    # end of the grid. A cap that silently does nothing is worse than no cap at
    # all, so the run stops here and names both repairs.
    if args.spend_cap and not args.stub:
        unpriced = sorted({
            C.MODELS[m].label for m in models
            if C.price(m, route).get("input") is None
            or C.price(m, route).get("output") is None
        })
        if unpriced:
            sys.exit(
                f"no call was made and no line was written, because --spend-cap "
                f"{args.spend_cap} cannot bind. A spend cap adds up the cost of "
                f"each call, and no price is filled in for these models:\n  "
                + "\n  ".join(unpriced)
                + f"\n\nEither fill PRICES in {C.PROJECT / 'scoring' / 'config.py'} "
                  "from the published price page, with the date read, or drop "
                  "--spend-cap and limit the run with --max-calls, which counts "
                  "calls and needs no price."
            )

    # A ledger holds one role, and the check runs against the models of this
    # invocation and against the models already in the ledger. Checking the
    # invocation alone would let two runs put two roles into one file, one run at a
    # time, which is the outcome the rule exists to prevent.
    roles = {C.MODELS[m].role for m in models}
    if len(roles) > 1:
        sys.exit("a ledger holds one role. Run the pilot models and the "
                 "confirmatory models into separate ledgers, so no filtering step "
                 "stands between the raw ledger and the analysis.")
    held = {row["role"] for row in done.values() if row.get("role")}
    if held and held != roles:
        sys.exit(
            f"no call was made and no line was written. {out} already holds "
            f"{len(done)} rows of role {', '.join(sorted(held))}, and this run "
            f"would add role {', '.join(sorted(roles))}. A ledger holds one role, "
            f"so no filtering step stands between the raw ledger and the analysis. "
            f"Write this run to a separate ledger with --out."
        )
    if roles == {"pilot"}:
        print("pilot models only. No score in this ledger may enter a "
              "confirmatory analysis.")

    # Section 4.4 of PLAN.md fixes the holistic wording alone for the confirmatory
    # models, so a confirmatory run defaults to that wording and refuses another.
    # A pilot run defaults to both wordings, as Stage A ran.
    allowed = C.CONFIRMATORY_INSTRUMENTS if roles == {"confirmatory"} else C.INSTRUMENTS
    inst = args.instruments.split(",") if args.instruments else list(allowed)
    refused = [i for i in inst if i not in allowed]
    if refused:
        sys.exit(f"no call was made and no line was written, because the "
                 f"{', '.join(refused)} wording is outside the design. Section 4.4 "
                 f"of PLAN.md fixes the {', '.join(allowed)} wording for the "
                 f"confirmatory models.")
    conds = args.conditions.split(",") if args.conditions else list(C.CONDITIONS)
    temps = [float(t) for t in args.temperatures.split(",")] if args.temperatures \
        else list(C.TEMPERATURES)

    cells = []
    for instrument in inst:
        for condition in conds:
            template = I.template_hash(instrument, condition)
            for model_key in models:
                for iso3 in countries:
                    for temperature in temps:
                        for replicate in range(1, args.replicates + 1):
                            cells.append((instrument, condition, model_key, iso3,
                                          replicate, temperature, template))
    return out, done, models, cells


def _pending(cells: list[tuple], done: dict, retry_failed: bool,
             in_flight: set[str] = frozenset()) -> list[tuple]:
    pending = []
    for cell in cells:
        key = cell_id(*cell)
        if key in in_flight:
            continue
        prior = done.get(key)
        if prior is None:
            pending.append(cell)
        elif retry_failed and prior.get("outcome") in ("transport_error", "empty"):
            pending.append(cell)
    return pending


def _cell_meta(cell: tuple, prompt: dict) -> dict:
    """What a ledger row records about the cell, fixed when the prompt is built."""
    instrument, condition, model_key, iso3, replicate, temperature, template = cell
    return {
        "cell": cell_id(*cell), "model": model_key, "iso3": iso3,
        "country": prompt["country"], "instrument": instrument,
        "instrument_version": prompt["instrument_version"],
        "record_version": prompt["record_version"],
        "correction_policy": prompt["correction_policy"],
        "condition": condition, "replicate": replicate,
        "temperature": temperature, "template_sha256_16": template,
        "prompt_sha256_16": prompt["prompt_sha256_16"],
    }


def _base_row(meta: dict, route: str) -> dict:
    model = C.MODELS[meta["model"]]
    return {
        "cell": meta["cell"], "written_at": now(),
        "model": model.key, "model_label": model.label,
        "provider": model.provider, "role": model.role,
        "iso3": meta["iso3"], "country": meta["country"],
        "instrument": meta["instrument"],
        "instrument_version": meta["instrument_version"],
        # Recorded on every row and not only on a record-condition row, so one
        # ledger has one schema and a filter never has to know which condition a
        # row belongs to before reading a field.
        "record_version": meta["record_version"],
        "correction_policy": meta["correction_policy"],
        "condition": meta["condition"], "replicate": meta["replicate"],
        "temperature": meta["temperature"],
        "template_sha256_16": meta["template_sha256_16"],
        "prompt_sha256_16": meta["prompt_sha256_16"],
        "route": route, "pin": model.pin,
        # False where the endpoint takes no temperature, so the temperature of the
        # cell was never sent and the cell differs from its twin at the other
        # temperature only by chance.
        "temperature_applied": model.takes_temperature,
    }


def _answered_row(row: dict, res: dict, cost: float | None) -> dict:
    parsed = P.parse(res["text"], row["instrument"])
    return row | {
        "outcome": parsed["outcome"], "value": parsed["value"],
        "detail": parsed["detail"], "raw": res["text"],
        "coerced": parsed["coerced"], "parser": P.PARSER_VERSION,
        "model_version": res["model_version"],
        "stop_reason": res["stop_reason"],
        "input_tokens": res["input_tokens"],
        "output_tokens": res["output_tokens"],
        "reasoning_tokens": res["reasoning_tokens"],
        "cost_usd": cost, "reported_cost": res["reported_cost"],
        "serving_provider": res["serving_provider"],
        "router_attempt": res["router_attempt"],
        "generation_id": res["generation_id"],
        "seconds": res.get("seconds"), "stub": res["stub"],
    }


def cmd_run(args) -> int:
    out, done, models, cells = _plan(args, "sync")
    pending = _pending(cells, done, args.retry_failed)

    print(f"{len(cells)} cells, {len(cells) - len(pending)} already in {out.name}, "
          f"{len(pending)} to call")
    if args.max_calls and len(pending) > args.max_calls:
        print(f"--max-calls {args.max_calls} caps this run, "
              f"{len(pending) - args.max_calls} cells left for a later run")
        pending = pending[:args.max_calls]
    if args.dry_run:
        for cell in pending[:20]:
            print("  would call", cell_id(*cell))
        print(f"  ... {max(0, len(pending) - 20)} more")
        return 0

    spent = 0.0
    counts: Counter[str] = Counter()
    with out.open("a") as fh:
        for n, cell in enumerate(pending, 1):
            instrument, condition, model_key, iso3, replicate, temperature, template = cell
            prompt = I.build(instrument, condition, iso3)
            row = _base_row(_cell_meta(cell, prompt), "sync")
            try:
                res = V.call(model_key, prompt["system"], prompt["user"], temperature,
                             instrument=instrument, stub=args.stub)
            except V.MissingKey as exc:
                # Reachable only where a key is removed from the environment while a
                # run is in flight. A key is not a property of a model, so the run
                # stops here rather than recording an outcome against the model.
                sys.exit(f"\nstopped after {n - 1} calls. {exc}")
            except Exception as exc:                    # noqa: BLE001
                row |= {"outcome": "transport_error",
                        "detail": f"{type(exc).__name__}: {exc}"[:500], "stub": args.stub}
                counts["transport_error"] += 1
            else:
                cost = V.cost_usd(model_key, res["input_tokens"], res["output_tokens"],
                                  route="sync")
                row = _answered_row(row, res, cost)
                counts[row["outcome"]] += 1
                # The charge OpenRouter reports is what the account pays, so the cap
                # counts the charge where one is reported and the listed price
                # where none is.
                charge = res["reported_cost"] if res["reported_cost"] is not None else cost
                if charge:
                    spent += charge
            fh.write(json.dumps(row) + "\n")
            fh.flush()

            if n % 10 == 0 or n == len(pending):
                shown = f"${spent:.4f}" if spent else "cost not priced"
                print(f"  {n}/{len(pending)}  {dict(counts)}  {shown}")
            if args.spend_cap and spent >= args.spend_cap:
                print(f"spend cap ${args.spend_cap} reached, stopping")
                break
            if args.sleep and not args.stub:
                time.sleep(args.sleep)

    print(f"\n{sum(counts.values())} calls written to {out}")
    for outcome, n in counts.most_common():
        print(f"  {outcome:18} {n}")
    return 0


def _custom_id(cell: tuple) -> str:
    return "cell-" + hashlib.sha256(cell_id(*cell).encode()).hexdigest()[:24]


def cmd_batch_submit(args) -> int:
    """Send the cells of the batch-route models to OpenRouter as batches.

    Nothing is written to the ledger here. Each batch accepted by OpenRouter is
    written to the manifest at once, with what every ledger row will need, so
    `batch-collect` writes the rows later from the manifest and the results alone.
    """
    out, done, models, cells = _plan(args, "batch")
    manifest = manifest_path(out)
    batches = read_manifest(manifest)
    in_flight = {meta["cell"] for b in batches.values() if b["closed"] is None
                 for meta in b["cells"].values()}
    pending = _pending(cells, done, args.retry_failed, in_flight)
    print(f"{len(cells)} cells, {len(cells) - len(pending)} already in {out.name} or "
          f"in an open batch in {manifest.name}, {len(pending)} to submit")
    if not pending:
        return 0

    # Each batch holds one model, because OpenRouter applies one model and one pin
    # to a whole batch, and at most --batch-size requests, because OpenRouter holds
    # the worst-case cost of every request in flight against the balance and
    # refuses a batch the balance cannot cover.
    chunks: list[tuple[str, list[tuple]]] = []
    for model_key in models:
        mine = [c for c in pending if c[2] == model_key]
        for start in range(0, len(mine), args.batch_size):
            chunks.append((model_key, mine[start:start + args.batch_size]))

    # The worst case of a batch is every request writing the full cap of output
    # tokens. The input count is the prompt length in characters divided by three,
    # which counts more tokens than any tokenizer measured so far does, because the
    # Stage A prompts ran from 3.77 to 4.62 characters a token.
    planned = []
    worst_total = 0.0
    for model_key, chunk in chunks:
        model = C.MODELS[model_key]
        price = C.price(model_key, "batch")
        requests, metas, worst = [], {}, 0.0
        for cell in chunk:
            instrument, condition, _, iso3, _, temperature, _ = cell
            prompt = I.build(instrument, condition, iso3)
            cid = _custom_id(cell)
            requests.append({"custom_id": cid, "body": V.openrouter_body(
                model, prompt["system"], prompt["user"], temperature)})
            metas[cid] = _cell_meta(cell, prompt)
            if price.get("input") is not None and price.get("output") is not None:
                chars = len(prompt["system"]) + len(prompt["user"])
                worst += (chars / 3 * price["input"]
                          + C.MAX_OUTPUT_TOKENS * price["output"]) / 1e6
        planned.append((model_key, requests, metas, worst))
        worst_total += worst
        print(f"  {model.label:16} {len(requests):4} requests, worst case "
              f"${worst:.2f} at ${price.get('input')} and ${price.get('output')} "
              f"per million, pinned to {model.pin}")
    print(f"worst case of this submission ${worst_total:.2f}, every request writing "
          f"the full {C.MAX_OUTPUT_TOKENS} output tokens")
    if args.spend_cap and worst_total > args.spend_cap:
        sys.exit(f"nothing was submitted, because the worst case ${worst_total:.2f} "
                 f"is above --spend-cap {args.spend_cap}. Lift the cap or submit "
                 f"fewer cells with --countries or --models.")
    if args.dry_run:
        return 0

    with manifest.open("a") as fh:
        for n, (model_key, requests, metas, worst) in enumerate(planned, 1):
            if args.stub:
                digest = hashlib.sha256("".join(metas).encode()).hexdigest()[:12]
                batch = {"id": f"stub-batch-{digest}", "status": "validating"}
            else:
                try:
                    batch = V.batch_submit(model_key, requests)
                except V.ProviderError as exc:
                    print(f"\nbatch {n} of {len(planned)} was refused, so the refused batch "
                          f"and every later batch were not submitted.\n  {exc}")
                    if "did not complete" in str(exc):
                        print("  The request may still have reached OpenRouter. Check "
                              "the batch list on openrouter.ai before submitting "
                              "these cells again.")
                    print(f"{n - 1} batch(es) were submitted and are in {manifest}.")
                    return 1
            fh.write(json.dumps({
                "event": "submitted", "at": now(), "batch_id": batch["id"],
                "model": model_key, "pin": C.MODELS[model_key].pin,
                "stub": args.stub, "status": batch.get("status"),
                "requests": len(requests), "worst_case_usd": round(worst, 6),
                "cells": metas,
            }) + "\n")
            fh.flush()
            print(f"  submitted {batch['id']}  {C.MODELS[model_key].label}  "
                  f"{len(requests)} requests  {batch.get('status')}")
    print(f"\n{len(planned)} batch(es) recorded in {manifest}. Collect the results "
          f"with `python -m scoring.run batch-collect --out {out}`. A batch is "
          f"answered within 24 hours.")
    return 0


def _stub_results(batch: dict) -> list[dict]:
    """Results for a stub batch, built by the stub provider in the shape OpenRouter uses."""
    results = []
    model = C.MODELS[batch["model"]]
    for cid, meta in batch["cells"].items():
        prompt = I.build(meta["instrument"], meta["condition"], meta["iso3"])
        res = V._stub(model, prompt["system"], prompt["user"], meta["temperature"],
                      meta["instrument"])
        results.append({"custom_id": cid, "error": None, "response": {
            "status_code": 200, "body": {
                "id": None, "model": res["model_version"],
                "choices": [{"message": {"content": res["text"]},
                             "finish_reason": res["stop_reason"]}],
                "usage": {"prompt_tokens": res["input_tokens"],
                          "completion_tokens": res["output_tokens"]}}}})
    return results


def cmd_batch_collect(args) -> int:
    """Write the results of every finished batch in the manifest into the ledger.

    Safe to run as often as wanted. A batch still running is reported and left
    open. A completed batch has one row written for every result whose cell holds
    no row from the same batch, so a collection broken off part-way is finished by
    running the command again. A batch that failed, expired or was cancelled is
    closed with nothing written, so the cells of the batch return to the pending
    cells of the next `batch-submit`.
    """
    out = Path(args.out)
    manifest = manifest_path(out)
    batches = read_manifest(manifest)
    open_batches = [b for b in batches.values() if b["closed"] is None]
    if not open_batches:
        print(f"no open batch in {manifest}")
        return 0
    if not all(b["stub"] for b in open_batches):
        provider = C.PROVIDERS["openrouter"]
        if not os.environ.get(provider.env_var):
            sys.exit(f"nothing was collected, because {provider.env_var} is absent "
                     f"from the environment. Paste the key into {C.ENV_FILE}.")

    done = read_ledger(out)
    written = Counter()
    with out.open("a") as ledger, manifest.open("a") as log:
        for batch in open_batches:
            label = C.MODELS[batch["model"]].label
            if batch["stub"]:
                n = len(batch["cells"])
                state = {"status": "completed", "results": _stub_results(batch),
                         "request_counts": {"total": n, "completed": n, "failed": 0},
                         "usage": None, "error": None, "finalized_at": None}
            else:
                try:
                    state = V.batch_get(batch["batch_id"])
                except V.ProviderError as exc:
                    print(f"  {batch['batch_id']}  {label}  not read, {exc}")
                    continue
            status = state.get("status")
            counts = state.get("request_counts") or {}
            print(f"  {batch['batch_id']}  {label}  {status}  "
                  f"{counts.get('completed', '?')} completed and "
                  f"{counts.get('failed', '?')} failed of {counts.get('total', '?')}")
            if status not in V.BATCH_TERMINAL:
                continue

            rows_written = 0
            if status == "completed":
                for result in state.get("results") or []:
                    meta = batch["cells"].get(result.get("custom_id"))
                    if meta is None:
                        print(f"    a result holds custom_id "
                              f"{result.get('custom_id')!r}, which the manifest "
                              f"never sent, so the result is not written")
                        continue
                    prior = done.get(meta["cell"])
                    if prior is not None and prior.get("batch_id") == batch["batch_id"]:
                        continue
                    row = _base_row(meta, "batch") | {
                        "batch_id": batch["batch_id"], "custom_id": result["custom_id"],
                    }
                    response = result.get("response") or {}
                    if result.get("error") or response.get("status_code", 200) >= 400:
                        problem = result.get("error") or response.get("body")
                        row |= {"outcome": "transport_error",
                                "detail": json.dumps(problem)[:500],
                                "stub": batch["stub"]}
                    else:
                        res = V.completion_record(response.get("body") or {}) | {
                            "seconds": None, "stub": batch["stub"]}
                        cost = V.cost_usd(batch["model"], res["input_tokens"],
                                          res["output_tokens"], route="batch")
                        row = _answered_row(row, res, cost)
                    ledger.write(json.dumps(row) + "\n")
                    ledger.flush()
                    done[meta["cell"]] = row
                    written[row["outcome"]] += 1
                    rows_written += 1
            log.write(json.dumps({
                "event": "closed", "at": now(), "batch_id": batch["batch_id"],
                "status": status, "request_counts": state.get("request_counts"),
                "usage": state.get("usage"), "error": state.get("error"),
                "finalized_at": state.get("finalized_at"),
                "rows_written": rows_written,
            }) + "\n")
            log.flush()
            if status != "completed":
                print(f"    closed with nothing written, so its "
                      f"{len(batch['cells'])} cells return to the next batch-submit. "
                      f"{json.dumps(state.get('error'))[:300]}")
            else:
                cost = (state.get("usage") or {}).get("cost")
                print(f"    {rows_written} rows written"
                      + (f", OpenRouter charged ${cost}" if cost is not None else ""))
    print(f"\n{sum(written.values())} rows written to {out}  {dict(written)}")
    still = sum(1 for b in read_manifest(manifest).values() if b["closed"] is None)
    if still:
        print(f"{still} batch(es) still open. Run this command again later.")
    return 0


def cmd_report(args) -> int:
    ledger = Path(args.ledger)
    rows = list(read_ledger(ledger).values())
    if not rows:
        sys.exit(f"no rows in {args.ledger}")
    stubbed = sum(1 for r in rows if r.get("stub"))
    print(f"{len(rows)} attempts, {stubbed} from the stub provider")
    roles = Counter(r.get("role", "role not recorded") for r in rows)
    print(f"role: {', '.join(f'{n} {name}' for name, n in roles.most_common())}")
    if roles.get("pilot"):
        print("A pilot score settles the instrument wording and the parse schema "
              "and enters no confirmatory analysis.")
    print()
    by_model: dict[str, Counter] = {}
    tokens: dict[str, list[int]] = {}
    for r in rows:
        by_model.setdefault(r["model"], Counter())[r.get("outcome", "?")] += 1
        if r.get("input_tokens"):
            tokens.setdefault(r["model"], []).append(
                r["input_tokens"] + (r.get("output_tokens") or 0))
    width = max(len(m) for m in by_model)
    for model, counter in by_model.items():
        total = sum(counter.values())
        ok = counter.get("ok", 0)
        mean_tok = (f"{sum(tokens[model]) / len(tokens[model]):7.0f}"
                    if model in tokens else "not reported")
        print(f"{model:{width}}  n={total:4}  ok={ok / total:6.1%}  "
              f"mean tokens={mean_tok}  {dict(counter)}")

    # Rows written since the OpenRouter route record the route, so the checks below
    # say whether the pin held, how often the cap of output tokens cut a response
    # short, and how much of the output went to reasoning the response never shows.
    routed = [r for r in rows if r.get("route") and r.get("outcome") != "transport_error"]
    if routed:
        print()
        for model in by_model:
            mine = [r for r in routed if r["model"] == model]
            if not mine:
                continue
            served = Counter(r.get("serving_provider") or "not reported" for r in mine)
            stops = Counter(r.get("stop_reason") or "none" for r in mine)
            reasoning = [r["reasoning_tokens"] for r in mine
                         if r.get("reasoning_tokens") is not None]
            unapplied = sum(1 for r in mine if r.get("temperature_applied") is False)
            line = (f"{model:{width}}  {mine[0]['route']} route, pin {mine[0].get('pin')}, "
                    f"served by {dict(served)}, stop reasons {dict(stops)}")
            if reasoning:
                line += (f", mean reasoning tokens "
                         f"{sum(reasoning) / len(reasoning):,.0f}")
            if unapplied:
                line += f", temperature not applied in {unapplied} rows"
            print(line)

    print()
    # Every row is priced here from its token counts at the price scoring/config.py
    # holds today, because a row written before a price was filled in stores no
    # cost, and a row records the route the row was sent on, which picks the price.
    known = [r for r in rows if r["model"] in C.MODELS]
    listed = [V.cost_usd(r["model"], r.get("input_tokens"), r.get("output_tokens"),
                         route=r.get("route")) for r in known]
    listed = [c for c in listed if c is not None]
    if listed:
        print(f"at the listed price in scoring/config.py today, ${sum(listed):.4f} "
              f"over {len(listed)} calls priced one by one, mean "
              f"${sum(listed) / len(listed):.5f} per call")
    unpriced = sorted({r["model"] for r in known
                       if C.price(r["model"], r.get("route")).get("input") is None
                       or C.price(r["model"], r.get("route")).get("output") is None})
    if unpriced:
        print(f"no price is filled in for {', '.join(unpriced)}. Fill PRICES in "
              f"scoring/config.py from the price page, then rerun this report.")
    charged = [r["reported_cost"] for r in rows
               if r.get("route") == "sync" and r.get("reported_cost") is not None]
    if charged:
        print(f"charged on the sync route, as OpenRouter reported each call, "
              f"${sum(charged):.4f} over {len(charged)} calls")
    batches = [b for b in read_manifest(manifest_path(ledger)).values()
               if b["closed"] and not b["stub"]]
    billed = [(b["closed"].get("usage") or {}).get("cost") for b in batches]
    billed = [c for c in billed if c is not None]
    if batches:
        print(f"charged on the batch route, as OpenRouter reported each batch, "
              f"${sum(billed):.4f} over {len(billed)} of {len(batches)} closed batches")
        # The documentation of OpenRouter shows a batch result with no token count
        # of its own, and a batch as a whole reports its token totals, so the mean
        # per request of a batch-route model is read from the totals as well.
        totals: dict[str, list[int]] = {}
        for b in batches:
            usage = b["closed"].get("usage") or {}
            answered = (b["closed"].get("request_counts") or {}).get("completed") or 0
            if usage.get("prompt_tokens") is None or not answered:
                continue
            held = totals.setdefault(b["model"], [0, 0, 0])
            held[0] += usage.get("prompt_tokens") or 0
            held[1] += usage.get("completion_tokens") or 0
            held[2] += answered
        for model, (tokens_in, tokens_out, answered) in totals.items():
            price = C.price(model, "batch")
            at_list = ""
            if price.get("input") is not None and price.get("output") is not None:
                at_list = (f", ${(tokens_in * price['input'] + tokens_out * price['output']) / 1e6:.4f}"
                           f" at the listed batch price")
            print(f"  {model:{width}}  {tokens_in / answered:,.0f} input and "
                  f"{tokens_out / answered:,.0f} output tokens per request, from the "
                  f"batch totals over {answered} requests{at_list}")
    return 0


def cmd_reparse(args) -> int:
    """Re-read the stored responses in a ledger under the current parse rule.

    The ledger is append-only and is never rewritten, because a ledger records
    what each provider returned and that record does not change when a parse rule
    changes. Every response is stored in the "raw" field, so a changed rule is
    applied by reading the ledger and writing a separate parse table beside the
    ledger, which costs nothing and calls no provider. The parse table names the
    parser version that produced the table, and an analysis reads the parse table
    rather than the ledger.
    """
    ledger = Path(args.ledger)
    rows = list(read_ledger(ledger).values())
    out = ledger.with_suffix(f".parsed_v{P.PARSER_VERSION}.jsonl")
    before, after, moved = Counter(), Counter(), []
    with out.open("w") as fh:
        for row in rows:
            before[row["outcome"]] += 1
            if row.get("raw") is None:
                after[row["outcome"]] += 1
                fh.write(json.dumps(row) + "\n")
                continue
            parsed = P.parse(row["raw"], row["instrument"])
            after[parsed["outcome"]] += 1
            if parsed["outcome"] != row["outcome"]:
                moved.append((row, parsed))
            fh.write(json.dumps(row | {
                "outcome": parsed["outcome"], "value": parsed["value"],
                "detail": parsed["detail"], "coerced": parsed["coerced"],
                "parser": P.PARSER_VERSION,
            }) + "\n")

    print(f"{len(rows)} responses re-read from {ledger.name} into {out.name}, "
          f"under parser version {P.PARSER_VERSION}. No provider was called and "
          f"{ledger.name} was not modified.")
    print()
    print(f"  {'outcome':18} {'as recorded':>12} {'re-read':>10}")
    for outcome in P.RUN_OUTCOMES:
        if before[outcome] or after[outcome]:
            print(f"  {outcome:18} {before[outcome]:12} {after[outcome]:10}")
    coerced = [r for r in map(json.loads, out.read_text().splitlines())
               if r.get("coerced")]
    print()
    print(f"  {len(moved)} responses changed outcome under the current rule")
    for row, parsed in moved[:10]:
        print(f"    {row['instrument']} {row['condition']} {row['iso3']} "
              f"temp {row['temperature']:g} rep {row['replicate']}, "
              f"{row['outcome']} to {parsed['outcome']}"
              + (f", converted {', '.join(parsed['coerced'])}"
                 if parsed["coerced"] else ""))
    print(f"  {len(coerced)} responses carried the right answer in the wrong type "
          f"and needed a conversion, so the count of responses that followed the "
          f"schema exactly is {after['ok'] - len(coerced)} of {len(rows)}")
    return 0


def cell_means(rows: list[dict]) -> dict[tuple[str, str], tuple[float, float, int]]:
    """Mean input and output tokens for every instrument and condition present.

    A flat mean over a part-finished ledger is wrong, and wrong in one direction.
    The harness walks the grid in a fixed order, so the opening rows of a ledger
    are all one instrument under one condition, and the training condition carries
    no administrative record and is the shortest prompt in the whole design.
    Averaging whichever rows happen to be present therefore quotes the cheapest
    cell of the grid as the price of every cell. Splitting the mean by instrument
    and condition, and then refusing to project a stage until every cell that
    stage runs has been measured, is what stops a part-finished ledger from
    underquoting a stage.
    """
    cells: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        cells.setdefault((row["instrument"], row["condition"]), []).append(row)
    return {
        key: (sum(r["input_tokens"] for r in group) / len(group),
              sum(r.get("output_tokens") or 0 for r in group) / len(group),
              len(group))
        for key, group in cells.items()
    }


def cmd_budget(args) -> int:
    """Project every stage from measured token counts and hand-entered prices.

    Token counts come from a ledger and prices come from scoring/config.py, so a
    figure printed here is a measurement multiplied by a published price and never
    an estimate. A model with no price filled in is listed as unpriced rather than
    left out, so a missing price cannot quietly shrink a projection. A stage whose
    instrument and condition cells are not all measured is reported as unmeasured
    rather than projected from the cells that are present. Each model is priced
    on the route the model runs on, and a worst case is printed beside every
    projection, at every call writing the full cap of output tokens, because a
    model that reasons before answering writes more output tokens than the model
    a ledger measured may have written.
    """
    rows = list(read_ledger(Path(args.ledger)).values())
    real = [r for r in rows if not r.get("stub") and r.get("input_tokens")]
    used = real or [r for r in rows if r.get("input_tokens")]
    if not used:
        sys.exit(f"{args.ledger} holds no token count to project from")
    if not real:
        print("WARNING every row in this ledger comes from the stub provider. The "
              "input count is the real prompt, so the input projection holds, and "
              "the output count is invented by the stub, so every output figure "
              "and every cost below is meaningless until one real call replaces it.")
        print()

    means = cell_means(used)
    measured_on = sorted({C.MODELS[r["model"]].label for r in used if r["model"] in C.MODELS})
    print(f"measured over {len(used)} calls in {Path(args.ledger).name}, "
          f"on {', '.join(measured_on)}")
    for instrument in C.INSTRUMENTS:
        for condition in C.CONDITIONS:
            cell = means.get((instrument, condition))
            if cell is None:
                print(f"  {instrument:9} {condition:9} no call yet")
            else:
                print(f"  {instrument:9} {condition:9} {cell[0]:6,.0f} input and "
                      f"{cell[1]:5,.0f} output tokens per call, over "
                      f"{cell[2]} calls")

    any_unpriced = False
    for stage in C.STAGES:
        calls = C.stage_calls(stage)
        keys = (list(C.PILOT_MODELS)[:stage["factors"]["models"]]
                if stage["role"] == "pilot" else list(C.CONFIRMATORY))
        per_model = calls // max(1, len(keys))
        conditions = list(C.CONDITIONS[:stage["factors"]["conditions"]])
        # A stage that runs both instruments is projected once over both. A stage
        # that runs one instrument is projected under the wording section 4.4 of
        # PLAN.md fixes for the confirmatory models.
        choices = ([("both instruments", list(C.INSTRUMENTS))]
                   if stage["factors"]["instruments"] == len(C.INSTRUMENTS)
                   else [(f"under the {i} wording", [i])
                         for i in C.CONFIRMATORY_INSTRUMENTS])
        print()
        print(f"stage {stage['code']}  {stage['name']}")
        print("  " + " x ".join(f"{v} {k}" for k, v in stage["factors"].items())
              + f" = {calls:,} calls, {per_model:,} per model")
        for caption, instruments in choices:
            wanted = [(i, c) for i in instruments for c in conditions]
            absent = [f"{i} {c}" for i, c in wanted if (i, c) not in means]
            print(f"  {caption}")
            if absent:
                print(f"    not projected, because no call has yet measured "
                      f"{', '.join(absent)}")
                continue
            # The grid is balanced, so every cell holds the same number of calls
            # and an unweighted mean over the cells is the mean over the stage.
            mean_in = sum(means[k][0] for k in wanted) / len(wanted)
            mean_out = sum(means[k][1] for k in wanted) / len(wanted)
            print(f"    {mean_in:,.0f} input and {mean_out:,.0f} output tokens per "
                  f"call, so {calls * mean_in / 1e6:.2f} million input tokens and "
                  f"{calls * mean_out / 1e6:.2f} million output tokens")
            print(f"      {'':20} {'projected':>10} {'worst case':>11}")
            total, worst_total, unpriced = 0.0, 0.0, []
            for key in keys:
                route = C.MODELS[key].route
                price = C.price(key)
                if price.get("input") is None or price.get("output") is None:
                    unpriced.append(C.MODELS[key].label)
                    continue
                cost = (per_model * mean_in / 1e6 * price["input"]
                        + per_model * mean_out / 1e6 * price["output"])
                worst = (per_model * mean_in / 1e6 * price["input"]
                         + per_model * C.MAX_OUTPUT_TOKENS / 1e6 * price["output"])
                total += cost
                worst_total += worst
                print(f"      {C.MODELS[key].label:20} ${cost:9,.2f}  ${worst:9,.2f}   "
                      f"{route} at ${price['input']}/${price['output']} per million, "
                      f"read {price['read_on']}")
            if total:
                print(f"      {'priced subtotal':20} ${total:9,.2f}  ${worst_total:9,.2f}")
            if unpriced:
                any_unpriced = True
                print(f"      unpriced, so absent from the subtotal above: "
                      f"{', '.join(unpriced)}")
    print()
    print(f"The projected column applies the token counts measured on "
          f"{', '.join(measured_on)} to every model listed, so a projection for "
          f"another model holds only as far as that model writes as much as "
          f"{', '.join(measured_on)} wrote. The worst case is every call writing "
          f"the full {C.MAX_OUTPUT_TOKENS} output tokens the harness allows, which "
          f"bounds the cost of a model that reasons at length before answering.")
    if any_unpriced:
        print("Fill PRICES in scoring/config.py from each price page, with the date "
              "read, and rerun to price the models listed as unpriced.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scoring.run")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("models", help="confirm every confirmatory model on the public "
                                  "listing of OpenRouter, with no key"
                   ).set_defaults(fn=cmd_models)

    sub.add_parser("records", help="render all 122 records").set_defaults(fn=cmd_records)

    def grid_options(parser, default_models: str):
        parser.add_argument("--countries", default="pilot", help="pilot | all | FRA,IND,...")
        parser.add_argument("--models", default="", help=default_models)
        parser.add_argument("--instruments", default="",
                            help="default is the holistic wording for the confirmatory "
                                 "models and both wordings for a pilot model")
        parser.add_argument("--conditions", default="")
        parser.add_argument("--temperatures", default="")
        parser.add_argument("--replicates", type=int, default=C.REPLICATES)
        parser.add_argument("--out", default=str(C.RUNS / "pilot.jsonl"))
        parser.add_argument("--stub", action="store_true", help="no provider is called")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--retry-failed", action="store_true")
        parser.add_argument("--spend-cap", type=float, default=0.0, help="US dollars")

    r = sub.add_parser("run", help="collect scores on the sync route")
    grid_options(r, "default is the confirmatory models on the sync route. Name a "
                    "pilot model to settle the instrument cheaply.")
    r.add_argument("--max-calls", type=int, default=0)
    r.add_argument("--sleep", type=float, default=0.0, help="seconds between calls")
    r.set_defaults(fn=cmd_run)

    bs = sub.add_parser("batch-submit", help="send the cells of the batch-route "
                                             "models to OpenRouter as batches")
    grid_options(bs, "default is the confirmatory models on the batch route")
    bs.add_argument("--batch-size", type=int, default=100,
                    help="most requests in one batch")
    bs.set_defaults(fn=cmd_batch_submit)

    bc = sub.add_parser("batch-collect", help="write the results of finished "
                                              "batches into the ledger")
    bc.add_argument("--out", default=str(C.RUNS / "pilot.jsonl"))
    bc.set_defaults(fn=cmd_batch_collect)

    p = sub.add_parser("report", help="summarise a ledger")
    p.add_argument("ledger")
    p.set_defaults(fn=cmd_report)

    b = sub.add_parser("budget", help="project every stage from a ledger and the prices")
    b.add_argument("ledger")
    b.set_defaults(fn=cmd_budget)

    rp = sub.add_parser("reparse", help="re-read stored responses under the "
                                        "current parse rule, calling no provider")
    rp.add_argument("ledger")
    rp.set_defaults(fn=cmd_reparse)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
