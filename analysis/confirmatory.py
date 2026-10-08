"""
The confirmatory analysis of Stage C, which answers the three research questions of section 1
of PLAN.md.

    python -m analysis.confirmatory                    reads runs/stage_c_training.jsonl and
                                                       runs/stage_c_record.jsonl, writes into
                                                       results/confirmatory
    python -m analysis.confirmatory --ledgers A B --out DIR [--stub]
    python -m analysis.confirmatory --reproduce-audit  reruns stages two and three of the audit
    python -m analysis.confirmatory --self-test        plants known answers in synthetic ledgers

The analysis reads ledgers and the deposited files of the AI Moral Status Audit and calls no
provider. A ledger holding the training condition alone is analysed as the training condition
alone, so the analysis runs before the record condition is sent.

PROPOSED RULES
--------------
Section 6.2 of PLAN.md is OPEN. Every rule section 6.2 will fix is written below as a named
constant or a named function marked PROPOSED, so freezing PLAN.md with a different rule means
changing one line, and the self-test states what every rule returns on planted data.

WHAT IS COMPARED WITH WHAT
--------------------------
The score of a model for a country is the mean of the calls of the model that returned a score
for the country. The panel score of a country is the mean of the model scores over the models
that returned a score, and the number of models behind every panel score is written beside the
panel score, following the rule the audit applies to a country missing a block of the count.
The count is the count of national action from the audit, rebuilt with the 18 strategy records
corrected under policy "entailed" of scoring/corrections.py, in all 20 constructions.

Research question one, on stability, is answered from the generalisability study of every
condition, on the countries holding all 30 scores of the condition (six models by five calls),
and every country left out is named in g_dropped.csv. A refusal is a substantive outcome for
research question one and is reported as a rate for every model and condition, and a refusal
is a missing score everywhere else.

Research question two, on English-language visibility, regresses the gap between the
percentile of the panel score and the percentile of the count on the log of English-language
visibility, with AI patents and high income as controls and standard errors robust to unequal
variance (HC3), under the training condition and the headline count. The answer has to hold
under English Wikipedia and under OpenAlex alike.

Research question three, on capability, tests by Williams's test whether the panel score
follows AI patents and private AI investment more closely than the count does, with a
bootstrap interval over countries for the difference between the two rank correlations.

Every estimate behind an answer is repeated under the 19 other constructions of the count,
under every model alone with a Holm correction across the six models, and under the record
condition as the contrast.

REPRODUCING THE AUDIT
---------------------
The option --reproduce-audit puts the score of the Sentience Readiness Index (sri_overall,
Rost 2026) in place of the panel score and the deposited count in place of the corrected
count, on the 30 countries holding both, and checks every number of stage three in
AIMSA_results.txt and in table_visibility_dependent_correlations.csv that involves no random
draw. A failed check stops the analysis, because functions unable to reproduce the published
audit cannot be trusted on Stage C.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests

from scoring import config as C
from scoring import corrections as K
from scoring import instruments as I
from scoring.parse import OUTCOMES
from scoring.run import RETRYABLE

from .gstudy import coefficients, d_study, estimate
from .pilot import (LABELS, LIMITATION, MODEL_SIZES, CALL_SIZES, SETTINGS, coefficient_rows,
                    latest, n_prime, one_way, read_rows)

OUT = C.PROJECT / "results" / "confirmatory"
LEDGERS = (C.RUNS / "stage_c_training.jsonl", C.RUNS / "stage_c_record.jsonl")
AUDIT_RESULTS = C.AUDIT / "results" / "AIMSA_results.txt"
AUDIT_DEPENDENT = C.AUDIT / "results" / "table_visibility_dependent_correlations.csv"
TEMPERATURE = 1.0
FINAL = (*OUTCOMES, "transport_error")
# An answer that ended normally. OpenRouter reports the finish reason stop, and the stub
# provider and the Anthropic API report end_turn. PROPOSED. A score parsed from a complete JSON
# object counts whatever the stop reason, and outcomes.csv counts the scores without a normal end.
NORMAL_END = ("stop", "end_turn")
SEED = 20260820             # the seed of 11_analysis.py in the audit
BOOT = 10_000

# PROPOSED for section 6.2 of PLAN.md, which is OPEN.
PRIMARY = "training"        # the condition of the practice behind the SRI, no record supplied
ALPHA = 0.05
TARGET = 0.80               # research question one, one model and one call
NEGLIGIBLE_BETA = 0.3       # research question two, a standardised slope within 0.3 of zero
NEGLIGIBLE_RHO = 0.1        # research question three, a difference in rank correlation below 0.1
VISIBILITY = ("log_wiki", "log_openalex")
CAPABILITY = ("log_patents", "log_investment")
CONTROLS = ("log_patents", "high_income")

# The columns and transformations of load() in 11_analysis.py of the audit.
LOGS = {"log_wiki": "vis_wikipedia", "log_openalex": "vis_openalex",
        "log_patents": "cap_patents_total_2010_2024", "log_investment": "cap_investment_usd_bn",
        "log_compute": "cap_compute_stock_h100"}
MINIMUM_PAIRS = 10          # the audit skips a capability measure held by fewer countries
CAPABILITY_LABELS = {"AI patents": "log_patents", "private investment": "log_investment",
                     "compute stock": "log_compute"}
VISIBILITY_LABELS = {"English Wikipedia": "log_wiki", "OpenAlex": "log_openalex"}


# --- reading and checking ----------------------------------------------------


def read(paths) -> tuple[list[dict], Counter]:
    """The last row written for every cell over the ledgers, and the attempts of every cell."""
    rows = [r for path in paths for r in read_rows(Path(path))]
    return list(latest(rows).values()), Counter(r["cell"] for r in rows)


def check(rows: list[dict], attempts: Counter, countries: list[str],
          stub: bool = False) -> list[str]:
    """Stop the analysis on any row Stage C could not have written, and return the conditions.

    Every row is checked against the route, role, wording, wording version, record version,
    correction policy and temperature of Stage C, and every scored row is checked to hold a
    score from 0 to 100. A cell ending in an outcome worth
    sending again (transport_error or empty) must have been sent twice, so a run left
    unfinished is never analysed as a run with missing scores. Every model must hold every
    country, condition and call of the conditions present exactly once.
    """
    problems = []
    for r in rows:
        spec = C.MODELS.get(r.get("model"))
        if spec is None:
            problems.append(f"{r.get('cell')} model {r.get('model')}")
            continue
        score = (r.get("value") or {}).get("score")
        scored = r.get("outcome") == "ok"
        wrong = [
            f"outcome {r.get('outcome')}" if r.get("outcome") not in FINAL else "",
            f"route {r.get('route')}" if r.get("route") != spec.route else "",
            f"role {r.get('role')}" if r.get("role") != "confirmatory" else "",
            f"instrument {r.get('instrument')}" if r.get("instrument") != "holistic" else "",
            (f"instrument version {r.get('instrument_version')}"
             if r.get("instrument_version") != I.VERSION else ""),
            (f"record version {r.get('record_version')}"
             if r.get("record_version") != C.RECORD_VERSION else ""),
            (f"correction policy {r.get('correction_policy')}"
             if r.get("correction_policy") != C.CORRECTION_POLICY else ""),
            f"stub {r.get('stub')}" if bool(r.get("stub")) != stub else "",
            (f"temperature {r.get('temperature')}"
             if float(r.get("temperature", -1)) != TEMPERATURE else ""),
            (f"temperature applied {r.get('temperature_applied')}"
             if r.get("temperature_applied") is not spec.takes_temperature else ""),
            (f"score {score!r}" if scored and (not isinstance(score, (int, float))
                                               or isinstance(score, bool)
                                               or not 0 <= score <= 100) else ""),
            (f"{r.get('outcome')} after one attempt"
             if r.get("outcome") in RETRYABLE and attempts[r.get("cell")] < 2 else ""),
        ]
        problems += [f"{r.get('cell')} {w}" for w in wrong if w]
    conditions = [c for c in C.CONDITIONS if any(r.get("condition") == c for r in rows)]
    grid = Counter((r.get("model"), r.get("iso3"), r.get("condition"), r.get("replicate"))
                   for r in rows)
    want = {(m, i, c, k) for m in C.CONFIRMATORY for i in countries for c in conditions
            for k in range(1, C.REPLICATES + 1)}
    if set(grid) != want or any(n != 1 for n in grid.values()):
        problems.append(f"the ledgers hold {len(set(grid) & want)} of the {len(want)} cells of "
                        f"the grid, {len(set(grid) - want)} cells outside the grid and "
                        f"{sum(n > 1 for n in grid.values())} cells more than once")
    if problems:
        raise SystemExit(f"{len(problems)} problems in the Stage C rows, first "
                         + "; ".join(problems[:5]))
    return conditions


# --- scores ------------------------------------------------------------------


def calls(rows: list[dict]) -> pd.DataFrame:
    """One line for every call that returned a score."""
    return pd.DataFrame([{"model": r["model"], "iso3": r["iso3"], "condition": r["condition"],
                          "replicate": r["replicate"], "score": float(r["value"]["score"])}
                         for r in rows if r["outcome"] == "ok"],
                        columns=["model", "iso3", "condition", "replicate", "score"])


def model_scores(scored: pd.DataFrame) -> pd.DataFrame:
    """The score of a model for a country in a condition, the mean of the scored calls."""
    return (scored.groupby(["model", "iso3", "condition"])["score"]
            .agg(score="mean", sd="std", calls="count").reset_index())


def panel_scores(ms: pd.DataFrame) -> pd.DataFrame:
    """PROPOSED. The panel score of a country, the mean of the model scores held."""
    return (ms.groupby(["iso3", "condition"])["score"]
            .agg(panel="mean", models="count").reset_index())


def outcome_table(rows: list[dict], conditions: list[str]) -> list[dict]:
    """The final outcome of every cell, counted for every model and condition."""
    out = []
    for m in C.CONFIRMATORY:
        for c in conditions:
            mine = [r for r in rows if r["model"] == m and r["condition"] == c]
            n = Counter(r["outcome"] for r in mine)
            held = Counter(r["iso3"] for r in mine if r["outcome"] == "ok")
            countries = {r["iso3"] for r in mine}
            out.append({
                "model": C.MODELS[m].label, "condition": c, "cells": len(mine),
                **{o: n.get(o, 0) for o in FINAL},
                "refusal_share": n.get("refusal", 0) / len(mine),
                "scored_share": n.get("ok", 0) / len(mine),
                "scored_without_a_normal_end": sum(r["outcome"] == "ok"
                                                   and r.get("stop_reason") not in NORMAL_END
                                                   for r in mine),
                "countries_without_a_score": len(countries - set(held)),
                "countries_short_of_five_scores": sum(held.get(i, 0) < C.REPLICATES
                                                      for i in countries),
            })
    return out


def agreement(ms: pd.DataFrame, conditions: list[str]) -> list[dict]:
    """Spearman's rho between the scores of every pair of models, in every condition."""
    out = []
    for c in conditions:
        wide = ms[ms["condition"] == c].pivot(index="iso3", columns="model", values="score")
        for a, b in combinations(C.CONFIRMATORY, 2):
            d = wide.reindex(columns=[a, b]).dropna()
            rho = stats.spearmanr(d[a], d[b]).statistic if len(d) > 2 else np.nan
            low, high = fisher_ci(rho, len(d))
            out.append({"condition": c, "model_a": C.MODELS[a].label,
                        "model_b": C.MODELS[b].label, "countries": len(d), "rho": rho,
                        "fisher_low": low, "fisher_high": high,
                        "tau": stats.kendalltau(d[a], d[b]).statistic if len(d) > 2 else np.nan})
    return out


