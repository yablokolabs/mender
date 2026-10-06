import subprocess
from pathlib import Path

import pytest

from mender.patching import Patch, PatchError, PatchFile, apply_patch
from mender.sandbox.runner import DockerRunner, SandboxResult
from mender.sandbox.verify import verify_with_repair


class ScriptedRunner:
    """Returns preset results in order (last repeats) and records calls."""

    def __init__(self, results: list[SandboxResult]) -> None:
        self.results = results
        self.calls: list[list[str]] = []

    def run(self, workdir: Path, command: list[str], *, timeout_s: int) -> SandboxResult:
        self.calls.append(command)
        result = self.results[min(len(self.calls) - 1, len(self.results) - 1)]
        return result


def _result(exit_code: int, stdout: str = "", stderr: str = "") -> SandboxResult:
    return SandboxResult(command=["pytest"], exit_code=exit_code, stdout=stdout, stderr=stderr)


def test_verify_passes_first_attempt(tmp_path: Path) -> None:
    runner = ScriptedRunner([_result(0, stdout="3 passed")])
    outcome = verify_with_repair(
        runner,
        tmp_path,
        ["pytest"],
        max_retries=3,
        timeout_s=60,
        allowed_paths={"deploy.yaml"},
    )
    assert outcome.passed is True
    assert outcome.attempts == 1
    assert outcome.changed_files == []


def test_verify_repairs_with_feedback_then_passes(tmp_path: Path) -> None:
    (tmp_path / "deploy.yaml").write_text("memory: 64Mi")
    runner = ScriptedRunner(
        [
            _result(1, stderr="assert memory >= 512Mi FAILED"),
            _result(0, stdout="ok"),
        ]
    )
    feedbacks: list[str] = []

    def repair(feedback: str) -> Patch:
        feedbacks.append(feedback)
        return Patch(
            files=[PatchFile(path="deploy.yaml", content="memory: 512Mi")],
            rationale="retry",
        )

    outcome = verify_with_repair(
        runner,
        tmp_path,
        ["pytest"],
        max_retries=2,
        timeout_s=60,
        allowed_paths={"deploy.yaml"},
        repair=repair,
    )
    assert outcome.passed is True
    assert outcome.attempts == 2
    assert outcome.changed_files == ["deploy.yaml"]
    assert feedbacks and "FAILED" in feedbacks[0]
    assert (tmp_path / "deploy.yaml").read_text() == "memory: 512Mi"


def test_verify_stops_at_retry_limit(tmp_path: Path) -> None:
    runner = ScriptedRunner([_result(1, stderr="always broken")])
    repair_calls: list[str] = []

    def repair(feedback: str) -> Patch:
        repair_calls.append(feedback)
        return Patch(files=[PatchFile(path="deploy.yaml", content="x")])

    outcome = verify_with_repair(
        runner,
        tmp_path,
        ["pytest"],
        max_retries=2,
        timeout_s=60,
        allowed_paths={"deploy.yaml"},
        repair=repair,
    )
    assert outcome.passed is False
    assert outcome.attempts == 3  # initial + 2 retries
    assert len(repair_calls) == 2
    assert len(runner.calls) == 3


def test_timeout_counts_as_failure(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        [
            SandboxResult(
                command=["sleep"],
                exit_code=124,
                stdout="",
                stderr="",
                timed_out=True,
            )
        ]
    )
    outcome = verify_with_repair(
        runner,
        tmp_path,
        ["sleep", "999"],
        max_retries=0,
        timeout_s=1,
        allowed_paths=set(),
    )
    assert outcome.passed is False
    assert outcome.attempt_log[0].timed_out is True


def test_docker_runner_builds_isolated_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr("mender.sandbox.runner.subprocess.run", fake_run)
    runner = DockerRunner("python:3.12-slim")
    result = runner.run(tmp_path, ["pytest", "-q"], timeout_s=30)

    argv = captured["argv"]
    assert isinstance(argv, list)
    assert "--network" in argv and "none" in argv
    assert str(tmp_path.resolve()) + ":/workspace" in argv
    assert "python:3.12-slim" in argv
    assert result.passed is True
    assert result.stdout == "ok"


def test_docker_runner_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=argv, timeout=30, output=b"partial", stderr=b"")

    monkeypatch.setattr("mender.sandbox.runner.subprocess.run", fake_run)
    runner = DockerRunner("python:3.12-slim")
    result = runner.run(tmp_path, ["pytest"], timeout_s=30)
    assert result.timed_out is True
    assert result.exit_code == 124
    assert result.stdout == "partial"


def test_apply_patch_used_by_repair_is_safe(tmp_path: Path) -> None:
    # repair returning a disallowed path must raise, not write outside
    (tmp_path / "deploy.yaml").write_text("a")
    patch = Patch(files=[PatchFile(path="../outside.yaml", content="evil")])
    with pytest.raises(PatchError, match="unsafe"):
        apply_patch(patch, tmp_path, {"deploy.yaml"})
    assert not (tmp_path.parent / "outside.yaml").exists()
