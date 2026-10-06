from mender.evidence import ClusterEvidence, CommandResult, CommandRunner, EvidenceCollector


def _runner(outputs: dict[str, tuple[int, str, str]]) -> CommandRunner:
    def run(argv: list[str]) -> CommandResult:
        key = " ".join(argv)
        for needle, (code, out, err) in outputs.items():
            if needle in key:
                return CommandResult(argv=argv, exit_code=code, stdout=out, stderr=err)
        return CommandResult(argv=argv, exit_code=1, stdout="", stderr="unstubbed")

    return run


def test_collect_maps_kubectl_output() -> None:
    runner = _runner(
        {
            "get pods": (
                0,
                "NAME READY STATUS RESTARTS\nweb-0 0/1 CrashLoopBackOff 3\n",
                "",
            ),
            "describe": (0, "Name: web-0\nReason: OOMKilled\n", ""),
            "get events": (0, "1s  Warning  OOMKilled  pod/web-0\n", ""),
            "logs": (0, "fatal: memory limit exceeded\n", ""),
        }
    )
    collector = EvidenceCollector(runner)
    evidence = collector.collect("web", "shop")

    assert evidence.service == "web"
    assert evidence.namespace == "shop"
    assert any("CrashLoopBackOff" in line for line in evidence.pod_lines)
    assert "OOMKilled" in evidence.describe
    assert "Warning" in evidence.events
    assert "memory limit" in evidence.logs
    assert evidence.notes == []
    rendered = evidence.render()
    assert "SERVICE: web" in rendered and "MANIFESTS" not in rendered


def test_failed_commands_become_notes() -> None:
    runner = _runner(
        {
            "get pods": (1, "", "connection refused"),
            "describe": (0, "", ""),
            "get events": (0, "", ""),
            "logs": (0, "", ""),
        }
    )
    collector = EvidenceCollector(runner)
    evidence = collector.collect("web")
    assert any("connection refused" in note for note in evidence.notes)
    rendered = evidence.render()
    assert "NOTES:" in rendered and "connection refused" in rendered


def test_logs_truncated_to_limit_keeping_tail() -> None:
    body = "\n".join(f"line {i}" for i in range(1000))
    runner = _runner(
        {
            "get pods": (0, "", ""),
            "describe": (0, "", ""),
            "get events": (0, "", ""),
            "logs": (0, body, ""),
        }
    )
    collector = EvidenceCollector(runner, log_limit=100)
    evidence = collector.collect("web")
    assert len(evidence.logs) <= 100
    assert evidence.logs.endswith("line 999")


def test_manifests_rendered() -> None:
    evidence = ClusterEvidence(
        service="web",
        namespace="default",
        collected_at="2026-10-06T00:00:00+00:00",
        manifests={"deploy.yaml": "replicas: 2"},
    )
    assert "deploy.yaml" in evidence.render()
