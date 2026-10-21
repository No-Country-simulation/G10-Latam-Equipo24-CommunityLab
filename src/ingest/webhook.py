"""Webhook HTTP de ingesta en tiempo real (Escalón 3).

Servidor HTTP mínimo con SOLO la librería estándar
(`http.server.ThreadingHTTPServer` + `BaseHTTPRequestHandler`) que recibe un
lote de interacciones en memoria por `POST /ingest`, corre el pipeline
(src.pipeline._run_with_batch) y devuelve el resumen del contrato.

Tres rutas:
    - `GET  /health`   -> 200 {"status": "ok"}.
    - `POST /ingest`   -> 200 con {status, resumen, activos, almacenamiento}.
    - `POST /telegram` -> 200 con el resumen del pipeline: recibe un update de
      la Bot API, valida el secret del header, deduplica por update_id y, si
      hay TELEGRAM_BOT_TOKEN configurado, le devuelve el análisis al chat por
      sendMessage (la misma experiencia que el bot en polling).

Cualquier otra ruta o método responde 404/405. El backend LLM lo decide
`COMMUNITYLAB_LLM_BACKEND` (por defecto rule_based); el CLI de demo
(scripts/run_webhook.py) permite sobreescribirlo.

Nota de convergencia: cuando se implementen la HU-S4-006 (API endpoint) y la
HU-S5-007 (webhooks), este server local converge con ellas; el objetivo de
este escalón es demostrar la ingesta en tiempo real sin dependencias nuevas.
"""

import hmac
import json
import logging
import os
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from src.domain.models import InputBatch, OutputBatch
from src.ingest.bot import WELCOME_TEXT, comando_de_texto, format_reply, send_message
from src.ingest.normalizer import InputNormalizer
from src.ingest.runtime import apply_backend
from src.ingest.telegram import (
    TelegramAuthError,
    TelegramPermanentError,
    TelegramTransientError,
    messages_to_batch,
)
from src.pipeline import _run_with_batch

logger = logging.getLogger(__name__)

# Prefijo del envelope default para el array plano: "webhook-<fecha>".
_ENVELOPE_PREFIX = "webhook"

# Header con el que Telegram firma cada entrega (setWebhook: secret_token).
_TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"

# Cantidad máxima de update_id memorizados para deduplicar (FIFO).
_DEDUPE_LIMIT = 1000

# Método permitido por ruta, para el header Allow de las respuestas 405.
_ALLOWED_METHODS = {
    "/health": "GET",
    "/ingest": "POST",
    "/telegram": "POST",
}

# Estado de un update_id memorizado: el pipeline ya terminó (_ESTADO_PROCESADO)
# o terminó y además la respuesta al chat salió / no aplica (_ESTADO_RESPONDIDO).
# Dos marcas para que un reintento de Telegram no vuelva a correr el pipeline
# (duplicaría activos) pero sí complete la respuesta pendiente, que queda
# guardada en el registro.
_ESTADO_PROCESADO = "procesado"
_ESTADO_RESPONDIDO = "respondido"

# Estado de la respuesta al chat devuelto por _responder_chat. Se usa una
# constante propia en lugar de mezclar None con strings: "reintentar" es un
# estado más, no la ausencia de valor.
RESPUESTA_ENVIADA = "enviada"
RESPUESTA_OMITIDA = "omitida"
RESPUESTA_FALLIDA = "fallida"
RESPUESTA_REINTENTAR = "reintentar"

# update_id ya vistos: {"estado": _ESTADO_*, "texto": respuesta pendiente,
# "status": status terminal del update ("exito" o "ignorado")}.
# Acotado a _DEDUPE_LIMIT (el más viejo se descarta) y protegido por
# _dedupe_lock porque el server usa un hilo por request. Vive en memoria: un
# reinicio del server lo vacía y Telegram reentregaría ese update (mismo
# límite que el dedupe de la fase 1).
_seen_update_ids: "OrderedDict[Any, Dict[str, Any]]" = OrderedDict()
_dedupe_lock = threading.Lock()


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


def _webhook_secret() -> str:
    """Lee TELEGRAM_WEBHOOK_SECRET en el momento del request.

    Se lee acá (y no al arrancar el server) para que los tests puedan setearla
    con monkeypatch y para que rotar el secret no requiera reiniciar. Devuelve
    cadena vacía si no está configurada, lo que activa el rechazo 503.
    """
    return os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()


