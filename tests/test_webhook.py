"""Tests de integración del webhook HTTP de ingesta (Escalón 3).

Levanta el server real (ThreadingHTTPServer con puerto efímero) en un hilo y
consume `POST /ingest` y `GET /health` con `requests`. Se fuerza el backend
rule_based para que el resultado sea determinista y sin red; el cwd se aísla
en tmp_path para que el snapshot local de almacenamiento no caiga en el repo
(mismo patrón que tests/test_pipeline.py).
"""
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from src.ingest.webhook import IngestHandler

_OCI_REQUIRED_ENV = (
    "OCI_USER_ID",
    "OCI_PRIVATE_KEY_PATH",
    "OCI_FINGERPRINT",
    "OCI_TENANCY_ID",
    "OCI_REGION",
)

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


@pytest.fixture(autouse=True)
def webhook_env(monkeypatch, tmp_path):
    """Backend rule_based, sin credenciales OCI y cwd aislado en tmp_path."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    for var in _OCI_REQUIRED_ENV:
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
