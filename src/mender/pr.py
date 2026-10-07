"""Pull-request payloads and opening via git/gh. Mender never merges anything."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field

from mender.diagnosis import RootCauseReport
from mender.evidence import ClusterEvidence, CommandResult, run_in
from mender.patching import Patch
from mender.sandbox.verify import VerifyResult

PrRunner = Callable[[list[str], Path], CommandResult]

_SLUG = re.compile(r"[^a-z0-9-]+")


class PRPayload(BaseModel):
    title: str
    branch: str
    base: str
    body: str
    files: list[str] = Field(default_factory=list)


class PROpenResult(BaseModel):
    mode: str
    opened: bool
    branch: str
    commit: str | None = None
    url: str | None = None
    body_path: str | None = None
    error: str | None = None
    notes: list[str] = Field(default_factory=list)


def short_id(service: str, report: RootCauseReport) -> str:
    seed = f"{service}:{report.title}:{report.triage_summary}"
    return hashlib.sha256(seed.encode()).hexdigest()[:7]


def branch_name(service: str, report: RootCauseReport) -> str:
    slug = _SLUG.sub("-", service.lower()).strip("-") or "service"
    return f"mender/{slug}-{short_id(service, report)}"


def build_payload(
    report: RootCauseReport,
    patch: Patch,
    verify: VerifyResult,
    evidence: ClusterEvidence,
    *,
    base: str = "main",
) -> PRPayload:
    title = f"Fix {evidence.service}: {report.title}"
    if len(title) > 90:
        title = title[:87] + "..."
    status = "PASSED" if verify.passed else "FAILED"
    attempts = "\n".join(
        (
            f"- attempt {a.attempt}: exit {a.exit_code}"
            f"{', timed out' if a.timed_out else ''}"
            f" in {a.duration_ms / 1000:.1f}s"
            f" — {'ok' if a.passed else 'failed'}"
        )
        for a in verify.attempt_log
    )
    sources = "\n".join(citation.pr_line(number=i + 1) for i, citation in enumerate(report.sources))
    if not sources:
        sources = "- (Tavily returned no results)"
    refs = [f"- {ref}" for ref in report.evidence_refs] or ["- (none recorded)"]
    queries_line = f"Queries: {'; '.join(report.search_queries)}" if report.search_queries else ""

    body = "\n".join(
        [
            "## Root cause",
            report.root_cause,
            "",
            "## Mechanism",
            report.mechanism,
            "",
            f"Confidence: {report.confidence:.2f} · Labels: {', '.join(report.labels) or 'n/a'}",
            "",
            "## Evidence relied on",
            *refs,
            "",
            "## Change",
            f"Files: {', '.join(patch.paths)}",
            f"Rationale: {patch.rationale or '(none given)'}",
            "",
            "## Sandbox test results",
            f"Command: `{' '.join(verify.command)}` — **{status}** in {verify.attempts} attempt(s)",
            attempts,
            "",
            "## Tavily sources used",
            queries_line,
            sources,
            "",
            "## How this was verified",
            "Tests ran in an isolated container (`docker run --rm --network none`), "
            f"replaying the sandbox command above. Evidence captured at {evidence.collected_at}.",
            "",
            "---",
            "Opened by Mender for human review. Do not auto-merge; a person must review "
            "and merge this PR.",
        ]
    )
    return PRPayload(
        title=title,
        branch=branch_name(evidence.service, report),
        base=base,
        body=body,
        files=list(patch.paths),
    )


def _default_runner(argv: list[str], cwd: Path) -> CommandResult:
    return run_in(argv, cwd=cwd)


def open_pr(
    payload: PRPayload,
    workdir: Path,
    body_path: Path,
    *,
    mode: str = "prepare",
    runner: PrRunner | None = None,
) -> PROpenResult:
    """Commit the change on a fresh branch; optionally open the PR with gh.

    mode="prepare": branch + commit + PR body file (no network).
    mode="gh": additionally push and `gh pr create`. Mender never merges.
    """
    run = runner or _default_runner
    notes: list[str] = []
    body_path.parent.mkdir(parents=True, exist_ok=True)
    body_path.write_text(payload.body, encoding="utf-8")

    head = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], workdir)
    if head.exit_code != 0:
        return PROpenResult(
            mode=mode,
            opened=False,
            branch=payload.branch,
            body_path=str(body_path),
            error=f"not a git repository: {head.stderr.strip()[:200]}",
        )
    base = head.stdout.strip()
    if base in {"", "HEAD"}:
        # Detached HEAD: fall back to the payload's configured base branch.
        base = payload.base
    if base == payload.branch:
        notes.append("already on the Mender branch; reusing it")
    else:
        created = run(["git", "checkout", "-b", payload.branch], workdir)
        if created.exit_code != 0:
            return PROpenResult(
                mode=mode,
                opened=False,
                branch=payload.branch,
                body_path=str(body_path),
                error=f"git checkout -b failed: {created.stderr.strip()[:200]}",
            )

    # Stage ONLY the files Mender is allowed to change. A bare `git add -A`
    # would sweep unrelated work-in-progress (and, in a repo without a
    # .gitignore, credentials) into the Mender branch.
    if payload.files:
        add = run(["git", "add", "--", *payload.files], workdir)
    else:
        add = run(["git", "add", "-A"], workdir)
    if add.exit_code != 0:
        return PROpenResult(
            mode=mode,
            opened=False,
            branch=payload.branch,
            body_path=str(body_path),
            error=f"git add failed: {add.stderr.strip()[:200]}",
        )

    staged = run(["git", "diff", "--cached", "--quiet"], workdir)
    if staged.exit_code == 0:
        notes.append("no file changes to commit")
    else:
        commit = run(["git", "commit", "-m", payload.title], workdir)
        if commit.exit_code != 0:
            return PROpenResult(
                mode=mode,
                opened=False,
                branch=payload.branch,
                body_path=str(body_path),
                error=f"git commit failed: {commit.stderr.strip()[:200]}",
            )

    sha = run(["git", "rev-parse", "--short", "HEAD"], workdir)
    commit_sha = sha.stdout.strip() or None

    if mode == "prepare":
        return PROpenResult(
            mode=mode,
            opened=False,
            branch=payload.branch,
            commit=commit_sha,
            body_path=str(body_path),
            notes=[*notes, "PR prepared locally; body written for review"],
        )
    if mode != "gh":
        return PROpenResult(
            mode=mode,
            opened=False,
            branch=payload.branch,
            commit=commit_sha,
            body_path=str(body_path),
            error=f"unknown pr mode: {mode}",
        )

    push = run(["git", "push", "-u", "origin", payload.branch], workdir)
    if push.exit_code != 0:
        return PROpenResult(
            mode=mode,
            opened=False,
            branch=payload.branch,
            commit=commit_sha,
            body_path=str(body_path),
            error=f"git push failed: {push.stderr.strip()[:200]}",
        )

    create = run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base,
            "--title",
            payload.title,
            "--body-file",
            str(body_path),
        ],
        workdir,
    )
    if create.exit_code != 0:
        return PROpenResult(
            mode=mode,
            opened=False,
            branch=payload.branch,
            commit=commit_sha,
            body_path=str(body_path),
            error=f"gh pr create failed: {create.stderr.strip()[:200]}",
        )
    url_match = re.search(r"https://\S+/pull/\d+", create.stdout)
    url = url_match.group(0) if url_match else None
    return PROpenResult(
        mode=mode,
        opened=True,
        branch=payload.branch,
        commit=commit_sha,
        url=url,
        body_path=str(body_path),
        notes=notes,
    )
