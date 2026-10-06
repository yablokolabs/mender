#!/usr/bin/env bash
# One-command demo environment: images + kind cluster + clean deployment.
set -euo pipefail
cd "$(dirname "$0")"

CLUSTER_NAME="${MENDER_CLUSTER:-mender}"
export PATH="$HOME/.local/bin:$PATH"

echo "[demo] building images"
docker build -q -t mender-demo-app:1.0.0 app
docker build -q -t mender-demo-test:latest test-image

if ! kind get clusters | grep -qx "$CLUSTER_NAME"; then
  echo "[demo] creating kind cluster $CLUSTER_NAME"
  kind create cluster --name "$CLUSTER_NAME" --wait 180s
else
  echo "[demo] kind cluster $CLUSTER_NAME already exists"
fi

echo "[demo] loading images into the cluster"
kind load docker-image mender-demo-app:1.0.0 --name "$CLUSTER_NAME"
kind load docker-image mender-demo-test:latest --name "$CLUSTER_NAME"

echo "[demo] deploying the clean app"
kubectl --context "kind-$CLUSTER_NAME" apply -f manifests/
kubectl --context "kind-$CLUSTER_NAME" rollout status deployment/checkout -n shop --timeout=180s
echo "[demo] ready. Pods:"
kubectl --context "kind-$CLUSTER_NAME" get pods -n shop -o wide
