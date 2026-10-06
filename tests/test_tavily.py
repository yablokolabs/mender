import json
from pathlib import Path

import httpx

from mender.config import TavilyConfig
from mender.router.usage import UsageLedger
from mender.tavily import TavilyClient

FIXTURES = Path(__file__).parent / "fixtures"


def _config(**overrides: object) -> TavilyConfig:
    base: dict[str, object] = {
        "max_results": 3,
        "search_depth": "basic",
        "max_retries": 2,
        "retry_backoff_s": 0.0,
    }
    base.update(overrides)
    return TavilyConfig.model_validate(base)


def _fixture_body() -> dict:
    return json.loads((FIXTURES / "tavily_search_response.json").read_text())


def test_search_maps_results_to_citations(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        body = json.loads(request.content)
        assert body["query"] == "kubernetes pod OOMKilled root cause"
        return httpx.Response(200, json=_fixture_body())

    ledger = UsageLedger(tmp_path / "usage.jsonl")
    client = TavilyClient(_config(), "test-key", ledger, transport=httpx.MockTransport(handler))
    result = client.search("kubernetes pod OOMKilled root cause")

    assert result.degraded is False
    assert result.error is None
    assert len(result.citations) >= 1
    citation = result.citations[0]
    assert citation.url.startswith("http")
    assert citation.title
    assert citation.query == "kubernetes pod OOMKilled root cause"
    assert citation.markdown().startswith("- [")

    records = ledger.records
    assert len(records) == 1
    assert records[0].kind == "tavily"
    assert records[0].ok is True
    assert records[0].cost_usd is None


def test_retries_on_429_then_succeeds(tmp_path: Path) -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, json=_fixture_body())

    ledger = UsageLedger(tmp_path / "usage.jsonl")
    client = TavilyClient(
        _config(max_retries=3),
        "test-key",
        ledger,
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    result = client.search("OOMKilled")
    assert result.degraded is False
    assert len(attempts) == 3


def test_exhausted_retries_returns_degraded(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    ledger = UsageLedger(tmp_path / "usage.jsonl")
    client = TavilyClient(
        _config(max_retries=1),
        "test-key",
        ledger,
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    result = client.search("anything")
    assert result.degraded is True
    assert result.citations == []
    assert result.error is not None and "429" in result.error

    records = ledger.records
    assert records[0].ok is False
    assert records[0].error is not None and "429" in records[0].error
