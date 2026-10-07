#!/usr/bin/env bash
# Smoke test for the service image: start it and wait for GET /healthz.
# Usage: image-smoke.sh <image>. The CI image job and `make image` run it.
set -euo pipefail

image="${1:?usage: image-smoke.sh <image>}"
container="mender-smoke-$$"
wait_seconds=30

cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT

fail() {
  echo "::error::$image does not answer GET /healthz with status ok: $1"
  echo "container log:"
  docker logs "$container" 2>&1 | tail -n 20
  exit 1
}

# The host port is chosen by Docker, so the test cannot collide with a local service.
docker run -d --name "$container" -p 127.0.0.1::8080 "$image" >/dev/null

for _ in $(seq "$wait_seconds"); do
  state="$(docker inspect "$container" --format '{{.State.Status}}, exit code {{.State.ExitCode}}')"
  [ "${state%%,*}" = "running" ] || fail "the container stopped ($state)"
  port="$(docker port "$container" 8080/tcp | head -n 1 | sed 's/.*://')"
  if body="$(curl -s --max-time 2 "http://127.0.0.1:${port}/healthz")" \
    && jq -e '.status == "ok"' >/dev/null 2>&1 <<<"$body"; then
    echo "OK: $image answers GET /healthz"
    exit 0
  fi
  sleep 1
done
fail "no answer in $wait_seconds seconds"
