"""Tests del bot interactivo de Telegram (Escalón 4 de ingesta, stretch S5).

Cubren `build_reply` (determinista offline con backend rule_based), el avance
del offset y el reintento con backoff ante errores de red. Se mockean
`requests.get`/`requests.post` con monkeypatch (sin deps nuevas como
requests-mock). El cwd se aísla en tmp_path para que el snapshot local de
almacenamiento no caiga en el repo (mismo patrón que tests/test_webhook.py).
"""
import pytest
import requests

from src.ingest.bot import (
    EMPTY_REPLY,
    WELCOME_TEXT,
    build_reply,
    next_offset,
    run_bot,
    send_message,
)

_OCI_REQUIRED_ENV = (
    "OCI_USER_ID",
    "OCI_PRIVATE_KEY_PATH",
    "OCI_FINGERPRINT",
    "OCI_TENANCY_ID",
    "OCI_REGION",
)

# Mensajes elegidos para que el backend rule_based arme cada camino:
# - positivo -> testimonio -> PUBLICAR (post de LinkedIn).
# - pregunta -> pregunta_tecnica -> CREAR_FAQ.
# - neutro -> discusion -> DESCARTAR.
MENSAJE_POSITIVO = "Logré mi primer empleo como desarrolladora, gracias a la comunidad!"
MENSAJE_PREGUNTA = "¿Cómo hago para configurar el backend?"
MENSAJE_NEUTRO = "El pipeline offline corrió perfecto en mi máquina."


@pytest.fixture(autouse=True)
def bot_env(monkeypatch, tmp_path):
    """Backend rule_based, sin credenciales OCI y cwd aislado en tmp_path."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    for var in _OCI_REQUIRED_ENV:
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# build_reply (pura, offline)
# ---------------------------------------------------------------------------


def test_reply_positivo_menciona_sentimiento_y_publicar():
    reply = build_reply(MENSAJE_POSITIVO)
    assert "Sentimiento: Positivo" in reply
    assert "PUBLICAR" in reply


def test_reply_pregunta_tecnica_menciona_faq():
    reply = build_reply(MENSAJE_PREGUNTA)
    assert "Sentimiento: Neutro" in reply
    assert "CREAR_FAQ" in reply
    # El FAQThemeGenerator fija el status del activo.
    assert "generado" in reply


def test_reply_neutro_devuelve_descartar():
    reply = build_reply(MENSAJE_NEUTRO)
    assert "DESCARTAR" in reply


def test_reply_start_y_help_devuelven_bienvenida():
    assert build_reply("/start") == WELCOME_TEXT
    assert build_reply("/help") == WELCOME_TEXT
    # Sufijo @botname y mayúsculas: sigue siendo el mismo comando.
    assert build_reply("/START@CommunityLabBot") == WELCOME_TEXT


def test_reply_comando_desconocido_se_ignora():
    assert build_reply("/cualquier-cosa") == ""
    assert build_reply("/foo bar") == ""


def test_reply_vacio_o_solo_espacios_devuelve_texto_amable():
    assert build_reply("") == EMPTY_REPLY
    assert build_reply("   ") == EMPTY_REPLY


def test_reply_falla_del_pipeline_devuelve_texto_amable(monkeypatch):
    def _explotar(_batch):
        raise RuntimeError("boom interno que no debe salir")

    monkeypatch.setattr("src.ingest.bot._run_with_batch", _explotar)
    reply = build_reply(MENSAJE_POSITIVO)
    assert "no pude analizar" in reply
    assert "boom" not in reply
    assert "Traceback" not in reply


# ---------------------------------------------------------------------------
# Manejo del offset
# ---------------------------------------------------------------------------


def test_next_offset_avanza_sobre_todos_los_updates():
    updates = [
        {"update_id": 1001, "message": {"chat": {"id": 1}}},
        {"update_id": 1002, "message": {"chat": {"id": 2}}},  # otro chat
        {"update_id": 1004, "message": {"chat": {"id": 1}}},
    ]
    # Aunque se filtren por chat, el offset avanza sobre el máximo visto + 1.
    assert next_offset(updates) == 1005


def test_next_offset_nunca_retrocede():
    updates = [{"update_id": 1001, "message": {"chat": {"id": 1}}}]
    assert next_offset(updates, current=2000) == 2000


def test_next_offset_sin_updates_conserva_el_actual():
    assert next_offset([], None) is None
    assert next_offset([], current=500) == 500
    assert next_offset([{"message": {}}], None) is None  # sin update_id


# ---------------------------------------------------------------------------
# Bucle con error de red y backoff
# ---------------------------------------------------------------------------


class _FakeRespuesta:
    """Mínima interfaz de requests usada por fetch_updates/send_message."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _updates_payload():
    return {
        "ok": True,
        "result": [
            {
                "update_id": 7,
                "message": {
                    "message_id": 10,
                    "from": {"id": 42, "first_name": "Ana"},
                    "chat": {"id": 555, "type": "private"},
                    "date": 1735689600,
                    "text": MENSAJE_POSITIVO,
                },
            }
        ],
    }


