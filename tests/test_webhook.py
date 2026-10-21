"""Tests de integración del webhook HTTP de ingesta (Escalón 3).

Levanta el server real (ThreadingHTTPServer con puerto efímero) en un hilo y
consume `POST /ingest`, `GET /health` y `POST /telegram` con `requests`. Se fuerza el backend
rule_based para que el resultado sea determinista y sin red; el cwd se aísla
en tmp_path para que el snapshot local de almacenamiento no caiga en el repo
(mismo patrón que tests/test_pipeline.py).
"""
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from src.ingest import webhook as webhook_module
from src.ingest.bot import WELCOME_TEXT
from src.ingest.telegram import TelegramPermanentError, TelegramTransientError
from src.ingest.webhook import IngestHandler
from src.oci.storage import OCI_REQUIRED_ENV

# Header con el que Telegram firma cada entrega del webhook.
_TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
_TELEGRAM_SECRET = "secreto-de-prueba"

# InputBatch completo del contrato; el testimonio positivo con rule_based
# genera el post de LinkedIn (decisión PUBLISH + LINKEDIN).
BATCH_VALIDO = {
    "origen_comunidad": "webhook-test",
    "periodo_referencia": "Semana_05",
    "interacciones": [
        {
            "autor": "Mariana",
            "canal": "#logros-y-empleos",
            "tipo": "testimonio",
            "texto": "Logré mi primer empleo como desarrolladora!",
        },
        {
            "autor": "Leo",
            "canal": "#dudas",
            "tipo": "pregunta_tecnica",
            "texto": "¿Cómo hago para configurar el backend?",
        },
    ],
}


def update_telegram(
    update_id=100001,
    texto="Logré mi primer empleo como desarrolladora!",
    chat_id=-1001234567890,
    chat_type="supergroup",
):
    """Arma un Update realista de la Bot API (update_id + message).

    Por defecto un supergroup (como el de la comunidad); `chat_type="private"`
    simula el chat directo en el que el bot sí contesta.
    """
    return {
        "update_id": update_id,
        "message": {
            "message_id": 42,
            "date": 1730000000,
            "text": texto,
            "from": {"id": 111, "first_name": "Ana", "language_code": "es"},
            "chat": {
                "id": chat_id,
                "type": chat_type,
                "title": "Comunidad de prueba",
            },
        },
    }


def headers_telegram(secret=_TELEGRAM_SECRET):
    """Headers con el secret del webhook configurado."""
    return {_TELEGRAM_SECRET_HEADER: secret}


@pytest.fixture(autouse=True)
def webhook_env(monkeypatch, tmp_path):
    """Backend rule_based, sin credenciales OCI y cwd aislado en tmp_path."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    # El secret del webhook arranca sin configurar y el dedupe se limpia entre
    # tests para que cada caso parta de un estado conocido.
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("TELEGRAM_WEBHOOK_ORIGEN", raising=False)
    # El token del bot es opcional: sin él el webhook es ingesta pura y ningún
    # test debe intentar salir a la red para responder en el chat.
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    seen = getattr(webhook_module, "_seen_update_ids", None)
    if seen is not None:
        seen.clear()
    for var in OCI_REQUIRED_ENV:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def server():
    """Levanta el server en un hilo con puerto efímero y devuelve su base URL."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), IngestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    yield f"http://{host}:{port}"
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=5)


def test_health_ok(server):
    respuesta = requests.get(f"{server}/health", timeout=10)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_ingest_batch_valido_devuelve_resumen(server):
    respuesta = requests.post(f"{server}/ingest", json=BATCH_VALIDO, timeout=30)
    assert respuesta.status_code == 200

    body = respuesta.json()
    assert body["status"] == "exito"
    resumen = body["resumen"]
    assert resumen["total_interacciones_procesadas"] == 2
    assert resumen["sentimiento_predominante"] == "Positivo"

    # El testimonio positivo genera el post de LinkedIn; el almacenamiento
    # degrada a snapshot local porque no hay credenciales OCI.
    assert body["activos"]["post_linkedin"] is not None
    assert body["almacenamiento"]["status"] == "pendiente"


