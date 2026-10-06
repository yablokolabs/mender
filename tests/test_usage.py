from pathlib import Path

from mender.config import PriceConfig
from mender.router.usage import UsageLedger, UsageRecord, compute_cost, now_ts


def _record(tier: str, cost: float | None, latency_ms: float = 100.0) -> UsageRecord:
    return UsageRecord(
        ts=now_ts(),
        kind="model",
        tier=tier,
        model="test-model",
        purpose="unit",
        prompt_tokens=1000,
        completion_tokens=500,
        reasoning_tokens=100,
        total_tokens=1500,
        latency_ms=latency_ms,
        cost_usd=cost,
        ok=True,
    )


def test_compute_cost_uses_per_million_rates() -> None:
    price = PriceConfig(input_per_m=0.06, output_per_m=0.24, source="test")
    cost, note = compute_cost(price, prompt_tokens=1_000_000, completion_tokens=250_000)
    assert cost == 0.06 + 0.06
    assert note is None


def test_compute_cost_unknown_price_returns_note() -> None:
    price = PriceConfig(input_per_m=None, output_per_m=None, source="unpublished")
    cost, note = compute_cost(price, prompt_tokens=1000, completion_tokens=1000)
    assert cost is None
    assert note is not None and "not published" in note


def test_ledger_roundtrip_and_tier_totals(tmp_path: Path) -> None:
    path = tmp_path / "usage.jsonl"
    ledger = UsageLedger(path)
    ledger.add(_record("nano", 0.001, latency_ms=50.0))
    ledger.add(_record("nano", 0.002, latency_ms=150.0))
    ledger.add(_record("ultra", None))

    reloaded = UsageLedger(path)
    assert len(reloaded.records) == 3

    totals = reloaded.by_tier()
    assert totals["nano"].calls == 2
    assert totals["nano"].cost_usd == 0.003
    assert totals["nano"].cost_complete is True
    assert totals["nano"].latency_ms_median == 100.0
    assert totals["nano"].total_tokens == 3000
    assert totals["ultra"].cost_usd is None
    assert totals["ultra"].cost_complete is False
