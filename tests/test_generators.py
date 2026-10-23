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
    assert result.pregunta_representativa == "¿Cómo configuro el retry?"
    assert result.total_preguntas == 1


def test_faq_theme_generator_overrides_forged_metadata():
    # Even if the model invents origen/status/pregunta, the code owns them.
    payload = json.dumps(
        {
            "tema": "Tema",
            "respuesta": "R",
            "origen": "pedido por el LLM",
            "status": "otra cosa",
            "pregunta_representativa": "pregunta inventada",
        }
    )
    gen = FAQThemeGenerator(client=FakeClient(payload))
    result = gen.generate_theme([_faq_candidate()])
    assert result.origen == "#dudas"
    assert result.status == "generado"
    assert result.pregunta_representativa == "¿Cómo configuro el retry?"
    assert result.total_preguntas == 1


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
    temas, huerfanos = cluster_faq_targets(candidates)
    assert len(temas) == 1
    assert len(temas[0]) == 2
    assert huerfanos == []


def test_cluster_faq_targets_joins_multi_topic_candidate_to_most_frequent():
    # Global frequency: "zeta" appears 3 times, "alfa" once. The multi-topic
    # candidate should join the "zeta" cluster, not split into its own group.
    # The topic names are picked so the alphabetical tie-break alone would pick
    # "alfa": only the frequency priority can put the candidate in "zeta".
    candidates = [
        _faq_candidate("¿Cómo uso LangChain?", topics=["zeta"]),
        _faq_candidate("¿Qué modelo elijo?", topics=["zeta"]),
        _faq_candidate("¿Python o JS?", topics=["alfa", "zeta"]),
    ]
    temas, huerfanos = cluster_faq_targets(candidates)
    assert len(temas) == 1
    assert len(temas[0]) == 3
    assert huerfanos == []


def test_cluster_faq_targets_keeps_frequency_priority_for_accented_topics():
    # "análisis de datos" appears 3 times, "python" once. The accented topic
    # must keep the frequency priority: the grouping key drops the accent
    # ("analisis de datos") while the ranked label keeps it.
    candidates = [
        _faq_candidate("¿Cómo analizo datos?", topics=["análisis de datos"]),
        _faq_candidate("¿Qué dataset uso?", topics=["análisis de datos"]),
        _faq_candidate("¿Python o JS?", topics=["python", "análisis de datos"]),
    ]
    temas, huerfanos = cluster_faq_targets(candidates)
    assert len(temas) == 1
    assert len(temas[0]) == 3
    assert huerfanos == []


def test_cluster_faq_targets_caps_at_nine():
    candidates = [
        _faq_candidate(f"Pregunta {i}?", topics=[f"tema{i:02d}"])
        for i in range(15)
    ]
    temas, huerfanos = cluster_faq_targets(candidates)
    assert len(temas) <= 9
    # Every candidate still belongs to some cluster or orphaned (no drops).
    assert sum(len(c) for c in temas) + len(huerfanos) == 15


def test_cluster_faq_targets_buckets_untopiced_into_otros():
    candidates = [
        _faq_candidate(f"Pregunta {i}?", topics=[f"tema{i}"])
        for i in range(9)
    ]
    candidates.append(
        FAQCandidate(
            autor="Ana",
            canal="#dudas",
            texto_original="Sin topic",
            relevancia=0.9,
            topics=[],
        )
    )
    temas, huerfanos = cluster_faq_targets(candidates)
    assert len(temas) == 9
    # The untopiced candidate is returned as orphaned.
    assert any(c.texto_original == "Sin topic" for c in huerfanos)


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
