import json
from pathlib import Path

import httpx
from conftest import FakeSender, make_client

from mender.config import MenderConfig
from mender.evidence import ClusterEvidence, CommandResult
from mender.pipeline import load_run, run_pipeline
from mender.router.usage import UsageLedger
from mender.sandbox.runner import SandboxResult
from mender.tavily import TavilyClient

TRIAGE_JSON = json.dumps(
    {
        "summary": "checkout crash loops after OOMKilled",
        "severity": "high",
        "suspects": ["memory limits"],
        "signals": ["OOMKilled"],
        "search_queries": ["OOMKilled memory limit"],
    }
)
QUERIES_JSON = json.dumps({"queries": ["OOMKilled memory limit kubernetes"]})
REPORT_JSON = json.dumps(
    {
        "title": "checkout OOMKilled by memory limit",
        "root_cause": "container limit 64Mi is below the 96Mi heap [1]",
        "mechanism": "heap grows -> kernel OOM kill -> CrashLoopBackOff",
        "labels": ["oomkilled", "memory_limit"],
        "confidence": 0.9,
        "evidence_refs": ["Warning OOMKilled"],
    }
)
PATCH_JSON = json.dumps(
    {
        "files": [{"path": "deploy.yaml", "content": "memory: 512Mi\n"}],
        "rationale": "raise limit above heap",
    }
)


def _config() -> MenderConfig:
    return MenderConfig.model_validate(
        {
            "router": {
                "tiers": {
                    "nano": {"model": "nvidia/test-nano"},
                    "ultra": {"model": "nvidia/test-ultra"},
                    "super": {"model": "nvidia/test-super"},
                }
            },
            "sandbox": {"max_retries": 0, "timeout_s": 30},
            "tavily": {"max_results": 3, "retry_backoff_s": 0.0},
        }
    )


def _evidence() -> ClusterEvidence:
    return ClusterEvidence(
        service="checkout",
        namespace="shop",
        collected_at="2026-10-06T14:00:00+00:00",
        events="Warning OOMKilled",
        logs="Killed",
    )


class PassRunner:
    def run(self, workdir: Path, command: list[str], *, timeout_s: int) -> SandboxResult:
        return SandboxResult(
            command=command, exit_code=0, stdout="3 passed", stderr="", duration_ms=10.0
        )


class FailRunner:
    def run(self, workdir: Path, command: list[str], *, timeout_s: int) -> SandboxResult:
        return SandboxResult(
            command=command,
            exit_code=1,
            stdout="",
            stderr="assert False: still broken",
            duration_ms=10.0,
        )


class RecordingPrRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], cwd: Path) -> CommandResult:
        self.calls.append(argv)
        key = f" {' '.join(argv)} "
        if " rev-parse --abbrev-ref " in key:
            return CommandResult(argv=argv, exit_code=0, stdout="main\n", stderr="")
        if " status --porcelain " in key:
            return CommandResult(argv=argv, exit_code=0, stdout=" M deploy.yaml\n", stderr="")
        return CommandResult(argv=argv, exit_code=0, stdout="", stderr="")


def _tavily(ledger: UsageLedger) -> TavilyClient:
    fixture: dict[str, object] = json.loads(
        (Path(__file__).parent / "fixtures" / "tavily_search_response.json").read_text()
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=fixture)

    config = _config().tavily
    return TavilyClient(config, "test-key", ledger, transport=httpx.MockTransport(handler))


def test_happy_path_prepares_pr(tmp_path: Path, ledger: UsageLedger) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "deploy.yaml").write_text("memory: 64Mi\n")
    out_dir = tmp_path / "run"

    sender = FakeSender([TRIAGE_JSON, QUERIES_JSON, REPORT_JSON, PATCH_JSON])
    client = make_client(sender, ledger)
    pr_runner = RecordingPrRunner()

    result = run_pipeline(
        client=client,
        tavily=_tavily(ledger),
        evidence=_evidence(),
        workdir=workdir,
        test_files=["deploy.yaml"],
        test_command=["pytest", "-q"],
        runner=PassRunner(),
        config=_config(),
        out_dir=out_dir,
        pr_mode="prepare",
        pr_runner=pr_runner,
    )

    assert result.status == "pr-prepared"
    assert result.verify is not None and result.verify.passed is True
    assert result.pr is not None and result.pr.error is None
    assert (workdir / "deploy.yaml").read_text() == "memory: 512Mi\n"
    for artifact in (
        "evidence.json",
        "triage.json",
        "report.json",
        "report.md",
        "patch.json",
        "verify.json",
        "pr-payload.json",
        "pr-body.md",
        "pr-open.json",
        "timings.json",
        "run-meta.json",
    ):
        assert (out_dir / artifact).is_file(), artifact
    assert ledger.path.is_file(), "usage ledger must be written"
    assert result.timings.total_ms > 0
    assert any(call[:2] == ["git", "checkout"] for call in pr_runner.calls)


def test_failed_verification_makes_no_pr(tmp_path: Path, ledger: UsageLedger) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "deploy.yaml").write_text("memory: 64Mi\n")

    sender = FakeSender([TRIAGE_JSON, QUERIES_JSON, REPORT_JSON, PATCH_JSON])
    client = make_client(sender, ledger)

    result = run_pipeline(
        client=client,
        tavily=_tavily(ledger),
        evidence=_evidence(),
        workdir=workdir,
        test_files=["deploy.yaml"],
        test_command=["pytest", "-q"],
        runner=FailRunner(),
        config=_config(),
        out_dir=tmp_path / "run2",
        pr_mode="prepare",
        pr_runner=RecordingPrRunner(),
    )
    assert result.status == "verify-failed"
    assert result.pr is None
    assert result.verify is not None and result.verify.passed is False
    assert not (tmp_path / "run2" / "pr-body.md").exists()


def test_fix_mode_skips_pr_entirely(tmp_path: Path, ledger: UsageLedger) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "deploy.yaml").write_text("memory: 64Mi\n")

    sender = FakeSender([TRIAGE_JSON, QUERIES_JSON, REPORT_JSON, PATCH_JSON])
    client = make_client(sender, ledger)
    result = run_pipeline(
        client=client,
        tavily=_tavily(ledger),
        evidence=_evidence(),
        workdir=workdir,
        test_files=["deploy.yaml"],
        test_command=["pytest"],
        runner=PassRunner(),
        config=_config(),
        out_dir=tmp_path / "run3",
        pr_mode=None,
    )
    assert result.status == "verified"
    assert result.pr is None


def test_load_run_roundtrip(tmp_path: Path, ledger: UsageLedger) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "deploy.yaml").write_text("memory: 64Mi\n")
    out_dir = tmp_path / "run4"
    sender = FakeSender([TRIAGE_JSON, QUERIES_JSON, REPORT_JSON, PATCH_JSON])
    client = make_client(sender, ledger)
    run_pipeline(
        client=client,
        tavily=_tavily(ledger),
        evidence=_evidence(),
        workdir=workdir,
        test_files=["deploy.yaml"],
        test_command=["pytest"],
        runner=PassRunner(),
        config=_config(),
        out_dir=out_dir,
        pr_mode="prepare",
        pr_runner=RecordingPrRunner(),
    )
    loaded = load_run(out_dir)
    assert loaded.service == "checkout"
    assert loaded.report.labels == ["oomkilled", "memory_limit"]
    assert loaded.verify is not None and loaded.verify.passed is True
    assert loaded.pr is not None
    assert loaded.patch is not None and loaded.patch.paths == ["deploy.yaml"]
