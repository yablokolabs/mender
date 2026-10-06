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


def test_repair_disabled_raises(ledger: UsageLedger) -> None:
    sender = FakeSender(["no json at all"])
    client = make_client(sender, ledger)
    with pytest.raises(JSONError):
        complete_json(
            client, "nano", [Message(role="user", content="hi")], purpose="t", repair=False
        )
