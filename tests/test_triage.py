from conftest import FakeSender, make_client

from mender.evidence import ClusterEvidence
from mender.router.usage import UsageLedger
from mender.triage import Triage, triage


def _evidence() -> ClusterEvidence:
    return ClusterEvidence(
        service="web",
        namespace="shop",
        collected_at="2026-10-06T00:00:00+00:00",
        pod_lines=["web-0  0/1  CrashLoopBackOff  3"],
        events="Warning OOMKilled",
        logs="fatal: out of memory",
    )


def test_triage_parses_json_reply(ledger: UsageLedger) -> None:
    payload = (
        '{"summary": "web-0 crash loops after OOMKill", "severity": "high",'
        ' "suspects": ["memory limits"], "signals": ["OOMKilled"],'
        ' "search_queries": ["OOMKilled CrashLoopBackOff", "second", "third", "fourth"]}'
    )
    sender = FakeSender([payload])
    client = make_client(sender, ledger)

    result = triage(client, _evidence())
    assert result.severity == "high"
    assert result.suspects == ["memory limits"]
    assert len(result.search_queries) == 3  # capped
    assert result.model == "nvidia/test-nano"
    assert "CrashLoopBackOff" in sender.last_user_message()


def test_triage_normalizes_bad_severity(ledger: UsageLedger) -> None:
    sender = FakeSender(['{"summary": "x", "severity": "apocalyptic"}'])
    client = make_client(sender, ledger)
    result = triage(client, _evidence())
    assert result.severity == "unknown"


def test_triage_handles_non_dict_reply(ledger: UsageLedger) -> None:
    sender = FakeSender(['"just a string"'])
    client = make_client(sender, ledger)
    result = triage(client, _evidence())
    assert result.summary == "just a string"
    assert isinstance(result, Triage)
