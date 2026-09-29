# Can a Language Model Measure National Laws, Strategies and Institutions Addressing the Moral Status of AI Systems?

Sentient Futures Project Incubator, 31 August to 9 November 2026, with a three-month
extension to 9 February 2027. Author Jason Hung.

Six frontier models score the same 122 countries that the completed AI Moral Status Audit
scores from administrative sources, five times each, from the training data of the scoring
model alone and again with the administrative record of the scored country supplied in the
prompt. The study reports how far a score moves when the same model scores the same country
again, when a different model scores the same country, and when the administrative record is
supplied.

**Read [PLAN.md](PLAN.md) first.** Every design choice carries a status label of FIXED, OPEN
or FROZEN, and the plan states the one rule that makes the open choices defensible, namely
that no pilot score enters any confirmatory analysis.

## What is inherited and never rebuilt here

The count of national action for 122 countries, the eligibility rule, the four blocks and the
20 constructions all come from the completed audit at
`/Users/newlivehung/Desktop/18. Yale DECS 2026`, deposited at
https://doi.org/10.7910/DVN/YQNFYI. This repository reads those files and never writes to
them.

## Layout

| Path | Holds |
|---|---|
| `PLAN.md` | The analysis plan, with a status label on every choice |
| `scoring/config.py` | Providers, models, prices, the design constants, the record allow-list |
| `scoring/record.py` | The administrative record renderer, with the contamination guard |
| `scoring/instruments.py` | The two candidate instruments and the prompt builder |
| `scoring/parse.py` | Response to one of six recorded outcomes |
| `scoring/providers.py` | One call interface across six providers, plus a stub |
| `scoring/run.py` | The harness, resumable and spend-capped |
| `scripts/00_select_pilot.py` | Reproduces the five pilot countries from the rule |
| `data/records/` | One rendered administrative record per country, 122 files |
| `runs/` | Append-only JSONL ledgers, one line per attempt |

## Order of work

```bash
# 1. Reproduce the pilot country selection
python scripts/00_select_pilot.py

# 2. Render the administrative record for all 122 countries
python -m scoring.run records

# 3. Read the two candidate prompt wordings
python -m scoring.instruments

# 4. Test the whole harness without calling any provider or spending anything
python -m scoring.run run --stub --countries pilot --out runs/stub_test.jsonl
python -m scoring.run report runs/stub_test.jsonl

# 5. Confirm every API identifier against each provider's own model listing
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=...
export DEEPSEEK_API_KEY=... MOONSHOT_API_KEY=... ZAI_API_KEY=...
python -m scoring.run models

# 6. Run the pilot, capped, one provider at a time while costs are unknown
python -m scoring.run run --countries pilot --models claude_opus_5 \
    --max-calls 20 --sleep 0.5 --out runs/pilot.jsonl
python -m scoring.run report runs/pilot.jsonl
```

Step five will report NOT FOUND for any identifier in `scoring/config.py` that a provider does
not serve, and will print candidate identifiers from the listing. No identifier in the config
is treated as correct until the listing confirms the identifier.

Fill `PRICES` in `scoring/config.py` by hand from each provider's published price page, with
the date read. Until a price is filled in, token counts are recorded and cost is left blank,
so no cost figure in any report is invented.

## Two guarantees the code enforces rather than trusts

**No contamination.** The rendered record carries the action layer only. Capability measures,
visibility measures and Sentience Readiness Index scores are withheld, because supplying a
capability measure would place the predictor of RQ3 inside the prompt and supplying a
visibility measure would do the same for RQ2. `scoring/record.py` renders an allow-list and
then checks the rendered numbers against the withheld values, and raises rather than returning
a record that leaks.

**No silent imputation.** A value absent from the sources renders as "not recorded" and never
as zero. A response that does not parse is recorded under one of six named outcomes and is
never replaced by a retry presented as a first attempt.
