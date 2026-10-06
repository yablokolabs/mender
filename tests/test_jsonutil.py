import pytest

from mender.jsonutil import JSONError, extract_json


def test_fenced_json() -> None:
    text = 'Sure! Here is the JSON:\n```json\n{"a": 1, "b": [2, 3]}\n```\nDone.'
    assert extract_json(text) == {"a": 1, "b": [2, 3]}


def test_raw_json() -> None:
    assert extract_json('{"ok": true}') == {"ok": True}


def test_json_with_surrounding_prose() -> None:
    text = 'The answer is {"summary": "bad pod", "n": 1} as requested.'
    assert extract_json(text) == {"summary": "bad pod", "n": 1}


def test_braces_inside_strings() -> None:
    text = '{"text": "value with { braces } and \\" quotes", "n": 2}'
    assert extract_json(text) == {"text": 'value with { braces } and " quotes', "n": 2}


def test_array_value() -> None:
    assert extract_json("steps: [1, 2, 3]") == [1, 2, 3]


def test_no_json_raises() -> None:
    with pytest.raises(JSONError):
        extract_json("there is no structured value here")
