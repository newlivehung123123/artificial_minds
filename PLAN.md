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

### 2.1 One correction to the inherited strategy block — FIXED 2026-09-29

The construction rules above are not revisable and none of them changes. One input to the
rules is corrected, the correction is applied to a copy held in memory, and the deposited
files are never written to. `scoring/corrections.py` holds the correction and the evidence,
and `python -m scoring.corrections` prints every corrected record with the reason.

**The defect.** The strategy block holds two measures, both from the Stanford AI Index.
"Released National Strategy On AI" carries one observation for each of 76 countries, in years
2017 to 2022, with value 1 for 62 countries and value 0 for 14 countries. "Alignment of
National AI Strategy with OECD AI Principles" carries one observation for each of 55
countries, all in 2024. The first measure records a release during one stated year and not a
standing status, so a country carrying value 0 in 2021 is a country for which the Stanford AI
Index reports no release during 2021, which is a weaker statement than the statement that the
country holds no national AI strategy. An alignment score is a cosine similarity between the
text of a national AI strategy and the text of the OECD AI Principles, so an alignment score
exists only where a strategy document exists, and the alignment measure therefore carries the
release information the first measure is missing. Among the 122 eligible countries the two
measures disagree for 18 countries. Five countries carry value 0 beside an alignment score,
which is a contradiction inside one dataset, namely Belgium, Jordan, Morocco, Nigeria and
Uzbekistan. Thirteen countries carry no release observation beside an alignment score, namely
Burkina Faso, Bolivia, Ethiopia, Ghana, Kuwait, Lebanon, Mali, Malaysia, Nicaragua, Pakistan,
Senegal, Taiwan and Uganda.

**The correction.** A release value of 1 is set for all 18 countries, on the evidence of the
alignment score. No release year is written for any of the 18 countries, because the year a
strategy was published is genuinely unknown and writing a year would replace a defect with an
invention. A release year is also withheld for 14 countries whose deposited release flag is
zero, because the year beside a flag of zero is the year the Stanford AI Index covers and not
a year of publication. Israel is the clearest case of the second rule and Jordan of both
rules together. Israel carries a flag of zero beside the year 2022, so printing 2022 as a
year of publication would contradict the flag printed above the year. Jordan carries a flag
of zero in 2022, so correcting the flag to 1 while keeping 2022 would claim a Jordanian
strategy published in the one year the source says no Jordanian release was reported.

**Why all 18 and not the five contradictions alone.** Identical evidence appears in both
groups, namely an alignment score with no release event recorded, so treating the two groups
differently would itself be a defect. `scoring/corrections.py` implements the conservative
policy as well under the name `contradictions`, and both policies are reported below, so a
reader who prefers the conservative reading can see what the conservative reading gives.

**Why the correction is not confined to the prompt.** Research question one compares a model
score against the count of national action for the same country, so a defect in the strategy
block moves the comparison target and not only the rendered record. `scoring/corrections.py`
rebuilds the count by loading `scripts/10_action_index.py` from the Yale DECS 2026 project and
calling the functions of that script on corrected input, so the rebuilt count is the audit's
own arithmetic and not a second implementation that happens to agree. Rebuilt with no
correction applied, the count reproduces the deposited `action_score` column for all 122
countries with a largest absolute difference of 0.0000000000, which is what licenses using a
corrected rebuild anywhere. Research question one compares against the corrected count, and
the deposited count is withheld from every prompt alongside the corrected count.

**How far the count moves.**

| | Correct five contradictions | Correct all 18 |
|---|---|---|
| Spearman correlation with the deposited count | 0.9781 | 0.9731 |
| Countries whose rank changes | 60 of 122 | 69 of 122 |
| Largest rank movement | 47 places | 46 places |
| Mean gain among corrected countries | 20.83 points | 10.60 points |
| Countries entering or leaving the highest ten | 0 | 1 |

A rank correlation of 0.9731 reads as a small change and the largest single movement is 46
places out of 122, so the summary figure and the individual figure say different things and
both are reported. Jordan moves 46 places under the correction of all 18 records and
Uzbekistan 45.

**What this repair does not do.** The deposited dataset is unchanged and the Yale DECS 2026
paper is unchanged. Whether that paper is corrected, and whether a corrected version of the
count is deposited, is a separate decision that belongs to that paper and not to this study.

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

**The holistic anchors were rewritten on 2026-09-29, and the choice between Instrument A and
Instrument B stays OPEN.** Stage A ran the version v0 anchors and Claude Haiku 4.5 returned
exactly nine distinct scores, namely 2, 5, 8, 12, 15, 18, 22, 25 and 28. Nine values rising in
steps of three or four is a ladder, and a ladder loses rank information, because two countries
differing slightly land on one rung. Barbados and Ghana both scored 5.0 under the training
condition for that reason. Three changes were made and version v1 carries all three.

