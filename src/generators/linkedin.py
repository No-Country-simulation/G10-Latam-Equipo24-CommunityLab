"""LinkedIn post generator (post_linkedin)."""
from src.domain.models import AnalysisComplete, InputMessage, LinkedInPost
from src.generators.base import BaseGenerator
from src.prompts.generators import build_linkedin_prompt


class LinkedInGenerator(BaseGenerator[LinkedInPost]):
    """Generates a LinkedIn post from a testimonio/logro."""

    @property
    def output_model(self):
        return LinkedInPost

    def build_prompt(self, message: InputMessage, analysis: AnalysisComplete) -> str:
        return build_linkedin_prompt(message)
