#!/usr/bin/env python3
"""Levanta el webhook HTTP de ingesta en tiempo real (Escalón 3).

Uso:
    python scripts/run_webhook.py [--host 127.0.0.1] [--port 8765]
        [--backend auto|ollama|openai|gemini|rule_based] [--model gemma4:31b]
        [--secret <token>]

El backend se resuelve: `--backend` > COMMUNITYLAB_LLM_BACKEND (.env) >
rule_based. `--model` setea OLLAMA_MODEL en el entorno. `--secret` setea
TELEGRAM_WEBHOOK_SECRET, el secret que Telegram manda en el header
`X-Telegram-Bot-Api-Secret-Token` al `POST /telegram` (Fase 2 del webhook de
Telegram); sin él esa ruta responde 503. Con TELEGRAM_BOT_TOKEN configurado, la
respuesta del análisis se envía de vuelta al chat que originó el update; sin ese
token el análisis se procesa igual pero la respuesta al chat queda omitida.
Ctrl-C apaga el server y sale con código 0.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE = REPO_ROOT / "data" / "sample" / "demo_fixed.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Levanta el webhook HTTP de ingesta de CommunityLab "
            "(POST /ingest, GET /health, POST /telegram)."
        )
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Interfaz a escuchar (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Puerto a escuchar (default: 8765).",
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
        "--secret",
        help=(
            "Secret del webhook de Telegram; setea TELEGRAM_WEBHOOK_SECRET. "
            "Sin él, POST /telegram responde 503."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    load_dotenv(REPO_ROOT / ".env")
    if args.model:
        os.environ["OLLAMA_MODEL"] = args.model
    if args.secret:
        os.environ["TELEGRAM_WEBHOOK_SECRET"] = args.secret

    sys.path.insert(0, str(REPO_ROOT))
    from src.ingest.runtime import apply_backend  # noqa: E402
    from src.ingest.webhook import make_server  # noqa: E402

    backend = apply_backend(args.backend)
    server = make_server(args.host, args.port)
    host, port = server.server_address

    print("=" * 68)
    print("CommunityLab — webhook de ingesta (Escalón 3)")
    print("=" * 68)
    print(f"  server  : http://{host}:{port}")
    print(f"  backend : {backend}")
    print("-" * 68)
    print("EJEMPLOS DE CURL")
    if DEFAULT_SAMPLE.exists():
        print(f"  curl -X POST http://{host}:{port}/ingest \\")
        print("       -H 'Content-Type: application/json' \\")
        print(f"       -d @{DEFAULT_SAMPLE}")
    print("  curl -X POST http://{0}:{1}/ingest \\".format(host, port))
    print("       -H 'Content-Type: application/json' \\")
    print(
        "       -d '[{\"autor\":\"Ana\",\"canal\":\"#general\","
        "\"tipo\":\"testimonio\","
        "\"texto\":\"Logré mi primer empleo como desarrolladora!\"}]'"
    )
    print(f"  curl http://{host}:{port}/health")
    print("  # POST /telegram (Fase 2): requiere --secret / TELEGRAM_WEBHOOK_SECRET;")
    print("  # con TELEGRAM_BOT_TOKEN la respuesta se envía al chat del update")
    print(f"  curl -X POST http://{host}:{port}/telegram \\")
    print("       -H 'Content-Type: application/json' \\")
    print("       -H 'X-Telegram-Bot-Api-Secret-Token: <secret>' \\")
    print(
        "       -d '{\"update_id\":1,\"message\":{\"message_id\":1,"
        "\"date\":1730000000,\"text\":\"Hola comunidad\","
        "\"from\":{\"first_name\":\"Ana\"},\"chat\":{\"id\":123456789,\"type\":\"private\"}}}'"
    )
    print("=" * 68)
    print("Ctrl-C para apagar el server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nApagando el webhook...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
