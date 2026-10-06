#!/usr/bin/env bash
# Restore the demo tree and the cluster to clean state.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
CONTEXT="kind-${MENDER_CLUSTER:-mender}"

git checkout -- . 2>/dev/null || true
docker build -q -t mender-demo-app:1.0.0 app >/dev/null
kind load docker-image mender-demo-app:1.0.0 --name "${MENDER_CLUSTER:-mender}" >/dev/null
kubectl --context "$CONTEXT" apply -f manifests/
kubectl --context "$CONTEXT" rollout status deployment/checkout -n shop --timeout=150s
kubectl --context "$CONTEXT" get pods -n shop
echo "[demo] clean state restored"
