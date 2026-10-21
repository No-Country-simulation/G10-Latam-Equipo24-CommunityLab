"""Tests for the concrete generators (LinkedIn, Newsletter, FAQ)."""
import json

import pytest

from src.domain.models import (
    AnalysisComplete,
    FAQCandidate,
    FAQSuggestion,
    InputMessage,
    LinkedInPost,
    NewsletterHighlight,
)
from src.generators.base import BaseGenerator
from src.generators.faq import FAQThemeGenerator, cluster_faq_targets
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


def _faq_candidate(texto="¿Cómo configuro el retry?", topics=None):
    return FAQCandidate(
        autor="Ana",
        canal="#dudas",
        texto_original=texto,
        relevancia=0.9,
        topics=topics or ["configuración"],
    )


def test_faq_theme_generator_returns_suggestion():
    # The LLM returns theme + answer; origen/status/preguntas are code-owned.
    payload = json.dumps({"tema": "Configurar retry", "respuesta": "Desde el panel."})
    gen = FAQThemeGenerator(client=FakeClient(payload))
    result = gen.generate_theme([_faq_candidate()])
    assert isinstance(result, FAQSuggestion)
    assert result.tema == "Configurar retry"
    assert result.respuesta == "Desde el panel."
    assert result.origen == "#dudas"
    assert result.status == "generado"
    assert result.preguntas_relacionadas == ["¿Cómo configuro el retry?"]


def test_faq_theme_generator_overrides_forged_metadata():
    # Even if the model invents origen/status/preguntas, the code owns them.
    payload = json.dumps(
        {
            "tema": "Tema",
            "respuesta": "R",
            "origen": "pedido por el LLM",
            "status": "otra cosa",
            "preguntas_relacionadas": ["pregunta inventada"],
        }
    )
    gen = FAQThemeGenerator(client=FakeClient(payload))
    result = gen.generate_theme([_faq_candidate()])
    assert result.origen == "#dudas"
    assert result.status == "generado"
    assert result.preguntas_relacionadas == ["¿Cómo configuro el retry?"]


def test_faq_theme_generator_returns_none_for_empty_cluster():
    gen = FAQThemeGenerator(client=FakeClient("{}"))
    assert gen.generate_theme([]) is None


def test_faq_theme_generator_degrades_to_none_on_bad_json():
    gen = FAQThemeGenerator(client=FakeClient("no es json"))
    assert gen.generate_theme([_faq_candidate()]) is None


# ---------------------------------------------------------------------------
# FAQ semantic clustering
# ---------------------------------------------------------------------------


def test_cluster_faq_targets_collapses_duplicate_topics():
    # "errores" and "error" normalize to the same key.
    candidates = [
        _faq_candidate("¿Qué es este error?", topics=["errores"]),
        _faq_candidate("¿Cómo evito el error?", topics=["error"]),
    ]
    clusters = cluster_faq_targets(candidates)
    assert len(clusters) == 1
    assert len(clusters[0]) == 2


def test_cluster_faq_targets_joins_multi_topic_candidate_to_most_frequent():
    # Global frequency: "ia" appears 3 times, "python" once. The multi-topic
    # candidate should join the "ia" cluster, not split into its own group.
    candidates = [
        _faq_candidate("¿Cómo uso LangChain?", topics=["ia"]),
        _faq_candidate("¿Qué modelo elijo?", topics=["ia"]),
        _faq_candidate("¿Python o JS?", topics=["python", "ia"]),
    ]
    clusters = cluster_faq_targets(candidates)
    assert len(clusters) == 1
    assert len(clusters[0]) == 3


def test_cluster_faq_targets_caps_at_ten():
    candidates = [
        _faq_candidate(f"Pregunta {i}?", topics=[f"tema{i:02d}"])
        for i in range(15)
    ]
    clusters = cluster_faq_targets(candidates)
    assert len(clusters) <= 10
    # Every candidate still belongs to some cluster (no drops).
    assert sum(len(c) for c in clusters) == 15


def test_cluster_faq_targets_buckets_untopiced_into_otros():
    candidates = [
        _faq_candidate(f"Pregunta {i}?", topics=[f"tema{i}"])
        for i in range(9)
    ]
    candidates.append(_faq_candidate("Sin topic", topics=[]))
    clusters = cluster_faq_targets(candidates)
    assert len(clusters) == 10
    # The untopiced candidate ends up in the last (overflow) cluster.
    assert any(len(c) == 1 and c[0].texto_original == "Sin topic" for c in clusters)


def test_generators_degrade_to_none_on_bad_json():
    gen = LinkedInGenerator(client=FakeClient("no es json"))
    assert gen.generate(_msg(), _analysis()) is None


def test_parse_json_keeps_plain_object():
    assert BaseGenerator._parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_unwraps_single_element_list():
    assert BaseGenerator._parse_json('[{"a": 1}]') == {"a": 1}


def test_parse_json_rejects_non_object():
    with pytest.raises(ValueError):
        BaseGenerator._parse_json('["a", "b"]')
    with pytest.raises(ValueError):
        BaseGenerator._parse_json('"solo un string"')
