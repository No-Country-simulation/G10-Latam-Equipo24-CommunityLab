"""Tests de la ingesta de Telegram (Escalón 2 de ingesta).

Mockean la llamada HTTP con monkeypatch sobre requests.get (sin deps nuevas)
usando una respuesta realista de getUpdates guardada en
tests/fixtures/telegram_updates.json.

Cobertura: parseo del contrato, descarte de mensajes sin texto y de comandos,
manejo de "ok": false, envelope, save_batch y merge con loader.load_batch.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests

from src.domain.models import InputBatch
from src.ingest.loader import load_batch
from src.ingest.telegram import fetch_updates, messages_to_batch, save_batch

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
UPDATES_FIXTURE = FIXTURES / "telegram_updates.json"
MUESTRA_CSV = FIXTURES / "muestra.csv"

CHAT = "-1001234567890"


def _payload() -> dict:
    """La respuesta realista de getUpdates, tal cual está en la fixture."""
    return json.loads(UPDATES_FIXTURE.read_text(encoding="utf-8"))


class _FakeRespuesta:
    """Mínima interfaz de requests que usa fetch_updates (raise_for_status/json)."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _mock_get(monkeypatch, payload: dict):
    monkeypatch.setattr(
        "src.ingest.telegram.requests.get",
        lambda *args, **kwargs: _FakeRespuesta(payload),
    )


class _FakeRespuestaHTTPError:
    """Simula una respuesta HTTP que provoca requests.HTTPError."""

    def __init__(self, codigo: int) -> None:
        self.status_code = codigo

    def raise_for_status(self) -> None:
        error = requests.HTTPError(f"HTTP {self.status_code}")
        error.response = self
        raise error

    def json(self) -> dict:
        return {
            "ok": False,
            "error_code": self.status_code,
            "description": f"Error HTTP {self.status_code}",
        }


@pytest.mark.parametrize(
    ("codigo", "tipo_error"),
    [
        (404, "permanent"),
        (409, "permanent"),
        (429, "transient"),
    ],
)

def test_fetch_updates_clasifica_errores_http(
    monkeypatch, codigo, tipo_error
):
    from src.ingest.telegram import (
    TelegramPermanentError,
    TelegramTransientError,
    fetch_updates,
    )

    respuesta = _FakeRespuestaHTTPError(codigo)
    monkeypatch.setattr(
        "src.ingest.telegram.requests.get",
        lambda *args, **kwargs: respuesta,
    )

    clase_esperada = (
        TelegramPermanentError
        if tipo_error == "permanent"
        else TelegramTransientError
    )

    with pytest.raises(clase_esperada) as exc:
        fetch_updates("token-de-prueba", CHAT)

    assert f"HTTP {codigo}" in str(exc.value)

# fetch_updates


def test_fetch_updates_filtra_por_chat(monkeypatch):
    _mock_get(monkeypatch, _payload())
    updates = fetch_updates("token-de-prueba", CHAT)
    assert len(updates) == 4
    assert all(str(u["message"]["chat"]["id"]) == CHAT for u in updates)


def test_fetch_updates_envia_offset_y_limit(monkeypatch):
    capturado = {}

    def fake_get(url, params=None, timeout=None):
        capturado["params"] = params
        return _FakeRespuesta(_payload())

    monkeypatch.setattr("src.ingest.telegram.requests.get", fake_get)
    fetch_updates("token-de-prueba", CHAT, offset=1001, limit=50)
    assert capturado["params"] == {"offset": 1001, "limit": 50}


def test_fetch_updates_sin_token_lanza_value_error():
    with pytest.raises(ValueError) as exc:
        fetch_updates("", CHAT)
    assert "token" in str(exc.value)


def test_ok_false_lanza_error_claro(monkeypatch):
    _mock_get(
        monkeypatch,
        {
            "ok": False,
            "description": "Conflict: terminated by other getUpdates request",
        },
    )
    with pytest.raises(RuntimeError) as exc:
        fetch_updates("token-de-prueba", CHAT)
    mensaje = str(exc.value)
    assert "ok=false" in mensaje
    assert "Conflict" in mensaje


