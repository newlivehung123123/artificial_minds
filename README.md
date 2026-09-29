# Can a Language Model Measure National Laws, Strategies and Institutions Addressing the Moral Status of AI Systems?

Sentient Futures Project Incubator, 31 August to 9 November 2026, with a three-month
extension to 9 February 2027. Author Jason Hung.

Six frontier models score the same 122 countries that the completed AI Moral Status Audit
scores from administrative sources, five times each, from the training data of the scoring
model alone and again with the administrative record of the scored country supplied in the
prompt. The study reports how far a score moves when the same model scores the same country
again, when a different model scores the same country, and when the administrative record is
supplied.

**Read [RESUME.md](RESUME.md) first**, for the state of the work, every decision already taken
and the rules that govern how work on this project is done. **Then read [PLAN.md](PLAN.md).**
Every design choice carries a status label of FIXED, OPEN or FROZEN, and the plan states the one
rule that makes the open choices defensible, namely that no pilot score enters any confirmatory
analysis.

## What is inherited and never rebuilt here

The count of national action for 122 countries, the eligibility rule, the four blocks and the
20 constructions all come from the completed audit at
`/Users/newlivehung/Desktop/18. Yale DECS 2026`, deposited at
https://doi.org/10.7910/DVN/YQNFYI. This repository reads those files and never writes to
them.

## Layout

| Path | Holds |
|---|---|
| `RESUME.md` | The state of the work, every decision taken, and the standing rules |
| `PLAN.md` | The analysis plan, with a status label on every choice |
| `.env.example` | The six key names to copy to `.env`, which git never tracks |
| `scoring/config.py` | Providers, models, prices, the design constants, the record allow-list |
| `scoring/corrections.py` | One correction to the inherited strategy block, with the evidence |
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

# 2. Check the one correction to the inherited strategy block, which prints the
#    evidence and proves that a rebuild of the count reproduces the deposit exactly
python -m scoring.corrections

# 3. Render the administrative record for all 122 countries
python -m scoring.run records

# 4. Read the two candidate prompt wordings
python -m scoring.instruments

# 5. Test the whole harness without calling any provider or spending anything
python -m scoring.run run --stub --countries pilot --out runs/stub_test.jsonl
python -m scoring.run report runs/stub_test.jsonl

# 6. Put the keys in .env, then confirm every API identifier against each
#    provider's own model listing
cp .env.example .env          # paste one key per line, .gitignore excludes .env
python -m scoring.run models
python -m scoring.run models --providers anthropic,openai   # or a few at a time

# 7. Stage A of the pilot, on one cheap model outside the six, which settles the
#    instrument wording and the parse schema. Start with 20 calls, then lift the cap.
#    One pass ran on 2026-09-29 under instrument version v0 and is kept in
#    runs/stage_a.jsonl. A pass under the current wording writes a new ledger.
python -m scoring.run run --countries pilot --models claude_haiku_4_5 \
    --max-calls 20 --sleep 0.5 --out runs/stage_a_v1.jsonl
python -m scoring.run report runs/stage_a_v1.jsonl

# 8. Re-read the stored responses of a ledger under the current parse rule, which
#    calls no provider, after any change to scoring/parse.py
python -m scoring.run reparse runs/stage_a.jsonl

# 9. Price the whole design from the tokens Stage A measured
python -m scoring.run budget runs/stage_a.jsonl

# 10. Stage B, the six confirmatory models under the wording Stage A chose.
#     The wording below is holistic only as an example. Stage A decides.
python -m scoring.run run --countries pilot --instruments holistic \
    --max-calls 60 --sleep 0.5 --out runs/stage_b.jsonl
python -m scoring.run budget runs/stage_b.jsonl
```

Stage A and Stage B never share a ledger. The harness exits rather than writing a pilot score
and a confirmatory score into one file, so no filtering step stands between a raw ledger and an
analysis. Section 7.3 of `PLAN.md` states what each stage settles and why Stage B cannot be
replaced by Stage A at any price.

Step six reports one of three outcomes for every identifier. CONFIRMED means the provider
serves that identifier. NOT SERVED means the identifier in `scoring/config.py` is wrong, and
the identifiers the provider does serve are printed underneath, so the repair is a copy from
the listing. NO KEY means the identifier was never checked, because no key for that provider
is in `.env`, and `scoring/config.py` may be perfectly correct. No identifier is treated as
correct until a listing confirms the identifier.

Keys live in `.env` and nowhere else. A shell `export` reaches only the shell that runs the
export, and a key typed at a prompt also lands in the shell history file. Every command in
this package reads `.env` at import, so a key is typed once and works in every terminal. A
name already set in the environment wins over the file, so one run can use a different key
without editing anything.

Fill `PRICES` in `scoring/config.py` by hand from each provider's published price page, with
the date read. Until a price is filled in, token counts are recorded and cost is left blank,
so no cost figure in any report is invented.

## Two guarantees the code enforces rather than trusts

**No contamination.** The rendered record carries the action layer only. Capability measures,
visibility measures, Sentience Readiness Index scores and both counts of national action are
withheld, because supplying a capability measure would place the predictor of RQ3 inside the
prompt, supplying a visibility measure would do the same for RQ2, and supplying either count of
national action would place the outcome of RQ1 inside the prompt. `scoring/record.py` renders an
allow-list and then checks the rendered numbers against the withheld values, and raises rather
than returning a record that leaks.

**No silent imputation.** A value absent from the sources renders as "not recorded" and never
as zero. A response that does not parse is recorded under one of six named outcomes and is
never replaced by a retry presented as a first attempt.
