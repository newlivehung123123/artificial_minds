# Pilot analysis of Stage B

`python -m analysis.pilot` writes every file in this folder except this README, and writes every
file again on every run, so no table or figure here is typed by hand. The program reads the two
ledgers of Stage B, the probe of the six confirmatory models, which are `runs/stage_b.jsonl` and
`runs/stage_b_cap8000.jsonl`. The program also reads the batch manifest
`runs/stage_b.batches.jsonl`, for the cost OpenRouter reported for every closed batch, and reads
`runs/stage_a_v2.jsonl`, the third pass of Stage A on Claude Haiku 4.5, the earlier pilot model,
for comparison alone. OpenRouter is the service which passes every call of the six models to the
provider. The program calls no provider and spends nothing. `summary.md` reports the five
measures of section 7.2 of `PLAN.md` in prose, with the tables and the four figures in place.

Every figure in this folder is a pilot figure on five countries, France, India, Ghana, Hong Kong
and Barbados, and no confirmatory analysis uses any of the figures.

`python -m analysis.gstudy` runs the self-tests of the variance decomposition, and
`python -m analysis.pilot` writes the folder. Both commands run from the root of the repository
and need numpy, scipy and matplotlib, which `requirements.txt` lists.

```bash
python -m analysis.gstudy
python -m analysis.pilot
```

## Where the scores come from

Stage B asked the six confirmatory models to score the five countries under the two conditions,
training data alone and the administrative record supplied in the prompt, at temperature zero and
at temperature one, with five calls for every country, model, condition and temperature. Every
call used the holistic wording, the instrument wording which section 4.4 of `PLAN.md` fixed, at
instrument version v2. A cell means the five calls of one country, model, condition and
temperature, so a model holds 20 cells and 100 calls.

The scores of Gemini 3.1 Pro, DeepSeek V4 Pro and Kimi K3 come from `runs/stage_b_cap8000.jsonl`,
where the three models were sent again at the output cap of 8,000 tokens which Stage C, the
confirmatory run, uses. The scores of Claude Opus 5, GPT-5.6 Sol and GLM-5.2 come from
`runs/stage_b.jsonl`. Inside a ledger the last row written for a call is the row used, so a call
sent again after a failure is read from the answer which succeeded.

Before any file is written, the program checks every row used. A row used must be a parsed answer
with a score from 0 to 100, which ended with the stop reason `stop`, under the route, the
wording, the instrument version and the record version of Stage C, and with a temperature sent
exactly where `scoring/config.py` says the model takes a temperature. Every model must hold the
full grid of 100 calls. A failed check ends the program before any file is written.

## Which file answers which measure

The table below matches every measure of section 7.2 of `PLAN.md` to the files which answer the
measure.

| Measure of section 7.2 of `PLAN.md` | Files |
|---|---|
| 7.2.1 Cost per call by provider, by condition and by instrument | `cost_per_call.csv` |
| 7.2.2 Projected cost of the 3,660 scores of the training condition | `stage_c_projection.csv` |
| 7.2.3 Rate of the six parse outcomes, by provider | `parse_outcomes.csv` |
| 7.2.4 Replicates at temperature zero and at temperature one | `replicate_spread.csv`, `score_values.csv`, `cells.csv`, Figures 1 and 2 |
| 7.2.5 Generalisability coefficient on pilot data alone | `g_components.csv`, `g_coefficients.csv`, `d_study.csv`, `model_reliability.csv`, `leave_one_model_out.csv`, Figures 3 and 4 |

The study scores with one instrument, the holistic wording, so cost by instrument has one level,
and `scoring/config.py` pins every confirmatory model to one endpoint, so cost by model is cost
by provider.

## Tables

Under every heading below, a sentence states what one row of the file holds, and a table names
every column. Money is in US dollars. Scores and standard deviations (SD) are in points of the
score, on the scale from 0 to 100. A blank cell means no value exists. Five columns recur across
the files with one meaning.

