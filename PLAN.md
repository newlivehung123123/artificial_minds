# Analysis plan

**Project.** Can a Language Model Measure National Laws, Strategies and Institutions
Addressing the Moral Status of AI Systems?

**Programme.** Sentient Futures Project Incubator, 31 August to 9 November 2026, with a
three-month extension from 10 November 2026 to 9 February 2027.

**Author.** Jason Hung.

**Status of this document.** DRAFT. Not yet frozen. Every item below carries one of three
status labels, and the document is frozen only when no item carries OPEN.

| Label | Meaning |
|---|---|
| FIXED | Inherited from the completed audit and the deposited AIMSA codebook. Cannot be changed without contradicting a published deposit. |
| OPEN | Not yet decided. The five-country pilot decides the item. |
| FROZEN | Decided after the pilot, recorded here, and not changed afterwards. |

**The one rule that makes the OPEN items defensible.** No score collected in the pilot
enters any confirmatory analysis. The pilot exists to choose the prompt wording, the parse
rules and the temperature. Once the choices are recorded here and this document is tagged,
the full run starts from zero on fresh calls. Choosing a prompt after reading model output
therefore costs nothing, because no pilot score answers a research question.

---

## 1. Research questions

Stated in the funded proposal and not revisable.

**RQ1.** Is a model's score for a country stable across repeated scoring by the same model
and across models?

**RQ2.** Is the difference between a model's score and the count of national action
associated with how much English-language material exists about a country's AI policy?

**RQ3.** Does a model's score follow the AI patents and private AI investment of a country
more closely than the count of national action does?

---

## 2. The count of national action — FIXED

Built by `scripts/10_action_index.py` in the Yale DECS 2026 project and deposited at
https://doi.org/10.7910/DVN/YQNFYI. Nothing below is revisable.

- **Units.** Countries and territories by ISO3 code. The European Union is dropped, because
  the European Union is not a country and every member state is already present.
- **Blocks.** Four, namely governance, legislation, strategy and institutional readiness.
  Public attitude items are excluded, because an attitude is not an act of government.
- **Eligibility.** A country is scored where at least two of the four blocks are present and
  at least one of the two present blocks is governance or legislation. Of the 183 countries
  holding any action record, 122 qualify, and all 30 countries scored by the Sentience
  Readiness Index are among the 122.
- **Direction.** A measure running against the block of that measure is flipped and not
  dropped, with polarity recorded in the `Direction` column of the deposited dataset.
- **Scaling.** Each measure scaled from zero to 100 by the minimum and the maximum across the
  122 eligible countries.
- **Aggregation.** Measures averaged within a block, then blocks averaged.
- **Missing blocks.** A country is scored on the blocks present for that country, with weight
  spread across the blocks present, and the number of contributing blocks reported beside
  every ranking claim.
- **Imputation.** None, at any stage. No missing value is written as zero.

## 3. The 20 constructions — FIXED

Already computed for all 122 countries in `data/processed/AIMSA_action_variants.csv` of the
Yale DECS 2026 project. Every construction is named by the column holding the construction,
so a reader reproduces any construction from the deposited file without reading code.

| Group | Columns | Count |
|---|---|---|
| Four scalings crossed with three weightings | `headline` (min-max and equal), `minmax_coverage`, `minmax_pca`, `rank_equal`, `rank_coverage`, `rank_pca`, `zscore_equal`, `zscore_coverage`, `zscore_pca`, `log_minmax_equal`, `log_minmax_coverage`, `log_minmax_pca` | 12 |
| Three uses of the governance block | `gov_overall_only`, `gov_pillars_only`, `gov_dimensions_only` | 3 |
| Four runs each removing one block | `without_governance`, `without_legislation`, `without_strategy`, `without_institutional` | 4 |
| One run restricted to countries scored on three or more blocks | `three_or_more_blocks` | 1 |
| **Total** | | **20** |

Note for the write-up. `docs/RESEARCH_DESIGN.md` of the Yale DECS 2026 project states three
scalings at line 105, written before `log_minmax` was added. The deposited variants file and
the funded proposal both carry four scalings, and four scalings is correct.

## 4. Scoring design

### 4.1 Models — FIXED

Six frontier models, three closed-weight models built in the United States and three
open-weight models built in China.

