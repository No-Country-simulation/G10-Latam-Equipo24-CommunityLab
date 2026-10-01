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
        if (
            analysis.categorization
            and analysis.categorization.category == "testimonio"
            and analysis.sentiment
            and analysis.sentiment.sentiment.value == "positivo"
            and analysis.relevance
            and analysis.relevance.score >= self.RELEVANCE_THRESHOLD
        ):
            return DecisionResult(
                message_id=message_id,
                action=ActionType.PUBLISH,
                asset_type=AssetType.LINKEDIN,
                reason="Testimonio positivo relevante",
            )

        # Rule 2: technical question -> FAQ.
        if (
            analysis.categorization
            and analysis.categorization.category == "pregunta_tecnica"
        ):
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