| Column | Holds |
|---|---|
| `stage` | `B`, or `A` for Claude Haiku 4.5 |
| `model` | The label of the model |
| `condition` | `training` for training data alone, `record` for the record supplied, and `both` for the two conditions together |
| `temperature` | `0.0` or `1.0` |
| `temperature_applied` | `True` where the call sent the temperature, and `False` where the endpoint takes no temperature, so every call ran at the default of the developer, as for Claude Opus 5, GPT-5.6 Sol and Kimi K3 |

### `cost_per_call.csv`, measure 7.2.1

One row holds a model under one condition or under the two conditions together, 18 rows.

| Column | Holds |
|---|---|
| `ledger`, `route` | The ledger the scores of the model come from, and the route, `sync` or `batch` |
| `calls` | The calls averaged, 50 under one condition and 100 under `both` |
| `mean_input_tokens`, `mean_output_tokens` | The mean tokens per call the provider recorded, with the reasoning tokens counted inside the output tokens |
| `mean_reasoning_tokens` | The mean reasoning tokens per call |
| `largest_output_tokens` | The largest output of a single call |
| `price_input_per_million`, `price_output_per_million` | The listed price per million tokens which `scoring/config.py` holds for the route of the model |
| `listed_usd_per_call` | The mean tokens priced at the listed price |
| `charged_usd_per_call` | The cost OpenRouter charged per call, blank for a model on the batch route under one condition, because OpenRouter reports the cost of a whole batch alone |
| `charged_basis` | How the charged cost was found |

### `stage_c_projection.csv`, measure 7.2.2

One row holds a model, and the last row holds the six models together, seven rows. Stage C sends
every model 610 calls under every condition, 122 countries by five calls at temperature one.

| Column | Holds |
|---|---|
| `route`, `output_cap` | The route and the output cap of the model in Stage C |
| `training_calls`, `record_calls`, `calls` | The calls of Stage C under training data alone, under the record supplied and under the two conditions together |
| `training_listed_usd`, `record_listed_usd` | The calls under the condition times the listed cost per call under the condition |
| `listed_usd` | The calls times the listed cost per call under the two conditions together |
| `listed_usd_from_temperature_one` | The same projection from the calls of Stage B at temperature one alone |
| `charged_rate_usd` | The calls times the charged cost per call under the two conditions together |
| `worst_case_usd` | The calls priced at the mean input tokens of the model and at the full output cap |

### `parse_outcomes.csv`, measure 7.2.3

One row holds a model in one ledger, nine rows. The harness names a single planned call a cell,
so the columns with `cells` in the name count calls. An attempt means one request sent for a
call. The first answered attempt of a call is the attempt counted, because a later attempt exists
only where an earlier attempt failed.

| Column | Holds |
|---|---|
| `ledger`, `route` | The ledger and the route |
| `output_cap` | The output cap of the attempts of the model in the ledger |
| `attempts` | Every attempt of the model in the ledger |
| `transport_error_attempts` | The attempts OpenRouter never answered |
| `cells` | The calls of the model in the ledger |
| `cells_answered` | The calls with at least one answered attempt |
| `first_ok`, `first_json_absent`, `first_json_invalid`, `first_schema_violation`, `first_refusal`, `first_empty` | The calls whose first answered attempt fell under the outcome, out of the six outcomes of `scoring/parse.py` |
| `first_stop_length` | The calls whose first answered attempt ended at the output cap |
| `first_stop_error` | The calls whose first answered attempt ended with the stop reason `error` |
| `cells_scored_at_end` | The calls whose last attempt in the ledger is `ok` |
| `scores_used` | `yes` where the analysis takes the scores of the model from the ledger |

### `replicate_spread.csv`, measure 7.2.4

One row holds a model at one temperature, 14 rows, for the six models of Stage B and Claude
Haiku 4.5.

