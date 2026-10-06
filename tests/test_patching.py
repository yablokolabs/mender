import json
from pathlib import Path

import pytest
from conftest import FakeSender, make_client

from mender.diagnosis import RootCauseReport
from mender.evidence import ClusterEvidence
from mender.patching import (
    Patch,
    PatchError,
    PatchFile,
    apply_patch,
    propose_patch,
    read_files,
    validate_patch,
)
from mender.router.usage import UsageLedger


def _report() -> RootCauseReport:
    return RootCauseReport(
        service="web",
        namespace="shop",
        title="OOMKilled",
        root_cause="memory limit too low",
        mechanism="kernel kills the container",
    )


def _evidence() -> ClusterEvidence:
    return ClusterEvidence(
        service="web",
        namespace="shop",
        collected_at="2026-10-06T00:00:00+00:00",
        events="Warning OOMKilled",
    )


ALLOWED = {"deploy.yaml": "resources:\n  limits:\n    memory: 64Mi\n"}


def test_propose_patch_parses_reply(ledger: UsageLedger) -> None:
    reply = json.dumps(
        {
            "files": [
                {"path": "deploy.yaml", "content": "resources:\n  limits:\n    memory: 512Mi\n"}
            ],
            "rationale": "raise limit above heap",
        }
    )
    sender = FakeSender([reply])
    client = make_client(sender, ledger)
    patch = propose_patch(client, _report(), _evidence(), ALLOWED)
    assert patch.paths == ["deploy.yaml"]
    assert patch.rationale == "raise limit above heap"
    prompt = sender.last_user_message()
    assert "memory limit too low" in prompt
    assert "=== FILE: deploy.yaml ===" in prompt


def test_propose_patch_rejects_empty_reply(ledger: UsageLedger) -> None:
    sender = FakeSender(['{"files": [], "rationale": "nothing"}'])
    client = make_client(sender, ledger)
    with pytest.raises(PatchError, match="no files"):
        propose_patch(client, _report(), _evidence(), ALLOWED)


def test_validate_rejects_escapes_and_unknown_paths() -> None:
    with pytest.raises(PatchError, match="unsafe"):
        validate_patch(Patch(files=[PatchFile(path="../evil.yaml", content="x")]), set(ALLOWED))
    with pytest.raises(PatchError, match="outside allowed"):
        validate_patch(Patch(files=[PatchFile(path="other.yaml", content="x")]), set(ALLOWED))
    with pytest.raises(PatchError, match="unsafe"):
        validate_patch(Patch(files=[PatchFile(path="/etc/passwd", content="x")]), set(ALLOWED))
    with pytest.raises(PatchError, match="duplicate"):
        validate_patch(
            Patch(
                files=[
                    PatchFile(path="deploy.yaml", content="a"),
                    PatchFile(path="deploy.yaml", content="b"),
                ]
            ),
            set(ALLOWED),
        )


def test_apply_patch_writes_and_detects_changes(tmp_path: Path) -> None:
    (tmp_path / "deploy.yaml").write_text(ALLOWED["deploy.yaml"])
    changed_content = "resources:\n  limits:\n    memory: 512Mi\n"
    changed = apply_patch(
        Patch(files=[PatchFile(path="deploy.yaml", content=changed_content)]),
        tmp_path,
        set(ALLOWED),
    )
    assert changed == ["deploy.yaml"]
    assert (tmp_path / "deploy.yaml").read_text() == changed_content

    # Applying the same content again reports no change.
    again = apply_patch(
        Patch(files=[PatchFile(path="deploy.yaml", content=changed_content)]),
        tmp_path,
        set(ALLOWED),
    )
    assert again == []


def test_read_files_missing_paths_skipped(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("a: 1")
    contents = read_files(tmp_path, ["a.yaml", "missing.yaml"])
    assert contents == {"a.yaml": "a: 1"}
