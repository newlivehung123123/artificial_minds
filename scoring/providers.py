"""
One call interface for the pilot model and the six confirmatory models.

The six confirmatory models run through OpenRouter, a company that resells the
API of each developer under one key and one account. OpenRouter speaks the OpenAI
chat-completions protocol, so one code path serves all six, and the Anthropic SDK
serves the pilot model, which Stage A ran through Anthropic directly.

Every call returns the same record, including the version string the provider
reports for the model. The version string is recorded with every score, because a
provider can move a named model to new weights without notice and a score is
uninterpretable without the version that produced the score. A call through
OpenRouter also returns the company that served the call and the charge
OpenRouter reports, so a ledger shows both that the pin in scoring/config.py held
and what each call cost.

Three models run through the batch route of OpenRouter at half the price, and
batch_submit and batch_get are the only functions that touch that route. A
result of a finished batch is read by completion_record, the same function that
reads a sync call, so one ledger schema serves both routes.

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


def openrouter_body(model: C.Model, system: str, user: str, temperature: float,
                    max_tokens: int = C.MAX_OUTPUT_TOKENS) -> dict:
    """The chat-completions body of one call, identical on the sync and batch routes.

    A temperature is sent only to an endpoint that lists the parameter. OpenRouter
    drops a parameter an endpoint does not take without saying so, and a ledger
    row that claimed a temperature the endpoint never applied would be false.
    """
    body = {
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "max_tokens": max_tokens,
    }
    if model.takes_temperature:
        body["temperature"] = temperature
    return body


def completion_record(body: dict) -> dict:
    """The fields a ledger row keeps from one chat completion, sync or batch.

    A field missing from the response is recorded as None and never filled in.
    The output token count includes any reasoning tokens, which are also counted
    on their own, because a reasoning model spends part of the cap of
    MAX_OUTPUT_TOKENS on reasoning the response never shows.
    """
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage = body.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    meta = body.get("openrouter_metadata") or {}
    selected = [e.get("provider") for e in (meta.get("endpoints") or {}).get("available", [])
                if e.get("selected")]
    return {
        "text": message.get("content"),
        "model_version": body.get("model"),
        "stop_reason": choice.get("finish_reason"),
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"),
        "reported_cost": usage.get("cost"),
        "serving_provider": body.get("provider") or (selected[0] if selected else None),
        "router_attempt": meta.get("attempt"),
        "generation_id": body.get("id"),
    }


def call(model_key: str, system: str, user: str, temperature: float,
         *, instrument: str, stub: bool = False,
         max_tokens: int = C.MAX_OUTPUT_TOKENS, timeout: float = 120.0) -> dict:
    """One completion on the sync route. Returns text, usage and the model version."""
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
        record = {
            "text": "".join(b.text for b in response.content
                            if getattr(b, "type", "") == "text"),
            "model_version": response.model,
            "stop_reason": response.stop_reason,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "reasoning_tokens": None,
            "reported_cost": None,
            "serving_provider": None,
            "router_attempt": None,
            "generation_id": response.id,
        }
    else:
        extra: dict = {}
        if model.pin:
            # The pin holds the call to the endpoint the developer runs. With
            # fallbacks off and every sent parameter required, OpenRouter refuses
            # the call when that endpoint is down or lacks a parameter, and the
            # refusal is recorded as a transport error, and no other company
            # answers the call.
            extra["extra_body"] = {"provider": {"only": [model.pin],
                                                "allow_fallbacks": False,
                                                "require_parameters": True}}
            extra["extra_headers"] = {"X-OpenRouter-Metadata": "enabled"}
        response = client.chat.completions.create(
            model=model.api_id,
            **openrouter_body(model, system, user, temperature, max_tokens),
            timeout=timeout,
            **extra,
        )
        record = completion_record(response.model_dump())

    return record | {
        "seconds": round(time.time() - started, 3),
        "route": "sync",
        "pin": model.pin,
        "temperature_applied": model.takes_temperature,
        "stub": False,
    }


def cost_usd(model_key: str, input_tokens: int | None, output_tokens: int | None,
             route: str | None = None) -> float | None:
    """Cost of one call at the listed price, or None where no price is filled in."""
    price = C.price(model_key, route)
    if price.get("input") is None or price.get("output") is None:
        return None
    if input_tokens is None or output_tokens is None:
        return None
    return round(input_tokens / 1e6 * price["input"]
                 + output_tokens / 1e6 * price["output"], 6)


# --- the public listing of OpenRouter, read with no key --------------------


def endpoints(api_id: str, *, batch: bool = False, timeout: float = 30.0) -> dict:
    """The endpoint listing of one model on OpenRouter, on the sync or batch route.

    The listing is public, so no key is sent and nothing is spent.
    """
    import httpx
    suffix = ":batch" if batch else ""
    url = f"{C.PROVIDERS['openrouter'].base_url}/models/{api_id}{suffix}/endpoints"
    response = httpx.get(url, timeout=timeout)
    if response.status_code >= 400:
        raise ProviderError(f"GET {url} returned {response.status_code}: "
                            f"{response.text[:300]}")
    return response.json()["data"]


# --- the batch route -------------------------------------------------------

BATCH_TERMINAL = ("completed", "failed", "expired", "cancelled")


def _openrouter(method: str, path: str, *, body: dict | None = None,
                timeout: float = 300.0) -> dict:
    import httpx
    provider = C.PROVIDERS["openrouter"]
    url = provider.base_url + path
    try:
        response = httpx.request(method, url, json=body, timeout=timeout,
                                 headers={"Authorization": f"Bearer {_key(provider)}"})
    except httpx.HTTPError as exc:
        raise ProviderError(f"{method} {path} did not complete, "
                            f"{type(exc).__name__}: {exc}") from exc
    if response.status_code >= 400:
        raise ProviderError(f"{method} {path} returned {response.status_code}: "
                            f"{response.text[:500]}")
    return response.json()


def batch_submit(model_key: str, requests: list[dict]) -> dict:
    """Submit one batch of {custom_id, body} requests. Returns the batch object."""
    model = C.MODELS[model_key]
    body: dict = {"endpoint": "/v1/chat/completions", "model": model.api_id}
    if model.pin:
        body["provider"] = {"only": [model.pin]}
    body["completion_window"] = "24h"
    # OpenRouter reads the body as a stream and answers 400 when "requests" comes
    # before the other fields, and a dict keeps the order its keys were added in.
    body["requests"] = requests
    return _openrouter("POST", "/batches", body=body)


def batch_get(batch_id: str) -> dict:
    """The batch object, which holds every result inline once the batch is completed."""
    return _openrouter("GET", f"/batches/{batch_id}")


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
        "reasoning_tokens": None,
        "reported_cost": None,
        "serving_provider": None,
        "router_attempt": None,
        "generation_id": None,
        "seconds": 0.0,
        "route": "sync",
        "pin": model.pin,
        "temperature_applied": model.takes_temperature,
        "stub": True,
    }
