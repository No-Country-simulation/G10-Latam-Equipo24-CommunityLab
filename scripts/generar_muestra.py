#!/usr/bin/env python3
"""Regenera la muestra de ejemplo del dashboard de CommunityLab.

La muestra es una **salida ya calculada** del contrato (`OutputBatch`) guardada
como JSON. El dashboard la carga de forma instantánea (botón "⚡ Cargar muestra
de ejemplo") sin ejecutar el LLM en vivo: por eso sirve para un Demo Day donde
no se puede esperar ni depender de la red.

Este script reconstruye esa muestra corriendo el pipeline real sobre las tres
fuentes de muestra completas, fusionadas en un solo lote:

    - data/sample/demo_fixed.json            (12 interacciones, curado)
    - data/sample/sintetico_120.csv          (120 interacciones)
    - data/sample/mastodon_interacciones.json (100 interacciones)

Total: 232 interacciones. Usa el mismo `process_combined_sample` que el botón
"🧪 Procesar demo combinada" del dashboard, así la muestra y la demo en vivo
producen exactamente el mismo formato.

Uso:
    python scripts/generar_muestra.py             # backend de .env (Gemma real)
    python scripts/generar_muestra.py --offline   # rule_based (determinista, sin key)

Salida: sobrescribe data/sample/corrida-completa-gemma.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "data" / "sample"

SOURCES = [
    SAMPLE_DIR / "demo_fixed.json",
    SAMPLE_DIR / "sintetico_120.csv",
    SAMPLE_DIR / "mastodon_interacciones.json",
]
OUTPUT = SAMPLE_DIR / "corrida-completa-gemma.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenera la muestra de ejemplo del dashboard con el pipeline real."
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Fuerza rule_based (sin key, sin red, determinista).",
    )
    args = parser.parse_args(argv)

    missing = [str(source) for source in SOURCES if not Path(source).exists()]
    if missing:
        print(f"ERROR: falta una fuente de muestra: {missing[0]}")
        return 1

    # --offline debe ganarle al backend de .env: run_pipeline() llama a
    # load_dotenv(), que NO sobreescribe variables ya presentes en el entorno.
    if args.offline:
        os.environ["COMMUNITYLAB_LLM_BACKEND"] = "rule_based"

    sys.path.insert(0, str(REPO_ROOT))
    from src.interface.app import process_combined_sample

    backend = os.getenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    print(f"Generando muestra con backend: {backend} ...")
    result = process_combined_sample(SOURCES, limits=[None, None, None])

    output_path = Path(OUTPUT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    resumen = result.get("resumen_comunidad", {}) or {}
    activos = result.get("activos_distribucion_generados", {}) or {}
    candidatos = activos.get("candidatos_post_linkedin") or []

    print(f"Muestra escrita en: {output_path}")
    print(f"  interacciones : {resumen.get('total_interacciones_procesadas')}")
    print(f"  candidatos    : {len(candidatos)}")
    print(f"  feedback neg. : {resumen.get('feedback_negativo')}")
    print(f"  faq           : {bool(activos.get('sugerencia_contenido_faq'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
