"""Tests for robust JSON extraction from agent responses."""

import pytest

from src.agents.parsing import AgentResponseParseError, parse_json_response


def test_parse_plain_json() -> None:
    raw = '{"account_holder_name": "Alex"}'
    parsed = parse_json_response(raw)
    assert parsed["account_holder_name"] == "Alex"


def test_parse_fenced_json() -> None:
    raw = """```json
{"account_holder_name": "Alex"}
```"""
    parsed = parse_json_response(raw)
    assert parsed["account_holder_name"] == "Alex"


def test_parse_json_with_explanation_wrapping() -> None:
    raw = "Here is the result:\n{\"account_holder_name\": \"Alex\"}\nDone."
    parsed = parse_json_response(raw)
    assert parsed["account_holder_name"] == "Alex"


def test_invalid_json_raises_clear_error() -> None:
    with pytest.raises(AgentResponseParseError):
        parse_json_response("I cannot answer this request")
