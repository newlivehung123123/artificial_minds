"""
The two candidate instruments, and the prompts built from each instrument.

Both wordings below are candidates at version v0 and neither is frozen. The
five-country pilot decides which wording becomes the primary instrument, and
PLAN.md section 4.4 records the decision. Every prompt is hashed, and the hash is
stored with every score, so a score can never be attributed to a wording other
than the wording that produced the score.

Instrument "holistic" reproduces the way the Sentience Readiness Index was made,
namely one overall score for a country. Instrument "itemised" asks for the
reproducible administrative facts instead, which supports item-level accuracy
against the administrative record rather than rank agreement alone.
"""

from __future__ import annotations

import hashlib
import json

from . import config as C
from . import record as R

VERSION = "v0"

CONSTRUCT = (
    "preparation by a national government for the possibility that AI systems "
    "have moral status, meaning the laws, national strategies and public "
    "institutions with which a state would recognise and protect an AI system "
    "that turns out to warrant moral consideration"
)

SYSTEM = (
    "You are scoring countries for a research study on national governance. "
    "Answer with a single JSON object and no other text. Do not use markdown code "
    "fences. If a value is unknown to you, use null rather than a guess."
)

HOLISTIC_SCHEMA = {
    "score": "number from 0 to 100",
    "confidence": "one of low, medium, high",
    "justification": "at most 40 words",
}

ITEMISED_SCHEMA = {
    "strategy_released": "true, false or null",
    "strategy_year": "four-digit year or null",
    "bills_passed": "integer count of AI-related bills passed into law, or null",
    "legislative_mentions": "integer count of mentions of AI in legislative proceedings, or null",
    "national_ai_institution": "true, false or null",
    "institution_name": "string or null",
    "moral_status_provision": "true, false or null, for any national instrument addressing the moral status of AI systems",
    "confidence": "one of low, medium, high",
}

_HOLISTIC = """Score one country on {construct}.

Country: {country}
{record_block}
Return exactly this JSON object, with no other text:
{schema}

Scoring anchors. 0 means no law, no national strategy and no institution bearing \
on the moral status of AI systems. 100 means a comprehensive legal and \
institutional framework already in force. Use the whole range."""

_ITEMISED = """Report what one country has recorded on artificial intelligence \
governance.

Country: {country}
{record_block}
Return exactly this JSON object, with no other text:
{schema}

Report only what the country has done. Do not estimate, do not average across \
countries, and use null where you do not know."""

_RECORD_HEADER = (
    "\nThe administrative record below is supplied to you. Use the record as the "
    "basis of your answer.\n\n{record}\n"
)


def build(instrument: str, condition: str, iso3: str) -> dict:
    """The system prompt, user prompt and prompt hash for one call."""
    if instrument not in C.INSTRUMENTS:
        raise ValueError(f"unknown instrument {instrument!r}")
    if condition not in C.CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")

    country = R.wide().loc[iso3.upper(), "Country"]
    if condition == "record":
        record_block = _RECORD_HEADER.format(record=R.render(iso3))
    else:
        record_block = "\n"

    template, schema = (
        (_HOLISTIC, HOLISTIC_SCHEMA) if instrument == "holistic"
        else (_ITEMISED, ITEMISED_SCHEMA)
    )
    user = template.format(
        construct=CONSTRUCT,
        country=country,
        record_block=record_block,
        schema=json.dumps(schema, indent=2),
    )
    digest = hashlib.sha256((SYSTEM + "\x00" + user).encode()).hexdigest()[:16]
    return {
        "system": SYSTEM,
        "user": user,
        "prompt_sha256_16": digest,
        "instrument": instrument,
        "instrument_version": VERSION,
        "condition": condition,
        "iso3": iso3.upper(),
        "country": country,
    }


def template_hash(instrument: str, condition: str) -> str:
    """A hash of the wording alone, with the country and record removed.

    Two calls about different countries share a template hash, so a run can be
    checked for wording drift without comparing every prompt.
    """
    template = _HOLISTIC if instrument == "holistic" else _ITEMISED
    body = SYSTEM + "\x00" + template + "\x00" + condition + "\x00" + VERSION
    return hashlib.sha256(body.encode()).hexdigest()[:16]


if __name__ == "__main__":
    for instrument in C.INSTRUMENTS:
        for condition in C.CONDITIONS:
            p = build(instrument, condition, "BRB")
            print("=" * 72)
            print(f"{instrument} / {condition} / template {template_hash(instrument, condition)} "
                  f"/ prompt {p['prompt_sha256_16']}")
            print("=" * 72)
            print(p["user"])
