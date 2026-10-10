"""Ingesta de mensajes de Telegram (Bot API) hacia el contrato del pipeline.

Esta es la fuente Telegram del Escalón 2 de ingesta: convierte los updates de
la Bot API en un InputBatch JSON válido con el MISMO contrato que ya consumen
loader.load_batch y el pipeline (origen_comunidad, periodo_referencia,
interacciones), de modo que puede mergearse con las fuentes .json/.csv
existentes.

Patrón: sigue el estilo de src/ingest/ingest.py (scraper de Mastodon): obtener
datos remotos, normalizar cada mensaje y escribir el JSON de salida. La
normalización de campos (alias en inglés, fecha->timestamp, url->metadata) se
delega en InputNormalizer para no duplicar reglas.

LIMITACIÓN REAL (Bot API, no la API MTProto de cliente):
- Un bot solo ve los mensajes que llegan DESPUÉS de que lo agregaron al
  grupo/canal; no puede leer el historial previo a su incorporación.
- getUpdates entrega únicamente el backlog reciente (ventana por defecto de
  24 h) y Telegram lo purga después; cada update se entrega una sola vez salvo
  que se juegue con `offset`.
- No existe forma de leer historial viejo arbitrario con la Bot API.
El valor de esta fuente es HACIA ADELANTE: se corre periódicamente y se
acumulan los mensajes nuevos.

Seguridad: el token nunca se imprime ni se incluye en los mensajes de error.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from src.domain.models import InputBatch, InputMessage
from src.ingest.normalizer import InputNormalizer

# Base de la Bot API. El token viaja embebido en la URL del método; por eso
# ningún error expone la URL cruda (evita filtrar el secreto en logs).
_API_BASE = "https://api.telegram.org"

# Timeout de red, consistente con ingest.py.
_TIMEOUT = 15

# Canal de salida para todos los mensajes de Telegram en el contrato.
CANAL_TELEGRAM = "#telegram"

# Fallback de autor cuando el remitente no trae nombre, apellido ni username.
_AUTOR_DESCONOCIDO = "usuario_desconocido"


# Funciones


def fetch_updates(
    token: str,
    chat: str,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Trae los updates recientes con getUpdates, filtrados por el chat pedido.

    - `token`: token del bot (lo emite @BotFather).
    - `chat`: chat_id del grupo/canal a ingestar. getUpdates no acepta chat_id,
      así que la respuesta se filtra acá comparando el id del mensaje.
    - `offset`: update_id desde el cual empezar; se reenvía tal cual a la API.
    - `limit`: cantidad máxima de updates a pedir (la API acepta 1..100).

    Devuelve la lista de updates (dicts con update_id + message) del chat.
    Levanta ValueError si falta el token, y RuntimeError con un mensaje claro
    si la API responde "ok": false o si hay un error HTTP/red.
    """
    if not token:
        raise ValueError(
            "Falta el token del bot de Telegram; pasalo con --token "
            "o definí la variable de entorno TELEGRAM_BOT_TOKEN."
        )

    url = f"{_API_BASE}/bot{token}/getUpdates"
    params: Dict[str, Any] = {}
    if offset is not None:
        params["offset"] = offset
    if limit is not None:
        params["limit"] = limit

    try:
        respuesta = requests.get(url, params=params, timeout=_TIMEOUT)
        respuesta.raise_for_status()
    except requests.HTTPError as err:
        codigo = err.response.status_code if err.response is not None else "?"
        # Se descarta la cadena del error (contiene la URL con el token).
        raise RuntimeError(
            f"Telegram respondió HTTP {codigo} al consultar getUpdates. "
            "Revisá el token (401 = inválido) y que el bot exista."
        ) from None
    except requests.RequestException:
        raise RuntimeError(
            "Error de red al consultar getUpdates de Telegram; "
            "revisá la conexión y volvé a intentar."
        ) from None

    datos = respuesta.json()
    if not datos.get("ok"):
        descripcion = datos.get("description") or "respuesta sin 'ok': true"
        raise RuntimeError(f"Telegram devolvió ok=false: {descripcion}")

    result = datos.get("result") or []
    return [u for u in result if _es_mensaje_del_chat(u, chat)]


