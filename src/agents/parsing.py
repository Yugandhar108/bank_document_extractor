"""Utilities for parsing JSON-like LLM responses safely."""

import json
from json import JSONDecodeError


class AgentResponseParseError(ValueError):
    """Raised when an agent response cannot be parsed into valid JSON."""


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def parse_json_response(raw_text: str) -> dict:
    """Parse possibly wrapped JSON text and return a Python dict."""
    if not raw_text or not raw_text.strip():
        raise AgentResponseParseError("Agent response was empty.")

    normalized = _strip_code_fences(raw_text)

    candidates = [normalized]
    extracted = _extract_first_json_object(normalized)
    if extracted:
        candidates.append(extracted)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise AgentResponseParseError("Agent response did not contain valid JSON object.")
