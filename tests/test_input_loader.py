"""Tests for JSON input loader."""
import json

import pytest

from src.domain.models import InputBatch, InputMessage
from src.ingest.input_loader import JSONInputLoader


def test_load_valid_json(tmp_path):
    sample = {
        "origen_comunidad": "Discord_Grupo_ONE_G10",
        "periodo_referencia": "Semana_04",
        "interacciones": [
            {
                "autor": "Mariana Souza",
                "canal": "#logros-y-empleos",
                "tipo": "testimonio",
                "texto": "Conseguí mi primer trabajo como dev.",
            }
        ],
    }
    file = tmp_path / "sample.json"
    file.write_text(json.dumps(sample))
    loader = JSONInputLoader()
    msgs = loader.load(str(file))
    assert len(msgs) == 1
    assert msgs[0].autor == "Mariana Souza"
    assert msgs[0].tipo == "testimonio"
    assert isinstance(msgs[0], InputMessage)


def test_load_batch_preserva_el_sobre(tmp_path):
    sample = {
        "origen_comunidad": "Mastodon_mastodon.social_python",
        "periodo_referencia": "Semana_39_2026",
        "interacciones": [
            {"autor": "a", "canal": "#c", "tipo": "testimonio", "texto": "t"}
        ],
    }
    file = tmp_path / "sample.json"
    file.write_text(json.dumps(sample))
    batch = JSONInputLoader().load_batch(str(file))
    assert isinstance(batch, InputBatch)
    assert batch.origen_comunidad == "Mastodon_mastodon.social_python"
    assert batch.periodo_referencia == "Semana_39_2026"


def test_load_tolera_interactions_ingles(tmp_path):
    """Acepta 'interactions' (inglés) como fallback, sin romper."""
    sample = {
        "origen_comunidad": "x",
        "periodo_referencia": "y",
        "interactions": [
            {"autor": "a", "canal": "#c", "tipo": "testimonio", "texto": "t"}
        ],
    }
    file = tmp_path / "sample.json"
    file.write_text(json.dumps(sample))
    msgs = JSONInputLoader().load(str(file))
    assert len(msgs) == 1


def test_load_missing_file():
    loader = JSONInputLoader()
    with pytest.raises(FileNotFoundError):
        loader.load("/nonexistent/path.json")


def test_load_invalid_json(tmp_path):
    invalid = {"origen_comunidad": "x"}  # falta "interacciones"
    file = tmp_path / "bad.json"
    file.write_text(json.dumps(invalid))
    with pytest.raises(ValueError):
        JSONInputLoader().load(str(file))
