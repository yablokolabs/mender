"""Offline invariant suite for the demo app — the sandbox test command.

Runs anywhere with stdlib + PyYAML, no cluster needed:
  python3 demo/app/check.py
Exit code 0 only if every invariant of the clean design holds.
"""

from __future__ import annotations

import importlib.util
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

DEMO_DIR = Path(__file__).resolve().parent.parent
MANIFESTS = DEMO_DIR / "manifests"
MIGRATIONS = DEMO_DIR / "migrations"

IMAGE_TAG_ALLOWLIST = {"1.0.0"}
MIN_MEMORY_LIMIT_MIB = 512
MAX_CPU_REQUEST = 2.0
EXPECTED_DB_HOST = "orders-db.shop.svc.cluster.local"
REQUIRED_ORDER_COLUMNS = {"id", "customer_id", "amount", "currency", "created_at"}


def _load_yaml(name: str) -> Any:
    return yaml.safe_load((MANIFESTS / name).read_text(encoding="utf-8"))


def _load_deploy() -> dict[str, Any]:
    return _load_yaml("deploy.yaml")


def _container() -> dict[str, Any]:
    return _load_deploy()["spec"]["template"]["spec"]["containers"][0]


def _to_mib(value: str) -> float:
    match = re.fullmatch(r"(\d+)(Mi|Gi|Ki|Ki)?", str(value).strip())
    if not match:
        raise ValueError(f"unparseable memory quantity: {value}")
    amount = float(match.group(1))
    unit = match.group(2) or "Mi"
    return amount * 1024 if unit == "Gi" else amount / 1024 if unit == "Ki" else amount


def _to_cpu(value: str) -> float:
    text = str(value).strip()
    return float(text[:-1]) / 1000 if text.endswith("m") else float(text)


def _probe_port_is_container(probe: dict[str, Any]) -> bool:
    port = probe["httpGet"]["port"]
    container = _container()
    if isinstance(port, int):
        return port == 8080
    names = {p.get("name"): p.get("containerPort") for p in container.get("ports", [])}
    return names.get(port) == 8080


