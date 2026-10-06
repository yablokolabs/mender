"""OpenAI-compatible client for Nebius Token Factory with per-call usage accounting."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from openai import APIError, OpenAI
from openai.types.chat import ChatCompletionMessageParam

from mender.config import RouterConfig, TierConfig
from mender.router.usage import UsageLedger, UsageRecord, compute_cost, now_ts

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str

    def as_param(self) -> ChatCompletionMessageParam:
        if self.role == "system":
            return {"role": "system", "content": self.content}
        if self.role == "assistant":
            return {"role": "assistant", "content": self.content}
        return {"role": "user", "content": self.content}


@dataclass(frozen=True)
class RawResponse:
    content: str | None
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int | None
    finish_reason: str | None


CompletionSender = Callable[[str, list[ChatCompletionMessageParam], float, int], RawResponse]


@dataclass(frozen=True)
class Completion:
    tier: str
    model: str
    content: str
    record: UsageRecord


class ModelError(RuntimeError):
    """Model call failed after retries, or the tier is unknown."""


def _sdk_sender(client: OpenAI) -> CompletionSender:
    def send(
        model: str, messages: list[ChatCompletionMessageParam], temperature: float, max_tokens: int
    ) -> RawResponse:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if not response.choices:
            raise ModelError(f"{model}: empty choices in response")
        choice = response.choices[0]
        usage = response.usage
        reasoning: int | None = None
        if usage is not None and usage.completion_tokens_details is not None:
            reasoning = usage.completion_tokens_details.reasoning_tokens
        return RawResponse(
            content=choice.message.content,
            prompt_tokens=usage.prompt_tokens if usage is not None else 0,
            completion_tokens=usage.completion_tokens if usage is not None else 0,
            reasoning_tokens=reasoning,
            finish_reason=choice.finish_reason,
        )

    return send


class ModelClient:
    """Routes messages to a configured tier and records every call in the ledger."""

    def __init__(
        self,
        config: RouterConfig,
        api_key: str,
        ledger: UsageLedger,
        *,
        sender: CompletionSender | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._ledger = ledger
        self._sender = sender or _sdk_sender(
            OpenAI(base_url=config.base_url, api_key=api_key, timeout=config.request_timeout_s)
        )
        self._sleep = sleep

    def tier(self, name: str) -> TierConfig:
        try:
            return self._config.tiers[name]
        except KeyError:
            raise ModelError(
                f"unknown tier {name!r}; configured tiers: {sorted(self._config.tiers)}"
            ) from None

    def complete(
        self,
        tier: str,
        messages: list[Message],
        purpose: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Completion:
        cfg = self.tier(tier)
        payload = [m.as_param() for m in messages]
        temp = cfg.temperature if temperature is None else temperature
        limit = cfg.max_tokens if max_tokens is None else max_tokens

        started = time.perf_counter()
        raw: RawResponse | None = None
        last_error: str | None = None
        attempts = self._config.max_retries + 1
        for attempt in range(attempts):
            try:
                raw = self._sender(cfg.model, payload, temp, limit)
                last_error = None
                break
            except (APIError, ConnectionError, OSError, ModelError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < attempts - 1:
                    self._sleep(self._config.retry_backoff_s * (attempt + 1))
        latency_ms = (time.perf_counter() - started) * 1000.0

        if raw is None:
            record = UsageRecord(
                ts=now_ts(),
                kind="model",
                tier=tier,
                model=cfg.model,
                purpose=purpose,
                latency_ms=latency_ms,
                cost_usd=None,
                cost_note="call failed; no usage reported",
                ok=False,
                error=last_error,
            )
            self._ledger.add(record)
            raise ModelError(f"tier {tier!r} call failed after {attempts} attempt(s): {last_error}")

        cost, cost_note = compute_cost(cfg.price, raw.prompt_tokens, raw.completion_tokens)
        record = UsageRecord(
            ts=now_ts(),
            kind="model",
            tier=tier,
            model=cfg.model,
            purpose=purpose,
            prompt_tokens=raw.prompt_tokens,
            completion_tokens=raw.completion_tokens,
            reasoning_tokens=raw.reasoning_tokens,
            total_tokens=raw.prompt_tokens + raw.completion_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            cost_note=cost_note,
            ok=True,
        )
        self._ledger.add(record)
        return Completion(
            tier=tier,
            model=cfg.model,
            content=raw.content or "",
            record=record,
        )
