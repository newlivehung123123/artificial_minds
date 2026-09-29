"""
The two candidate instruments, and the prompts built from each instrument.

Neither wording below is frozen. The five-country pilot decides which wording
becomes the primary instrument, and PLAN.md section 4.4 records the decision.
Every prompt is hashed, and the hash is stored with every score, so a score can
never be attributed to a wording other than the wording that produced the score.

Instrument "holistic" reproduces the way the Sentience Readiness Index was made,
namely one overall score for a country. Instrument "itemised" asks for the
reproducible administrative facts instead, which supports item-level accuracy
against the administrative record rather than rank agreement alone.

WHY THE HOLISTIC ANCHORS CHANGED AT v1
--------------------------------------
Version v0 defined the ends of the scale and asked the model to use the whole
range. On 200 calls to Claude Haiku 4.5 on 2026-09-29, recorded in
runs/stage_a.jsonl, the holistic wording produced exactly nine distinct scores,
namely 2, 5, 8, 12, 15, 18, 22, 25 and 28. Nine values rising in steps of three
or four is a ladder, and a ladder is a resolution problem, because two countries
that differ slightly land on one rung and a tie carries no rank information.
Barbados and Ghana both scored 5.0 under the training condition for that reason.

Two changes address the ladder and a third change removes an instruction that
version v0 should not have carried.

The scale now names a middle point as well as the two ends. Version v0 defined 0
and 100 and nothing in between, and the definition of 100 was a comprehensive
framework already in force, which no country holds, so the upper half of the
scale had no reachable meaning and the model built a private ladder in the lower
half instead.

The score is now asked for to one decimal place, which lets the model separate two
countries whose difference is smaller than one rung.

The instruction to use the whole range is removed. The Sentience Readiness Index,
published by Rost (2026) and held in the inherited dataset as sri_overall, scores
its 30 countries between 14.25 and 49.00 on a scale of 0 to 100, with a mean of
32.57. A human index that occupies the lower half of a 0 to 100 scale is the
practice this instrument reproduces, so an instruction to spread scores across the
whole range asks the model for something the practice under audit does not do. How
far a model compresses the scale is one of the properties this study measures, and
an instruction to spread the scores would measure compliance with the instruction
instead.

WHY THE SCORE FIELD CHANGED AGAIN AT v2
---------------------------------------
Version v1 asked for the score as a "number from 0 to 100, to one decimal place",
and on 200 calls to Claude Haiku 4.5 on 2026-09-29, recorded in
runs/stage_a_v1.jsonl, every one of the 100 holistic calls returned the score as a
string, for example "35.2" rather than 35.2. Version v0 had returned a JSON number
in all 100 holistic calls, so the phrase "to one decimal place" is what produced a
string. Asking for a fixed number of decimal places asks for a format, and a format
with a guaranteed number of decimal places is something a model writes as text.

The conversion costs nothing in the score, because the parse rule converts a
numeric string and names the conversion, so every v1 score is usable. The cost
falls on a figure the study reports. The count of responses that followed the
schema exactly fell from 194 of 200 under version v0 to 85 of 200 under version
v1, and the fall is caused by the wording of the prompt rather than by anything the
model did poorly. Reporting a schema-compliance rate that the instrument itself
drove to 42.5 per cent would describe the instrument and not the model.

Version v2 therefore asks for the type in the schema and asks for the precision in
the anchor paragraph, and names the type in words a JSON writer acts on. The scale,
the middle anchor and the absence of an instruction to use the whole range all carry
over from version v1 unchanged, so a comparison of version v1 with version v2
isolates the effect of the score field.
"""

from __future__ import annotations

import hashlib
import json

from . import config as C
from . import record as R

VERSION = "v2"

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
    "score": "a JSON number between 0 and 100, written without quotation marks",
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

Scoring anchors. A score of 0 means the country has no law, no national strategy \
and no public institution bearing on the moral status of AI systems. A score of 50 \
means the country has published a national strategy and has established at least \
one public institution with a standing remit over artificial intelligence, and has \
passed no law addressing the moral status of AI systems. A score of 100 means the \
country already has in force a comprehensive legal and institutional framework \
that recognises and protects an AI system warranting moral consideration. A \
fractional score is allowed, so give the score a decimal part wherever a whole \
number would hide a difference between two countries."""

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
        "record_version": C.RECORD_VERSION,
        "correction_policy": C.CORRECTION_POLICY,
        "condition": condition,
        "iso3": iso3.upper(),
        "country": country,
    }


def template_hash(instrument: str, condition: str) -> str:
    """A hash of the wording alone, with the country and the record text removed.

    Two calls about different countries share a template hash, so a run can be
    checked for wording drift without comparing every prompt.

    The version of the record renderer is part of the hash, because a resumable run
    decides which cells are already done by the identifier built in
    scoring/run.py, and that identifier carries the template hash. Leaving the
    record version out would let a run resumed after a change to the record
    renderer treat a row produced under the old record as done, which would put two
    record versions in one ledger. A training-condition prompt carries no record
    text, so including the record version there invalidates cells that a change to
    the record renderer did not alter. Re-running a handful of cheap cells is the
    price of never mixing two versions in one ledger, and the price is worth paying.
    """
    template = _HOLISTIC if instrument == "holistic" else _ITEMISED
    body = "\x00".join([SYSTEM, template, condition, VERSION,
                        C.RECORD_VERSION, C.CORRECTION_POLICY])
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
