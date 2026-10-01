"""Tests for the rule-based decision engine."""

from src.decisions.engine import RuleBasedDecisionEngine
from src.domain.models import (
    AnalysisComplete,
    CategorizationResult,
    RelevanceResult,
    SentimentResult,
    SentimentType,
    ActionType,
    AssetType,
)


def build_analysis(
    *,
    category: str,
    sentiment: SentimentType = SentimentType.POSITIVO,
    relevance: float = 0.8,
) -> AnalysisComplete:
    """Build a complete analysis for decision-engine tests."""
    return AnalysisComplete(
        message_id="msg-test",
        sentiment=SentimentResult(
            message_id="msg-test",
            sentiment=sentiment,
            score=0.9,
            reasoning="test",
        ),
        categorization=CategorizationResult(
            message_id="msg-test",
            category=category,
        ),
        relevance=RelevanceResult(
            message_id="msg-test",
            score=relevance,
            is_marketing_worthy=relevance >= 0.6,
        ),
    )


def test_positive_relevant_testimonial_goes_to_linkedin():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.POSITIVO,
        relevance=0.6,
    )

    result = engine.decide(analysis)

    assert result.action == ActionType.PUBLISH
    assert result.asset_type == AssetType.LINKEDIN
    assert result.message_id == "msg-test"


def test_positive_testimonial_below_relevance_threshold_is_discarded():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.POSITIVO,
        relevance=0.59,
    )

    result = engine.decide(analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_negative_testimonial_is_discarded():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.9,
    )

    result = engine.decide(analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_technical_question_goes_to_faq():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="pregunta_tecnica",
        sentiment=SentimentType.NEUTRO,
        relevance=0.3,
    )

    result = engine.decide(analysis)

    assert result.action == ActionType.CREAR_FAQ
    assert result.asset_type == AssetType.FAQ


def test_neutral_message_is_discarded():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="feedback",
        sentiment=SentimentType.NEUTRO,
        relevance=0.8,
    )

    result = engine.decide(analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_unknown_category_is_discarded():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="categoria_desconocida",
        sentiment=SentimentType.POSITIVO,
        relevance=0.9,
    )

    result = engine.decide(analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None
