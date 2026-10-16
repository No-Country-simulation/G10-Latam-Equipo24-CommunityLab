#!/usr/bin/env python3
"""CLI de ingesta de Telegram (Bot API) hacia el contrato del pipeline.

Uso:
    python scripts/ingest_telegram.py --token <BOT_TOKEN> --chat <chat_id> \
        [--out data/sample/telegram_interacciones.json] [--limit N] \
        [--offset N] [--origen TEXT] [--verbose]

El token también puede venir de la variable de entorno TELEGRAM_BOT_TOKEN.
Salida: 0 = éxito, 1 = error (falta token, error de red/API o de escritura).

Limitación: un bot solo ve los mensajes posteriores a su incorporación al
grupo/canal y getUpdates entrega únicamente el backlog reciente (ventana de
24 h por defecto). No hay forma de leer historial viejo con la Bot API.
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = "data/sample/telegram_interacciones.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingesta de mensajes de Telegram (Bot API) para CommunityLab"
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Token del bot (alternativa: variable de entorno TELEGRAM_BOT_TOKEN)",
    )
    parser.add_argument(
        "--chat", required=True, help="chat_id del grupo/canal a ingestar"
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Ruta del JSON de salida (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cantidad máxima de updates a pedir (la API acepta 1..100)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=None,
        help="update_id desde el cual empezar (getUpdates)",
    )
    parser.add_argument(
        "--origen",
        default=None,
        help="Valor de 'origen_comunidad' en el JSON de salida",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Imprime detalles del proceso"
    )
    args = parser.parse_args()

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print(
            "ERROR: falta el token del bot. Pasalo con --token o definí "
            "TELEGRAM_BOT_TOKEN en el entorno.",
            file=sys.stderr,
        )
        return 1

    sys.path.insert(0, str(REPO_ROOT))
    from src.ingest.telegram import fetch_updates, messages_to_batch, save_batch

    if args.verbose:
        print(f"Consultando getUpdates del chat {args.chat}", file=sys.stderr)

    try:
        updates = fetch_updates(token, args.chat, offset=args.offset, limit=args.limit)
    except (RuntimeError, ValueError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    batch = messages_to_batch(updates, args.chat, origen=args.origen)

    if args.verbose:
        print(
            f"Updates recibidos para el chat: {len(updates)} "
            f"(quedan {len(batch.interacciones)} tras descartar vacíos/comandos)",
            file=sys.stderr,
        )

    try:
        out_path = save_batch(batch, args.out)
    except OSError as err:
        print(f"ERROR: no se pudo escribir {args.out}: {err}", file=sys.stderr)
        return 1

    print(
        f"Guardado: {out_path} ({len(batch.interacciones)} interacciones, "
        f"origen {batch.origen_comunidad})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
