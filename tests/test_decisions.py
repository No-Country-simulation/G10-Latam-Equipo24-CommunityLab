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
    InputMessage,
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


def build_message(*, tipo: str) -> InputMessage:
    """Build an input message for decision-engine tests."""
    return InputMessage(
        autor="test-user",
        canal="test",
        tipo=tipo,
        texto="Mensaje de prueba",
        id="msg-test",
    )


def test_positive_relevant_testimonial_goes_to_linkedin():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.POSITIVO,
        relevance=0.6,
    )

    message = build_message(tipo="testimonio")
    result = engine.decide(message, analysis)

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

    message = build_message(tipo="testimonio")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_negative_testimonial_is_derived_to_human():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.9,
    )

    message = build_message(tipo="testimonio")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DERIVAR
    assert result.asset_type is None
    assert result.reason == (
        "Feedback negativo: requiere atención personalizada por el community manager"
    )


def test_negative_feedback_is_derived_to_human():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="feedback",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.2,
    )

    message = build_message(tipo="feedback")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DERIVAR
    assert result.asset_type is None
    assert result.reason == (
        "Feedback negativo: requiere atención personalizada por el community manager"
    )


def test_negative_technical_question_still_goes_to_faq():
    # R2 runs before R4: a negative technical question is still a FAQ.
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="pregunta_tecnica",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.9,
    )

    message = build_message(tipo="pregunta_tecnica")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.CREAR_FAQ
    assert result.asset_type == AssetType.FAQ


def test_negative_message_without_relevance_is_still_derived():
    # R4 has no relevance threshold, unlike R1.
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.0,
    )

    message = build_message(tipo="testimonio")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DERIVAR
    assert result.asset_type is None


def test_technical_question_goes_to_faq():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="pregunta_tecnica",
        sentiment=SentimentType.NEUTRO,
        relevance=0.3,
    )

    message = build_message(tipo="pregunta_tecnica")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.CREAR_FAQ
    assert result.asset_type == AssetType.FAQ


def test_neutral_message_is_discarded():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="feedback",
        sentiment=SentimentType.NEUTRO,
        relevance=0.8,
    )

    message = build_message(tipo="feedback")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_unknown_category_is_discarded():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="categoria_desconocida",
        sentiment=SentimentType.POSITIVO,
        relevance=0.9,
    )

    message = build_message(tipo="discusion")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_empty_analysis_is_discarded():
    engine = RuleBasedDecisionEngine()
    analysis = AnalysisComplete(message_id="msg-empty")
    message = build_message(tipo="discusion")

    result = engine.decide(message, analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_explicit_message_type_takes_precedence_over_analysis_category():
    engine = RuleBasedDecisionEngine()

    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.POSITIVO,
        relevance=0.9,
    )
    message = build_message(tipo="pregunta_tecnica")

    result = engine.decide(message, analysis)

    assert result.action == ActionType.CREAR_FAQ
    assert result.asset_type == AssetType.FAQ


def test_type_otro_falls_back_to_analysis_category():
    engine = RuleBasedDecisionEngine()

    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.POSITIVO,
        relevance=0.85,
    )
    message = build_message(tipo="otro")

    result = engine.decide(message, analysis)

    assert result.action == ActionType.PUBLISH
    assert result.asset_type == AssetType.LINKEDIN


def test_empty_type_falls_back_to_analysis_category():
    engine = RuleBasedDecisionEngine()

    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.POSITIVO,
        relevance=0.85,
    )
    message = build_message(tipo="")

    result = engine.decide(message, analysis)

    assert result.action == ActionType.PUBLISH
    assert result.asset_type == AssetType.LINKEDIN


def test_comentario_general_falls_back_to_analysis_category():
    engine = RuleBasedDecisionEngine()

    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.POSITIVO,
        relevance=0.85,
    )
    message = build_message(tipo="comentario_general")

    result = engine.decide(message, analysis)

    assert result.action == ActionType.PUBLISH
    assert result.asset_type == AssetType.LINKEDIN


def test_explicit_testimonial_type_takes_precedence_over_other_category():
    engine = RuleBasedDecisionEngine()

    analysis = build_analysis(
        category="otro",
        sentiment=SentimentType.POSITIVO,
        relevance=0.90,
    )
    message = build_message(tipo="testimonio")

    result = engine.decide(message, analysis)

    assert result.action == ActionType.PUBLISH
    assert result.asset_type == AssetType.LINKEDIN


def test_technical_question_generates_faq_regardless_of_relevance():
    engine = RuleBasedDecisionEngine()

    analysis = build_analysis(
        category="pregunta_tecnica",
        sentiment=SentimentType.NEUTRO,
        relevance=0.1,
    )
    message = build_message(tipo="pregunta_tecnica")

    result = engine.decide(message, analysis)

    assert result.action == ActionType.CREAR_FAQ
    assert result.asset_type == AssetType.FAQ
