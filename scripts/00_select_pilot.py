"""
Choose the five pilot countries by a rule written before the choice.

The rule, fixed in PLAN.md section 7.1:

  one country per quintile of the 122 countries ranked on the count of national
  action, taking the country nearest each quintile midpoint, subject to the five
  jointly covering five World Bank regions, two or three countries scored by the
  Sentience Readiness Index, at least one country in the lowest and one in the
  highest tertile of English Wikipedia visibility, at least one country scored on
  only two blocks, and at least one country where English is not an official
  language.

The search is exhaustive over the eight countries nearest each quintile midpoint,
which is 32,768 combinations, and the selection is therefore deterministic. Writes
data/pilot_countries.csv.

    python scripts/00_select_pilot.py
"""

from __future__ import annotations

import csv
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scoring import config as C           # noqa: E402

POOL_PER_BAND = 8
BANDS = 5


def load() -> list[dict]:
    wide = {r["ISO3"]: r for r in csv.DictReader(C.AUDIT_WIDE.open())}

    def num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    rows = []
    for r in csv.DictReader(C.AUDIT_INDEX.open()):
        w = wide.get(r["ISO3"], {})
        rows.append({
            "ISO3": r["ISO3"], "Country": r["Country"], "Region": r["Region"],
            "rank": int(float(r["action_rank"])), "score": float(r["action_score"]),
            "n_blocks": int(r["n_blocks"]),
            "in_sri": w.get("In_SRI") == "1",
            "english_official": w.get("English_Official") == "1",
            "vis_wikipedia": num(w.get("vis_wikipedia")),
            "patents": num(w.get("cap_patents_total_2010_2024")),
        })
    rows.sort(key=lambda d: d["rank"])
    return rows


def tertiles(rows: list[dict]) -> None:
    values = sorted(d["vis_wikipedia"] for d in rows if d["vis_wikipedia"] is not None)
    low, high = values[len(values) // 3], values[2 * len(values) // 3]
    for d in rows:
        v = d["vis_wikipedia"]
        d["vis_tertile"] = ("unknown" if v is None else
                            "low" if v <= low else "high" if v > high else "mid")
    print(f"Wikipedia visibility tertile cuts: {low:.0f} and {high:.0f}")


def select(rows: list[dict]) -> list[dict]:
    n = len(rows)
    bands, pools, midpoints = [], [], []
    for i in range(BANDS):
        band = rows[i * n // BANDS:(i + 1) * n // BANDS]
        mid = (band[0]["rank"] + band[-1]["rank"]) / 2
        bands.append(band)
        midpoints.append(mid)
        pools.append(sorted(band, key=lambda d: abs(d["rank"] - mid))[:POOL_PER_BAND])
        print(f"band {i + 1}: ranks {band[0]['rank']} to {band[-1]['rank']}, "
              f"n={len(band)}, midpoint {mid}")

    best = None
    for combo in itertools.product(*pools):
        n_sri = sum(d["in_sri"] for d in combo)
        if not 2 <= n_sri <= 3:
            continue
        tert = {d["vis_tertile"] for d in combo}
        if "low" not in tert or "high" not in tert:
            continue
        if not any(d["n_blocks"] == 2 for d in combo):
            continue
        if len({d["Region"] for d in combo}) < BANDS:
            continue
        if not any(d["english_official"] for d in combo):
            continue
        if not any(not d["english_official"] for d in combo):
            continue
        cost = sum(abs(d["rank"] - m) for d, m in zip(combo, midpoints))
        if best is None or cost < best[0]:
            best = (cost, combo)
    if best is None:
        sys.exit("no combination satisfies the rule. Do not relax the rule silently.")
    print(f"\nselected at total distance {best[0]:.1f} from the quintile midpoints")
    return list(best[1])


def main() -> None:
    rows = load()
    print(f"{len(rows)} eligible countries in {C.AUDIT_INDEX.name}")
    tertiles(rows)
    chosen = select(rows)

    fields = ["ISO3", "Country", "Region", "rank", "score", "n_blocks", "in_sri",
              "english_official", "vis_wikipedia", "vis_tertile", "patents"]
    C.PILOT_COUNTRIES.parent.mkdir(parents=True, exist_ok=True)
    with C.PILOT_COUNTRIES.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for d in chosen:
            writer.writerow({k: d[k] for k in fields})

    print()
    for d in chosen:
        print(f"  {d['ISO3']}  {d['Country']:<16} rank {d['rank']:>4}  "
              f"score {d['score']:>5.1f}  blocks {d['n_blocks']}  "
              f"{'in the Index' if d['in_sri'] else 'not in the Index':<16} "
              f"visibility {d['vis_tertile']}")
    print(f"\nwritten to {C.PILOT_COUNTRIES}")


if __name__ == "__main__":
    main()
