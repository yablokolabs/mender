"""Verification loop: run tests, feed failures back, retry up to a bound."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field

from mender.patching import Patch, PatchError, apply_patch
from mender.sandbox.runner import SandboxResult, SandboxRunner

MAX_FEEDBACK_CHARS = 4_000


class Attempt(BaseModel):
    attempt: int
    exit_code: int
    timed_out: bool
    duration_ms: float
    passed: bool
    output_tail: str


class VerifyResult(BaseModel):
    passed: bool
    attempts: int
    command: list[str]
    changed_files: list[str] = Field(default_factory=list)
    attempt_log: list[Attempt] = Field(default_factory=list)

    @property
    def last_output(self) -> str:
        return self.attempt_log[-1].output_tail if self.attempt_log else ""


RepairFn = Callable[[str], Patch]


def verify_with_repair(
    runner: SandboxRunner,
    workdir: Path,
    command: list[str],
    *,
    max_retries: int,
    timeout_s: int,
    allowed_paths: set[str],
    repair: RepairFn | None = None,
) -> VerifyResult:
    """Run tests in the sandbox; on failure call `repair(failure_output)` and retry."""
    attempt_log: list[Attempt] = []
    changed: list[str] = []

    for attempt in range(1, max_retries + 2):
        result: SandboxResult = runner.run(workdir, command, timeout_s=timeout_s)
        attempt_log.append(
            Attempt(
                attempt=attempt,
                exit_code=result.exit_code,
                timed_out=result.timed_out,
                duration_ms=result.duration_ms,
                passed=result.passed,
                output_tail=result.output_tail,
            )
        )
        if result.passed:
            return VerifyResult(
                passed=True,
                attempts=attempt,
                command=command,
                changed_files=changed,
                attempt_log=attempt_log,
            )
        if attempt > max_retries or repair is None:
            break
        failure_feedback = result.output_tail[-MAX_FEEDBACK_CHARS:]
        patch = repair(failure_feedback)
        try:
            changed = list(set(changed) | set(apply_patch(patch, workdir, allowed_paths)))
        except PatchError as exc:
            changed.append(f"## patch repair error (no further retries): {exc}")
            break

    return VerifyResult(
        passed=False,
        attempts=len(attempt_log),
        command=command,
        changed_files=changed,
        attempt_log=attempt_log,
    )