| Key | Model | Developer | Weights |
|---|---|---|---|
| `claude_opus_5` | Claude Opus 5 | Anthropic | closed |
| `gpt_5_6_sol` | GPT-5.6 Sol | OpenAI | closed |
| `gemini_3_1_pro` | Gemini 3.1 Pro | Google DeepMind | closed |
| `deepseek_v4_pro` | DeepSeek V4 Pro | DeepSeek | open |
| `kimi_k3` | Kimi K3 | Moonshot AI | open |
| `glm_5_2` | GLM-5.2 | Z.ai | open |

The exact API identifier of every model is confirmed against the model listing of the
provider before the pilot, by `python -m scoring.run models`, and the confirmed identifier and
the version string returned by every call are recorded with every score. No identifier in
`scoring/config.py` is treated as correct until the listing confirms the identifier.

### 4.2 Conditions — FIXED

| Key | Prompt content |
|---|---|
| `training` | The country name only. The model scores from the training data of the model alone. |
| `record` | The country name and the administrative record of that country, rendered by `scoring/record.py`. |

The incubator period collects the `training` condition for all 122 countries, giving 3,660
scores. The extension collects the `record` condition, giving a further 3,660 scores and
7,320 in total.

### 4.3 Replicates — FIXED

Five per country, per model, per condition, per instrument.

### 4.4 Instrument — OPEN

Two candidate wordings are piloted on the same five countries, and one is frozen as primary.

**Instrument A, holistic.** The model returns one score from zero to 100 for preparation for
the possibility that AI systems have moral status. Instrument A reproduces the way the
Sentience Readiness Index was produced, so Instrument A audits the practice the research paper
criticises. Comparison with the count of national action is by rank only, because a holistic
score and a min-max composite share no scale.

**Instrument B, itemised.** The model returns the reproducible administrative facts, namely
whether a national AI strategy has been released and in which year, how many AI bills have
passed into law, how many mentions of AI are recorded in legislative proceedings, whether a
national AI institution exists, and whether any national instrument addresses the moral
status of AI systems. Instrument B supports item-level accuracy against the administrative
record and not rank agreement alone.

Reason for piloting both. The Digital Minds Research Sprint study found 87.6 per cent of the
variance separating one model from another in the combination of the model, the prompt format
and the outcome, so a design carrying one prompt format cannot estimate how much the prompt
format contributes, and a reliability figure from one prompt format is optimistic by an
unknown amount. If the measured cost of the pilot allows, both instruments are carried into
the full run and the instrument enters the reliability design as a facet.

Why Instrument B cannot ask for a block score. The block scores of the count are min-max
scaled across the 122 eligible countries, so a block score is undefined for any respondent
who does not hold the 122-country reference set. Instrument B therefore asks for the
administrative facts, and the same scaling code converts model-supplied facts and
record-supplied facts alike.

### 4.5 Temperature — OPEN

Research question one asks whether a score is stable across repeated scoring by the same
model. At temperature zero several providers return near-identical text, so a reliability
figure computed from five replicates at temperature zero would look high for a reason
unrelated to the measurement being reliable. The pilot runs replicates at temperature zero
and at one stated non-zero temperature, and the frozen plan states which setting the full run
uses and why.

### 4.6 Contamination safeguards — FIXED

The rendered administrative record carries the action layer of the dataset only. The record
never carries the count of national action, the rank of the country, any score or rank from
the Sentience Readiness Index, any capability measure such as AI patents or private AI
investment, or any visibility measure. Supplying a capability measure would place the
predictor of RQ3 inside the prompt, and supplying a visibility measure would do the same for
RQ2. `scoring/record.py` enforces the restriction by an allow-list of columns and fails
rather than rendering an unlisted column.

---

## 5. Parse rules — OPEN

Every response is parsed to one of six outcomes, and every outcome is counted and reported.

| Outcome | Meaning |
|---|---|
| `ok` | Valid structured output satisfying the schema of the instrument. |
| `json_absent` | No structured output found in the response. |
| `json_invalid` | Structured output found and not parsable. |
| `schema_violation` | Structured output parsable and failing the schema of the instrument. |
| `refusal` | The model declined to answer. |
| `empty` | No content returned. |

