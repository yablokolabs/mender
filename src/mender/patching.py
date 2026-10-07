"""Super-tier patch writing: propose complete replacement files, apply them safely."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from mender.diagnosis import RootCauseReport
from mender.evidence import ClusterEvidence
from mender.modelio import complete_json
from mender.router.client import Message, ModelClient

MAX_FILE_CHARS = 30_000
MAX_FEEDBACK_CHARS = 4_000

_PATCH_SYSTEM = (
    "You are the patch stage of a Kubernetes incident agent. You receive a root-cause "
    "report and the current contents of exactly the files you are allowed to change. "
    "Produce the smallest correct fix for the root cause. Respond with ONLY a JSON object:\n"
    '{"files": [{"path": str, "content": str}], "rationale": str}\n'
    "- path must match one of the allowed files exactly (no new paths, no absolute paths)\n"
    "- content is the COMPLETE new file content, not a diff\n"
    "- keep unrelated behaviour unchanged"
)


class PatchError(RuntimeError):
    """The model proposed a patch that cannot be applied safely."""


class PatchFile(BaseModel):
    path: str
    content: str


class Patch(BaseModel):
    files: list[PatchFile] = Field(default_factory=list)
    rationale: str = ""
    model: str = ""

    @property
    def paths(self) -> list[str]:
        return [f.path for f in self.files]

    @classmethod
    def from_model_json(cls, data: object, *, model: str) -> Patch:
        if not isinstance(data, dict):
            raise PatchError(f"patch reply was not a JSON object: {str(data)[:120]}")
        raw_files = data.get("files", [])
        files = [
            PatchFile(path=str(item.get("path", "")), content=str(item.get("content", "")))
            for item in raw_files
            if isinstance(item, dict) and str(item.get("path", "")).strip()
        ]
        if not files:
            raise PatchError("model proposed no files")
        return cls(
            files=files,
            rationale=str(data.get("rationale", "")),
            model=model,
        )


def _allowed_block(allowed: dict[str, str]) -> str:
    blocks = []
    for path in sorted(allowed):
        body = allowed[path]
        if len(body) > MAX_FILE_CHARS:
            body = body[:MAX_FILE_CHARS] + "\n... (truncated)"
        blocks.append(f"=== FILE: {path} ===\n{body}")
    return "\n\n".join(blocks)


def propose_patch(
    client: ModelClient,
    report: RootCauseReport,
    evidence: ClusterEvidence,
    allowed_files: dict[str, str],
    *,
    feedback: str | None = None,
) -> Patch:
    """Ask the super tier for replacement contents of `allowed_files` only."""
    user_parts = [
        f"ROOT CAUSE:\n{report.root_cause}\n\nMECHANISM:\n{report.mechanism}",
        f"EVIDENCE (service {evidence.service}):\n{evidence.render(log_limit=4_000)}",
        f"ALLOWED FILES (path must match exactly):\n{_allowed_block(allowed_files)}",
    ]
    if feedback:
        user_parts.append(
            "TEST FAILURE FEEDBACK FROM THE PREVIOUS ATTEMPT (fix this too):\n"
            + feedback[-MAX_FEEDBACK_CHARS:]
        )
    reply = complete_json(
        client,
        "super",
        [
            Message(role="system", content=_PATCH_SYSTEM),
            Message(role="user", content="\n\n".join(user_parts)),
        ],
        purpose="patch",
    )
    return Patch.from_model_json(reply, model=client.tier("super").model)


def validate_patch(patch: Patch, allowed: set[str]) -> None:
    """Reject path escapes and files outside the allowed set."""
    seen: set[str] = set()
    for patch_file in patch.files:
        path = patch_file.path
        if path in seen:
            raise PatchError(f"duplicate path in patch: {path}")
        seen.add(path)
        if path.startswith("/") or ".." in Path(path).parts or "\\" in path:
            raise PatchError(f"unsafe patch path: {path}")
        if path not in allowed:
            raise PatchError(f"patch path outside allowed set: {path}")


def _resolve_within(workdir: Path, path: str) -> Path:
    """Resolve `path` under `workdir`, rejecting symlinks that escape it."""
    target = workdir / path
    resolved = target.resolve()
    if not resolved.is_relative_to(workdir.resolve()):
        raise PatchError(f"patch path escapes workdir via symlink: {path}")
    return target


def apply_patch(patch: Patch, workdir: Path, allowed: set[str]) -> list[str]:
    """Write the patch into `workdir`; returns paths whose content actually changed."""
    validate_patch(patch, allowed)
    changed: list[str] = []
    for patch_file in patch.files:
        target = _resolve_within(workdir, patch_file.path)
        before = target.read_text(encoding="utf-8") if target.is_file() else None
        if before == patch_file.content:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(patch_file.content, encoding="utf-8")
        changed.append(patch_file.path)
    return changed


def read_files(workdir: Path, paths: list[str]) -> dict[str, str]:
    """Read the current contents of the given repo-relative paths.

    Symlinks pointing outside `workdir` are skipped — their contents must not
    leak into the model prompt, and they are not safe write targets.
    """
    contents: dict[str, str] = {}
    workdir_resolved = workdir.resolve()
    for path in paths:
        candidate = workdir / path
        if candidate.is_symlink() and not candidate.resolve().is_relative_to(workdir_resolved):
            continue
        if candidate.is_file():
            contents[path] = candidate.read_text(encoding="utf-8")
    return contents


def patch_summary(patch: Patch) -> str:
    lines = [f"Patch by {patch.model}: {len(patch.files)} file(s)"]
    if patch.rationale:
        lines.append(f"Rationale: {patch.rationale}")
    return "\n".join(lines)
