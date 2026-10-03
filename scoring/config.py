"""
Shared configuration for the model-scoring layer.

The count of national action, the 122 eligible countries and the 20 constructions
are inherited unchanged from the Yale DECS 2026 project and are never rebuilt here.
This package adds one thing only: the scores that six frontier models give to the
same 122 countries.

Nothing in this file is authoritative until confirmed empirically:

  * every MODELS[...].api_id, pin and batch endpoint of a confirmatory model is
    confirmed against the public endpoint listing of OpenRouter by
    `python -m scoring.run models`, which needs no key and spends nothing
  * every price in PRICES and BATCH_PRICES is copied from a published price
    listing by hand, with the address and the date read, and a price left as
    None means cost is not computed, only tokens counted

See PLAN.md for the status of every design choice.
"""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT = Path("/Users/newlivehung/Desktop/21. Sentient Futures Incubator")
AUDIT = Path("/Users/newlivehung/Desktop/18. Yale DECS 2026")

# --- API keys --------------------------------------------------------------
# Keys are read from PROJECT/.env, which .gitignore excludes, so a key is typed
# once into one file and is never typed into a shell. A shell `export` reaches
# only the shell that runs the export, and a key typed at a prompt also lands in
# the shell history file, where a key does not belong.

ENV_FILE = PROJECT / ".env"


def load_env(path: Path = ENV_FILE) -> list[str]:
    """Read KEY=value lines from .env into the environment. Returns the names read.

    A name already present in the environment wins, so a key exported in the
    shell for one run is never silently replaced by an older key in the file.
    """
    names: list[str] = []
    if not path.exists():
        return names
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if not value:
            continue
        names.append(name)
        os.environ.setdefault(name, value)
    return names


ENV_NAMES_READ = load_env()

# Inherited inputs. Read only. Never written by this package.
AUDIT_WIDE = AUDIT / "data" / "processed" / "AIMSA_analysis_wide.csv"
AUDIT_INDEX = AUDIT / "data" / "processed" / "AIMSA_action_index.csv"
AUDIT_VARIANTS = AUDIT / "data" / "processed" / "AIMSA_action_variants.csv"

DATA = PROJECT / "data"
RUNS = PROJECT / "runs"
DOCS = PROJECT / "docs"
RECORDS = DATA / "records"          # one rendered administrative record per country
PILOT_COUNTRIES = DATA / "pilot_countries.csv"

# --- Models ----------------------------------------------------------------


@dataclass(frozen=True)
class Provider:
    key: str
    kind: str                 # "anthropic" or "openai_compat"
    env_var: str
    base_url: str | None      # None means the SDK default


PROVIDERS = {
    # The pilot model ran Stage A through Anthropic directly and stays on the same
    # route, so the three Stage A ledgers can be reproduced exactly as the ledgers ran.
    "anthropic": Provider("anthropic", "anthropic", "ANTHROPIC_API_KEY", None),
    # The six confirmatory models run through OpenRouter, a company that resells
    # the API of each developer under one key and one account. Jason Hung approved
    # the OpenRouter route on 2026-10-03 in place of six funded provider accounts.
    # OpenRouter speaks the OpenAI chat-completions protocol, so one code path
    # serves all six models.
    "openrouter": Provider("openrouter", "openai_compat", "OPENROUTER_API_KEY",
                           "https://openrouter.ai/api/v1"),
}


@dataclass(frozen=True)
class Model:
    key: str
    label: str                # as written in the proposal
    provider: str
    api_id: str               # CONFIRM with `run models` before use
    developer: str
    weights: str              # "closed" or "open"
    built_in: str
    role: str = "confirmatory"   # "confirmatory" or "pilot", see below
    pin: str | None = None       # the one OpenRouter endpoint a call may reach
    route: str = "sync"          # "sync" or "batch", see below
    takes_temperature: bool = True