def _registro_update(update_id: Any) -> Optional[Dict[str, Any]]:
    """Registro del update_id ({estado, texto}), o None si nunca lo vimos."""
    with _dedupe_lock:
        registro = _seen_update_ids.get(update_id)
        return dict(registro) if registro is not None else None


def _remember_update(
    update_id: Any,
    estado: str,
    texto: Optional[str] = None,
    status: Optional[str] = None,
) -> None:
    """Memoriza el estado, la respuesta pendiente y el status de un update_id.

    FIFO con tope _DEDUPE_LIMIT, el más viejo se descarta. `status` guarda el
    status terminal del update ("exito" si corrió el pipeline, "ignorado" si no
    tenía contenido) para que un reintento de Telegram responda lo mismo sin
    afirmar que el pipeline corrió cuando en realidad no lo hizo.
    """
    with _dedupe_lock:
        _seen_update_ids[update_id] = {
            "estado": estado,
            "texto": texto,
            "status": status,
        }
        _seen_update_ids.move_to_end(update_id)
        while len(_seen_update_ids) > _DEDUPE_LIMIT:
            _seen_update_ids.popitem(last=False)


def _chat_de_update(update: Dict[str, Any]) -> str:
    """Deriva el chat del update: message.chat.id, si no el title del chat."""
    mensaje = update.get("message")
    chat = mensaje.get("chat") if isinstance(mensaje, dict) else None
    if isinstance(chat, dict):
        if chat.get("id") is not None:
            return str(chat["id"])
        if chat.get("title"):
            return chat["title"]
    return "desconocido"


def _chat_id_de_update(update: Dict[str, Any]) -> Optional[int]:
    """chat.id del update para sendMessage; None si el update no lo trae.

    Misma regla que el polling del bot: el bot escucha en cualquier chat pero
    sólo contesta en privado, así que un chat de grupo devuelve None.
    """
    mensaje = update.get("message")
    chat = mensaje.get("chat") if isinstance(mensaje, dict) else None
    if not isinstance(chat, dict) or chat.get("id") is None:
        return None
    if chat.get("type") is not None and chat.get("type") != "private":
        return None
    return chat["id"]


