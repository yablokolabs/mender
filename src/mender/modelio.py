"""Structured (JSON) completion helper with one bounded repair attempt."""

from __future__ import annotations

from typing import Any

from mender.jsonutil import JSONError, extract_json
from mender.router.client import Message, ModelClient


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
            *messages,
            Message(role="assistant", content=reply.content),
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