def _import_service() -> Any:
    spec = importlib.util.spec_from_file_location(
        "demo_service", DEMO_DIR / "app" / "service.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load demo/app/service.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- deployment invariants -------------------------------------------------


def check_memory_limit() -> None:
    limit = _container()["resources"]["limits"]["memory"]
    assert _to_mib(limit) >= MIN_MEMORY_LIMIT_MIB, (
        f"memory limit {limit} below required {MIN_MEMORY_LIMIT_MIB}Mi "
        "(startup cache alone is 96Mi)"
    )


def check_cpu_limit_present() -> None:
    limits = _container()["resources"]["limits"]
    assert "cpu" in limits, "limits.cpu missing"


def check_cpu_request_sane() -> None:
    requests = _container()["resources"]["requests"]
    assert "cpu" in requests, "requests.cpu missing"
    assert _to_cpu(requests["cpu"]) <= MAX_CPU_REQUEST, (
        f"requests.cpu {requests['cpu']} exceeds this cluster's capacity"
    )


def check_replicas() -> None:
    assert _load_deploy()["spec"]["replicas"] >= 1, "replicas must be >= 1"


def check_image_tag() -> None:
    image = _container()["image"]
    tag = image.rsplit(":", 1)[-1] if ":" in image else "latest"
    assert tag in IMAGE_TAG_ALLOWLIST, f"image tag not in allowlist: {image}"


def check_readiness_probe() -> None:
    probe = _container().get("readinessProbe")
    assert probe is not None, "readinessProbe missing"
    assert probe["httpGet"]["path"] == "/healthz", "readiness path must be /healthz"
    assert _probe_port_is_container(probe), "readiness port must reach container 8080"


def check_liveness_probe() -> None:
    probe = _container().get("livenessProbe")
    assert probe is not None, "livenessProbe missing"
    assert probe["httpGet"]["path"] == "/healthz", "liveness path must be /healthz"
    assert _probe_port_is_container(probe), "liveness port must reach container 8080"


def check_container_port() -> None:
    ports = {p.get("containerPort") for p in _container().get("ports", [])}
    assert 8080 in ports, f"containerPort 8080 missing, found {ports}"


def _env_entry(name: str) -> dict[str, Any] | None:
    for entry in _container().get("env", []):
        if entry.get("name") == name:
            return entry
    return None


def check_secret_env_ref() -> None:
    entry = _env_entry("SECRET_KEY")
    assert entry is not None, "env SECRET_KEY missing"
    ref = entry.get("valueFrom", {}).get("secretKeyRef", {})
    assert ref.get("name") == "checkout-secrets", f"wrong secret name: {ref}"
    assert ref.get("key") == "secret_key", f"wrong secret key: {ref}"


def check_db_env_ref() -> None:
    entry = _env_entry("DB_HOST")
    assert entry is not None, "env DB_HOST missing"
    ref = entry.get("valueFrom", {}).get("configMapKeyRef", {})
    assert ref.get("name") == "checkout-config", f"wrong config map: {ref}"
    assert ref.get("key") == "db_host", f"wrong config map key: {ref}"


def check_config_mount() -> None:
    container = _container()
    mounts = {m.get("name"): m for m in container.get("volumeMounts", [])}
    assert "app-config" in mounts, "app-config volume mount missing"
    assert mounts["app-config"]["mountPath"] == "/etc/app", (
        f"config must be mounted at /etc/app, found {mounts['app-config']['mountPath']}"
    )
    volumes = _load_deploy()["spec"]["template"]["spec"].get("volumes", [])
    config_volumes = [v for v in volumes if v.get("name") == "app-config"]
    assert config_volumes, "app-config volume missing"
    items = config_volumes[0].get("configMap", {}).get("items", [])
    assert any(
        item.get("key") == "config.yaml" and item.get("path") == "config.yaml"
        for item in items
    ), f"configMap item must mount key config.yaml, found {items}"


def check_selector_match() -> None:
    deploy = _load_deploy()
    selector = deploy["spec"]["selector"]["matchLabels"]
    template_labels = deploy["spec"]["template"]["metadata"]["labels"]
    for key, value in selector.items():
        assert template_labels.get(key) == value, (
            f"selector {key}={value} does not match template labels {template_labels}"
        )


# --- service invariants ----------------------------------------------------


def check_service_selector_and_ports() -> None:
    service = _load_yaml("service.yaml")
    selector = service["spec"]["selector"]
    template_labels = _load_deploy()["spec"]["template"]["metadata"]["labels"]
    for key, value in selector.items():
        assert template_labels.get(key) == value, (
            f"service selector {key}={value} matches no pod label {template_labels}"
        )
    port = service["spec"]["ports"][0]
    target = port.get("targetPort")
    container = _container()
    if isinstance(target, int):
        assert target == 8080, f"targetPort {target} must be 8080"
    else:
        names = {p.get("name"): p.get("containerPort") for p in container.get("ports", [])}
        assert names.get(target) == 8080, f"named targetPort {target!r} unresolved"
    assert port.get("port") == 8080, f"service port must be 8080, found {port.get('port')}"


# --- config map / secret invariants --------------------------------------


def check_configmap_values() -> None:
    data = _load_yaml("configmap.yaml")["data"]
    assert data.get("db_host") == EXPECTED_DB_HOST, (
        f"db_host must be {EXPECTED_DB_HOST}, found {data.get('db_host')}"
    )
    assert "config.yaml" in data, "config.yaml key missing"
    service = _import_service()
    config = service.parse_config(data["config.yaml"])  # raises on invalid content
    assert config["log_level"] in service.ALLOWED_LOG_LEVELS


def check_secret_value() -> None:
    string_data = _load_yaml("secret.yaml")["stringData"]
    assert "secret_key" in string_data, "secret_key missing"
    value = string_data["secret_key"]
    assert len(value) >= 32, f"secret_key too short ({len(value)} < 32 chars)"


# --- migration invariants --------------------------------------------------


def check_migration_executes() -> None:
    sql = (MIGRATIONS / "001_init.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(sql)
    finally:
        conn.close()


def check_migration_schema() -> None:
    sql = (MIGRATIONS / "001_init.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(sql)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    finally:
        conn.close()
    missing = REQUIRED_ORDER_COLUMNS - columns
    assert not missing, f"migration missing columns used by the app: {sorted(missing)}"


# --- application source invariants ----------------------------------------


def check_service_parses_amounts() -> None:
    service = _import_service()
    assert service.parse_amount("12.34") == 12.34
    assert service.parse_amount("1,234.56") == 1234.56
    assert service.parse_amount("-7") == -7.0
    for bad in ("", "abc", "12.3.4", "1.234", "--5"):
        try:
            service.parse_amount(bad)
        except ValueError:
            continue
        raise AssertionError(f"parse_amount accepted invalid input {bad!r}")


def check_service_healthcheck_logic() -> None:
    service = _import_service()
    code, _ = service.healthcheck(EXPECTED_DB_HOST, "info")
    assert code == 200, "healthy inputs must return 200"
    assert service.healthcheck("orders-db.default.svc.cluster.local", "info")[0] == 500
    assert service.healthcheck(EXPECTED_DB_HOST, "verbose")[0] == 500


def check_service_env_validation() -> None:
    service = _import_service()
    import os

    saved = dict(os.environ)
    try:
        os.environ["SECRET_KEY"] = "demo-only-not-a-real-key-0123456789abcdef0123456789abcdef"
        os.environ["DB_HOST"] = EXPECTED_DB_HOST
        service.require_environment()

        os.environ["SECRET_KEY"] = "short"
        try:
            service.require_environment()
        except service.ConfigError:
            pass
        else:
            raise AssertionError("short SECRET_KEY accepted")

        del os.environ["DB_HOST"]
        try:
            service.require_environment()
        except service.ConfigError:
            pass
        else:
            raise AssertionError("missing DB_HOST accepted")
    finally:
        os.environ.clear()
        os.environ.update(saved)


def check_service_config_validation() -> None:
    service = _import_service()
    assert service.parse_config("log_level: info\n")["log_level"] == "info"
    try:
        service.parse_config("log_level: verbose\n")
    except service.ConfigError:
        pass
    else:
        raise AssertionError("invalid log_level accepted")


CHECKS: list[tuple[str, Callable[[], None]]] = [
    (check.__name__, check)
    for check in (
        check_memory_limit,
        check_cpu_limit_present,
        check_cpu_request_sane,
        check_replicas,
        check_image_tag,
        check_readiness_probe,
        check_liveness_probe,
        check_container_port,
        check_secret_env_ref,
        check_db_env_ref,
        check_config_mount,
        check_selector_match,
        check_service_selector_and_ports,
        check_configmap_values,
        check_secret_value,
        check_migration_executes,
        check_migration_schema,
        check_service_parses_amounts,
        check_service_healthcheck_logic,
        check_service_env_validation,
        check_service_config_validation,
    )
]


def main() -> int:
    failures = 0
    for name, check in CHECKS:
        try:
            check()
        except Exception as exc:  # noqa: BLE001 - the suite reports every failure
            failures += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {name}")
    total = len(CHECKS)
    print(f"{total - failures}/{total} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