# --- research question one ---------------------------------------------------


def balanced(scored: pd.DataFrame, countries: list[str], conditions: tuple[str, ...]
             ) -> tuple[np.ndarray, list[str], list[str]]:
    """Scores as country by model by condition by call, on the countries holding every score.

    The estimator of analysis/gstudy.py needs a balanced design, so a country missing any score
    of the conditions asked for is left out of the array and named.
    """
    x = np.full((len(countries), len(C.CONFIRMATORY), len(conditions), C.REPLICATES), np.nan)
    d = scored[scored["condition"].isin(conditions)]
    where = {i: j for j, i in enumerate(countries)}
    x[d["iso3"].map(where).to_numpy(),
      d["model"].map({m: j for j, m in enumerate(C.CONFIRMATORY)}).to_numpy(),
      d["condition"].map({c: j for j, c in enumerate(conditions)}).to_numpy(),
      d["replicate"].to_numpy() - 1] = d["score"].to_numpy()
    keep = ~np.isnan(x).any(axis=(1, 2, 3))
    return (x[keep], [i for i, k in zip(countries, keep) if k],
            [i for i, k in zip(countries, keep) if not k])


def boot_coefficients(data: np.ndarray, facets: str, fixed: tuple[str, ...], design: str,
                      rng: np.random.Generator, reps: int = BOOT) -> dict[str, tuple]:
    """Percentile intervals over countries for the coefficient of every setting of SETTINGS.

    Countries are drawn with replacement and every component is estimated again, so the
    interval exists for one call per cell, where no exact interval exists.
    """
    n = data.shape[0]
    held = {label: np.empty(reps) for label, _, _ in SETTINGS}
    for b in range(reps):
        gs = estimate(data[rng.integers(0, n, n)], facets)
        for label, models, calls_ in SETTINGS:
            held[label][b] = coefficients(gs, n_prime(design, models, calls_),
                                          fixed=fixed)["Erho2"]
    return {label: tuple(np.nanpercentile(v, [2.5, 97.5])) for label, v in held.items()}