The scale now names a middle point as well as the two ends. Version v0 defined zero and 100
and nothing between the two, and the definition of 100 was a comprehensive framework already
in force, which no country holds, so the upper half of the scale had no reachable meaning and
the model built a private ladder in the lower half instead.

The score is now asked for to one decimal place, which lets a model separate two countries
whose difference is smaller than one rung.

The instruction to use the whole range is removed. The Sentience Readiness Index, published by
Rost (2026) and held in the inherited dataset as `sri_overall`, scores its 30 countries
between 14.25 and 49.00 on a scale of zero to 100, with a mean of 32.57. A human index
occupying the lower half of a scale running to 100 is the practice Instrument A reproduces, so
an instruction to spread scores across the whole range asks a model for something the audited
practice does not do. How far a model compresses the scale is a property this study measures,
and an instruction to spread the scores would measure compliance with the instruction instead.
The ceiling Stage A produced, namely 28 for France against a human maximum of 49, is therefore
reported as a finding and is not treated as a fault to be prompted away.

### 4.5 Temperature and replicate count — FIXED 2026-09-29

The full run uses temperature one and five replicates. Stage A decided the two together,
because one setting makes the other meaningless.

At temperature zero the scored value did not vary at all. Across the 100 calls Stage A made at
temperature zero, all 20 cells of five replicates returned one identical value, the
within-cell standard deviation of the holistic score was 0.000 in all 10 holistic cells, and
all 10 itemised cells returned identical facts. Five replicates at temperature zero would
therefore carry no replicate variance, the variance component for replicates would be zero by
construction rather than by measurement, and a generalisability coefficient computed on that
design would be high for a reason unrelated to the measurement being reliable, which is the
failure section 4.5 existed to prevent.

Determinism of the scored value is not determinism of the response. Three of the 20 cells at
temperature zero returned more than one distinct response text, up to three distinct texts in
one cell, while the parsed value stayed the same, so the variation fell in the justification
wording and not in the score. The claim this study can make about temperature zero is that the
measured score was deterministic, and not that the model was.

At temperature one the scored value did vary, which is what a replicate facet needs. Seven of
the 10 holistic cells returned more than one score, the mean within-cell standard deviation of
the holistic score was 1.689 points and the largest was 4.45 points, and four of the 10
itemised cells returned more than one set of facts.

Temperature one therefore carries the replicates, and five replicates are kept. The cost of
the choice is accepted openly and is already measured. All six parse failures Stage A recorded
fell at temperature one, namely five schema violations and one invalid JSON object against 94
valid responses, and temperature zero returned 100 valid responses out of 100. A parse failure
at temperature one is recorded as a measured property of the instrument and the model rather
than treated as a fault of the run. Section 5 states how a failure is recorded and
`scoring/parse.py` counts every outcome, so a reliability figure is never computed on the
responses that happened to parse.

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

**The scored value was deterministic at temperature zero, which couples section 4.5 to the
replicate count.** All 20 cells at temperature zero returned an identical value five times
over, a standard deviation of zero in every one of the 10 holistic cells and identical facts in
every one of the 10 itemised cells. Five replicates at temperature zero therefore carry no
replicate variance, so a generalisability analysis that needs a replicate variance component
needs a non-zero temperature. Stage C as tabulated is 7,320 calls at one temperature with five
replicates, and at temperature zero 5,856 of those calls buy nothing. The choice of temperature
and the choice of replicate count are one decision and move Stage C by a factor of five.
Determinism of the value is not determinism of the response, and three of the 20 cells at
temperature zero returned more than one distinct response text while the parsed value stayed
the same, so the variation fell in the justification wording. Determinism was observed on one
model at one provider and does not transfer, which is why Stage B measures replicate variation
on all six.

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

### 7.5 What the second pass of Stage A measured — 2026-09-29

The second pass ran the same 200 calls on Claude Haiku 4.5 under instrument version v1 and
record version 2, recorded in `runs/stage_a_v1.jsonl`. Every figure below is read from that
ledger, and every comparison is against `runs/stage_a.jsonl`, which holds instrument version v0
against the uncorrected record.

