"""Checkout demo service (stdlib only).

Kept deliberately small so every injected fault maps to a checkable invariant:
SECRET_KEY from the secret, DB_HOST from the config map, a fixed startup cache
(simulating a JVM heap so a too-small memory limit really OOM-kills the pod),
and a health endpoint used by both probes.
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

CONFIG_PATH = os.environ.get("CONFIG_PATH", "/etc/app/config.yaml")
EXPECTED_DB_SUFFIX = ".shop.svc.cluster.local"
MIN_SECRET_LENGTH = 32
ALLOWED_LOG_LEVELS = {"debug", "info", "warn", "error"}
STARTUP_CACHE_BYTES = 96 * 1024 * 1024  # the "JVM heap" that OOMs a 64Mi limit


class ConfigError(RuntimeError):
    """Configuration or environment is invalid; the service must not start."""


def parse_amount(value: str) -> float:
    """Parse a decimal money string; reject anything that is not an amount."""
    if value is None:
        raise ValueError("missing amount")
    cleaned = str(value).strip().replace(",", "")
    if not re.fullmatch(r"-?\d+(\.\d{1,2})?", cleaned):
        raise ValueError(f"bad amount: {value!r}")
    return float(cleaned)


def parse_config(text: str) -> dict[str, str]:
    """Parse the flat `key: value` config file (no YAML dependency)."""
    config: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        config[key.strip()] = value.strip()
    if "log_level" not in config:
        raise ConfigError("config is missing log_level")
    if config["log_level"] not in ALLOWED_LOG_LEVELS:
        raise ConfigError(f"invalid log_level: {config['log_level']}")
    return config


def require_environment() -> dict[str, str]:
    """SECRET_KEY and DB_HOST must both be present and valid."""
    secret = os.environ.get("SECRET_KEY", "")
    if not secret:
        raise ConfigError("missing required env var SECRET_KEY")
    if len(secret) < MIN_SECRET_LENGTH:
        raise ConfigError(
            f"SECRET_KEY too short ({len(secret)} < {MIN_SECRET_LENGTH} chars)"
        )
    db_host = os.environ.get("DB_HOST", "")
    if not db_host:
        raise ConfigError("missing required env var DB_HOST")
    return {"SECRET_KEY": secret, "DB_HOST": db_host}


def load_config(path: str = CONFIG_PATH) -> dict[str, str]:
    if not os.path.isfile(path):
        raise ConfigError(f"config file not found: {path}")
    with open(path, encoding="utf-8") as handle:
        return parse_config(handle.read())


def healthcheck(db_host: str, log_level: str) -> tuple[int, str]:
    """200 only when the service is genuinely healthy."""
    problems: list[str] = []
    if not db_host.endswith(EXPECTED_DB_SUFFIX):
        problems.append(f"db host outside cluster domain: {db_host}")
    if log_level not in ALLOWED_LOG_LEVELS:
        problems.append(f"invalid log_level: {log_level}")
    if problems:
        return 500, "; ".join(problems)
    return 200, "ok"


class Handler(BaseHTTPRequestHandler):
    server_version = "checkout/1.0"

    def _reply(self, code: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            code, message = healthcheck(_ENV["DB_HOST"], _CONFIG["log_level"])
            self._reply(code, {"status": message})
            return
        if parsed.path == "/amount":
            query = parse_qs(parsed.query)
            raw = (query.get("amount") or [""])[0]
            try:
                self._reply(200, {"amount": parse_amount(raw)})
            except ValueError as exc:
                self._reply(400, {"error": str(exc)})
            return
        self._reply(404, {"error": "not found"})

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stdout.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))
        sys.stdout.flush()


_ENV: dict[str, str] = {}
_CONFIG: dict[str, str] = {}


def main() -> None:
    global _ENV, _CONFIG
    _ENV = require_environment()
    _CONFIG = load_config()
    # Simulated heap: reserves the cache the container limit must accommodate.
    cache = bytearray(STARTUP_CACHE_BYTES)
    cache[0] = 1
    print(
        f"starting checkout service (log_level={_CONFIG['log_level']}, "
        f"db={_ENV['DB_HOST']}, cache={len(cache) // (1024 * 1024)}Mi)",
        flush=True,
    )
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except ConfigError as exc:
        print(f"FATAL: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