| Column | Holds |
|---|---|
| `cells` | The 10 cells of the model at the temperature, five countries by two conditions |
| `identical_cells` | The cells whose five calls gave the same score |
| `distinct_scores` | The distinct scores among the 50 calls |
| `mean_within_cell_sd`, `largest_within_cell_sd` | The SD of the five calls of a cell, with a divisor of four, as a mean over the 10 cells and at the largest |

### `cells.csv`, measure 7.2.4

One row holds a cell, 140 rows, for the 120 cells of Stage B and the 20 cells of Claude Haiku
4.5.

| Column | Holds |
|---|---|
| `country` | The three-letter ISO code of the country |
| `calls` | The five calls of the cell |
| `mean`, `sd`, `lowest`, `highest` | The mean, the SD, the lowest and the highest of the five scores |
| `scores` | The five scores in the order of the calls |

### `score_values.csv`, measure 7.2.4

One row holds a model under one condition at one temperature, 28 rows. The holistic wording
anchors the scale at 0, 50 and 100.

| Column | Holds |
|---|---|
| `calls` | The 25 calls, five countries by five calls |
| `distinct_scores` | The distinct scores among the 25 calls |
| `anchor_scores` | The calls which returned 0, 50 or 100 exactly |
| `lowest`, `highest` | The lowest and the highest score |

### `g_components.csv`, measure 7.2.5

One row holds a variance component of one design, 16 rows. The section on the generalisability
study below describes the three designs.

| Column | Holds |
|---|---|
| `design` | `training`, `record` or `both` |
| `component`, `key` | The name of the component, and the letters `analysis/gstudy.py` uses, with `p` for the country, `m` for the model, `c` for the condition and `r` for the call, so `r:pm` and `r:pmc` mean the calls within a cell |
| `variance` | The estimate in squared points of the score, with a negative estimate set to zero |
| `untruncated` | The estimate before a negative estimate is set to zero |
| `share` | The share of the total variance of the design |
| `ms`, `df` | The mean square and the degrees of freedom of the component |
| `set_to_zero` | `yes` where the estimate was negative and was set to zero |

### `g_coefficients.csv`, measure 7.2.5

One row holds a design at one setting, nine rows.

| Column | Holds |
|---|---|
| `design`, `setting` | The design and the setting |
| `models`, `calls` | The models averaged and the calls per cell of the setting |
| `erho2`, `phi` | Eρ² and Φ |
| `erho2_untruncated` | Eρ² from the components before a negative estimate is set to zero |
| `lower_95`, `upper_95` | The 95 per cent interval of Eρ², blank where no exact interval exists |
| `interval` | How the interval was found |

### `d_study.csv`, measure 7.2.5

One row holds a design at one number of models, from one to 12, and at one number of calls per
cell, out of one, two, three, five and 10, 180 rows. In the design with two conditions the
condition is held at the two conditions of the data. The columns are `design`, `models`, `calls`,
`erho2` and `phi`.

### `model_reliability.csv`, measure 7.2.5

One row holds a model under one condition at temperature one, 14 rows. The design of a row is
the five countries with five calls per country, for one model under one condition.

| Column | Holds |
|---|---|
| `between_country_variance`, `within_cell_variance` | The variance component of the country and the variance component of the calls within a country |
| `ms_country`, `ms_within_cell`, `df_country`, `df_within_cell` | The mean squares and the degrees of freedom |
| `reliability_mean_of_five_calls` | One minus `ms_within_cell` over `ms_country`, the reliability of the mean of five calls |
| `lower_95`, `upper_95` | The exact 95 per cent interval from the F distribution on 20 and four degrees of freedom |
| `reliability_one_call`, `one_call_lower_95`, `one_call_upper_95` | The coefficient and the interval converted to one call by the Spearman-Brown formula |
| `negative_components` | The components with a negative estimate, blank where no estimate was negative |
| `note` | Why no interval exists, where no interval exists |

### `leave_one_model_out.csv`, measure 7.2.5

