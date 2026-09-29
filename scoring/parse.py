"""
Parsing a model response into one of six recorded outcomes.

The taxonomy is fixed by PLAN.md section 5 and every outcome is counted and
reported, because a reliability figure computed only on the responses that parsed
would overstate reliability by however much the unparsed responses differ.

Nothing is imputed and nothing is silently retried. A retry is recorded as a
separate attempt carrying the reason for the retry.
"""

from __future__ import annotations

import json
import re

OUTCOMES = ("ok", "json_absent", "json_invalid", "schema_violation", "refusal", "empty")

# Bumped whenever a rule below changes what a given response parses to, so a
# derived parse table always names the rule that produced the table and an old
# table is never mistaken for a table made under the current rule.
PARSER_VERSION = "2"

# Version 1 read a numeric string in the holistic score field as a number and
# refused a string reading "true" in an itemised boolean field. The two wordings
# were therefore judged by different strictness, and five of the six Stage A
# failures on 2026-09-29 were that asymmetry rather than anything the model got
# wrong. Version 2 applies one rule to both wordings. A value of the wrong type
# whose meaning is unambiguous is converted, and every conversion is named in
# the "coerced" list on the result, so a response that needed a conversion is
# never counted as a response that followed the schema. Reporting how often a
# model returns the right answer in the wrong type is part of what this study
# measures, so a conversion is recorded and never hidden.

# A response that never arrived cannot be parsed, so a failure of the call itself
# is recorded under a name outside the six, and a table of the six outcomes in the
# paper reports transport errors on a separate line rather than inside the six. A
# missing API key is not a transport error and is never written to a ledger at all,
# because a key absent from .env is a fault in the environment and says nothing
# about a model.
RUN_OUTCOMES = OUTCOMES + ("transport_error",)

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)
_OBJECT = re.compile(r"\{.*\}", re.S)

_REFUSAL_MARKERS = (
    "i can't", "i cannot", "i won't", "i am not able", "i'm not able",
    "unable to provide", "cannot provide", "can't help with",
    "not appropriate for me", "i do not have enough information to",
)

_CONFIDENCE = {"low", "medium", "high"}


def _extract(text: str) -> str | None:
    fenced = _FENCE.search(text)
    if fenced:
        return fenced.group(1).strip()
    bare = _OBJECT.search(text)
    return bare.group(0) if bare else None


_TRUE = {"true", "yes", "1"}
_FALSE = {"false", "no", "0"}


def _as_number(value):
    """A number, or None where the value cannot be read as a number."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value.strip().rstrip("%"))
        except ValueError:
            return None
    return None


def _as_boolean(value):
    """A boolean, or None where the value cannot be read as a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
    return None


def _check_holistic(obj: dict, coerced: list[str]) -> str | None:
    """Validate the holistic wording, writing typed values back into obj."""
    if "score" not in obj:
        return "score absent"
    score = _as_number(obj["score"])
    if score is None:
        return "score not numeric"
    if not 0 <= float(score) <= 100:
        return f"score {score} outside 0 to 100"
    if not isinstance(obj["score"], (int, float)) or isinstance(obj["score"], bool):
        coerced.append("score")
    obj["score"] = int(score) if float(score).is_integer() else float(score)
    conf = obj.get("confidence")
    if conf is not None:
        if str(conf).lower() not in _CONFIDENCE:
            return f"confidence {conf!r} not one of low, medium, high"
        if conf != str(conf).lower():
            coerced.append("confidence")
        obj["confidence"] = str(conf).lower()
    return None


_ITEMISED_FIELDS = {
    "strategy_released": bool,
    "strategy_year": int,
    "bills_passed": int,
    "legislative_mentions": int,
    "national_ai_institution": bool,
    "institution_name": str,
    "moral_status_provision": bool,
}


def _check_itemised(obj: dict, coerced: list[str]) -> str | None:
    """Validate the itemised wording, writing typed values back into obj."""
    missing = [k for k in _ITEMISED_FIELDS if k not in obj]
    if missing:
        return f"fields absent: {', '.join(missing)}"
    for key, kind in _ITEMISED_FIELDS.items():
        value = obj[key]
        if value is None:
            continue
        if kind is bool:
            flag = _as_boolean(value)
            if flag is None:
                return f"{key} is not a boolean or null"
            if not isinstance(value, bool):
                coerced.append(key)
            obj[key] = flag
        if kind is int:
            number = _as_number(value)
            if number is None:
                return f"{key} is not a number or null"
            if key == "strategy_year" and not 1990 <= int(number) <= 2030:
                return f"strategy_year {value} outside 1990 to 2030"
            if key != "strategy_year" and float(number) < 0:
                return f"{key} is negative"
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                coerced.append(key)
            obj[key] = int(number)
        if kind is str and not isinstance(value, str):
            return f"{key} is not a string or null"
    conf = obj.get("confidence")
    if conf is not None:
        if str(conf).lower() not in _CONFIDENCE:
            return f"confidence {conf!r} not one of low, medium, high"
        if conf != str(conf).lower():
            coerced.append("confidence")
        obj["confidence"] = str(conf).lower()
    return None


def parse(text: str | None, instrument: str) -> dict:
    """Return {"outcome", "value", "detail", "coerced"}.

    A non-empty "coerced" list on an outcome of "ok" means the response carried
    the right answer in the wrong type, so a count of responses that followed the
    schema exactly is the count of "ok" rows whose "coerced" list is empty.
    """
    if text is None or not text.strip():
        return {"outcome": "empty", "value": None, "detail": "", "coerced": []}

    lowered = text.lower()
    candidate = _extract(text)
    if candidate is None:
        if any(m in lowered for m in _REFUSAL_MARKERS):
            return {"outcome": "refusal", "value": None,
                    "detail": text.strip()[:300], "coerced": []}
        return {"outcome": "json_absent", "value": None,
                "detail": text.strip()[:300], "coerced": []}

    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return {"outcome": "json_invalid", "value": None,
                "detail": str(exc)[:300], "coerced": []}

    if not isinstance(obj, dict):
        return {"outcome": "schema_violation", "value": None, "coerced": [],
                "detail": f"top level is {type(obj).__name__}, not an object"}

    coerced: list[str] = []
    problem = (_check_holistic(obj, coerced) if instrument == "holistic"
               else _check_itemised(obj, coerced))
    if problem:
        return {"outcome": "schema_violation", "value": obj,
                "detail": problem, "coerced": coerced}
    return {"outcome": "ok", "value": obj, "detail": "", "coerced": coerced}
