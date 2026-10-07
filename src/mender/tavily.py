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

    def markdown(self, *, number: int | None = None) -> str:
        if number is not None:
            return f"[{number}] [{self.title}]({self.url}) — {self.snippet}"
        return f"- [{self.title}]({self.url}) — {self.snippet}"

    def pr_line(self, *, number: int | None = None) -> str:
        if number is not None:
            return f"[{number}] {self.title}: {self.url}"
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
            response: httpx.Response | None = None
            response_err: str | None = None
            try:
                response = self._client.post("/search", json=payload, headers=headers)
            except (httpx.HTTPError, ValueError) as exc:
                response_err = f"{type(exc).__name__}: {exc}"
            if response_err:
                last_error = response_err
                if attempt < attempts - 1:
                    self._sleep(self._config.retry_backoff_s * (2**attempt))
                continue

            # Response body parsing is outside the network-retry try block — a
            # bad JSON scaffold shape is a permanent error, not a transient one.
            if response is not None and response.status_code == 200:
                try:
                    body = response.json()
                except ValueError as exc:
                    last_error = f"bad HTTP response body: {exc}"
                    break
                try:
                    citations = []
                    for idx, item in enumerate(body.get("results", []), start=1):
                        title = (
                            str(item.get("title", "")) if isinstance(item.get("title"), str) else ""
                        )
                        url = str(item.get("url", "")) if isinstance(item.get("url"), str) else ""
                        snippet_raw = item.get("content") or item.get("snippet")
                        snippet = str(snippet_raw) if isinstance(snippet_raw, str) else ""
                        raw_score = item.get("score")
                        score: float | None = (
                            float(raw_score)
                            if raw_score is not None and isinstance(raw_score, (int, float))
                            else None
                        )
                        if title or url:
                            _ = idx
                            citations.append(
                                Citation(
                                    title=title,
                                    url=url,
                                    snippet=snippet,
                                    score=score,
                                    query=query,
                                )
                            )
                except (TypeError, ValueError) as exc:
                    last_error = f"bad HTTP response body: {exc}"
                    break
                last_error = None
                break

            if response is not None:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                if response.status_code < 500 and response.status_code != 429:
                    break  # client errors will not succeed on retry
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
