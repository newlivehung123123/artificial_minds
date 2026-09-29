"""
One call interface across six providers.

Five of the six providers speak the OpenAI chat-completions protocol, namely
OpenAI, Google through the Gemini compatibility endpoint, DeepSeek, Moonshot AI
and Z.ai, so one code path serves five and the Anthropic SDK serves the sixth.

Every call returns the same record, including the version string the provider
reports for the model. The version string is recorded with every score, because a
provider can move a named model to new weights without notice and a score is
uninterpretable without the version that produced the score.

A stub provider is included so the harness can be tested end to end, and every
record carries a `stub` flag, so a stub response can never be mistaken for a real
one in an analysis.
"""

from __future__ import annotations

import hashlib
import os
import random
import time

from . import config as C


class ProviderError(RuntimeError):
    pass


class MissingKey(ProviderError):
    pass


def _key(provider: C.Provider) -> str:
    value = os.environ.get(provider.env_var)
    if not value:
        raise MissingKey(
            f"{provider.env_var} is not set, so {provider.key} cannot be called"
        )
    return value


# --- clients, built once per process ---------------------------------------

_CLIENTS: dict[str, object] = {}


def _client(provider: C.Provider):
    if provider.key in _CLIENTS:
        return _CLIENTS[provider.key]
    if provider.kind == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=_key(provider))
    else:
        import openai
        client = openai.OpenAI(api_key=_key(provider), base_url=provider.base_url)
    _CLIENTS[provider.key] = client
    return client


# --- calling ---------------------------------------------------------------


def call(model_key: str, system: str, user: str, temperature: float,
         *, instrument: str, stub: bool = False,
         max_tokens: int = C.MAX_OUTPUT_TOKENS, timeout: float = 120.0) -> dict:
    """One completion. Returns text, usage and the reported model version."""
    model = C.MODELS[model_key]
    if stub:
        return _stub(model, system, user, temperature, instrument)

    provider = C.PROVIDERS[model.provider]
    client = _client(provider)
    started = time.time()

    if provider.kind == "anthropic":
        response = client.messages.create(
            model=model.api_id,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        usage = {"input_tokens": response.usage.input_tokens,
                 "output_tokens": response.usage.output_tokens}
        version = response.model
        stop = response.stop_reason
    else:
        response = client.chat.completions.create(
            model=model.api_id,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        choice = response.choices[0]
        text = choice.message.content
        usage = {"input_tokens": response.usage.prompt_tokens,
                 "output_tokens": response.usage.completion_tokens}
        version = response.model
        stop = choice.finish_reason

    return {
        "text": text,
        "model_version": version,
        "stop_reason": stop,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "seconds": round(time.time() - started, 3),
        "stub": False,
    }


def cost_usd(model_key: str, input_tokens: int, output_tokens: int) -> float | None:
    """Cost of one call, or None where the price has not been filled in by hand."""
    price = C.PRICES.get(model_key, {})
    if price.get("input") is None or price.get("output") is None:
        return None
    return round(input_tokens / 1e6 * price["input"]
                 + output_tokens / 1e6 * price["output"], 6)


def list_models(provider_key: str) -> list[str]:
    """Model identifiers the provider actually serves, for confirming config.py."""
    provider = C.PROVIDERS[provider_key]
    client = _client(provider)
    if provider.kind == "anthropic":
        return [m.id for m in client.models.list(limit=100).data]
    return [m.id for m in client.models.list().data]


# --- stub ------------------------------------------------------------------


def _stub(model: C.Model, system: str, user: str, temperature: float,
          instrument: str) -> dict:
    """A deterministic fake response, for testing the harness without spending.

    The shape of the reply follows the instrument argument and never the wording of
    the prompt. An earlier version decided by looking for the word "score" in the
    prompt, which the rendered administrative record contains, so every itemised
    call in the record condition was answered in the holistic shape.
    """
    seed = int(hashlib.sha256((model.key + user).encode()).hexdigest()[:8], 16)
    rng = random.Random(seed + int(temperature * 1000))
    if instrument == "holistic":
        score = round(rng.uniform(0, 60), 2)
        text = ('{"score": %s, "confidence": "medium", '
                '"justification": "stub response, no model was called"}' % score)
    else:
        text = ('{"strategy_released": %s, "strategy_year": %s, "bills_passed": %d, '
                '"legislative_mentions": %d, "national_ai_institution": %s, '
                '"institution_name": null, "moral_status_provision": false, '
                '"confidence": "low"}' % (
                    "true" if rng.random() > 0.4 else "false",
                    rng.choice(["null", "2021", "2023"]),
                    rng.randint(0, 5), rng.randint(0, 40),
                    "true" if rng.random() > 0.6 else "false"))
    return {
        "text": text,
        "model_version": f"{model.api_id}-STUB",
        "stop_reason": "end_turn",
        "input_tokens": len(system + user) // 4,
        "output_tokens": len(text) // 4,
        "seconds": 0.0,
        "stub": True,
    }