A response that never arrives cannot be parsed, so a failure of the call itself is recorded as
`transport_error` and reported on a line of its own, outside the six. A key absent from `.env`
is not a transport error and is never written to a ledger, because a key absent from a file is a
fault in the environment of the run and says nothing about a model. The harness stops before
writing a line when a key for a named model is absent.

Fixed now. A response that does not parse to `ok` is never replaced by a retry that is then
treated as the first attempt. A retry is recorded as a separate attempt with the reason for
the retry. Nothing is imputed, in line with section 2.

Settled by Stage A on 2026-09-29. A value of the wrong type whose meaning is unambiguous is
converted, a numeric field returned as text and a boolean field returned as the string `"true"`
alike, and every conversion is named in a `coerced` list on the parsed row. One rule applies to
both wordings, because an earlier rule converted a numeric string in the holistic score field
and refused a boolean string in an itemised field, which held the two wordings to different
strictness and made a comparison between the two wordings unfair to the itemised wording. A
response needing a conversion is counted separately from a response that followed the schema
exactly, so the rate at which a model returns the right answer in the wrong type is reported
rather than absorbed. Section 7.4 gives both counts for Stage A.

A parse rule is applied by re-reading the stored responses in a ledger and never by calling a
provider again. `scoring.run reparse` writes a parse table beside the ledger, names the parser
version in the file name and in every row, and leaves the append-only ledger unmodified,
because a ledger records what a provider returned and that record does not change when a parse
rule changes.

Open now. The exact schema of each instrument, and whether a refusal is treated as missing or
as a substantive outcome for the purposes of RQ1.

---

## 6. Analysis rules

### 6.1 Inherited and FIXED

- Rank correlations reported as Spearman's rho and Kendall's tau, with intervals from the
  Fisher z transformation and from the bootstrap.
- Two dependent correlations compared by Williams's test.
- Every ranking claim reported with the range that claim takes across the 20 constructions.
- Nothing imputed.
- A null result on a comparison limited to the 30 countries shared with the Sentience
  Readiness Index is reported as an underpowered null, because simulation at 30 countries puts
  power at 0.34 for a rank correlation of 0.3.

### 6.2 New and OPEN

Never written before, because the completed audit never called a model. Each item below is
written out in full before the full run starts.

1. The reliability design for RQ1. The facets are country, model, replicate, condition and,
   if both instruments are carried, instrument. The variance components to be estimated, the
   generalisability coefficient to be reported, and the decision study to be run, all follow
   the design already coded for the Digital Minds Research Sprint study, and the design is
   restated here in full rather than referenced.
2. The estimand of RQ2, namely the definition of the difference between a model's score and
   the count of national action, given that Instrument A supports rank comparison only.
3. The model specification of RQ2, including whether region and total AI capability enter as
   controls, following the stage-three specification of the completed audit.
4. The comparison of RQ3, namely which correlation is compared with which and by what test.
5. The treatment of multiplicity across the 20 constructions, stating whether the headline
   construction carries the confirmatory test and the remaining 19 constructions are reported
   as a robustness range.
6. The treatment of refusals and parse failures in every analysis.
7. The decision rule for each research question, stated so that the result can disagree with
   the expectation.

---

## 7. The pilot

### 7.1 Country selection — FIXED

Five countries, chosen by a rule written before the choice and reproduced by
`scripts/00_select_pilot.py`. One country per quintile of the 122 countries ranked on the
count of national action, taking the country nearest each quintile midpoint, subject to the
five jointly covering five World Bank regions, two or three countries scored by the Sentience
Readiness Index, at least one country in the lowest and one in the highest tertile of English
Wikipedia visibility, at least one country scored on only two blocks, and at least one country
where English is not an official language.

| ISO3 | Country | Rank of 122 | Count | Blocks | In the Index | Wikipedia visibility | AI patents |
|---|---|---|---|---|---|---|---|
| FRA | France | 12 | 60.3 | 3 | yes | 655, high | 9,531 |
| IND | India | 37 | 49.8 | 3 | yes | 766, high | 2,067 |
| GHA | Ghana | 61 | 39.3 | 2 | no | 114, mid | no record |
| HKG | Hong Kong | 85 | 18.1 | 2 | no | 395, high | 1,271 |
| BRB | Barbados | 111 | 1.6 | 2 | no | 61, low | 307 |

