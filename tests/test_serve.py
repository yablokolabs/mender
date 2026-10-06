import json
import threading
from http.client import HTTPConnection
from typing import Any

import pytest

from mender.config import MenderConfig
from mender.serve import ApiError, diagnose, make_handler


def _config() -> MenderConfig:
    return MenderConfig.model_validate(
        {
            "router": {
                "tiers": {
                    "nano": {"model": "nvidia/test-nano"},
                    "ultra": {"model": "nvidia/test-ultra"},
                    "super": {"model": "nvidia/test-super"},
                }
            }
        }
    )


@pytest.fixture
def server() -> Any:
    from http.server import ThreadingHTTPServer

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(_config()))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    thread.join(timeout=5)


def _request(
    server: Any, method: str, path: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any]]:
    port = server.server_address[1]
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    payload = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if payload else {}
    conn.request(method, path, body=payload, headers=headers)
    response = conn.getresponse()
    data: dict[str, Any] = json.loads(response.read() or b"{}")
    conn.close()
    return response.status, data


def test_healthz(server: Any) -> None:
    status, body = _request(server, "GET", "/healthz")
    assert status == 200
    assert body["status"] == "ok"


def test_unknown_path_404(server: Any) -> None:
    status, body = _request(server, "GET", "/nope")
    assert status == 404
    assert body["error"] == "not found"


def test_invalid_json_400(server: Any) -> None:
    port = server.server_address[1]
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(
        "POST", "/diagnose", body=b"{not json", headers={"Content-Type": "application/json"}
    )
    response = conn.getresponse()
    assert response.status == 400
    conn.close()


def test_diagnose_requires_service() -> None:
    with pytest.raises(ApiError, match="service"):
        diagnose(_config(), {})


def test_run_requires_fields() -> None:
    from mender.serve import run as run_endpoint

    with pytest.raises(ApiError, match="workdir"):
        run_endpoint(_config(), {"service": "checkout"})