def messages_to_batch(
    updates: List[Dict[str, Any]],
    chat: str,
    origen: Optional[str] = None,
) -> InputBatch:
    """Mapea updates de Telegram a un InputBatch del contrato.

    Campos por mensaje:
    - `autor`: first_name/last_name del remitente (o username, o título del chat).
    - `canal`: "#telegram".
    - `tipo`: el default de InputNormalizer cuando no hay tipo ("otro").
    - `texto`: message.text.
    - `id`: message_id como texto.
    - `timestamp`: message.date (unix) convertido a ISO-8601 UTC.
    - `metadata["url"]`: primera URL de las entities, si existe.

    Se descartan los mensajes sin texto y los comandos internos (texto que
    empieza con "/"). El envelope queda con `origen_comunidad` = `origen` (o
    "Telegram-<chat>") y `periodo_referencia` = "telegram-<fecha de hoy>".
    """
    normalizer = InputNormalizer()
    interacciones: List[InputMessage] = []

    for update in updates:
        mensaje = update.get("message") if isinstance(update, dict) else None
        if not isinstance(mensaje, dict):
            continue

        texto = (mensaje.get("text") or "").strip()
        if not texto or texto.startswith("/"):
            continue

        metadata: Dict[str, Any] = {}
        url = _url_de_entities(mensaje, texto)
        if url:
            metadata["url"] = url

        message_id = mensaje.get("message_id")
        raw = {
            "autor": _autor_de_remitente(mensaje),
            "canal": CANAL_TELEGRAM,
            "texto": texto,
            "id": str(message_id) if message_id is not None else None,
            "timestamp": _timestamp_iso(mensaje.get("date")),
            "metadata": metadata,
        }
        interacciones.append(normalizer.normalize("telegram", raw))

    origen_final = origen or f"Telegram-{chat}"
    periodo = datetime.now(timezone.utc).strftime("telegram-%Y-%m-%d")

    return InputBatch(
        origen_comunidad=origen_final,
        periodo_referencia=periodo,
        interacciones=interacciones,
    )


def save_batch(batch: InputBatch, out: Union[str, Path]) -> Path:
    """Escribe el InputBatch como JSON del contrato (utf-8, indentado)."""
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(batch.model_dump(mode="json"), handle, ensure_ascii=False, indent=2)
    return out_path


def _es_mensaje_del_chat(update: Dict[str, Any], chat: str) -> bool:
    """True si el update es un 'message' del chat pedido (ids comparados como texto)."""
    if not isinstance(update, dict):
        return False
    mensaje = update.get("message")
    if not isinstance(mensaje, dict):
        return False
    chat_mensaje = mensaje.get("chat")
    if not isinstance(chat_mensaje, dict):
        return False
    chat_id = chat_mensaje.get("id")
    return chat_id is not None and str(chat_id) == str(chat)


def _autor_de_remitente(mensaje: Dict[str, Any]) -> str:
    """Arma el autor: nombre y apellido, con username y título del chat de respaldo."""
    remitente = mensaje.get("from") or {}
    nombre = " ".join(
        parte
        for parte in (remitente.get("first_name"), remitente.get("last_name"))
        if parte
    )
    if nombre:
        return nombre
    if remitente.get("username"):
        return remitente["username"]
    chat = mensaje.get("chat") or {}
    return chat.get("title") or _AUTOR_DESCONOCIDO


def _url_de_entities(mensaje: Dict[str, Any], texto: str) -> Optional[str]:
    """Extrae la primera URL de las entities del mensaje, si existe.

    - type "url": la URL es el propio fragmento de texto (offset + length).
    - type "text_link": la URL viene en el campo "url" de la entity.
    """
    for entity in mensaje.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        tipo = entity.get("type")
        if tipo == "text_link" and entity.get("url"):
            return entity["url"]
        if tipo == "url":
            offset = entity.get("offset") or 0
            length = entity.get("length") or 0
            url = texto[offset: offset + length]
            if url:
                return url
    return None


def _timestamp_iso(unix_date: Optional[int]) -> Optional[str]:
    """Convierte la fecha unix de Telegram al timestamp ISO-8601 (UTC) del contrato."""
    if unix_date is None:
        return None
    fecha = datetime.fromtimestamp(int(unix_date), tz=timezone.utc)
    return fecha.strftime("%Y-%m-%dT%H:%M:%SZ")