def g_tables(scored: pd.DataFrame, countries: list[str], conditions: list[str],
             rng: np.random.Generator, reps: int = BOOT) -> dict[str, list[dict]]:
    out = {k: [] for k in ("components", "coefficients", "d_study", "leave_one_out",
                           "dropped", "reliability")}
    designs = [(c, (c,), "pm", ()) for c in conditions]
    if len(conditions) == len(C.CONDITIONS):
        designs.append(("both", tuple(conditions), "pmc", ("c",)))
    for design, conds, facets, fixed in designs:
        x, kept, dropped = balanced(scored, countries, conds)
        data = x[:, :, 0, :] if facets == "pm" else x
        out["dropped"] += [{"design": design, "iso3": i} for i in dropped]
        gs = estimate(data, facets)
        shares = gs.shares()
        for key in gs.components:
            out["components"].append({
                "design": design, "countries": len(kept), "component": LABELS[key],
                "key": key, "variance": gs.components[key], "untruncated": gs.untruncated[key],
                "share": shares[key], "ms": gs.ms[key], "df": gs.df[key],
                "set_to_zero": "yes" if key in gs.negatives else "no"})
        boot = boot_coefficients(data, facets, fixed, design, rng, reps)
        for row in coefficient_rows(design, gs, fixed):
            row["countries"] = len(kept)
            row["boot_lower_95"], row["boot_upper_95"] = boot[row["setting"]]
            out["coefficients"].append(row)
        for row in d_study(gs, {k: (MODEL_SIZES if k == "m" else CALL_SIZES if k == "r"
                                    else [len(C.CONDITIONS)])
                                for k in n_prime(design, 1, 1)}, fixed=fixed):
            out["d_study"].append({"design": design, "models": row["n_prime"]["m"],
                                   "calls": row["n_prime"]["r"], "erho2": row["Erho2"],
                                   "phi": row["Phi"]})
        for drop in C.CONFIRMATORY:
            keep = [j for j, m in enumerate(C.CONFIRMATORY) if m != drop]
            part = estimate(data[:, keep], facets)
            out["leave_one_out"].append({
                "design": design, "model_left_out": C.MODELS[drop].label,
                **{f"erho2_{label.replace(', ', '_').replace(' ', '_')}": coefficients(
                    part, n_prime(design, models, calls_), fixed=fixed)["Erho2"]
                   for label, models, calls_ in SETTINGS},
                "set_to_zero": " ".join(LABELS[k] for k in part.negatives)})
    for j, m in enumerate(C.CONFIRMATORY):
        for c in conditions:
            d = scored[(scored["model"] == m) & (scored["condition"] == c)]
            x = np.full((len(countries), C.REPLICATES), np.nan)
            x[d["iso3"].map({i: k for k, i in enumerate(countries)}).to_numpy(),
              d["replicate"].to_numpy() - 1] = d["score"].to_numpy()
            x = x[~np.isnan(x).any(axis=1)]
            out["reliability"].append({"model": C.MODELS[m].label, "condition": c,
                                       "countries": len(x), **one_way(x)})
    return out


def rq1_answer(coefficient_table: list[dict], d_table: list[dict]) -> dict:
    """PROPOSED. One model and one call under the training condition, the practice of the SRI.

    Reliable where the lower bound of the bootstrap interval reaches TARGET, unreliable where
    the upper bound falls short of TARGET, and not settled otherwise. The smallest design
    reaching TARGET is reported beside the answer.
    """
    row = next(r for r in coefficient_table
               if r["design"] == PRIMARY and r["setting"] == "one model, one call")
    lo, hi = row["boot_lower_95"], row["boot_upper_95"]
    answer = "reliable" if lo >= TARGET else "unreliable" if hi < TARGET else "not settled"
    reach = sorted((r["models"] * r["calls"], r["models"], r["calls"]) for r in d_table
                   if r["design"] == PRIMARY and r["erho2"] >= TARGET)
    return {"question": "RQ1", "condition": PRIMARY, "answer": answer,
            "estimate": row["erho2"], "lower_95": lo, "upper_95": hi,
            "smallest_design_reaching_target": (f"{reach[0][1]} models by {reach[0][2]} calls"
                                                if reach else "none in the grid"),
            "note": LIMITATION}


# --- research questions two and three ----------------------------------------


def region_group(r):
    """The four groups of region_group() in 11_analysis.py of the audit."""
    if pd.isna(r):
        return "Other"
    for start, name in (("Europe", "Europe & Central Asia"), ("East Asia", "East Asia & Pacific"),
                        ("North America", "North America")):
        if r.startswith(start):
            return name
    return "Other"


def countries_frame(policy: str = K.DEFAULT_POLICY) -> pd.DataFrame:
    """The 122 countries as load() in 11_analysis.py of the audit builds them.

    The 20 constructions of the count, rebuilt under the correction policy, are added as
    columns named count_ and the construction, and the deposited count stays as action_score.
    """
    idx = pd.read_csv(C.AUDIT_INDEX, dtype={"ISO3": str})
    wide = pd.read_csv(C.AUDIT_WIDE, dtype={"ISO3": str}, low_memory=False)
    df = idx.merge(wide[["ISO3", "sri_overall", *LOGS.values()]], on="ISO3", how="left")
    df["region_group"] = df["Region"].map(region_group)
    for name, column in LOGS.items():
        df[name] = np.log10(df[column] + 1)
    df["high_income"] = (df["Income_Group"] == "High income").astype(float)
    variants = K.corrected_variants(policy).add_prefix("count_")
    return df.merge(variants, left_on="ISO3", right_index=True, how="left").set_index("ISO3")


def pct_rank(s: pd.Series) -> pd.Series:
    """Percentile position within the sample, 0 lowest and 100 highest, as in the audit."""
    return 100 * (s.rank(method="average") - 1) / (s.notna().sum() - 1)


