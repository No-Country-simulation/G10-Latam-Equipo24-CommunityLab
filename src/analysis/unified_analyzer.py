"""Unified analyzer: sentiment + categorization + relevance in ONE Gemini call.

This module implements HU-S2-001 (fused). It replaces the four separate
analysis stories (sentiment, categorization, relevance) with a single
structured LLM call per message.

Design decisions (agreed with the QA matrix #48):
    - The canonical categories are the contract's `InteractionType` values:
      testimonio, pregunta_tecnica, feedback, logro, discusion, otro.
    - `duda_tecnica` is an alias of `pregunta_tecnica`.
    - `pregunta_general` and `comentario_general` map to `otro`.
    - `sentiment.score` is the model's CONFIDENCE (0-1), not polarity.
    - On any failure the analyzer returns a safe default and never raises.
"""
import json
import logging
import re
import unicodedata
from typing import Any, Dict, Optional

from pydantic import ValidationError

from src.domain.models import (
    AnalysisComplete,
    CategorizationResult,
    InputMessage,
    RelevanceResult,
    SentimentResult,
    SentimentType,
)
from src.utils.llm import LLMError, get_llm_client

logger = logging.getLogger(__name__)


# Non-canonical values the LLM may return, mapped to the contract's vocabulary.
_CATEGORY_ALIASES = {
    "duda_tecnica": "pregunta_tecnica",
    "pregunta_general": "otro",
    "comentario_general": "otro",
}

_SENTIMENT_VALUES = {"positivo", "negativo", "neutral"}

# The contract's canonical categories (InteractionType). Anything else -> "otro".
_CANONICAL_CATEGORIES = {
    "testimonio",
    "pregunta_tecnica",
    "feedback",
    "logro",
    "discusion",
    "otro",
}


class GeminiUnifiedAnalyzer:
    """Analyzes one message with a single structured LLM call.

    Usage:
        analyzer = GeminiUnifiedAnalyzer()          # backend from env
        analysis = analyzer.analyze(message)        # -> AnalysisComplete
    """

    def __init__(self, client: Optional[Any] = None) -> None:
        self.client = client or get_llm_client()

    def analyze(self, message: InputMessage) -> AnalysisComplete:
        """Returns the consolidated analysis for one message.

        Never raises: on failure (network, quota, invalid JSON) it returns the
        safe default. Makes exactly ONE LLM call per non-empty message.
        """
        if not message.texto or not message.texto.strip():
            return self._default(message)

        try:
            raw = self.client.generate(self._build_prompt(message))
            data = self._parse_json(raw)
            return self._to_analysis(message, data)
        except (
            LLMError,
            json.JSONDecodeError,
            ValueError,
            AttributeError,
            TypeError,
            ValidationError,
        ) as exc:
            logger.warning(
                "Unified analyzer fell back to default for %r: %s",
                message.id,
                exc,
            )
            return self._default(message)

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def _build_prompt(self, message: InputMessage) -> str:
        """Builds the structured prompt.

        TODO(HU-S2-008): move this template to src/prompts/templates.py so all
        modules share one prompt contract.
        """
        return (
            "Analizá el siguiente mensaje de una comunidad técnica y respondé "
            "ÚNICAMENTE con un JSON válido, sin markdown ni texto extra.\n\n"
            "Estructura exacta esperada:\n"
            '{\n'
            '  "sentiment": {"type": "positivo|negativo|neutral", '
            '"score": <confianza 0.0-1.0>, "reasoning": "..."},\n'
            '  "categorization": {"category": "testimonio|pregunta_tecnica|'
            'feedback|logro|discusion|otro", "topics": ["..."], '
            '"entities": ["..."]},\n'
            '  "relevance": {"score": <0.0-1.0>, "is_marketing_worthy": true|false}\n'
            '}\n\n'
            f"Mensaje:\n<mensaje>\n{message.texto}\n</mensaje>\n"
        )

    # ------------------------------------------------------------------
    # Parsing / mapping
    # ------------------------------------------------------------------

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """Extracts a JSON object from the LLM output.

        Tolerates markdown code fences (```json ... ```) which Gemini commonly
        wraps around its JSON answer.
        """
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("LLM output is not a JSON object")
        return data

    def _to_analysis(
        self, message: InputMessage, data: Dict[str, Any]
    ) -> AnalysisComplete:
        """Maps the LLM JSON into the contract's AnalysisComplete."""
        mid = message.id or ""

        sentiment_data = data.get("sentiment") or {}
        sentiment = self._normalize_sentiment(sentiment_data.get("type"))

        categorization_data = data.get("categorization") or {}
        category = self._normalize_category(categorization_data.get("category"))

        relevance_data = data.get("relevance") or {}
        relevance_score = self._clamp(relevance_data.get("score"))
        # Derived from the score (>= 0.6). The explicit field is redundant and
        # may contradict the score (ANL-15); the score wins.
        is_worthy = relevance_score >= 0.6

        return AnalysisComplete(
            message_id=mid,
            sentiment=SentimentResult(
                message_id=mid,
                sentiment=sentiment,
                score=self._clamp(sentiment_data.get("score", 0.5)),
                reasoning=str(sentiment_data.get("reasoning", "")),
            ),
            categorization=CategorizationResult(
                message_id=mid,
                category=category,
                topics=list(categorization_data.get("topics") or []),
                entities=list(categorization_data.get("entities") or []),
            ),
            relevance=RelevanceResult(
                message_id=mid,
                score=relevance_score,
                is_marketing_worthy=is_worthy,
            ),
        )

    def _default(self, message: InputMessage) -> AnalysisComplete:
        """Safe default used when the LLM fails or the input is empty."""
        mid = message.id or ""
        return AnalysisComplete(
            message_id=mid,
            sentiment=SentimentResult(
                message_id=mid,
                sentiment=SentimentType.NEUTRO,
                score=0.5,
                reasoning="default",
            ),
            categorization=CategorizationResult(
                message_id=mid,
                category="otro",
                topics=[],
                entities=[],
            ),
            relevance=RelevanceResult(
                message_id=mid,
                score=0.0,
                is_marketing_worthy=False,
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_token(value: Optional[str]) -> str:
        """Lowercases, strips accents and turns spaces into underscores."""
        if not value:
            return ""
        text = str(value).strip().lower()
        text = "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )
        return text.replace(" ", "_")

    @classmethod
    def _normalize_sentiment(cls, value: Optional[str]) -> SentimentType:
        token = cls._normalize_token(value)
        if token in _SENTIMENT_VALUES:
            return SentimentType(token)
        return SentimentType.NEUTRO

    @classmethod
    def _normalize_category(cls, value: Optional[str]) -> str:
        token = cls._normalize_token(value)
        if not token:
            return "otro"
        token = _CATEGORY_ALIASES.get(token, token)
        if token not in _CANONICAL_CATEGORIES:
            return "otro"
        return token

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, num))
