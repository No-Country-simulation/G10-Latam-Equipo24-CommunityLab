"""Rule-based decision engine for CommunityLab."""

from src.domain.interfaces import DecisionEngine
from src.domain.models import (
    ActionType,
    AnalysisComplete,
    AssetType,
    DecisionResult,
    InputMessage,
)


class RuleBasedDecisionEngine(DecisionEngine):
    """Decides the action for a message using business rules."""

    RELEVANCE_THRESHOLD = 0.6

    def decide(
        self, message: InputMessage, analysis: AnalysisComplete
    ) -> DecisionResult:
        """Evaluate an analysis and return the corresponding decision."""

        message_id = analysis.message_id

        # Explicit message type takes precedence over LLM category.
        recognized_types = {
            "testimonio",
            "pregunta_tecnica",
            "feedback",
            "logro",
            "discusion",
        }

        if message.tipo in recognized_types:
            effective_type = message.tipo
        elif analysis.categorization is not None:
            effective_type = analysis.categorization.category
        else:
            effective_type = None

        # Rule 1: positive testimonial with sufficient relevance -> LinkedIn.
        is_testimonial = effective_type == "testimonio"

        is_positive = False
        is_negative = False
        if analysis.sentiment is not None:
            is_positive = analysis.sentiment.sentiment.value == "positivo"
            is_negative = analysis.sentiment.sentiment.value == "negativo"

        is_relevant = False
        if analysis.relevance is not None:
            is_relevant = analysis.relevance.score >= self.RELEVANCE_THRESHOLD

        if is_testimonial and is_positive and is_relevant:
            return DecisionResult(
                message_id=message_id,
                action=ActionType.PUBLISH,
                asset_type=AssetType.LINKEDIN,
                reason="Testimonio positivo relevante",
            )

        # Rule 2: technical question -> FAQ.
        is_technical_question = effective_type == "pregunta_tecnica"

        if is_technical_question:
            return DecisionResult(
                message_id=message_id,
                action=ActionType.CREAR_FAQ,
                asset_type=AssetType.FAQ,
                reason="Duda tecnica o pregunta frecuente",
            )

        # Rule 4: negative feedback -> derive to a human (community manager).
        # No relevance threshold and no type check: R2 already handled technical
        # questions, so any remaining negative message needs personal attention.
        if is_negative:
            return DecisionResult(
                message_id=message_id,
                action=ActionType.DERIVAR,
                asset_type=None,
                reason="Feedback negativo: requiere atención personalizada por el community manager",
            )

        # Rule 3: all other cases -> discard.
        return DecisionResult(
            message_id=message_id,
            action=ActionType.DESCARTAR,
            asset_type=None,
            reason="Mensaje neutral o no relevante",
        )
