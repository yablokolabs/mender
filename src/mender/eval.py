"""Eval harness: run Mender against every injected fault and report honestly.

Definitions (also documented in the README):
- root-cause accuracy: cases whose predicted labels intersect the fault's
  expected labels, divided by all cases run (errors count as misses).
- fix-pass rate: cases whose sandbox tests passed within the retry bound,
  divided by all cases run.
- time to PR: wall time from pipeline start to a complete, ready-to-open PR
  (branch committed, body written) — reported only for cases that got there.
- cost per tier: summed from the per-case usage ledgers; a tier is reported
  as None if any of its calls had no published price. Nothing is estimated.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

import yaml
from pydantic import BaseModel, Field

from mender.config import MenderConfig
from mender.evidence import EvidenceCollector, run_here
from mender.pipeline import run_pipeline
from mender.router.client import ModelClient
from mender.router.usage import UsageLedger
from mender.sandbox.runner import DockerRunner
from mender.tavily import TavilyClient

EVAL_SCHEMA = "mender-eval-v1"


class EvalError(RuntimeError):
    """The harness cannot start or a case could not be set up."""


class Fault(BaseModel):
    id: str
    title: str
    category: str
    expected_labels: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    signal: str = "cluster"
    cluster: bool = True
    rebuild: bool = False


class CaseResult(BaseModel):
    fault_id: str
    category: str
    status: str
    error: str | None = None
    reused: bool = False
    root_cause_correct: bool = False
    predicted_labels: list[str] = Field(default_factory=list)
    expected_labels: list[str] = Field(default_factory=list)
    verify_passed: bool = False
    verify_attempts: int | None = None
    time_to_pr_ready_ms: float | None = None
    case_wall_ms: float = 0.0
    report_title: str = ""
    cost_usd_by_tier: dict[str, float | None] = Field(default_factory=dict)
    tokens_by_tier: dict[str, int] = Field(default_factory=dict)
    calls_by_tier: dict[str, int] = Field(default_factory=dict)
    out_dir: str = ""


class EvalSummary(BaseModel):
    faults_total: int
    cases_run: int
    root_cause_correct: int
    root_cause_accuracy: float
    fix_passed: int
    fix_pass_rate: float
    time_to_pr_ready_ms_median: float | None = None
    time_to_pr_ready_n: int = 0
    cost_usd_by_tier: dict[str, float | None] = Field(default_factory=dict)
    tokens_by_tier: dict[str, int] = Field(default_factory=dict)
    calls_by_tier: dict[str, int] = Field(default_factory=dict)
    failures: list[dict[str, str]] = Field(default_factory=list)


class EvalReport(BaseModel):
    schema_version: str = EVAL_SCHEMA
    started_at: str
    finished_at: str
    pr_mode: str
    settle_s: float
    sandbox_image: str
    cases: list[CaseResult]
    summary: EvalSummary


def load_faults(demo_dir: Path) -> list[Fault]:
    faults: list[Fault] = []
    for fault_file in sorted((demo_dir / "faults").glob("*/fault.yaml")):
        data = yaml.safe_load(fault_file.read_text(encoding="utf-8")) or {}
        data.setdefault("id", fault_file.parent.name)
        faults.append(Fault.model_validate(data))
    if not faults:
        raise EvalError(f"no faults found under {demo_dir / 'faults'}")
    return faults


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    local_bin = str(Path.home() / ".local" / "bin")
    env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    return env


def _run_tool(
    argv: list[str], *, cwd: Path, timeout_s: int = 300
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, cwd=cwd, env=_child_env(), capture_output=True, text=True, timeout=timeout_s
    )


def _evidence_manifests(case_repo: Path) -> dict[str, str]:
    demo = case_repo / "demo"
    paths = [
        *sorted((demo / "manifests").glob("*.yaml")),
        *sorted((demo / "app").glob("*.py")),
        *sorted((demo / "migrations").glob("*.sql")),
    ]
    return {
        f"demo/{path.relative_to(demo)}": path.read_text(encoding="utf-8")
        for path in paths
        if path.is_file()
    }


def _flush_events() -> None:
    """Drop old events so a case's evidence cannot inherit a previous fault."""
    cluster = os.environ.get("MENDER_CLUSTER", "mender")
    _run_tool(
        ["kubectl", "--context", f"kind-{cluster}", "delete", "events", "-n", "shop", "--all"],
        cwd=Path.cwd(),
        timeout_s=60,
    )


