# Can a Language Model Measure National Laws, Strategies and Institutions Addressing the Moral Status of AI Systems?

Sentient Futures Project Incubator, 31 August to 9 November 2026, with a three-month
extension to 9 February 2027. Author Jason Hung.

Six frontier models score the same 122 countries that the completed AI Moral Status Audit
scores from administrative sources, five times each, from the training data of the scoring
model alone and again with the administrative record of the scored country supplied in the
prompt. The study reports how far a score moves when the same model scores the same country
again, when a different model scores the same country, and when the administrative record is
supplied. The six models are called through OpenRouter, a company that resells the API of each
model developer under one account and one key.

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
| `.env.example` | The two key names to copy to `.env`, which git never tracks |
| `scoring/config.py` | Models, the OpenRouter pin and route of each model, prices on both routes, the design constants, the record allow-list |
| `scoring/corrections.py` | One correction to the inherited strategy block, with the evidence |
| `scoring/record.py` | The administrative record renderer, with the contamination guard |
| `scoring/instruments.py` | The two instrument wordings and the prompt builder |
| `scoring/parse.py` | Response to one of six recorded outcomes |
| `scoring/providers.py` | One call interface for the six confirmatory models through OpenRouter and for the pilot model through Anthropic, the developer of the pilot model, plus the batch route of OpenRouter and a stub |
| `scoring/run.py` | The harness, resumable and spend-capped, on the sync route and the batch route |
| `scripts/00_select_pilot.py` | Reproduces the five pilot countries from the rule |
| `data/records/` | One rendered administrative record per country, 122 files |
| `runs/` | Append-only JSONL ledgers, one line per attempt, and beside a ledger of batch calls the manifest of every batch submitted |
| `analysis/gstudy.py` | The variance decomposition, the generalisability coefficients and the decision study, with self-tests |
| `analysis/pilot.py` | The pilot analysis of Stage B, which reads the ledgers and calls no provider |
| `results/pilot/` | Every table, figure and summary the pilot analysis writes, with a `README.md` describing every file |

## Order of work

```bash
# 1. Reproduce the pilot country selection
python scripts/00_select_pilot.py

# 2. Check the one correction to the inherited strategy block, which prints the
#    evidence and proves that a rebuild of the count reproduces the deposit exactly
python -m scoring.corrections

# 3. Render the administrative record for all 122 countries
python -m scoring.run records

# 4. Read the two prompt wordings
python -m scoring.instruments

# 5. Test the whole harness without calling any provider or spending anything.
#    The stub answers on the sync route and the batch route alike.
python -m scoring.run run --stub --countries pilot --out runs/stub_stage_b.jsonl
python -m scoring.run batch-submit --stub --countries pilot --out runs/stub_stage_b.jsonl
python -m scoring.run batch-collect --out runs/stub_stage_b.jsonl
python -m scoring.run report runs/stub_stage_b.jsonl

# 6. Confirm every confirmatory model on the public listing of OpenRouter, with
#    no key and no spending, then copy the key names to .env and type the
#    OpenRouter key after the equals sign. The -n flag never overwrites an
#    existing .env, and .gitignore excludes .env.
python -m scoring.run models
cp -n .env.example .env

# 7. Stage A of the pilot, on one cheap model outside the six, which settles the
#    instrument wording and the parse schema. Three passes ran on 2026-09-29, one
#    per instrument version, each in a separate ledger, and no further pass is
#    planned. runs/stage_a.jsonl holds version v0, runs/stage_a_v1.jsonl holds
#    version v1 and runs/stage_a_v2.jsonl holds version v2, which is the wording
#    the full run uses. Any later pass starts with 20 calls, then lifts the cap.
python -m scoring.run run --countries pilot --models claude_haiku_4_5 \
    --max-calls 20 --sleep 0.5 --out runs/stage_a_v3.jsonl
python -m scoring.run report runs/stage_a_v2.jsonl

# 8. Re-read the stored responses of a ledger under the current parse rule, which
#    calls no provider, after any change to scoring/parse.py
python -m scoring.run reparse runs/stage_a_v2.jsonl

# 9. Price the whole design from the tokens Stage A measured
python -m scoring.run budget runs/stage_a_v2.jsonl

# 10. Stage B, the six confirmatory models under the holistic wording of
#     instrument version v2. Gemini 3.1 Pro and the three open-weight models,
#     DeepSeek V4 Pro, Kimi K3 and GLM-5.2, run on the sync route. Claude Opus 5 and
#     GPT-5.6 Sol run on the batch route at half the price. First, one call per model,
#     on cells the full run would call anyway, so the full run skips the answered cells.
python -m scoring.run run --countries FRA --conditions training --temperatures 1 \
    --replicates 1 --out runs/stage_b.jsonl
python -m scoring.run batch-submit --countries FRA --conditions training \
    --temperatures 1 --replicates 1 --out runs/stage_b.jsonl
python -m scoring.run batch-collect --out runs/stage_b.jsonl   # repeat until no batch is open
python -m scoring.run report runs/stage_b.jsonl

#     Then the full 600 calls. The batches go first, because batch-submit writes
#     only the manifest, and the sync calls run while the batches wait.
python -m scoring.run batch-submit --countries pilot --spend-cap 5 --out runs/stage_b.jsonl
python -m scoring.run run --countries pilot --sleep 0.5 --spend-cap 5 --out runs/stage_b.jsonl
python -m scoring.run batch-collect --out runs/stage_b.jsonl   # repeat until no batch is open
python -m scoring.run report runs/stage_b.jsonl
python -m scoring.run budget runs/stage_b.jsonl

# 11. The pilot analysis of Stage B, which calls no provider and writes every
#     table, figure and summary into results/pilot. The analysis also reads
#     runs/stage_b_cap8000.jsonl, the checks of the cap of 8,000 output tokens,
#     whose commands are in section 8 of RESUME.md. The first command runs the
#     self-tests of the variance decomposition.
python -m analysis.gstudy
python -m analysis.pilot
```

