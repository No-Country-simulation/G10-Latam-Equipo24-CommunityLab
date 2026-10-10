#!/usr/bin/env python3
"""Levanta el bot interactivo de Telegram (Escalón 4 de ingesta, stretch S5).

Uso:
    python scripts/run_bot.py [--token TOKEN] [--backend auto|rule_based|...]
        [--model gemma4:31b] [--poll-timeout 30]

El token se resuelve: `--token` > TELEGRAM_BOT_TOKEN (.env o entorno). El
backend se resuelve igual que el webhook: `--backend` >
COMMUNITYLAB_LLM_BACKEND > rule_based (determinista, sin red, sin costo).
`--model` setea OLLAMA_MODEL. `--poll-timeout` ajusta el long polling de la
Bot API (default 30 segundos). Ctrl-C apaga el bot con salida 0.

El bot responde a cada mensaje con el análisis del pipeline; es el
diferencial del demo, nunca el camino obligatorio (el camino por archivo
siempre funciona).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Levanta el bot interactivo de Telegram de CommunityLab "
            "(responde con el análisis del pipeline)."
        )
    )
    parser.add_argument(
        "--token",
        help="Token del bot de Telegram (default: TELEGRAM_BOT_TOKEN).",
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "ollama", "openai", "gemini", "rule_based"],
        default="auto",
        help=(
            "Backend LLM; 'auto' usa COMMUNITYLAB_LLM_BACKEND "
            "(default: rule_based)."
        ),
    )
    parser.add_argument(
        "--model",
        help="Modelo Ollama; setea OLLAMA_MODEL en el entorno.",
    )
    parser.add_argument(
        "--poll-timeout",
        type=int,
        default=30,
        help="Long polling de la Bot API en segundos (default: 30).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    load_dotenv(REPO_ROOT / ".env")
    if args.model:
        os.environ["OLLAMA_MODEL"] = args.model

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print(
            "Falta el token del bot. Pasalo con --token o definí la variable "
            "de entorno TELEGRAM_BOT_TOKEN.",
            file=sys.stderr,
        )
        return 1

    sys.path.insert(0, str(REPO_ROOT))
    from src.ingest.bot import run_bot  # noqa: E402
    from src.ingest.webhook import apply_backend  # noqa: E402

    backend = apply_backend(args.backend)

    print("=" * 68)
    print("CommunityLab — bot interactivo de Telegram (Escalón 4 / S5)")
    print("=" * 68)
    print(f"  backend      : {backend}")
    print(f"  long polling : {args.poll_timeout}s")
    print("-" * 68)
    print("bot listo. Mandale un mensaje al bot en Telegram para probarlo.")
    print("Comandos: /start y /help. Ctrl-C para apagarlo.")
    print("=" * 68)

    try:
        run_bot(token, backend=args.backend, poll_timeout=args.poll_timeout)
    except KeyboardInterrupt:
        print("\nApagando el bot...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