Hong Kong is one of the six jurisdictions the proposal names as holding many AI patents while
sitting below the median on the count of national action, and the Sentience Readiness Index
does not score Hong Kong.

### 7.2 What the pilot measures

1. Cost per call by provider, by condition and by instrument, from recorded token counts.
2. The projected cost of all 3,660 scores of the `training` condition.
3. The rate of each of the six parse outcomes, by provider.
4. Whether replicates differ at temperature zero and at the stated non-zero temperature.
5. A generalisability coefficient on pilot data alone, reported as a pilot figure that no
   confirmatory analysis uses.

### 7.3 Stages and size — FIXED 2026-09-29

The pilot runs in two stages, and the arithmetic of every stage is held in `STAGES` in
`scoring/config.py` and printed by `python -m scoring.run budget`.

| Stage | Models | Calls | What the stage settles |
|---|---|---|---|
| A | one cheap model outside the six | 200 | The instrument wording of section 4.4 and the parse schema of section 5 |
| B | the six confirmatory models | 600 | Cost per call, parse outcome rate, replicate variation and temperature, so sections 7.2.1, 7.2.3, 7.2.4 and 7.2.5 |
| C | the six confirmatory models | 7,320 | The study the proposal reports |

Stage A runs on a model the study never reports, which is stronger than running Stage A on one
of the six. A wording chosen on a reported model could have been chosen, however
unintentionally, to suit that model. A wording that a small model returns as valid JSON is
also returned as valid JSON by a larger model of the same family, so Stage A is the harder test
of a wording as well as the cheaper test.

Refusal rate, token count and replicate variation do not transfer between models, so Stage B
cannot be replaced by Stage A at any price. Stage B is also where a model that emits reasoning
tokens reveals the true output cost of the design, before Stage C commits 7,320 calls.

The harness refuses to write pilot scores and confirmatory scores into one ledger, so no
filtering step stands between a raw ledger and an analysis.

### 7.4 What Stage A measured — 2026-09-29

Stage A ran the full 200 calls on Claude Haiku 4.5, five pilot countries by two wordings by
two conditions by two temperatures by five replicates, recorded in `runs/stage_a.jsonl`. Every
figure below is read from that ledger.

**Parse outcome.** The holistic wording returned 100 valid responses out of 100, under both
conditions and at both temperatures. The itemised wording returned 94 out of 100 as first
recorded, and 99 out of 100 once one parse rule was applied to both wordings, of which five
responses carried the right answer in the wrong type. The one remaining failure is malformed
JSON the model wrote around a free-text institution name, `"AI for Humanity" (Artificial
Intelligence for Humanity initiative)`, where a parenthesis sits outside the closing quotation
mark. Every one of the six failures occurred at temperature one. Temperature zero returned 100
valid responses out of 100 across both wordings.

**Temperature zero was exactly deterministic, which couples section 4.5 to the replicate
count.** All 20 cells at temperature zero returned an identical score five times over, a
standard deviation of zero in every cell. Five replicates at temperature zero are therefore
five identical calls and carry no replicate variance, so a generalisability analysis that needs
a replicate variance component needs a non-zero temperature. Stage C as tabulated is 7,320
calls at one temperature with five replicates, and at temperature zero 5,856 of those calls buy
nothing. The choice of temperature and the choice of replicate count are one decision and move
Stage C by a factor of five. Determinism was observed on one model at one provider and does
not transfer, which is why Stage B measures replicate variation on all six.

**Supplying the administrative record moved the ordering towards the count of national
action.** The count of national action orders the five pilot countries France, India, Ghana,
Hong Kong, Barbados. Scoring from training data alone the model ordered France, Hong Kong,
India, Barbados, Ghana, placing Ghana last where the count of national action places Ghana
third of the five at rank 61 of 122. Supplying the record the model ordered France, India,
Hong Kong, Ghana, Barbados. India gained most, from a mean of 15.0 to a mean of 28.0 at
temperature zero. Supplying the record also removed every low-confidence answer, from 20 low,
59 medium and 20 high under training data alone to zero low, 33 medium and 62 high.

