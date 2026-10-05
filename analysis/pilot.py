"""
The pilot analysis of Stage B, which answers the five measures of section 7.2 of PLAN.md.

    python -m analysis.pilot          writes every table, figure and summary into results/pilot

The analysis reads three ledgers and one manifest and calls no provider.

    runs/stage_b.jsonl            Stage B, the probe of the six confirmatory models, 600 cells
    runs/stage_b_cap8000.jsonl    the 300 cells of DeepSeek V4 Pro, Kimi K3 and Gemini 3.1 Pro
                                  sent again at a cap of 8,000 output tokens
    runs/stage_b.batches.jsonl    the batches of Claude Opus 5 and GPT-5.6 Sol, with the cost
                                  OpenRouter reported for every closed batch
    runs/stage_a_v2.jsonl         the third pass of Stage A on Claude Haiku 4.5, the pilot
                                  model, read for comparison alone

The scores of a model come from one ledger alone. A model sent again at the cap of 8,000
takes every score from runs/stage_b_cap8000.jsonl, because the cap of 1,500 cut answers of
the model unequally across the two conditions (section 7.3 of PLAN.md) and Stage C, the
confirmatory run, sends the model at 8,000. Every other model takes every score from
runs/stage_b.jsonl. Inside a ledger the last row written for a cell is the row used, so a
cell sent again after a failure is read from the answer that succeeded.

Before any figure is computed, every row used is checked to be a parsed answer that ended
normally, sent on the route, under the wording version and with the record version that
Stage C will use, and every model is checked to hold the full grid of five countries, two
conditions, two temperatures and five calls. A failed check stops the analysis.

The generalisability study uses the calls at temperature one alone, because Stage C runs at
temperature one. Claude Opus 5, GPT-5.6 Sol and Kimi K3 take no temperature at the endpoint
the harness pins, so every call of the three models is a call at the default of the
developer, at temperature zero and at temperature one alike.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from scoring import config as C  # noqa: E402
from scoring import instruments as I  # noqa: E402
from scoring.parse import OUTCOMES  # noqa: E402
from scoring.run import manifest_path, read_manifest  # noqa: E402

from .gstudy import (GStudy, coefficients, d_study, estimate, feldt_interval,  # noqa: E402
                     spearman_brown)

OUT = C.PROJECT / "results" / "pilot"
STAGE_B = C.RUNS / "stage_b.jsonl"
CAP8000 = C.RUNS / "stage_b_cap8000.jsonl"
STAGE_A = C.RUNS / "stage_a_v2.jsonl"
PILOT_MODEL = C.PILOT_MODELS[0]

# Section 4.4 of PLAN.md requires the sentence beside every generalisability coefficient the
# study reports.
LIMITATION = ("The Digital Minds Research Sprint found a share of 0.876 of the variance "
              "separating one model from another in the combination of the model, the prompt "
              "format and the outcome, so a design with one wording cannot estimate how much "
              "the wording contributes, and the coefficient the study reports is optimistic by "
              "an unknown amount.")

LABELS = {"p": "country", "m": "model", "c": "condition", "pm": "country by model",
          "pc": "country by condition", "mc": "model by condition",
          "pmc": "country by model by condition", "r:p": "replicate within cell",
          "r:pm": "replicate within cell", "r:pmc": "replicate within cell"}

DESIGNS = {
    "training": "training data alone, countries by models",
    "record": "administrative record supplied, countries by models",
    "both": "the two conditions together, countries by models by fixed conditions",
}
SETTINGS = (("six models, five calls", 6, 5), ("one model, five calls", 1, 5),
            ("one model, one call", 1, 1))
MODEL_SIZES = list(range(1, 13))
CALL_SIZES = [1, 2, 3, 5, 10]
REFERENCE = 0.80          # a conventional reference line, and no target of the study
MARKERS = ("o", "s", "^", "D", "v", "p")
ANCHORS = (0.0, 50.0, 100.0)    # the three anchor scores of the holistic wording
TITLES = {"training": "Training data alone", "record": "Record supplied",
          "both": "Two conditions, condition fixed"}
CONDITION_NAMES = {"training": "training data alone", "record": "record supplied",
                   "both": "two conditions"}
CONDITION_PROSE = {"training": "training data alone", "record": "the record supplied",
                   "both": "the two conditions together"}
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")

# The price facts `scoring/config.py` records for a model whose charged cost falls well below
# the listed cost. A note states the listing and the run, and names no cause beyond.
PRICE_NOTES = {
    "gpt_5_6_sol": ("The listing of GPT-5.6 Sol marks a discount of 0.5 on the batch route, and "
                    "`scoring/config.py` never takes a discount the listing marks, so the file "
                    "prices the batch route at the full price."),
    "deepseek_v4_pro": ("`scoring/config.py` prices DeepSeek V4 Pro at the higher of the two "
                        "prices the listing gives, the price of two blocks of hours on "
                        "weekdays, and every call of DeepSeek V4 Pro used here was written on "
                        "{days}."),
}


def _countries() -> tuple[tuple[str, ...], dict[str, str]]:
    """The five pilot countries in the order of section 7.1 of PLAN.md, with names."""
    with C.PILOT_COUNTRIES.open() as fh:
        rows = list(csv.DictReader(fh))
    return tuple(r["ISO3"] for r in rows), {r["ISO3"]: r["Country"] for r in rows}


COUNTRIES, NAMES = _countries()


# --- reading -----------------------------------------------------------------


def read_rows(path: Path) -> list[dict]:
    """Every attempt in a ledger, in the order written."""
    with path.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


def latest(rows: list[dict]) -> dict[str, dict]:
    """The last row written for every cell."""
    return {r["cell"]: r for r in rows}


def _check(model: str, rows: list[dict]) -> None:
    spec = C.MODELS[model]
    problems = []
    for r in rows:
        score = (r.get("value") or {}).get("score")
        wrong = [
            f"outcome {r.get('outcome')}" if r.get("outcome") != "ok" else "",
            f"stop reason {r.get('stop_reason')}" if r.get("stop_reason") != "stop" else "",
            f"route {r.get('route')}" if r.get("route") != spec.route else "",
            f"role {r.get('role')}" if r.get("role") != "confirmatory" else "",
            f"instrument {r.get('instrument')}" if r.get("instrument") != "holistic" else "",
            (f"instrument version {r.get('instrument_version')}"
             if r.get("instrument_version") != I.VERSION else ""),
            (f"record version {r.get('record_version')}"
             if r.get("record_version") != C.RECORD_VERSION else ""),
            "stub" if r.get("stub") else "",
            (f"temperature applied {r.get('temperature_applied')}"
             if r.get("temperature_applied") is not spec.takes_temperature else ""),
            (f"score {score!r}" if not isinstance(score, (int, float)) or isinstance(score, bool)
             or not 0 <= score <= 100 else ""),
        ]
        problems += [f"{r['cell']} {w}" for w in wrong if w]
    grid = Counter((r["iso3"], r["condition"], float(r["temperature"]), r["replicate"])
                   for r in rows)
    want = {(i, c, float(t), k) for i in COUNTRIES for c in C.CONDITIONS
            for t in C.TEMPERATURES for k in range(1, C.REPLICATES + 1)}
    if set(grid) != want or any(n != 1 for n in grid.values()):
        problems.append(f"{model} holds {len(set(grid) & want)} of the {len(want)} cells of "
                        f"the grid and {len(set(grid) - want)} cells outside the grid")
    if problems:
        raise SystemExit(f"{len(problems)} problems in the rows of {model}, first "
                         + "; ".join(problems[:5]))


def score_rows(b_rows: list[dict], k_rows: list[dict]) -> tuple[dict[str, Path], list[dict]]:
    """The ledger every confirmatory model takes scores from, and the 600 rows used."""
    resent = {r["model"] for r in k_rows}
    source = {m: CAP8000 if m in resent else STAGE_B for m in C.CONFIRMATORY}
    b_latest, k_latest = latest(b_rows), latest(k_rows)
    used = []
    for m in C.CONFIRMATORY:
        rows = [r for r in (k_latest if m in resent else b_latest).values() if r["model"] == m]
        _check(m, rows)
        used += rows
    return source, used


def pilot_rows() -> list[dict]:
    """The 100 holistic rows of the third pass of Stage A on the pilot model."""
    rows = [r for r in latest(read_rows(STAGE_A)).values() if r["instrument"] == "holistic"]
    bad = [r["cell"] for r in rows if r.get("outcome") != "ok" or r["model"] != PILOT_MODEL]
    if bad or len(rows) != len(COUNTRIES) * 2 * 2 * C.REPLICATES:
        raise SystemExit(f"{STAGE_A.name} holds {len(rows)} holistic rows, {len(bad)} unusable")
    return rows


def array(rows: list[dict], temperature: float, models: tuple[str, ...]) -> np.ndarray:
    """Scores as an array of country by model by condition by call."""
    x = np.full((len(COUNTRIES), len(models), len(C.CONDITIONS), C.REPLICATES), np.nan)
    for r in rows:
        if float(r["temperature"]) == temperature and r["model"] in models:
            x[COUNTRIES.index(r["iso3"]), models.index(r["model"]),
              C.CONDITIONS.index(r["condition"]), r["replicate"] - 1] = float(r["value"]["score"])
    if np.isnan(x).any():
        raise SystemExit(f"{int(np.isnan(x).sum())} scores missing at temperature {temperature:g}")
    return x


def write_csv(name: str, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (OUT / name).open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (round(v, 6) if isinstance(v, float) else v)
                             for k, v in row.items()})


def words(n: int) -> str:
    """A whole number as the documents of the project write a number, in words below ten."""
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else f"{n:,}"


def listing(items, last: str = "and") -> str:
    """Items joined as prose, with `last` before the last item."""
    items = list(items)
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {last} " + items[-1]


def num(value, places: int) -> str:
    """A number to a fixed number of decimal places, and a blank where no number exists."""
    return "" if value is None else f"{value:,.{places}f}"


def pct(part: int, whole: int) -> str:
    """A count as a share of a whole, in per cent to one decimal place at most."""
    return f"{round(100 * part / whole, 1):g}"


def table(header: list[str], rows: list[list]) -> str:
    """A Markdown table, with a blank cell where no value exists."""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join("" if v is None else str(v) for v in row) + " |"
              for row in rows]
    return "\n".join(lines) + "\n"


# --- measures 7.2.1 and 7.2.2, cost ------------------------------------------


def batch_charges(path: Path) -> dict[str, dict]:
    """The cost OpenRouter reported for the closed batches of every model."""
    held: dict[str, dict] = {}
    for b in read_manifest(path).values():
        if b["stub"] or not b["closed"]:
            continue
        usage = b["closed"].get("usage") or {}
        answered = (b["closed"].get("request_counts") or {}).get("completed") or 0
        if usage.get("cost") is None:
            continue
        mine = held.setdefault(b["model"], {"cost": 0.0, "requests": 0, "batches": 0})
        mine["cost"] += usage["cost"]
        mine["requests"] += answered
        mine["batches"] += 1
    return held


def cost_tables(used: list[dict], source: dict[str, Path]) -> tuple[list[dict], list[dict]]:
    charges = batch_charges(manifest_path(STAGE_B))
    stage_c = next(s for s in C.STAGES if s["code"] == "C")
    per_model = C.stage_calls(stage_c) // stage_c["factors"]["models"]
    per_condition = per_model // stage_c["factors"]["conditions"]
    cost, projection = [], []
    for m in C.CONFIRMATORY:
        spec, price, cap = C.MODELS[m], C.price(m), C.output_cap(m)
        listed = {}
        for condition in (*C.CONDITIONS, "both"):
            rows = [r for r in used if r["model"] == m
                    and condition in ("both", r["condition"])]
            tokens_in = mean(r["input_tokens"] for r in rows)
            tokens_out = mean(r["output_tokens"] for r in rows)
            listed[condition] = (tokens_in * price["input"] + tokens_out * price["output"]) / 1e6
            if spec.route == "sync":
                charged = mean(r["reported_cost"] for r in rows)
                basis = "sync, mean of the cost OpenRouter reported for every call"
            elif condition == "both" and m in charges:
                charged = charges[m]["cost"] / charges[m]["requests"]
                basis = (f"batch, cost OpenRouter reported for {charges[m]['batches']} closed "
                         f"batches over {charges[m]['requests']} requests answered")
            else:
                charged, basis = None, "batch, reported for a batch as a whole alone"
            cost.append({
                "model": spec.label, "condition": condition, "ledger": source[m].name,
                "route": spec.route, "calls": len(rows),
                "mean_input_tokens": tokens_in, "mean_output_tokens": tokens_out,
                "mean_reasoning_tokens": mean(r.get("reasoning_tokens") or 0 for r in rows),
                "largest_output_tokens": max(r["output_tokens"] for r in rows),
                "price_input_per_million": price["input"],
                "price_output_per_million": price["output"],
                "listed_usd_per_call": listed[condition],
                "charged_usd_per_call": charged, "charged_basis": basis,
            })
            if condition == "both":
                both_rows, both_charged = rows, charged
        warm = [r for r in used if r["model"] == m and float(r["temperature"]) == 1.0]
        warm_listed = (mean(r["input_tokens"] for r in warm) * price["input"]
                       + mean(r["output_tokens"] for r in warm) * price["output"]) / 1e6
        worst = (mean(r["input_tokens"] for r in both_rows) * price["input"]
                 + cap * price["output"]) / 1e6
        projection.append({
            "model": spec.label, "route": spec.route, "output_cap": cap,
            "training_calls": per_condition,
            "training_listed_usd": per_condition * listed["training"],
            "record_calls": per_condition,
            "record_listed_usd": per_condition * listed["record"],
            "calls": per_model, "listed_usd": per_model * listed["both"],
            "listed_usd_from_temperature_one": per_model * warm_listed,
            "charged_rate_usd": per_model * both_charged if both_charged is not None else None,
            "worst_case_usd": per_model * worst,
        })
    total = {"model": "all six models", "route": "", "output_cap": ""}
    for key in list(projection[0])[3:]:
        values = [row[key] for row in projection]
        total[key] = sum(values) if all(v is not None for v in values) else None
    projection.append(total)
    return cost, projection


# --- measure 7.2.3, parse outcomes -------------------------------------------


def first_answers(rows: list[dict], model: str) -> dict[str, dict]:
    """The first attempt a provider answered, for every cell of a model in a ledger."""
    first: dict[str, dict] = {}
    for r in rows:
        if r["model"] == model and r["outcome"] != "transport_error":
            first.setdefault(r["cell"], r)
    return first


def parse_table(b_rows: list[dict], k_rows: list[dict], source: dict[str, Path]) -> list[dict]:
    """Outcomes of the first answered attempt of every cell, for every ledger and model.

    A cell can hold several attempts. The first attempt a provider answered is the attempt a
    rate of parse outcomes describes, because a later attempt exists only where an earlier
    attempt failed, so counting later attempts would understate failure. An attempt the
    provider never answered is counted apart as a transport error."""
    out = []
    for path, rows in ((STAGE_B, b_rows), (CAP8000, k_rows)):
        for m in C.CONFIRMATORY:
            mine = [r for r in rows if r["model"] == m]
            if not mine:
                continue
            first = first_answers(mine, m)
            end = latest(mine)
            caps = sorted({r.get("max_tokens", C.CAP_BEFORE_RECORDING) for r in mine})
            outcomes = Counter(r["outcome"] for r in first.values())
            stops = Counter(r.get("stop_reason") for r in first.values())
            out.append({
                "ledger": path.name, "model": C.MODELS[m].label, "route": mine[0]["route"],
                "output_cap": " and ".join(f"{c}" for c in caps), "attempts": len(mine),
                "transport_error_attempts": sum(r["outcome"] == "transport_error" for r in mine),
                "cells": len(end), "cells_answered": len(first),
                **{f"first_{o}": outcomes.get(o, 0) for o in OUTCOMES},
                "first_stop_length": stops.get("length", 0),
                "first_stop_error": stops.get("error", 0),
                "cells_scored_at_end": sum(r["outcome"] == "ok" for r in end.values()),
                "scores_used": "yes" if source[m] == path else "no",
            })
    return out


# --- measure 7.2.4, replicates -----------------------------------------------


def groups(used: list[dict], pilot: list[dict]) -> list[tuple[str, str, list[dict]]]:
    """The stage, the model and the rows of the six models of Stage B and the pilot model."""
    return [("B", m, used) for m in C.CONFIRMATORY] + [("A", PILOT_MODEL, pilot)]


def spread_tables(used: list[dict], pilot: list[dict]) -> tuple[list[dict], list[dict]]:
    spread, cells = [], []
    for stage, m, rows in groups(used, pilot):
        for t in C.TEMPERATURES:
            mine = [r for r in rows if r["model"] == m and float(r["temperature"]) == t]
            sds = []
            for iso in COUNTRIES:
                for condition in C.CONDITIONS:
                    scores = [float(r["value"]["score"]) for r in
                              sorted((r for r in mine if r["iso3"] == iso
                                      and r["condition"] == condition),
                                     key=lambda r: r["replicate"])]
                    sd = float(np.std(scores, ddof=1))
                    sds.append(sd)
                    cells.append({
                        "stage": stage, "model": C.MODELS[m].label, "temperature": t,
                        "temperature_applied": mine[0].get("temperature_applied", C.MODELS[m].takes_temperature),
                        "country": iso, "condition": condition, "calls": len(scores),
                        "mean": float(np.mean(scores)), "sd": sd, "lowest": min(scores),
                        "highest": max(scores), "scores": " ".join(f"{s:g}" for s in scores),
                    })
            spread.append({
                "stage": stage, "model": C.MODELS[m].label, "temperature": t,
                "temperature_applied": mine[0].get("temperature_applied", C.MODELS[m].takes_temperature),
                "cells": len(sds), "identical_cells": sum(sd == 0 for sd in sds),
                "distinct_scores": len({float(r["value"]["score"]) for r in mine}),
                "mean_within_cell_sd": float(np.mean(sds)),
                "largest_within_cell_sd": float(np.max(sds)),
            })
    return spread, cells


def value_table(used: list[dict], pilot: list[dict]) -> list[dict]:
    """For every model, condition and temperature, the distinct scores among the calls and
    the calls which returned an anchor score of the holistic wording exactly."""
    out = []
    for stage, m, rows in groups(used, pilot):
        for condition in C.CONDITIONS:
            for t in C.TEMPERATURES:
                mine = [r for r in rows if r["model"] == m and r["condition"] == condition
                        and float(r["temperature"]) == t]
                scores = [float(r["value"]["score"]) for r in mine]
                out.append({
                    "stage": stage, "model": C.MODELS[m].label, "condition": condition,
                    "temperature": t,
                    "temperature_applied": mine[0].get("temperature_applied",
                                                       C.MODELS[m].takes_temperature),
                    "calls": len(scores), "distinct_scores": len(set(scores)),
                    "anchor_scores": sum(s in ANCHORS for s in scores),
                    "lowest": min(scores), "highest": max(scores),
                })
    return out


# --- measure 7.2.5, the generalisability study -------------------------------


def designs(x: np.ndarray) -> dict[str, tuple[np.ndarray, str, tuple[str, ...]]]:
    """The three designs, with the array, the factor letters and the fixed factors."""
    return {"training": (x[:, :, 0, :], "pm", ()), "record": (x[:, :, 1, :], "pm", ()),
            "both": (x, "pmc", ("c",))}


def n_prime(design: str, models: int, calls: int) -> dict[str, int]:
    return ({"m": models, "c": len(C.CONDITIONS), "r": calls} if design == "both"
            else {"m": models, "r": calls})


def coefficient_rows(design: str, gs: GStudy, fixed: tuple[str, ...]) -> list[dict]:
    """Three settings of one design. At six models and five calls the interval is exact, and
    at one model and five calls the interval is the exact interval passed through the
    Spearman-Brown formula, which is exact because the formula is increasing. One call per
    cell changes the replicate term alone, so no exact interval exists for that setting."""
    n_m = gs.n["m"]
    rho_hat = 1 - gs.ms["pm"] / gs.ms["p"]
    lo, hi = feldt_interval(rho_hat, gs.df["pm"], gs.df["p"])
    rows = []
    for label, models, calls in SETTINGS:
        size = n_prime(design, models, calls)
        kept = coefficients(gs, size, fixed=fixed)
        raw = coefficients(gs, size, fixed=fixed, truncated=False)
        row = {"design": design, "setting": label, "models": models, "calls": calls,
               "erho2": kept["Erho2"], "phi": kept["Phi"],
               "erho2_untruncated": raw["Erho2"], "lower_95": None, "upper_95": None,
               "interval": "none, no exact interval when the number of calls changes"}
        if calls == gs.n["r"]:
            factor = models / n_m
            row["lower_95"] = spearman_brown(lo, factor)
            row["upper_95"] = spearman_brown(hi, factor)
            row["interval"] = (f"exact, F on {words(gs.df['pm'])} and {words(gs.df['p'])} "
                               "degrees of freedom"
                               + ("" if factor == 1 else
                                  f", converted to {words(models)} model"
                                  f"{'' if models == 1 else 's'} by the Spearman-Brown formula"))
        rows.append(row)
    return rows


def one_way(x: np.ndarray) -> dict:
    """Reliability of one model as a measure of countries, from five calls per country."""
    gs = estimate(x, "p")
    rho_hat = 1 - gs.ms["r:p"] / gs.ms["p"]
    k = gs.n["r"]
    # Where the five calls agree in every country, the within-cell variance is zero, the
    # coefficient is one by construction and the F interval collapses to a point, so no
    # interval is reported.
    agreed = gs.ms["r:p"] == 0
    lo, hi = (None, None) if agreed else feldt_interval(rho_hat, gs.df["r:p"], gs.df["p"])
    return {
        "between_country_variance": gs.components["p"],
        "within_cell_variance": gs.components["r:p"],
        "ms_country": gs.ms["p"], "ms_within_cell": gs.ms["r:p"],
        "df_country": gs.df["p"], "df_within_cell": gs.df["r:p"],
        "reliability_mean_of_five_calls": rho_hat, "lower_95": lo, "upper_95": hi,
        "reliability_one_call": spearman_brown(rho_hat, 1 / k),
        "one_call_lower_95": None if agreed else spearman_brown(lo, 1 / k),
        "one_call_upper_95": None if agreed else spearman_brown(hi, 1 / k),
        "negative_components": " ".join(gs.negatives),
        "note": ("the five calls agreed in every country, so no interval exists" if agreed
                 else ""),
    }


def g_tables(x: np.ndarray, pilot_x: np.ndarray) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"components": [], "coefficients": [], "d_study": [],
                                  "reliability": [], "leave_one_out": []}
    studies = {}
    for design, (data, facets, fixed) in designs(x).items():
        gs = estimate(data, facets)
        studies[design] = gs
        shares = gs.shares()
        for key in gs.components:
            out["components"].append({
                "design": design, "component": LABELS[key], "key": key,
                "variance": gs.components[key], "untruncated": gs.untruncated[key],
                "share": shares[key], "ms": gs.ms[key], "df": gs.df[key],
                "set_to_zero": "yes" if key in gs.negatives else "no"})
        out["coefficients"] += coefficient_rows(design, gs, fixed)
        for row in d_study(gs, {k: (MODEL_SIZES if k == "m" else CALL_SIZES if k == "r"
                                    else [len(C.CONDITIONS)])
                                for k in n_prime(design, 1, 1)}, fixed=fixed):
            out["d_study"].append({"design": design, "models": row["n_prime"]["m"],
                                   "calls": row["n_prime"]["r"], "erho2": row["Erho2"],
                                   "phi": row["Phi"]})
        for drop in (None, *C.CONFIRMATORY):
            keep = [j for j, m in enumerate(C.CONFIRMATORY) if m != drop]
            part = estimate(data[:, keep], facets)
            row = {"design": design,
                   "model_left_out": C.MODELS[drop].label if drop else "none"}
            # A component outside the design is left blank, so the three designs share columns.
            row.update({label.replace(" ", "_"): None for label in dict.fromkeys(LABELS.values())})
            row.update({LABELS[k].replace(" ", "_"): v for k, v in part.components.items()})
            for label, models, calls in SETTINGS[:2]:
                row[f"erho2_{label.replace(', ', '_').replace(' ', '_')}"] = coefficients(
                    part, n_prime(design, models, calls), fixed=fixed)["Erho2"]
            row["set_to_zero"] = " ".join(LABELS[k] for k in part.negatives)
            out["leave_one_out"].append(row)
    for stage, models, data in (("B", C.CONFIRMATORY, x), ("A", (PILOT_MODEL,), pilot_x)):
        for j, m in enumerate(models):
            for c, condition in enumerate(C.CONDITIONS):
                out["reliability"].append({
                    "stage": stage, "model": C.MODELS[m].label, "condition": condition,
                    "temperature": 1.0, **one_way(data[:, j, c, :])})
    out["studies"] = studies
    return out


# --- figures -----------------------------------------------------------------


def _save(fig, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def figures(x: np.ndarray, g: dict, cells: list[dict]) -> None:
    plt.rcParams.update({"font.size": 8, "axes.linewidth": 0.6, "font.family": "DejaVu Sans"})
    labels = [C.MODELS[m].label for m in C.CONFIRMATORY]
    names = [NAMES[i].replace(" ", "\n") for i in COUNTRIES]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.3), sharey=True)
    offsets = np.linspace(-0.3, 0.3, len(C.CONFIRMATORY))
    for ax, (c, condition) in zip(axes, enumerate(C.CONDITIONS)):
        for j, label in enumerate(labels):
            for i in range(len(COUNTRIES)):
                ax.scatter(np.full(C.REPLICATES, i + offsets[j]), x[i, j, c, :],
                           marker=MARKERS[j], facecolors="none", edgecolors="black",
                           linewidths=0.6, s=16, label=label if i == 0 else None)
        ax.set_xticks(range(len(COUNTRIES)), names)
        ax.set_title("Training data alone" if condition == "training"
                     else "Administrative record supplied")
        ax.set_ylim(-3, 103)
        ax.grid(axis="y", color="0.85", linewidth=0.5)
    axes[0].set_ylabel("Score out of 100")
    axes[1].legend(frameon=False, loc="upper right", fontsize=7)
    _save(fig, "fig1_scores")

    # Every panel lists the eight components of the design with two conditions, so a row
    # reads across the three panels, and a component outside a design is marked as outside
    # the design.
    order = list(dict.fromkeys(LABELS.values()))
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.0), sharex=True, sharey=True)
    for ax, design in zip(axes, DESIGNS):
        share = {r["component"]: r["share"] for r in g["components"] if r["design"] == design}
        ax.barh(range(len(order)), [share.get(k, 0.0) for k in order], color="0.6",
                edgecolor="black", linewidth=0.5)
        for k, component in enumerate(order):
            if component in share:
                ax.text(share[component] + 0.02, k, f"{share[component]:.2f}", va="center",
                        fontsize=7)
            else:
                ax.text(0.02, k, "not in design", va="center", fontsize=6.5, color="0.45")
        ax.set_xlim(0, 1)
        ax.set_title(TITLES[design])
        ax.set_xlabel("Share of score variance")
    axes[0].set_yticks(range(len(order)), order)
    axes[0].invert_yaxis()
    _save(fig, "fig3_variance_shares")

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8), sharey=True)
    styles = {1: (0, (1, 1.5)), 2: (0, (4, 1.5, 1, 1.5)), 3: (0, (5, 2)), 5: "-", 10: "-"}
    greys = {1: "black", 2: "black", 3: "black", 5: "black", 10: "0.55"}
    for ax, design in zip(axes, DESIGNS):
        for calls in CALL_SIZES:
            rows = [r for r in g["d_study"] if r["design"] == design and r["calls"] == calls]
            ax.plot([r["models"] for r in rows], [r["erho2"] for r in rows],
                    linestyle=styles[calls], color=greys[calls], linewidth=0.9,
                    label=f"{calls} call" + ("s" if calls > 1 else "") + " per cell")
        mark = next(r for r in g["d_study"] if r["design"] == design
                    and r["models"] == 6 and r["calls"] == 5)
        ax.plot([6], [mark["erho2"]], marker="o", color="black", markersize=4)
        ax.axhline(REFERENCE, color="0.4", linestyle="--", linewidth=0.6)
        ax.text(12, REFERENCE + 0.015, "conventional reference", ha="right", fontsize=6.5,
                color="0.3")
        ax.set_xticks([1, 2, 4, 6, 8, 10, 12])
        ax.set_ylim(0.5, 1)
        ax.set_xlabel("Models averaged")
        ax.set_title(TITLES[design])
    axes[0].set_ylabel("Generalisability coefficient")
    axes[0].legend(frameon=False, fontsize=6.5, loc="lower right")
    _save(fig, "fig4_decision_study")

    fig, ax = plt.subplots(figsize=(3.6, 3.4))
    stage_b = [c for c in cells if c["stage"] == "B"]
    for j, (m, label) in enumerate(zip(C.CONFIRMATORY, labels)):
        cold = [c["sd"] for c in stage_b if c["model"] == label and c["temperature"] == 0.0]
        warm = [c["sd"] for c in stage_b if c["model"] == label and c["temperature"] == 1.0]
        ax.scatter(cold, warm, marker=MARKERS[j], facecolors="none", edgecolors="black",
                   linewidths=0.6, s=18, label=label + ("" if C.MODELS[m].takes_temperature
                                                        else ", temperature not sent"))
    top = max(c["sd"] for c in stage_b) * 1.05
    ax.plot([0, top], [0, top], color="0.5", linestyle="--", linewidth=0.6)
    ax.set_xlim(-0.8, top)
    ax.set_ylim(-0.8, top)
    ax.set_xlabel("Standard deviation of five calls, temperature zero")
    ax.set_ylabel("Standard deviation of five calls, temperature one")
    ax.legend(frameon=False, fontsize=6.5, loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncol=2)
    _save(fig, "fig2_replicate_spread")


# --- summary -----------------------------------------------------------------


def _rel(path: Path) -> str:
    return str(path.relative_to(C.PROJECT))


def _interval(lo, hi) -> str:
    return "" if lo is None else f"{lo:.3f} to {hi:.3f}"


def _per_thousand(value) -> str:
    return num(None if value is None else value * 1000, 2)


def _cap(value) -> str:
    return " and ".join(f"{int(c):,}" for c in str(value).split(" and ")) if value != "" else ""


def _design(design: str) -> str:
    return CONDITION_NAMES[design].capitalize()


def summary(t: dict) -> str:
    """The five measures of section 7.2 of PLAN.md in Markdown, every number read from the
    tables of the same run."""
    g, used, source = t["g"], t["used"], t["source"]
    label = {m: C.MODELS[m].label for m in C.MODELS}
    resent = [m for m in C.CONFIRMATORY if source[m] == CAP8000]
    kept = [m for m in C.CONFIRMATORY if source[m] == STAGE_B]
    calls, n_models = C.REPLICATES, len(C.CONFIRMATORY)
    n_cells = len(COUNTRIES) * len(C.CONDITIONS)
    quote = "> " + LIMITATION + "\n"
    md = [
        "# Pilot analysis of Stage B\n",
        f"Written by `python -m analysis.pilot` from `{_rel(STAGE_B)}` and `{_rel(CAP8000)}`, "
        f"with the cost of the batches read from `{_rel(manifest_path(STAGE_B))}`. The third "
        f"pass of Stage A, the earlier pilot on {label[PILOT_MODEL]}, is read from "
        f"`{_rel(STAGE_A)}` for comparison alone. The program writes the file again on every "
        "run, so no figure below is typed by hand, and `README.md` in the same folder "
        "describes every table and figure the program writes.\n",
        f"Every figure below is a pilot figure on {words(len(COUNTRIES))} countries, "
        f"{listing(NAMES[i] for i in COUNTRIES)}, and no confirmatory analysis uses any of the "
        f"figures. Stage B asked the {words(n_models)} confirmatory models to score the "
        f"{words(len(COUNTRIES))} countries under the {words(len(C.CONDITIONS))} conditions, "
        "training data alone and the administrative record supplied in the prompt, at "
        f"temperature zero and at temperature one, with {words(calls)} calls for every country, "
        "model, condition and temperature, under the holistic wording at instrument version "
        f"{I.VERSION}. A cell below means the {words(calls)} calls of one country, model, "
        "condition and temperature. Stage C, the confirmatory run, asks the same models to "
        f"score every country of the study. The scores of {listing(label[m] for m in resent)} "
        f"come from `{_rel(CAP8000)}`, where the {words(len(resent))} models were sent again "
        f"at the output cap of {C.output_cap(resent[0]):,} tokens which Stage C uses, and the "
        f"scores of {listing(label[m] for m in kept)} come from `{_rel(STAGE_B)}`. All "
        f"{words(len(used))} scores used pass every check of `analysis/pilot.py`.\n",
    ]

    # Measure 7.2.1
    cost = t["cost"]
    per_model = next(r["calls"] for r in cost if r["condition"] == "both")
    both = {r["model"]: r for r in cost
            if r["condition"] == "both" and r["charged_usd_per_call"] is not None}
    ratio = {m: both[label[m]]["charged_usd_per_call"] / both[label[m]]["listed_usd_per_call"]
             for m in C.CONFIRMATORY if label[m] in both}
    notes = []
    for m, text in PRICE_NOTES.items():
        if m in ratio and ratio[m] < 0.9:
            days = sorted({r["written_at"][:10] for r in used if r["model"] == m})
            notes.append(text.format(
                days=listing(f"{date.fromisoformat(d):%A} {d}" for d in days)))
    md += [
        "## 1. Cost per call (section 7.2.1)\n",
        "The listed cost per call prices the mean input and output tokens the provider "
        f"recorded over the {words(per_model)} calls of a model in Stage B at the listed price "
        "per million tokens which `scoring/config.py` holds for the route of the model. The "
        "table gives the cost of 1,000 calls in US dollars under each condition and under the "
        "two conditions together, with the token counts as means per call. The charged cost is "
        "the cost reported by OpenRouter, the service which passes every call of the "
        f"{words(n_models)} models to the provider. On the sync route OpenRouter reports the "
        "cost of every call, and the table gives the mean. On the batch route OpenRouter "
        "reports the cost of a whole batch, so a charged cost exists for the two conditions "
        "together alone, as the cost of the closed batches divided by the requests answered. "
        "The study scores with one instrument, the holistic wording which section 4.4 of "
        "PLAN.md fixed, so cost by instrument has one level, and `scoring/config.py` pins "
        "every confirmatory model to one endpoint, so cost by model is cost by provider.\n",
        table(["Model", "Condition", "Route", "Input tokens", "Output tokens",
               "Reasoning tokens", "Listed USD per 1,000 calls", "Charged USD per 1,000 calls"],
              [[r["model"], CONDITION_NAMES[r["condition"]], r["route"],
                num(r["mean_input_tokens"], 1), num(r["mean_output_tokens"], 1),
                num(r["mean_reasoning_tokens"], 1), _per_thousand(r["listed_usd_per_call"]),
                _per_thousand(r["charged_usd_per_call"])] for r in cost]),
        "Under the two conditions together, the charged cost as a share of the listed cost was "
        + listing(f"{100 * v:.0f} per cent for {label[m]}" for m, v in ratio.items()) + ". "
        + " ".join(notes) + "\n",
    ]

    # Measure 7.2.2
    proj = t["projection"]
    total = proj[-1]
    stage_c = next(s for s in C.STAGES if s["code"] == "C")["factors"]
    md += [
        "## 2. Projected cost of the training condition in Stage C (section 7.2.2)\n",
        f"Stage C asks every confirmatory model to score {words(stage_c['countries'])} "
        f"countries at temperature one, with {words(stage_c['replicates'])} calls for every "
        f"country under the {words(stage_c['conditions'])} conditions, so a model receives "
        f"{words(proj[0]['training_calls'])} calls under the training condition and "
        f"{words(proj[0]['record_calls'])} under the record condition, and the "
        f"{words(stage_c['models'])} models receive {words(total['calls'])} calls in all. The "
        "projection multiplies the calls of Stage C by the cost per call of measure one, in US "
        "dollars. The listed projection takes the calls of Stage B at both temperatures, and "
        "the projection from temperature one takes the calls at temperature one alone, the "
        "temperature of Stage C. The charged projection takes the rate OpenRouter charged in "
        "Stage B. The worst case prices every call at the mean input tokens of the model and "
        "at the full output cap.\n",
        table(["Model", "Route", "Output cap", "Training, listed", "Record, listed",
               "Two conditions, listed", "Two conditions, from temperature one",
               "Two conditions, at the charged rate", "Two conditions, worst case"],
              [[r["model"][:1].upper() + r["model"][1:], r["route"], _cap(r["output_cap"]),
                num(r["training_listed_usd"], 2),
                num(r["record_listed_usd"], 2), num(r["listed_usd"], 2),
                num(r["listed_usd_from_temperature_one"], 2), num(r["charged_rate_usd"], 2),
                num(r["worst_case_usd"], 2)] for r in proj]),
        f"The {words(total['training_calls'])} scores of the training condition are projected "
        f"at {num(total['training_listed_usd'], 2)} dollars at listed prices. The two "
        f"conditions together, {words(total['calls'])} calls, are projected at "
        f"{num(total['listed_usd'], 2)} dollars at listed prices, at "
        f"{num(total['listed_usd_from_temperature_one'], 2)} dollars from the calls at "
        f"temperature one alone and at {num(total['charged_rate_usd'], 2)} dollars at the rate "
        f"charged in Stage B, and the worst case is {num(total['worst_case_usd'], 2)} dollars.\n",
    ]

    # Measure 7.2.3
    parse = t["parse"]
    in_use = [r for r in parse if r["scores_used"] == "yes"]
    lines = [f"In the ledgers the scores come from, "
             f"{words(sum(r['first_ok'] for r in in_use))} of the "
             f"{words(sum(r['cells_answered'] for r in in_use))} first answers are `ok`."]
    for path, rows in ((STAGE_B, t["b_rows"]), (CAP8000, t["k_rows"])):
        for m in C.CONFIRMATORY:
            if source[m] != path:
                continue
            failed = [r for r in first_answers(rows, m).values() if r["outcome"] != "ok"]
            if not failed:
                continue
            outcomes = Counter(r["outcome"] for r in failed)
            stops = sorted({str(r.get("stop_reason")) for r in failed})
            end = latest([r for r in rows if r["model"] == m])
            lines.append(
                f"{label[m]} gave {listing(f'{words(n)} `{o}`' for o, n in outcomes.items())} "
                f"first answer{'s' if len(failed) > 1 else ''}, which ended with the stop "
                f"reason{'s' if len(stops) > 1 else ''} {listing(f'`{s}`' for s in stops)}"
                + (f", and every call of {label[m]} was scored in the end."
                   if all(r["outcome"] == "ok" for r in end.values()) else "."))
    never = [o for o in OUTCOMES if not any(r[f"first_{o}"] for r in parse)]
    if never:
        lines.append("No first answer in either ledger is "
                     + listing((f"`{o}`" for o in never), last="or") + ".")
    cut = [r for r in parse if r["ledger"] == STAGE_B.name and r["first_stop_length"]]
    if cut:
        lines.append(
            f"At the cap of {listing(sorted({_cap(r['output_cap']) for r in cut}))} output "
            f"tokens in `{_rel(STAGE_B)}`, the first answer ended at the cap in "
            + listing(f"{words(r['first_stop_length'])} calls of {r['model']}" for r in cut)
            + f", and {listing(label[m] for m in resent)} were sent again at the cap of "
            f"{C.output_cap(resent[0]):,} in `{_rel(CAP8000)}`.")
    for path, rows in ((STAGE_B, t["b_rows"]), (CAP8000, t["k_rows"])):
        for m in C.CONFIRMATORY:
            errors = [r for r in rows if r["model"] == m and r["outcome"] == "transport_error"]
            if not errors:
                continue
            if all("404" in (r.get("detail") or "")
                   and "Paid model training" in (r.get("detail") or "") for r in errors):
                lines.append(f"The {words(len(errors))} transport errors of {label[m]} in "
                             f"`{_rel(path)}` are answers with status 404 from OpenRouter, "
                             "because the privacy setting of the OpenRouter account excluded "
                             "every paid endpoint which may train on the request, the pinned "
                             f"endpoint of {label[m]} included.")
            else:
                lines.append(f"`{_rel(path)}` holds {words(len(errors))} transport errors of "
                             f"{label[m]}, and the ledger keeps the message of every error.")
    md += [
        "## 3. Parse outcomes (section 7.2.3)\n",
        "`scoring/parse.py` gives every answer an outcome out of six, namely "
        f"{listing(f'`{o}`' for o in OUTCOMES)}. A call means one planned score, and an attempt "
        "means one request sent for the call, so a call sent again after a failure holds two "
        "attempts or more. The rate below is the share, in per cent, of the calls of a model "
        "whose first answered attempt fell under an outcome. The first answered attempt is "
        "counted because a later attempt exists only where an earlier attempt failed, so "
        "counting later attempts would understate failure. An attempt OpenRouter never "
        "answered is counted apart as a transport error. The table also gives the share of "
        "first answers which ended at the output cap.\n",
        table(["Ledger", "Model", "Output cap", "Calls answered", *[f"`{o}`" for o in OUTCOMES],
               "Ended at the cap", "Transport error attempts", "Scores used"],
              [[f"`{r['ledger']}`", r["model"], _cap(r["output_cap"]), r["cells_answered"],
                *[pct(r[f"first_{o}"], r["cells_answered"]) for o in OUTCOMES],
                pct(r["first_stop_length"], r["cells_answered"]), r["transport_error_attempts"],
                r["scores_used"]] for r in parse]),
        " ".join(lines) + "\n",
    ]

    # Measure 7.2.4
    spread, values, cells = t["spread"], t["values"], t["cells"]
    unsent = [m for m in C.CONFIRMATORY if not C.MODELS[m].takes_temperature]
    sent = [m for m in C.CONFIRMATORY if C.MODELS[m].takes_temperature]
    cold = {r["model"]: r for r in spread if r["stage"] == "B" and r["temperature"] == 0.0}
    warm = {r["model"]: r for r in spread if r["stage"] == "B" and r["temperature"] == 1.0}
    steady = [f"{m} at temperature {r['temperature']:g}" for rows in (cold, warm)
              for m, r in rows.items() if r["identical_cells"] == r["cells"]]

    def most_equal(rows: dict) -> str:
        top = max(r["identical_cells"] for r in rows.values())
        return (f"{words(top)} of {words(n_cells)}, for "
                + listing(m for m, r in rows.items() if r["identical_cells"] == top))

    def sds(models: list[str], rows: dict) -> str:
        return listing(f"{rows[label[m]]['mean_within_cell_sd']:.2f}" for m in models)

    lines = [
        (f"{listing(steady)} gave {words(calls)} equal calls in every cell." if steady else
         f"No model of Stage B gave {words(calls)} equal calls in every cell at either "
         "temperature."),
        f"The largest count of cells with {words(calls)} equal calls was {most_equal(cold)} "
        f"at temperature zero, and {most_equal(warm)} at temperature one.",
        f"For {listing(label[m] for m in sent)}, the {words(len(sent))} models which take a "
        f"temperature, the mean SD was {sds(sent, cold)} points at temperature zero and "
        f"{sds(sent, warm)} points at temperature one, in the same order of models.",
        f"For {listing(label[m] for m in unsent)}, whose two runs share the default of the "
        f"developer, the mean SD was {sds(unsent, cold)} points in the run labelled temperature "
        f"zero and {sds(unsent, warm)} points in the run labelled temperature one, in the same "
        "order of models.",
    ]
    heavy = [r for r in values if r["stage"] == "B" and r["temperature"] == 1.0
             and r["anchor_scores"] * 2 > r["calls"]]
    anchored = []
    if heavy:
        anchored.append(
            "At temperature one, more than half the calls returned an anchor score for "
            + listing(f"{r['model']} under {CONDITION_PROSE[r['condition']]} "
                      f"({words(r['anchor_scores'])} of {words(r['calls'])})" for r in heavy)
            + ".")
    for m in C.CONFIRMATORY:
        for condition in C.CONDITIONS:
            mine = [r for r in used if r["model"] == m and r["condition"] == condition]
            scores = {float(r["value"]["score"]) for r in mine}
            if not scores <= set(ANCHORS):
                continue
            sentence = (f"Every call of {label[m]} under {CONDITION_PROSE[condition]}, at both "
                        "temperatures, returned "
                        + listing((f"{s:g}" for s in sorted(scores)), last="or") + ".")
            by_score: dict[float, list[str]] = {}
            for iso in COUNTRIES:
                got = {float(r["value"]["score"]) for r in mine if r["iso3"] == iso}
                if len(got) == 1:
                    by_score.setdefault(got.pop(), []).append(NAMES[iso])
            if sum(len(v) for v in by_score.values()) == len(COUNTRIES):
                sentence += (" " + ", and ".join(
                    f"{listing(names)} received {s:g} in every call"
                    for s, names in sorted(by_score.items(), reverse=True)) + ".")
            anchored.append(sentence)
    wide = sorted((c for c in cells if c["stage"] == "B" and c["temperature"] == 1.0),
                  key=lambda c: -c["sd"])[:5]
    md += [
        "## 4. Replicates at temperature zero and at temperature one (section 7.2.4)\n",
        f"Every model scored the {words(len(COUNTRIES))} countries under the "
        f"{words(len(C.CONDITIONS))} conditions {words(calls)} times at temperature zero and "
        f"{words(calls)} times at temperature one, so a model holds {words(n_cells)} cells at "
        f"a temperature. The table counts the cells whose {words(calls)} calls gave the same "
        f"score and the distinct scores among the {words(n_cells * calls)} calls, and gives the "
        f"standard deviation (SD) of the {words(calls)} calls of a cell, in points of the "
        f"score, as a mean over the {words(n_cells)} cells and at the largest. "
        f"{listing(label[m] for m in unsent)} take no temperature at the endpoints the harness "
        f"pins, so every call of the {words(len(unsent))} models ran at the default of the "
        f"developer, and the two rows of the {words(len(unsent))} models compare two runs at "
        f"the same setting. {label[PILOT_MODEL]}, the pilot model of Stage A, is shown for "
        "comparison.\n",
        table(["Stage", "Model", "Temperature", "Temperature sent",
               f"Cells with {words(calls)} equal calls", "Distinct scores", "Mean SD",
               "Largest SD"],
              [[r["stage"], r["model"], f"{r['temperature']:g}",
                "yes" if r["temperature_applied"] else "no", r["identical_cells"],
                r["distinct_scores"], num(r["mean_within_cell_sd"], 2),
                num(r["largest_within_cell_sd"], 2)] for r in spread]),
        " ".join(lines) + "\n",
        "The holistic wording anchors the scale at 0, 50 and 100, and asks for a decimal part "
        "wherever a whole number would hide a difference between two countries. The table "
        "below counts, for every model, condition and temperature, the distinct scores among "
        f"the {words(len(COUNTRIES) * calls)} calls and the calls which returned 0, 50 or 100 "
        "exactly.\n",
        table(["Stage", "Model", "Condition", "Temperature", "Calls", "Distinct scores",
               "Calls at 0, 50 or 100", "Lowest", "Highest"],
              [[r["stage"], r["model"], CONDITION_NAMES[r["condition"]],
                f"{r['temperature']:g}", r["calls"], r["distinct_scores"], r["anchor_scores"],
                f"{r['lowest']:g}", f"{r['highest']:g}"] for r in values]),
        " ".join(anchored) + "\n" if anchored else "",
        f"The table below gives the {words(len(wide))} cells of Stage B with the largest SD at "
        f"temperature one, with the {words(calls)} scores of every cell.\n",
        table(["Model", "Country", "Condition", f"Scores of the {words(calls)} calls", "SD"],
              [[c["model"], NAMES[c["country"]], CONDITION_NAMES[c["condition"]],
                c["scores"].replace(" ", ", "), num(c["sd"], 2)] for c in wide]),
        "Figure 1 shows every score of Stage B at temperature one, by country and model, "
        "under the two conditions. Figure 2 compares the SD of every cell of Stage B at "
        "temperature zero with the SD of the same cell at temperature one, and a cell above "
        "the dashed line varied more at temperature one.\n",
        "![Figure 1. Scores at temperature one by country and model](fig1_scores.png)\n",
        "![Figure 2. SD of the calls of every cell at temperature zero and at temperature one]"
        "(fig2_replicate_spread.png)\n",
    ]

    # Measure 7.2.5
    studies = g["studies"]
    df_pm, df_p = studies["training"].df["pm"], studies["training"].df["p"]
    order = list(dict.fromkeys(LABELS.values()))
    comp = {(r["design"], r["component"]): r for r in g["components"]}
    zeroed = [f"{LABELS[k]} under {CONDITION_PROSE[d]}"
              for d, gs in studies.items() for k in gs.negatives]
    ds = {(r["design"], r["models"], r["calls"]): r["erho2"] for r in g["d_study"]}
    rel = g["reliability"]
    loo = g["leave_one_out"]
    six, one = "erho2_six_models_five_calls", "erho2_one_model_five_calls"
    ranges = []
    for d in DESIGNS:
        base = next(r for r in loo if r["design"] == d and r["model_left_out"] == "none")
        mine = [r for r in loo if r["design"] == d and r["model_left_out"] != "none"]
        lo, hi = min(mine, key=lambda r: r[six]), max(mine, key=lambda r: r[six])
        ranges.append(f"Under {CONDITION_PROSE[d]}, Eρ² at {words(n_models)} models ran from "
                      f"{lo[six]:.3f}, with {lo['model_left_out']} removed, to {hi[six]:.3f}, "
                      f"with {hi['model_left_out']} removed, against {base[six]:.3f} with no "
                      "model removed.")
    md += [
        "## 5. Generalisability coefficient on pilot data alone (section 7.2.5)\n",
        f"Every figure in this section is a pilot figure on {words(len(COUNTRIES))} countries, "
        "and no confirmatory analysis uses any of the figures. The section uses the calls at "
        "temperature one alone, the temperature of Stage C.\n",
        "A generalisability study splits the variance of the scores into variance components. "
        "A facet is a source of variation the design names, here the model, the call and the "
        "condition, and the design gives a component to the country, to every facet and to "
        "every combination of factors. The country is the object of measurement, so variance "
        f"between countries is the signal. The model is a random facet, because the "
        f"{words(n_models)} models stand in for any models, and the call is a random facet as "
        "well. A component which combines the country with the model or with the call changes "
        "the order of countries from one model or call to the next, and counts as error. The "
        f"condition is a fixed facet, because the study names {words(len(C.CONDITIONS))} "
        "conditions and asks about no other condition, so the component of the country by "
        "condition counts as signal. Three designs are estimated, the training condition alone "
        "and the record condition alone as countries by models, and the two conditions "
        "together as countries by models by fixed conditions, with the calls within cells in "
        "every design.\n",
        "The generalisability coefficient, Eρ², is the share of the variance of averaged "
        "country scores which comes from differences between countries, when the scores are "
        "used to order countries. The dependability coefficient, Φ, is the same share when an "
        "averaged score places a country on the scale itself, so the components which shift "
        "every country alike, the main effect of the model and, in the design with two "
        "conditions, the model by condition, count as error as well, and Φ is never above "
        f"Eρ². A coefficient is reported at three settings, {words(n_models)} models with "
        f"{words(calls)} calls per cell, the size of the data, one model with {words(calls)} "
        "calls per cell, and one model with one call, the size of a single score.\n",
        f"The 95 per cent interval is exact, from the F distribution on {words(df_pm)} and "
        f"{words(df_p)} degrees of freedom, and the Spearman-Brown formula converts the "
        f"interval from {words(n_models)} models to one model. No exact interval exists when "
        "the number of calls changes, and Φ has no interval. "
        f"{words(len(COUNTRIES)).capitalize()} countries give {words(df_p)} degrees of freedom "
        "between countries, so every interval is wide.\n",
        "The table below gives every variance component in squared points of the score, with "
        "the share of the total variance of the design, and Figure 3 shows the shares. "
        + ("No estimate was negative, so no component was set to zero.\n" if not zeroed else
           f"The estimate of {listing(zeroed)} was negative and was set to zero.\n"),
        table(["Component", *[f"{_design(d)}, {x}" for d in DESIGNS
                              for x in ("variance", "share")]],
              [[name, *[v for d in DESIGNS for v in
                        ([num(comp[(d, name)]["variance"], 2), num(comp[(d, name)]["share"], 3)]
                         if (d, name) in comp else ["not in design", ""])]]
               for name in order]),
        "![Figure 3. Share of score variance by component in the three designs]"
        "(fig3_variance_shares.png)\n",
        "The table below gives the coefficients of the three designs at the three settings.\n",
        table(["Design", "Setting", "Eρ²", "95 per cent interval", "Φ"],
              [[_design(r["design"]), r["setting"], num(r["erho2"], 3),
                _interval(r["lower_95"], r["upper_95"]) or "none", num(r["phi"], 3)]
               for r in g["coefficients"]]),
        quote,
        "The decision study projects Eρ² to other numbers of models and of calls per cell, "
        "with the condition held at the two conditions of the data in the third design. The "
        f"table gives one call and {words(calls)} calls per cell, `d_study.csv` holds "
        f"{listing((words(c) for c in CALL_SIZES))} calls, and Figure 4 plots every number of "
        f"calls. The dashed line at {REFERENCE:.2f} in Figure 4 marks a conventional reference "
        "alone and no target of the study, because item one of section 6.2 of PLAN.md has "
        "still to name the target of the decision study.\n",
        table(["Models", *[f"{_design(d)}, {words(c)} call{'s' if c > 1 else ''}"
                           for d in DESIGNS for c in (1, calls)]],
              [[n, *[num(ds[(d, n, c)], 3) for d in DESIGNS for c in (1, calls)]]
               for n in MODEL_SIZES]),
        quote,
        "![Figure 4. Projected generalisability coefficient by models averaged and calls per "
        "cell](fig4_decision_study.png)\n",
        "The reliability of one model as a measure of countries comes from a design of "
        f"countries with {words(calls)} calls per country, for every model under every "
        f"condition. The coefficient of the mean of {words(calls)} calls is one minus the ratio "
        "of the mean square between the calls of a country to the mean square between "
        "countries, with an exact interval from the F distribution on "
        f"{words(rel[0]['df_within_cell'])} and {words(rel[0]['df_country'])} degrees of "
        "freedom, and the Spearman-Brown formula converts the coefficient and the interval to "
        f"one call. {label[PILOT_MODEL]}, the pilot model of Stage A, is shown for "
        "comparison.\n",
        table(["Stage", "Model", "Condition", f"Mean of {words(calls)} calls",
               "95 per cent interval", "One call", "95 per cent interval"],
              [[r["stage"], r["model"], CONDITION_NAMES[r["condition"]],
                num(r["reliability_mean_of_five_calls"], 3),
                _interval(r["lower_95"], r["upper_95"]) or r["note"],
                num(r["reliability_one_call"], 3),
                _interval(r["one_call_lower_95"], r["one_call_upper_95"]) or "none"]
               for r in rel]),
        quote,
        "Every model was removed in turn, the components were estimated again from the "
        f"{words(n_models - 1)} models which remain, and Eρ² was projected to "
        f"{words(n_models)} models and to one model with {words(calls)} calls per cell, so a "
        "row reads against the row with no model removed. " + " ".join(ranges) + "\n",
        table(["Design", "Model removed", f"Eρ², {words(n_models)} models", "Eρ², one model",
               "Components set to zero"],
              [[_design(r["design"]), r["model_left_out"], num(r[six], 3), num(r[one], 3),
                r["set_to_zero"] or "none"] for r in loo]),
        quote,
    ]
    return "\n".join(part for part in md if part)


# --- main --------------------------------------------------------------------


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    b_rows, k_rows = read_rows(STAGE_B), read_rows(CAP8000)
    source, used = score_rows(b_rows, k_rows)
    pilot = pilot_rows()

    cost, projection = cost_tables(used, source)
    write_csv("cost_per_call.csv", cost)
    write_csv("stage_c_projection.csv", projection)
    parse = parse_table(b_rows, k_rows, source)
    write_csv("parse_outcomes.csv", parse)
    spread, cells = spread_tables(used, pilot)
    write_csv("replicate_spread.csv", spread)
    write_csv("cells.csv", cells)
    values = value_table(used, pilot)
    write_csv("score_values.csv", values)

    x = array(used, 1.0, C.CONFIRMATORY)
    pilot_x = array(pilot, 1.0, (PILOT_MODEL,))
    g = g_tables(x, pilot_x)
    write_csv("g_components.csv", g["components"])
    write_csv("g_coefficients.csv", g["coefficients"])
    write_csv("d_study.csv", g["d_study"])
    write_csv("model_reliability.csv", g["reliability"])
    write_csv("leave_one_model_out.csv", g["leave_one_out"])
    figures(x, g, cells)
    (OUT / "summary.md").write_text(summary({
        "source": source, "used": used, "b_rows": b_rows, "k_rows": k_rows, "cost": cost,
        "projection": projection, "parse": parse, "spread": spread, "values": values,
        "cells": cells, "g": g}))
    # README.md in the folder is written by hand, so the count excludes the README
    wrote = [f for f in OUT.iterdir() if f.name != "README.md" and not f.name.startswith(".")]
    print(f"wrote {len(wrote)} files to {OUT.relative_to(C.PROJECT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
