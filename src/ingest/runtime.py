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
