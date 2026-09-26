"""Tests for the input normalizer."""
from src.domain.models import InputMessage
from src.ingest.normalizer import InputNormalizer


def test_normalize_contract_fields():
    raw = {
        "autor": "alice",
        "canal": "#testimonios",
        "tipo": "testimonio",
        "texto": "Excelente sesion",
    }
    msg = InputNormalizer().normalize("mastodon", raw)
    assert isinstance(msg, InputMessage)
    assert msg.autor == "alice"
    assert msg.canal == "#testimonios"
    assert msg.tipo == "testimonio"
    assert msg.texto == "Excelente sesion"


def test_normalize_accepts_english_names():
    raw = {"author": "bob", "content": "python question", "channel": "#dudas"}
    msg = InputNormalizer().normalize("discord", raw)
    assert msg.autor == "bob"
    assert msg.texto == "python question"
    assert msg.canal == "#dudas"
    assert msg.tipo == "otro"  # no explicit tipo


def test_normalize_explicit_tipo_wins():
    raw = {"autor": "c", "texto": "t", "tipo": "pregunta_tecnica"}
    msg = InputNormalizer().normalize("mastodon", raw, tipo="testimonio")
    assert msg.tipo == "testimonio"


def test_normalize_tipo_with_spaces():
    """Raw values with spaces are normalized to underscores."""
    raw = {"autor": "e", "texto": "t", "tipo": "pregunta tecnica"}
    msg = InputNormalizer().normalize("mastodon", raw)
    assert msg.tipo == "pregunta_tecnica"


def test_normalize_tipo_case_and_spaces():
    raw = {"autor": "f", "texto": "t", "tipo": "Comentario General"}
    msg = InputNormalizer().normalize("mastodon", raw)
    assert msg.tipo == "comentario_general"


def test_normalize_preserves_url_in_metadata():
    raw = {
        "autor": "d",
        "texto": "t",
        "tipo": "testimonio",
        "url": "https://mastodon.social/example",
    }
    msg = InputNormalizer().normalize("mastodon", raw)
    assert msg.metadata.get("url") == "https://mastodon.social/example"
