import json
from pathlib import Path

from mender.cli import build_parser, load_run_meta


def test_parser_exposes_expected_commands() -> None:
    parser = build_parser()
    actions = [
        action for action in parser._actions if action.__class__.__name__ == "_SubParsersAction"
    ]
    assert actions, "expected subparsers"
    assert set(actions[0].choices or {}) == {"diagnose", "fix", "run", "pr", "eval"}


def test_run_parser_requires_pipeline_args() -> None:
    parser = build_parser()
    try:
        parser.parse_args(["run"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("run without args must fail")


def test_load_run_meta_missing_returns_empty(tmp_path: Path) -> None:
    assert load_run_meta(tmp_path) == {}


def test_load_run_meta_reads_recorded_values(tmp_path: Path) -> None:
    (tmp_path / "run-meta.json").write_text(
        json.dumps({"workdir": "/tmp/repo", "test_files": ["a.yaml"], "test_command": ["pytest"]})
    )
    meta = load_run_meta(tmp_path)
    assert meta["workdir"] == "/tmp/repo"
    assert meta["test_files"] == ["a.yaml"]
