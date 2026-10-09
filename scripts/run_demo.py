#!/usr/bin/env python3
"""Demo runner for CommunityLab: pipeline completo sobre un dataset de ejemplo.

Uso:
    python scripts/run_demo.py [dataset.json] [--offline] [--backend X] [--model Y]

Rutas:
    Online (por defecto): usa el backend de .env (COMMUNITYLAB_LLM_BACKEND).
        Con OLLAMA_API_KEY + OLLAMA_MODEL=gemma4:31b llama a Ollama Cloud.
    Offline (--offline): fuerza rule_based, sin key, sin red, 100% determinista.

Salida: 0 = exito, 1 = el pipeline fallo (imprime el error).
El snapshot queda en storage/activos/paquete-distribucion-<fecha>.json
(gitignored) cuando no hay credenciales OCI configuradas.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from pathlib import Path

from dotenv import load_dotenv

# El campo `copy` de LinkedInPost sombrea a BaseModel; warning pre-existente,
# irrelevante para el demo.
warnings.filterwarnings(
    "ignore", message='Field name "copy".*shadows an attribute', category=UserWarning
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "sample" / "demo_fixed.json"


def _trim(text: str, limit: int = 160) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _resolve_backend(offline: bool, backend: str | None) -> str:
    if offline:
        return "rule_based"
    if backend and backend != "auto":
        return backend
    return os.getenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")


def main() -> int:
    parser = argparse.ArgumentParser(description="Corre el pipeline de CommunityLab sobre un dataset.")
    parser.add_argument("input", nargs="?", default=str(DEFAULT_INPUT), help="JSON de entrada (default: data/sample/demo_fixed.json)")
    parser.add_argument("--offline", action="store_true", help="Fuerza rule_based (sin key, sin red).")
    parser.add_argument("--backend", choices=["auto", "ollama", "openai", "gemini", "rule_based"], default="auto")
    parser.add_argument("--model", help="Modelo a usar (ej. gemma4:31b). Omite el de .env.")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    if args.model:
        os.environ["OLLAMA_MODEL"] = args.model

    backend = _resolve_backend(args.offline, args.backend)
    os.environ["COMMUNITYLAB_LLM_BACKEND"] = backend  # aplica el backend de verdad
    model = os.getenv("OLLAMA_MODEL", "n/a")
    has_key = bool(os.getenv("OLLAMA_API_KEY"))

    print("=" * 68)
    print("CommunityLab — demo del pipeline")
    print("=" * 68)
    print(f"  dataset : {args.input}")
    print(f"  backend : {backend}" + (f" (Ollama Cloud, modelo {model})" if backend == "ollama" and has_key else ""))
    if backend == "ollama" and not has_key:
        print("  aviso   : no hay OLLAMA_API_KEY en .env -> el cliente caera a modo local")
    print("-" * 68)

    if not Path(args.input).exists():
        print(f"ERROR: no existe el dataset {args.input}")
        return 1

    sys.path.insert(0, str(REPO_ROOT))
    from src.pipeline import run_pipeline  # noqa: E402

    started = time.monotonic()
    try:
        result = run_pipeline(args.input)
    except Exception as exc:  # el pipeline no debe romper, pero si rompe: visible
        print(f"ERROR: el pipeline fallo: {exc}")
        return 1
    elapsed = time.monotonic() - started

    assets = result.activos_distribucion_generados
    storage = result.almacenamiento_oci
    summary = result.resumen_comunidad

    print(f"  status  : {result.status.upper()}")
    print(f"  tiempo  : {elapsed:.1f}s")
    print("=" * 68)
    print("ACTIVOS GENERADOS")
    print("-" * 68)
    if assets.post_linkedin:
        print("  [LinkedIn]")
        print(f"    titulo : {assets.post_linkedin.titulo}")
        print(f"    copy   : {_trim(assets.post_linkedin.copy)}")
    else:
        print("  [LinkedIn]   (no generado: sin decision PUBLISH+LINKEDIN)")
    if assets.destaque_newsletter_semanal:
        print("  [Newsletter]")
        print(f"    seccion : {assets.destaque_newsletter_semanal.seccion}")
        print(f"    titular : {assets.destaque_newsletter_semanal.titular}")
        print(f"    resumen : {_trim(assets.destaque_newsletter_semanal.resumen)}")
    else:
        print("  [Newsletter] (no generado)")
    if assets.sugerencia_contenido_faq:
        print("  [FAQ]")
        print(f"    tema   : {_trim(assets.sugerencia_contenido_faq.tema)}")
    else:
        print("  [FAQ]        (no generado: sin decision CREAR_FAQ)")
    print("=" * 68)
    print("ALMACENAMIENTO")
    print("-" * 68)
    print(f"  status : {storage.status}")
    print(f"  ruta   : {storage.ruta_objeto}")
    if storage.status != "guardado_con_exito" and "storage/activos" in storage.ruta_objeto:
        print("  nota   : sin credenciales OCI -> snapshot local (gitignored)")
    print("=" * 68)
    print("RESUMEN DE LA COMUNIDAD")
    print("-" * 68)
    print(f"  interacciones : {summary.total_interacciones_procesadas}")
    print(f"  sentimiento   : {summary.sentimiento_predominante}")
    # Rule R4 (decision D-F): negative feedback routed to a human. Shown so the
    # capability is visible in the demo, not just in the JSON contract output.
    print(f"  feedback neg. : {summary.feedback_negativo} derivado(s) a atencion humana")
    topics = summary.temas_principales
    if topics:
        shown = topics[:12]
        print(f"  temas         : {', '.join(shown)}" + (f" (+{len(topics) - len(shown)} mas)" if len(topics) > 12 else ""))
    print("=" * 68)
    print("Demo OK. Los activos listos para publicar quedaron arriba.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