# Three fields govern the OpenRouter route, and all three were read from the
# public endpoint listing of OpenRouter on 2026-10-03.
#
# A pin holds every call of a model to one endpoint. OpenRouter sells most models
# through several companies, and a company other than the developer may serve the
# same weights at a lower numerical precision, so an unpinned call could be
# answered by different hardware from one replicate to the next, and the
# replicate variation the study measures would then include a change of server.
# Every pin below names the endpoint the developer runs. When the pinned endpoint
# is down, the call is refused and is never sent to another company.
#
# A route of "batch" sends the calls of a model through the Batch API of
# OpenRouter at half the price, with results returned within 24 hours. Three
# developers serve a batch endpoint on their own servers, namely Anthropic,
# OpenAI and Google. Kimi K3 is served in batch only by DeepInfra, a company
# other than the developer, so Kimi K3 stays on the sync route at the endpoint
# Moonshot AI runs. DeepSeek and Z.ai serve no batch endpoint.
#
# takes_temperature is False where the pinned endpoint lists no temperature
# parameter. OpenRouter drops a parameter an endpoint does not take without
# saying so, so the harness sends a temperature only to an endpoint that lists
# the parameter, and every ledger row records whether the temperature of the
# cell was applied.


# Two roles, and no score ever crosses from one role to the other.
#
# A confirmatory model is one of the six the proposal names, and every score the
# study reports comes from a confirmatory model.
#
# A pilot model is a cheap model used to settle the instrument wording and the
# parse schema, which are sections 4.4 and 5 of PLAN.md. Settling the wording on
# a model outside the six is stronger than settling the wording on one of the six,
# because a wording chosen on a model the study reports could have been chosen,
# however unintentionally, to suit that model. A prompt a small model returns as
# valid JSON is also returned as valid JSON by a larger model of the same family,
# so a pilot model is the harder test of a wording and the cheaper one.
#
# Refusal rates, token counts and replicate variation do not transfer between
# models, so sections 7.2.1, 7.2.3, 7.2.4 and 7.2.5 need the six confirmatory
# models and cannot be answered by a pilot model at any price.

MODELS = {
    "claude_opus_5": Model("claude_opus_5", "Claude Opus 5", "openrouter",
                           "anthropic/claude-opus-5", "Anthropic", "closed",
                           "United States", pin="anthropic", route="batch",
                           takes_temperature=False),
    "gpt_5_6_sol": Model("gpt_5_6_sol", "GPT-5.6 Sol", "openrouter",
                         "openai/gpt-5.6-sol", "OpenAI", "closed", "United States",
                         pin="openai", route="batch", takes_temperature=False),
    # The developer names the model Gemini 3.1 Pro Preview, and the identifier
    # ends in the suffix. The proposal calls the model Gemini 3.1 Pro.
    "gemini_3_1_pro": Model("gemini_3_1_pro", "Gemini 3.1 Pro", "openrouter",
                            "google/gemini-3.1-pro-preview", "Google DeepMind",
                            "closed", "United States", pin="google-vertex/global",
                            route="batch"),
    # The dated identifier names the general release of DeepSeek V4 Pro, and the
    # endpoint DeepSeek runs serves the dated identifier alone.
    "deepseek_v4_pro": Model("deepseek_v4_pro", "DeepSeek V4 Pro", "openrouter",
                             "deepseek/deepseek-v4-pro-0813", "DeepSeek", "open",
                             "China", pin="deepseek"),
    "kimi_k3": Model("kimi_k3", "Kimi K3", "openrouter", "moonshotai/kimi-k3",
                     "Moonshot AI", "open", "China", pin="moonshotai/mxfp4",
                     takes_temperature=False),
    "glm_5_2": Model("glm_5_2", "GLM-5.2", "openrouter", "z-ai/glm-5.2",
                     "Z.ai", "open", "China", pin="z-ai/fp8"),

    # Pilot workhorse. Haiku 4.5 is the cheapest model Anthropic serves and the
    # identifier below is a dated release identifier rather than an alias, so the
    # weights behind the identifier do not move under the pilot. Add a second
    # pilot model the same way once `run models` prints the listing of a provider,
    # for example the cheapest chat model DeepSeek serves.
    "claude_haiku_4_5": Model("claude_haiku_4_5", "Claude Haiku 4.5", "anthropic",
                              "claude-haiku-4-5-20251001", "Anthropic", "closed",
                              "United States", "pilot"),
}

