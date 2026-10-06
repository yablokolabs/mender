"""Sandbox runners: tests execute isolated from the host, behind one interface."""

from __future__ import annotations

import shlex
import subprocess
import time
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

OUTPUT_TAIL = 8_000


class SandboxResult(BaseModel):
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def output_tail(self) -> str:
        combined = (self.stdout + "\n" + self.stderr).strip()
        return combined[-OUTPUT_TAIL:]


class SandboxRunner(Protocol):
    def run(self, workdir: Path, command: list[str], *, timeout_s: int) -> SandboxResult:
        """Run `command` against `workdir` in isolation and return its outcome."""
        ...


def _tail(text: str, limit: int = OUTPUT_TAIL) -> str:
    return text[-limit:] if len(text) > limit else text


class DockerRunner:
    """Runs each command in a fresh `docker run --rm` container with the workdir mounted."""

    def __init__(self, image: str, *, docker_binary: str = "docker") -> None:
        self._image = image
        self._docker = docker_binary

    def run(self, workdir: Path, command: list[str], *, timeout_s: int) -> SandboxResult:
        argv = [
            self._docker,
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            "1g",
            "--cpus",
            "2",
            "-v",
            f"{workdir.resolve()}:/workspace",
            "-w",
            "/workspace",
            self._image,
            "sh",
            "-lc",
            shlex.join(command),
        ]
        started = time.perf_counter()
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout_s)
            result = SandboxResult(
                command=command,
                exit_code=proc.returncode,
                stdout=_tail(proc.stdout),
                stderr=_tail(proc.stderr),
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            result = SandboxResult(
                command=command,
                exit_code=124,
                stdout=_tail(stdout),
                stderr=_tail(stderr),
                timed_out=True,
            )
        except OSError as exc:
            result = SandboxResult(
                command=command,
                exit_code=127,
                stdout="",
                stderr=str(exc),
                timed_out=False,
            )
        result.duration_ms = (time.perf_counter() - started) * 1000.0
        return result
