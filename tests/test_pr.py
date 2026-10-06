from pathlib import Path

from conftest import FIXTURES

from mender.diagnosis import RootCauseReport
from mender.evidence import ClusterEvidence, CommandResult
from mender.patching import Patch, PatchFile
from mender.pr import PRPayload, branch_name, build_payload, open_pr
from mender.sandbox.verify import Attempt, VerifyResult


def _report() -> RootCauseReport:
    import json

    data = json.loads((FIXTURES / "tavily_search_response.json").read_text())
    results = data.get("results", [])
    from mender.tavily import Citation

    citations = [
        Citation(
            title=str(r.get("title", "")),
            url=str(r.get("url", "")),
            snippet=str(r.get("content", "")),
            score=None,
            query="OOMKilled",
        )
        for r in results[:2]
    ]
    return RootCauseReport(
        service="checkout",
        namespace="shop",
        title="checkout OOMKilled by memory limit",
        root_cause="limit 64Mi below heap 96Mi [1]",
        mechanism="RSS exceeds limit → OOM kill → CrashLoopBackOff",
        labels=["oomkilled", "memory_limit"],
        confidence=0.9,
        evidence_refs=["Warning OOMKilled"],
        search_queries=["OOMKilled memory limit"],
        sources=citations,
        model="nvidia/test-ultra",
    )


def _verify(passed: bool = True) -> VerifyResult:
    return VerifyResult(
        passed=passed,
        attempts=1,
        command=["pytest", "-q"],
        changed_files=["deploy.yaml"],
        attempt_log=[
            Attempt(
                attempt=1,
                exit_code=0 if passed else 1,
                timed_out=False,
                duration_ms=1200.0,
                passed=passed,
                output_tail="3 passed" if passed else "1 failed",
            )
        ],
    )


def _evidence() -> ClusterEvidence:
    return ClusterEvidence(
        service="checkout",
        namespace="shop",
        collected_at="2026-10-06T14:00:00+00:00",
    )


def _payload() -> PRPayload:
    return build_payload(
        _report(),
        Patch(
            files=[PatchFile(path="deploy.yaml", content="memory: 512Mi")],
            rationale="raise limit",
        ),
        _verify(),
        _evidence(),
    )


def test_payload_contains_required_sections() -> None:
    payload = _payload()
    assert payload.title.startswith("Fix checkout:")
    assert "## Root cause" in payload.body
    assert "## Mechanism" in payload.body
    assert "## Sandbox test results" in payload.body
    assert "**PASSED**" in payload.body
    assert "## Tavily sources used" in payload.body
    assert "http" in payload.body
    assert "Do not auto-merge" in payload.body


def test_branch_is_slugified_and_stable() -> None:
    branch = _payload().branch
    assert branch.startswith("mender/checkout-")
    assert branch == branch_name("checkout", _report())
    assert len(branch.split("-")[-1]) == 7


class RecordingRunner:
    def __init__(self, responses: dict[str, tuple[int, str, str]] | None = None) -> None:
        self.calls: list[list[str]] = []
        self.responses = responses or {}

    def __call__(self, argv: list[str], cwd: Path) -> CommandResult:
        self.calls.append(argv)
        key = f" {' '.join(argv)} "
        for needle, (code, out, err) in self.responses.items():
            if f" {needle} " in key:
                return CommandResult(argv=argv, exit_code=code, stdout=out, stderr=err)
        return CommandResult(argv=argv, exit_code=0, stdout="main", stderr="")


def test_prepare_mode_branches_and_commits(tmp_path: Path) -> None:
    payload = _payload()
    runner = RecordingRunner(
        {
            "rev-parse --abbrev-ref": (0, "main\n", ""),
            "status --porcelain": (0, " M deploy.yaml\n", ""),
        }
    )
    result = open_pr(payload, tmp_path, tmp_path / "pr-body.md", mode="prepare", runner=runner)
    assert result.error is None
    assert result.opened is False
    assert result.branch == payload.branch
    assert (tmp_path / "pr-body.md").read_text() == payload.body

    joined = [" ".join(call) for call in runner.calls]
    assert any("checkout -b" in c for c in joined)
    assert any("git add -A" in c for c in joined)
    commit_calls = [c for c in joined if c.startswith("git commit -m")]
    assert len(commit_calls) == 1
    # Commit subject is the plain title: no trailers, no attribution.
    commit_argv = next(c for c in runner.calls if c[0] == "git" and c[1] == "commit")
    assert commit_argv[-1] == payload.title
    assert not any("Co-Authored" in arg for call in runner.calls for arg in call)


def test_prepare_mode_without_changes_skips_commit(tmp_path: Path) -> None:
    payload = _payload()
    runner = RecordingRunner(
        {"rev-parse --abbrev-ref": (0, "main\n", ""), "status --porcelain": (0, "", "")}
    )
    result = open_pr(payload, tmp_path, tmp_path / "pr-body.md", mode="prepare", runner=runner)
    assert result.error is None
    assert not any(call[:2] == ["git", "commit"] for call in runner.calls)


def test_not_a_repo_returns_error(tmp_path: Path) -> None:
    payload = _payload()
    runner = RecordingRunner({"rev-parse": (128, "", "fatal: not a git repository")})
    result = open_pr(payload, tmp_path, tmp_path / "pr-body.md", mode="prepare", runner=runner)
    assert result.error is not None and "not a git repository" in result.error
    assert result.opened is False


def test_gh_mode_pushes_and_creates_pr(tmp_path: Path) -> None:
    payload = _payload()
    runner = RecordingRunner(
        {
            "rev-parse --abbrev-ref": (0, "main\n", ""),
            "status --porcelain": (0, " M deploy.yaml\n", ""),
            "push": (0, "", ""),
            "gh pr create": (
                0,
                "Creating pull request...\nhttps://github.com/x/y/pull/1\n",
                "",
            ),
        }
    )
    result = open_pr(payload, tmp_path, tmp_path / "pr-body.md", mode="gh", runner=runner)
    assert result.opened is True
    assert result.url == "https://github.com/x/y/pull/1"
    joined = [" ".join(call) for call in runner.calls]
    assert any("git push -u origin" in c for c in joined)
    create = next(c for c in runner.calls if c[:3] == ["gh", "pr", "create"])
    assert "--body-file" in create
    # Mender never merges: no merge-capable command may appear.
    assert not any("merge" in arg for call in runner.calls for arg in call)


def test_unknown_mode_returns_error(tmp_path: Path) -> None:
    payload = _payload()
    runner = RecordingRunner({"rev-parse --abbrev-ref": (0, "main\n", "")})
    result = open_pr(payload, tmp_path, tmp_path / "pr-body.md", mode="weird", runner=runner)
    assert result.error is not None and "unknown pr mode" in result.error


def test_failed_verification_payload_marked(tmp_path: Path) -> None:
    payload = build_payload(
        _report(),
        Patch(files=[PatchFile(path="a.yaml", content="x")]),
        _verify(passed=False),
        _evidence(),
    )
    assert "**FAILED**" in payload.body