One row holds a design with no model removed or with one model removed, 21 rows. The components
are estimated again from the five models which remain, and Eρ² is projected from the new
components.

| Column | Holds |
|---|---|
| `design`, `model_left_out` | The design, and `none` or the model removed |
| `country`, `model`, `condition`, `country_by_model`, `country_by_condition`, `model_by_condition`, `country_by_model_by_condition`, `replicate_within_cell` | The variance components, blank for a component outside the design |
| `erho2_six_models_five_calls`, `erho2_one_model_five_calls` | Eρ² projected to six models and to one model, with five calls per cell |
| `set_to_zero` | The components with a negative estimate set to zero, blank where no estimate was negative |

## Figures

Every figure is written twice, as PNG at 300 dots per inch and as PDF, in black and white. The
table below names the four figures in the order `summary.md` introduces the figures.

| Figure | File | Shows |
|---|---|---|
| 1 | `fig1_scores` | Every score of Stage B at temperature one, by country and model, with a panel for every condition |
| 2 | `fig2_replicate_spread` | The SD of every cell of Stage B at temperature zero against the SD of the same cell at temperature one, with a dashed line where the two SDs are equal, and a legend which marks the three models sent no temperature |
| 3 | `fig3_variance_shares` | The share of score variance of every component in the three designs, with a component outside a design marked as not in design |
| 4 | `fig4_decision_study` | Eρ² projected to one to 12 models at one, two, three, five and 10 calls per cell in the three designs, with a point at six models and five calls, the size of the data, and a dashed line at 0.80 marked as a conventional reference |

## The generalisability study

A generalisability study splits the variance of the scores into variance components. A facet is
a source of variation the design names, here the model, the call and the condition. The country
is the object of measurement, so variance between countries is the signal. The model and the call
are random facets, because the six models and the five calls stand in for any models and any
calls. The condition is a fixed facet, because the study names two conditions and asks about no
other condition. The study uses the calls at temperature one alone, the temperature of Stage C.
The table below names the three designs.

| Design | Name in the files | Factors |
|---|---|---|
| Training data alone | `training` | Countries by models, with five calls within every cell |
| Record supplied | `record` | Countries by models, with five calls within every cell |
| Two conditions | `both` | Countries by models by fixed conditions, with five calls within every cell |

The generalisability coefficient, Eρ², is the share of the variance of averaged country scores
which comes from differences between countries, when the scores are used to order countries. A
component which combines the country with the model or with the call counts as error, and the
component of the country by the fixed condition counts as signal. The dependability coefficient,
Φ, is the same share when an averaged score places a country on the scale itself, so the
components which shift every country alike, the main effect of the model and, in the design with
two conditions, the model by condition, count as error as well, and Φ is never above Eρ². A
coefficient is reported at three settings, six models with five calls per cell, the size of the
data, one model with five calls per cell, and one model with one call, the size of a single
score.

Five countries give four degrees of freedom between countries, so every interval is wide. At
five calls per cell the 95 per cent interval of Eρ² is exact, from the F distribution on 20 and
four degrees of freedom. The Spearman-Brown formula, which projects a reliability to a different
number of models or calls, converts the interval from six models to one model. No exact interval
exists where the number of calls changes, Φ has no interval, and the reliability of Gemini 3.1
Pro under training data alone has no interval, because the five calls agreed in every country.

No confirmatory analysis uses any figure in this folder. Item one of section 6.2 of `PLAN.md` has
still to name the target of the decision study, so the dashed line at 0.80 in Figure 4 marks a
conventional reference alone and no target of the study. Section 4.4 of `PLAN.md` requires the
sentence below beside every generalisability coefficient the study reports.

> The Digital Minds Research Sprint found a share of 0.876 of the variance separating one model from another in the combination of the model, the prompt format and the outcome, so a design with one wording cannot estimate how much the wording contributes, and the coefficient the study reports is optimistic by an unknown amount.
