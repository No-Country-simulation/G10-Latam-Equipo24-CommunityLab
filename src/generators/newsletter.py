"""Newsletter highlight generator (destaque_newsletter_semanal)."""
from src.domain.models import AnalysisComplete, InputMessage, NewsletterHighlight
from src.generators.base import BaseGenerator
from src.prompts.generators import build_newsletter_prompt


class NewsletterGenerator(BaseGenerator[NewsletterHighlight]):
    """Generates a weekly newsletter highlight from a testimonio/logro."""

    @property
    def output_model(self):
        return NewsletterHighlight

    def build_prompt(self, message: InputMessage, analysis: AnalysisComplete) -> str:
        return build_newsletter_prompt(message)