def _texto_de_respuesta(
    update: Dict[str, Any], result: Optional[OutputBatch]
) -> Optional[str]:
    """Texto a responder en el chat, o None si no corresponde responder.

    Reutiliza el análisis que este mismo request ya corrió (`result`) en vez de
    volver a pasarlo por el pipeline: `bot.build_reply` hace eso y duplicaría
    los activos. Los comandos se tratan igual que en el polling: `/start` y
    `/help` reciben la bienvenida, el resto no recibe respuesta.
    """
    mensaje = update.get("message")
    texto = mensaje.get("text") if isinstance(mensaje, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        return None

    comando = comando_de_texto(texto)
    if comando is not None:
        return WELCOME_TEXT if comando in ("/start", "/help") else None

    return format_reply(result) if result is not None else None


def _responder_chat(update: Dict[str, Any], texto: str) -> str:
    """Estado de la respuesta al chat (ver las constantes RESPUESTA_*).

    Devuelve RESPUESTA_ENVIADA, RESPUESTA_OMITIDA (no hay token, no hay chat o
    chat de grupo), RESPUESTA_FALLIDA (error permanente de la Bot API, al que
    los reintentos de Telegram no le agregan nada) o RESPUESTA_REINTENTAR
    (error transitorio: el caller responde 500 para que Telegram reentregue).
    Sin `TELEGRAM_BOT_TOKEN` el webhook sigue siendo ingesta pura: el mensaje
    se procesa y no se responde, con un warning en el log para que no pase
    inadvertido.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.warning(
            "TELEGRAM_BOT_TOKEN sin configurar: el mensaje se procesó, "
            "pero no se respondió en el chat."
        )
        return RESPUESTA_OMITIDA

    chat_id = _chat_id_de_update(update)
    if chat_id is None:
        # Sin chat identificable o chat de grupo: no hay a quién responderle.
        return RESPUESTA_OMITIDA

    try:
        send_message(token, chat_id, texto)
    except TelegramAuthError as exc:
        logger.error("No se pudo responder en el chat (token inválido): %s", exc)
        return RESPUESTA_FALLIDA
    except TelegramPermanentError as exc:
        logger.error("No se pudo responder en el chat (error permanente): %s", exc)
        return RESPUESTA_FALLIDA
    except TelegramTransientError as exc:
        logger.warning("Respuesta al chat pendiente (error transitorio): %s", exc)
        return RESPUESTA_REINTENTAR

    logger.info("Webhook /telegram respondió en el chat de %s.", chat_id)
    return RESPUESTA_ENVIADA


def _result_payload(result: OutputBatch) -> Dict[str, Any]:
    """Cuerpo JSON común de la respuesta del pipeline (misma forma en /ingest)."""
    return {
        "status": result.status,
        "resumen": result.resumen_comunidad.model_dump(mode="json"),
        "activos": result.activos_distribucion_generados.model_dump(mode="json"),
        "almacenamiento": result.almacenamiento_oci.model_dump(mode="json"),
    }


def make_server(
    host: str, port: int, backend: Optional[str] = None
) -> ThreadingHTTPServer:
    """Crea el server HTTP (un hilo por request) y aplica el backend LLM.

    Con `port=0` el sistema operativo elige un puerto efímero (útil en tests).
    """
    apply_backend(backend)
    return ThreadingHTTPServer((host, port), IngestHandler)


class IngestHandler(BaseHTTPRequestHandler):
    """Handler de `/ingest`, `/health` y `/telegram` (pipeline en tiempo real)."""

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
        if path == "/telegram":
            if self.command == "POST":
                self._telegram()
            else:
                self._send_error(405, "Método no permitido en /telegram; usá POST")
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
        logger.info(
            "Webhook /ingest procesado: status=%s, interacciones=%d",
            result.status,
            result.resumen_comunidad.total_interacciones_procesadas,
        )

        self._send_json(200, _result_payload(result))

    def _telegram(self) -> None:
        """POST /telegram: recibe un update, lo corre por el pipeline y responde.

        Orden de controles:
        1. Fail closed: sin `TELEGRAM_WEBHOOK_SECRET` responde 503 (no se acepta
           input sin autenticar en el pipeline).
        2. Secret del header `X-Telegram-Bot-Api-Secret-Token` ausente o distinto
           -> 401 (comparado en tiempo constante con hmac.compare_digest).
        3. Body no parseable -> 400.
        4. update_id ya respondido -> 200 {"status": "duplicado"} sin reprocesar.
        5. Update sin mensaje utilizable -> 200 {"status": "ignorado"}.

        Un update procesado responde 200 con la misma forma que /ingest mas
        `ruta`, `update_id` y `respuesta` ("enviada", "omitida" o "fallida").
        El análisis se le devuelve al chat por sendMessage cuando hay
        TELEGRAM_BOT_TOKEN configurado; si esa respuesta falla de forma
        transitoria responde 500 para que Telegram reentregue, y el reintento
        sólo reenvía el chat sin volver a correr el pipeline. Un error del
        pipeline responde 500 con un mensaje sanitizado (nunca el body crudo).
        """
        secret = _webhook_secret()
        if not secret:
            self._send_error(
                503,
                "Webhook de Telegram deshabilitado: falta configurar "
                "TELEGRAM_WEBHOOK_SECRET.",
            )
            return

        header = self.headers.get(_TELEGRAM_SECRET_HEADER, "")
        if not header or not hmac.compare_digest(header, secret):
            self._send_error(401, "Secret del webhook de Telegram inválido.")
            return

        raw = self._read_body()
        try:
            update = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_error(400, "Body JSON inválido")
            return

        if not isinstance(update, dict):
            self._send_error(
                400, "Body inválido: se esperaba un update de Telegram."
            )
            return

        update_id = update.get("update_id")
        registro = _registro_update(update_id)

        # Telegram reintenta las entregas no confirmadas; un update ya
        # respondido se confirma con 200 para cortar los reintentos.
        if registro is not None and registro["estado"] == _ESTADO_RESPONDIDO:
            self._send_json(200, {"status": "duplicado", "update_id": update_id})
            return

        # Reintento de un update cuyo pipeline ya terminó: no se vuelve a
        # correr (duplicaría activos), sólo se reenvía la respuesta pendiente
        # que quedó registrada en la entrega anterior.
        reintento = registro is not None
        result: Optional[OutputBatch] = None
        body: Optional[Dict[str, Any]] = None
        texto: Optional[str] = registro["texto"] if reintento else None

        if not reintento:
            origen = os.getenv("TELEGRAM_WEBHOOK_ORIGEN") or None
            batch = messages_to_batch([update], _chat_de_update(update), origen=origen)

            if batch.interacciones:
                try:
                    result = _run_with_batch(batch)
                except Exception as exc:  # el pipeline no debe filtrar el input crudo
                    logger.exception("Error interno del pipeline en /telegram: %s", exc)
                    self._send_error(500, "Error interno del pipeline")
                    return

                logger.info(
                    "Webhook /telegram procesado: status=%s, update_id=%s, "
                    "interacciones=%d",
                    result.status,
                    update_id,
                    result.resumen_comunidad.total_interacciones_procesadas,
                )

                body = _result_payload(result)
            else:
                # Update válido de Telegram sin contenido utilizable (sin
                # message, sin texto o comando desconocido): se ignora sin
                # correr el pipeline. Un /start o /help igual recibe la
                # bienvenida, igual que con el bot en polling.
                body = {"status": "ignorado", "update_id": update_id}

            texto = _texto_de_respuesta(update, result)

            # Se memoriza recién cuando el resultado es terminal: si el
            # pipeline falla (500) NO se marca, para que Telegram reintente y
            # no se pierda. Se guarda si el pipeline realmente corrió (y con
            # qué status) para que el reintento no afirme que corrió cuando en
            # realidad fue un update sin contenido (p. ej. /start).
            if update_id is not None:
                _remember_update(
                    update_id,
                    _ESTADO_PROCESADO,
                    texto,
                    status=body.get("status"),
                )

        if body is None:
            # Reintento: el pipeline ya corrió (o el update se ignoró) en una
            # entrega anterior. Se reconstruye la nota según lo que pasó de
            # verdad, sin afirmar que el pipeline corrió cuando no lo hizo.
            # `status_previo` nunca es None para un registro creado por esta
            # versión; se defaultea por robustez ante un registro sin status.
            status_previo = registro.get("status") or "procesado"
            body = {"status": status_previo, "update_id": update_id}
            if status_previo == "ignorado":
                body["nota"] = (
                    "update sin contenido procesable, "
                    "ya atendido en una entrega anterior"
                )
            else:
                body["nota"] = (
                    "pipeline ejecutado en una entrega anterior de Telegram"
                )

        estado_respuesta = RESPUESTA_OMITIDA
        if texto is not None:
            estado_respuesta = _responder_chat(update, texto)
            if estado_respuesta == RESPUESTA_REINTENTAR:
                # Falla transitoria de la Bot API: 500 para que Telegram
                # reentregue. El estado queda "procesado" y el reintento sólo
                # reenvía el chat, sin volver a correr el pipeline.
                self._send_error(500, "No se pudo enviar la respuesta a Telegram.")
                return

        # Nota de concurrencia: entre el _registro_update de arriba y este
        # _remember_update hay una llamada de red (sendMessage). Si Telegram
        # reentrega el update por timeout antes de que esto termine, dos hilos
        # pueden enviar el mismo mensaje una vez cada uno. No se serializa
        # porque el costo (bloquear el handler durante la red) supera el
        # beneficio: el peor caso es un mensaje duplicado, no una pérdida.
        if update_id is not None:
            _remember_update(
                update_id,
                _ESTADO_RESPONDIDO,
                texto,
                status=body.get("status"),
            )

        body["ruta"] = "/telegram"
        body["update_id"] = update_id
        body["respuesta"] = estado_respuesta
        self._send_json(200, body)

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
            allow = _ALLOWED_METHODS.get(self.path.split("?", 1)[0])
            if allow:
                self.send_header("Allow", allow)
        self.end_headers()
        self.wfile.write(payload)

    def _send_error(self, status: int, message: str) -> None:
        """Error JSON uniforme: {"error": "<mensaje>"}."""
        self._send_json(status, {"error": message})
