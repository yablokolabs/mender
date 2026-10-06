"""Shared test helpers: a fake model sender and typed config factories."""

from __future__ import annotations

from pathlib import Path

import pytest
from openai.types.chat import ChatCompletionMessageParam

from mender.config import PriceConfig, RouterConfig, TierConfig
from mender.router.client import CompletionSender, ModelClient, RawResponse
from mender.router.usage import UsageLedger

FIXTURES = Path(__file__).parent / "fixtures"

KNOWN_PRICE = PriceConfig(input_per_m=0.06, output_per_m=0.24, source="test")


def router_config() -> RouterConfig:
    return RouterConfig(
        max_retries=0,
        retry_backoff_s=0.0,
        tiers={
            "nano": TierConfig(model="nvidia/test-nano", max_tokens=4096, price=KNOWN_PRICE),
            "ultra": TierConfig(model="nvidia/test-ultra", max_tokens=4096, price=KNOWN_PRICE),
            "super": TierConfig(model="nvidia/test-super", max_tokens=4096, price=KNOWN_PRICE),
        },
    )


class FakeSender:
    """Returns canned replies in order (last one repeats) and records every call."""

    def __init__(self, payloads: list[str]) -> None:
        self.payloads = payloads
        self.calls: list[list[ChatCompletionMessageParam]] = []

    def __call__(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        temperature: float,
        max_tokens: int,
    ) -> RawResponse:
        self.calls.append(list(messages))
        text = self.payloads[min(len(self.calls) - 1, len(self.payloads) - 1)]
        return RawResponse(
            content=text,
            prompt_tokens=100,
            completion_tokens=50,
            reasoning_tokens=20,
            finish_reason="stop",
        )

    @property
    def as_sender(self) -> CompletionSender:
        return self

    def last_user_message(self) -> str:
        for message in reversed(self.calls[-1]):
            if message.get("role") == "user":
                content = message.get("content")
                return content if isinstance(content, str) else str(content)
        return ""


def make_client(sender: FakeSender, ledger: UsageLedger) -> ModelClient:
    return ModelClient(router_config(), "test-key", ledger, sender=sender.as_sender)


@pytest.fixture
def ledger(tmp_path: Path) -> UsageLedger:
    return UsageLedger(tmp_path / "usage.jsonl")
