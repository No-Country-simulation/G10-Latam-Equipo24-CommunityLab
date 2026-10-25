"""Selección del backend LLM en tiempo de ejecución.

Vive en un módulo propio (y no en `webhook.py`) porque lo usan tanto la capa
HTTP (`webhook.py`, `scripts/run_webhook.py`) como el bot en polling
(`bot.py`, `scripts/run_bot.py`). Que el bot importara desde el webhook
creaba una dependencia al revés: el cliente de Telegram no debe depender del
servidor HTTP.
"""

import os
from typing import Optional


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


# Orden de los backends en el selector del panel: los LLM reales primero y
# `rule_based` (el fallback determinista) al final.
LLM_BACKEND_ORDER = ("ollama", "gemini", "openai", "rule_based")


def _ollama_importable() -> bool:
    """Indica si el paquete Python `ollama` está instalado (modo local).

    `OllamaClient` en modo local (sin `OLLAMA_API_KEY`) habla con `ollama
    serve` a través del paquete `ollama`. Sin ese paquete el modo local falla
    al correr aunque el binario de Ollama esté instalado, así que la opción no
    debe figurar como habilitada.
    """
    try:
        import ollama  # noqa: F401
    except ImportError:
        return False
    return True


def _ollama_available() -> bool:
    """`ollama` está habilitado en modo nube (key) o en modo local (paquete).

    Son dos modos distintos de `OllamaClient`: con `OLLAMA_API_KEY` usa el SDK
    `openai` contra `OLLAMA_BASE_URL`; sin key usa el paquete `ollama` contra
    el servidor local. Se habilita si al menos uno de los dos está disponible.
    """
    return bool(os.getenv("OLLAMA_API_KEY")) or _ollama_importable()


def available_backends() -> dict[str, bool]:
    """Backends habilitados según las credenciales y dependencias presentes.

    `rule_based` no necesita nada. `ollama` requiere la key (nube) o el paquete
    Python `ollama` (local). `gemini` y `openai` requieren su API key.
    """
    return {
        "ollama": _ollama_available(),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "rule_based": True,
    }


def split_backends() -> tuple[list[str], list[str]]:
    """Particiona los backends en (activos, inactivos) según `LLM_BACKEND_ORDER`.

    Útil para el selector del panel: los activos van al `selectbox` y los
    inactivos se listan debajo para dejar claro que el sistema los soporta
    aunque hoy no estén disponibles.
    """
    disponibles = available_backends()
    activos = [b for b in LLM_BACKEND_ORDER if disponibles.get(b, False)]
    inactivos = [b for b in LLM_BACKEND_ORDER if not disponibles.get(b, False)]
    return activos, inactivos
