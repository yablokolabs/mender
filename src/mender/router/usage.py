"""Usage ledger: tokens, latency and cost per tier for every model and Tavily call."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from statistics import median

from pydantic import BaseModel

from mender.config import PriceConfig


def now_ts() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def compute_cost(
    price: PriceConfig, prompt_tokens: int, completion_tokens: int
) -> tuple[float | None, str | None]:
    """Cost in USD for a call, or (None, reason) when the price is not published."""
    if price.input_per_m is None or price.output_per_m is None:
        return None, f"price not published for this model ({price.source})"
    cost = (
        price.input_per_m * prompt_tokens / 1_000_000
        + price.output_per_m * completion_tokens / 1_000_000
    )
    return cost, None


class UsageRecord(BaseModel):
    ts: str
    kind: str  # "model" | "tavily"
    tier: str  # nano | ultra | super | tavily
    model: str
    purpose: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int | None = None
    total_tokens: int = 0
    latency_ms: float
    cost_usd: float | None = None
    cost_note: str | None = None
    ok: bool = True
    error: str | None = None


class TierTotals(BaseModel):
    calls: int
    failures: int
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    total_tokens: int
    latency_ms_median: float
    cost_usd: float | None
    cost_complete: bool


class UsageLedger:
    """Append-only JSONL ledger of every metered call."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._records: list[UsageRecord] = []
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._records.append(UsageRecord.model_validate_json(line))

    def add(self, record: UsageRecord) -> UsageRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")
        self._records.append(record)
        return record

    @property
    def records(self) -> list[UsageRecord]:
        return list(self._records)

    def by_tier(self) -> dict[str, TierTotals]:
        grouped: dict[str, list[UsageRecord]] = {}
        for record in self._records:
            grouped.setdefault(record.tier, []).append(record)

        totals: dict[str, TierTotals] = {}
        for tier, records in grouped.items():
            costs = [r.cost_usd for r in records]
            known_costs = [c for c in costs if c is not None]
            cost_complete = len(known_costs) == len(costs)
            reasoning = sum(r.reasoning_tokens or 0 for r in records)
            totals[tier] = TierTotals(
                calls=len(records),
                failures=sum(1 for r in records if not r.ok),
                prompt_tokens=sum(r.prompt_tokens for r in records),
                completion_tokens=sum(r.completion_tokens for r in records),
                reasoning_tokens=reasoning,
                total_tokens=sum(r.total_tokens for r in records),
                latency_ms_median=median(r.latency_ms for r in records),
                cost_usd=sum(known_costs) if cost_complete else None,
                cost_complete=cost_complete,
            )
        return totals