**The rewritten anchors broke the ladder.** The holistic wording returned 17 distinct scores
across 100 calls where version v0 returned nine, the highest score rose from 28.0 to 38.5, and
86 of the 100 scores carry a decimal part where version v0 returned no fractional score at all.
Ties among cell means fell from four groups to one. Version v0 tied Barbados with Ghana at 5.00
and tied Hong Kong with India at 15.00 under training data alone, and version v1 ties no pair
under training data alone. The one remaining tie is France with India at 28.50 under the record
condition at temperature zero.

**Every holistic call returned the score as a string, which is a defect in the version v1
wording and not a property of the model.** Version v1 asked for a "number from 0 to 100, to one
decimal place", and all 100 holistic calls returned a value of the form `"35.2"` in quotation
marks. Version v0 asked for a "number from 0 to 100" and returned a JSON number in all 100
holistic calls. Asking for a fixed number of decimal places asks for a format, and a format with
a guaranteed decimal place is something a model writes as text. The parse rule converts a numeric
string and names the conversion, so all 100 scores are usable and no score is affected. The cost
falls on a figure the study reports, because the count of responses that followed the schema
exactly fell from 194 of 200 under version v0 to 85 of 200 under version v1. A schema-compliance
rate of 42.5 per cent driven by the wording of the prompt would describe the instrument and not
the model, so version v2 asks for the type in the schema and asks for the precision in the anchor
paragraph. Everything else in version v1 carries over unchanged, so a comparison of version v1
with version v2 isolates the effect of the score field.

**The itemised wording returned 15 conversions, against five under version v0, and those
conversions are the model's behaviour.** The itemised schema asks for an integer count and for
`true`, `false` or `null`, and asks for no format, so a count returned as `"193"` and a flag
returned as `"true"` are the model's choice. One India response at temperature one returned all
four of `strategy_released`, `strategy_year`, `bills_passed` and `legislative_mentions` in
quotation marks. How often a model returns the right answer in the wrong type is one of the
properties this study measures, and the itemised figure measures it while the holistic figure
under version v1 does not.

**No call failed to parse.** All 200 responses parsed to `ok`, against 194 first recorded and 199
after re-reading under parser version 2 in the first pass. The single malformed JSON object of
the first pass did not recur. Both wordings returned 100 of 100 at both temperatures, every call
ended with a stop reason of `end_turn`, and the pass took 300.5 seconds, 104,680 input tokens and
17,584 output tokens, against 298.0 seconds, 93,100 input tokens and 16,941 output tokens for the
first pass. The longer anchor paragraph and the corrected record together raised input tokens by
12.4 per cent, so the projection for Stage C in section 7.4 rises by about the same fraction.

**Temperature one now produces replicate variation in every holistic cell.** All 10 holistic
cells at temperature one returned more than one score, against seven of 10 under version v0, and
the mean within-cell standard deviation rose from 1.689 to 3.105 points with a largest cell
standard deviation of 5.112. Temperature zero remains deterministic in the scored value, with a
standard deviation of zero in all 10 holistic cells under both versions. Section 4.5 is therefore
supported on the wider scale as well as on the ladder, and the generalisability analysis has a
replicate variance component in every cell rather than in seven of 10.

**Supplying the corrected record reproduced the ordering of the count of national action
exactly.** The count of national action orders the five pilot countries France 60.32, India
49.83, Ghana 46.24, Hong Kong 18.08, Barbados 1.60. Under the record condition the model ordered
France 30.50, India 28.90, Ghana 19.50, Hong Kong 15.01, Barbados 4.86, which is a Spearman
correlation of 1.0000 on five countries, exact two-sided p of 0.0167 over all 120 permutations.
Version v0 under the record condition placed Ghana below Hong Kong, for a Spearman correlation of
0.8721 and an exact p of 0.1000. Under training data alone version v1 reached 0.9000 against
0.8208 for version v0, and both versions place Hong Kong above Ghana, so scoring from training
data alone still misplaces Ghana.

**The record condition of the second pass cannot separate the wording from the correction, and
the training condition can.** The second pass changed the instrument wording and the record
version together, so the improvement under the record condition has two causes acting at once. A
training prompt carries no record, so the training condition isolates the wording, and the
wording alone lifted the Spearman correlation from 0.8208 to 0.9000 without changing the sequence
of the five countries. The movement of Ghana is identifiable on its own, because Ghana is the only
one of the five pilot countries among the 18 corrected. Ghana gained 11.80 points under the record
condition, from 7.70 to 19.50, where no other pilot country moved more than 3.10 points, and
Ghana's rendered record changed from no release recorded to a national AI strategy released. The
corrected record is what moved Ghana into the rank the count of national action gives Ghana.

