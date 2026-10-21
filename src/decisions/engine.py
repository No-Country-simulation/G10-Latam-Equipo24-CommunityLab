"""Rule-based decision engine for CommunityLab."""

from src.domain.interfaces import DecisionEngine
from src.domain.models import (
    ActionType,
    AnalysisComplete,
    AssetType,
    DecisionResult,
    InputMessage,
    SentimentType,
)

# Explicit `tipo` values that take precedence over the LLM category (decision
# D-B). Shared with the pipeline, which counts `tipo` vs category disagreements
# to measure risk O-16 without changing this precedence.
RECOGNIZED_TYPES = frozenset(
    {
        "testimonio",
        "pregunta_tecnica",
        "feedback",
        "logro",
        "discusion",
    }
)


class RuleBasedDecisionEngine(DecisionEngine):
    """Decides the action for a message using business rules."""

    RELEVANCE_THRESHOLD = 0.6
    CONFIDENCE_THRESHOLD = 0.8

    def decide(
        self, message: InputMessage, analysis: AnalysisComplete
    ) -> DecisionResult:
        """Evaluate an analysis and return the corresponding decision.

        Rule order: R1 -> R4 -> R2 -> R3 (decision D-I).
        """

        message_id = analysis.message_id

        if message.tipo in RECOGNIZED_TYPES:
            effective_type = message.tipo
        elif analysis.categorization is not None:
            effective_type = analysis.categorization.category
        else:
            effective_type = None

        # Rule 1: positive testimonial or achievement ("logro") with sufficient
        # relevance -> LinkedIn. The architecture doc defines R1 as "Testimonio
        # o logro positivo y relevante", and "logro" is a canonical category the
        # LLM emits for achievements, so accepting only "testimonio" silently
        # discarded every achievement (docs/arquitectura-tecnica/analisis-
        # arquitectura.md, Regla 1).
        is_publishable_type = effective_type in {"testimonio", "logro"}

        is_positive = False
        is_negative = False
        negative_confidence = 0.0
        if analysis.sentiment is not None:
            is_positive = analysis.sentiment.sentiment == SentimentType.POSITIVO
            is_negative = analysis.sentiment.sentiment == SentimentType.NEGATIVO
            negative_confidence = analysis.sentiment.score

        is_relevant = False
        if analysis.relevance is not None:
            is_relevant = analysis.relevance.score >= self.RELEVANCE_THRESHOLD

        if is_publishable_type and is_positive and is_relevant:
            return DecisionResult(
                message_id=message_id,
                action=ActionType.PUBLISH,
                asset_type=AssetType.LINKEDIN,
                reason="Testimonio o logro positivo relevante",
            )

        # Rule 4: high-confidence negative feedback -> derive to a human
        # (community manager). Evaluated BEFORE R2 (decision D-I): a negative
        # message needs personal attention even when its type is a technical
        # question, so R2 no longer swallows it. No relevance threshold; only
        # sentiment confidence above the threshold triggers derivation.
        if is_negative and negative_confidence > self.CONFIDENCE_THRESHOLD:
            return DecisionResult(
                message_id=message_id,
                action=ActionType.DERIVAR,
                asset_type=None,
                reason="Feedback negativo: feedback negativo",
            )

        # Rule 2: technical question -> FAQ. Every non-negative technical
        # question reaches this point, because R4 already returned for all
        # negative messages.
        is_technical_question = effective_type == "pregunta_tecnica"

        if is_technical_question:
            return DecisionResult(
                message_id=message_id,
                action=ActionType.CREAR_FAQ,
                asset_type=AssetType.FAQ,
                reason="Duda tecnica o pregunta frecuente",
            )

        # Rule 3: all other cases -> discard.
        return DecisionResult(
            message_id=message_id,
            action=ActionType.DESCARTAR,
            asset_type=None,
            reason="Mensaje neutral o no relevante",
        )
