"""Collect the cluster evidence a diagnosis runs on (kubectl behind a runner)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_LOG_LIMIT = 20_000
DEFAULT_DESCRIBE_LIMIT = 40_000
DEFAULT_EVENTS_LIMIT = 12_000


@dataclass(frozen=True)
class CommandResult:
    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str


CommandRunner = Callable[[list[str]], CommandResult]


def run_in(argv: list[str], *, cwd: Path | None = None) -> CommandResult:
    """Run a command for real (kubectl, git, gh); injectable in tests."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=120, cwd=cwd)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(argv=argv, exit_code=127, stdout="", stderr=str(exc))
    return CommandResult(
        argv=argv, exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr
    )


def run_here(argv: list[str]) -> CommandResult:
    """Zero-argument runner adapter for CommandRunner slots (ambient cwd)."""
    return run_in(argv)


class ClusterEvidence(BaseModel):
    service: str
    namespace: str
    collected_at: str
    context: str | None = None
    pod_lines: list[str] = Field(default_factory=list)
    describe: str = ""
    events: str = ""
    logs: str = ""
    manifests: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)

    def render(self, *, log_limit: int = DEFAULT_LOG_LIMIT) -> str:
        """Compact text block for prompts, with bounded log size."""
        sections = [
            f"SERVICE: {self.service} (namespace {self.namespace})",
            "PODS:\n" + ("\n".join(self.pod_lines) or "(no pod output)"),
            "EVENTS:\n" + (self.events[:DEFAULT_EVENTS_LIMIT] or "(none)"),
            "DESCRIBE:\n" + (self.describe[:DEFAULT_DESCRIBE_LIMIT] or "(none)"),
            "LOGS:\n" + (self.logs[:log_limit] or "(none)"),
        ]
        if self.manifests:
            rendered = "\n\n".join(
                f"# {path}\n{body}" for path, body in sorted(self.manifests.items())
            )
            sections.append("MANIFESTS:\n" + rendered)
        if self.notes:
            sections.append("NOTES:\n" + "\n".join(f"- {note}" for note in self.notes))
        return "\n\n".join(sections)


class EvidenceCollector:
    """Runs kubectl read-only commands through an injectable runner."""

    def __init__(self, runner: CommandRunner, *, log_limit: int = DEFAULT_LOG_LIMIT) -> None:
        self._runner = runner
        self._log_limit = log_limit

    def _run(self, argv: list[str], notes: list[str]) -> str:
        result = self._runner(argv)
        if result.exit_code != 0:
            detail = result.stderr.strip()[:200]
            notes.append(f"command failed ({result.exit_code}): {' '.join(argv)}: {detail}")
        return result.stdout

    def collect(
        self,
        service: str,
        namespace: str = "default",
        *,
        context: str | None = None,
        manifests: dict[str, str] | None = None,
    ) -> ClusterEvidence:
        notes: list[str] = []
        kubectl = ["kubectl"]
        if context:
            kubectl += ["--context", context]

        pods = self._run([*kubectl, "get", "pods", "-n", namespace, "-o", "wide"], notes)
        describe = self._run(
            [*kubectl, "describe", "pods", "-n", namespace, "-l", f"app={service}"],
            notes,
        )
        events = self._run(
            [*kubectl, "get", "events", "-n", namespace, "--sort-by=.lastTimestamp"],
            notes,
        )
        logs = self._run(
            [
                *kubectl,
                "logs",
                "-n",
                namespace,
                "-l",
                f"app={service}",
                "--all-containers",
                "--tail=400",
            ],
            notes,
        )
        # Bound captured logs to the limit, keeping the tail — errors are recent.
        if len(logs) > self._log_limit:
            logs = logs[-self._log_limit :]

        return ClusterEvidence(
            service=service,
            namespace=namespace,
            collected_at=datetime.now(UTC).isoformat(timespec="seconds"),
            context=context,
            pod_lines=[line for line in pods.splitlines() if line.strip()],
            describe=describe,
            events=events,
            logs=logs,
            manifests=manifests or {},
            notes=notes,
        )
