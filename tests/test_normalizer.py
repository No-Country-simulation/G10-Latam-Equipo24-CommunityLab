"""Tests for input normalizer."""
from src.domain.models import InputMessage
from src.ingest.normalizer import InputNormalizer


def test_normalize_campos_del_contrato():
    raw = {
        "autor": "alice",
        "canal": "#testimonios",
        "tipo": "testimonio",
        "texto": "Excelente sesión",
    }
    msg = InputNormalizer().normalize("mastodon", raw)
    assert isinstance(msg, InputMessage)
    assert msg.autor == "alice"
    assert msg.canal == "#testimonios"
    assert msg.tipo == "testimonio"
    assert msg.texto == "Excelente sesión"


def test_normalize_acepta_nombres_en_ingles():
    raw = {"author": "bob", "content": "duda de python", "channel": "#dudas"}
    msg = InputNormalizer().normalize("discord", raw)
    assert msg.autor == "bob"
    assert msg.texto == "duda de python"
    assert msg.canal == "#dudas"
    assert msg.tipo == "otro"  # sin tipo explícito


def test_normalize_tipo_explicito_gana():
    raw = {"autor": "c", "texto": "t", "tipo": "pregunta_tecnica"}
    msg = InputNormalizer().normalize("mastodon", raw, tipo="testimonio")
    assert msg.tipo == "testimonio"


def test_normalize_preserva_url_en_metadata():
    raw = {
        "autor": "d",
        "texto": "t",
        "tipo": "testimonio",
        "url": "https://mastodon.social/example",
    }
    msg = InputNormalizer().normalize("mastodon", raw)
    assert msg.metadata.get("url") == "https://mastodon.social/example"
