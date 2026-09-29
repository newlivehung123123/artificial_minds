"""
Shared configuration for the model-scoring layer.

The count of national action, the 122 eligible countries and the 20 constructions
are inherited unchanged from the Yale DECS 2026 project and are never rebuilt here.
This package adds one thing only: the scores that six frontier models give to the
same 122 countries.

Nothing in this file is authoritative until confirmed empirically:

  * every MODELS[...].api_id is confirmed against the model listing of the provider
    by `python -m scoring.run models` before the pilot runs
  * every PROVIDERS[...].base_url is confirmed by the same command
  * every price in PRICES is copied from the published price page of the provider
    by hand, and a price left as None means cost is not computed, only tokens counted

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
    "anthropic": Provider("anthropic", "anthropic", "ANTHROPIC_API_KEY", None),
    "openai": Provider("openai", "openai_compat", "OPENAI_API_KEY", None),
    # Google serves Gemini through an OpenAI-compatible endpoint, which keeps one
    # call path for five of the six providers. Confirm with `run models`.
    "google": Provider("google", "openai_compat", "GEMINI_API_KEY",
                       "https://generativelanguage.googleapis.com/v1beta/openai/"),
    "deepseek": Provider("deepseek", "openai_compat", "DEEPSEEK_API_KEY",
                         "https://api.deepseek.com/v1"),
    "moonshot": Provider("moonshot", "openai_compat", "MOONSHOT_API_KEY",
                         "https://api.moonshot.ai/v1"),
    "zai": Provider("zai", "openai_compat", "ZAI_API_KEY",
                    "https://api.z.ai/api/paas/v4"),
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
    "claude_opus_5": Model("claude_opus_5", "Claude Opus 5", "anthropic",
                           "claude-opus-5", "Anthropic", "closed", "United States"),
    "gpt_5_6_sol": Model("gpt_5_6_sol", "GPT-5.6 Sol", "openai",
                         "gpt-5.6-sol", "OpenAI", "closed", "United States"),
    "gemini_3_1_pro": Model("gemini_3_1_pro", "Gemini 3.1 Pro", "google",
                            "gemini-3.1-pro", "Google DeepMind", "closed", "United States"),
    "deepseek_v4_pro": Model("deepseek_v4_pro", "DeepSeek V4 Pro", "deepseek",
                             "deepseek-v4-pro", "DeepSeek", "open", "China"),
    "kimi_k3": Model("kimi_k3", "Kimi K3", "moonshot",
                     "kimi-k3", "Moonshot AI", "open", "China"),
    "glm_5_2": Model("glm_5_2", "GLM-5.2", "zai",
                     "glm-5.2", "Z.ai", "open", "China"),

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

# US dollars per million tokens. Filled in by hand from the price page of each
# provider, with the date read. A None leaves cost uncomputed and token counts
# are recorded either way, so no number in any report is ever invented.
PRICES: dict[str, dict[str, float | None]] = {
    key: {"input": None, "output": None, "read_on": None} for key in MODELS
}

# --- Design ----------------------------------------------------------------

CONDITIONS = ("training", "record")
INSTRUMENTS = ("holistic", "itemised")
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
        ("act_strategy_released", "National AI strategy released", "1 for yes, 0 for no"),
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
