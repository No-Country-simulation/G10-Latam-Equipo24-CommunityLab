"""Unit tests for GeminiUnifiedAnalyzer (HU-S2-001).

Covers the analyzer's contract with mocked LLM responses (no real API key).
Case IDs (ANL-xx) follow the QA matrix in docs/pruebas/analisis-decisiones.md.
"""
import json

from src.analysis.unified_analyzer import GeminiUnifiedAnalyzer
from src.domain.models import InputMessage, SentimentType
from src.utils.llm import LLMError


class FakeClient:
    """Deterministic fake LLM client returning a canned response (or error)."""

    def __init__(self, response):
        self._response = response
        self.calls = 0

    def generate(self, prompt, **kwargs):
        self.calls += 1
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class SequenceClient:
    """Returns a sequence of canned responses/errors, one per call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def generate(self, prompt, **kwargs):
        idx = self.calls
        self.calls += 1
        if idx >= len(self._responses):
            return "{}"
        resp = self._responses[idx]
        if isinstance(resp, Exception):
            raise resp
        return resp


def _msg(texto: str = "hola", tipo: str = "otro") -> InputMessage:
    return InputMessage(autor="A", canal="#c", tipo=tipo, texto=texto, id="m1")


def _full_json() -> str:
    return json.dumps(
        {
            "sentiment": {"type": "positivo", "score": 0.9, "reasoning": "alegre"},
            "categorization": {
                "category": "testimonio",
                "topics": ["empleo"],
                "entities": ["Oracle"],
            },
            "relevance": {"score": 0.8, "is_marketing_worthy": True},
        }
    )


# ANL-01: valid JSON maps to AnalysisComplete (message_id injected by analyzer)
def test_maps_valid_json_to_analysis():
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(_full_json()))
    result = analyzer.analyze(_msg())

    assert result.message_id == "m1"
    assert result.sentiment.sentiment == SentimentType.POSITIVO
    assert result.sentiment.score == 0.9
    assert result.categorization.category == "testimonio"
    assert result.categorization.topics == ["empleo"]
    assert result.relevance.is_marketing_worthy is True


# ANL-02: exactly one LLM call per message
def test_single_llm_call_per_message():
    client = FakeClient(_full_json())
    analyzer = GeminiUnifiedAnalyzer(client=client)
    analyzer.analyze(_msg())
    assert client.calls == 1


# ANL-03: JSON wrapped in a markdown fence is extracted
def test_parses_fenced_json():
    fenced = "```json\n" + _full_json() + "\n```"
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(fenced))
    result = analyzer.analyze(_msg())
    assert result.sentiment.sentiment == SentimentType.POSITIVO


# ANL-04: free text (not JSON) returns the default, without raising
def test_free_text_returns_default():
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient("Lo siento, no puedo analizar ese mensaje."))
    result = analyzer.analyze(_msg())
    assert result.sentiment.sentiment == SentimentType.NEUTRO
    assert result.categorization.category == "otro"
    assert result.relevance.score == 0.0


# ANL-06: network failure returns the default, no exception propagates
def test_connection_error_returns_default():
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(LLMError("connection lost")))
    result = analyzer.analyze(_msg())
    assert result.sentiment.sentiment == SentimentType.NEUTRO
    assert result.categorization.category == "otro"


# ANL-08: unknown sentiment value falls back to neutral
def test_unknown_sentiment_falls_back_to_neutral():
    data = {"sentiment": {"type": "mixto", "score": 0.5, "reasoning": ""}}
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(json.dumps(data)))
    result = analyzer.analyze(_msg())
    assert result.sentiment.sentiment == SentimentType.NEUTRO


# ANL-09: comentario_general maps to otro (fallback of #68)
def test_comentario_general_maps_to_otro():
    data = {"categorization": {"category": "comentario_general"}}
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(json.dumps(data)))
    result = analyzer.analyze(_msg())
    assert result.categorization.category == "otro"


# ANL-10: unrecognized category maps to otro
def test_spam_maps_to_otro():
    data = {"categorization": {"category": "spam"}}
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(json.dumps(data)))
    result = analyzer.analyze(_msg())
    assert result.categorization.category == "otro"


# ANL-11: duda_tecnica is an alias of the contract's pregunta_tecnica
def test_duda_tecnica_aliases_to_pregunta_tecnica():
    data = {"categorization": {"category": "duda_tecnica"}}
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(json.dumps(data)))
    result = analyzer.analyze(_msg())
    assert result.categorization.category == "pregunta_tecnica"


# ANL-12 / ANL-13: relevance border is inclusive at 0.60
def test_relevance_border_inclusive_and_exclusive():
    # 0.60 -> worthy
    data_60 = {"relevance": {"score": 0.60, "is_marketing_worthy": False}}
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(json.dumps(data_60)))
    assert analyzer.analyze(_msg()).relevance.is_marketing_worthy is True

    # 0.59 -> not worthy
    data_59 = {"relevance": {"score": 0.59}}
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(json.dumps(data_59)))
    assert analyzer.analyze(_msg()).relevance.is_marketing_worthy is False


# ANL-15: a contradictory explicit field loses to the derived score
def test_marketing_worthy_derives_from_score():
    data = {"relevance": {"score": 0.3, "is_marketing_worthy": True}}
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(json.dumps(data)))
    assert analyzer.analyze(_msg()).relevance.is_marketing_worthy is False


# ANL-14: out-of-range scores are clamped to [0, 1]
def test_clamps_out_of_range_scores():
    data = {"relevance": {"score": 1.3}, "sentiment": {"score": -0.2}}
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(json.dumps(data)))
    result = analyzer.analyze(_msg())
    assert result.relevance.score == 1.0
    assert result.sentiment.score == 0.0


# ANL-16: empty/whitespace text skips the LLM call entirely
def test_empty_text_skips_llm():
    client = FakeClient(_full_json())
    analyzer = GeminiUnifiedAnalyzer(client=client)
    result = analyzer.analyze(_msg(texto="   "))
    assert client.calls == 0
    assert result.categorization.category == "otro"


# Review (Emmanuel, blocker 1): valid JSON with unexpected types -> default
def test_unexpected_types_return_default():
    data = {"sentiment": "positivo"}  # a string where an object is expected
    analyzer = GeminiUnifiedAnalyzer(client=FakeClient(json.dumps(data)))
    result = analyzer.analyze(_msg())
    assert result.sentiment.sentiment == SentimentType.NEUTRO
    assert result.categorization.category == "otro"


# ANL-17: a batch isolates per-message failures (the pipeline iterates)
def test_batch_isolates_failures():
    client = SequenceClient([_full_json(), LLMError("boom"), _full_json()])
    analyzer = GeminiUnifiedAnalyzer(client=client)
    messages = [_msg(texto="a"), _msg(texto="b"), _msg(texto="c")]
    results = analyzer.analyze_batch(messages)

    assert len(results) == 3
    assert results[0].categorization.category == "testimonio"
    assert results[1].categorization.category == "otro"      # falló -> default
    assert results[2].categorization.category == "testimonio"
