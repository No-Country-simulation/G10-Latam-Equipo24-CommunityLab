"""Publish a selected LinkedIn candidate to a Telegram chat.

This module is the bridge between the dashboard and the Telegram transport
that already exists and is already tested in ``src.ingest.bot``. It NEVER
implements its own HTTP client and never duplicates Bot API calls: it only
formats the message and delegates the actual send to ``send_message``.

The token is never printed, logged, returned, or embedded in any exception
message — same care as ``src/ingest/telegram.py`` and ``src/ingest/bot.py``.
"""

import os
from typing import Any, Callable, Mapping, Optional

from src.ingest.bot import send_message

# dotenv is optional: a missing dependency must not break the dashboard.
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - exercised only without python-dotenv
    load_dotenv = None

ENV_TOKEN = "TELEGRAM_BOT_TOKEN"
ENV_CHAT_ID = "TELEGRAM_CHAT_ID"

# ``.env`` is loaded lazily and only once; tests always inject ``env=`` and
# never reach this path.
_ENV_LOADED = False


class TelegramConfigError(ValueError):
    """Falta configuración de Telegram para poder publicar."""


# ---------------------------------------------------------------------------
# Formato del mensaje
# ---------------------------------------------------------------------------


def _as_text(value: Any) -> str:
    """Normaliza un valor a texto plano; ``None`` y ausente -> cadena vacía."""
    if value is None:
        return ""
    return str(value).strip()


def _as_percentage(value: Any) -> Optional[str]:
    """Renderiza ``relevancia`` como porcentaje entero (0.75 -> ``75%``).

    Devuelve ``None`` cuando no hay un valor numérico utilizable, para que el
    llamador omita la línea completa.
    """
    if value is None or value == "":
        return None
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return None


def format_candidate_message(candidato: Mapping[str, Any]) -> str:
    """Arma el texto plano exacto que se enviará a Telegram.

    Solo texto plano: ``send_message`` no pasa ``parse_mode``, así que
    cualquier Markdown llegaría literal. La forma es: ``titulo``, una línea en
    blanco, ``copy`` y luego las líneas de pie que existan (canal sugerido,
    autor y relevancia como porcentaje). Un campo vacío no emite su etiqueta y
    nunca se emite una línea en blanco inicial cuando falta el ``titulo``.
    """
    datos: Mapping[str, Any] = candidato or {}
    titulo = _as_text(datos.get("titulo"))
    copy = _as_text(datos.get("copy"))

    partes = []
    if titulo:
        partes.append(titulo)
    if copy:
        if partes:
            partes.append("")  # línea en blanco entre el título y el copy
        partes.append(copy)

    canal = _as_text(datos.get("canal_recomendado"))
    if canal:
        partes.append(f"Canal sugerido: {canal}")

    autor = _as_text(datos.get("autor"))
    if autor:
        partes.append(f"Autor: {autor}")

    relevancia = _as_percentage(datos.get("relevancia"))
    if relevancia is not None:
        partes.append(f"Relevancia: {relevancia}")

    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Configuración y envío
# ---------------------------------------------------------------------------


def _load_env_once() -> None:
    """Carga ``.env`` una sola vez; si falta python-dotenv no hace nada."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    if load_dotenv is not None:
        load_dotenv()


def _clean_env_value(value: Any) -> Any:
    """Recorta los espacios de un valor textual; deja pasar los no textuales."""
    if isinstance(value, str):
        return value.strip()
    return value


def _resolve_config(env: Optional[Mapping[str, Any]]) -> Any:
    """Resuelve token y chat_id; falla con el nombre exacto de lo faltante."""
    if env is None:
        _load_env_once()
        fuente: Mapping[str, Any] = os.environ
    else:
        fuente = env

    token = _clean_env_value(fuente.get(ENV_TOKEN))
    chat_id = _clean_env_value(fuente.get(ENV_CHAT_ID))

    faltantes = []
    if not token:
        faltantes.append(ENV_TOKEN)
    if not chat_id:
        faltantes.append(ENV_CHAT_ID)
    if faltantes:
        raise TelegramConfigError(
            f"Falta configuración de Telegram: {', '.join(faltantes)}. "
            "Definí esas variables en el archivo .env (ver .env.example)."
        )
    return token, chat_id


def publish_candidate(
    candidato: Mapping[str, Any],
    *,
    sender: Callable[[str, Any, str], None] = send_message,
    env: Optional[Mapping[str, Any]] = None,
) -> str:
    """Publica el candidato en Telegram y devuelve el texto enviado.

    - ``sender`` es inyectable para que los tests no toquen la red.
    - ``env`` es inyectable para que los tests nunca lean el entorno real; si
      es ``None`` se cae a ``os.environ`` después de cargar ``.env`` una vez.
    - Configuración incompleta -> ``TelegramConfigError`` nombrando la variable
      faltante, sin enviar nada.
    - El token nunca aparece en excepciones, logs ni en el valor devuelto.
    """
    token, chat_id = _resolve_config(env)
    texto = format_candidate_message(candidato)
    sender(token, chat_id, texto)
    return texto
