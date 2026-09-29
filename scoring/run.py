"""
The scoring harness.

    python -m scoring.run models                     confirm every API identifier
    python -m scoring.run records                    render all 122 records to disk
    python -m scoring.run run --stub --countries pilot
    python -m scoring.run run --countries pilot --max-calls 300
    python -m scoring.run report runs/pilot.jsonl

One call writes one line to a JSONL ledger. A run is resumable, because the ledger
is keyed by the cell a line answers, and a cell already answered is skipped unless
--retry-failed is passed. Nothing is overwritten and nothing is deleted, so a
ledger is an append-only record of every attempt, which is what the deposit needs.
"""

from __future__ import annotations

import argparse
import datetime as dt
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


# --- subcommands -----------------------------------------------------------


def cmd_models(args) -> int:
    """Confirm every api_id in config.py against the listing of the provider.

    Three outcomes are reported separately, because a missing key and a wrong
    identifier call for different repairs. No key set means the identifier was
    never checked and scoring/config.py may well be correct. Not served means the
    identifier in scoring/config.py is wrong and has to be replaced by hand.
    """
    chosen = ([p.strip() for p in args.providers.split(",") if p.strip()]
              if args.providers else sorted(C.PROVIDERS))
    unknown = [p for p in chosen if p not in C.PROVIDERS]
    if unknown:
        sys.exit(f"no such provider: {', '.join(unknown)}. "
                 f"Choose from {', '.join(sorted(C.PROVIDERS))}.")

    if C.ENV_NAMES_READ:
        print(f"{len(C.ENV_NAMES_READ)} key name(s) read from {C.ENV_FILE.name}, "
              f"namely {', '.join(sorted(C.ENV_NAMES_READ))}")
    else:
        print(f"no key in {C.ENV_FILE}. Copy .env.example to .env and paste "
              f"one key per line.")
    print()

    confirmed, not_served, not_checked = [], [], []
    for provider_key in chosen:
        wanted = [m for m in C.MODELS.values() if m.provider == provider_key]
        try:
            served = V.list_models(provider_key)
        except V.MissingKey:
            env_var = C.PROVIDERS[provider_key].env_var
            print(f"{provider_key:10} NO KEY    {env_var} is not set, so no "
                  f"identifier was checked")
            not_checked += [m.api_id for m in wanted]
            continue
        except Exception as exc:                       # noqa: BLE001
            print(f"{provider_key:10} ERROR     {type(exc).__name__}: {exc}")
            not_checked += [m.api_id for m in wanted]
            continue
        for model in wanted:
            hit = model.api_id in served
            print(f"{provider_key:10} {'CONFIRMED' if hit else 'NOT SERVED'} "
                  f"{model.api_id}  ({model.label})")
            if hit:
                confirmed.append(model.api_id)
            else:
                not_served.append(model.api_id)
                stem = model.api_id.split("-")[0]
                near = [s for s in served if stem in s][:8] or served[:8]
                print(f"{'':10} the provider serves: {', '.join(near)}")

    print()
    print(f"{len(confirmed)} confirmed, {len(not_served)} not served, "
          f"{len(not_checked)} not checked")
    if not_served:
        print(f"Replace in scoring/config.py: {', '.join(not_served)}")
    if not_checked:
        print("Set a key in .env, then rerun, to check: "
              f"{', '.join(not_checked)}")
    if not not_served and not not_checked:
        print("Every identifier is confirmed against the listing of its provider.")
    return 1 if (not_served or not_checked) else 0


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


def cmd_run(args) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = read_ledger(out)

    countries = _countries(args.countries)
    models = args.models.split(",") if args.models else list(C.CONFIRMATORY)
    unknown = [m for m in models if m not in C.MODELS]
    if unknown:
        sys.exit(f"no such model: {', '.join(unknown)}. Choose from "
                 f"{', '.join(C.MODELS)}.")
    # Pre-flight, before anything is printed or written. A key missing from .env is
    # a fault in the environment and says nothing about a model, so the run stops
    # here. An earlier version caught the missing key once per call and wrote 20
    # lines reading transport_error, which put 20 rows into an append-only research
    # record to report that a key had not been pasted into a file.
    if not args.stub:
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

    roles = {C.MODELS[m].role for m in models}
    if roles == {"pilot"}:
        print("pilot models only. No score in this ledger may enter a "
              "confirmatory analysis.")
    elif len(roles) > 1:
        sys.exit("a ledger holds one role. Run the pilot models and the "
                 "confirmatory models into separate ledgers, so no filtering step "
                 "stands between the raw ledger and the analysis.")
    inst = args.instruments.split(",") if args.instruments else list(C.INSTRUMENTS)
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

    pending = []
    for cell in cells:
        key = cell_id(*cell)
        prior = done.get(key)
        if prior is None:
            pending.append(cell)
        elif args.retry_failed and prior.get("outcome") in ("transport_error", "empty"):
            pending.append(cell)

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
            row = {
                "cell": cell_id(*cell), "written_at": now(),
                "model": model_key, "model_label": C.MODELS[model_key].label,
                "provider": C.MODELS[model_key].provider,
                "role": C.MODELS[model_key].role,
                "iso3": iso3, "country": prompt["country"],
                "instrument": instrument, "instrument_version": I.VERSION,
                "condition": condition, "replicate": replicate,
                "temperature": temperature, "template_sha256_16": template,
                "prompt_sha256_16": prompt["prompt_sha256_16"],
            }
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
                parsed = P.parse(res["text"], instrument)
                cost = V.cost_usd(model_key, res["input_tokens"], res["output_tokens"])
                row |= {
                    "outcome": parsed["outcome"], "value": parsed["value"],
                    "detail": parsed["detail"], "raw": res["text"],
                    "model_version": res["model_version"],
                    "stop_reason": res["stop_reason"],
                    "input_tokens": res["input_tokens"],
                    "output_tokens": res["output_tokens"],
                    "cost_usd": cost, "seconds": res["seconds"], "stub": res["stub"],
                }
                counts[parsed["outcome"]] += 1
                if cost:
                    spent += cost
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


