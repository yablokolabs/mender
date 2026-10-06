"""Extract JSON objects from model replies without guessing at structure."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class JSONError(ValueError):
    """The model reply did not contain a parseable JSON value."""


def _balanced(text: str, start: int) -> str | None:
    """Return the balanced {...} or [...] slice starting at `start`."""
    opening = text[start]
    closing = "{" if opening == "{" else "["
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == closing:
            depth += 1
        elif char == ("}" if closing == "{" else "]"):
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def extract_json(text: str) -> Any:
    """Parse the first JSON value in `text`: fenced block, raw value, or balanced scan."""
    candidates = [match.strip() for match in _FENCE.findall(text)]
    candidates.append(text.strip())

    first_brace = min(
        (pos for pos in (text.find("{"), text.find("[")) if pos != -1),
        default=-1,
    )
    if first_brace != -1:
        chunk = _balanced(text, first_brace)
        if chunk is not None:
            candidates.append(chunk)

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise JSONError("no parseable JSON value found in model reply")