def test_ingest_array_plano_de_mensajes(server):
    # Fila cruda con alias en inglés (author/channel/content), igual que
    # acepta InputNormalizer en csv_loader.
    mensajes = [
        {
            "author": "Bob",
            "channel": "#ayuda",
            "tipo": "pregunta tecnica",
            "content": "¿Cómo hago para conectarme a la API?",
        },
        {
            "author": "Ana",
            "channel": "#logros",
            "tipo": "testimonio",
            "texto": "Conseguí mi primer empleo, estoy feliz!",
        },
    ]
    respuesta = requests.post(f"{server}/ingest", json=mensajes, timeout=30)
    assert respuesta.status_code == 200

    body = respuesta.json()
    assert body["status"] == "exito"
    assert body["resumen"]["total_interacciones_procesadas"] == 2


@pytest.mark.parametrize(
    "payload",
    [
        "esto no es json",          # body no parseable -> 400
        '{"foo": 1}',               # objeto sin 'interacciones' -> 400
    ],
)
def test_ingest_body_invalido_devuelve_400(server, payload):
    respuesta = requests.post(
        f"{server}/ingest",
        data=payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    assert respuesta.status_code == 400
    assert "error" in respuesta.json()


def test_ingest_array_con_fila_invalida_devuelve_400(server):
    respuesta = requests.post(
        f"{server}/ingest",
        json=[
            {"autor": "Ana", "tipo": "testimonio", "texto": "Hola a todos."},
            "esta fila no es un mensaje",
        ],
        timeout=10,
    )
    assert respuesta.status_code == 400
    assert "fila 2" in respuesta.json()["error"]


def test_ingest_con_metodo_equivocado_devuelve_405(server):
    respuesta = requests.get(f"{server}/ingest", timeout=10)
    assert respuesta.status_code == 405
    assert respuesta.json()["error"]


def test_ruta_desconocida_devuelve_404(server):
    respuesta_get = requests.get(f"{server}/no-existe", timeout=10)
    assert respuesta_get.status_code == 404

    respuesta_post = requests.post(f"{server}/no-existe", json={}, timeout=10)
    assert respuesta_post.status_code == 404


# --- POST /telegram (Fase 1 del webhook de Telegram) -----------------------


def test_telegram_sin_secret_configurado_devuelve_503(server):
    # Fail closed: sin TELEGRAM_WEBHOOK_SECRET el endpoint se niega.
    respuesta = requests.post(
        f"{server}/telegram",
        json=update_telegram(),
        headers=headers_telegram(),
        timeout=10,
    )
    assert respuesta.status_code == 503
    assert respuesta.json()["error"]


def test_telegram_con_secret_sin_header_devuelve_401(server, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    respuesta = requests.post(
        f"{server}/telegram", json=update_telegram(), timeout=10
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]


def test_telegram_con_header_incorrecto_devuelve_401(server, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    respuesta = requests.post(
        f"{server}/telegram",
        json=update_telegram(),
        headers=headers_telegram(secret="otro-secreto"),
        timeout=10,
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]


def test_telegram_con_secret_valido_procesa_una_interaccion(server, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    update = update_telegram(update_id=200001)

    respuesta = requests.post(
        f"{server}/telegram",
        json=update,
        headers=headers_telegram(),
        timeout=30,
    )
    assert respuesta.status_code == 200

    body = respuesta.json()
    assert body["status"] == "exito"
    assert body["ruta"] == "/telegram"
    assert body["update_id"] == 200001
    assert body["resumen"]["total_interacciones_procesadas"] == 1
    # Misma forma que /ingest: resumen, activos y almacenamiento.
    assert "resumen" in body
    assert "activos" in body
    assert "almacenamiento" in body


def test_telegram_update_duplicado_no_reprocesa(server, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)

    # Espía del pipeline: cuenta cuántas veces realmente se ejecuta.
    llamadas = []
    original = webhook_module._run_with_batch

    def espia(batch):
        llamadas.append(batch)
        return original(batch)

    monkeypatch.setattr(webhook_module, "_run_with_batch", espia)

    update = update_telegram(update_id=300001)
    primera = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert primera.status_code == 200
    assert primera.json()["resumen"]["total_interacciones_procesadas"] == 1

    segunda = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert segunda.status_code == 200
    body = segunda.json()
    assert body["status"] == "duplicado"
    assert body["update_id"] == 300001
    # El pipeline corrió una sola vez: el duplicado no se reprocesó.
    assert len(llamadas) == 1


def test_telegram_update_sin_message_se_ignora(server, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)

    llamadas = []
    monkeypatch.setattr(
        webhook_module, "_run_with_batch", lambda batch: llamadas.append(batch)
    )

    update = {
        "update_id": 400001,
        "my_chat_member": {"chat": {"id": -1001234567890}, "from": {"id": 111}},
    }
    respuesta = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=10
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ignorado"
    assert llamadas == []


def test_telegram_comando_se_ignora(server, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)

    llamadas = []
    monkeypatch.setattr(
        webhook_module, "_run_with_batch", lambda batch: llamadas.append(batch)
    )

    update = update_telegram(update_id=500001, texto="/start")
    respuesta = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=10
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ignorado"
    assert llamadas == []


def test_telegram_con_metodo_equivocado_devuelve_405(server):
    respuesta = requests.get(f"{server}/telegram", timeout=10)
    assert respuesta.status_code == 405
    assert respuesta.headers["Allow"] == "POST"
    assert respuesta.json()["error"]


def test_telegram_body_invalido_devuelve_400(server, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    headers = headers_telegram()
    headers["Content-Type"] = "application/json"
    respuesta = requests.post(
        f"{server}/telegram",
        data="esto no es json",
        headers=headers,
        timeout=10,
    )
    assert respuesta.status_code == 400
    assert "error" in respuesta.json()


# --- Respuesta al chat (Fase 2: el bot contesta por webhook) ----------------


def _espia_envios(monkeypatch, fallo=None):
    """Reemplaza send_message del webhook y devuelve la lista de envíos.

    Con `fallo` (una excepción) el envío lanza en vez de registrar, para
    simular caídas de la Bot API.
    """
    envios = []

    def espia(token, chat_id, text):
        if fallo is not None:
            raise fallo
        envios.append({"token": token, "chat_id": chat_id, "text": text})

    monkeypatch.setattr(webhook_module, "send_message", espia)
    return envios


def test_telegram_responde_al_chat_en_privado(server, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-de-prueba")
    envios = _espia_envios(monkeypatch)

    update = update_telegram(update_id=600001, chat_id=7191785744, chat_type="private")
    respuesta = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert respuesta.status_code == 200

    body = respuesta.json()
    assert body["status"] == "exito"
    assert body["respuesta"] == "enviada"

    # El análisis llega al chat con el mismo texto que el bot de polling.
    assert len(envios) == 1
    assert envios[0]["chat_id"] == 7191785744
    assert envios[0]["token"] == "token-de-prueba"
    assert envios[0]["text"].startswith("Análisis de tu mensaje:")


def test_telegram_en_grupo_no_responde(server, monkeypatch):
    """El bot escucha en el grupo (se procesa) pero sólo contesta en privado."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-de-prueba")
    envios = _espia_envios(monkeypatch)

    llamadas = []
    original = webhook_module._run_with_batch
    monkeypatch.setattr(
        webhook_module, "_run_with_batch", lambda b: llamadas.append(b) or original(b)
    )

    update = update_telegram(update_id=600002)  # supergroup, como el default
    respuesta = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "exito"
    assert respuesta.json()["respuesta"] == "omitida"
    assert envios == []
    assert len(llamadas) == 1


def test_telegram_sin_token_es_ingesta_pura(server, monkeypatch):
    """Sin TELEGRAM_BOT_TOKEN el endpoint sigue funcionando, sólo no responde."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    envios = _espia_envios(monkeypatch)

    update = update_telegram(update_id=600003, chat_id=7191785744, chat_type="private")
    respuesta = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert respuesta.status_code == 200

    body = respuesta.json()
    assert body["status"] == "exito"
    assert body["respuesta"] == "omitida"
    assert envios == []


def test_telegram_comando_start_recibe_la_bienvenida(server, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-de-prueba")
    envios = _espia_envios(monkeypatch)

    llamadas = []
    monkeypatch.setattr(
        webhook_module, "_run_with_batch", lambda batch: llamadas.append(batch)
    )

    update = update_telegram(
        update_id=600004, texto="/start", chat_id=7191785744, chat_type="private"
    )
    respuesta = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=10
    )
    assert respuesta.status_code == 200
    # Sin pipeline (el comando no es contenido), pero con la bienvenida.
    assert respuesta.json()["status"] == "ignorado"
    assert respuesta.json()["respuesta"] == "enviada"
    assert llamadas == []
    assert [envio["text"] for envio in envios] == [WELCOME_TEXT]


def test_telegram_reintento_de_start_no_afirma_que_corrio_el_pipeline(
    server, monkeypatch
):
    """Un reintento de /start tras una falla transitoria NO debe decir que el
    pipeline corrió: en un comando el pipeline nunca se ejecutó."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-de-prueba")

    llamadas = []
    monkeypatch.setattr(
        webhook_module, "_run_with_batch", lambda batch: llamadas.append(batch)
    )

    envios = []
    fallos = {"restantes": 1}

    def espia(token, chat_id, text):
        if fallos["restantes"] > 0:
            fallos["restantes"] -= 1
            raise TelegramTransientError("red caída")
        envios.append({"token": token, "chat_id": chat_id, "text": text})

    monkeypatch.setattr(webhook_module, "send_message", espia)

    update = update_telegram(
        update_id=600006, texto="/start", chat_id=7191785744, chat_type="private"
    )
    primera = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert primera.status_code == 500  # Telegram debe reentregar

    segunda = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert segunda.status_code == 200
    body = segunda.json()
    # El pipeline nunca corrió: el reintento conserva "ignorado" y no afirma
    # lo contrario en la nota.
    assert body["status"] == "ignorado"
    assert body["respuesta"] == "enviada"
    assert body.get("nota") != (
        "pipeline ejecutado en una entrega anterior de Telegram"
    )
    assert llamadas == []
    assert [envio["text"] for envio in envios] == [WELCOME_TEXT]

    # Una tercera entrega ya se corta como duplicado.
    tercera = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=10
    )
    assert tercera.status_code == 200
    assert tercera.json()["status"] == "duplicado"


def test_telegram_reintento_no_reprocesa_pero_reenvia_la_respuesta(
    server, monkeypatch
):
    """Si sendMessage falla de forma transitoria, el reintento de Telegram no
    vuelve a correr el pipeline: sólo reenvía la respuesta pendiente."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-de-prueba")

    llamadas = []
    original = webhook_module._run_with_batch
    monkeypatch.setattr(
        webhook_module, "_run_with_batch", lambda b: llamadas.append(b) or original(b)
    )
    _espia_envios(monkeypatch, fallo=TelegramTransientError("red caída"))

    update = update_telegram(update_id=600005, chat_id=7191785744, chat_type="private")
    primera = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert primera.status_code == 500  # Telegram debe reentregar
    assert len(llamadas) == 1

    envios = _espia_envios(monkeypatch)
    segunda = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert segunda.status_code == 200
    body = segunda.json()
    # El pipeline NO corrió de nuevo y el reintento refleja su status real.
    assert body["status"] == "exito"
    assert body["nota"] == "pipeline ejecutado en una entrega anterior de Telegram"
    assert body["respuesta"] == "enviada"
    assert len(llamadas) == 1
    assert len(envios) == 1
    assert envios[0]["text"].startswith("Análisis de tu mensaje:")

    # Una tercera entrega del mismo update ya se corta como duplicado.
    tercera = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=10
    )
    assert tercera.status_code == 200
    assert tercera.json()["status"] == "duplicado"
    assert len(llamadas) == 1
    assert len(envios) == 1


def test_telegram_error_permanente_no_provoca_reintentos(server, monkeypatch):
    """Un error permanente de la Bot API responde 200: pedirle a Telegram que
    reintente no arreglaría nada y sólo generaría tormenta de reintentos."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", _TELEGRAM_SECRET)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-de-prueba")
    _espia_envios(monkeypatch, fallo=TelegramPermanentError("chat inexistente"))

    update = update_telegram(update_id=600006, chat_id=7191785744, chat_type="private")
    respuesta = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=30
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["respuesta"] == "fallida"

    segunda = requests.post(
        f"{server}/telegram", json=update, headers=headers_telegram(), timeout=10
    )
    assert segunda.json()["status"] == "duplicado"
