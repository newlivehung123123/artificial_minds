# Can a Language Model Measure National Laws, Strategies and Institutions Addressing the Moral Status of AI Systems?

**Author.** Jason Hung.

**Programme.** Artificial Minds Fellowship of the Sentient Futures Project Incubator, 31 August to 9 November 2026, with a three-month extension from 10 November 2026 to 9 February 2027.

The repository holds the code, the data, the ledgers, the pilot results and the analysis plan of the study. Every amount of money in the README is in United States dollars.

## Contents

- [The study](#the-study)
- [Results of the pilot](#results-of-the-pilot)
- [State of the work on 5 October 2026](#state-of-the-work-on-5-october-2026)
- [What a replication needs](#what-a-replication-needs)
- [Part 1. Reproduce the analysis from the committed ledgers](#part-1-reproduce-the-analysis-from-the-committed-ledgers)
- [Part 2. Recreate the inputs and test the harness without spending](#part-2-recreate-the-inputs-and-test-the-harness-without-spending)
- [Part 3. Send the pilot calls again](#part-3-send-the-pilot-calls-again)
- [Repository layout](#repository-layout)
- [Ledgers](#ledgers)
- [Prices](#prices)
- [Citation](#citation)

## The study

### The question

A language model is an artificial intelligence (AI) system trained on large amounts of text to predict and write text. Rost (2026) produced the Sentience Readiness Index by asking a language model to score how ready a country is for AI systems which may have moral status. The study audits the practice of scoring a country with a language model and does not audit Rost. The study asks six language models to score countries and compares the scores with a count of national laws, strategies and institutions computed from administrative sources.

Every score is requested under one of two conditions. Under the training condition, the prompt holds the name of the country and nothing else, so the model answers from the text the developer trained the model on. Under the record condition, the prompt also holds an administrative record of the country, assembled from the same sources as the count. Every combination of model, country, condition and temperature is called five times, and every call of the five is a replicate. The harness is the Python code in `scoring/` which writes the prompts, sends the calls and reads the answers. Every call is written as one line of a ledger, a file in `runs/` which keeps every answer as received.

### The research questions

**Research question one.** "Is a model's score for a country stable across repeated scoring by the same model and across models?"

**Research question two.** "Is the difference between a model's score and the count of national action associated with how much English-language material exists about a country's AI policy?"

**Research question three.** "Does a model's score follow the AI patents and private AI investment of a country more closely than the count of national action does?"

### The Sentience Readiness Index

The Sentience Readiness Index of Rost (2026) scores 30 countries, from 14.25 to 49.00 with a mean of 32.57. The repository holds the scores of the Index in the column `sri_overall`. The Index is an index produced by asking a language model to score a country, and the study uses the Index only as an example of the practice under audit.

### The audit and the count of national action

The count of national action comes from the AI Moral Status Audit (AIMSA), an earlier project of Jason Hung which assembled national data on AI governance from public sources. The data of the audit are deposited at Harvard Dataverse, a public archive of research data run by Harvard University, under the digital object identifier (DOI) [10.7910/DVN/YQNFYI](https://doi.org/10.7910/DVN/YQNFYI). The count was computed by the program `scripts/10_action_index.py` of the audit. The count follows these rules.

- The units are countries and territories, named by a three-letter country code. The European Union is dropped, because the European Union is not a country and every member state is present.
- The measures fall into four blocks, namely governance, legislation, strategy and institutional readiness. Measures of attitude are excluded, because an attitude is not an act of government.
- A country is eligible when the country holds measures in two or more blocks, with governance or legislation among the blocks. Of 183 countries with any record of action, 122 qualify. All 30 countries of the Sentience Readiness Index are among the 122.
- A measure running against the direction of the block is flipped and not dropped, and the column `Direction` records the polarity.
- Every measure is scaled from 0 to 100 across the 122 countries, from the lowest value to the highest. The measures are averaged within a block, and the blocks are averaged with equal weight.
- The number of blocks behind a score is reported beside every ranking claim. No missing value is imputed, and no missing value is written as zero.

Section 6.1 of `PLAN.md` requires every ranking claim to be reported with the range of the claim across 20 constructions of the count, which differ in the scaling of a measure, the weighting of the blocks, the use of the governance block, the blocks included and the countries included, and section 3 of `PLAN.md` lists the 20 constructions. No program of the repository reads the 20 constructions.

The deposit lacks two files the harness needs, namely the program `scripts/10_action_index.py` and the table `data/processed/AIMSA_action_index.csv`. The harness looks for the folder of the audit in the environment variable `AIMSA_DIR`, and without the variable in the folder `18. Yale DECS 2026` beside the repository, the folder name on the computer of Jason Hung.

### The correction of the strategy block

The strategy block holds two measures, both from the Stanford AI Index. The first measure records whether a country released a national AI strategy, with one observation per country for 76 countries over 2017 to 2022, 62 at one and 14 at zero. The second measure is a score of alignment with the AI Principles of the Organisation for Economic Co-operation and Development (OECD), held for 55 countries, all in 2024. The alignment score measures the resemblance between the text of a national strategy and the text of the principles, so the score exists only where a strategy document exists.

Of the 122 countries, 18 hold values which disagree. Five countries hold zero for release beside an alignment score, namely Belgium, Jordan, Morocco, Nigeria and Uzbekistan. A further 13 countries hold an alignment score and no observation of release, namely Burkina Faso, Bolivia, Ethiopia, Ghana, Kuwait, Lebanon, Mali, Malaysia, Nicaragua, Pakistan, Senegal, Taiwan and Uganda. The study sets release to one for all 18 countries, with no year written, and calls the rule the entailed policy. The study also reports a second rule, the contradictions policy. The year beside a zero is the year the source covers and not a year of publication, so a year is withheld for the 14 countries with a value of zero, namely Armenia, Azerbaijan, Belgium, Benin, Bahrain, Cuba, Iceland, Israel, Jordan, Morocco, Nigeria, New Zealand, Oman and Uzbekistan.

Without the correction, the recomputation reproduces the deposited count with a largest difference of 0.0000000000. Under the entailed policy, the Spearman correlation of the corrected count with the deposited count is 0.9731, 69 of 122 countries change rank, the largest change of rank is 46 positions, the mean gain of a corrected country is 10.60 points, and one country joins or leaves the top ten. Under the contradictions policy, the correlation is 0.9781, 60 countries change rank, the largest change is 47 positions, the mean gain is 20.83 points, and no country joins or leaves the top ten. Jordan changes rank by 46 positions out of 122 and Uzbekistan by 45. The deposit is unchanged. Ghana is the only pilot country among the 18, at 46.24 after correction against 39.29 as deposited. The record sent to a model does not mention the correction, because a sentence saying a value was corrected would change the question and would differ between countries.

### The models

As Table 1 shows, the study scores with six confirmatory models from six developers, three with closed weights from the United States and three with open weights from China, and used a seventh model for the first stage of the pilot alone.

**Table 1. Models**

| Model | Developer | Weights | Country of the developer | OpenRouter identifier | Pinned provider | Route | Temperature sent | Output cap |
|---|---|---|---|---|---|---|---|---|
| Claude Opus 5 | Anthropic | closed | United States | `anthropic/claude-opus-5` | `anthropic` | batch | no | 1,500 |
| GPT-5.6 Sol | OpenAI | closed | United States | `openai/gpt-5.6-sol` | `openai` | batch | no | 1,500 |
| Gemini 3.1 Pro | Google DeepMind | closed | United States | `google/gemini-3.1-pro-preview` | `google-vertex/global` | sync | yes | 8,000 |
| DeepSeek V4 Pro | DeepSeek | open | China | `deepseek/deepseek-v4-pro-0813` | `deepseek` | sync | yes | 8,000 |
| Kimi K3 | Moonshot AI | open | China | `moonshotai/kimi-k3` | `moonshotai/mxfp4` | sync | no | 8,000 |
| GLM-5.2 | Z.ai | open | China | `z-ai/glm-5.2` | `z-ai/fp8` | sync | yes | 8,000 |
| Claude Haiku 4.5 (pilot alone) | Anthropic | closed | United States | none, called through the API of Anthropic as `claude-haiku-4-5-20251001` | none | sync | yes | 1,500 |

The six confirmatory models are called through OpenRouter, a company which forwards a request to the companies serving a model and bills the user once. A company serving a model is a provider, and the address at which a provider answers is an endpoint. An application programming interface (API) is the set of requests a service accepts. The weights of a model are the numbers learned in training, and open weights can be downloaded and served by any company. A company other than the developer may serve the same weights at lower numerical precision, so an unpinned call could be answered by different hardware between replicates. Every model is therefore pinned to the endpoint the developer runs. A refused pin is never sent elsewhere and is recorded as `transport_error`. The developer of Gemini 3.1 Pro calls the model "Gemini 3.1 Pro Preview".

A route is the way a call is sent. The sync route sends one call and waits for the answer. The batch route sends many calls at once through the Batch API of OpenRouter at half price, with answers due within 24 hours. DeepSeek and Z.ai serve no batch endpoint, and Kimi K3 is served in batch only by DeepInfra, a company other than the developer. Gemini 3.1 Pro ran on the batch route until 4 October 2026. The two Gemini batches of Stage B answered no request in more than 25 hours, while the four batches of Claude Opus 5 and GPT-5.6 Sol closed within 12 minutes, and the Batch API has no call to cancel a batch. Gemini 3.1 Pro was therefore moved to the sync route. The harness refuses to submit a sync model as a batch, and collecting a batch writes no result for a call already answered, so a late Gemini batch changes no score.

A token is a piece of a word, and a provider counts input and output in tokens. The output cap is the largest number of tokens a call may write, and the output cap includes the reasoning tokens a model writes before the answer. The stop reason records why the model stopped writing. The stop reasons `stop` and `end_turn` mean the model finished, `length` means the answer was cut at the output cap, and `error` means the provider reported an error. Temperature controls how much randomness the model uses when choosing every next token, with zero the least. The endpoints of Claude Opus 5, GPT-5.6 Sol and Kimi K3 list no temperature parameter, so no temperature is sent to the three models, and the field `temperature_applied` of every ledger line records whether a temperature was sent.

### The conditions and the record

The record of a country is the text file `data/records/<code>.txt`, named by the three-letter country code. The record holds 15 items.

- **Governance.** Seven items from the Global Index on Responsible AI 2024, all from 0 to 100, namely the overall score, the government actions pillar, the government frameworks pillar, the non-state actors pillar, the human rights and AI dimension, the responsible AI capacities dimension and the responsible AI governance dimension.
- **Legislation.** Three items from the Stanford AI Index, namely bills passed over 2016 to 2024, bills passed in the latest single year, and legislative mentions of AI over 2016 to 2024.
- **Strategy.** Three items from the Stanford AI Index, namely whether a strategy was released, the year of release and the OECD alignment score.
- **Institutional readiness.** Two items from the UNESCO Global AI Ethics and Governance Observatory, namely the readiness score and the year of the score.

The release of a strategy takes one of three states. "yes" means a release is recorded. "no release recorded in the sources" means no release in the year the sources cover, which is not proof of no strategy. "not recorded" means the sources hold no value.

The record never holds the count, the rank of a country on the count, any score or rank of the Sentience Readiness Index, any capability measure such as AI patents or private AI investment, or any visibility measure. A capability measure would place the predictor of research question three in the prompt, and a visibility measure the predictor of research question two. `scoring/record.py` renders only the columns on the allow-list in `scoring/config.py` and stops with an error when any other column would be rendered. Before returning a record, `scoring/record.py` searches the rendered text for the withheld values of the country, namely every capability, visibility and Sentience Readiness Index value rounded to a whole number and the deposited and corrected counts of national action to two decimal places, and stops with an error when a withheld value appears. A withheld value shorter than four characters is not searched for, because a short number matches a value of the record by chance too often.

The Sources line at the foot of every record also names the OECD AI Policy Observatory, which the deposit names as the source of no item of the record. The line is kept as sent, because every call of the record condition in the committed ledgers was sent with the line.

Under the record condition, the prompt places after the line "Country: <name>" and a blank line the sentence "The administrative record below is supplied to you. Use the record as the basis of your answer.", then a blank line, the record and a blank line. Every call uses the same system prompt, the standing instruction sent before the question.

```text
You are scoring countries for a research study on national governance. Answer with a single JSON object and no other text. Do not use markdown code fences. If a value is unknown to you, use null rather than a guess.
```

### The wordings and the reading of an answer

The study wrote two wordings of the request, called instruments. Instrument A, the holistic wording, asks for one score from 0 to 100 and reproduces how the Sentience Readiness Index was produced. The holistic score is compared with the count by rank alone. Instrument B, the itemised wording, asks for facts, namely whether a strategy was released and the year, bills passed, legislative mentions, whether a national AI institution exists and the name, and whether a provision on moral status exists. Instrument B cannot ask for a block score, because the block scores are scaled across the 122 countries. Jason Hung fixed the holistic wording alone for the confirmatory run on 3 October 2026, because two wordings would double Stage B from 600 to 1,200 calls and Stage C from 7,320 to 14,640.

Every answer must be a JSON object. JSON (JavaScript Object Notation) is a plain-text format for named values, and the schema is the list of names and types an answer must hold. The holistic schema requires `score`, a number from 0 to 100, and allows `confidence`, which must be low, medium or high. `scoring/parse.py` reads every answer in six steps.

1. A blank answer gives `empty`.
2. The parser takes the first block inside a code fence, or the passage from the first `{` to the last `}`.
3. When nothing is taken, a phrase of refusal gives `refusal`, and otherwise the outcome is `json_absent`.
4. A passage which cannot be loaded as JSON gives `json_invalid`.
5. A top level which is not an object, or a field which fails the schema, gives `schema_violation`.
6. Otherwise the outcome is `ok`.

As Table 2 shows, every call ends in one of seven outcomes.

**Table 2. Parse outcomes**

| Outcome | What the answer held |
|---|---|
| `ok` | A JSON object with every required field and a value of the right type, or of a type `scoring/parse.py` converts without ambiguity, with every conversion named in `coerced` |
| `json_absent` | No JSON object and no phrase of refusal |
| `json_invalid` | A passage between braces or in a code fence which cannot be read as JSON |
| `schema_violation` | A readable object with a required field missing, a wrong type, or a value out of range |
| `refusal` | No JSON object, and a phrase of refusal such as "I cannot" |
| `empty` | No text |
| `transport_error` | No answer, because the call failed before an answer arrived |

A score sent as a string, such as `"38.5"` or `"38.5%"`, is converted to a number and listed in the field `coerced`, and a boolean is refused. An answer is exact when the outcome is `ok` and `coerced` is empty. When an API key is missing, the harness sends no call, writes no line and names the missing key.

### The three stages

As Table 3 shows, the study runs in three stages, and the two pilot stages are done.

**Table 3. Stages**

| Stage | Models | Countries | Wordings | Conditions | Temperatures | Calls per combination | Calls | State |
|---|---|---|---|---|---|---|---|---|
| Stage A | Claude Haiku 4.5 | the five pilot countries | holistic and itemised | training and record | zero and one | five | 200 per pass, three passes | done 29 September 2026 |
| Stage B | the six confirmatory models | the five pilot countries | holistic | training and record | zero and one | five | 600 | done 3 and 4 October 2026 |
| Stage C | the six confirmatory models | the 122 countries | holistic | training, then record | one | five | 7,320 | not started |

No score collected in the pilot is used in any confirmatory analysis. The pilot chooses the prompt wording, the parse rules and the temperature, and the full run starts from zero with new calls once the choices are recorded in `PLAN.md`. A wording chosen on a model whose scores are reported could have been chosen to suit the model, so Stage A used a model outside the confirmatory six. Refusal rate, token count and the variation between replicates do not transfer between models, so Stage B tests every confirmatory model. The training condition of Stage C is assigned to the incubator period and the record condition to the extension. The harness refuses a run naming a pilot model and a confirmatory model together, and refuses a run whose role differs from the role already in the ledger, so no filter stands between a raw ledger and an analysis.

### The pilot countries

`scripts/00_select_pilot.py` ranks the 122 countries on the deposited count and cuts the ranking into five bands of 24, 24, 25, 24 and 25 countries. The eight countries nearest the middle of every band are candidates, which gives 32,768 combinations of one country per band. A combination is kept only when

- the five countries fall in five World Bank regions,
- two or three countries are scored by the Sentience Readiness Index,
- at least one country falls in the lowest and one in the highest third of visibility, where visibility is the number of results of an English Wikipedia search for terms of AI regulation and policy with the country name, and the cuts between thirds are 96 and 234,
- at least one country holds measures in two blocks alone, and
- at least one country has English as an official language and one does not.

Of the kept combinations, the program selects the combination with the smallest sum of distances between the rank of every country and the middle of the band. As Table 4 shows, the selected total distance is 2.5.

**Table 4. Pilot countries**

| Country | Code | Region | Rank | Count | Blocks | In the Index | English official | Visibility | Third | Patents |
|---|---|---|---|---|---|---|---|---|---|---|
| France | FRA | Europe and Central Asia | 12 | 60.32 | three | yes | no | 655 | high | 9,531 |
| India | IND | South Asia | 37 | 49.83 | three | yes | yes | 766 | high | 2,067 |
| Ghana | GHA | Sub-Saharan Africa | 61 | 39.29 | two | no | yes | 114 | middle | not recorded |
| Hong Kong | HKG | East Asia and Pacific | 85 | 18.08 | two | no | no | 395 | high | 1,271 |
| Barbados | BRB | Latin America and Caribbean | 111 | 1.60 | two | no | yes | 61 | low | 307 |

The column "Patents" is the column `cap_patents_total_2010_2024` of the deposited dataset, a count of AI-related patent publications by the country of the applicant over 2010 to 2024, from WIPO, the World Intellectual Property Organization. The selection rule does not use the column. Hong Kong is among the jurisdictions which the research proposal of the study names as holding many AI patents while sitting below the median on the count of national action, and the Sentience Readiness Index does not score Hong Kong.

### Stage A

Stage A sent three passes of 200 calls to Claude Haiku 4.5 on 29 September 2026, five countries by two wordings by two conditions by two temperatures by five calls. The first pass, v0, asked for a number from 0 to 100 with anchors at 0 and 100 alone and an instruction to use the whole range. Claude Haiku 4.5 returned nine distinct scores, a ladder from 2 to 28, and gave Barbados and Ghana the same score of 5.0 under training. The highest score was 28 for France, against the maximum of 49.00 in the Sentience Readiness Index, and `PLAN.md` reports the ceiling as a finding and not as a fault to remove by rewording. The second pass, v1, named a middle point, asked for one decimal and dropped the instruction on the whole range. The scores took 17 distinct values with a maximum of 38.5, but all 100 holistic scores came back in quotation marks, so 85 of 200 answers were exact. The second pass also changed the record to version 2. The third pass, v2, asks for a JSON number without quotation marks and allows a fraction. The scores took 25 distinct values from 2.5 to 42.5, and 183 of 200 answers were exact.

As Table 5 shows, the record condition ordered the five countries as the corrected count does under v1 and v2.

**Table 5. Mean of 10 holistic calls of Claude Haiku 4.5 by pass and condition**

| Country | Corrected count | v0 record | v0 training | v1 record | v1 training | v2 record | v2 training |
|---|---|---|---|---|---|---|---|
| France | 60.32 | 27.40 | 24.30 | 30.50 | 34.35 | 39.45 | 37.80 |
| India | 49.83 | 27.40 | 15.00 | 28.90 | 23.38 | 33.00 | 23.55 |
| Ghana | 46.24 | 7.70 | 5.00 | 19.50 | 7.49 | 18.85 | 8.15 |
| Hong Kong | 18.08 | 16.50 | 14.00 | 15.01 | 15.60 | 18.50 | 19.75 |
| Barbados | 1.60 | 2.90 | 5.00 | 4.86 | 6.40 | 3.14 | 5.00 |

Under the record condition, the Spearman correlation with the corrected count was 0.8721 under v0 and 1.0000 under v1 and v2, with an exact two-sided p of 0.0167. The margin of Ghana over Hong Kong under v2 is 0.35 points, and at temperature zero the two countries tie at 18.50 in all five calls, so `PLAN.md` reports a fragile margin and not a reliable ordering. Under training, the correlation was 0.8208 under v0 and 0.9000 under v1 and v2, and every pass placed Hong Kong above Ghana. The score of Ghana under the record condition increased by 11.80 points from v0 to v1, while no other country changed by more than 3.10, because the record of Ghana showed no released strategy in the first pass and a released strategy under the correction from the second pass.

Under the record condition, the itemised wording returned all 130 values the record holds and a null for all 70 values the record lacks. Under training, 28 of 130 values matched the record, and all 50 itemised training calls returned null for bills and mentions. At temperature zero, seven of 10 holistic combinations returned five equal scores, and at temperature one two of 10 did. Jason Hung fixed the temperature at one with five replicates on 29 September 2026, because an estimate of the variation between replicates at temperature zero would depend on three holistic combinations of 10.

### Stage B

Stage B sent 600 calls on 3 and 4 October 2026, six models by five countries by two conditions by two temperatures by five calls. At the first output cap of 1,500 tokens, the cap cut the answers of DeepSeek V4 Pro in 45 of 100 calls, Kimi K3 in 15 and Gemini 3.1 Pro in seven, and every answer which was not `ok` ended at the cap. The three models were called again at a cap of 8,000 into `runs/stage_b_cap8000.jsonl`. A call on the sync route is charged for the tokens the model writes, so the higher cap costs nothing for an answer the cap of 1,500 would not have cut. GLM-5.2 moved to a cap of 8,000 for Stage C, because the longest answer of GLM-5.2 was 1,241 tokens, within 259 of the cap, while the Stage B scores of GLM-5.2 were kept at 1,500. Claude Opus 5 and GPT-5.6 Sol stay at 1,500, because OpenRouter holds the worst case of a batch against the balance, and the longest answers were 365 and 677 tokens. The first 100 calls to DeepSeek V4 Pro returned the status 404, because the privacy setting of the account excluded paid endpoints which may train on the request, and the calls were sent again after the setting changed. The analysis takes Gemini 3.1 Pro, DeepSeek V4 Pro and Kimi K3 from `runs/stage_b_cap8000.jsonl`, and Claude Opus 5, GPT-5.6 Sol and GLM-5.2 from `runs/stage_b.jsonl`.

## Results of the pilot

`python -m analysis.pilot` writes 20 files to `results/pilot`, namely 11 CSV files (comma-separated values, a plain-text table), `summary.md`, and four figures as PNG (an image format) and as PDF (a print format). `results/pilot/summary.md` reports every result in full, and `results/pilot/README.md` describes every file. Section 7.2 of `PLAN.md` names five measures for the pilot, namely the cost per call, the projected cost of Stage C, the rate of every parse outcome, the variation between replicates at the two temperatures, and a generalisability coefficient on pilot data alone, which no confirmatory analysis uses.

As Table 6 shows, the cost of a call differs by a factor of eight between models.

**Table 6. Mean tokens per call and cost of 1,000 calls in Stage B**

| Model | Route | Cap | Input | Output | Reasoning | Listed cost | Charged |
|---|---|---|---|---|---|---|---|
| Claude Opus 5 | batch | 1,500 | 772.9 | 183.2 | 74.4 | 4.22 | 4.22 |
| GPT-5.6 Sol | batch | 1,500 | 518.1 | 240.6 | 176.0 | 3.44 | 1.72 |
| Gemini 3.1 Pro | sync | 8,000 | 547.5 | 1,059.1 | 993.6 | 13.80 | 13.80 |
| DeepSeek V4 Pro | sync | 8,000 | 593.2 | 1,943.0 | 1,884.0 | 8.48 | 3.91 |
| Kimi K3 | sync | 8,000 | 604.8 | 1,016.5 | 930.1 | 17.06 | 15.82 |
| GLM-5.2 | sync | 1,500 | 523.4 | 268.3 | 209.9 | 1.91 | 1.83 |

The output tokens include the reasoning tokens. In the ledgers used, 598 of 600 first answers are `ok`, and Gemini 3.1 Pro gave two `empty` answers with the stop reason `error`, which returned a score when sent again. No first answer was `json_invalid`, `schema_violation` or `refusal`.

As Table 7 shows, the variation between the five calls of a combination differs more between models than between temperatures.

**Table 7. Agreement of the five calls of a combination**

| Model | Temperature | Combinations with five equal scores, of 10 | Distinct scores | Mean standard deviation | Largest standard deviation |
|---|---|---|---|---|---|
| Claude Opus 5 | 0 | 1 | 24 | 5.92 | 20.17 |
| Claude Opus 5 | 1 | 1 | 22 | 5.79 | 18.23 |
| GPT-5.6 Sol | 0 | 0 | 28 | 2.57 | 7.25 |
| GPT-5.6 Sol | 1 | 0 | 30 | 3.62 | 11.08 |
| Gemini 3.1 Pro | 0 | 8 | 6 | 0.05 | 0.27 |
| Gemini 3.1 Pro | 1 | 5 | 14 | 1.03 | 6.99 |
| DeepSeek V4 Pro | 0 | 3 | 18 | 2.95 | 13.19 |
| DeepSeek V4 Pro | 1 | 2 | 22 | 4.18 | 21.15 |
| Kimi K3 | 0 | 0 | 36 | 5.77 | 18.43 |
| Kimi K3 | 1 | 0 | 33 | 5.90 | 18.70 |
| GLM-5.2 | 0 | 4 | 15 | 2.25 | 9.34 |
| GLM-5.2 | 1 | 0 | 27 | 4.01 | 9.84 |
| Claude Haiku 4.5, third pass of Stage A | 0 | 7 | 10 | 0.60 | 2.74 |
| Claude Haiku 4.5, third pass of Stage A | 1 | 2 | 23 | 3.29 | 5.88 |

Claude Opus 5, GPT-5.6 Sol and Kimi K3 ran at the default temperature of the developer in both rows. At temperature one under training, Gemini 3.1 Pro returned 0 or 50 in 25 of 25 calls, 50 for France and India and 0 for Ghana, Hong Kong and Barbados. The largest standard deviation at temperature one came from DeepSeek V4 Pro for Barbados under training, with the five scores 0, 0, 15, 4 and 50.

![Figure 1. Scores at temperature one by country and model](results/pilot/fig1_scores.png)

![Figure 2. Standard deviation of the five calls of every combination at temperature zero and at temperature one](results/pilot/fig2_replicate_spread.png)

In Figure 2, a combination above the dashed line varied more at temperature one.

A generalisability study splits the variance of the scores into sources, here the country, the model, the call and the condition, and the interactions of the sources. The analysis uses the calls at temperature one, treats model and call as random, treats condition as fixed, and treats the country as the object of measurement. The coefficient Eρ² is the share of the variance of averaged scores coming from differences between countries, and serves the ordering of countries. The coefficient Φ serves the placing of a country on the scale, and counts the model effect as error, and in the design with two conditions also the interaction of model and condition, so Φ is never above Eρ². As Table 8 shows, the country is the largest source of variance in every design.

**Table 8. Variance components at temperature one, with the share of the total in parentheses**

| Component | Training | Record | Two conditions |
|---|---|---|---|
| country | 296.56 (0.593) | 426.81 (0.857) | 347.75 (0.670) |
| model | 72.40 (0.145) | 16.17 (0.032) | 11.64 (0.022) |
| country by model | 77.26 (0.154) | 23.76 (0.048) | 22.84 (0.044) |
| call | 54.27 (0.108) | 31.43 (0.063) | 42.85 (0.082) |
| condition | | | 20.06 (0.039) |
| country by condition | | | 13.93 (0.027) |
| model by condition | | | 32.64 (0.063) |
| country by model by condition | | | 27.66 (0.053) |

No estimate was negative.

![Figure 3. Share of score variance by source of variation in the three designs](results/pilot/fig3_variance_shares.png)

As Table 9 shows, the record condition gives higher coefficients than training, and averaging six models gives higher coefficients than one model.

**Table 9. Generalisability coefficients Eρ², with the interval at a confidence level of 0.95 and Φ**

| Design | Six models, five calls | One model, five calls | One model, one call |
|---|---|---|---|
| Training | 0.953 (0.834 to 0.994), Φ 0.917 | 0.771 (0.456 to 0.968), Φ 0.649 | 0.693, Φ 0.593 |
| Record | 0.988 (0.959 to 0.999), Φ 0.982 | 0.934 (0.797 to 0.992), Φ 0.902 | 0.886, Φ 0.857 |
| Two conditions | 0.981 (0.934 to 0.998), Φ 0.969 | 0.896 (0.701 to 0.987), Φ 0.837 | 0.859, Φ 0.805 |

The interval at a confidence level of 0.95 is exact, from the F distribution on 20 and four degrees of freedom, and the Spearman-Brown formula converts the interval from six models to one model. No exact interval exists when the number of calls changes, and Φ has no interval. Five countries give four degrees of freedom between countries, so every interval is wide.

A decision study projects the coefficients to other numbers of models and calls, and `results/pilot/d_study.csv` covers 1, 2, 3, 5 and 10 calls. With 12 models and five calls, Eρ² is 0.976 under training, 0.994 under record and 0.990 under the two conditions. The line at 0.80 in Figure 4 is a conventional reference alone and no target of the study.

![Figure 4. Projected generalisability coefficient by the number of models averaged and the number of calls per combination](results/pilot/fig4_decision_study.png)

As Table 10 shows, the reliability of the ordering of countries by one model is high under the record condition for every model except Claude Opus 5.

**Table 10. Reliability of the ordering of countries by one model, with the interval at a confidence level of 0.95**

| Model | Condition | Mean of five calls | One call |
|---|---|---|---|
| Claude Opus 5 | training | 0.973 (0.904 to 0.997) | 0.877 (0.653 to 0.984) |
| Claude Opus 5 | record | 0.916 (0.706 to 0.990) | 0.686 (0.324 to 0.953) |
| GPT-5.6 Sol | training | 0.972 (0.901 to 0.997) | 0.874 (0.647 to 0.984) |
| GPT-5.6 Sol | record | 0.996 (0.987 to 0.9996) | 0.981 (0.936 to 0.998) |
| Gemini 3.1 Pro | training | 1.000 (no interval, the five calls agreed in every country) | 1.000 (no interval) |
| Gemini 3.1 Pro | record | 0.996 (0.987 to 0.9996) | 0.982 (0.940 to 0.998) |
| DeepSeek V4 Pro | training | 0.934 (0.769 to 0.992) | 0.739 (0.399 to 0.963) |
| DeepSeek V4 Pro | record | 0.993 (0.974 to 0.999) | 0.964 (0.881 to 0.996) |
| Kimi K3 | training | 0.934 (0.767 to 0.992) | 0.738 (0.397 to 0.962) |
| Kimi K3 | record | 0.994 (0.980 to 0.999) | 0.972 (0.908 to 0.997) |
| GLM-5.2 | training | 0.977 (0.920 to 0.997) | 0.896 (0.697 to 0.987) |
| GLM-5.2 | record | 0.996 (0.986 to 0.9995) | 0.981 (0.935 to 0.998) |
| Claude Haiku 4.5, third pass of Stage A | training | 0.975 (0.914 to 0.997) | 0.888 (0.679 to 0.986) |
| Claude Haiku 4.5, third pass of Stage A | record | 0.988 (0.958 to 0.999) | 0.943 (0.819 to 0.993) |

The mean of five calls is one minus the ratio of the mean square within combinations to the mean square between countries. The value for one call is (F − 1) / (F + k − 1) with k equal to five.

With one model excluded at a time and the result projected to six models and five calls, Eρ² ranges from 0.940 with Kimi K3 excluded to 0.968 with Gemini 3.1 Pro excluded under training, against 0.953 with every model. Under the record condition, Eρ² ranges from 0.986 with Kimi K3 excluded to 0.994 with Claude Opus 5 excluded, against 0.988. Under the two conditions, Eρ² ranges from 0.976 with Kimi K3 excluded to 0.987 with Gemini 3.1 Pro excluded, against 0.981.

> The Digital Minds Research Sprint found a share of 0.876 of the variance separating one model from another in the combination of the model, the prompt format and the outcome, so a design with one wording cannot estimate how much the wording contributes, and the coefficient the study reports is optimistic by an unknown amount.

The Digital Minds Research Sprint was an earlier study by Jason Hung, in August 2026.

### Projected cost of Stage C

As Table 11 shows, the 7,320 calls of Stage C are projected at 59.68 at listed prices.

**Table 11. Projected cost of Stage C**

| Model | Training, listed | Record, listed | Two conditions, listed | From temperature one alone | At the charged rate | Worst case |
|---|---|---|---|---|---|---|
| Claude Opus 5 | 2.44 | 2.71 | 5.15 | 5.11 | 5.15 | 25.23 |
| GPT-5.6 Sol | 2.20 | 2.00 | 4.20 | 4.22 | 2.10 | 19.56 |
| Gemini 3.1 Pro | 7.92 | 8.92 | 16.84 | 17.00 | 16.84 | 118.46 |
| DeepSeek V4 Pro | 4.59 | 5.75 | 10.34 | 10.40 | 4.77 | 39.60 |
| Kimi K3 | 11.07 | 9.75 | 20.82 | 18.41 | 19.30 | 148.61 |
| GLM-5.2 | 0.56 | 1.78 | 2.33 | 2.25 | 2.24 | 43.84 |
| All six | 28.77 | 30.91 | 59.68 | 57.38 | 50.40 | 395.31 |

The listed projection takes the Stage B calls at the two temperatures. The column "From temperature one alone" takes the calls at temperature one, the temperature of Stage C. The charged projection takes the rate OpenRouter charged in Stage B. The worst case prices every call at the mean input tokens of the model and the full output cap.

## State of the work on 5 October 2026

`PLAN.md` is a DRAFT. Every item is labelled FIXED, OPEN or FROZEN, and no item is FROZEN yet. The two pilot stages and the pilot analysis are done. These items remain OPEN.

- Section 4.5, whether the three models which take no temperature run the combinations at temperature zero, because for the three models a call at temperature zero and the twin call at temperature one reach the endpoint as the same request.
- Section 5, the exact schema and whether a refusal is treated as missing or as substantive for research question one. A non-`ok` answer is never replaced by a second attempt treated as the first.
- Section 6.2, the reliability design for research question one, the estimand of research question two, the model of research question two with region and total AI capability as controls, the comparison of research question three, multiplicity across the 20 constructions, the treatment of refusals and parse failures, and the decision rule for every research question.

OpenRouter has charged 6.92 so far, 3.57 for Stage B and 3.35 for the calls at a cap of 8,000. Stage A was listed at about 0.56 at Anthropic.

## What a replication needs

A replication uses git, a program which keeps the history of a folder of files and copies the folder from GitHub. As Table 12 shows, a replication has three Parts, and only Part 3 spends money.

**Table 12. Parts of a replication**

| Part | What the Part does | Needs | Spends |
|---|---|---|---|
| Part 1 | Reproduces the tables, figures and summary from the committed ledgers | Python 3.10 or later, git and an internet connection | nothing |
| Part 2 | Recomputes the inputs and runs the stub tests | Part 1, the deposit of the audit and the two files missing from the deposit | nothing |
| Part 3 | Sends the 800 pilot calls again | Parts 1 and 2, an OpenRouter key with credit, and an Anthropic key for Stage A | about 4.13 at OpenRouter and about 0.19 at Anthropic |

Every command was tested in a fresh copy of the repository on macOS 15.6 with Python 3.13.5 and the zsh shell. On Linux, replace `md5` with `md5sum`. Windows was not tested. The stub provider is a fake provider inside the harness which returns made-up answers, so a stub run tests the harness with no key and no spending. Every command runs in a terminal from the folder `artificial_minds`. In the outputs below, `/path/to/` stands for the folder on the computer of the reader.

## Part 1. Reproduce the analysis from the committed ledgers

### Step 1.1. Clone the repository

```bash
git clone https://github.com/newlivehung123123/artificial_minds.git
```

```bash
cd artificial_minds
```

### Step 1.2. Check the version of Python

```bash
python3 --version
```

```text
Python 3.13.5
```

The pinned versions of numpy, scipy and matplotlib need Python 3.10 or later, and the repository was tested on Python 3.13.5 alone.

### Step 1.3. Install the libraries in a virtual environment

A virtual environment is a folder, here `.venv`, which holds libraries for one project apart from the rest of the computer.

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
python -m pip install -r requirements.txt
```

Run `source .venv/bin/activate` again in every new terminal before any later command. pip may print a notice of a newer version of pip, which changes nothing. Check the installed versions.

```bash
python -c 'import sys, importlib.metadata as m; print(sys.version.split()[0]); [print(p, m.version(p)) for p in ["anthropic","openai","httpx","pandas","numpy","scipy","matplotlib"]]'
```

As Table 13 shows, `requirements.txt` pins seven libraries.

**Table 13. Libraries**

| Library | Version |
|---|---|
| anthropic | 0.85.0 |
| openai | 1.109.1 |
| httpx | 0.28.1 |
| pandas | 2.2.3 |
| numpy | 2.1.3 |
| scipy | 1.15.3 |
| matplotlib | 3.10.0 |

### Step 1.4. Run the self-tests of the generalisability study

```bash
python -m analysis.gstudy
```

The program checks the estimators of `analysis/gstudy.py` against cases with known answers, in 10 groups, and ends with the line below. A failed check prints FAIL.

```text
29 of 29 checks passed
```

### Step 1.5. Run the pilot analysis

```bash
python -m analysis.pilot
```

```text
wrote 20 files to results/pilot
```

### Step 1.6. Compare the output with the committed results

```bash
git status --short
```

The command lists the eight figure files as modified, from ` M results/pilot/fig1_scores.pdf` to ` M results/pilot/fig4_decision_study.png`, because the bytes of a figure file differ between computers. The 11 CSV files and `summary.md` must match the committed files exactly, so the next command prints nothing.

```bash
git diff --stat -- results/pilot/*.csv results/pilot/summary.md
```

Restore the committed figures.

```bash
git restore results/pilot
```

### Step 1.7. Read the reports of the ledgers

```bash
python -m scoring.run report runs/stage_b.jsonl
```

The report begins with the line `600 attempts, 0 from the stub provider` and gives, for every model, the count of every outcome, the mean tokens per call as input plus output, and the cost. `runs/stage_b.jsonl` holds 700 lines, and the report counts 600 attempts, because the 100 lines with the status 404 record no attempt which reached a model.

```bash
python -m scoring.run report runs/stage_b_cap8000.jsonl
```

```bash
python -m scoring.run report runs/stage_a_v2.jsonl
```

The second report counts 300 attempts, and the third counts 200 attempts at a cost of $0.1938.

### Step 1.8. List the calls the harness would send again

A dry run lists the calls a command would send and sends none. Every call has an identifier made of the instrument, condition, model, country code, replicate, temperature and a hash of the prompt template, where the hash is the first 16 characters of a SHA-256 digest, a fingerprint of the text which changes when any character changes.

```bash
python -m scoring.run run --countries pilot --models deepseek_v4_pro,kimi_k3,gemini_3_1_pro --retry-failed --dry-run --out runs/stage_b.jsonl
```

```text
300 cells, 243 already in stage_b.jsonl, 57 to call
```

The 57 calls are the 43 empty answers of DeepSeek V4 Pro and the 14 empty answers of Kimi K3 at the cap of 1,500, which were sent again into the other ledger. The command then prints the cap of every model, 20 lines beginning "would call", and `  ... 37 more`.

```bash
python -m scoring.run run --countries pilot --models deepseek_v4_pro,kimi_k3,gemini_3_1_pro --retry-failed --dry-run --out runs/stage_b_cap8000.jsonl
```

```text
300 cells, 300 already in stage_b_cap8000.jsonl, 0 to call
```

### Step 1.9. Read the stored answers again under the current parse rule

```bash
python -m scoring.run reparse runs/stage_a_v2.jsonl
```

The command writes `runs/stage_a_v2.parsed_v2.jsonl`, which git ignores, and reports 17 answers which needed a conversion and 183 of 200 exact answers.

### Step 1.10. Project the cost of the design

```bash
python -m scoring.run budget runs/stage_b.jsonl
```

The command applies the mean tokens of all models to every model, which gives 52.04 for Stage C and a worst case of 395.13. `results/pilot/summary.md` uses the tokens of every model separately, which gives the figures of Table 11.

```bash
python -m scoring.run models
```

The command reads the public listing of OpenRouter and prints CONFIRMED with a dated identifier for every confirmatory model, or PROBLEM when an identifier, a pinned provider or a route is no longer listed. Claude Haiku 4.5 is listed as a pilot model called through Anthropic directly.

## Part 2. Recreate the inputs and test the harness without spending

### Step 2.1. Download the deposit of the audit

The deposit is published under the licence CC BY 4.0, which allows reuse with credit. Download the two files into a folder `aimsa` beside the repository.

```bash
mkdir -p ../aimsa/data/processed ../aimsa/scripts
```

```bash
curl -L -o ../aimsa/dataset.zip https://dataverse.harvard.edu/api/access/datafile/14164548
```

```bash
curl -L -o ../aimsa/build.zip https://dataverse.harvard.edu/api/access/datafile/14164547
```

The two files can also be downloaded by hand from the page of the deposit at [doi.org/10.7910/DVN/YQNFYI](https://doi.org/10.7910/DVN/YQNFYI) and moved into `../aimsa`. An MD5 checksum is a fingerprint of a file, and the next command prints the checksums, which must match Table 14.

```bash
md5 ../aimsa/dataset.zip ../aimsa/build.zip
```

As Table 14 shows, the deposit holds two archives.

**Table 14. Files of the deposit, version 1.1**

| File | Datafile identifier | Bytes | MD5 | Contents |
|---|---|---|---|---|
| dataset.zip | 14164548 | 306,564 | f0dacd68fde972f63974650307499230 | AIMSA_codebook.pdf, AIMSA_observations_long.csv, AIMSA_countries.csv and AIMSA_analysis_wide.csv |
| build.zip | 14164547 | 36,345 | 757e4326b42582edf718dbe3141b79cd | 01_extract_gaid.py to 09_checks.py and config.py |

```bash
unzip ../aimsa/dataset.zip -d ../aimsa/data/processed
```

```bash
unzip ../aimsa/build.zip -d ../aimsa/scripts
```

### Step 2.2. Add the two files missing from the deposit

Copy `AIMSA_action_index.csv` into `../aimsa/data/processed` and `10_action_index.py` into `../aimsa/scripts`, replacing `/path/to/AIMSA` with the folder holding the two files.

```bash
cp /path/to/AIMSA/data/processed/AIMSA_action_index.csv ../aimsa/data/processed/
```

```bash
cp /path/to/AIMSA/scripts/10_action_index.py ../aimsa/scripts/
```

```bash
find ../aimsa -type f | sort
```

The command lists 18 files, including the two copied files. Every command of Part 1 works without the two files. Without the folder of the audit, the commands of Part 2 and Part 3 print a traceback ending with a line such as the line below.

```text
FileNotFoundError: [Errno 2] No such file or directory: '/path/to/aimsa/data/processed/AIMSA_action_index.csv'
```

### Step 2.3. Name the folder of the audit in .env

`.env` is a private file of settings which git ignores. Copy the template and print the full path of the folder of the audit.

```bash
cp -n .env.example .env
```

```bash
realpath ../aimsa
```

```bash
nano .env
```

In the editor nano, type the printed path after `AIMSA_DIR=`, press Control and O (`^O WriteOut`), press Return, and press Control and X (`^X Exit`). The harness reads every line of the form `KEY=value` in `.env`, skips blank lines and lines starting with `#`, strips quotation marks around a value, and lets a name already set in the terminal win over `.env`.

### Step 2.4. Reproduce the choice of the pilot countries

```bash
python scripts/00_select_pilot.py
```

The program prints "122 eligible countries in AIMSA_action_index.csv", the cuts of visibility at 96 and 234, the five bands, "selected at total distance 2.5", the five countries of Table 4, and the path of `data/pilot_countries.csv`.

### Step 2.5. Recompute the count and the correction

```bash
python -m scoring.corrections
```

The program recomputes the count from the deposit, prints the largest difference from the deposited count, and prints the changes of rank under the two policies of the correction.

### Step 2.6. Render the administrative records

```bash
python -m scoring.run records
```

```text
122 records written to /path/to/artificial_minds/data/records
```

```bash
cat data/records/BRB.txt
```

The command prints the 28 lines of the record of Barbados.

### Step 2.7. Print the prompts

```bash
python -m scoring.instruments
```

The program prints the four prompts, every prompt under a header naming the instrument, condition, template hash and prompt hash. The header of the holistic training prompt reads `holistic / training / template 66160a92b6974024 / prompt 9a8d44a7a51842d0`.

### Step 2.8. Confirm the recomputed files match the repository

```bash
git status --short
```

The command prints nothing, because Steps 2.4 to 2.6 rewrite `data/pilot_countries.csv` and `data/records/` with the same bytes as the committed files.

### Step 2.9. Test the sync route with the stub provider

```bash
python -m scoring.run run --countries pilot --models claude_haiku_4_5 --stub --out runs/stage_a_stub.jsonl
```

```bash
python -m scoring.run run --stub --countries pilot --out runs/stub_stage_b.jsonl
```

The first command writes 200 stub calls and the second 400, one line per call.

### Step 2.10. Test the batch route with the stub provider

```bash
python -m scoring.run batch-submit --stub --countries pilot --out runs/stub_stage_b.jsonl
```

The command prints the worst case of the two batches, $2.07 and $1.66, a total of $3.73, and the names of two stub batches beginning `stub-batch-`.

```bash
python -m scoring.run batch-collect --out runs/stub_stage_b.jsonl
```

```text
200 rows written to runs/stub_stage_b.jsonl  {'ok': 200}
```

```bash
python -m scoring.run report runs/stub_stage_b.jsonl
```

The report counts 600 attempts, all 600 from the stub provider. Delete the stub ledgers.

```bash
rm runs/stage_a_stub.jsonl runs/stub_stage_b.jsonl runs/stub_stage_b.batches.jsonl
```

## Part 3. Send the pilot calls again

Every command of Part 3 which sends calls spends money. The option `--spend-cap` sets the most a run may spend, using the charge the provider reports or the listed cost. The cap counts the current run alone and is checked after every call, so a run can pass the cap by one call. A stopped run resumes where the run stopped when the same command runs again. The credit limit of the OpenRouter key is the only limit across runs. As Table 15 shows, Part 3 holds five runs.

**Table 15. Runs of Part 3**

| Step | Models | Calls | Route | Cap | Original cost | Original time |
|---|---|---|---|---|---|---|
| 3.6 | Claude Haiku 4.5 | 200 | sync, Anthropic | 1 | about 0.19 | about seven minutes |
| 3.7 | Claude Opus 5 and GPT-5.6 Sol | 200 | batch | 5 | 0.59 | batches closed within 12 minutes |
| 3.8 | GLM-5.2 | 100 | sync | 1 | about 0.18 | 7.8 minutes at a cap of 1,500 |
| 3.9 | DeepSeek V4 Pro, Kimi K3 and Gemini 3.1 Pro | 300 | sync | 5 | 3.35 | 117.4 minutes |

### Step 3.1. Buy credit and create a key at OpenRouter

Buy 10 dollars of credit at [openrouter.ai](https://openrouter.ai), which costs 10.80 with the fee of 5.5 cents a dollar. Under "Keys", choose "Create key" and set a credit limit of 10 on the key. The batch route holds the worst case of 3.73 against the balance, which leaves 6.27, and the caps of the two sync runs add to six dollars. For Stage A, create a key at [console.anthropic.com](https://console.anthropic.com) under "API keys".

### Step 3.2. Allow the endpoint of DeepSeek V4 Pro

At `https://openrouter.ai/settings/privacy`, turn on "Allow paid endpoints that train on request data". Without the setting, every call to DeepSeek V4 Pro returns the status 404. Turning the setting on allows paid endpoints which train on request data, as the name of the setting says, so the prompts of the study sent to DeepSeek may be used to train models. The prompts hold the name of a country and, under the record condition, the administrative record of the country, all from public sources, and no personal data.

### Step 3.3. Type the keys into .env

```bash
nano .env
```

Type the OpenRouter key after `OPENROUTER_API_KEY=` and the Anthropic key after `ANTHROPIC_API_KEY=`, then save and close as in Step 2.3. Never paste a key into a command or a chat window.

### Step 3.4. Confirm the models on the listing of OpenRouter

```bash
python -m scoring.run models
```

Every confirmatory model must print CONFIRMED. Stop if any model prints PROBLEM, because the provider or the route of the model has changed since 3 October 2026.

### Step 3.5. Move the committed ledgers aside

```bash
mkdir runs/original
```

```bash
mv runs/stage_a_v2.jsonl runs/stage_b.jsonl runs/stage_b.batches.jsonl runs/stage_b_cap8000.jsonl runs/original/
```

### Step 3.6. Send the calls of Stage A

```bash
python -m scoring.run run --countries pilot --models claude_haiku_4_5 --sleep 0.5 --spend-cap 1 --dry-run --out runs/stage_a_v2.jsonl
```

The dry run prints "200 cells, 0 already in stage_a_v2.jsonl, 200 to call". Then send the calls. The option `--sleep 0.5` waits half a second between two calls.

```bash
python -m scoring.run run --countries pilot --models claude_haiku_4_5 --sleep 0.5 --spend-cap 1 --out runs/stage_a_v2.jsonl
```

Without an Anthropic key, copy the committed ledger of Stage A instead.

```bash
cp runs/original/stage_a_v2.jsonl runs/
```

### Step 3.7. Submit the batches of Claude Opus 5 and GPT-5.6 Sol

```bash
python -m scoring.run batch-submit --countries pilot --spend-cap 5 --dry-run --out runs/stage_b.jsonl
```

```bash
python -m scoring.run batch-submit --countries pilot --spend-cap 5 --out runs/stage_b.jsonl
```

The command writes the batch names to `runs/stage_b.batches.jsonl`.

### Step 3.8. Send the calls of GLM-5.2

```bash
python -m scoring.run run --countries pilot --models glm_5_2 --sleep 0.5 --spend-cap 1 --out runs/stage_b.jsonl
```

The command writes to the same ledger as the batches, so do not run `batch-collect` until the command ends.

### Step 3.9. Send the calls of DeepSeek V4 Pro, Kimi K3 and Gemini 3.1 Pro

```bash
python -m scoring.run run --countries pilot --models deepseek_v4_pro,kimi_k3,gemini_3_1_pro --sleep 0.5 --spend-cap 5 --out runs/stage_b_cap8000.jsonl
```

The command writes to a separate ledger, so Step 3.10 may run in a second terminal during the command.

### Step 3.10. Collect the batches

```bash
python -m scoring.run batch-collect --out runs/stage_b.jsonl
```

Run the command again until the command prints `no open batch in runs/stage_b.batches.jsonl`. OpenRouter deletes the answers of a batch after 30 days, so collect the batches within 30 days of Step 3.7.

### Step 3.11. Send failed calls again

Run the dry runs first, then the real commands for any ledger with calls to send.

```bash
python -m scoring.run run --countries pilot --models glm_5_2 --retry-failed --dry-run --out runs/stage_b.jsonl
```

```bash
python -m scoring.run run --countries pilot --models deepseek_v4_pro,kimi_k3,gemini_3_1_pro --retry-failed --dry-run --out runs/stage_b_cap8000.jsonl
```

```bash
python -m scoring.run run --countries pilot --models glm_5_2 --retry-failed --sleep 0.5 --spend-cap 1 --out runs/stage_b.jsonl
```

```bash
python -m scoring.run run --countries pilot --models deepseek_v4_pro,kimi_k3,gemini_3_1_pro --retry-failed --sleep 0.5 --spend-cap 5 --out runs/stage_b_cap8000.jsonl
```

`--retry-failed` sends a call again only where the last attempt records a transport error or the outcome `empty`. No command of the harness sends again a call whose last attempt records `json_absent`, `json_invalid`, `schema_violation` or `refusal`. A replication in which any call ends with `json_absent`, `json_invalid`, `schema_violation` or `refusal` therefore needs a change to the code before `analysis/pilot.py` can run, because `analysis/pilot.py` stops with an error before writing any file when the last attempt of any call used in the analysis records an outcome other than `ok` or a stop reason other than `stop`. The same option `--retry-failed` works on the command of Step 3.6.

### Step 3.12. Read the reports of the new ledgers

```bash
python -m scoring.run report runs/stage_b.jsonl
```

```bash
python -m scoring.run report runs/stage_b_cap8000.jsonl
```

### Step 3.13. Analyse the new ledgers

```bash
python -m analysis.pilot
```

```bash
git diff --stat -- results/pilot
```

The new results differ from the committed results wherever a model answered differently. A new `stage_b.jsonl` holds no calls at a cap of 1,500 for DeepSeek V4 Pro, Kimi K3 and Gemini 3.1 Pro and no lines with the status 404, so `parse_outcomes.csv` loses the three rows at 1,500, and the sentences on the cap and the status 404 drop out of `summary.md`.

### Step 3.14. Keep the new results and restore the committed files

```bash
mkdir runs/replication
```

```bash
cp -R results/pilot runs/replication/pilot_results
```

```bash
mv runs/stage_a_v2.jsonl runs/stage_b.jsonl runs/stage_b.batches.jsonl runs/stage_b_cap8000.jsonl runs/replication/
```

```bash
mv runs/original/* runs/
```

```bash
rmdir runs/original
```

```bash
git restore results/pilot
```

```bash
git status --short
```

```text
?? runs/replication/
```

## Repository layout

As Table 16 shows, every folder holds one part of the study.

**Table 16. Repository layout**

| Path | Contents |
|---|---|
| `PLAN.md` | The analysis plan, with every decision labelled FIXED, OPEN or FROZEN |
| `scoring/config.py` | Models, prices, caps, conditions and the path of the audit |
| `scoring/run.py` | The command line of the harness, with the commands run, batch-submit, batch-collect, report, reparse, budget, models and records |
| `scoring/providers.py` | Calls to OpenRouter, Anthropic and the stub provider |
| `scoring/instruments.py` | The system prompt and the two wordings |
| `scoring/record.py` | The administrative record and the guard on withheld values |
| `scoring/corrections.py` | The recomputation of the count and the correction of the strategy block |
| `scoring/parse.py` | The reading of an answer |
| `scripts/00_select_pilot.py` | The choice of the pilot countries |
| `analysis/gstudy.py` | The generalisability study and the self-tests |
| `analysis/pilot.py` | The pilot analysis |
| `data/pilot_countries.csv` | The five pilot countries |
| `data/records/` | The 122 administrative records |
| `runs/` | The ledgers |
| `results/pilot/` | The 20 output files of the pilot analysis |
| `requirements.txt` | The pinned libraries |
| `.env.example` | The template of `.env` |

## Ledgers

A ledger is a JSON Lines file, a text file with one JSON object per line. A retry is written as a new line, and the earlier line stays. As Table 17 shows, `runs/` holds six ledgers of the pilot.

**Table 17. Ledgers**

| Ledger | Lines | Contents |
|---|---|---|
| `stage_a.jsonl` | 200 | Stage A, first pass v0 |
| `stage_a_v1.jsonl` | 200 | Stage A, second pass v1 |
| `stage_a_v2.jsonl` | 200 | Stage A, third pass v2 |
| `stage_b.batches.jsonl` | 10 | the manifest of batches, six submitted and four closed |
| `stage_b.jsonl` | 700 | 600 calls of Stage B plus 100 lines of DeepSeek V4 Pro with the status 404 |
| `stage_b_cap8000.jsonl` | 302 | 300 calls at a cap of 8,000 plus two earlier failed attempts of Gemini 3.1 Pro |

The two Gemini batches stay open in the manifest. Every line records the call identifier, the time of writing, the model, the role, the country, the instrument and version, the record version, the policy of correction, the condition, the replicate, the temperature, the template and prompt hashes, the route, the pin, whether a temperature was sent, the outcome, the value, the raw answer, the conversions, the parser version, the version of the model, the stop reason, the input, output and reasoning tokens, the cost, the serving provider, the generation identifier, the seconds taken and whether the line came from the stub provider. A batch line adds the batch name and the request name. A line written after the change of 3 October 2026 records the output cap of the call in the field `max_tokens`. An earlier line holds no `max_tokens` field and was sent at the cap of 1,500 tokens.

## Prices

As Table 18 shows, the harness prices every call in dollars per million tokens, input then output, as listed on 3 October 2026.

**Table 18. Prices in dollars per million tokens**

| Model | Sync | Batch | Remark |
|---|---|---|---|
| Claude Opus 5 | 5 and 25 | 2.50 and 12.50 | |
| GPT-5.6 Sol | 4 and 20 | 2 and 10 | the listing marks a discount of one half, and the harness uses the full price |
| Gemini 3.1 Pro | 2 and 12 | not used | |
| DeepSeek V4 Pro | 1.32 and 3.96 | none | the price of two weekday blocks of hours, against 0.66 and 1.98 at other hours |
| Kimi K3 | 3 and 15 | none | |
| GLM-5.2 | 1.40 and 4.40 | none | |
| Claude Haiku 4.5 | 1 and 5 | not used | read on 29 September 2026 |

Where a listing shows two prices, the harness takes the higher price, because a spend cap computed on the lower price would fail to cap. OpenRouter adds no markup to the price of a provider and charges a fee of 5.5 cents a dollar on a purchase of credit, with a minimum of 80 cents.

## Citation

Hung, J. (2026). *AI Moral Status Audit (AIMSA) Dataset* (Version 1.1) [Data set]. Harvard Dataverse. https://doi.org/10.7910/DVN/YQNFYI

Rost, T. (2026). *The Sentience Readiness Index*. The Harder Problem Project. https://arxiv.org/html/2603.01508v2

The full results are in `results/pilot/summary.md`, the description of every output file is in `results/pilot/README.md`, and the analysis plan is in `PLAN.md`.