def _inject(demo_dir: Path, fault_id: str, *, mode: str) -> subprocess.CompletedProcess[str]:
    argv = ["python3", "inject.py", fault_id, "--demo-dir", str(demo_dir)]
    if mode == "cleanup":
        argv += ["--mode", "cleanup"]
    return _run_tool(argv, cwd=demo_dir, timeout_s=400)


def run_case(
    fault: Fault,
    *,
    repo_root: Path,
    work_root: Path,
    result_root: Path,
    config: MenderConfig,
    settle_s: float,
    pr_mode: str,
    sandbox_image: str,
    force: bool = False,
    progress: bool = True,
) -> CaseResult:
    case_dir = (work_root / "cases" / fault.id).resolve()
    out_dir = case_dir / "out"
    result_path = out_dir / "case-result.json"

    if result_path.is_file() and not force:
        reused = CaseResult.model_validate_json(result_path.read_text(encoding="utf-8"))
        reused.reused = True
        return reused

    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    clone = _run_tool(
        ["git", "clone", "--quiet", "--local", str(repo_root), str(case_dir / "repo")],
        cwd=work_root,
        timeout_s=120,
    )
    if clone.returncode != 0:
        raise EvalError(f"{fault.id}: git clone failed: {clone.stderr.strip()[:300]}")

    case_repo = case_dir / "repo"
    demo_dir = case_repo / "demo"
    started = time.perf_counter()

    if progress:
        print(f"[eval] {fault.id}: injecting...", flush=True)
    _flush_events()
    inject = _inject(demo_dir, fault.id, mode="apply")
    if inject.returncode != 0:
        error = f"inject failed: {(inject.stderr or inject.stdout)[-500:]}"
        if progress:
            print(f"[eval] {fault.id}: {error}", flush=True)
        result = CaseResult(
            fault_id=fault.id,
            category=fault.category,
            status="inject-failed",
            error=error,
            expected_labels=fault.expected_labels,
            case_wall_ms=(time.perf_counter() - started) * 1000.0,
            out_dir=str(out_dir),
        )
        _finish_case(result, out_dir, result_root, demo_dir, fault)
        return result

    if fault.signal == "cluster" and settle_s > 0:
        time.sleep(settle_s)

    evidence = EvidenceCollector(run_here).collect(
        "checkout",
        "shop",
        manifests=_evidence_manifests(case_repo),
    )

    ledger = UsageLedger(out_dir / "usage.jsonl")
    models = ModelClient(config.router, os.environ.get("NEBIUS_API_KEY", ""), ledger)
    tavily = TavilyClient(config.tavily, os.environ.get("TAVILY_API_KEY", ""), ledger)

    if progress:
        print(f"[eval] {fault.id}: pipeline...", flush=True)
    try:
        pipeline = run_pipeline(
            client=models,
            tavily=tavily,
            evidence=evidence,
            workdir=case_repo,
            test_files=fault.files,
            test_command=["python3", "demo/app/check.py"],
            runner=DockerRunner(sandbox_image),
            config=config,
            out_dir=out_dir,
            pr_mode=pr_mode,
            progress=progress,
        )
        correct = bool(
            pipeline.report.normalized_labels
            & {label.strip() for label in fault.expected_labels if label.strip()}
        )
        result = CaseResult(
            fault_id=fault.id,
            category=fault.category,
            status=pipeline.status,
            root_cause_correct=correct,
            predicted_labels=sorted(pipeline.report.normalized_labels),
            expected_labels=fault.expected_labels,
            verify_passed=bool(pipeline.verify and pipeline.verify.passed),
            verify_attempts=pipeline.verify.attempts if pipeline.verify else None,
            time_to_pr_ready_ms=(
                pipeline.timings.total_ms
                if pipeline.status in {"pr-prepared", "pr-opened"}
                else None
            ),
            case_wall_ms=(time.perf_counter() - started) * 1000.0,
            report_title=pipeline.report.title,
            out_dir=str(out_dir),
        )
    except Exception as exc:
        result = CaseResult(
            fault_id=fault.id,
            category=fault.category,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
            expected_labels=fault.expected_labels,
            case_wall_ms=(time.perf_counter() - started) * 1000.0,
            out_dir=str(out_dir),
        )
        if progress:
            print(f"[eval] {fault.id}: ERROR {result.error}", flush=True)
    finally:
        cleanup = _inject(demo_dir, fault.id, mode="cleanup")
        if cleanup.returncode != 0 and progress:
            print(
                f"[eval] {fault.id}: cleanup problem: {cleanup.stderr[-300:]}",
                flush=True,
            )
        _flush_events()

    # Cost/token roll-up from this case's own ledger.
    for tier, totals in ledger.by_tier().items():
        result.cost_usd_by_tier[tier] = totals.cost_usd
        result.tokens_by_tier[tier] = totals.total_tokens
        result.calls_by_tier[tier] = totals.calls

    _finish_case(result, out_dir, result_root, demo_dir, fault)
    if progress:
        print(
            f"[eval] {fault.id}: {result.status} "
            f"(root_cause={'hit' if result.root_cause_correct else 'miss'}, "
            f"verify={'pass' if result.verify_passed else 'fail'})",
            flush=True,
        )
    return result


