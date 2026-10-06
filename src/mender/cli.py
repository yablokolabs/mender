"""mender CLI: diagnose, fix, run, pr (argparse only)."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import time
from pathlib import Path

from mender.config import MenderConfig, load_config, load_env, require_env
from mender.diagnosis import run_diagnosis
from mender.evidence import ClusterEvidence, EvidenceCollector, run_here
from mender.pipeline import PipelineError, load_run, run_pipeline
from mender.pr import build_payload, open_pr
from mender.router.client import ModelClient
from mender.router.usage import UsageLedger
from mender.sandbox.runner import DockerRunner
from mender.tavily import TavilyClient
from mender.triage import triage

MANIFEST_SUFFIXES = (".yaml", ".yml", ".json")


def _log(message: str) -> None:
    print(f"[mender] {message}", file=sys.stderr, flush=True)


def _new_out_dir(kind: str, service: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return Path("runs") / f"{stamp}-{service}-{kind}"


def _read_manifests(manifests_dir: Path | None) -> dict[str, str]:
    if manifests_dir is None:
        return {}
    manifests: dict[str, str] = {}
    for path in sorted(manifests_dir.rglob("*")):
        if path.is_file() and path.suffix in MANIFEST_SUFFIXES:
            manifests[str(path.relative_to(manifests_dir))] = path.read_text(encoding="utf-8")
    return manifests


def _collect_evidence(args: argparse.Namespace) -> ClusterEvidence:
    if getattr(args, "evidence", None):
        return ClusterEvidence.model_validate_json(Path(args.evidence).read_text(encoding="utf-8"))
    collector = EvidenceCollector(run_here)
    return collector.collect(
        args.service,
        args.namespace,
        context=args.context,
        manifests=_read_manifests(Path(args.manifests_dir) if args.manifests_dir else None),
    )


def _print_tiers(ledger: UsageLedger) -> None:
    for tier, totals in sorted(ledger.by_tier().items()):
        _log(
            f"usage {tier}: calls={totals.calls} failures={totals.failures} "
            f"tokens={totals.total_tokens} median_ms={totals.latency_ms_median:.0f} "
            f"cost_usd={totals.cost_usd}"
        )


def _build_clients(
    out_dir: Path, config: MenderConfig
) -> tuple[ModelClient, TavilyClient, UsageLedger]:
    ledger = UsageLedger(out_dir / "usage.jsonl")
    models = ModelClient(config.router, require_env("NEBIUS_API_KEY"), ledger)
    tavily = TavilyClient(config.tavily, require_env("TAVILY_API_KEY"), ledger)
    return models, tavily, ledger


def _add_common(parser: argparse.ArgumentParser, *, need_service: bool = True) -> None:
    if need_service:
        parser.add_argument("--service", required=True, help="service (app) name")
        parser.add_argument("--namespace", default="default")
        parser.add_argument("--context", default=None, help="kubectl context")
        parser.add_argument("--evidence", default=None, help="reuse a saved evidence.json")
        parser.add_argument(
            "--manifests-dir", default=None, help="directory of manifests to attach as evidence"
        )


def _add_pipeline_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workdir", required=True, help="checkout the patch is applied to")
    parser.add_argument(
        "--test-file",
        action="append",
        required=True,
        dest="test_files",
        help="repo-relative file Mender may change (repeatable)",
    )
    parser.add_argument("--test-command", required=True, help="sandbox test command (shlex)")
    parser.add_argument("--out", default=None, help="artifact directory (default runs/<ts>)")


def cmd_diagnose(args: argparse.Namespace) -> int:
    config = load_config()
    out_dir = Path(args.out) if args.out else _new_out_dir("diagnose", args.service)
    models, tavily, ledger = _build_clients(out_dir, config)
    evidence = _collect_evidence(args)
    _log(f"triage for {evidence.service}...")
    t = triage(models, evidence)
    _log(f"diagnosis ({t.severity})...")
    report = run_diagnosis(models, tavily, evidence, t)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evidence.json").write_text(evidence.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "triage.json").write_text(t.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(report.markdown(), encoding="utf-8")
    _print_tiers(ledger)
    _log(f"report: {out_dir / 'report.md'}")
    print(report.title)
    return 0


def cmd_fix(args: argparse.Namespace, *, pr_mode: str | None) -> int:
    config = load_config()
    out_dir = (
        Path(args.out) if args.out else _new_out_dir("run" if pr_mode else "fix", args.service)
    )
    models, tavily, ledger = _build_clients(out_dir, config)
    evidence = _collect_evidence(args)
    result = run_pipeline(
        client=models,
        tavily=tavily,
        evidence=evidence,
        workdir=Path(args.workdir),
        test_files=args.test_files,
        test_command=shlex.split(args.test_command),
        runner=DockerRunner(config.sandbox.image),
        config=config,
        out_dir=out_dir,
        pr_mode=pr_mode,
        progress=True,
    )
    _print_tiers(ledger)
    _log(f"status: {result.status}")
    _log(f"timings_ms: {result.timings.model_dump()}")
    _log(f"artifacts: {out_dir}")
    return 0 if result.status in {"verified", "pr-prepared", "pr-opened"} else 1


def cmd_pr(args: argparse.Namespace) -> int:
    out_dir = Path(args.run)
    result = load_run(out_dir)
    if result.verify is None or not result.verify.passed:
        _log("run has no passing verification; refusing to open a PR")
        return 1
    if result.patch is None:
        _log("run has no patch artifact; refusing to open a PR")
        return 1
    meta = load_run_meta(out_dir)
    recorded = meta.get("workdir", "")
    workdir = Path(str(args.workdir or recorded))
    evidence = ClusterEvidence.model_validate_json(
        (out_dir / "evidence.json").read_text(encoding="utf-8")
    )
    payload = build_payload(result.report, result.patch, result.verify, evidence)
    opened = open_pr(
        payload,
        workdir,
        out_dir / "pr-body.md",
        mode=args.pr_mode,
    )
    (out_dir / "pr-open.json").write_text(opened.model_dump_json(indent=2), encoding="utf-8")
    if opened.error:
        _log(f"pr failed: {opened.error}")
        return 1
    _log(f"branch: {opened.branch}" + (f" url: {opened.url}" if opened.url else ""))
    return 0


def load_run_meta(out_dir: Path) -> dict[str, object]:
    path = out_dir / "run-meta.json"
    if not path.is_file():
        return {}
    data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mender",
        description="Mender: Kubernetes Incident-to-Fix Agent",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    diagnose = sub.add_parser("diagnose", help="root-cause report only")
    _add_common(diagnose)
    diagnose.add_argument("--out", default=None)
    diagnose.set_defaults(func=cmd_diagnose)

    fix = sub.add_parser("fix", help="diagnose + patch + sandbox verification (no PR)")
    _add_common(fix)
    _add_pipeline_args(fix)
    fix.set_defaults(func=lambda a: cmd_fix(a, pr_mode=None))

    run = sub.add_parser("run", help="full pipeline including PR preparation")
    _add_common(run)
    _add_pipeline_args(run)
    run.add_argument(
        "--pr-mode",
        choices=["prepare", "gh"],
        default="prepare",
        help="prepare = branch+commit locally; gh = push and open the PR",
    )
    run.set_defaults(func=lambda a: cmd_fix(a, pr_mode=a.pr_mode))

    pr = sub.add_parser("pr", help="open the PR for a finished run")
    pr.add_argument("--run", required=True, help="run artifact directory")
    pr.add_argument("--workdir", default=None, help="override the recorded workdir")
    pr.add_argument("--pr-mode", choices=["prepare", "gh"], default="gh")
    pr.set_defaults(func=cmd_pr)

    return parser


def main(argv: list[str] | None = None) -> int:
    load_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (PipelineError, FileNotFoundError, ValueError) as exc:
        _log(f"error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
