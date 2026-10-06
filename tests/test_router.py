import json
from pathlib import Path

import pytest
from openai.types.chat import ChatCompletionMessageParam

from mender.config import PriceConfig, RouterConfig, TierConfig
from mender.router.client import Message, ModelClient, ModelError, RawResponse
from mender.router.usage import UsageLedger

FIXTURES = Path(__file__).parent / "fixtures"


def _router_config(max_retries: int = 1) -> RouterConfig:
    return RouterConfig(
        max_retries=max_retries,
        retry_backoff_s=0.0,
        tiers={
            "nano": TierConfig(
                model="nvidia/test-nano",
                price=PriceConfig(input_per_m=0.06, output_per_m=0.24, source="test"),
            ),
            "mystery": TierConfig(
                model="nvidia/test-unpriced",
                price=PriceConfig(input_per_m=None, output_per_m=None, source="unpublished"),
            ),
        },
    )


def _fixture_response() -> RawResponse:
    body = json.loads((FIXTURES / "nemotron_chat_completion.json").read_text())
    usage = body.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    choice = body["choices"][0]
    return RawResponse(
        content=choice["message"].get("content"),
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        reasoning_tokens=details.get("reasoning_tokens"),
        finish_reason=choice.get("finish_reason"),
    )


def test_complete_records_usage_and_cost(tmp_path: Path) -> None:
    calls: list[tuple[str, float, int]] = []

    def sender(
        model: str,
        messages: list[ChatCompletionMessageParam],
        temperature: float,
        max_tokens: int,
    ) -> RawResponse:
        calls.append((model, temperature, max_tokens))
        return _fixture_response()

    ledger = UsageLedger(tmp_path / "usage.jsonl")
    client = ModelClient(_router_config(), "test-key", ledger, sender=sender, sleep=lambda _: None)
    result = client.complete("nano", [Message(role="user", content="hi")], purpose="unit test")

    assert calls == [("nvidia/test-nano", 0.0, 8192)]
    assert result.record.ok is True
    assert result.record.tier == "nano"
    assert result.record.prompt_tokens > 0
    assert result.record.cost_usd is not None and result.record.cost_usd > 0
    assert result.record.latency_ms >= 0
    assert len(ledger.records) == 1


def test_unpriced_tier_reports_no_cost(tmp_path: Path) -> None:
    ledger = UsageLedger(tmp_path / "usage.jsonl")
    client = ModelClient(
        _router_config(),
        "test-key",
        ledger,
        sender=lambda *_: _fixture_response(),
        sleep=lambda _: None,
    )
    result = client.complete("mystery", [Message(role="user", content="hi")], purpose="unit")
    assert result.record.cost_usd is None
    assert result.record.cost_note is not None


def test_failure_is_recorded_and_raises(tmp_path: Path) -> None:
    def failing_sender(*_args: object) -> RawResponse:
        raise ConnectionError("boom")

    ledger = UsageLedger(tmp_path / "usage.jsonl")
    client = ModelClient(
        _router_config(max_retries=1),
        "test-key",
        ledger,
        sender=failing_sender,
        sleep=lambda _: None,
    )
    with pytest.raises(ModelError, match="failed after 2 attempt"):
        client.complete("nano", [Message(role="user", content="hi")], purpose="unit")

    records = ledger.records
    assert len(records) == 1
    assert records[0].ok is False
    assert records[0].error is not None and "boom" in records[0].error


def test_retry_then_success(tmp_path: Path) -> None:
    attempts: list[int] = []

    def flaky_sender(*_args: object) -> RawResponse:
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError("transient")
        return _fixture_response()

    ledger = UsageLedger(tmp_path / "usage.jsonl")
    client = ModelClient(
        _router_config(max_retries=1),
        "test-key",
        ledger,
        sender=flaky_sender,
        sleep=lambda _: None,
    )
    result = client.complete("nano", [Message(role="user", content="hi")], purpose="unit")
    assert len(attempts) == 2
    assert result.record.ok is True


def test_unknown_tier_raises(tmp_path: Path) -> None:
    ledger = UsageLedger(tmp_path / "usage.jsonl")
    client = ModelClient(
        _router_config(), "test-key", ledger, sender=lambda *_: _fixture_response()
    )
    with pytest.raises(ModelError, match="unknown tier"):
        client.complete("nope", [Message(role="user", content="hi")], purpose="unit")