def _finish_case(
    result: CaseResult,
    out_dir: Path,
    result_root: Path,
    demo_dir: Path,
    fault: Fault,
) -> None:
    """Persist the case result and copy its evidence into the results tree."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "case-result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    keep_dir = result_root / "cases" / fault.id
    keep_dir.mkdir(parents=True, exist_ok=True)
    (keep_dir / "case-result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    for name in ("report.md", "pr-body.md", "verify.json", "usage.jsonl"):
        source = out_dir / name
        if source.is_file():
            shutil.copyfile(source, keep_dir / name)


def aggregate(
    cases: list[CaseResult],
    *,
    fault_count: int,
    started_at: str,
    finished_at: str,
    pr_mode: str,
    settle_s: float,
    sandbox_image: str,
) -> EvalReport:
    run = len(cases)
    correct = sum(1 for case in cases if case.root_cause_correct)
    passed = sum(1 for case in cases if case.verify_passed)
    times = [case.time_to_pr_ready_ms for case in cases if case.time_to_pr_ready_ms is not None]

    tiers = sorted({tier for case in cases for tier in case.cost_usd_by_tier})
    cost: dict[str, float | None] = {}
    tokens: dict[str, int] = {}
    calls: dict[str, int] = {}
    for tier in tiers:
        # A case that never called this tier contributes nothing; only a case
        # that DID call it but has no price makes the whole tier unknown.
        costs: list[float] = []
        complete = True
        for case in cases:
            used = tier in case.cost_usd_by_tier or case.calls_by_tier.get(tier, 0) > 0
            if not used:
                continue
            value = case.cost_usd_by_tier.get(tier)
            if value is None:
                complete = False
                break
            costs.append(value)
        cost[tier] = sum(costs) if complete else None
        tokens[tier] = sum(case.tokens_by_tier.get(tier, 0) for case in cases)
        calls[tier] = sum(case.calls_by_tier.get(tier, 0) for case in cases)

    failures = [
        {"fault_id": case.fault_id, "status": case.status, "error": case.error or ""}
        for case in cases
        if case.status not in {"pr-prepared", "pr-opened", "verified"}
    ]

    summary = EvalSummary(
        faults_total=fault_count,
        cases_run=run,
        root_cause_correct=correct,
        root_cause_accuracy=(correct / run) if run else 0.0,
        fix_passed=passed,
        fix_pass_rate=(passed / run) if run else 0.0,
        time_to_pr_ready_ms_median=median(times) if times else None,
        time_to_pr_ready_n=len(times),
        cost_usd_by_tier=cost,
        tokens_by_tier=tokens,
        calls_by_tier=calls,
        failures=failures,
    )
    return EvalReport(
        started_at=started_at,
        finished_at=finished_at,
        pr_mode=pr_mode,
        settle_s=settle_s,
        sandbox_image=sandbox_image,
        cases=cases,
        summary=summary,
    )


def write_report(report: EvalReport, result_root: Path) -> Path:
    result_root.mkdir(parents=True, exist_ok=True)
    path = result_root / "eval-v1.json"
    path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
    return path


def now_ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
