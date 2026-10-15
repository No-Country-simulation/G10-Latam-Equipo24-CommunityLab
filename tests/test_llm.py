"""Tests for the LLM client layer (src/utils/llm.py)."""
import json
import sys
import types
from types import SimpleNamespace

import pytest

from src.domain.models import InputMessage
from src.prompts.templates import build_analysis_prompt
from src.utils.llm import LLMError, OllamaClient, RuleBasedClient


def _install_fake_module(monkeypatch, name: str, module: types.ModuleType):
    """Inject a fake module into sys.modules so `import name` resolves locally."""
    monkeypatch.setitem(sys.modules, name, module)


def _fake_openai_module(content: str, captured: dict):
    """A hermetic stand-in for the `openai` package (no SDK, no network)."""

    class FakeCompletions:
        def __init__(self, captured: dict):
            self.captured = captured

        def create(self, **kwargs):
            self.captured["create_kwargs"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    class FakeChat:
        def __init__(self, captured: dict):
            self.completions = FakeCompletions(captured)

    class FakeOpenAI:
        def __init__(self, base_url, api_key):
            self.captured = captured
            self.captured["base_url"] = base_url
            self.captured["api_key"] = api_key
            self.chat = FakeChat(captured)

    module = types.ModuleType("openai")
    module.OpenAI = FakeOpenAI
    return module


def test_ollama_cloud_mode_calls_openai_compatible_endpoint(monkeypatch):
    captured = {}
    _install_fake_module(
        monkeypatch, "openai", _fake_openai_module("respuesta-json", captured)
    )
    monkeypatch.setenv("OLLAMA_API_KEY", "ollama-test-key")
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:31b")

    client = OllamaClient()
    result = client.generate("prompt de prueba")

    assert result == "respuesta-json"
    assert captured["base_url"] == "https://ollama.com/v1"
    assert captured["api_key"] == "ollama-test-key"
    assert captured["create_kwargs"]["model"] == "gemma4:31b"
    assert captured["create_kwargs"]["messages"] == [
        {"role": "user", "content": "prompt de prueba"}
    ]


def test_ollama_cloud_mode_failure_raises_llm_error(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            raise RuntimeError("boom cloud")

    class FakeOpenAI:
        def __init__(self, base_url, api_key):
            captured["base_url"] = base_url
            self.chat = SimpleNamespace(completions=FakeCompletions())

    module = types.ModuleType("openai")
    module.OpenAI = FakeOpenAI
    _install_fake_module(monkeypatch, "openai", module)
    monkeypatch.setenv("OLLAMA_API_KEY", "ollama-test-key")

    client = OllamaClient()
    with pytest.raises(LLMError):
        client.generate("prompt de prueba")


def _fake_ollama_module(content: str, captured: dict):
    """A hermetic stand-in for the `ollama` package (local SDK, no server)."""

    def chat(model, messages, **kwargs):
        captured["model"] = model
        captured["messages"] = messages
        return {"message": {"content": content}}

    module = types.ModuleType("ollama")
    module.chat = chat
    return module


def test_ollama_local_mode_without_key_uses_native_sdk(monkeypatch):
    captured = {}
    _install_fake_module(
        monkeypatch, "ollama", _fake_ollama_module("respuesta-local", captured)
    )
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1")

    client = OllamaClient()
    result = client.generate("prompt local")

    assert result == "respuesta-local"
    assert captured["model"] == "llama3.1"
    assert captured["messages"] == [{"role": "user", "content": "prompt local"}]


def test_ollama_local_mode_failure_raises_llm_error(monkeypatch):
    def chat(model, messages, **kwargs):
        raise ConnectionError("no ollama serve")

    module = types.ModuleType("ollama")
    module.chat = chat
    _install_fake_module(monkeypatch, "ollama", module)
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

    client = OllamaClient()
    with pytest.raises(LLMError):
        client.generate("prompt local")


def test_rule_based_queja_con_exclamacion_es_negativa():
    client = RuleBasedClient()
    queja = InputMessage(
        autor="Ana", canal="#feedback", tipo="otro",
        texto="¡Qué desastre! Gracias por nada, perdí dos semanas.",
    )
    data = json.loads(client.generate(build_analysis_prompt(queja)))
    assert data["sentiment"]["type"] == "negativo"
    assert data["categorization"]["category"] == "feedback"


def test_rule_based_analysis_ignores_prompt_instructions():
    """Regression: los indicadores miran el mensaje, no el prompt completo.

    El prompt de análisis contiene "éxito" y "?" en las instrucciones; si el
    cliente los mirara, TODA pregunta caería en el branch de testimonio y un
    mensaje neutro jamás sería DESCARTAR (el bot del escalón 4 depende de
    esta clasificación cuando el mensaje no trae `tipo`).
    """
    client = RuleBasedClient()

    pregunta = InputMessage(
        autor="Dev",
        canal="#dudas",
        tipo="otro",
        texto="¿Cómo hago para configurar el backend?",
    )
    data = json.loads(client.generate(build_analysis_prompt(pregunta)))
    assert data["categorization"]["category"] == "pregunta_tecnica"
    assert data["sentiment"]["type"] == "neutral"

    testimonio = InputMessage(
        autor="Ana",
        canal="#logros",
        tipo="otro",
        texto="Logré mi primer empleo, gracias a la comunidad!",
    )
    data = json.loads(client.generate(build_analysis_prompt(testimonio)))
    assert data["categorization"]["category"] == "testimonio"
    assert data["sentiment"]["type"] == "positivo"


def test_rule_based_analysis_detects_negative_feedback():
    """Regression: a complaint must surface "negativo" so R4 deriva to human.

    Before the negative branch, the deterministic backend only produced
    "neutral"/"positivo", so feedback_negativo was always 0 on demos/CI even
    though the CSV samples carry real complaints (D-F #97).
    """
    client = RuleBasedClient()

    queja = InputMessage(
        autor="Federico",
        canal="#feedback",
        tipo="otro",
        texto="El canal de ayuda quedó sin respuestas varias horas y no hay un plan B.",
    )
    data = json.loads(client.generate(build_analysis_prompt(queja)))
    assert data["sentiment"]["type"] == "negativo"
    assert data["categorization"]["category"] == "feedback"

    queja_por_retraso = InputMessage(
        autor="Diego",
        canal="#feedback",
        tipo="otro",
        texto="Las correcciones de los proyectos tardan demasiado: perdí dos semanas.",
    )
    data = json.loads(client.generate(build_analysis_prompt(queja_por_retraso)))
    assert data["sentiment"]["type"] == "negativo"
    assert data["categorization"]["category"] == "feedback"

    duda = InputMessage(
        autor="Dev",
        canal="#dudas",
        tipo="otro",
        texto="¿Cómo hago para configurar el backend?",
    )
    data = json.loads(client.generate(build_analysis_prompt(duda)))
    assert data["sentiment"]["type"] == "neutral"
    assert data["categorization"]["category"] == "pregunta_tecnica"


def test_rule_based_empty_message_defaults_to_discusion():
    """Un <mensaje> vacío no debe clasificarse a partir de las instrucciones."""
    client = RuleBasedClient()
    vacio = InputMessage(autor="Ana", canal="#feedback", tipo="otro", texto="   ")
    data = json.loads(client.generate(build_analysis_prompt(vacio)))
    assert data["categorization"]["category"] == "discusion"
    assert data["sentiment"]["type"] == "neutral"