def with_gap(frame: pd.DataFrame, score: str, count: str) -> pd.DataFrame:
    """The countries holding a score and a count, with the gap between the two percentiles."""
    both = frame[frame[score].notna() & frame[count].notna()].copy()
    both["gap"] = pct_rank(both[score]) - pct_rank(both[count])
    return both


def ols(frame: pd.DataFrame, y: str, xs: list[str]) -> list[dict]:
    """Least squares with HC3 standard errors, one line for every predictor, as in the audit."""
    d = frame[[y, *xs]].dropna()
    m = sm.OLS(d[y].astype(float), sm.add_constant(d[xs].astype(float))).fit(cov_type="HC3")
    ci = m.conf_int()
    out = []
    for k in xs:
        ratio = d[k].std() / d[y].std()
        out.append({"term": k, "n": int(m.nobs), "adj_r2": m.rsquared_adj, "b": m.params[k],
                    "lower_95": ci.loc[k, 0], "upper_95": ci.loc[k, 1],
                    "beta": m.params[k] * ratio, "beta_lower_95": ci.loc[k, 0] * ratio,
                    "beta_upper_95": ci.loc[k, 1] * ratio, "p": m.pvalues[k]})
    return out


def region_ols(both: pd.DataFrame, shared: str) -> list[dict]:
    """The regression of the audit with region, three indicators against Europe."""
    d = both.dropna(subset=["gap", shared, "log_patents"]).copy()
    dummies = pd.get_dummies(d["region_group"], prefix="reg", drop_first=False)
    dummies = dummies.drop(columns=[c for c in dummies.columns if "Europe" in c])
    d = pd.concat([d, dummies.astype(float)], axis=1)
    return ols(d, "gap", [shared, "log_patents", *dummies.columns])


def partial_rho(both: pd.DataFrame, shared: str, control: str = "log_patents") -> dict:
    """Spearman's rho between a measure and the gap, with the ranks of the control taken out."""
    d = both[[shared, "gap", control]].dropna()
    z = sm.add_constant(d[control].rank())
    r = stats.spearmanr(sm.OLS(d[shared].rank(), z).fit().resid,
                        sm.OLS(d["gap"].rank(), z).fit().resid)
    return {"measure": shared, "n": len(d), "partial_rho": r.statistic, "p": r.pvalue}


def williams(r_jk, r_jh, r_kh, n):
    """Williams's test that two correlations sharing variable j differ, as in the audit."""
    r_bar = (r_jk + r_jh) / 2
    det = (1 - r_jk ** 2 - r_jh ** 2 - r_kh ** 2) + 2 * r_jk * r_jh * r_kh
    num = (r_jk - r_jh) * np.sqrt((n - 1) * (1 + r_kh))
    den = np.sqrt(2 * (n - 1) / (n - 3) * det + r_bar ** 2 * (1 - r_kh) ** 3)
    t = num / den
    return t, 2 * stats.t.sf(abs(t), n - 3)


def fisher_ci(rho, n, alpha=0.05):
    """Fisher z interval for Spearman's rho with the standard error of Bonett and Wright, as in
    the audit."""
    if n < 5:
        return np.nan, np.nan
    z, se = np.arctanh(rho), 1.06 / np.sqrt(n - 3)
    q = stats.norm.ppf(1 - alpha / 2)
    return np.tanh(z - q * se), np.tanh(z + q * se)


