"""FAQ generator (sugerencia_contenido_faq)."""
from typing import Any, Dict

from src.domain.models import AnalysisComplete, FAQSuggestion, InputMessage
from src.generators.base import BaseGenerator
from src.prompts.generators import build_faq_prompt

_STATUS = "derivado_a_mentoria"


class FAQGenerator(BaseGenerator[FAQSuggestion]):
    """Generates a FAQ topic suggestion from a technical question.

    The LLM only produces `tema`. The code owns the metadata: `origen` comes
    from the message channel and `status` is fixed, so they never depend on
    the model's output.
    """

    @property
    def output_model(self):
        return FAQSuggestion

    def build_prompt(self, message: InputMessage, analysis: AnalysisComplete) -> str:
        return build_faq_prompt(message)

    def enrich(
        self,
        data: Dict[str, Any],
        message: InputMessage,
        analysis: AnalysisComplete,
    ) -> Dict[str, Any]:
        data["origen"] = message.canal or message.autor or ""
        data["status"] = _STATUS
        return data
