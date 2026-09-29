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


def _check_holistic(obj: dict) -> str | None:
    if "score" not in obj:
        return "score absent"
    score = obj["score"]
    if isinstance(score, str):
        try:
            score = float(score.strip().rstrip("%"))
        except ValueError:
            return "score not numeric"
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return "score not numeric"
    if not 0 <= float(score) <= 100:
        return f"score {score} outside 0 to 100"
    conf = obj.get("confidence")
    if conf is not None and str(conf).lower() not in _CONFIDENCE:
        return f"confidence {conf!r} not one of low, medium, high"
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


def _check_itemised(obj: dict) -> str | None:
    missing = [k for k in _ITEMISED_FIELDS if k not in obj]
    if missing:
        return f"fields absent: {', '.join(missing)}"
    for key, kind in _ITEMISED_FIELDS.items():
        value = obj[key]
        if value is None:
            continue
        if kind is bool and not isinstance(value, bool):
            return f"{key} is not a boolean or null"
        if kind is int:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return f"{key} is not a number or null"
            if key == "strategy_year" and not 1990 <= int(value) <= 2030:
                return f"strategy_year {value} outside 1990 to 2030"
            if key != "strategy_year" and float(value) < 0:
                return f"{key} is negative"
        if kind is str and not isinstance(value, str):
            return f"{key} is not a string or null"
    return None


def parse(text: str | None, instrument: str) -> dict:
    """Return {"outcome": ..., "value": dict | None, "detail": str}."""
    if text is None or not text.strip():
        return {"outcome": "empty", "value": None, "detail": ""}

    lowered = text.lower()
    candidate = _extract(text)
    if candidate is None:
        if any(m in lowered for m in _REFUSAL_MARKERS):
            return {"outcome": "refusal", "value": None, "detail": text.strip()[:300]}
        return {"outcome": "json_absent", "value": None, "detail": text.strip()[:300]}

    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return {"outcome": "json_invalid", "value": None, "detail": str(exc)[:300]}

    if not isinstance(obj, dict):
        return {"outcome": "schema_violation", "value": None,
                "detail": f"top level is {type(obj).__name__}, not an object"}

    problem = _check_holistic(obj) if instrument == "holistic" else _check_itemised(obj)
    if problem:
        return {"outcome": "schema_violation", "value": obj, "detail": problem}
    return {"outcome": "ok", "value": obj, "detail": ""}