# The six the proposal names. Every default in the harness is this tuple and never
# MODELS, so a pilot model is called only when a command names the pilot model.
CONFIRMATORY = tuple(k for k, m in MODELS.items() if m.role == "confirmatory")
PILOT_MODELS = tuple(k for k, m in MODELS.items() if m.role == "pilot")

# --- Prices ----------------------------------------------------------------
# US dollars per million tokens, matching the division by 1e6 in
# scoring/providers.py. Filled in by hand from a published price listing, with the
# date read. A None leaves cost uncomputed and token counts are recorded either
# way, so no number in any report is ever invented. A price is never guessed and
# never carried over from an earlier model of the same family, because a family
# name is not a price. Until a price is filled in, `scoring.run report` and
# `scoring.run budget` count tokens and leave every dollar figure blank, and
# `--spend-cap` refuses to run rather than pretending to cap a run it cannot cost.
#
# Where two prices could both apply to a run of this study, the higher price is
# taken, because a spend cap built on the lower price would fail to cap. A
# discount the listing marks is therefore never taken, because the listing does
# not say how long a discount lasts, and cache prices are never taken, because a
# cache hit is not guaranteed and a study that assumed a hit would under-report
# cost. `python -m scoring.run models` applies the same rule to the live listing
# and stops on any price below that no longer matches.
#
# PRICES holds the price of the sync route, where each call is answered at once,
# and BATCH_PRICES holds the price of the batch route of OpenRouter. The price a
# model pays is read through price() below, which picks the table by the route of
# the model.

PRICES: dict[str, dict[str, float | str | None]] = {
    key: {"input": None, "output": None, "read_on": None} for key in MODELS
}
BATCH_PRICES: dict[str, dict[str, float | str | None]] = {}

# A price tier keyed on prompt length applies to this study only where the tier
# starts below this many prompt tokens. The longest prompt Stage A sent was 815
# input tokens, read from runs/stage_a_v2.jsonl, and the ceiling is more than ten
# times that length, so a tokenizer that counts the same text as longer stays
# well inside.
PROMPT_TOKEN_CEILING = 10_000

# The pilot model runs through Anthropic directly, as Stage A ran.
# https://platform.claude.com/docs/en/about-claude/pricing
PRICES["claude_haiku_4_5"] = {"input": 1.00, "output": 5.00, "read_on": "2026-09-29"}

# Every price below was read on 2026-10-03 from the endpoint listing of OpenRouter,
# at https://openrouter.ai/api/v1/models/<api_id>/endpoints for the sync route and
# at https://openrouter.ai/api/v1/models/<api_id>:batch/endpoints for the batch
# route, in both cases at the endpoint the pin in MODELS names. OpenRouter passes
# the price of the developer through without a markup and charges a fee on buying
# credit instead, which no price below includes. The prices read from the price
# page of each developer on 2026-09-29 are kept in commit 5cddccd.

# Claude Opus 5, endpoint anthropic. The batch endpoint is priced at half.
PRICES["claude_opus_5"] = {"input": 5.00, "output": 25.00, "read_on": "2026-10-03"}
BATCH_PRICES["claude_opus_5"] = {"input": 2.50, "output": 12.50, "read_on": "2026-10-03"}

