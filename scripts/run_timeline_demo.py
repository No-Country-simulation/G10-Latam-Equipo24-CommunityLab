#!/usr/bin/env python3
"""Demo runner de evolución semanal para CommunityLab.

Uso:
    python scripts/run_timeline_demo.py [semana01.csv semana02.csv ...]
                                        [--dir data/sample/timeline]
                                        [--offline] [--backend X] [--model Y]

A diferencia de scripts/run_demo.py, que MERGEA todas las fuentes en un único
lote, este runner corre el pipeline UNA VEZ POR SEMANA y muestra la evolución
semana a semana: volumen, composición de tipos, sentimiento, temas y activos
generados. Sirve para ver cómo cambia el resultado a medida que la comunidad
madura, algo que el merge de run_demo.py oculta.

Rutas:
    - Posicionales: si se pasan una o más rutas .csv, cada una se corre como una
      semana, respetando el orden indicado.
    - --dir: si no hay rutas posicionales, se toman los `semana*.csv` del
      directorio (default: data/sample/timeline) ordenados por nombre.

Backend (misma resolución que run_demo.py):
    Offline (--offline): fuerza rule_based, sin key, sin red, determinista.
    Online (por defecto): --backend > COMMUNITYLAB_LLM_BACKEND del .env.

Salida: 0 = al menos una semana corrió bien; 1 = fallaron todas o una ruta no
existe. El snapshot quedará en storage/activos/paquete-distribucion-<fecha>.json
(gitignored) cuando no haya credenciales OCI configuradas.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

# El campo `copy` de LinkedInPost sombrea a BaseModel; warning pre-existente,
# irrelevante para el demo (mismo filtro que run_demo.py).
warnings.filterwarnings(
    "ignore", message='Field name "copy".*shadows an attribute', category=UserWarning
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
# Se agregan la raíz del repositorio (para el paquete src y scripts) y el
# directorio de scripts (para importar generate_timeline por nombre) antes de
# importar módulos del repo.
for _path in (str(REPO_ROOT), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# Se reutiliza el conteo por tipo del generador de la línea de tiempo en lugar
# de duplicar la lógica de composición.
from generate_timeline import _mezcla_por_tipo  # noqa: E402

DEFAULT_DIR = REPO_ROOT / "data" / "sample" / "timeline"
# Marcador para un activo ausente o un valor no disponible al imprimir.
_EMPTY = "—"
# Tipos que cuentan como "dudas" y como "logros+testimonios" en la evolución.
_TIPOS_DUDA = ("pregunta_tecnica",)
_TIPOS_LOGRO = ("testimonio", "logro")


def _resolve_backend(offline: bool, backend: Optional[str]) -> str:
    """Resuelve el backend activo (misma lógica que run_demo.py)."""
    if offline:
        return "rule_based"
    if backend and backend != "auto":
        return backend
    return os.getenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")


def descubrir_semanas(
    rutas: Optional[List[str]] = None, directorio: Path = DEFAULT_DIR
) -> List[Path]:
    """Devuelve la lista de CSV semanales a procesar.

    - Con rutas explícitas: respeta esas rutas, en el orden indicado.
    - Sin rutas: todos los `semana*.csv` del directorio, ordenados por nombre.
    """
    if rutas:
        return [Path(ruta) for ruta in rutas]
    return sorted(Path(directorio).glob("semana*.csv"), key=lambda p: p.name)


def leer_filas(path: Path) -> List[Dict[str, str]]:
    """Lee un CSV semanal y devuelve sus filas como diccionarios (utf-8-sig)."""
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def composicion(filas: List[Dict[str, str]]) -> Dict[str, int]:
    """Cuenta filas por `tipo` reutilizando generate_timeline._mezcla_por_tipo."""
    return _mezcla_por_tipo(filas)


def _porcentaje(parte: int, total: int) -> float:
    """Porcentaje seguro (0.0 cuando no hay filas)."""
    return (parte / total * 100.0) if total else 0.0


def _fila_base(path: Path, filas_csv: List[Dict[str, str]]) -> Dict:
    """Arma la fila de resultado de una semana antes de correr el pipeline."""
    mezcla = composicion(filas_csv)
    total = len(filas_csv)
    return {
        "semana": path.stem,
        "archivo": path.name,
        "filas": total,
        "mezcla": mezcla,
        "pct_dudas": _porcentaje(sum(mezcla.get(t, 0) for t in _TIPOS_DUDA), total),
        "pct_logros": _porcentaje(sum(mezcla.get(t, 0) for t in _TIPOS_LOGRO), total),
        "ok": False,
        "error": None,
        "sentimiento": None,
        "temas": [],
        "degradados": 0,
        "linkedin": None,
        "newsletter": None,
        "faq": None,
    }


def _llenar_con_resultado(fila: Dict, result) -> None:
    """Copia el resultado del pipeline en la fila de la semana."""
    summary = result.resumen_comunidad
    assets = result.activos_distribucion_generados
    fila["ok"] = True
    fila["sentimiento"] = summary.sentimiento_predominante
    fila["temas"] = list(summary.temas_principales)
    fila["degradados"] = summary.analisis_degradados
    fila["linkedin"] = assets.post_linkedin.titulo if assets.post_linkedin else None
    fila["newsletter"] = (
        assets.destaque_newsletter_semanal.titular
        if assets.destaque_newsletter_semanal
        else None
    )
    fila["faq"] = (
        assets.sugerencia_contenido_faq.tema
        if assets.sugerencia_contenido_faq
        else None
    )


def correr_timeline(
    rutas: Optional[List[str]],
    directorio: Path,
    backend: str,
) -> List[Dict]:
    """Corre el pipeline semana por semana y devuelve una fila por semana.

    Si el pipeline o la lectura de una semana falla, esa semana queda marcada
    con `ok=False` y su `error`, sin abortar el resto. Un KeyboardInterrupt se
    propaga hacia arriba (lo maneja main con salida 0).
    """
    # Import tardío: mantiene liviano el import del módulo para los tests.
    from src.pipeline import run_pipeline  # noqa: E402

    resultados: List[Dict] = []
    for path in descubrir_semanas(rutas, directorio):
        try:
            filas_csv = leer_filas(path)
        except Exception as exc:  # noqa: BLE001 - se reporta y se sigue
            fila = _fila_base(path, [])
            fila["error"] = str(exc)
            resultados.append(fila)
            continue

        fila = _fila_base(path, filas_csv)
        try:
            # Una semana = un lote: se pasa como lista de una sola fuente para
            # que el loader NO mergee semanas distintas.
            result = run_pipeline([str(path)])
        except Exception as exc:  # noqa: BLE001 - el pipeline no debe abortar todo
            fila["error"] = str(exc)
            resultados.append(fila)
            continue

        _llenar_con_resultado(fila, result)
        resultados.append(fila)
    return resultados


def _detalle_composicion(fila: Dict) -> str:
    """Texto compacto 'tipo=cantidad (%)' para la composición de la semana."""
    if not fila["filas"]:
        return "sin filas"
    return " | ".join(
        f"{tipo}={cantidad} ({cantidad / fila['filas'] * 100:.1f}%)"
        for tipo, cantidad in sorted(fila["mezcla"].items())
    )


def _imprimir_semana(fila: Dict) -> None:
    """Imprime el bloque de una semana."""
    print("-" * 68)
    print(f"SEMANA {fila['semana']}  ({fila['archivo']})")
    print("-" * 68)
    print(f"  filas      : {fila['filas']}")
    print(f"  composicion: {_detalle_composicion(fila)}")
    print(
        f"  dudas      : {fila['pct_dudas']:.1f}%"
        f"  |  logros+testimonios: {fila['pct_logros']:.1f}%"
    )
    if fila["error"]:
        print(f"  ERROR      : el pipeline fallo: {fila['error']}")
        return
    print(f"  sentimiento: {fila['sentimiento']}")
    temas = fila["temas"]
    print(f"  temas      : {', '.join(temas) if temas else _EMPTY}")
    print(f"  degradados : {fila['degradados']}")
    print(f"  LinkedIn   : {fila['linkedin'] or _EMPTY}")
    print(f"  Newsletter : {fila['newsletter'] or _EMPTY}")
    print(f"  FAQ        : {fila['faq'] or _EMPTY}")


def _imprimir_tabla(resultados: List[Dict]) -> None:
    """Imprime la tabla comparativa de evolución entre semanas."""
    headers = [
        "Semana",
        "Filas",
        "%Dudas",
        "%Logros+Test",
        "Sentimiento",
        "LinkedIn(S/N)",
        "FAQ(S/N)",
    ]
    rows: List[List[str]] = []
    for fila in resultados:
        if fila["error"]:
            rows.append(
                [
                    fila["semana"],
                    str(fila["filas"]),
                    f"{fila['pct_dudas']:.1f}",
                    f"{fila['pct_logros']:.1f}",
                    "ERROR",
                    "—",
                    "—",
                ]
            )
            continue
        rows.append(
            [
                fila["semana"],
                str(fila["filas"]),
                f"{fila['pct_dudas']:.1f}",
                f"{fila['pct_logros']:.1f}",
                fila["sentimiento"] or _EMPTY,
                "S" if fila["linkedin"] else "N",
                "S" if fila["faq"] else "N",
            ]
        )

    widths = [
        max([len(headers[i])] + [len(row[i]) for row in rows])
        for i in range(len(headers))
    ]

    def _linea(row: List[str]) -> str:
        return "  ".join(valor.ljust(widths[i]) for i, valor in enumerate(row))

    print(_linea(headers))
    print("  ".join("-" * ancho for ancho in widths))
    for row in rows:
        print(_linea(row))


def main(argv: Optional[List[str]] = None) -> int:
    """Punto de entrada del runner semanal. Devuelve el código de salida."""
    parser = argparse.ArgumentParser(
        description="Corre el pipeline semana por semana y muestra la evolución."
    )
    parser.add_argument(
        "rutas",
        nargs="*",
        help="CSV de semanas (opcional; si no, se usan los semana*.csv de --dir).",
    )
    parser.add_argument(
        "--dir",
        dest="directorio",
        default=str(DEFAULT_DIR),
        help=f"Directorio con semana*.csv (default: {DEFAULT_DIR}).",
    )
    parser.add_argument(
        "--offline", action="store_true", help="Fuerza rule_based (sin key, sin red)."
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "ollama", "openai", "gemini", "rule_based"],
        default="auto",
    )
    parser.add_argument(
        "--model", help="Modelo a usar (ej. gemma4:31b). Setea OLLAMA_MODEL."
    )
    args = parser.parse_args(argv)

    load_dotenv(REPO_ROOT / ".env")
    if args.model:
        os.environ["OLLAMA_MODEL"] = args.model

    backend = _resolve_backend(args.offline, args.backend)
    os.environ["COMMUNITYLAB_LLM_BACKEND"] = backend  # aplica el backend de verdad

    directorio = Path(args.directorio)
    semanas = descubrir_semanas(args.rutas, directorio)

    print("=" * 68)
    print("CommunityLab — evolución semanal del pipeline")
    print("=" * 68)
    print(
        "  semanas : "
        + (", ".join(str(path) for path in semanas) if semanas else "(ninguna)")
    )
    print(f"  backend : {backend}")
    print("-" * 68)

    if not semanas:
        print(f"ERROR: no se encontraron archivos semana*.csv en {directorio}")
        return 1

    faltantes = [path for path in semanas if not path.exists()]
    if faltantes:
        print(f"ERROR: no existe la ruta {faltantes[0]}")
        return 1

    try:
        resultados = correr_timeline(semanas, directorio, backend)
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario; salida 0.")
        return 0

    for fila in resultados:
        _imprimir_semana(fila)

    print("=" * 68)
    print("EVOLUCIÓN SEMANAL")
    print("=" * 68)
    _imprimir_tabla(resultados)

    exitosas = sum(1 for fila in resultados if fila["ok"])
    if exitosas == 0:
        print("Ninguna semana corrió correctamente.")
        return 1
    print(f"Semanas exitosas: {exitosas}/{len(resultados)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
