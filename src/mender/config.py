"""Typed configuration: mender.yaml plus .env loading (names only, never logged)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

DEFAULT_CONFIG_PATH = Path("mender.yaml")


class MissingCredential(RuntimeError):
    """A required environment variable is not set."""


class PriceConfig(BaseModel):
    """USD per 1M tokens. None means the price is not published; cost reports as None."""

    input_per_m: float | None = None
    output_per_m: float | None = None
    source: str = "unpublished"


class TierConfig(BaseModel):
    model: str
    temperature: float = 0.0
    max_tokens: int = 8192
    price: PriceConfig = Field(default_factory=PriceConfig)


class RouterConfig(BaseModel):
    base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    request_timeout_s: float = 120.0
    max_retries: int = 1
    retry_backoff_s: float = 2.0
    tiers: dict[str, TierConfig]


class TavilyConfig(BaseModel):
    base_url: str = "https://api.tavily.com"
    max_results: int = 5
    search_depth: str = "advanced"
    timeout_s: float = 30.0
    max_retries: int = 3
    retry_backoff_s: float = 1.0


class SandboxConfig(BaseModel):
    image: str = "python:3.12-slim"
    max_retries: int = 3
    timeout_s: int = 900


class MenderConfig(BaseModel):
    router: RouterConfig
    tavily: TavilyConfig = Field(default_factory=TavilyConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)


def load_env(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from a .env file into the environment if not already set."""
    env_path = path or Path(".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise MissingCredential(f"{name} is not set (see .env.example)")
    return value


def load_config(path: Path | None = None) -> MenderConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        raise FileNotFoundError(f"config file not found: {config_path}")
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return MenderConfig.model_validate(raw)