def cmd_report(args) -> int:
    rows = list(read_ledger(Path(args.ledger)).values())
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
                r["input_tokens"] + r.get("output_tokens", 0))
    width = max(len(m) for m in by_model)
    for model, counter in by_model.items():
        total = sum(counter.values())
        ok = counter.get("ok", 0)
        mean_tok = sum(tokens.get(model, [0])) / max(1, len(tokens.get(model, [1])))
        print(f"{model:{width}}  n={total:4}  ok={ok / total:6.1%}  "
              f"mean tokens={mean_tok:7.0f}  {dict(counter)}")
    priced = [r["cost_usd"] for r in rows if r.get("cost_usd")]
    print()
    if priced:
        print(f"measured spend ${sum(priced):.4f} over {len(priced)} priced calls, "
              f"mean ${sum(priced) / len(priced):.5f} per call")
    else:
        print("no call is priced. Fill PRICES in scoring/config.py from each "
              "provider's price page, then rerun this report.")
    return 0


def cmd_budget(args) -> int:
    """Project every stage from measured token counts and hand-entered prices.

    Token counts come from a ledger and prices come from scoring/config.py, so a
    figure printed here is a measurement multiplied by a published price and never
    an estimate. A model with no price filled in is listed as unpriced rather than
    left out, so a missing price cannot quietly shrink a projection.
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

    mean_in = sum(r["input_tokens"] for r in used) / len(used)
    mean_out = sum(r.get("output_tokens") or 0 for r in used) / len(used)
    print(f"measured over {len(used)} calls in {Path(args.ledger).name}, mean "
          f"{mean_in:,.0f} input tokens and {mean_out:,.0f} output tokens per call")

    priced = {k: v for k, v in C.PRICES.items()
              if v.get("input") is not None and v.get("output") is not None}
    for stage in C.STAGES:
        calls = C.stage_calls(stage)
        keys = (list(C.PILOT_MODELS)[:stage["factors"]["models"]]
                if stage["role"] == "pilot" else list(C.CONFIRMATORY))
        per_model = calls // max(1, len(keys))
        print()
        print(f"stage {stage['code']}  {stage['name']}")
        print("  " + " x ".join(f"{v} {k}" for k, v in stage["factors"].items())
              + f" = {calls:,} calls, {per_model:,} per model")
        print(f"  {calls * mean_in / 1e6:.2f} million input tokens, "
              f"{calls * mean_out / 1e6:.2f} million output tokens")
        total, unpriced = 0.0, []
        for key in keys:
            price = priced.get(key)
            if price is None:
                unpriced.append(C.MODELS[key].label)
                continue
            cost = (per_model * mean_in / 1e6 * price["input"]
                    + per_model * mean_out / 1e6 * price["output"])
            total += cost
            print(f"    {C.MODELS[key].label:20} ${cost:9,.2f}   "
                  f"at ${price['input']}/${price['output']} per million, "
                  f"read {price['read_on']}")
        if total:
            print(f"    {'priced subtotal':20} ${total:9,.2f}")
        if unpriced:
            print(f"    unpriced, so absent from the subtotal above: "
                  f"{', '.join(unpriced)}")
    print()
    print("Fill PRICES in scoring/config.py from each price page, with the date "
          "read, and rerun to price the models listed as unpriced.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scoring.run")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("models", help="confirm every API identifier")
    m.add_argument("--providers", default="",
                   help="anthropic,openai,... to check only the providers you hold a key for")
    m.set_defaults(fn=cmd_models)

    sub.add_parser("records", help="render all 122 records").set_defaults(fn=cmd_records)

    r = sub.add_parser("run", help="collect scores")
    r.add_argument("--countries", default="pilot", help="pilot | all | FRA,IND,...")
    r.add_argument("--models", default="",
                   help="default is the six confirmatory models. Name a pilot "
                        "model to settle the instrument cheaply.")
    r.add_argument("--instruments", default="")
    r.add_argument("--conditions", default="")
    r.add_argument("--temperatures", default="")
    r.add_argument("--replicates", type=int, default=C.REPLICATES)
    r.add_argument("--out", default=str(C.RUNS / "pilot.jsonl"))
    r.add_argument("--stub", action="store_true", help="no provider is called")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--retry-failed", action="store_true")
    r.add_argument("--max-calls", type=int, default=0)
    r.add_argument("--spend-cap", type=float, default=0.0, help="US dollars")
    r.add_argument("--sleep", type=float, default=0.0, help="seconds between calls")
    r.set_defaults(fn=cmd_run)

    p = sub.add_parser("report", help="summarise a ledger")
    p.add_argument("ledger")
    p.set_defaults(fn=cmd_report)

    b = sub.add_parser("budget", help="project every stage from a ledger and the prices")
    b.add_argument("ledger")
    b.set_defaults(fn=cmd_budget)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