Stage A and Stage B never share a ledger. The harness refuses a run that names both a pilot model
and a confirmatory model, and refuses a run whose role differs from the role already in the ledger
being written to, so no filtering step stands between a raw ledger and an analysis. Section 7.3 of
`PLAN.md` states what each stage settles and why Stage B cannot be replaced by Stage A at any
price.

Step six prints CONFIRMED or PROBLEM for every confirmatory model on every route the model
runs on. CONFIRMED means that, on the listing that day, the endpoint named by the pin in
`scoring/config.py` serves the model, takes `max_tokens`, writes at least as many output tokens
as the cap of the model in `scoring/config.py`, takes a temperature exactly where
`scoring/config.py` says so, and lists the price that the rule in `scoring/config.py` takes.
PROBLEM names what differs and ends the check with exit status 1. The repair is made by hand in
`scoring/config.py`, with the address of the listing and the date read in the comment, as
section 4 of RESUME.md requires. The listing is public, so the check needs no key and spends
nothing, and the check is worth rerunning on the day of every paid run, because a listed price
can change without notice.

Keys live in `.env` and nowhere else. A shell `export` reaches only the shell that runs the
export, and a key typed at a prompt also lands in the shell history file. Every command in
this package reads `.env` at import, so a key is typed once and works in every terminal. A
name already set in the environment wins over the file, so one run can use a different key
without editing anything. One OpenRouter key serves all six confirmatory models, and the
Anthropic key is needed only to rerun the Stage A pilot. A credit limit set on the OpenRouter
key at openrouter.ai caps what the key can spend, whatever any command does.

`PRICES` in `scoring/config.py` holds the price of the sync route and `BATCH_PRICES` the price of
the batch route, with the address of the listing and the date read in the comment above each
price. The six confirmatory prices were read on 2026-10-03 from the endpoint listing of OpenRouter
at the pin of each model, and the price of the pilot model was read on 2026-09-29 from the price
page of Anthropic. Where a listing shows more than one price for the same model, the comment names
every price shown and takes the higher price, because a spend cap built on the lower price would
fail to cap. GPT-5.6 Sol is therefore priced at the full price and not at the half price the
listing marks as a discount, and DeepSeek V4 Pro at the price DeepSeek charges in two blocks of
weekday hours, so a real bill comes in lower when the discount holds or a DeepSeek call falls
outside the two blocks of hours. No price includes the fee OpenRouter charges on buying credit,
5.5 cents a dollar with a minimum of 80 cents a purchase. A price is never written from memory and
never taken over from an earlier model of the same family, and step six rereads every
confirmatory price from the listing, so a changed price shows as a PROBLEM before any paid run.

The batch route sends the cells of Claude Opus 5 and GPT-5.6 Sol to OpenRouter as batches, one
model to a batch, under a completion window of 24 hours, and a batch can stay open past the
window, as the two Stage B batches of Gemini 3.1 Pro did before Gemini 3.1 Pro moved to the sync
route on 2026-10-04. `batch-submit`
writes nothing to the ledger and records every batch OpenRouter accepts in a manifest beside the
ledger, `runs/stage_b.batches.jsonl` for `runs/stage_b.jsonl`. Git tracks the manifest with the
ledger, because the manifest is the only record of what was submitted and of the charge OpenRouter
reports for each batch, and OpenRouter reports no charge for a single request inside a batch.
`batch-collect` writes the results of every finished batch into the ledger, except a result for a
cell the ledger already holds an answer for, and is safe to repeat.
A batch that failed, expired or was cancelled closes with nothing written, so the cells of the
batch return to the next `batch-submit`. A request that failed inside a finished batch is written
as a transport error and is sent again only by `batch-submit --retry-failed`. OpenRouter deletes
the results of a batch 30 days after the batch was created, so every batch is collected well
inside 30 days. OpenRouter also holds the worst-case cost of every request in flight against the
balance of the account and refuses a batch the balance cannot cover. `batch-submit` therefore
prints the worst case of every batch and submits nothing when the total is above `--spend-cap`,
and a batch refused at submission spends nothing and stops the batches after the refused batch.
`run` and `batch-collect` append to the same ledger, so the two commands are never run on one
ledger at the same time.

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
