"""SDG Impact Analyzer with Pydantic validation and retry logic.

Fix 7: Replaces silent failure (returning score=0) with:
  - Pydantic ImpactSchema for structured validation
  - re.search-based JSON extraction (no brace-counting surgery)
  - Retry loop (max 2 attempts) with JSON-mode forcing
  - RuntimeError on final failure so the API returns HTTP 500
"""

import json
import re
import logging
from typing import List

from pydantic import BaseModel, Field, ValidationError
from rich.console import Console

from ..chatbot.ollama_client import get_ollama_client

console = Console()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schema for validated impact output
# ---------------------------------------------------------------------------

class ImpactSchema(BaseModel):
    """Validated schema for impact analysis results."""
    score: float = Field(ge=0, le=10, description="Impact score 1-10")
    sdgs: List[str] = Field(default_factory=list, description="UN SDG alignments")
    summary: str = Field(default="", description="Why this research matters")


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class ImpactAnalyzer:
    """Analyzes the potential impact of research ideas."""

    MAX_RETRIES = 2

    def __init__(self):
        self.client = get_ollama_client()

    def _build_prompt(self, title: str, description: str, additional_context: str = "") -> str:
        context_str = f"\nAdditional Context (Faculty Achievements):\n{additional_context}\n" if additional_context else ""
        return f"""
        Analyze the following research idea for potential societal impact.
        Title: {title}
        Description: {description}{context_str}
        
        Task:
        1. Assign an "Impact Score" from 1-10 (10 being high global impact).
        2. Identify relevant UN Sustainable Development Goals (SDGs).
        3. Write a 1-sentence summary of why it matters.
        
        Output JSON format ONLY:
        {{
            "score": 8.5,
            "sdgs": ["Goal 2: Zero Hunger", "Goal 13: Climate Action"],
            "summary": "This research addresses critical food security issues..."
        }}
        """

    def _extract_and_validate(self, response: str) -> ImpactSchema:
        """Extract JSON from LLM response and validate via Pydantic.

        Uses regex to isolate the JSON object, then Pydantic to validate.
        Raises ValueError on failure (caller handles retry).
        """
        # Attempt 1: direct parse
        try:
            return ImpactSchema(**json.loads(response.strip()))
        except (json.JSONDecodeError, ValidationError):
            pass

        # Attempt 2: regex extraction
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return ImpactSchema(**data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise ValueError(f"JSON found but validation failed: {e}") from e

        raise ValueError(f"No valid JSON in response: {response[:200]}")

    def analyze_impact(self, title: str, description: str, additional_context: str = "") -> dict:
        """Generates an impact score and SDG alignment (sync, with retry).

        Raises RuntimeError on final failure instead of returning score=0.
        """
        if not self.client._initialized:
            self.client.initialize()

        prompt = self._build_prompt(title, description, additional_context=additional_context)
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.client.generate(
                    prompt,
                    system_prompt="You are an impact analyst. Output JSON only.",
                    options={"format": "json", "temperature": 0.1},
                )
                result = self._extract_and_validate(response)
                return result.model_dump()
            except (ValueError, Exception) as e:
                last_error = e
                logger.warning(f"Impact analysis attempt {attempt}/{self.MAX_RETRIES} failed: {e}")

        raise RuntimeError(
            f"Impact analysis failed after {self.MAX_RETRIES} attempts. "
            f"Last error: {last_error}"
        )

    async def analyze_impact_async(self, title: str, description: str, additional_context: str = "") -> dict:
        """Generates an impact score and SDG alignment (async, with retry).

        Raises RuntimeError on final failure instead of returning score=0.
        """
        if not self.client._initialized:
            self.client.initialize()

        prompt = self._build_prompt(title, description, additional_context=additional_context)
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await self.client.generate_async(
                    prompt,
                    system_prompt="You are an impact analyst. Output JSON only.",
                    options={"format": "json", "temperature": 0.1},
                )
                result = self._extract_and_validate(response)
                return result.model_dump()
            except (ValueError, Exception) as e:
                last_error = e
                logger.warning(f"Impact analysis async attempt {attempt}/{self.MAX_RETRIES} failed: {e}")

        raise RuntimeError(
            f"Impact analysis failed after {self.MAX_RETRIES} attempts. "
            f"Last error: {last_error}"
        )