# GPT-5.6 Sol, endpoint openai. The listing prices the sync endpoint at $2.00 and
# $10.00 and the batch endpoint at $1.00 and $5.00, both under a discount of 0.5
# that the listing marks, so the full prices are $4.00 and $20.00 and $2.00 and
# $10.00. The price page of OpenAI showed $4.00 and $20.00 on 2026-09-29. The full
# price is taken on both routes, under the rule above. A prompt past 272,000
# tokens is priced higher, and no prompt in this study comes near that length.
PRICES["gpt_5_6_sol"] = {"input": 4.00, "output": 20.00, "read_on": "2026-10-03"}
BATCH_PRICES["gpt_5_6_sol"] = {"input": 2.00, "output": 10.00, "read_on": "2026-10-03"}

# Gemini 3.1 Pro, endpoint google-vertex/global. The listing prices the sync
# endpoint at $2.00 and $12.00 and the batch endpoint at $1.00 and $6.00, and
# prices a prompt past 200,000 tokens higher on both routes, at $4.00 and $18.00
# and at $2.00 and $9.00. Every prompt in this study is under 1,000 tokens, so the
# lower tier applies. Reasoning tokens are priced as output tokens on both routes.
PRICES["gemini_3_1_pro"] = {"input": 2.00, "output": 12.00, "read_on": "2026-10-03"}
BATCH_PRICES["gemini_3_1_pro"] = {"input": 1.00, "output": 6.00, "read_on": "2026-10-03"}

# DeepSeek V4 Pro, endpoint deepseek. The listing prices the endpoint at $0.66 and
# $1.98, and at $1.32 and $3.96 in two blocks of hours on weekdays, which the
# listing gives in UTC. The higher price is taken, because the hour a run reaches
# DeepSeek is not fixed in advance. The price page of DeepSeek showed the same two
# prices on 2026-09-29, as off-peak and peak.
PRICES["deepseek_v4_pro"] = {"input": 1.32, "output": 3.96, "read_on": "2026-10-03"}

# Kimi K3, endpoint moonshotai/mxfp4, the one endpoint Moonshot AI runs.
PRICES["kimi_k3"] = {"input": 3.00, "output": 15.00, "read_on": "2026-10-03"}

# GLM-5.2, endpoint z-ai/fp8, the one endpoint Z.ai runs.
PRICES["glm_5_2"] = {"input": 1.40, "output": 4.40, "read_on": "2026-10-03"}


def price(model_key: str, route: str | None = None) -> dict:
    """The price of a model on a route, by default the route the model runs on."""
    route = route or MODELS[model_key].route
    table = BATCH_PRICES if route == "batch" else PRICES
    return table.get(model_key, {})


# --- Design ----------------------------------------------------------------

CONDITIONS = ("training", "record")
INSTRUMENTS = ("holistic", "itemised")
# Stage B and Stage C run the holistic wording alone. Jason Hung fixed section 4.4
# of PLAN.md on 2026-10-03, because the two wordings together nearly doubled the
# cost of the study. The itemised wording stays in the harness, so the Stage A
# ledgers can be reproduced and a pilot run can still call both wordings.
CONFIRMATORY_INSTRUMENTS = ("holistic",)
REPLICATES = 5
TEMPERATURES = (0.0, 1.0)          # pilot runs both, the frozen plan names one

MAX_OUTPUT_TOKENS = 1500

# --- Size of each stage ----------------------------------------------------
# Every factor is written out, so the arithmetic behind a call count in any report
# is checkable without reading code. Stage A runs on one cheap pilot model and
# settles the instrument wording and the parse schema. Stage B runs on the six
# confirmatory models under the wording Stage A chose, and answers the questions
# that do not transfer between models, namely refusal rate, token count and
# replicate variation. Stage C is the run the proposal reports.

STAGES = [
    {"code": "A", "name": "instrument shake-down, one pilot model", "role": "pilot",
     "factors": {"models": 1, "countries": 5, "instruments": 2, "conditions": 2,
                 "temperatures": 2, "replicates": 5}},
    {"code": "B", "name": "per-provider probe, six confirmatory models",
     "role": "confirmatory",
     "factors": {"models": 6, "countries": 5, "instruments": 1, "conditions": 2,
                 "temperatures": 2, "replicates": 5}},
    {"code": "C", "name": "confirmatory run, six confirmatory models",
     "role": "confirmatory",
     "factors": {"models": 6, "countries": 122, "instruments": 1, "conditions": 2,
                 "temperatures": 1, "replicates": 5}},
]


