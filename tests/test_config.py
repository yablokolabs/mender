import os
from pathlib import Path

import pytest

from mender.config import (
    MenderConfig,
    MissingCredential,
    load_config,
    load_env,
    require_env,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_default_config_loads_with_three_tiers() -> None:
    config = load_config(REPO_ROOT / "mender.yaml")
    assert isinstance(config, MenderConfig)
    assert set(config.router.tiers) == {"nano", "ultra", "super"}
    for tier in config.router.tiers.values():
        assert tier.model.startswith("nvidia/")
        assert tier.price.source != ""


def test_prices_have_documented_sources() -> None:
    config = load_config(REPO_ROOT / "mender.yaml")
    for name, tier in config.router.tiers.items():
        assert tier.price.input_per_m is not None, name
        assert tier.price.output_per_m is not None, name
        assert "retrieved" in tier.price.source, name


def test_missing_config_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_config(REPO_ROOT / "no-such-file.yaml")


def test_require_env_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MENDER_TEST_MISSING_KEY", raising=False)
    with pytest.raises(MissingCredential):
        require_env("MENDER_TEST_MISSING_KEY")


def test_load_env_sets_unset_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('# comment\nMENDER_TEST_A="value-a"\nMENDER_TEST_B=value-b\n')
    monkeypatch.delenv("MENDER_TEST_A", raising=False)
    monkeypatch.setenv("MENDER_TEST_B", "already-set")
    load_env(env_file)
    assert os.environ["MENDER_TEST_A"] == "value-a"
    assert os.environ["MENDER_TEST_B"] == "already-set"
