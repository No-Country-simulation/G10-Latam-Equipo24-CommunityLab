"""Webhook HTTP de ingesta en tiempo real (Escalón 3).

Servidor HTTP mínimo con SOLO la librería estándar
(`http.server.ThreadingHTTPServer` + `BaseHTTPRequestHandler`) que recibe un
lote de interacciones en memoria por `POST /ingest`, corre el pipeline
(src.pipeline._run_with_batch) y devuelve el resumen del contrato.

Dos rutas:
    - `GET  /health` -> 200 {"status": "ok"}.
    - `POST /ingest` -> 200 con {status, resumen, activos, almacenamiento}.

Cualquier otra ruta o método responde 404/405. El backend LLM lo decide
`COMMUNITYLAB_LLM_BACKEND` (por defecto rule_based); el CLI de demo
(scripts/run_webhook.py) permite sobreescribirlo.

Nota de convergencia: cuando se implementen la HU-S4-006 (API endpoint) y la
HU-S5-007 (webhooks), este server local converge con ellas; el objetivo de
este escalón es demostrar la ingesta en tiempo real sin dependencias nuevas.
"""

import json
import logging
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from src.domain.models import InputBatch
from src.ingest.normalizer import InputNormalizer
from src.pipeline import _run_with_batch

logger = logging.getLogger(__name__)

# Prefijo del envelope default para el array plano: "webhook-<fecha>".
_ENVELOPE_PREFIX = "webhook"


class BodyError(ValueError):
    """Body inválido: el handler responde 400 con este mensaje."""


def parse_body(payload: Any) -> InputBatch:
    """Convierte el body JSON en un InputBatch listo para el pipeline.

    Acepta dos formatos:
    - Objeto con `interacciones`: InputBatch completo, validado con pydantic.
      Si no valida -> BodyError (400).
    - Array plano de mensajes crudos: cada fila se normaliza con
      InputNormalizer (mismas reglas que csv_loader) y se envuelve en el
      envelope default `webhook-<fecha>`. Una fila que no sea un objeto JSON
      -> BodyError (400).
    """
    if isinstance(payload, dict):
        if "interacciones" not in payload:
            raise BodyError(
                "Body inválido: falta la clave 'interacciones'. Enviá un "
                "InputBatch completo o un array plano de mensajes."
            )
        try:
            return InputBatch.model_validate(payload)
        except ValidationError as exc:
            raise BodyError(_describe_validation_error(exc)) from exc

    if isinstance(payload, list):
        return _batch_from_flat_list(payload)

    raise BodyError(
        "Body inválido: se esperaba un objeto JSON con 'interacciones' "
        "o un array plano de mensajes."
    )


def _describe_validation_error(exc: ValidationError) -> str:
    """Primer error de pydantic en forma legible: `interacciones.0.texto: ...`."""
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first.get("loc", ()))
    detalle = first.get("msg", "dato inválido")
    return f"Batch inválido: {loc}: {detalle}"


def _batch_from_flat_list(rows: List[Any]) -> InputBatch:
    """Array plano -> InputBatch con el envelope `webhook-<fecha>`.

    Normaliza cada fila con InputNormalizer (acepta autor/author,
    canal/channel, texto/content, tipo, id, timestamp/fecha y url).
    """
    normalizer = InputNormalizer()
    envelope = datetime.now(timezone.utc).strftime("webhook-%Y-%m-%d")

    interacciones = []
    for indice, fila in enumerate(rows, start=1):
        if not isinstance(fila, dict):
            raise BodyError(
                f"Body inválido: la fila {indice} del array no es un mensaje "
                "válido (se esperaba un objeto JSON con autor/canal/tipo/texto)."
            )
        interacciones.append(normalizer.normalize(_ENVELOPE_PREFIX, fila))

    return InputBatch(
        origen_comunidad=envelope,
        periodo_referencia=envelope,
        interacciones=interacciones,
    )


def resolve_backend(name: Optional[str]) -> str:
    """Resuelve el backend: argumento explícito > env > rule_based."""
    if name and name != "auto":
        return name
    return os.getenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")


