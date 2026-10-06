import pytest
from conftest import FakeSender, make_client

from mender.jsonutil import JSONError
from mender.modelio import complete_json
from mender.router.client import Message
from mender.router.usage import UsageLedger


def test_parse_success_single_call(ledger: UsageLedger) -> None:
    sender = FakeSender(['{"queries": ["a"]}'])
    client = make_client(sender, ledger)
    result = complete_json(client, "nano", [Message(role="user", content="hi")], purpose="t")
    assert result == {"queries": ["a"]}
    assert len(sender.calls) == 1


def test_repair_attempt_on_invalid_json(ledger: UsageLedger) -> None:
    sender = FakeSender(["I think the answer is unclear.", '{"queries": ["oomkilled"]}'])
    client = make_client(sender, ledger)
    result = complete_json(client, "nano", [Message(role="user", content="hi")], purpose="t")
    assert result == {"queries": ["oomkilled"]}
    assert len(sender.calls) == 2
    repair_turn = sender.calls[1]
    assert repair_turn[-1]["role"] == "user"
    assert "not valid JSON" in str(repair_turn[-1]["content"])


def test_repair_folds_nudge_into_system_and_drops_empty_reply(ledger: UsageLedger) -> None:
    """A starved (empty) reply must not be echoed back; the anti-reasoning
    nudge must land in the SYSTEM message — user-turn nudges do not break
    Nemotron's runaway-reasoning loop (verified against Nebius 2026-10-06)."""
    sender = FakeSender(["", '{"queries": ["oomkilled"]}'])
    client = make_client(sender, ledger)
    result = complete_json(
        client,
        "nano",
        [
            Message(role="system", content="sys prompt"),
            Message(role="user", content="hi"),
        ],
        purpose="t",
    )
    assert result == {"queries": ["oomkilled"]}
    repair_turn = sender.calls[1]
    system_turns = [m for m in repair_turn if m["role"] == "system"]
    assert len(system_turns) == 1
    assert "Do not perform extended chain-of-thought reasoning" in str(system_turns[0]["content"])
    assert not any(m["role"] == "assistant" and m["content"] == "" for m in repair_turn)
    assert repair_turn[-1]["role"] == "user"


def test_repair_disabled_raises(ledger: UsageLedger) -> None:
    sender = FakeSender(["no json at all"])
    client = make_client(sender, ledger)
    with pytest.raises(JSONError):
        complete_json(
            client, "nano", [Message(role="user", content="hi")], purpose="t", repair=False
        )
