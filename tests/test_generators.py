"""Tests for the concrete generators (LinkedIn, Newsletter, FAQ)."""
import json

from src.domain.models import (
    AnalysisComplete,
    FAQSuggestion,
    InputMessage,
    LinkedInPost,
    NewsletterHighlight,
)
from src.generators.faq import FAQGenerator
from src.generators.linkedin import LinkedInGenerator
from src.generators.newsletter import NewsletterGenerator
from src.utils.llm import LLMClient


class FakeClient(LLMClient):
    """Returns a canned JSON payload."""

    def __init__(self, payload: str) -> None:
        self._payload = payload

    def generate(self, prompt: str, **kwargs) -> str:
        return self._payload


def _msg() -> InputMessage:
    return InputMessage(autor="Ana", canal="#logros", tipo="testimonio", texto="Consegui empleo")


def _analysis() -> AnalysisComplete:
    return AnalysisComplete(message_id="m1")


def test_linkedin_generator_returns_linkedin_post():
    payload = json.dumps({"titulo": "T", "copy": "C"})
    gen = LinkedInGenerator(client=FakeClient(payload))
    result = gen.generate(_msg(), _analysis())
    assert isinstance(result, LinkedInPost)
    assert result.titulo == "T"


def test_newsletter_generator_returns_highlight():
    payload = json.dumps({"seccion": "Logro", "titular": "T", "resumen": "R"})
    gen = NewsletterGenerator(client=FakeClient(payload))
    result = gen.generate(_msg(), _analysis())
    assert isinstance(result, NewsletterHighlight)
    assert result.titular == "T"


def test_faq_generator_returns_suggestion():
    payload = json.dumps({"tema": "LangGraph", "origen": "O", "status": "derivado_a_mentoria"})
    gen = FAQGenerator(client=FakeClient(payload))
    result = gen.generate(_msg(), _analysis())
    assert isinstance(result, FAQSuggestion)
    assert result.tema == "LangGraph"
    assert result.status == "derivado_a_mentoria"


def test_generators_degrade_to_none_on_bad_json():
    gen = LinkedInGenerator(client=FakeClient("no es json"))
    assert gen.generate(_msg(), _analysis()) is None
