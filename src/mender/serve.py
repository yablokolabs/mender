"""Service mode: a small HTTP API over the pipeline (stdlib only).

Endpoints:
  GET  /healthz  -> {"status": "ok"}
  POST /diagnose {"service", "namespace", "evidence"?, "manifests"?}
               -> root-cause report JSON (nano triage + ultra report + Tavily)
  POST /run     {"service", "namespace", "workdir", "test_files",
                 "test_command", "pr_mode"?}
               -> full pipeline result JSON; runs synchronously and needs
                  docker (sandbox) plus kubectl in the container environment
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from mender.config import MenderConfig, require_env
from mender.diagnosis import run_diagnosis
from mender.evidence import ClusterEvidence, EvidenceCollector, run_here
from mender.pipeline import PipelineError, run_pipeline
from mender.router.client import ModelClient
from mender.router.usage import UsageLedger
from mender.sandbox.runner import DockerRunner
from mender.tavily import TavilyClient
from mender.triage import triage

MAX_BODY = 2_000_000


class ApiError(RuntimeError):
    """Request could not be served (bad input or missing capability)."""


def diagnose(config: MenderConfig, payload: dict[str, Any]) -> dict[str, Any]:
    service = str(payload.get("service", ""))
    if not service:
        raise ApiError("'service' is required")
    namespace = str(payload.get("namespace", "default"))
    evidence_raw = payload.get("evidence")
    if evidence_raw:
        evidence = ClusterEvidence.model_validate(evidence_raw)
    else:
        manifests = {str(k): str(v) for k, v in dict(payload.get("manifests") or {}).items()}
        evidence = EvidenceCollector(run_here).collect(service, namespace, manifests=manifests)

    ledger = UsageLedger(Path("runs/serve/usage.jsonl"))
    models = ModelClient(config.router, require_env("NEBIUS_API_KEY"), ledger)
    tavily = TavilyClient(config.tavily, require_env("TAVILY_API_KEY"), ledger)
    triage_result = triage(models, evidence)
    report = run_diagnosis(models, tavily, evidence, triage_result)
    return {
        "triage": triage_result.model_dump(),
        "report": report.model_dump(),
        "markdown": report.markdown(),
    }


def run(config: MenderConfig, payload: dict[str, Any]) -> dict[str, Any]:
    service = str(payload.get("service", ""))
    workdir = payload.get("workdir")
    test_files = payload.get("test_files")
    test_command = payload.get("test_command")
    if not service or not workdir or not test_files or not test_command:
        raise ApiError("'service', 'workdir', 'test_files' and 'test_command' are required")
    workdir_path = Path(str(workdir)).resolve()
    if not workdir_path.is_dir():
        raise ApiError(f"workdir does not exist: {workdir_path}")

    evidence_raw = payload.get("evidence")
    if evidence_raw:
        evidence = ClusterEvidence.model_validate(evidence_raw)
    else:
        manifests = {str(k): str(v) for k, v in dict(payload.get("manifests") or {}).items()}
        evidence = EvidenceCollector(run_here).collect(
            service, str(payload.get("namespace", "default")), manifests=manifests
        )

    out_dir = Path(str(payload.get("out_dir") or f"runs/serve/{service}"))
    ledger = UsageLedger(out_dir / "usage.jsonl")
    models = ModelClient(config.router, require_env("NEBIUS_API_KEY"), ledger)
    tavily = TavilyClient(config.tavily, require_env("TAVILY_API_KEY"), ledger)
    result = run_pipeline(
        client=models,
        tavily=tavily,
        evidence=evidence,
        workdir=workdir_path,
        test_files=[str(path) for path in test_files],
        test_command=[str(part) for part in test_command],
        runner=DockerRunner(str(payload.get("sandbox_image") or config.sandbox.image)),
        config=config,
        out_dir=out_dir,
        pr_mode=str(payload.get("pr_mode") or "prepare"),
    )
    return result.model_dump()


def make_handler(config: MenderConfig) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "mender-serve"

        def _send(self, code: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > MAX_BODY:
                    raise ApiError("request body too large")
                payload = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(payload, dict):
                    raise ApiError("body must be a JSON object")
                if self.path == "/diagnose":
                    self._send(200, diagnose(config, payload))
                elif self.path == "/run":
                    self._send(200, run(config, payload))
                else:
                    self._send(404, {"error": "not found"})
            except ApiError as exc:
                self._send(400, {"error": str(exc)})
            except json.JSONDecodeError:
                self._send(400, {"error": "invalid JSON body"})
            except (PipelineError, ValueError) as exc:
                self._send(500, {"error": str(exc)})
            except Exception as exc:
                self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

        def log_message(self, fmt: str, *args: object) -> None:
            print(f"[serve] {fmt % args}", flush=True)

    return Handler


def serve(config: MenderConfig, *, host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(config))
    print(f"[serve] listening on http://{host}:{port}", flush=True)
    server.serve_forever()
