"""Common infrastructure for asset generators.

Every generator (LinkedIn, Newsletter, FAQ) follows the same shape:
    1. build a prompt for its asset type
    2. call the LLM (via src.utils.llm)
    3. parse the JSON response
    4. validate against the contract model

This base class owns steps 2-4. A subclass only implements:
    - `build_prompt(message, analysis) -> str`
    - the `output_model` property (the contract model it produces, e.g.
      LinkedInPost)

Convention (src/utils/llm.py): the client returns RAW text; parsing and
validating against the contract is the caller's responsibility. Here that
caller is this base class.
"""
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from src.domain.models import AnalysisComplete, InputMessage
from src.utils.llm import LLMError, get_llm_client

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseGenerator(ABC, Generic[T]):
    """Common machinery shared by all asset generators.

    `generate()` handles the LLM call, JSON parsing and validation, and
    degrades to None (never raising) on any failure, so the pipeline can simply
    skip the asset.
    """

    def __init__(self, client=None) -> None:
        self.client = client or get_llm_client()

    # -- subclass contract -------------------------------------------------

    @abstractmethod
    def build_prompt(self, message: InputMessage, analysis: AnalysisComplete) -> str:
        """Build the prompt for this asset type."""

    @property
    @abstractmethod
    def output_model(self) -> Type[T]:
        """The contract model this generator produces (e.g. LinkedInPost)."""

    # -- shared machinery --------------------------------------------------

    def generate(
        self, message: InputMessage, analysis: AnalysisComplete
    ) -> Optional[T]:
        """Generate one asset. Never raises: returns None on any failure."""
        try:
            prompt = self.build_prompt(message, analysis)
            raw = self.client.generate(prompt)
            data = self._parse_json(raw)
            data = self.enrich(data, message, analysis)
            return self.output_model(**data)
        except (
            LLMError,
            json.JSONDecodeError,
            ValueError,
            ValidationError,
            AttributeError,
            TypeError,
        ) as exc:
            logger.warning(
                "%s produced no asset for autor=%r: %s",
                type(self).__name__,
                message.autor,
                exc,
            )
            return None

    def enrich(
        self,
        data: Dict[str, Any],
        message: InputMessage,
        analysis: AnalysisComplete,
    ) -> Dict[str, Any]:
        """Hook: subclasses set fields the CODE owns (metadata).

        The LLM only proposes content; fields like `origen` or `status` are
        derived deterministically (e.g. from the message channel). Default
        returns the parsed JSON unchanged.
        """
        return data

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        """Tolerant JSON parse: strips markdown code fences (```json ... ```)."""
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        return json.loads(text)