def stage_calls(stage: dict) -> int:
    n = 1
    for value in stage["factors"].values():
        n *= value
    return n


# --- Administrative record -------------------------------------------------
# Allow-list. scoring/record.py renders these columns and nothing else, and
# raises on any column not listed here. Supplying a capability measure would put
# the predictor of RQ3 inside the prompt and supplying a visibility measure would
# do the same for RQ2, so cap_*, vis_*, sri_*, the six Index category scores,
# In_SRI, Region and Income_Group are all withheld deliberately.

# Bumped whenever a label, a unit, a block or the correction policy below changes
# what a country's rendered record says. Stored with every call, so a score is
# never attributed to a record other than the record that produced the score.
# Version 1 printed a strategy release value of 0 as the word "no", which asserts
# that a country has no national AI strategy on the evidence of a source that
# reports only whether a strategy was released during one stated year. Version 2
# applies the correction in scoring/corrections.py and says what the sources
# record instead.
RECORD_VERSION = "2"

# Which correction policy scoring/record.py renders and scoring/corrections.py
# rebuilds the count of national action under. See the module docstring of
# scoring/corrections.py for the evidence and for the two alternatives.
CORRECTION_POLICY = "entailed"

RECORD_BLOCKS: list[tuple[str, list[tuple[str, str, str]]]] = [
    ("Responsible AI governance", [
        ("act_girai_overall", "Global Index on Responsible AI, overall score", "0-100"),
        ("act_girai_gov_actions", "Global Index on Responsible AI, government actions pillar", "0-100"),
        ("act_girai_gov_frameworks", "Global Index on Responsible AI, government frameworks pillar", "0-100"),
        ("act_girai_nonstate", "Global Index on Responsible AI, non-state actors pillar", "0-100"),
        ("act_girai_human_rights", "Global Index on Responsible AI, human rights and AI dimension", "0-100"),
        ("act_girai_capacities", "Global Index on Responsible AI, responsible AI capacities dimension", "0-100"),
        ("act_girai_governance", "Global Index on Responsible AI, responsible AI governance dimension", "0-100"),
    ]),
    ("Legislation", [
        ("act_bills_cumulative", "AI-related bills passed into law, cumulative 2016 to 2024", "count"),
        ("act_bills_2023", "AI-related bills passed into law, latest single year reported", "count"),
        ("act_mentions_cumulative", "Mentions of AI in legislative proceedings, cumulative 2016 to 2024", "count"),
    ]),
    ("National strategy", [
        # The unit below renders three states and not two, because the source
        # reports whether a strategy was released during one stated year and a
        # country with no release in that year may still hold a strategy.
        ("act_strategy_released", "National AI strategy released", "strategy status"),
        ("act_strategy_released_year", "Year the national AI strategy was released", "year"),
        ("act_strategy_oecd_alignment", "Alignment of the national AI strategy with the OECD AI Principles", "cosine similarity"),
    ]),
    ("Institutional readiness", [
        ("act_unesco_readiness", "UNESCO AI readiness assessment score", "per cent"),
        ("act_unesco_readiness_year", "Year of the UNESCO AI readiness assessment", "year"),
    ]),
]

RECORD_ALLOWED = {col for _, items in RECORD_BLOCKS for col, _, _ in items}

RECORD_SOURCES = (
    "Global Index on Responsible AI 2024; Stanford AI Index; OECD AI Policy "
    "Observatory; UNESCO AI Readiness Assessment. Compiled in the AI Moral Status "
    "Audit (AIMSA) dataset, https://doi.org/10.7910/DVN/YQNFYI"
)
