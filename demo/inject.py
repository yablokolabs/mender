#!/usr/bin/env python3
"""Apply or clean one demo fault.

Usage:
  python3 inject.py <fault-id> [--demo-dir DIR] [--mode apply|cleanup]

Each fault lives in faults/<id>/fault.yaml with:
  id, title, category, expected_labels, files, signal, cluster, rebuild,
  apply, cleanup

`apply`/`cleanup` are bash snippets run with cwd = the demo dir. The executor
re-applies the manifests to the kind cluster when `cluster: true`, restarting
the deployment so the change is actually observable; `rebuild: true` also
rebuilds and reloads the app image (used by source-code faults).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
CLUSTER = os.environ.get("MENDER_CLUSTER", "mender")
CONTEXT = f"kind-{CLUSTER}"


def _run(argv: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        sys.stderr.write(f"[inject] failed: {' '.join(argv)}\n{proc.stderr}\n")
    return proc


def _bash(snippet: str, cwd: Path) -> int:
    proc = _run(["bash", "-c", f"set -euo pipefail\n{snippet}"], cwd=cwd, check=False)
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
    return proc.returncode


def _kubectl_apply(demo_dir: Path) -> int:
    ctx = ["kubectl", "--context", CONTEXT]
    for argv in (
        [*ctx, "apply", "-f", "manifests/"],
        [*ctx, "rollout", "restart", "deployment/checkout", "-n", "shop"],
        [*ctx, "rollout", "status", "deployment/checkout", "-n", "shop", "--timeout=150s"],
    ):
        proc = _run(argv, cwd=demo_dir, check=False)
        if proc.returncode != 0:
            # A rollout that never becomes ready is itself the injected symptom.
            sys.stderr.write(f"[inject] {argv[2]} returned {proc.returncode}: {proc.stderr[-400:]}\n")
            if argv[2] == "apply":
                return proc.returncode
    return 0


def _rebuild(demo_dir: Path) -> int:
    if _run(
        ["docker", "build", "-q", "-t", "mender-demo-app:1.0.0", "app"],
        cwd=demo_dir,
        check=False,
    ).returncode:
        return 1
    if _run(
        ["kind", "load", "docker-image", "mender-demo-app:1.0.0", "--name", CLUSTER],
        check=False,
    ).returncode:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fault_id")
    parser.add_argument("--demo-dir", default=str(HERE))
    parser.add_argument("--mode", choices=["apply", "cleanup"], default="apply")
    args = parser.parse_args(argv)

    demo_dir = Path(args.demo_dir).resolve()
    fault_path = demo_dir / "faults" / args.fault_id / "fault.yaml"
    if not fault_path.is_file():
        sys.stderr.write(f"[inject] no such fault: {args.fault_id}\n")
        return 2
    fault = yaml.safe_load(fault_path.read_text(encoding="utf-8"))
    snippet = str(fault.get(args.mode, "")).strip()
    if not snippet:
        sys.stderr.write(f"[inject] fault {args.fault_id} has no {args.mode} snippet\n")
        return 2

    rc = _bash(snippet, demo_dir)
    if rc != 0:
        return rc

    if args.mode == "apply":
        if fault.get("rebuild"):
            rc = _rebuild(demo_dir)
            if rc != 0:
                return rc
        if fault.get("cluster", True):
            rc = _kubectl_apply(demo_dir)
            if rc != 0:
                return rc
    else:
        if fault.get("rebuild"):
            rc = _rebuild(demo_dir)
            if rc != 0:
                return rc
        if fault.get("cluster", True) or fault.get("rebuild"):
            rc = _kubectl_apply(demo_dir)
            if rc != 0:
                return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