def _rowwise_r(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a - a.mean(axis=1, keepdims=True)
    b = b - b.mean(axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (a * b).sum(axis=1) / np.sqrt((a * a).sum(axis=1) * (b * b).sum(axis=1))


def dependent(frame: pd.DataFrame, shared: str, score: str, count: str,
              rng: np.random.Generator | None = None, reps: int = BOOT) -> dict:
    """Whether the score or the count goes with a shared measure more closely.

    Spearman's rho of the shared measure with the score and with the count, with a Fisher
    interval and Kendall's tau beside every rho as section 6.1 requires, Williams's test of the
    difference, and, given a generator, percentile bootstrap intervals over countries for both
    correlations and for the difference. Spearman's rho of a resample is Pearson's r of the average ranks within the
    resample, which is the statistic scipy computes.
    """
    d = frame[[shared, score, count]].dropna()
    n = len(d)
    r_s = stats.spearmanr(d[shared], d[score]).statistic
    r_c = stats.spearmanr(d[shared], d[count]).statistic
    r_sc = stats.spearmanr(d[score], d[count]).statistic
    t, p = williams(r_s, r_c, r_sc, n)
    row = {"measure": shared, "n": n, "rho_score": r_s, "rho_count": r_c,
           "rho_score_count": r_sc, "difference": r_s - r_c, "williams_t": t, "p": p,
           "boot_low": None, "boot_high": None}
    for name, column, r in (("score", score, r_s), ("count", count, r_c)):
        row[f"rho_{name}_fisher_low"], row[f"rho_{name}_fisher_high"] = fisher_ci(r, n)
        tau = stats.kendalltau(d[shared], d[column])
        row[f"tau_{name}"], row[f"tau_{name}_p"] = tau.statistic, tau.pvalue
    if rng is not None:
        ranks = stats.rankdata(d.to_numpy()[rng.integers(0, n, (reps, n))], axis=1)
        with_score = _rowwise_r(ranks[..., 0], ranks[..., 1])
        with_count = _rowwise_r(ranks[..., 0], ranks[..., 2])
        row["boot_low"], row["boot_high"] = np.nanpercentile(with_score - with_count, [2.5, 97.5])
        for name, values in (("score", with_score), ("count", with_count)):
            row[f"rho_{name}_boot_low"], row[f"rho_{name}_boot_high"] = np.nanpercentile(
                values, [2.5, 97.5])
    return row


def rq2(frame: pd.DataFrame, score: str, count: str, rng: np.random.Generator | None,
        reps: int = BOOT) -> dict[str, list[dict]]:
    """The primary regression of the gap for both measures of visibility, and the secondary
    analyses of stage three of the audit."""
    both = with_gap(frame, score, count)
    both["score_percentile"], both["count_percentile"] = pct_rank(both[score]), pct_rank(both[count])
    primary, secondary = [], []
    for vis in VISIBILITY:
        for spec, xs in (("alone", [vis]), ("capability", [vis, "log_patents"]),
                         ("capability and income", [vis, *CONTROLS])):
            for row in ols(both, "gap", xs):
                line = {"measure": vis, "specification": spec, **row}
                (primary if spec == "capability and income" and row["term"] == vis
                 else secondary).append(line)
        secondary += [{"measure": vis, "specification": "capability and region", **row}
                      for row in region_ols(both, vis)]
        secondary.append({"specification": "partial rank correlation, patents held constant",
                          **partial_rho(both, vis)})
        secondary.append({"specification": "Williams's test on visibility",
                          **dependent(both, vis, score, count, rng, reps)})
        # PROPOSED. The percentile of the score regressed on the percentile of the count, so a
        # score agreeing with the count only partly does not move the slope of visibility.
        secondary += [{"measure": vis, "specification": "score on count", **row} for row in
                      ols(both, "score_percentile", ["count_percentile", vis, *CONTROLS])]
    return {"primary": primary, "secondary": secondary}


def rq3(frame: pd.DataFrame, score: str, count: str, rng: np.random.Generator | None,
        reps: int = BOOT) -> list[dict]:
    """Williams's test of capability against the score and the count, for every measure held
    by MINIMUM_PAIRS countries or more. Compute stock is secondary."""
    both = with_gap(frame, score, count)
    out = []
    for cap in (*CAPABILITY, "log_compute"):
        if both[[cap, score, count]].dropna().shape[0] < MINIMUM_PAIRS:
            continue
        out.append({"primary": cap in CAPABILITY, **dependent(both, cap, score, count, rng, reps)})
    return out


# PROPOSED. Printed beside the answer reversed to research question two. In 300 synthetic runs
# where the score agreed with the count at a correlation of 0.5 and visibility had no effect on
# the score, the gap model answered reversed in nine per cent of runs, and the slope of
# visibility in the score-on-count model reached p < 0.05 under both measures in two per cent.
REVERSED_NOTE = ("A score which agrees with the count only partly pulls the slope of visibility "
                 "on the gap below zero even where visibility has no effect on the score, because "
                 "the count rises with visibility. The rows of rq2 marked score on count hold the "
                 "count constant, and the slope of visibility in the rows of rq2 marked score on "
                 "count should be read before the answer reversed is reported.")


def rq2_answer(primary: list[dict], secondary: list[dict]) -> str:
    """PROPOSED. Yes where the slope of visibility in the primary model is positive at ALPHA
    under English Wikipedia and under OpenAlex, reversed where the slope is negative at ALPHA
    under English Wikipedia and under OpenAlex, absent where the 95 per cent interval of the
    standardised slope of visibility alone, on every country holding a score and a count, lies
    within NEGLIGIBLE_BETA of zero under English Wikipedia and under OpenAlex, and not settled
    otherwise. Absent is judged on visibility alone because the primary model loses the 32
    countries without a patent count and, in synthetic runs with no visibility effect, the
    interval of the primary model fell inside NEGLIGIBLE_BETA in one run of 40 under English
    Wikipedia."""
    alone = [r for r in secondary
             if r.get("specification") == "alone" and r.get("term") == r.get("measure")]
    if len(primary) != len(VISIBILITY) or len(alone) != len(VISIBILITY):
        return "not settled"
    if all(r["b"] > 0 and r["p"] < ALPHA for r in primary):
        return "yes"
    if all(r["b"] < 0 and r["p"] < ALPHA for r in primary):
        return "reversed"
    if all(-NEGLIGIBLE_BETA < r["beta_lower_95"] and r["beta_upper_95"] < NEGLIGIBLE_BETA
           for r in alone):
        return "absent"
    return "not settled"


def rq3_answer(rows: list[dict]) -> str:
    """PROPOSED. Yes where the score goes with capability more closely than the count does at
    ALPHA under patents and investment alike, no where the upper bootstrap bound of the
    difference falls below NEGLIGIBLE_RHO under both, and not settled otherwise."""
    primary = [r for r in rows if r["primary"]]
    if len(primary) != len(CAPABILITY):
        return "not settled"
    if all(r["difference"] > 0 and r["p"] < ALPHA for r in primary):
        return "yes"
    if all(r["boot_high"] is not None and r["boot_high"] < NEGLIGIBLE_RHO for r in primary):
        return "no"
    return "not settled"


def construction_rows(frame: pd.DataFrame, score: str) -> list[dict]:
    """The estimate behind every answer, under every one of the 20 constructions of the count."""
    out = []
    for column in [c for c in frame.columns if c.startswith("count_")]:
        both = with_gap(frame, score, column)
        name = column.removeprefix("count_")
        for vis in VISIBILITY:
            row = ols(both, "gap", [vis, *CONTROLS])[0]
            out.append({"construction": name, "question": "RQ2", "measure": vis,
                        "n": row["n"], "estimate": row["b"], "standardised": row["beta"],
                        "p": row["p"]})
        for cap in CAPABILITY:
            row = dependent(both, cap, score, column)
            out.append({"construction": name, "question": "RQ3", "measure": cap,
                        "n": row["n"], "estimate": row["difference"], "standardised": None,
                        "p": row["p"]})
    return out


def construction_ranges(rows: list[dict]) -> list[dict]:
    """The range of every estimate across the 20 constructions, as section 6.1 requires."""
    out = []
    for (question, measure), part in pd.DataFrame(rows).groupby(["question", "measure"],
                                                                sort=False):
        head = part[part["construction"] == "headline"].iloc[0]
        out.append({"question": question, "measure": measure,
                    "constructions": len(part), "headline": head["estimate"],
                    "lowest": part["estimate"].min(), "highest": part["estimate"].max(),
                    "same_sign_as_headline": int((np.sign(part["estimate"])
                                                  == np.sign(head["estimate"])).sum()),
                    "p_below_alpha": int((part["p"] < ALPHA).sum()),
                    "smallest_n": int(part["n"].min())})
    return out


def per_model_rows(frame: pd.DataFrame, ms: pd.DataFrame, condition: str) -> list[dict]:
    """Every model alone in place of the panel, with a Holm correction across the six models."""
    out = []
    for m in C.CONFIRMATORY:
        s = ms[(ms["model"] == m) & (ms["condition"] == condition)].set_index("iso3")["score"]
        f = frame.assign(model_score=s.reindex(frame.index))
        both = with_gap(f, "model_score", "count_headline")
        for vis in VISIBILITY:
            row = ols(both, "gap", [vis, *CONTROLS])[0]
            out.append({"model": C.MODELS[m].label, "question": "RQ2", "measure": vis,
                        "n": row["n"], "estimate": row["b"], "p": row["p"]})
        for cap in CAPABILITY:
            row = dependent(both, cap, "model_score", "count_headline")
            out.append({"model": C.MODELS[m].label, "question": "RQ3", "measure": cap,
                        "n": row["n"], "estimate": row["difference"], "p": row["p"]})
    table = pd.DataFrame(out)
    table["p_holm"] = table.groupby(["question", "measure"])["p"].transform(
        lambda p: multipletests(p, method="holm")[1])
    return table.to_dict("records")


# --- reproducing the audit ---------------------------------------------------


def published() -> dict:
    """Every number of stage three of the audit that involves no random draw.

    Read from AIMSA_results.txt between the heading of stage three and the power analysis, and
    from table_visibility_dependent_correlations.csv, so no number is typed by hand.
    """
    lines = AUDIT_RESULTS.read_text().splitlines()
    start = next(j for j, s in enumerate(lines) if "what the disagreement tracks" in s.lower())
    end = next(j for j, s in enumerate(lines) if j > start and "power at this sample size" in s)
    num = r"(-?\d+\.\d+)"
    out = {"ols": {}, "partial": {}, "capability": {}, "dependent": {}}
    model = None
    for s in lines[start:end]:
        if m := re.match(rf"\s+gap ~ (.+?)\s+n = (\d+)\s+adj R2 =\s*{num}", s):
            model = m.group(1)
            out["ols"][model] = {"n": int(m.group(2)), "adj_r2": float(m.group(3)), "terms": {}}
        elif m := re.match(rf"\s+(\S.*?)\s+b =\s*{num}\s+\[\s*{num},\s*{num}\]\s+beta =\s*{num}"
                           rf"\s+p = {num}", s):
            out["ols"][model]["terms"][m.group(1)] = tuple(float(v) for v in m.groups()[1:])
        elif m := re.match(rf"\s+(log_\w+)\s+partial rho =\s*{num}\s+p = {num}\s+n = (\d+)", s):
            out["partial"][m.group(1)] = (float(m.group(2)), float(m.group(3)), int(m.group(4)))
        elif m := re.match(rf"\s+({'|'.join(CAPABILITY_LABELS)})\s+index rho =\s*{num}\s+"
                           rf"action rho =\s*{num}\s+difference\s+{num}\s+Williams p = {num}"
                           rf"\s+n = (\d+)", s):
            out["capability"][CAPABILITY_LABELS[m.group(1)]] = (
                *(float(v) for v in m.groups()[1:5]), int(m.group(6)))
    for row in pd.read_csv(AUDIT_DEPENDENT).to_dict("records"):
        out["dependent"][VISIBILITY_LABELS[row["text"]]] = row
    return out


def reproduce_audit() -> list[dict]:
    """Every published number of stages two and three against the same number from this module."""
    frame = countries_frame("none")
    rebuilt = float((frame["count_headline"] - frame["action_score"]).abs().max())
    both = with_gap(frame, "sri_overall", "action_score")
    pub = published()
    checks = [{"check": "rebuilt headline count against the deposited count",
               "published": 0.0, "reproduced": rebuilt, "places": 9}]

    def add(label, want, got, places):
        checks.append({"check": label, "published": want, "reproduced": got, "places": places})

    add("countries holding the SRI and the count", 30, len(both), 0)
    stage_two = AUDIT_RESULTS.read_text()
    m = re.search(r"action count against the index\s+n = (\d+)\s+Spearman rho\s+(-?\d+\.\d+)\s+"
                  r"Fisher CI \[\s*(-?\d+\.\d+),\s*(-?\d+\.\d+)\].*?Kendall tau\s+(-?\d+\.\d+)",
                  stage_two, re.S)
    rho = stats.spearmanr(both["sri_overall"], both["action_score"]).statistic
    low, high = fisher_ci(rho, len(both))
    for label, want, got in (("rho", m.group(2), rho), ("Fisher lower", m.group(3), low),
                             ("Fisher upper", m.group(4), high),
                             ("Kendall tau", m.group(5), stats.kendalltau(
                                 both["sri_overall"], both["action_score"]).statistic)):
        add(f"stage two, the SRI against the count, {label}", float(want), got, 3)
    specs = {}
    for vis in VISIBILITY:
        specs[vis] = [vis]
        specs[f"{vis} + capability"] = [vis, "log_patents"]
        specs[f"{vis} + capability + income"] = [vis, *CONTROLS]
    for label, xs in specs.items():
        want = pub["ols"][label]
        rows = ols(both, "gap", xs)
        add(f"gap ~ {label}, n", want["n"], rows[0]["n"], 0)
        add(f"gap ~ {label}, adjusted R2", want["adj_r2"], rows[0]["adj_r2"], 3)
        for row in rows:
            b, lo, hi, beta, p = want["terms"][row["term"]]
            for name, w, g, places in (("b", b, row["b"], 3), ("lower", lo, row["lower_95"], 3),
                                       ("upper", hi, row["upper_95"], 3),
                                       ("beta", beta, row["beta"], 3), ("p", p, row["p"], 4)):
                add(f"gap ~ {label}, {row['term']} {name}", w, g, places)
    want = pub["ols"]["wikipedia + capability + region"]
    for row in region_ols(both, "log_wiki"):
        b, lo, hi, beta, p = want["terms"][row["term"]]
        add(f"gap ~ wikipedia + capability + region, {row['term']} b", b, row["b"], 3)
        add(f"gap ~ wikipedia + capability + region, {row['term']} p", p, row["p"], 4)
    for vis, (rho, p, n) in pub["partial"].items():
        row = partial_rho(both, vis)
        add(f"partial rho, {vis}", rho, row["partial_rho"], 3)
        add(f"partial rho, {vis}, p", p, row["p"], 4)
        add(f"partial rho, {vis}, n", n, row["n"], 0)
    for vis, want in pub["dependent"].items():
        row = dependent(both, vis, "sri_overall", "action_score")
        for name, key, places in (("n", "n", 0), ("rho_index", "rho_score", 3),
                                  ("rho_action", "rho_count", 3), ("difference", "difference", 3),
                                  ("williams_t", "williams_t", 3), ("p", "p", 4)):
            add(f"Williams on visibility, {vis}, {name}", want[name], row[key], places)
    for cap, (r_s, r_a, diff, p, n) in pub["capability"].items():
        row = dependent(both, cap, "sri_overall", "action_score")
        for name, w, g, places in (("index rho", r_s, row["rho_score"], 3),
                                   ("action rho", r_a, row["rho_count"], 3),
                                   ("difference", diff, row["difference"], 3),
                                   ("Williams p", p, row["p"], 4), ("n", n, row["n"], 0)):
            add(f"Williams on capability, {cap}, {name}", w, g, places)
    for c in checks:
        c["match"] = abs(c["reproduced"] - c["published"]) <= 0.5 * 10 ** -c["places"] + 1e-12
    return checks


# --- the analysis ------------------------------------------------------------


def write_csv(out: Path, name: str, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (out / name).open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (round(v, 6) if isinstance(v, float) else v)
                             for k, v in row.items()})


def analyse(rows: list[dict], attempts: Counter, out: Path | None, stub: bool = False,
            frame: pd.DataFrame | None = None, reps: int = BOOT) -> dict:
    """Every table of the three research questions, written into `out` when `out` is given."""
    frame = countries_frame() if frame is None else frame
    countries = sorted(frame.index)
    conditions = check(rows, attempts, countries, stub)
    rng = np.random.default_rng(SEED)
    scored = calls(rows)
    ms = model_scores(scored)
    ps = panel_scores(ms)
    t = {"outcomes": outcome_table(rows, conditions), "model_scores": ms.to_dict("records"),
         "panel_scores": ps.to_dict("records"), "agreement": agreement(ms, conditions)}
    g = g_tables(scored, countries, conditions, rng, reps)
    t.update({f"g_{k}": v for k, v in g.items()})
    answers = [rq1_answer(g["coefficients"], g["d_study"])]
    for condition in conditions:
        panel = ps[ps["condition"] == condition].set_index("iso3")
        f = frame.assign(panel=panel["panel"].reindex(frame.index),
                         panel_models=panel["models"].reindex(frame.index))
        two = rq2(f, "panel", "count_headline", rng, reps)
        three = rq3(f, "panel", "count_headline", rng, reps)
        role = "primary" if condition == PRIMARY else "contrast"
        t[f"rq2_{condition}"] = two["primary"] + two["secondary"]
        t[f"rq3_{condition}"] = three
        a2 = rq2_answer(two["primary"], two["secondary"])
        answers += [{"question": "RQ2", "condition": condition, "role": role, "answer": a2,
                     "note": REVERSED_NOTE if a2 == "reversed" else None,
                     "countries": int(f["panel"].notna().sum())},
                    {"question": "RQ3", "condition": condition, "role": role,
                     "answer": rq3_answer(three), "countries": int(f["panel"].notna().sum())}]
        t[f"constructions_{condition}"] = construction_rows(f, "panel")
        t[f"construction_ranges_{condition}"] = construction_ranges(t[f"constructions_{condition}"])
        t[f"per_model_{condition}"] = per_model_rows(frame, ms, condition)
    t["answers"] = answers
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        for name, table in t.items():
            write_csv(out, f"{name}.csv", table)
    return t


def report(t: dict) -> None:
    print("Answers, under the rules PROPOSED for section 6.2 of PLAN.md, which is OPEN")
    for a in t["answers"]:
        print(f"  {a['question']}  {a['condition']:<9} {a['answer']}")
    for row in t["g_coefficients"]:
        if row["setting"] == "one model, one call":
            print(f"  one model and one call, {row['design']:<9} E rho2 = {row['erho2']:.3f} "
                  f"[{row['boot_lower_95']:.3f}, {row['boot_upper_95']:.3f}] on "
                  f"{row['countries']} countries")
    for key in [k for k in t if k.startswith("construction_ranges_")]:
        for row in t[key]:
            print(f"  {key.removeprefix('construction_ranges_'):<9} {row['question']} "
                  f"{row['measure']:<15} headline {row['headline']: .3f}, range "
                  f"{row['lowest']: .3f} to {row['highest']: .3f} over {row['constructions']} "
                  f"constructions")


# --- self-test ---------------------------------------------------------------


PLANTED = {"m": 25.0, "pm": 16.0, "r:pm": 36.0}     # in squared score points
SPREAD = 10.0                                       # score points per unit of the country effect


def _z(s: pd.Series) -> pd.Series:
    return ((s - s.mean()) / s.std()).fillna(0.0)


def synthetic(frame: pd.DataFrame, plant: tuple[str, ...], seed: int,
              conditions: tuple[str, ...] = C.CONDITIONS) -> list[dict]:
    """A Stage C ledger written by no provider.

    The country effect is the standardised headline count, plus the standardised visibility
    where `plant` names visibility and the standardised capability where `plant` names
    capability, so research questions two and three have a known answer. The model, the
    country by model and the call components are drawn at the sizes of PLANTED.
    """
    rng = np.random.default_rng(seed)
    base = _z(frame["count_headline"])
    if "visibility" in plant:
        base = base + 1.5 * _z(frame[list(VISIBILITY)].mean(axis=1))
    if "capability" in plant:
        base = base + 1.5 * _z(frame[list(CAPABILITY)].mean(axis=1))
    country = (base / base.std()).to_numpy()
    n, k = len(country), len(C.CONFIRMATORY)
    rows = []
    for condition in conditions:
        model = rng.normal(0, np.sqrt(PLANTED["m"]), k)
        inter = rng.normal(0, np.sqrt(PLANTED["pm"]), (n, k))
        for j, m in enumerate(C.CONFIRMATORY):
            spec = C.MODELS[m]
            for rep in range(1, C.REPLICATES + 1):
                score = (50 + SPREAD * country + model[j] + inter[:, j]
                         + rng.normal(0, np.sqrt(PLANTED["r:pm"]), n))
                for iso, s in zip(frame.index, np.clip(score, 0, 100).round(1)):
                    rows.append({
                        "cell": f"holistic|{condition}|{m}|{iso}|{rep}|1|synthetic",
                        "model": m, "iso3": iso, "condition": condition, "replicate": rep,
                        "temperature": TEMPERATURE, "temperature_applied": spec.takes_temperature,
                        "route": spec.route, "role": "confirmatory", "instrument": "holistic",
                        "instrument_version": I.VERSION, "record_version": C.RECORD_VERSION,
                        "correction_policy": C.CORRECTION_POLICY, "stub": False,
                        "outcome": "ok", "stop_reason": "stop", "value": {"score": float(s)}})
    return rows


def self_test(reps: int = 2_000) -> int:
    results = []

    def expect(label, ok, detail=""):
        results.append((label, bool(ok), detail))

    expect("percentile rank of 1, 2, 3 is 0, 50, 100",
           list(pct_rank(pd.Series([1.0, 2.0, 3.0]))) == [0.0, 50.0, 100.0])
    t, p = williams(0.5, 0.5, 0.3, 30)
    expect("Williams's test of two equal correlations gives t 0 and p 1", t == 0 and p == 1)

    checks = reproduce_audit()
    bad = [c for c in checks if not c["match"]]
    expect(f"the {len(checks)} published numbers of stage three of the audit reproduce",
           not bad, "; ".join(f"{c['check']} {c['published']} against {c['reproduced']:.4f}"
                              for c in bad[:3]))

    frame = countries_frame()
    attempts = Counter()
    null = synthetic(frame, (), seed=1)
    # Kimi K3 refuses 30 training cells, GLM-5.2 refuses every call for two countries under
    # training, and one DeepSeek V4 Pro cell ends empty after a second attempt.
    rng = np.random.default_rng(2)
    training = [r for r in null if r["condition"] == "training"]
    kimi = [r for r in training if r["model"] == "kimi_k3"]
    for r in rng.choice(len(kimi), 30, replace=False):
        kimi[r].update(outcome="refusal", value=None)
    silent = sorted(frame.index)[:2]
    for r in training:
        if r["model"] == "glm_5_2" and r["iso3"] in silent:
            r.update(outcome="refusal", value=None)
    empty = next(r for r in training if r["model"] == "deepseek_v4_pro" and r["iso3"] == "FRA")
    empty.update(outcome="empty", value=None)
    attempts[empty["cell"]] = 2
    hit = {r["iso3"] for r in training if r["outcome"] != "ok"}
    t0 = analyse(null, attempts, None, frame=frame, reps=reps)

    outcomes = {(r["model"], r["condition"]): r for r in t0["outcomes"]}
    expect("the outcome table counts the 30 refusals of Kimi K3 under training",
           outcomes[(C.MODELS["kimi_k3"].label, "training")]["refusal"] == 30)
    expect("the outcome table counts the two countries GLM-5.2 never scored",
           outcomes[(C.MODELS["glm_5_2"].label, "training")]["countries_without_a_score"] == 2)
    panel = pd.DataFrame(t0["panel_scores"])
    held = panel[(panel["condition"] == "training") & panel["iso3"].isin(silent)]["models"]
    expect("the panel score of a country GLM-5.2 never scored rests on five models",
           list(held) == [5, 5])
    dropped = {r["iso3"] for r in t0["g_dropped"] if r["design"] == "training"}
    expect(f"the training design leaves out exactly the {len(hit)} countries with a missing "
           "score, and names them", dropped == hit)
    comp = {r["key"]: r["variance"] for r in t0["g_components"] if r["design"] == "record"}
    expect("the record design recovers the planted call variance within 10 per cent",
           abs(comp["r:pm"] / PLANTED["r:pm"] - 1) < 0.10, f"{comp['r:pm']:.1f}")
    expect("the record design recovers the planted country by model variance within 30 per cent",
           abs(comp["pm"] / PLANTED["pm"] - 1) < 0.30, f"{comp['pm']:.1f}")
    expect("the record design recovers the country variance within 30 per cent",
           abs(comp["p"] / SPREAD ** 2 - 1) < 0.30, f"{comp['p']:.1f}")
    a0 = {(a["question"], a["condition"]): a["answer"] for a in t0["answers"]}
    # With patents and income as controls on the 90 countries holding a patent count, the
    # interval of the standardised slope is too wide to fall inside NEGLIGIBLE_BETA in most
    # runs, so the null case is required to give neither yes nor reversed.
    expect("with nothing planted, research question two is answered neither yes nor reversed",
           a0[("RQ2", "training")] not in ("yes", "reversed"), a0[("RQ2", "training")])
    expect("with nothing planted, research question three is answered no",
           a0[("RQ3", "training")] == "no", a0[("RQ3", "training")])
    expect("research question one is answered from the training design",
           t0["answers"][0]["condition"] == "training")
    ranges = {(r["question"], r["measure"]): r for r in t0["construction_ranges_training"]}
    expect("every estimate is repeated under the 20 constructions of the count",
           all(r["constructions"] == 20 for r in ranges.values()))

    vis = analyse(synthetic(frame, ("visibility",), seed=3), Counter(), None, frame=frame,
                  reps=reps)
    a1 = {(a["question"], a["condition"]): a["answer"] for a in vis["answers"]}
    expect("with visibility planted, research question two is answered yes",
           a1[("RQ2", "training")] == "yes", a1[("RQ2", "training")])
    cap = analyse(synthetic(frame, ("capability",), seed=4), Counter(), None, frame=frame,
                  reps=reps)
    a2 = {(a["question"], a["condition"]): a["answer"] for a in cap["answers"]}
    expect("with capability planted, research question three is answered yes",
           a2[("RQ3", "training")] == "yes", a2[("RQ3", "training")])

    alone = [r for r in synthetic(frame, (), seed=5) if r["condition"] == "training"]
    t3 = analyse(alone, Counter(), None, frame=frame, reps=reps)
    expect("a ledger holding the training condition alone is analysed without a record design",
           {r["design"] for r in t3["g_coefficients"]} == {"training"})

    for label, change in (("a wrong wording version", {"instrument_version": "v1"}),
                          ("a stub row", {"stub": True}),
                          ("a row at temperature zero", {"temperature": 0.0}),
                          ("an empty answer sent once", {"outcome": "empty", "value": None})):
        rows = synthetic(frame, (), seed=6, conditions=("training",))
        rows[0].update(change)
        try:
            check(rows, Counter(), sorted(frame.index))
            expect(f"the check stops on {label}", False)
        except SystemExit:
            expect(f"the check stops on {label}", True)
    rows = synthetic(frame, (), seed=6, conditions=("training",))[1:]
    try:
        check(rows, Counter(), sorted(frame.index))
        expect("the check stops on a missing cell", False)
    except SystemExit:
        expect("the check stops on a missing cell", True)

    for label, ok, detail in results:
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))
    failed = sum(not ok for _, ok, _ in results)
    print(f"{len(results) - failed} of {len(results)} checks pass")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ledgers", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--stub", action="store_true", help="analyse stub ledgers, for rehearsal")
    ap.add_argument("--reps", type=int, default=BOOT)
    ap.add_argument("--reproduce-audit", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.reproduce_audit:
        checks = reproduce_audit()
        for c in checks:
            print(f"  {'ok  ' if c['match'] else 'FAIL'}  {c['check']:<62} published "
                  f"{c['published']:>9}  reproduced {c['reproduced']:.{c['places']}f}")
        bad = sum(not c["match"] for c in checks)
        print(f"{len(checks) - bad} of {len(checks)} published numbers reproduce")
        return 1 if bad else 0
    paths = args.ledgers or [p for p in LEDGERS if p.exists()]
    if not paths:
        raise SystemExit("no Stage C ledger exists yet")
    rows, attempts = read(paths)
    t = analyse(rows, attempts, args.out, stub=args.stub, reps=args.reps)
    report(t)
    print(f"wrote {len(list(args.out.glob('*.csv')))} tables to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
