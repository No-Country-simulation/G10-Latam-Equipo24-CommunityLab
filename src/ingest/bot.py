"""Bot interactivo de Telegram (Escalón 4 de ingesta, stretch S5).

Responde en tiempo real a cada mensaje con el análisis del pipeline: arma un
InputBatch de 1 mensaje en memoria (envelope `Telegram-bot-<fecha>`), lo pasa
a `src.pipeline._run_with_batch` (el mismo helper del webhook) y devuelve un
texto corto en español con el sentimiento, los temas principales y la decisión
(PUBLICAR / CREAR_FAQ / DESCARTAR).

Es el diferencial del demo, NUNCA el camino obligatorio: el camino por archivo
siempre funciona. Es stretch S5 y converge con la HU-S5-007 (webhooks de
Emanuel), porque reutiliza exactamente el mismo `_run_with_batch` y el mismo
contrato de entrada (`InputBatch`).

Solo se usan `requests` y la librería estándar (sin dependencias nuevas). El
token nunca se imprime ni se incluye en los mensajes de error (mismo cuidado
que src/ingest/telegram.py): los errores se sanitizan con `from None` y se
descartan las cadenas de excepción que puedan contener la URL con el token.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from src.domain.models import InputBatch, OutputBatch
from src.ingest.normalizer import InputNormalizer
from src.ingest.telegram import fetch_updates
from src.ingest.webhook import apply_backend
from src.pipeline import _run_with_batch

logger = logging.getLogger(__name__)

# Base de la Bot API y timeout de red, consistentes con telegram.py.
_API_BASE = "https://api.telegram.org"
_TIMEOUT = 15

# Envelope del batch armado para cada mensaje: "Telegram-bot-<fecha>".
_ENVELOPE_PREFIX = "Telegram-bot"

# Autor/canal por defecto de un mensaje recibido por el bot. build_reply es
# una función pura (solo recibe el texto), así que el remitente real no llega
# hasta acá; el texto es lo que manda para el análisis.
_REPLY_AUTOR = "usuario_telegram"
_REPLY_CANAL = "#telegram"

# Backoff exponencial para errores de red/HTTP: 1s, 2s, 4s, ... tope 30s.
_BACKOFF_BASE = 1
_BACKOFF_MAX = 30

WELCOME_TEXT = (
    "Hola, soy el bot de CommunityLab. Mandame un mensaje de la comunidad "
    "(un testimonio, una duda técnica, un logro) y te devuelvo el análisis "
    "del pipeline: sentimiento, temas principales y la decisión "
    "(PUBLICAR, CREAR_FAQ o DESCARTAR).\n"
    "Comandos: /start y /help."
)

EMPTY_REPLY = (
    "No recibí ningún texto para analizar. Escribime un mensaje de la "
    "comunidad y te cuento el análisis del pipeline."
)

GENERIC_ERROR_REPLY = (
    "Uy, en este momento no pude analizar tu mensaje. Probá de nuevo en un "
    "rato; el resto del pipeline sigue funcionando con normalidad."
)

# Indirección para que los tests puedan reemplazar los sleeps del backoff.
_sleep = time.sleep


# ---------------------------------------------------------------------------
# Respuesta pura (sin I/O de Telegram)
# ---------------------------------------------------------------------------


def build_reply(message_text: str) -> str:
    """Respuesta pura para un mensaje del bot.

    - Vacío o solo espacios -> texto amable (EMPTY_REPLY).
    - `/start` y `/help` -> bienvenida (WELCOME_TEXT).
    - Cualquier otro comando (empieza con "/") -> cadena vacía (se ignora; el
      bucle no envía respuesta, como en el escalón 2).
    - Cualquier otro texto -> arma un InputBatch de 1 mensaje
      (InputNormalizer + envelope `Telegram-bot-<fecha>`), lo pasa a
      `_run_with_batch` y aplana el OutputBatch en un texto corto en español:
      sentimiento, hasta 3 temas principales y el estado del activo FAQ o la
      decisión. Si el pipeline falla, devuelve un texto amable genérico, nunca
      el traceback.

    Es determinista con backend rule_based (sin red). No hace I/O de Telegram;
    el único efecto colateral del pipeline es el snapshot local de
    almacenamiento cuando no hay credenciales OCI (misma degradación que el
    webhook), por eso los tests aíslan el cwd en tmp_path.
    """
    if not message_text or not message_text.strip():
        return EMPTY_REPLY

    comando = _comando(message_text)
    if comando in ("/start", "/help"):
        return WELCOME_TEXT
    if comando is not None:
        return ""  # comando no reconocido: no se envía respuesta

    batch = _batch_de_un_mensaje(message_text)
    try:
        result = _run_with_batch(batch)
    except Exception as exc:  # el bot nunca le filtra el traceback al usuario
        logger.warning(
            "El pipeline falló al analizar el mensaje del bot: %s",
            type(exc).__name__,
        )
        return GENERIC_ERROR_REPLY
    return _formatear_respuesta(result)


def _comando(texto: str) -> Optional[str]:
    """Primer token del texto si empieza con "/", sin el sufijo @botname."""
    token = texto.strip().split(maxsplit=1)[0] if texto.strip() else ""
    if not token.startswith("/"):
        return None
    return token.split("@", 1)[0].lower()


def _batch_de_un_mensaje(texto: str) -> InputBatch:
    """Arma un InputBatch de 1 mensaje con el envelope `Telegram-bot-<fecha>`."""
    normalizer = InputNormalizer()
    raw: Dict[str, Any] = {
        "autor": _REPLY_AUTOR,
        "canal": _REPLY_CANAL,
        "texto": texto,
    }
    envelope = datetime.now(timezone.utc).strftime(f"{_ENVELOPE_PREFIX}-%Y-%m-%d")
    return InputBatch(
        origen_comunidad=envelope,
        periodo_referencia=envelope,
        interacciones=[normalizer.normalize("telegram", raw)],
    )


def _formatear_respuesta(result: OutputBatch) -> str:
    """Aplana un OutputBatch a un texto corto en español.

    La decisión se deriva de los activos generados (el pipeline decide y los
    generadores materializan): post de LinkedIn presente -> PUBLICAR;
    sugerencia de FAQ presente -> CREAR_FAQ con su estado; ninguna -> DESCARTAR.
    """
    resumen = result.resumen_comunidad
    temas = resumen.temas_principales[:3]
    linea_temas = ", ".join(temas) if temas else "sin temas detectados"

    activos = result.activos_distribucion_generados
    if activos.post_linkedin is not None:
        decision = "PUBLICAR (post para LinkedIn generado)"
    elif activos.sugerencia_contenido_faq is not None:
        faq = activos.sugerencia_contenido_faq
        decision = f"CREAR_FAQ (tema: {faq.tema}; estado: {faq.status})"
    else:
        decision = "DESCARTAR (sin activo para distribuir)"

    return "\n".join(
        [
            "Análisis de tu mensaje:",
            f"- Sentimiento: {resumen.sentimiento_predominante}",
            f"- Temas principales: {linea_temas}",
            f"- Decisión: {decision}",
        ]
    )


# ---------------------------------------------------------------------------
# Bot API (long polling + respuesta)
# ---------------------------------------------------------------------------


def send_message(token: str, chat_id: Any, text: str) -> None:
    """Envía una respuesta con sendMessage; errores sanitizados (sin token)."""
    if not token:
        raise ValueError("Falta el token del bot de Telegram.")

    url = f"{_API_BASE}/bot{token}/sendMessage"
    try:
        respuesta = requests.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=_TIMEOUT,
        )
        respuesta.raise_for_status()
    except requests.HTTPError as err:
        codigo = err.response.status_code if err.response is not None else "?"
        # Se descarta la cadena del error (contiene la URL con el token).
        raise RuntimeError(
            f"Telegram respondió HTTP {codigo} al enviar sendMessage. "
            "Revisá el token (401 = inválido)."
        ) from None
    except requests.RequestException:
        raise RuntimeError(
            "Error de red al enviar sendMessage a Telegram; "
            "revisá la conexión y volvé a intentar."
        ) from None

    datos = respuesta.json()
    if not datos.get("ok"):
        descripcion = datos.get("description") or "respuesta sin 'ok': true"
        raise RuntimeError(
            f"Telegram devolvió ok=false al enviar la respuesta: {descripcion}"
        ) from None


def next_offset(
    updates: List[Dict[str, Any]], current: Optional[int] = None
) -> Optional[int]:
    """Avanza el offset: último update_id visto + 1 (nunca retrocede).

    Se calcula sobre TODOS los updates devueltos por la API, no solo los que
    se procesan: Telegram no vuelve a entregar un update hasta que se confirma
    con un offset mayor, así que quedarse atrás re-entregaría los mismos
    updates en cada ciclo.
    """
    ids = [
        u["update_id"]
        for u in updates
        if isinstance(u, dict) and u.get("update_id") is not None
    ]
    if not ids:
        return current
    siguiente = max(ids) + 1
    if current is None:
        return siguiente
    return max(current, siguiente)


def _backoff_delay(attempt: int) -> int:
    """Delay de reintento: 1s, 2s, 4s, ..., tope 30s."""
    return min(_BACKOFF_MAX, _BACKOFF_BASE * (2 ** attempt))


def run_bot(
    token: str,
    *,
    backend: Optional[str] = None,
    poll_timeout: int = 30,
    max_cycles: Optional[int] = None,
) -> int:
    """Bucle de long polling: getUpdates -> responder -> avanzar offset.

    - `backend`: se aplica a COMMUNITYLAB_LLM_BACKEND (la fuente de verdad de
      get_llm_client), igual que en el webhook.
    - `poll_timeout`: long polling de la Bot API en segundos (default 30).
    - `max_cycles`: límite de iteraciones del bucle, solo para tests.
    - Error de red/HTTP: backoff exponencial (1s, 2s, 4s, tope 30s) y
      reintento; el bucle no muere (solo se loguea el tipo de error, nunca el
      token).
    - KeyboardInterrupt: se propaga para que el CLI cierre con exit 0.
    """
    apply_backend(backend)
    offset: Optional[int] = None
    attempt = 0
    cycles = 0

    while max_cycles is None or cycles < max_cycles:
        cycles += 1
        try:
            updates = fetch_updates(token, offset=offset, poll_timeout=poll_timeout)
            _responder_updates(token, updates)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            delay = _backoff_delay(attempt)
            attempt += 1
            logger.warning(
                "Error de red o de la Bot API (%s); reintento en %ss",
                type(exc).__name__,
                delay,
            )
            _sleep(delay)
            continue

        attempt = 0
        offset = next_offset(updates, offset)
    return 0


def _responder_updates(token: str, updates: List[Dict[str, Any]]) -> int:
    """Responde a cada mensaje de texto de los updates; devuelve cuántos.

    Se ignoran los updates que no son `message`, los mensajes sin texto y los
    comandos que no sean /start o /help (`build_reply` devuelve "" para esos).
    Si send_message falla, el error se propaga para que el bucle reintente con
    backoff (el update aún no se confirma con el offset).
    """
    respondidos = 0
    for update in updates:
        mensaje = update.get("message") if isinstance(update, dict) else None
        if not isinstance(mensaje, dict):
            continue

        texto = (mensaje.get("text") or "").strip()
        if not texto:
            continue

        chat_id = (mensaje.get("chat") or {}).get("id")
        if chat_id is None:
            continue

        reply = build_reply(texto)
        if not reply:
            continue  # comando no reconocido o vacío: no se responde

        send_message(token, chat_id, reply)
        respondidos += 1
    return respondidos
