"""
The administrative record renderer.

Turns the action layer of the AIMSA dataset into the plain-text record that the
`record` condition supplies to a model. One country in, one block of text out.

Three rules hold, and each rule is enforced in code rather than trusted.

1. Only the columns on the allow-list in scoring/config.py are rendered. Any other
   column raises. The capability measures, the visibility measures and the
   Sentience Readiness Index scores are withheld, because supplying a capability
   measure would place the predictor of RQ3 inside the prompt and supplying a
   visibility measure would do the same for RQ2.
2. Nothing is imputed. A missing value is rendered as "not recorded" and never as
   zero, in line with the rule inherited from the completed audit.
3. The rendered text is checked against the withheld values for that country before
   the text is returned, so a leak fails loudly instead of contaminating a run.
"""

from __future__ import annotations

import pandas as pd

from . import config as C


class RecordLeak(RuntimeError):
    """The rendered record contains a value that must be withheld."""


_WIDE: pd.DataFrame | None = None


def wide() -> pd.DataFrame:
    global _WIDE
    if _WIDE is None:
        _WIDE = pd.read_csv(C.AUDIT_WIDE, dtype={"ISO3": str}).set_index("ISO3")
    return _WIDE


def eligible() -> pd.DataFrame:
    """The 122 countries the completed audit scores, with rank and block count."""
    return pd.read_csv(C.AUDIT_INDEX, dtype={"ISO3": str}).set_index("ISO3")


def _fmt(value, unit: str) -> tuple[str, str]:
    """Return the text shown to the model and the bare number inside that text.

    The bare number is kept separately so the leak check can compare withheld
    values against rendered numbers alone, rather than against boilerplate such
    as the phrase "out of 100".
    """
    if pd.isna(value):
        return "not recorded", ""
    v = float(value)
    if unit == "year":
        return str(int(v)), str(int(v))
    if unit == "count":
        return f"{int(v):,}", f"{int(v)}"
    if unit == "1 for yes, 0 for no":
        return ("yes" if v >= 0.5 else "no"), ""
    if unit == "per cent":
        return f"{v:.1f} per cent", f"{v:.1f}"
    if unit == "0-100":
        return f"{v:.2f} out of 100", f"{v:.2f}"
    return f"{v:.3f}", f"{v:.3f}"


def _withheld(iso3: str) -> list[str]:
    """Values that must not reach a prompt, as formatted strings.

    Short strings are dropped. A three-digit patent count and a three-digit
    governance score collide by chance often enough that a short match would fire
    on coincidence rather than on leakage, and the allow-list in scoring/config.py
    is what structurally prevents a capability column from being rendered at all.
    """
    row = wide().loc[iso3]
    idx = eligible()
    out = []
    for col in row.index:
        if col.startswith(("cap_", "vis_", "sri_")) and not pd.isna(row[col]):
            out.append(f"{float(row[col]):.0f}")
    if iso3 in idx.index:
        out.append(f"{float(idx.loc[iso3, 'action_score']):.2f}")
    return [s for s in out if len(s) >= 4]


def render(iso3: str, *, check: bool = True) -> str:
    """The administrative record of one country as plain text."""
    iso3 = iso3.upper()
    w = wide()
    if iso3 not in w.index:
        raise KeyError(f"{iso3} is not in {C.AUDIT_WIDE.name}")
    row = w.loc[iso3]

    unknown = C.RECORD_ALLOWED - set(w.columns)
    if unknown:
        raise KeyError(f"allow-listed columns absent from the dataset: {sorted(unknown)}")

    lines = [f"ADMINISTRATIVE RECORD FOR {row['Country'].upper()} ({iso3})", ""]
    numbers: list[str] = []
    for block, items in C.RECORD_BLOCKS:
        lines.append(f"{block}:")
        for col, label, unit in items:
            if col not in C.RECORD_ALLOWED:
                raise RecordLeak(f"{col} is rendered but not allow-listed")
            shown, bare = _fmt(row[col], unit)
            # A four-digit year collides with a four-digit patent count by
            # arithmetic and not by leakage, and a year is independently sourced,
            # so years are held out of the comparison below.
            if bare and unit != "year":
                numbers.append(bare)
            lines.append(f"  - {label}: {shown}")
        lines.append("")
    lines.append(f"Values retrieved on {row['Retrieved']}.")
    lines.append(f"Sources: {C.RECORD_SOURCES}")
    lines.append(
        "A value shown as not recorded is absent from the sources above. "
        "An absent value is not a zero."
    )
    text = "\n".join(lines)

    if check:
        rendered = " ".join(numbers)
        for bad in _withheld(iso3):
            if bad in rendered:
                raise RecordLeak(
                    f"rendered record for {iso3} contains the withheld value {bad!r}"
                )
    return text


def coverage(iso3: str) -> dict[str, int]:
    """How many allow-listed items are recorded for a country, by block."""
    row = wide().loc[iso3.upper()]
    return {
        block: int(sum(not pd.isna(row[col]) for col, _, _ in items))
        for block, items in C.RECORD_BLOCKS
    }


if __name__ == "__main__":
    import sys

    codes = sys.argv[1:] or ["FRA", "IND", "GHA", "HKG", "BRB"]
    for code in codes:
        print(render(code))
        print(f"[coverage: {coverage(code)}]")
        print("=" * 72)
