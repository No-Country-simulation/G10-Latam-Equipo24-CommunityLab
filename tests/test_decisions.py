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
    score: float = 0.9,
) -> AnalysisComplete:
    """Build a complete analysis for decision-engine tests."""
    return AnalysisComplete(
        message_id="msg-test",
        sentiment=SentimentResult(
            message_id="msg-test",
            sentiment=sentiment,
            score=score,
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


def test_positive_relevant_logro_goes_to_linkedin():
    """R1 también cubre `logro`: la arquitectura define R1 como
    "Testimonio o logro positivo y relevante". Un mensaje de logro con
    `tipo="otro"` (el default de Telegram) llega por la categoría del LLM.
    """
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="logro",
        sentiment=SentimentType.POSITIVO,
        relevance=0.9,
    )

    message = build_message(tipo="otro")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.PUBLISH
    assert result.asset_type == AssetType.LINKEDIN
    assert result.message_id == "msg-test"


def test_positive_logro_below_relevance_threshold_is_discarded():
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="logro",
        sentiment=SentimentType.POSITIVO,
        relevance=0.4,
    )

    message = build_message(tipo="otro")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_explicit_non_publishable_type_wins_over_logro_category():
    """Precedencia D-B: `message.tipo` explícito pesa más que la categoría del
    LLM. Un `feedback` reconocido con `category="logro"` no debe publicarse,
    porque el tipo declarado manda sobre lo que infirió el analizador.
    """
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="logro",
        sentiment=SentimentType.POSITIVO,
        relevance=0.9,
    )

    message = build_message(tipo="feedback")
    result = engine.decide(message, analysis)

    assert result.action != ActionType.PUBLISH
    assert result.asset_type != AssetType.LINKEDIN


def test_logro_with_non_positive_sentiment_is_not_published():
    """R1 exige sentimiento positivo: un `logro` relevante pero neutro o
    negativo no debe publicarse, aunque el tipo y la relevancia alcancen.
    """
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="logro",
        sentiment=SentimentType.NEUTRO,
        relevance=0.9,
    )

    message = build_message(tipo="otro")
    result = engine.decide(message, analysis)

    assert result.action != ActionType.PUBLISH
    assert result.asset_type != AssetType.LINKEDIN


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


def test_dec_22_negative_technical_question_is_derived():
    # DEC-22: R4 runs before R2 (decision D-I), so a negative technical
    # question is derived to a human instead of being swallowed by the FAQ rule.
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="pregunta_tecnica",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.9,
    )

    message = build_message(tipo="pregunta_tecnica")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DERIVAR
    assert result.asset_type is None


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


def test_high_confidence_negative_message_is_derived():
    # R4 confidence gate: sentiment.score > CONFIDENCE_THRESHOLD (0.8).
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="feedback",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.3,
        score=0.81,
    )

    message = build_message(tipo="feedback")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DERIVAR
    assert result.asset_type is None
    assert result.reason == (
        "Feedback negativo: requiere atención personalizada por el community manager"
    )


def test_low_confidence_negative_message_is_not_derived():
    # R4 confidence gate: 0.79 is below the 0.8 threshold, so R4 does not fire.
    # A non-technical negative message falls through to R3 (DESCARTAR).
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="feedback",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.3,
        score=0.79,
    )

    message = build_message(tipo="feedback")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_low_confidence_negative_technical_question_goes_to_faq():
    # R4 confidence gate: 0.79 does not derive, so the technical question
    # reaches R2 and becomes an FAQ candidate.
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="pregunta_tecnica",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.3,
        score=0.79,
    )

    message = build_message(tipo="pregunta_tecnica")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.CREAR_FAQ
    assert result.asset_type == AssetType.FAQ


def test_exact_threshold_negative_message_is_not_derived():
    # R4 uses a strict > comparison: 0.80 must NOT derive.
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="feedback",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.3,
        score=0.80,
    )

    message = build_message(tipo="feedback")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DESCARTAR
    assert result.asset_type is None


def test_high_relevance_low_confidence_negative_not_derived():
    # Relevance is ignored for the R4 derivation decision.
    engine = RuleBasedDecisionEngine()
    analysis = build_analysis(
        category="testimonio",
        sentiment=SentimentType.NEGATIVO,
        relevance=0.9,
        score=0.5,
    )

    message = build_message(tipo="testimonio")
    result = engine.decide(message, analysis)

    assert result.action == ActionType.DESCARTAR
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
