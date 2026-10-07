"""Tests for the BaseGenerator shared infrastructure."""
import json

from src.domain.models import AnalysisComplete, InputMessage, LinkedInPost
from src.generators.base import BaseGenerator
from src.utils.llm import LLMClient, LLMError


class FakeClient(LLMClient):
    """Deterministic client for tests."""

    def __init__(self, response: str = "", error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    def generate(self, prompt: str, **kwargs) -> str:
        if self._error:
            raise self._error
        return self._response


class _LinkedInGenerator(BaseGenerator[LinkedInPost]):
    """Minimal concrete subclass to exercise the base machinery."""

    @property
    def output_model(self):
        return LinkedInPost

    def build_prompt(self, message: InputMessage, analysis: AnalysisComplete) -> str:
        return f"Escribi un post de LinkedIn sobre: {message.texto}"


def _msg() -> InputMessage:
    return InputMessage(
        autor="Ana",
        canal="#logros",
        tipo="testimonio",
        texto="Consegui empleo",
    )


def _analysis() -> AnalysisComplete:
    return AnalysisComplete(message_id="m1")


def test_generate_returns_model_on_valid_json():
    gen = _LinkedInGenerator(client=FakeClient(json.dumps({"titulo": "T", "copy": "C"})))
    result = gen.generate(_msg(), _analysis())
    assert isinstance(result, LinkedInPost)
    assert result.titulo == "T"
    assert result.copy == "C"


def test_generate_strips_markdown_fence():
    payload = '```json\n{"titulo": "T", "copy": "C"}\n```'
    gen = _LinkedInGenerator(client=FakeClient(payload))
    result = gen.generate(_msg(), _analysis())
    assert result.titulo == "T"


def test_generate_returns_none_on_llm_error():
    gen = _LinkedInGenerator(client=FakeClient(error=LLMError("quota")))
    assert gen.generate(_msg(), _analysis()) is None


def test_generate_returns_none_on_invalid_json():
    gen = _LinkedInGenerator(client=FakeClient("esto no es json"))
    assert gen.generate(_msg(), _analysis()) is None


def test_generate_returns_none_on_validation_error():
    # `copy` es obligatorio en LinkedInPost; faltarlo debe degradar a None.
    gen = _LinkedInGenerator(client=FakeClient(json.dumps({"titulo": "falta copy"})))
    assert gen.generate(_msg(), _analysis()) is None
