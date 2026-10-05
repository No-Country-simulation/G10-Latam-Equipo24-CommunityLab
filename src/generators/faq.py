"""FAQ generator (sugerencia_contenido_faq)."""
from src.domain.models import AnalysisComplete, FAQSuggestion, InputMessage
from src.generators.base import BaseGenerator
from src.prompts.generators import build_faq_prompt


class FAQGenerator(BaseGenerator[FAQSuggestion]):
    """Generates a FAQ from a technical question."""

    @property
    def output_model(self):
        return FAQSuggestion

    def build_prompt(self, message: InputMessage, analysis: AnalysisComplete) -> str:
        return build_faq_prompt(message)