def test_run_bot_reintenta_con_backoff_y_procesa_el_update(monkeypatch):
    """La primera llamada HTTP falla, la segunda entrega el update pendiente."""
    llamadas_get = {"n": 0}
    enviados = []

    def fake_get(url, params=None, timeout=None):
        llamadas_get["n"] += 1
        if llamadas_get["n"] == 1:
            raise requests.ConnectionError("sin red")
        return _FakeRespuesta(_updates_payload())

    def fake_post(url, json=None, timeout=None):
        enviados.append(json)
        return _FakeRespuesta({"ok": True, "result": {"message_id": 11}})

    monkeypatch.setattr("src.ingest.telegram.requests.get", fake_get)
    monkeypatch.setattr("src.ingest.bot.requests.post", fake_post)

    esperas = []
    monkeypatch.setattr("src.ingest.bot._sleep", lambda segundos: esperas.append(segundos))

    codigo = run_bot("token-de-prueba", max_cycles=2)

    assert codigo == 0
    assert llamadas_get["n"] == 2  # falló una vez y reintentó
    assert esperas == [1]  # el backoff arranca en 1s
    assert len(enviados) == 1
    assert enviados[0]["chat_id"] == 555
    assert "PUBLICAR" in enviados[0]["text"]


def test_run_bot_ignora_comandos_desconocidos(monkeypatch):
    """Un /comando no reconocido no dispara ninguna respuesta."""
    enviados = []

    def fake_get(url, params=None, timeout=None):
        payload = _updates_payload()
        payload["result"][0]["message"]["text"] = "/desconocido"
        return _FakeRespuesta(payload)

    monkeypatch.setattr("src.ingest.telegram.requests.get", fake_get)

    def fake_post(url, json=None, timeout=None):
        enviados.append(json)
        return _FakeRespuesta({"ok": True})

    monkeypatch.setattr("src.ingest.bot.requests.post", fake_post)
    monkeypatch.setattr("src.ingest.bot._sleep", lambda _s: None)

    run_bot("token-de-prueba", max_cycles=1)

    assert enviados == []


# ---------------------------------------------------------------------------
# Seguridad del token
# ---------------------------------------------------------------------------


def test_send_message_error_de_red_no_filtra_el_token(monkeypatch):
    def fake_post(url, json=None, timeout=None):
        # La excepción real incluiría la URL con el token.
        raise requests.ConnectionError(f"no conecta a {url}")

    monkeypatch.setattr("src.ingest.bot.requests.post", fake_post)

    with pytest.raises(RuntimeError) as exc:
        send_message("SUPER-SECRET-TOKEN", 555, "hola")
    mensaje = str(exc.value)
    assert "SUPER-SECRET-TOKEN" not in mensaje
    assert "Error de red" in mensaje
