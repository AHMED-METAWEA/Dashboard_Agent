"""
Dashboard Agent — Robust JSON Parser
Extracts valid JSON from Groq LLM responses that may contain markdown
fencing, preamble text, or other non-JSON content.
"""

import re
import json
from typing import Any, Optional


def extract_json(text: str) -> Any:
    """
    Extract and parse JSON from an LLM response string.

    Handles common LLM output issues:
      - Markdown code fences (```json ... ```)
      - Preamble/postscript text around JSON
      - Nested JSON objects and arrays
      - Trailing commas (basic cleanup)

    Args:
        text: Raw LLM response string.

    Returns:
        Parsed JSON as a Python object (dict or list).

    Raises:
        ValueError: If no valid JSON can be extracted.
    """
    if not text or not text.strip():
        raise ValueError("Empty response from LLM — no JSON to extract.")

    cleaned = text.strip()

    # ── Step 1: Remove markdown code fences ──────────────────────────
    fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    fence_match = re.search(fence_pattern, cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    # ── Step 2: Try direct parse ─────────────────────────────────────
    parsed = _try_parse(cleaned)
    if parsed is not None:
        return parsed

    # ── Step 3: Find JSON object {...} ───────────────────────────────
    obj_match = _find_balanced(cleaned, "{", "}")
    if obj_match:
        parsed = _try_parse(obj_match)
        if parsed is not None:
            return parsed

    # ── Step 4: Find JSON array [...] ────────────────────────────────
    arr_match = _find_balanced(cleaned, "[", "]")
    if arr_match:
        parsed = _try_parse(arr_match)
        if parsed is not None:
            return parsed

    # ── Step 5: Aggressive cleanup and retry ─────────────────────────
    aggressive = _aggressive_cleanup(cleaned)
    parsed = _try_parse(aggressive)
    if parsed is not None:
        return parsed

    raise ValueError(
        f"Could not extract valid JSON from LLM response. "
        f"Response preview: {text[:300]}..."
    )


def _try_parse(text: str) -> Optional[Any]:
    """Try to parse a string as JSON, returning None on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _find_balanced(text: str, open_char: str, close_char: str) -> Optional[str]:
    """
    Find the first balanced bracket/brace pair in text.
    Handles nested structures correctly.
    """
    start = text.find(open_char)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None


def _aggressive_cleanup(text: str) -> str:
    """
    Apply aggressive cleanup to salvage malformed JSON:
      - Remove trailing commas before ] or }
      - Remove single-line comments
      - Replace single quotes with double quotes (if no double quotes present)
    """
    cleaned = text

    # Remove single-line comments (// ...)
    cleaned = re.sub(r"//[^\n]*", "", cleaned)

    # Remove trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    # If no double quotes exist but single quotes do, swap them
    if '"' not in cleaned and "'" in cleaned:
        cleaned = cleaned.replace("'", '"')

    # Replace Python-style True/False/None with JSON equivalents
    cleaned = re.sub(r"\bTrue\b", "true", cleaned)
    cleaned = re.sub(r"\bFalse\b", "false", cleaned)
    cleaned = re.sub(r"\bNone\b", "null", cleaned)

    return cleaned


def safe_json_get(data: dict, key: str, default: Any = None, expected_type: type = None) -> Any:
    """
    Safely get a value from a parsed JSON dict with type checking.

    Args:
        data: Parsed JSON dictionary.
        key: Key to look up.
        default: Default value if key is missing or type mismatch.
        expected_type: Expected Python type; returns default on mismatch.

    Returns:
        The value if found and type-correct, else default.
    """
    value = data.get(key, default)
    if expected_type is not None and not isinstance(value, expected_type):
        return default
    return value