**The holistic scale collapsed into the bottom quarter, which threatens research question
one.** Across 100 holistic calls the model emitted nine distinct scores, 2, 5, 8, 12, 15, 18,
22, 25 and 28, on a scale running to 100. The anchors ask the model to use the whole range and
place 100 at a comprehensive legal and institutional framework already in force, which no
country holds, so every country lands near the floor. Barbados and Ghana tied at 5.0 under
training data alone. Across 122 countries a nine-value scale ties heavily and a rank
correlation with the count of national action would be decided by how ties are broken. The
anchors need rewriting into reachable steps before Stage B fixes a wording, and the rewrite is
a change to section 4.4.

**Under the record condition the itemised wording became transcription.** The itemised answers
reproduced the supplied table exactly, France at nine bills passed against nine in the record,
India at one bill passed against one in the record, and a strategy year of 2018 against 2018 in
the record for France and for India. Item-level accuracy for the itemised wording under the
record condition therefore measures whether a model can copy a table, and carries no
information about what a model knows.

**A self-contradictory record reached the prompt for 18 of the 122 countries.** The record
rendered for Ghana states that release of a national AI strategy is not recorded and that the
year of release is not recorded, and on the next line gives alignment of the national AI
strategy with the OECD AI Principles as 0.640. An alignment score exists for a strategy whose
release is not recorded. The same pattern holds for Belgium, Burkina Faso, Bolivia, Ethiopia,
Ghana, Jordan, Kuwait, Lebanon, Morocco, Mali, Malaysia, Nigeria, Nicaragua, Pakistan,
Senegal, Taiwan, Uganda and Uzbekistan, which is 18 of the 122 eligible countries. Resolving
the inconsistency in the inherited audit is a precondition for the record condition of Stage C.

---

## 8. Deposit

All 7,320 scores, with every prompt, every model version string and every raw output,
deposited on Harvard Dataverse beside the AIMSA dataset. The long-format schema of the AIMSA
deposit already reserves a `Model_Score` value for the `Layer` column, so the scores stack
with the existing deposit without a schema change.

---

## 9. Change log

| Date | Change |
|---|---|
| 2026-09-29 | Document created. Sections 2, 3, 4.1, 4.2, 4.3, 4.6, 6.1 and 7.1 set to FIXED. Sections 4.4, 4.5, 5 and 6.2 set to OPEN. |
| 2026-09-29 | Operational only, no design choice touched. Keys moved to a `.env` file that git never tracks, and `scoring.run models` now separates a wrong identifier from an unchecked identifier. |
| 2026-09-29 | Section 5 gained the standing of `transport_error`, which sits outside the six parse outcomes, and the rule that a missing key is never written to a ledger. A run with 20 calls and no key had written 20 rows reading `transport_error` into an append-only record, and the harness now stops before the first line. |
| 2026-09-29 | Section 7.3 rewritten. The pilot splits into Stage A on one cheap model outside the six, which settles the instrument wording and the parse schema, and Stage B on the six confirmatory models, which settles what does not transfer between models. Stage A lowers the cost of the pilot and removes the possibility that a wording was chosen to suit a reported model. |
| 2026-09-29 | Stage A ran in full, 200 calls on Claude Haiku 4.5. Section 7.4 added, recording what the 200 calls measured. Section 5 settled the tolerance for a value of the wrong type and the rule that a parse rule is applied by re-reading a ledger rather than by calling a provider again. Sections 4.4 and 4.5 stay OPEN, and Stage A has changed what each section has to decide. Section 4.4 now has to rewrite the holistic anchors, because the model used nine distinct values between 2 and 28 on a scale running to 100. Section 4.5 now has to be decided together with the replicate count, because temperature zero was exactly deterministic and five replicates at temperature zero carry no replicate variance. |
| 2026-09-29 | Operational only, no design choice touched. `scoring.run budget` had averaged token counts over whichever calls a ledger held, and the harness walks the grid in a fixed order, so the first 20 calls of Stage A were all the holistic wording under the training condition, which carries no administrative record and is the shortest prompt in the design. The projection for Stage C therefore read 1.54 million input tokens where the four prompt cells give roughly 3.2 million. The command now holds one mean for each instrument and condition pair and reports a stage as unmeasured rather than projecting a stage from the cells that happen to be present. |