def test_error_api_no_filtra_el_token(monkeypatch):
    _mock_get(monkeypatch, {"ok": False, "description": "Unauthorized"})
    with pytest.raises(RuntimeError) as exc:
        fetch_updates("SUPER-SECRET-TOKEN", CHAT)
    assert "SUPER-SECRET-TOKEN" not in str(exc.value)


# messages_to_batch


def test_messages_to_batch_parsea_campos_del_contrato():
    batch = messages_to_batch(_payload()["result"], CHAT)
    assert isinstance(batch, InputBatch)
    assert len(batch.interacciones) == 2

    primera = batch.interacciones[0]
    assert primera.autor == "Mariana Souza"
    assert primera.canal == "#telegram"
    assert primera.tipo == "otro"  # default de InputNormalizer cuando no hay tipo
    assert primera.texto.startswith("https://example.com/empleo")
    assert primera.id == "41"
    assert primera.timestamp == "2025-01-01T00:00:00Z"
    assert primera.metadata["url"] == "https://example.com/empleo"

    segunda = batch.interacciones[1]
    assert segunda.autor == "Carlos"  # sin apellido: cae al first_name
    assert segunda.id == "42"
    assert segunda.timestamp == "2025-01-01T00:01:00Z"
    assert segunda.metadata.get("url") is None


def test_descarta_mensajes_sin_texto_y_comandos():
    batch = messages_to_batch(_payload()["result"], CHAT)
    # 43 (foto sin texto) y 44 (/start) se descartan; 41 y 42 se conservan.
    assert [msg.id for msg in batch.interacciones] == ["41", "42"]


def test_envelope_por_defecto_y_override():
    batch = messages_to_batch(_payload()["result"], CHAT)
    assert batch.origen_comunidad == f"Telegram-{CHAT}"
    assert batch.periodo_referencia == datetime.now(timezone.utc).strftime(
        "telegram-%Y-%m-%d"
    )

    batch_custom = messages_to_batch(_payload()["result"], CHAT, origen="Mi_Comunidad")
    assert batch_custom.origen_comunidad == "Mi_Comunidad"


# save_batch y merge


def test_save_batch_escribe_json_valido(tmp_path):
    batch = messages_to_batch(_payload()["result"], CHAT)
    destino = tmp_path / "sub" / "telegram.json"
    out_path = save_batch(batch, destino)

    assert out_path == destino
    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert set(datos) == {"origen_comunidad", "periodo_referencia", "interacciones"}
    assert len(datos["interacciones"]) == 2
    roundtrip = InputBatch.model_validate(datos)
    assert roundtrip.origen_comunidad == f"Telegram-{CHAT}"
    assert roundtrip.interacciones[0].timestamp == "2025-01-01T00:00:00Z"


def test_batch_de_telegram_se_mergea_con_loader(tmp_path):
    batch = messages_to_batch(_payload()["result"], CHAT)
    destino = tmp_path / "telegram.json"
    save_batch(batch, destino)

    combinado = load_batch([str(destino), str(MUESTRA_CSV)])

    # 2 de Telegram + 3 del CSV, concatenadas en orden.
    assert len(combinado.interacciones) == 5
    assert combinado.interacciones[0].canal == "#telegram"
    assert "Telegram-" + CHAT in combinado.origen_comunidad
    assert "Comunidad_Tech" in combinado.origen_comunidad
    # Periodos distintos -> "combinado".
    assert combinado.periodo_referencia == "combinado"


# CLI


def test_cli_falla_sin_token():
    env = {k: v for k, v in os.environ.items() if k != "TELEGRAM_BOT_TOKEN"}
    resultado = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "ingest_telegram.py"),
            "--chat",
            CHAT,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert resultado.returncode == 1
    assert "token" in resultado.stderr
    assert CHAT not in resultado.stderr