def apply_backend(name: Optional[str] = None) -> str:
    """Aplica el backend elegido a COMMUNITYLAB_LLM_BACKEND y lo devuelve.

    `COMMUNITYLAB_LLM_BACKEND` es la fuente de verdad que lee get_llm_client();
    este helper solo la setea desde el parámetro del server/CLI.
    """
    backend = resolve_backend(name)
    os.environ["COMMUNITYLAB_LLM_BACKEND"] = backend
    return backend


def make_server(
    host: str, port: int, backend: Optional[str] = None
) -> ThreadingHTTPServer:
    """Crea el server HTTP (un hilo por request) y aplica el backend LLM.

    Con `port=0` el sistema operativo elige un puerto efímero (útil en tests).
    """
    apply_backend(backend)
    return ThreadingHTTPServer((host, port), IngestHandler)


class IngestHandler(BaseHTTPRequestHandler):
    """Handler de `/ingest` y `/health` para el pipeline en tiempo real."""

    server_version = "CommunityLabWebhook/0.1"

    # --- Despacho por ruta y método -------------------------------------

    def _route(self) -> None:
        """Enruta la request; cualquier otra ruta/método responde 404/405."""
        path = self.path.split("?", 1)[0]
        if path == "/health":
            if self.command == "GET":
                self._health()
            else:
                self._send_error(405, "Método no permitido en /health; usá GET")
            return
        if path == "/ingest":
            if self.command == "POST":
                self._ingest()
            else:
                self._send_error(405, "Método no permitido en /ingest; usá POST")
            return
        self._send_error(404, f"Ruta no encontrada: {path}")

    # Todo método HTTP conocido cae en el mismo despacho. Los no declarados
    # (TRACE, CONNECT, ...) se resuelven con __getattr__, así ninguna ruta ni
    # método queda sin respuesta 404/405.
    do_GET = do_POST = do_PUT = do_DELETE = _route
    do_PATCH = do_OPTIONS = do_HEAD = _route

    def __getattr__(self, name: str) -> Any:
        if name.startswith("do_"):
            return self._route
        raise AttributeError(name)

    # --- Endpoints ------------------------------------------------------

    def _health(self) -> None:
        """GET /health: chequeo simple de vida del server."""
        self._send_json(200, {"status": "ok"})

    def _ingest(self) -> None:
        """POST /ingest: parsea el body, corre el pipeline y devuelve el resumen."""
        raw = self._read_body()
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_error(400, "Body JSON inválido")
            return

        try:
            batch = parse_body(payload)
        except BodyError as exc:
            self._send_error(400, str(exc))
            return

        try:
            result = _run_with_batch(batch)
        except Exception as exc:  # el pipeline no debe filtrar el input crudo
            logger.exception("Error interno del pipeline en /ingest: %s", exc)
            self._send_error(500, "Error interno del pipeline")
            return

        # Solo se loguea el resumen del resultado, nunca el body completo.
        resumen = result.resumen_comunidad
        logger.info(
            "Webhook /ingest procesado: status=%s, interacciones=%d",
            result.status,
            resumen.total_interacciones_procesadas,
        )

        self._send_json(
            200,
            {
                "status": result.status,
                "resumen": resumen.model_dump(mode="json"),
                "activos": result.activos_distribucion_generados.model_dump(
                    mode="json"
                ),
                "almacenamiento": result.almacenamiento_oci.model_dump(mode="json"),
            },
        )

    # --- Utilidades de request/response ---------------------------------

    def _read_body(self) -> bytes:
        """Lee exactamente el Content-Length declarado (0 si falta o es inválido)."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        """Escribe una respuesta JSON con Content-Length y, si va, Allow."""
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if status == 405:
            allow = "GET" if self.path.split("?", 1)[0] == "/health" else "POST"
            self.send_header("Allow", allow)
        self.end_headers()
        self.wfile.write(payload)

    def _send_error(self, status: int, message: str) -> None:
        """Error JSON uniforme: {"error": "<mensaje>"}."""
        self._send_json(status, {"error": message})
