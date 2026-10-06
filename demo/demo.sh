#!/usr/bin/env bash
# One-command demo: a fault goes from failure to diagnosis to patch to
# sandbox test to prepared PR. Usage: demo.sh [fault-id] (default: low-memory-limit)
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
[ -f .env ] && { set -a; . ./.env; set +a; }

FAULT="${1:-low-memory-limit}"
OUT="runs/demo-$(date +%Y%m%d-%H%M%S)"
STAMP="$(date +%s)"
REPO="$OUT/repo"

echo "[demo] fault: $FAULT"
echo "[demo] working copy: $REPO"
mkdir -p "$OUT"
git clone --quiet --local . "$REPO"

cleanup() {
  python3 demo/inject.py "$FAULT" --demo-dir "$REPO/demo" --mode cleanup >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[demo] injecting fault into the cluster..."
python3 demo/inject.py "$FAULT" --demo-dir "$REPO/demo"
sleep 25

TEST_FILES="$(python3 - "$FAULT" <<'PY'
import sys, yaml
fault = yaml.safe_load(open(f"demo/faults/{sys.argv[1]}/fault.yaml"))
print(" ".join(f"--test-file {path}" for path in fault["files"]))
PY
)"

echo "[demo] running Mender (triage -> diagnosis -> patch -> sandbox -> PR)..."
# shellcheck disable=SC2086
uv run mender run \
  --service checkout --namespace shop \
  --manifests-dir demo/manifests \
  --workdir "$REPO" $TEST_FILES \
  --test-command "python3 demo/app/check.py" \
  --out "$OUT/out" --pr-mode prepare

echo
echo "[demo] === root cause report ==="
head -20 "$OUT/out/report.md"
echo
echo "[demo] === prepared PR ==="
git -C "$REPO" log --oneline -1
echo "[demo] branch: $(git -C "$REPO" branch --show-current)"
echo "[demo] PR body: $OUT/out/pr-body.md"
echo "[demo] full artifacts: $OUT/out/"
