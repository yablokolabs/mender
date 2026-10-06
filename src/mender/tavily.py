"""Tavily search client — the citation source for root-cause reports and PRs."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from mender.config import TavilyConfig
from mender.router.usage import UsageLedger, UsageRecord, now_ts

_TAVILY_COST_NOTE = "Tavily is billed per search credit; plan-dependent, not recorded as USD"


@dataclass(frozen=True)
class Citation:
    title: str
    url: str
    snippet: str
    score: float | None
    query: str

    def markdown(self) -> str:
        return f"- [{self.title}]({self.url}) — {self.snippet}"

    def pr_line(self) -> str:
        return f"- {self.title}: {self.url}"


@dataclass(frozen=True)
class SearchResult:
    query: str
    citations: list[Citation]
    degraded: bool
    error: str | None
    latency_ms: float
    record: UsageRecord


class TavilyClient:
    """Search with bounded retries; on exhaustion returns a degraded result, never raises."""

    def __init__(
        self,
        config: TavilyConfig,
        api_key: str,
        ledger: UsageLedger,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._api_key = api_key
        self._ledger = ledger
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_s,
            transport=transport,
        )
        self._sleep = sleep

    def search(self, query: str, *, purpose: str = "diagnosis") -> SearchResult:
        payload = {
            "query": query,
            "max_results": self._config.max_results,
            "search_depth": self._config.search_depth,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        started = time.perf_counter()
        attempts = self._config.max_retries + 1
        last_error: str | None = None
        citations: list[Citation] = []

        for attempt in range(attempts):
            try:
                response = self._client.post("/search", json=payload, headers=headers)
                if response.status_code == 200:
                    body = response.json()
                    citations = [
                        Citation(
                            title=str(item.get("title", "")),
                            url=str(item.get("url", "")),
                            snippet=str(item.get("content", item.get("snippet", ""))),
                            score=float(item["score"]) if item.get("score") is not None else None,
                            query=query,
                        )
                        for item in body.get("results", [])
                    ]
                    last_error = None
                    break
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                if response.status_code < 500 and response.status_code != 429:
                    break  # client errors will not succeed on retry
            except (httpx.HTTPError, ValueError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts - 1:
                self._sleep(self._config.retry_backoff_s * (2**attempt))

        latency_ms = (time.perf_counter() - started) * 1000.0
        degraded = last_error is not None
        record = UsageRecord(
            ts=now_ts(),
            kind="tavily",
            tier="tavily",
            model="tavily-search",
            purpose=purpose,
            latency_ms=latency_ms,
            cost_usd=None,
            cost_note=_TAVILY_COST_NOTE,
            ok=not degraded,
            error=last_error,
        )
        self._ledger.add(record)
        return SearchResult(
            query=query,
            citations=citations,
            degraded=degraded,
            error=last_error,
            latency_ms=latency_ms,
            record=record,
        )
