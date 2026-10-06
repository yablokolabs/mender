"""End-to-end incident pipeline: triage → diagnosis → patch → sandbox → PR."""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import BaseModel

from mender.config import MenderConfig
from mender.diagnosis import RootCauseReport, run_diagnosis
from mender.evidence import ClusterEvidence
from mender.patching import Patch, apply_patch, propose_patch, read_files
from mender.pr import PROpenResult, PRPayload, PrRunner, build_payload, open_pr
from mender.router.client import ModelClient
from mender.sandbox.runner import SandboxRunner
from mender.sandbox.verify import VerifyResult, verify_with_repair
from mender.tavily import TavilyClient
from mender.triage import Triage, triage


class PipelineError(RuntimeError):
    """The pipeline cannot continue (missing inputs, model failure)."""


class StageTimings(BaseModel):
    triage_ms: float = 0.0
    diagnosis_ms: float = 0.0
    patch_ms: float = 0.0
    verify_ms: float = 0.0
    pr_ms: float = 0.0
    total_ms: float = 0.0


class PipelineResult(BaseModel):
    status: str
    service: str
    namespace: str
    out_dir: str
    timings: StageTimings
    triage: Triage
    report: RootCauseReport
    patch: Patch | None = None
    verify: VerifyResult | None = None
    pr: PROpenResult | None = None


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def run_pipeline(
    *,
    client: ModelClient,
    tavily: TavilyClient,
    evidence: ClusterEvidence,
    workdir: Path,
    test_files: list[str],
    test_command: list[str],
    runner: SandboxRunner,
    config: MenderConfig,
    out_dir: Path,
    pr_mode: str | None = "prepare",
    pr_runner: PrRunner | None = None,
    progress: bool = False,
) -> PipelineResult:
    """Run one incident to a verified fix (and optionally an opened PR).

    Every stage writes its artifact into `out_dir`; failures are reported, not hidden.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evidence.json").write_text(evidence.model_dump_json(indent=2), encoding="utf-8")
    timings = StageTimings()
    total_started = time.perf_counter()

    if progress:
        print(f"[mender] triage ({evidence.service})...", flush=True)
    started = time.perf_counter()
    triage_result = triage(client, evidence)
    timings.triage_ms = _elapsed_ms(started)
    (out_dir / "triage.json").write_text(triage_result.model_dump_json(indent=2), encoding="utf-8")

    if progress:
        print("[mender] root-cause diagnosis with Tavily...", flush=True)
    started = time.perf_counter()
    report = run_diagnosis(client, tavily, evidence, triage_result)
    timings.diagnosis_ms = _elapsed_ms(started)
    (out_dir / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(report.markdown(), encoding="utf-8")

    allowed = read_files(workdir, test_files)
    if not allowed:
        raise PipelineError(f"none of the allowed patch files exist in {workdir}: {test_files}")
    allowed_paths = set(allowed)

    if progress:
        print("[mender] writing patch (super tier)...", flush=True)
    started = time.perf_counter()
    patch = propose_patch(client, report, evidence, allowed)
    changed = apply_patch(patch, workdir, allowed_paths)
    if progress:
        changed_desc = ", ".join(changed) or "(no content change)"
        print(f"[mender] applied patch to: {changed_desc}", flush=True)
    timings.patch_ms = _elapsed_ms(started)
    (out_dir / "patch.json").write_text(patch.model_dump_json(indent=2), encoding="utf-8")

    if progress:
        print(f"[mender] sandbox verification: {' '.join(test_command)}", flush=True)

    def repair(feedback: str) -> Patch:
        return propose_patch(client, report, evidence, allowed, feedback=feedback)

    started = time.perf_counter()
    verify = verify_with_repair(
        runner,
        workdir,
        test_command,
        max_retries=config.sandbox.max_retries,
        timeout_s=config.sandbox.timeout_s,
        allowed_paths=allowed_paths,
        repair=repair,
    )
    timings.verify_ms = _elapsed_ms(started)
    (out_dir / "verify.json").write_text(verify.model_dump_json(indent=2), encoding="utf-8")

    pr_result: PROpenResult | None = None
    status = "verified" if verify.passed else "verify-failed"
    if pr_mode is not None and verify.passed:
        if progress:
            print(f"[mender] preparing PR (mode {pr_mode})...", flush=True)
        started = time.perf_counter()
        payload: PRPayload = build_payload(report, patch, verify, evidence)
        (out_dir / "pr-payload.json").write_text(
            payload.model_dump_json(indent=2), encoding="utf-8"
        )
        pr_result = open_pr(
            payload,
            workdir,
            out_dir / "pr-body.md",
            mode=pr_mode,
            runner=pr_runner,
        )
        timings.pr_ms = _elapsed_ms(started)
        (out_dir / "pr-open.json").write_text(pr_result.model_dump_json(indent=2), encoding="utf-8")
        if pr_result.error:
            status = "pr-failed"
        elif pr_result.opened:
            status = "pr-opened"
        else:
            status = "pr-prepared"
    elif pr_mode is not None and not verify.passed:
        # A PR carries proof; without passing tests there is nothing to open.
        if progress:
            print("[mender] tests failed — no PR prepared", flush=True)

    timings.total_ms = _elapsed_ms(total_started)
    (out_dir / "timings.json").write_text(timings.model_dump_json(indent=2), encoding="utf-8")
    meta = {
        "workdir": str(workdir),
        "test_files": test_files,
        "test_command": test_command,
        "pr_mode": pr_mode,
    }
    (out_dir / "run-meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return PipelineResult(
        status=status,
        service=evidence.service,
        namespace=evidence.namespace,
        out_dir=str(out_dir),
        timings=timings,
        triage=triage_result,
        report=report,
        patch=patch,
        verify=verify,
        pr=pr_result,
    )


def load_run(out_dir: Path) -> PipelineResult:
    """Rebuild a result from artifacts so `mender pr` can run later."""

    def _read(name: str) -> str:
        path = out_dir / name
        if not path.is_file():
            raise PipelineError(f"missing artifact: {path}")
        return path.read_text(encoding="utf-8")

    def _optional(name: str) -> str | None:
        return _read(name) if (out_dir / name).is_file() else None

    evidence = ClusterEvidence.model_validate_json(_read("evidence.json"))
    patch_json = _optional("patch.json")
    verify_json = _optional("verify.json")
    pr_json = _optional("pr-open.json")
    timings_json = _optional("timings.json")
    return PipelineResult(
        status="loaded",
        service=evidence.service,
        namespace=evidence.namespace,
        out_dir=str(out_dir),
        timings=(
            StageTimings.model_validate_json(timings_json) if timings_json else StageTimings()
        ),
        triage=Triage.model_validate_json(_read("triage.json")),
        report=RootCauseReport.model_validate_json(_read("report.json")),
        patch=Patch.model_validate_json(patch_json) if patch_json else None,
        verify=VerifyResult.model_validate_json(verify_json) if verify_json else None,
        pr=PROpenResult.model_validate_json(pr_json) if pr_json else None,
    )
