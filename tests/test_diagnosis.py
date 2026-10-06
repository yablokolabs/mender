import json

import httpx
from conftest import FIXTURES, FakeSender, make_client

from mender.diagnosis import (
    RootCauseReport,
    diagnose,
    normalize_label,
    propose_queries,
    run_diagnosis,
)
from mender.evidence import ClusterEvidence
from mender.router.usage import UsageLedger
from mender.tavily import TavilyClient
from mender.triage import Triage

REPORT_JSON = json.dumps(
    {
        "title": "web-0 OOMKilled by memory limit",
        "root_cause": "The container memory limit is 64Mi but the JVM needs ~256Mi [1].",
        "mechanism": (
            "RSS grows past 64Mi → kernel OOM-kills PID 1 → restarts rise → CrashLoopBackOff."
        ),
        "labels": ["oomkilled", "memory_limit"],
        "confidence": 0.8,
        "evidence_refs": ["Warning OOMKilled", "fatal: out of memory"],
    }
)


def _evidence() -> ClusterEvidence:
    return ClusterEvidence(
        service="web",
        namespace="shop",
        collected_at="2026-10-06T00:00:00+00:00",
        pod_lines=["web-0  0/1  CrashLoopBackOff  3"],
        events="Warning OOMKilled",
        logs="fatal: out of memory",
    )


def _triage() -> Triage:
    return Triage(
        summary="web-0 crash loops after OOMKill",
        severity="high",
        suspects=["memory limits"],
        search_queries=["OOMKilled CrashLoopBackOff"],
    )


def _tavily(ledger: UsageLedger) -> TavilyClient:
    from mender.config import TavilyConfig

    fixture = json.loads((FIXTURES / "tavily_search_response.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=fixture)

    config = TavilyConfig(max_results=3, search_depth="basic", retry_backoff_s=0.0)
    return TavilyClient(config, "test-key", ledger, transport=httpx.MockTransport(handler))


def test_propose_queries_parses_list(ledger: UsageLedger) -> None:
    sender = FakeSender(['{"queries": ["OOMKilled limit", "exit code 137"]}'])
    client = make_client(sender, ledger)
    queries = propose_queries(client, _evidence(), _triage())
    assert queries == ["OOMKilled limit", "exit code 137"]


def test_propose_queries_falls_back_to_triage(ledger: UsageLedger) -> None:
    sender = FakeSender(['"not an object"'])
    client = make_client(sender, ledger)
    queries = propose_queries(client, _evidence(), _triage())
    assert queries == ["OOMKilled CrashLoopBackOff"]


def test_diagnosis_builds_report_with_sources(ledger: UsageLedger) -> None:
    sender = FakeSender([REPORT_JSON])
    client = make_client(sender, ledger)
    tavily = _tavily(ledger)
    results = [tavily.search("OOMKilled CrashLoopBackOff")]

    report = diagnose(client, _evidence(), _triage(), results)
    assert report.title.startswith("web-0")
    assert report.labels == ["oomkilled", "memory_limit"]
    assert report.confidence == 0.8
    assert len(report.sources) == 3
    assert report.tavily_degraded is False
    markdown = report.markdown()
    assert "## Tavily sources" in markdown
    assert any(citation.url in markdown for citation in report.sources)


def test_normalized_labels(ledger: UsageLedger) -> None:
    assert normalize_label("OOM Killed!") == "oom_killed"
    report = RootCauseReport.from_model_json(
        {"labels": ["OOMKilled", "bad image tag"], "root_cause": "x"},
        service="web",
        namespace="shop",
        triage=_triage(),
        queries=[],
        results=[],
        model="m",
    )
    assert report.normalized_labels == {"oomkilled", "bad_image_tag"}


def test_run_diagnosis_end_to_end_with_fakes(ledger: UsageLedger) -> None:
    sender = FakeSender(['{"queries": ["OOMKilled CrashLoopBackOff"]}', REPORT_JSON])
    client = make_client(sender, ledger)
    tavily = _tavily(ledger)

    report = run_diagnosis(client, tavily, _evidence(), _triage())
    assert report.sources, "Tavily sources must flow into the report"
    assert report.model == "nvidia/test-ultra"
    assert report.search_queries == ["OOMKilled CrashLoopBackOff"]
    # ledger has model + tavily records
    kinds = {record.kind for record in ledger.records}
    assert kinds == {"model", "tavily"}
