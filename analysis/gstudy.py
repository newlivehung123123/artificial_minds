"""
Generalisability theory for the reliability design of research question one.

    python -m analysis.gstudy          runs the self-tests and prints every check

A score in the study is the number one model gives one country under one condition on one
call. The design crosses three factors, namely the country scored, the model scoring, and the
condition, which is training data alone or the administrative record supplied in the prompt.
The five calls of every combination of country, model and condition are replicates inside the
combination. Generalisability theory (Cronbach, Gleser, Nanda and Rajaratnam 1972, Brennan
2001) splits the variance of the scores into one variance component for every factor and for
every interaction of factors, plus a component for the replicates inside a combination, and
asks how much of the variance in an averaged country score comes from real differences between
countries.

The country is the object of measurement, so variance between countries is the signal, and
every other component that changes the ordering of countries is error. The model and the
replicate are random factors, because the six models and the five calls stand in for any
models and any calls. The condition is a fixed factor, because the study names two conditions
and asks about no other condition.

The estimator is analysis of variance solved through the expected mean squares of a balanced
random design, in closed form, for any number of crossed factors. The design of one condition,
country by model, and the design of the two conditions together, country by model by
condition, therefore run through the same code, and every step can be checked by hand. A negative estimate is set to
zero and named, following Cronbach and colleagues (1972), because sampling error can drive a
small true component below zero.

The estimator refuses a design with a missing score, because the expected mean squares hold
for a balanced design alone, and refuses a design with one replicate per combination, because
the highest interaction and the replicate component are then the same quantity.

The generic solution reproduces the closed forms of `gstudy.py` in the Digital Minds Research
Sprint study of August 2026, a sprint run by Apart Research, an AI safety research group, in
which Jason Hung measured how much of a stated AI preference belongs to the model and how much
to the prompt format. This repository
does not import the Digital Minds file, and the self-tests below write the closed forms of the
Digital Minds file out again and check the generic solution against the closed forms to nine
decimal places.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import prod

import numpy as np
from scipy import stats


@dataclass
class GStudy:
    """Variance components of one balanced design, in squared points of the score.

    A component is named by the letters of the factors in the component, in the order of
    `facets`, so "pm" is the interaction of country and model. The replicate component is
    named "r:" followed by every factor letter, so "r:pm" is the variance between the calls
    inside one combination of country and model. `components` holds every estimate with a
    negative estimate set to zero, `untruncated` holds every estimate as solved, and
    `negatives` names every component set to zero. `ms` and `df` hold the mean square and the
    degrees of freedom of every source, under the same names. `n` holds the number of levels
    of every factor and, under "r", the number of replicates per combination."""

    facets: tuple[str, ...]
    n: dict[str, int]
    components: dict[str, float]
    untruncated: dict[str, float]
    ms: dict[str, float]
    df: dict[str, int]
    negatives: tuple[str, ...]

    @property
    def residual(self) -> str:
        return "r:" + "".join(self.facets)

    def total(self) -> float:
        return float(sum(self.components.values()))

    def shares(self) -> dict[str, float]:
        total = self.total()
        return {k: (v / total if total > 0 else float("nan"))
                for k, v in self.components.items()}


def _name(subset, facets: tuple[str, ...]) -> str:
    return "".join(f for f in facets if f in subset)


def estimate(x, facets) -> GStudy:
    """Estimate every variance component of a balanced crossed design.

    `x` holds one axis per factor, in the order of `facets`, and a last axis of replicates.
    A design of five countries by six models with five calls per combination is an array of
    shape (5, 6, 5) with facets "pm". Every factor needs two levels or more, and the replicate
    axis needs two replicates or more.

    For every set of factors, the effect is the mean over every axis outside the set, with
    every lower-order effect taken away by inclusion and exclusion, and the sum of squares is
    the squared effect summed over every score. The expected mean square of a set of factors
    is the replicate variance plus every component whose factors include the set, weighted by
    the number of scores behind one level of the component, and the equations are solved from
    the highest interaction downwards with the unrounded, untruncated estimates."""
    facets = tuple(facets)
    x = np.asarray(x, dtype=float)
    k = len(facets)
    if k == 0 or len(set(facets)) != k or any(len(f) != 1 or f == "r" for f in facets):
        raise ValueError(f"facets must be distinct single letters other than r, got {facets}")
    if x.ndim != k + 1:
        raise ValueError(f"a design of {k} factors needs {k + 1} axes, got shape {x.shape}")
    if np.isnan(x).any():
        raise ValueError(f"{int(np.isnan(x).sum())} of {x.size} scores are missing. The "
                         "expected mean squares hold for a balanced design alone, so a "
                         "missing score is reported and never averaged over.")
    n = dict(zip(facets, x.shape[:k]))
    n["r"] = x.shape[k]
    single = [f for f in facets if n[f] < 2]
    if single:
        raise ValueError(f"factor {', '.join(single)} has one level, so no variance between "
                         "levels of the factor can be estimated")
    if n["r"] < 2:
        raise ValueError("one replicate per combination makes the highest interaction and "
                         "the replicate component the same quantity, so neither component "
                         "can be estimated")

    subsets = [frozenset(c) for size in range(1, k + 1) for c in combinations(facets, size)]
    means = {frozenset(): x.mean(axis=tuple(range(k + 1)), keepdims=True)}
    for s in subsets:
        drop = tuple(i for i, f in enumerate(facets) if f not in s) + (k,)
        means[s] = x.mean(axis=drop, keepdims=True)

    ms: dict[str, float] = {}
    df: dict[str, int] = {}
    weight: dict[str, int] = {}
    for s in subsets:
        key = _name(s, facets)
        effect = sum((-1) ** (len(s) - size) * means[frozenset(t)]
                     for size in range(len(s) + 1) for t in combinations(s, size))
        ss = float((effect ** 2).sum()) * (x.size / effect.size)
        df[key] = prod(n[f] - 1 for f in s)
        ms[key] = ss / df[key]
        weight[key] = n["r"] * prod(n[f] for f in facets if f not in s)
    resid = "r:" + "".join(facets)
    df[resid] = prod(n[f] for f in facets) * (n["r"] - 1)
    ms[resid] = float(((x - means[frozenset(facets)]) ** 2).sum()) / df[resid]

    solved = {resid: ms[resid]}
    for s in sorted(subsets, key=len, reverse=True):
        above = sum(weight[_name(t, facets)] * solved[_name(t, facets)]
                    for t in subsets if t > s)
        key = _name(s, facets)
        solved[key] = (ms[key] - ms[resid] - above) / weight[key]

    order = [_name(s, facets) for s in subsets] + [resid]
    untruncated = {key: float(solved[key]) for key in order}
    return GStudy(
        facets=facets,
        n=n,
        components={key: max(0.0, v) for key, v in untruncated.items()},
        untruncated=untruncated,
        ms={key: ms[key] for key in order},
        df={key: df[key] for key in order},
        negatives=tuple(key for key, v in untruncated.items() if v < 0),
    )


def coefficients(gs: GStudy, n_prime: dict[str, int], fixed=(), obj: str = "p",
                 truncated: bool = True) -> dict:
    """The generalisability coefficient and the dependability coefficient of one decision study.

    A decision study asks what the coefficients would be if a country score were the mean over
    `n_prime` levels of every factor other than the country, with `n_prime["r"]` calls in every
    combination. A fixed factor keeps the number of levels the data hold, because a fixed factor
    names levels and does not sample levels.

    The universe score variance, tau, is the country component plus every interaction of the
    country with fixed factors alone, divided by the number of levels averaged over. The
    relative error variance, delta, is every other interaction of the country with the other
    factors, plus the replicate component, with every component divided by the number of
    levels and calls averaged over. The absolute error variance, Delta, adds every component without the
    country that involves at least one random factor, so the main effect of a fixed factor is
    never error. The generalisability coefficient, Erho2, is tau over tau plus delta and
    describes how well averaged scores order countries. The dependability coefficient, Phi, is
    tau over tau plus Delta and describes how well an averaged score places one country on the
    scale itself (Brennan 2001).

    With `truncated` false the coefficients use the untruncated estimates. When the model is
    the only random factor besides the replicate, as in every design of the study, the
    generalisability coefficient at the sizes of the data then equals one minus the ratio of
    the mean square of country by model to the mean square of countries, and in a design of
    countries with replicates alone, one minus the ratio of the replicate mean square to the
    mean square of countries. `feldt_interval` gives an exact interval for a coefficient of
    the kind."""
    values = gs.components if truncated else gs.untruncated
    if obj not in gs.facets:
        raise ValueError(f"object of measurement {obj!r} is not a factor of {gs.facets}")
    fixed = set(fixed)
    others = [f for f in gs.facets if f != obj]
    if obj in fixed or not fixed <= set(others):
        raise ValueError(f"fixed factors {sorted(fixed)} must be factors other than {obj!r}")
    absent = (set(others) | {"r"}) - set(n_prime)
    if absent:
        raise ValueError(f"the decision study needs a number of levels for {sorted(absent)}")
    for f in fixed:
        if n_prime[f] != gs.n[f]:
            raise ValueError(f"factor {f!r} is fixed, so the decision study keeps the "
                             f"{gs.n[f]} levels of the data, not {n_prime[f]}")

    tau = delta = Delta = 0.0
    for key, v in values.items():
        if key == gs.residual:
            share = v / (prod(n_prime[f] for f in others) * n_prime["r"])
            delta += share
            Delta += share
            continue
        factors = set(key)
        rest = factors - {obj}
        share = v / prod(n_prime[f] for f in rest)
        if obj in factors:
            if rest <= fixed:
                tau += share
            else:
                delta += share
                Delta += share
        elif not factors <= fixed:
            Delta += share
    return {
        "n_prime": dict(n_prime),
        "fixed": tuple(sorted(fixed)),
        "tau": tau,
        "delta": delta,
        "Delta": Delta,
        "Erho2": tau / (tau + delta) if tau + delta > 0 else float("nan"),
        "Phi": tau / (tau + Delta) if tau + Delta > 0 else float("nan"),
    }


def d_study(gs: GStudy, sizes: dict[str, list[int]], fixed=(), obj: str = "p") -> list[dict]:
    """The coefficients over every combination of the numbers of levels listed in `sizes`."""
    keys = list(sizes)
    grid = [[]]
    for key in keys:
        grid = [g + [v] for g in grid for v in sizes[key]]
    return [coefficients(gs, dict(zip(keys, g)), fixed=fixed, obj=obj) for g in grid]


def feldt_interval(rho_hat: float, df_error: int, df_object: int,
                   level: float = 0.95) -> tuple[float, float]:
    """Exact interval for a coefficient of the form one minus a ratio of two mean squares.

    With normal effects in a balanced design, (1 - rho_hat) / (1 - rho) follows an F
    distribution with `df_error` and `df_object` degrees of freedom, where `df_error` belongs to
    the mean square in the numerator of the ratio and `df_object` to the mean square of
    countries (Feldt 1965 for the design of country by model, McGraw and Wong 1996 for the
    design of countries with replicates alone). The interval inverts the two tails of the F
    distribution."""
    tail = (1.0 - level) / 2.0
    lower_f = stats.f.ppf(tail, df_error, df_object)
    upper_f = stats.f.ppf(1.0 - tail, df_error, df_object)
    return 1.0 - (1.0 - rho_hat) / lower_f, 1.0 - (1.0 - rho_hat) / upper_f


def spearman_brown(rho: float, factor: float) -> float:
    """The coefficient after the number of averaged levels of every error source is multiplied
    by `factor`. The function is increasing in `rho`, so applying the function to the two ends
    of an exact interval gives an exact interval for the new coefficient."""
    return factor * rho / (1.0 + (factor - 1.0) * rho)


def simulate(sizes: dict[str, int], replicates: int, planted: dict[str, float],
             seed: int = 0, grand_mean: float = 20.0) -> np.ndarray:
    """Scores with known variance components, for testing the estimator. `planted` is keyed
    like `GStudy.components`, and a component left unnamed is zero."""
    facets = tuple(sizes)
    rng = np.random.default_rng(seed)
    shape = tuple(sizes.values()) + (replicates,)
    x = np.full(shape, grand_mean)
    for key, variance in planted.items():
        if key.startswith("r:"):
            x = x + rng.normal(0.0, np.sqrt(variance), shape)
        else:
            x = x + rng.normal(0.0, np.sqrt(variance),
                               tuple(sizes[f] if f in key else 1 for f in facets) + (1,))
    return x


# --- self-tests ---------------------------------------------------------------


def _closed_forms(x: np.ndarray) -> dict[str, float]:
    """The eight closed forms of `gstudy.py` in the Digital Minds study, written out again with
    the letters a, b and c for the three factors and returned untruncated."""
    n_a, n_b, n_c, n_r = x.shape
    g = x.mean()
    m_a = x.mean(axis=(1, 2, 3), keepdims=True)
    m_b = x.mean(axis=(0, 2, 3), keepdims=True)
    m_c = x.mean(axis=(0, 1, 3), keepdims=True)
    m_ab = x.mean(axis=(2, 3), keepdims=True)
    m_ac = x.mean(axis=(1, 3), keepdims=True)
    m_bc = x.mean(axis=(0, 3), keepdims=True)
    m_abc = x.mean(axis=3, keepdims=True)
    ss_a = n_b * n_c * n_r * ((m_a - g) ** 2).sum()
    ss_b = n_a * n_c * n_r * ((m_b - g) ** 2).sum()
    ss_c = n_a * n_b * n_r * ((m_c - g) ** 2).sum()
    ss_ab = n_c * n_r * ((m_ab - m_a - m_b + g) ** 2).sum()
    ss_ac = n_b * n_r * ((m_ac - m_a - m_c + g) ** 2).sum()
    ss_bc = n_a * n_r * ((m_bc - m_b - m_c + g) ** 2).sum()
    ss_abc = n_r * ((m_abc - m_ab - m_ac - m_bc + m_a + m_b + m_c - g) ** 2).sum()
    ss_e = ((x - m_abc) ** 2).sum()
    ms_a, ms_b, ms_c = ss_a / (n_a - 1), ss_b / (n_b - 1), ss_c / (n_c - 1)
    ms_ab = ss_ab / ((n_a - 1) * (n_b - 1))
    ms_ac = ss_ac / ((n_a - 1) * (n_c - 1))
    ms_bc = ss_bc / ((n_b - 1) * (n_c - 1))
    ms_abc = ss_abc / ((n_a - 1) * (n_b - 1) * (n_c - 1))
    ms_e = ss_e / (n_a * n_b * n_c * (n_r - 1))
    return {
        "a": (ms_a - ms_ab - ms_ac + ms_abc) / (n_r * n_b * n_c),
        "b": (ms_b - ms_ab - ms_bc + ms_abc) / (n_r * n_a * n_c),
        "c": (ms_c - ms_ac - ms_bc + ms_abc) / (n_r * n_a * n_b),
        "ab": (ms_ab - ms_abc) / (n_r * n_c),
        "ac": (ms_ac - ms_abc) / (n_r * n_b),
        "bc": (ms_bc - ms_abc) / (n_r * n_a),
        "abc": (ms_abc - ms_e) / n_r,
        "r:abc": ms_e,
    }


def self_test() -> int:
    """Run every check, print one line per check, and return the number of failures."""
    failures = ran = 0

    def check(label: str, passed: bool, detail: str = "") -> None:
        nonlocal failures, ran
        ran += 1
        failures += not passed
        print(f"  {'ok  ' if passed else 'FAIL'} {label}{'  ' + detail if detail else ''}")

    def refused(label: str, call) -> None:
        try:
            call()
        except ValueError:
            check(label, True)
        else:
            check(label, False, "accepted")

    print("agreement with the closed forms of the Digital Minds study, untruncated")
    x = simulate({"a": 4, "b": 3, "c": 5}, 3, {"a": 2.0, "b": 0.5, "c": 1.0, "ab": 0.4,
                                                "ac": 0.3, "bc": 0.2, "abc": 0.6,
                                                "r:abc": 1.0}, seed=1)
    gs = estimate(x, "abc")
    closed = _closed_forms(x)
    gap = max(abs(gs.untruncated[k] - closed[k]) for k in closed)
    check("all eight components agree to 1e-9", gap < 1e-9, f"largest gap {gap:.1e}")

    print("\nthe estimator is unbiased over 400 simulated designs of eight countries, six models "
          "and four conditions with three calls")
    planted = {"p": 4.0, "m": 1.0, "c": 2.0, "pm": 1.5, "pc": 0.8, "mc": 0.5,
               "pmc": 0.6, "r:pmc": 1.0}
    draws = np.array([[estimate(simulate({"p": 8, "m": 6, "c": 4}, 3, planted,
                                         seed=100 + s), "pmc").untruncated[k]
                       for k in planted] for s in range(400)])
    for j, k in enumerate(planted):
        mean = draws[:, j].mean()
        se = draws[:, j].std(ddof=1) / np.sqrt(len(draws))
        check(f"mean estimate of {k:6} within four standard errors of the planted value",
              abs(mean - planted[k]) <= 4 * se,
              f"mean {mean:7.4f}, planted {planted[k]:.2f}, standard error {se:.4f}")

    print("\nno signal is invented when only replicate variance is planted")
    gs = estimate(simulate({"p": 20, "m": 8, "c": 6}, 6, {"r:pmc": 1.0}, seed=3), "pmc")
    check("replicate component near one", abs(gs.components["r:pmc"] - 1.0) < 0.08,
          f"{gs.components['r:pmc']:.4f}")
    largest = max(v for k, v in gs.components.items() if k != "r:pmc")
    check("every other component near zero", largest < 0.05, f"largest {largest:.4f}")

    print("\nrefusals")
    good = simulate({"p": 5, "m": 6}, 5, {"p": 1.0, "r:pm": 1.0}, seed=4)
    holed = good.copy()
    holed[0, 0, 0] = np.nan
    refused("a missing score is refused", lambda: estimate(holed, "pm"))
    refused("one replicate per combination is refused", lambda: estimate(good[:, :, :1], "pm"))
    refused("a factor with one level is refused", lambda: estimate(good[:, :1, :], "pm"))
    gs3 = estimate(simulate({"p": 5, "m": 6, "c": 2}, 5, planted, seed=5), "pmc")
    refused("a fixed factor cannot change size in a decision study",
            lambda: coefficients(gs3, {"m": 6, "c": 3, "r": 5}, fixed=("c",)))

    print("\nat the sizes of the data, the coefficient is one minus a ratio of mean squares")
    gs = estimate(good, "pm")
    co = coefficients(gs, {"m": 6, "r": 5}, truncated=False)["Erho2"]
    check("country by model, 1 - MS(pm) / MS(p)",
          abs(co - (1 - gs.ms["pm"] / gs.ms["p"])) < 1e-12)
    one_way = estimate(good[:, 0, :], "p")
    co = coefficients(one_way, {"r": 5}, truncated=False)["Erho2"]
    check("countries with replicates alone, 1 - MS(r:p) / MS(p)",
          abs(co - (1 - one_way.ms["r:p"] / one_way.ms["p"])) < 1e-12)

    print("\nwith the condition fixed, the coefficient equals the coefficient of the design "
          "averaged over conditions")
    x3 = simulate({"p": 5, "m": 6, "c": 2}, 5, planted, seed=6)
    gs3 = estimate(x3, "pmc")
    fixed_c = coefficients(gs3, {"m": 6, "c": 2, "r": 5}, fixed=("c",), truncated=False)["Erho2"]
    averaged = estimate(x3.mean(axis=2), "pm")
    check("condition fixed equals 1 - MS(pm) / MS(p) of the averaged design",
          abs(fixed_c - (1 - averaged.ms["pm"] / averaged.ms["p"])) < 1e-12)
    rng = np.random.default_rng(7)
    shuffled = x3.copy()
    for i in range(5):
        for j in range(6):
            shuffled[i, j, 1, :] = shuffled[i, j, 1, rng.permutation(5)]
    paired = estimate(shuffled.mean(axis=2), "pm")
    check("pairing calls across conditions changes neither mean square",
          abs(paired.ms["p"] - averaged.ms["p"]) < 1e-9
          and abs(paired.ms["pm"] - averaged.ms["pm"]) < 1e-9)

    print("\na fixed condition counts the country by condition interaction as signal")
    gs = estimate(simulate({"p": 40, "m": 8, "c": 2}, 5,
                           {"p": 10.0, "m": 2.0, "c": 2.0, "pm": 5.0, "pc": 20.0, "mc": 1.0,
                            "pmc": 5.0, "r:pmc": 10.0}, seed=8), "pmc")
    as_fixed = coefficients(gs, {"m": 8, "c": 2, "r": 5}, fixed=("c",))["Erho2"]
    as_random = coefficients(gs, {"m": 8, "c": 2, "r": 5})["Erho2"]
    check("fixed condition gives a larger coefficient than a random condition",
          as_fixed > as_random, f"{as_fixed:.3f} against {as_random:.3f}")

    print("\na decision study is monotone")
    gs = estimate(simulate({"p": 30, "m": 10}, 6, {"p": 4.0, "m": 1.0, "pm": 2.0,
                                                    "r:pm": 6.0}, seed=9), "pm")
    by_models = [coefficients(gs, {"m": m, "r": 5})["Erho2"] for m in range(1, 13)]
    by_calls = [coefficients(gs, {"m": 6, "r": r})["Erho2"] for r in (1, 2, 3, 5, 10)]
    check("more models never lowers the coefficient", all(np.diff(by_models) > 0))
    check("more calls never lowers the coefficient", all(np.diff(by_calls) > 0))
    grid = d_study(gs, {"m": list(range(1, 13)), "r": [1, 2, 3, 5, 10]})
    check("dependability never exceeds generalisability",
          all(row["Phi"] <= row["Erho2"] + 1e-12 for row in grid))

    print("\nSpearman-Brown")
    check("round trip", abs(spearman_brown(spearman_brown(0.7, 1 / 6), 6) - 0.7) < 1e-12)
    gs = estimate(good, "pm")
    six = coefficients(gs, {"m": 6, "r": 5}, truncated=False)["Erho2"]
    one = coefficients(gs, {"m": 1, "r": 5}, truncated=False)["Erho2"]
    check("six models to one model equals the decision study at one model",
          abs(spearman_brown(six, 1 / 6) - one) < 1e-12)
    f_ratio = one_way.ms["p"] / one_way.ms["r:p"]
    single = spearman_brown(1 - 1 / f_ratio, 1 / 5)
    check("one call from five equals (F - 1) / (F + k - 1)",
          abs(single - (f_ratio - 1) / (f_ratio + 5 - 1)) < 1e-12)

    print("\ncoverage of the exact 95 per cent interval over 2,000 simulated designs per setting")
    designs = [
        ("five countries by six models with five calls", {"p": 5, "m": 6},
         {"p": 10.0, "m": 20.0, "pm": 30.0, "r:pm": 40.0}, "pm",
         10.0 / (10.0 + 30.0 / 6 + 40.0 / 30)),
        ("five countries with five calls and no model factor", {"p": 5},
         {"p": 10.0, "r:p": 40.0}, "r:p", 10.0 / (10.0 + 40.0 / 5)),
        ("five countries by six models by two fixed conditions with five calls",
         {"p": 5, "m": 6, "c": 2},
         {"p": 10.0, "m": 5.0, "c": 20.0, "pm": 20.0, "pc": 8.0, "mc": 3.0, "pmc": 10.0,
          "r:pmc": 40.0}, "pm",
         (10.0 + 8.0 / 2) / (10.0 + 8.0 / 2 + 20.0 / 6 + 10.0 / 12 + 40.0 / 60)),
    ]
    for label, sizes, comps, error, true in designs:
        hits = 0
        for s in range(2000):
            gs = estimate(simulate(sizes, 5, comps, seed=10_000 + s), "".join(sizes))
            rho_hat = 1 - gs.ms[error] / gs.ms["p"]
            lo, hi = feldt_interval(rho_hat, gs.df[error], gs.df["p"])
            hits += lo <= true <= hi
        check(f"{label}, coverage between 0.93 and 0.97", 0.93 <= hits / 2000 <= 0.97,
              f"{hits / 2000:.3f} at a true coefficient of {true:.3f}")

    print(f"\n{ran - failures} of {ran} checks passed")
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if self_test() else 0)
