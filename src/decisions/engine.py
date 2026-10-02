"""Rule-based decision engine for CommunityLab."""

from src.domain.interfaces import DecisionEngine
from src.domain.models import (
    ActionType,
    AnalysisComplete,
    AssetType,
    DecisionResult,
)


class RuleBasedDecisionEngine(DecisionEngine):
    """Decides the action for a message using business rules."""

    RELEVANCE_THRESHOLD = 0.6

    def decide(self, analysis: AnalysisComplete) -> DecisionResult:
        """Evaluate an analysis and return the corresponding decision."""

        message_id = analysis.message_id

        # Rule 1: positive testimonial with sufficient relevance -> LinkedIn.
        is_testimonial = False
        if analysis.categorization is not None:
            is_testimonial = analysis.categorization.category == "testimonio"

        is_positive = False
        if analysis.sentiment is not None:
            is_positive = analysis.sentiment.sentiment.value == "positivo"

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
        is_technical_question = False
        if analysis.categorization is not None:
            is_technical_question = (
                analysis.categorization.category == "pregunta_tecnica"
            )

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
