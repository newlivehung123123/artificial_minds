"""
One correction to the inherited action layer, and the evidence for the correction.

The completed audit at https://doi.org/10.7910/DVN/YQNFYI is deposited and this
package reads the deposited files and never writes to the deposited files. A
correction therefore lives here, is applied to a copy in memory, and names every
record changed together with the reason for the change.

WHAT IS WRONG
-------------
The action layer holds two measures of national AI strategy, both taken from the
Stanford AI Index.

  "Released National Strategy On AI"
      76 countries, one observation each, years 2017 to 2022, value 1 or 0.
      Value 1 for 62 countries and value 0 for 14 countries.
  "Alignment of National AI Strategy with OECD AI Principles (Cosine Similarity
  Score)"
      55 countries, one observation each, year 2024.

The first measure records a release event in a stated year and not a standing
status. A country carrying value 0 in 2021 is a country for which the Stanford AI
Index reports no release during 2021, which is a different statement from the
statement that the country has no national AI strategy. The rendered
administrative record printed value 0 as the word "no", which asserts the second
statement on the evidence of the first.

An alignment score is a cosine similarity between the text of a national AI
strategy and the text of the OECD AI Principles, so an alignment score exists
only where a strategy document exists. The alignment measure therefore contains
the release information the first measure is missing, and among the 122 eligible
countries the two measures disagree for 18 countries.

  Five countries carry value 0 for release alongside an alignment score, which is
  a contradiction inside one dataset. Belgium, Jordan, Morocco, Nigeria and
  Uzbekistan.
  Thirteen countries carry no release observation at all alongside an alignment
  score, which is not a contradiction but withholds information the dataset
  holds. Burkina Faso, Bolivia, Ethiopia, Ghana, Kuwait, Lebanon, Mali, Malaysia,
  Nicaragua, Pakistan, Senegal, Taiwan and Uganda.

WHY THE CORRECTION MATTERS TO THIS STUDY
----------------------------------------
Research question one compares a model score for a country against the count of
national action for that same country, so a defect in the count moves the
comparison target and not only the prompt. Rebuilding the count with the 18
records corrected moves 69 of the 122 countries in the ordering, moves one
country into or out of the highest ten, and moves Jordan 46 places. A defect that
moves a country 46 places is large enough to change what research question one
concludes, so the corrected count is what this study compares against, and the
size of the movement is reported rather than absorbed.

POLICIES
--------
"none"            Change nothing. Used to prove that the rebuild below reproduces
                  the deposited count exactly before any correction is applied.
"contradictions"  Correct the five countries whose two measures contradict each
                  other, and leave the 13 countries with no release observation
                  as not recorded. The conservative reading.
"entailed"        Correct all 18 countries, on the grounds that an alignment score
                  entails the existence of a strategy document in both groups
                  equally. The default, because treating identical evidence
                  differently in two groups would itself be a defect.

A correction sets the release value to 1. A correction never sets a release year,
because the year in which a strategy was published is genuinely unknown for a
country with no release observation, and writing a year there would replace a
defect with an invention.

A correction also clears the year already held for a country in the contradiction
group. The year held beside a release value of 0 is the year during which the
Stanford AI Index reports no release, so once the value is corrected to 1 that
same year would read as the year of publication and would assert something the
source does not support. Jordan is the clearest case. Jordan carries value 0 in
2022, and printing "released: yes" beside "year: 2022" would claim a Jordanian
strategy published in 2022 on the evidence of a source saying only that no
Jordanian release was reported during 2022. Both groups therefore end with a
release of 1 and a year of not recorded.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

from . import config as C

POLICIES = ("none", "contradictions", "entailed")
DEFAULT_POLICY = "entailed"

RELEASE_METRIC = "Released National Strategy On AI"
ALIGNMENT_METRIC = (
    "Alignment of National AI Strategy with OECD AI Principles "
    "(Cosine Similarity Score)"
)

AUDIT_LONG = C.AUDIT / "data" / "processed" / "AIMSA_observations_long.csv"
AUDIT_INDEX_SCRIPT = C.AUDIT / "scripts" / "10_action_index.py"

# The year an appended release observation carries. A country in the "entailed"
# group has no release observation, so the year below is the year of the evidence
# for the correction, namely the year of the alignment score, and is never read as
# a year of publication. The rendered record leaves the year of publication as not
# recorded for these countries, which is what scoring/record.py does by taking the
# year from the deposited files and not from a correction.
EVIDENCE_YEAR = 2024

REASON = (
    "an alignment score with the OECD AI Principles exists for this country, and "
    "an alignment score is computed from the text of a national AI strategy, so a "
    "national AI strategy exists"
)

_LONG: pd.DataFrame | None = None


def audit_long() -> pd.DataFrame:
    """The deposited observation file. Read once, never written."""
    global _LONG
    if _LONG is None:
        _LONG = pd.read_csv(AUDIT_LONG, dtype={"ISO3": str}, low_memory=False)
    return _LONG


def _eligible() -> list[str]:
    """The 122 countries the completed audit gives a count of national action."""
    return sorted(pd.read_csv(C.AUDIT_INDEX, dtype={"ISO3": str})["ISO3"])


def corrections(policy: str = DEFAULT_POLICY) -> pd.DataFrame:
    """One row per record corrected, with the old value, new value and reason.

    Columns: ISO3, Country, group, old_value, new_value, alignment_score, reason.
    The "group" column is "contradiction" where a release value of 0 is present
    and "absent" where no release observation is present.
    """
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}, expected one of {POLICIES}")
    if policy == "none":
        return pd.DataFrame(
            columns=["ISO3", "Country", "group", "old_value", "new_value",
                     "alignment_score", "reason"]
        )

    long = audit_long()
    release = long[long["Metric"] == RELEASE_METRIC].set_index("ISO3")
    align = long[long["Metric"] == ALIGNMENT_METRIC].set_index("ISO3")
    eligible = _eligible()

    rows = []
    for iso3 in eligible:
        if iso3 not in align.index:
            continue
        score = float(align.loc[iso3, "Value"])
        if iso3 in release.index:
            old = float(release.loc[iso3, "Value"])
            if old >= 0.5:
                continue
            group, old_shown = "contradiction", old
        else:
            group, old_shown = "absent", None
        if group == "absent" and policy == "contradictions":
            continue
        rows.append({
            "ISO3": iso3,
            "Country": align.loc[iso3, "Country"],
            "group": group,
            "old_value": old_shown,
            "new_value": 1.0,
            "alignment_score": round(score, 4),
            "reason": REASON,
        })
    return pd.DataFrame(rows).sort_values(["group", "ISO3"]).reset_index(drop=True)


def corrected_wide(policy: str = DEFAULT_POLICY) -> pd.DataFrame:
    """The deposited wide file with the release flag corrected, indexed by ISO3.

    Two columns change and no other column changes.

    The flag act_strategy_released is set to 1 for every country the policy
    corrects. The year act_strategy_released_year is kept only where the deposited
    flag is already 1, and is cleared everywhere else, because the year beside a
    deposited flag of 0 is the year during which the Stanford AI Index reports no
    release and is therefore not a year of publication. Keeping the year wherever
    the deposited flag is 0 would print a publication year beside Israel, whose
    flag says no release was reported, and would print 2022 beside Jordan, whose
    flag this policy corrects. One rule removes both, and the rule is stated in
    terms of the deposited flag rather than the corrected flag, because correcting
    a flag does not turn a year of observation into a year of publication.
    """
    wide = pd.read_csv(C.AUDIT_WIDE, dtype={"ISO3": str}, low_memory=False).set_index("ISO3")
    released = pd.to_numeric(wide["act_strategy_released"], errors="coerce") >= 0.5
    wide.loc[~released, "act_strategy_released_year"] = pd.NA
    fixes = corrections(policy)
    if not fixes.empty:
        wide.loc[list(fixes["ISO3"]), "act_strategy_released"] = 1.0
    return wide


def years_cleared() -> list[str]:
    """Countries whose strategy year is withheld because no release is recorded.

    A year held beside a deposited release flag of 0 is the year the Stanford AI
    Index covers and not a year of publication, so the year is not rendered. The
    list is reported rather than left implicit, because withholding a value that
    the deposited file contains is a change a replicator has to be able to see.
    """
    wide = pd.read_csv(C.AUDIT_WIDE, dtype={"ISO3": str}, low_memory=False).set_index("ISO3")
    wide = wide.loc[_eligible()]
    flag = pd.to_numeric(wide["act_strategy_released"], errors="coerce")
    year = pd.to_numeric(wide["act_strategy_released_year"], errors="coerce")
    return sorted(wide.index[(flag < 0.5) & year.notna()])


def corrected_long(policy: str = DEFAULT_POLICY) -> pd.DataFrame:
    """The deposited observation file with the release observations corrected.

    A country in the contradiction group has the value of an existing observation
    changed from 0 to 1. A country in the absent group gains one observation,
    copied field for field from an existing release observation so that the unit,
    direction, component, layer and source are identical, then given this
    country, the value 1 and the year of the evidence. Every changed or added row
    carries a "Correction" column naming the reason, and a row left alone carries
    an empty string, so a corrected file can always be told from a deposited one.
    """
    long = audit_long().copy()
    long["Correction"] = ""
    fixes = corrections(policy)
    if fixes.empty:
        return long

    is_release = long["Metric"] == RELEASE_METRIC
    template = long[is_release].iloc[0]

    changed = fixes.loc[fixes["group"] == "contradiction", "ISO3"].tolist()
    mask = is_release & long["ISO3"].isin(changed)
    long.loc[mask, "Value"] = 1.0
    long.loc[mask, "Correction"] = REASON

    added = fixes[fixes["group"] == "absent"]
    new_rows = []
    for _, fix in added.iterrows():
        row = template.copy()
        row["ISO3"] = fix["ISO3"]
        row["Country"] = fix["Country"]
        row["Value"] = 1.0
        row["Year"] = EVIDENCE_YEAR
        row["Correction"] = REASON
        new_rows.append(row)
    if new_rows:
        long = pd.concat([long, pd.DataFrame(new_rows)], ignore_index=True)
    return long


def _audit_index_module():
    """The audit's own index builder, loaded from file.

    The file name begins with a digit, so a plain import statement cannot name the
    module. Loading the audit's own code and calling the audit's own functions is
    what makes the rebuild below the audit's arithmetic by construction rather
    than a second implementation that happens to agree.
    """
    spec = importlib.util.spec_from_file_location("aimsa_action_index", AUDIT_INDEX_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("aimsa_action_index", module)
    spec.loader.exec_module(module)
    return module


def action_index(policy: str = DEFAULT_POLICY) -> pd.Series:
    """The count of national action, rebuilt under one correction policy.

    Built by calling the audit's own latest(), eligible_units() and build(), so
    the only difference between the series returned here and the deposited
    action_score column is the correction named by the policy.
    """
    mod = _audit_index_module()
    audit_config = sys.modules["config"]
    long = corrected_long(policy)
    act = mod.latest(long)
    eligible = audit_config.eligible_units(long)
    _, score, _, _ = mod.build(act, eligible)
    return score.dropna()


def verify() -> dict:
    """Prove the rebuild reproduces the deposited count before correcting anything.

    Returns the largest absolute difference between the rebuilt count under policy
    "none" and the deposited action_score column, the correlation between the two,
    and the number of countries compared. A largest difference of zero is the only
    result that licenses using the rebuilt count anywhere.
    """
    deposited = (pd.read_csv(C.AUDIT_INDEX, dtype={"ISO3": str})
                 .set_index("ISO3")["action_score"].dropna())
    rebuilt = action_index("none")
    both = pd.DataFrame({"deposited": deposited, "rebuilt": rebuilt}).dropna()
    return {
        "countries": len(both),
        "max_abs_difference": float((both["deposited"] - both["rebuilt"]).abs().max()),
        "correlation": float(both["deposited"].corr(both["rebuilt"])),
        "deposited_only": sorted(set(deposited.index) - set(rebuilt.index)),
        "rebuilt_only": sorted(set(rebuilt.index) - set(deposited.index)),
    }


def sensitivity(policy: str = DEFAULT_POLICY) -> dict:
    """How far the count moves when the correction is applied.

    Every figure reported about the correction in PLAN.md or in the memo comes
    from this function, so a figure in prose can be reproduced by one call.
    """
    base = action_index("none")
    alt = action_index(policy)
    both = pd.DataFrame({"base": base, "alt": alt}).dropna()
    rank_base = both["base"].rank(ascending=False)
    rank_alt = both["alt"].rank(ascending=False)
    moved = (rank_base - rank_alt).abs()
    touched = list(corrections(policy)["ISO3"])
    top_base = set(both["base"].nlargest(10).index)
    top_alt = set(both["alt"].nlargest(10).index)
    return {
        "policy": policy,
        "records_corrected": len(touched),
        "countries": len(both),
        "spearman": float(rank_base.corr(rank_alt, method="spearman")),
        "pearson": float(both["base"].corr(both["alt"])),
        "countries_whose_rank_moves": int((moved > 0).sum()),
        "largest_rank_move": int(moved.max()),
        "mean_point_gain_among_corrected": float(
            (both["alt"] - both["base"]).reindex(touched).dropna().mean()),
        "highest_ten_changes": len(top_base ^ top_alt) // 2,
    }


if __name__ == "__main__":
    check = verify()
    print("Rebuilding the deposited count with no correction applied")
    print(f"  countries compared            {check['countries']}")
    print(f"  largest absolute difference   {check['max_abs_difference']:.10f}")
    print(f"  correlation                   {check['correlation']:.10f}")
    if check["deposited_only"] or check["rebuilt_only"]:
        print(f"  in the deposit only           {check['deposited_only']}")
        print(f"  in the rebuild only           {check['rebuilt_only']}")
    if check["max_abs_difference"] > 1e-9:
        raise SystemExit(
            "the rebuild does not reproduce the deposited count, so no corrected "
            "count may be used anywhere until the difference is explained"
        )
    print("  the rebuild is the deposited count, so a corrected rebuild is comparable")

    cleared = years_cleared()
    print()
    print(f"=== a strategy year withheld for {len(cleared)} countries ===")
    print(f"  {', '.join(cleared)}")
    print("  the year beside a release flag of 0 is the year the source covers and")
    print("  not a year of publication, so the year is not rendered")

    for policy in ("contradictions", "entailed"):
        fixes = corrections(policy)
        print()
        print(f"=== policy {policy}: {len(fixes)} records corrected ===")
        print(fixes[["ISO3", "Country", "group", "old_value", "new_value",
                     "alignment_score"]].to_string(index=False))
        s = sensitivity(policy)
        print(f"  Spearman with the deposited count      {s['spearman']:.4f}")
        print(f"  countries whose rank moves             {s['countries_whose_rank_moves']}"
              f" of {s['countries']}")
        print(f"  largest rank move                      {s['largest_rank_move']} places")
        print(f"  mean gain among corrected countries    "
              f"{s['mean_point_gain_among_corrected']:.2f} points")
        print(f"  countries entering or leaving the top ten  {s['highest_ten_changes']}")
