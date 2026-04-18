"""Centralized, robust JSON extraction for TigerResearchBuddy.

Design mandate: Zero string surgery.
Never use ``replace('```json', '')`` or ``.split('json')``.
Use brace-matching regex to extract the first valid JSON object from
any LLM output, regardless of markdown fencing or prose leakage.

Usage
-----
    from src.utils.json_utils import extract_json, extract_and_validate

    # Basic extraction
    data = extract_json(raw_llm_output)

    # Pydantic-validated extraction
    from pydantic import BaseModel
    class MySchema(BaseModel):
        field: str
    result = extract_and_validate(raw_llm_output, MySchema)
"""

from __future__ import annotations

import json
import re
import logging
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract_json(raw: str) -> Optional[dict]:
    """Extract the first balanced ``{...}`` block from an LLM output string.

    Three-attempt strategy (no string surgery):
    1. Direct ``json.loads`` on the trimmed string.
    2. Regex to find the first ``{`` … last ``}`` block (handles prose leakage
       and markdown fences).
    3. Repair common LLM errors (trailing commas, unescaped newlines) and retry.

    Returns None if all attempts fail.
    """
    if not raw or not isinstance(raw, str):
        return None

    text = raw.strip()

    # ---- Attempt 1: direct parse ----------------------------------------
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # ---- Attempt 2: brace-match extraction --------------------------------
    # Find the first '{' and the last '}' in the string.
    # This handles ``...some text... { ... } ...trailing prose``
    # as well as ````json\n{ ... }\n``` `` fences — without string surgery.
    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            # Fall through to repair
            pass

        # ---- Attempt 3: repair common LLM JSON errors --------------------
        repaired = _repair_json(candidate)
        if repaired is not None:
            return repaired

    logger.warning("extract_json: all three attempts failed. Raw preview: %s", text[:200])
    return None


def extract_and_validate(raw: str, schema: Type[T]) -> Optional[T]:
    """Extract JSON from *raw* and validate it against a Pydantic *schema*.

    Returns a validated Pydantic model instance, or ``None`` if extraction
    or validation fails.  Logs the validation error for traceability.
    """
    data = extract_json(raw)
    if data is None:
        logger.warning("extract_and_validate: JSON extraction returned None.")
        return None
    try:
        return schema(**data)
    except ValidationError as exc:
        logger.warning("extract_and_validate: Pydantic validation failed: %s", exc)
        return None
    except Exception as exc:
        logger.warning("extract_and_validate: unexpected error: %s", exc)
        return None


# ---------------------------------------------------------------------------
# JSON repair helpers (private)
# ---------------------------------------------------------------------------

def _repair_json(json_str: str) -> Optional[dict]:
    """Attempt to repair common LLM JSON errors in sequence.

    Strategies (applied cumulatively on failure):
    1. Strip trailing commas before ``]`` or ``}``.
    2. Replace literal newlines inside strings with ``\\n``.
    3. Both repairs applied together.
    """
    strategies = [
        lambda s: re.sub(r",\s*([\]}])", r"\1", s),
        lambda s: s.replace("\n", " "),
        lambda s: re.sub(r",\s*([\]}])", r"\1", s.replace("\n", " ")),
    ]
    for strategy in strategies:
        try:
            result = json.loads(strategy(json_str))
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, Exception):
            continue
    return None