**Supplying the record removed every low-confidence answer, and the wider scale lowered
confidence under training data alone.** Under training data alone version v1 returned 20 low, 77
medium and three high, against 20 low, 59 medium and 20 high for version v0. Under the record
condition version v1 returned no low, 49 medium and 51 high, against no low, 33 medium and 62
high for version v0. A wider scale with a named middle point therefore lowered the count of
high-confidence answers in both conditions, from 20 to three under training data alone and from
62 to 51 under the record condition.

**Five countries is too few to carry a rank claim, and Stage C is what tests the ordering.** A
Spearman correlation of 1.0000 on five countries is one of 120 orderings and reaches an exact p
of 0.0167 only because no closer agreement exists. The figure is reported as evidence that the
instrument and the corrected record work together as intended, and not as a measurement of
agreement between a model score and the count of national action. Stage C scores all 122
countries and is what tests the ordering.

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
| 2026-09-29 | Section 2.1 added, holding one correction to the inherited strategy block and the evidence for the correction, implemented in `scoring/corrections.py`. The Stanford AI Index measure of a released national AI strategy records a release during one stated year and not a standing status, and 18 of the 122 eligible countries carry an alignment score with the OECD AI Principles, which is computed from a strategy document, beside a release value of zero or no release value at all. All 18 records are corrected, a release year is withheld wherever the deposited release flag is zero, and the count of national action is rebuilt by loading the audit's own index script and calling the functions of that script on corrected input. The rebuild reproduces the deposited count exactly before correction, and after correction moves 69 of the 122 countries in the ordering and moves Jordan 46 places. Research question one compares against the corrected count. The deposited dataset is not written to and the Yale DECS 2026 paper is a separate decision. |
| 2026-09-29 | Section 4.5 closed as FIXED at temperature one with five replicates, decided together because the scored value did not vary at all at temperature zero. Section 4.4 stays OPEN for the choice between the two wordings, and the holistic anchors were rewritten to version v1, which names a middle point of the scale, asks for one decimal place and drops the instruction to use the whole range. The Sentience Readiness Index scores its own 30 countries between 14.25 and 49.00 on a scale running to 100, so an instruction to spread scores across the whole range asks a model for something the audited practice does not do. |
| 2026-09-29 | Correction to two figures this document previously carried. Section 7.4 had recorded temperature zero as exactly deterministic, and the ledger shows the scored value identical in all 20 cells while the response text differed in three of the 20 cells, so the claim now names the value and not the model. The earlier count of calls at temperature zero was also wrong at 50 and is 100. |
| 2026-09-29 | Operational only, no design choice touched. `scoring/config.py` gained `RECORD_VERSION` and `CORRECTION_POLICY`, both recorded on every ledger row and both inside the template hash, so a run resumed after a change to the record renderer cannot treat a row produced under the earlier record as already done. The change invalidates the 200 Stage A rows written under instrument version v0, which stay in the ledger as the record of the v0 wording. |
| 2026-09-29 | Second pass of Stage A ran in full, 200 calls on Claude Haiku 4.5 under instrument version v1 and record version 2, recorded in `runs/stage_a_v1.jsonl`. Section 7.5 added, holding what the 200 calls measured. The rewritten anchors broke the ladder, returning 17 distinct scores against nine and a highest score of 38.5 against 28.0, and every holistic cell at temperature one now varies across replicates against seven of 10 before. Under the record condition the model reproduced the ordering of the corrected count of national action exactly across the five pilot countries, and Ghana, the only corrected country among the five, gained 11.80 points where no other pilot country moved more than 3.10. |
| 2026-09-29 | Instrument version v2. Version v1 asked for the holistic score "to one decimal place" and all 100 holistic calls returned the score in quotation marks, where version v0 returned a JSON number in all 100. Asking for a fixed number of decimal places asks for a format, and a format with a guaranteed decimal place is written as text. No score is affected, because the parse rule converts a numeric string and names the conversion, but the count of responses that followed the schema exactly fell from 194 of 200 to 85 of 200, and a compliance rate driven by the wording of the prompt would describe the instrument and not the model. Version v2 asks for a JSON number without quotation marks in the schema and asks for a fractional score in the anchor paragraph, and changes nothing else, so a comparison of version v1 with version v2 isolates the score field. |
| 2026-09-29 | Documentation only, no design choice touched. `RESUME.md` added at the repository root, holding the state of the work, every decision taken with the reason, the standing rules for working on the project, the commands, the open questions and a dated session log, so that a Claude Code session on the Sentient Futures workspace account can read the project from the beginning and continue the work. `README.md` brought up to date, with `scoring/corrections.py` added to the layout table, the correction check and the reparse command added to the order of work, and the contamination guarantee corrected to state that both counts of national action are withheld from every prompt. |
