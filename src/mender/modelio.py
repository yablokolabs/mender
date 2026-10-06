"""Structured (JSON) completion helper with one bounded repair attempt."""

from __future__ import annotations

from typing import Any

from mender.jsonutil import JSONError, extract_json
from mender.router.client import Message, ModelClient

# Nemotron reasoning models can loop in their reasoning budget until
# finish_reason=length with an empty content field. Appending this nudge to the
# SYSTEM message of the repair call reliably breaks the loop (verified against
# Nebius Token Factory, 2026-10-06); nudging only the user turn does not.
_REPAIR_NUDGE = (
    " Reply immediately with ONLY the requested JSON value. "
    "Do not perform extended chain-of-thought reasoning."
)


def _repair_messages(messages: list[Message], bad_reply: str) -> list[Message]:
    """Original messages with the nudge folded into the system prompt.

    An empty (starved) reply is dropped entirely — echoing it back as an
    assistant turn keeps the model in the same loop.
    """
    repaired: list[Message] = []
    has_system = any(message.role == "system" for message in messages)
    for message in messages:
        if message.role == "system":
            repaired.append(Message(role="system", content=message.content + _REPAIR_NUDGE))
        else:
            repaired.append(message)
    if not has_system:
        repaired.insert(0, Message(role="system", content=_REPAIR_NUDGE.strip()))
    if bad_reply.strip():
        repaired.append(Message(role="assistant", content=bad_reply))
    return repaired


def complete_json(
    client: ModelClient,
    tier: str,
    messages: list[Message],
    purpose: str,
    *,
    repair: bool = True,
) -> Any:
    """Complete on `tier` and parse JSON; on parse failure, retry once with the error."""
    reply = client.complete(tier, messages, purpose=purpose)
    try:
        return extract_json(reply.content)
    except JSONError as first_error:
        if not repair:
            raise
        repair_messages = [
            *_repair_messages(messages, reply.content),
            Message(
                role="user",
                content=(
                    f"Your reply was not valid JSON ({first_error}). "
                    "Reply again with ONLY the corrected JSON value, no prose."
                ),
            ),
        ]
        repaired = client.complete(tier, repair_messages, purpose=f"{purpose} (json repair)")
        return extract_json(repaired.content)
