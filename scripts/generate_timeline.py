#!/usr/bin/env python3
"""Generador de línea de tiempo semanal sintética para CommunityLab.

Uso:
    python scripts/generate_timeline.py [--semanas 4] [--base-filas 60]
                                        [--incremento 30] [--semilla 42]
                                        [--salida-dir data/sample/timeline]

Genera una serie de archivos CSV (semana01.csv, semana02.csv, ...) que
representan la evolución de una comunidad a lo largo de varias semanas. Cada
semana crece en volumen (base_filas + incremento por semana) y madura: baja la
proporción de dudas técnicas (tipo pregunta_tecnica) y sube la de testimonios y
logros (tipo testimonio o logro). El feedback positivo y negativo se mantiene
constante porque es material de la regla R4/DERIVAR.

Los textos y las canales no se duplican: se reutilizan los pools definidos en
scripts/generate_dataset.py (importados por nombre). El esquema de salida es el
mismo: encabezados autor,canal,tipo,texto.

Determinismo: cada semana usa random.Random(semilla + indice_semana), nunca el
random global; la misma semilla y los mismos argumentos producen siempre los
mismos CSV. Sin dependencias externas (solo stdlib).
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
# Se agrega la raíz del repositorio para poder importar el paquete scripts.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_dataset import (  # noqa: E402
    AUTORES,
    _HEADERS,
    _POOLS,
)

DEFAULT_SEMANAS = 4
DEFAULT_BASE_FILAS = 60
DEFAULT_INCREMENTO = 30
DEFAULT_SEMILLA = 42
DEFAULT_SALIDA_DIR = REPO_ROOT / "data" / "sample" / "timeline"

# Sesgo de maduración por grupo. Cada multiplicador interpola linealmente entre
# el valor de la primera semana y el de la última (t = 0 -> 1).
#   learning    (dudas técnicas): 2.0 -> 0.6  (baja con la madurez)
#   achievement (testimonios/logros): 0.5 -> 2.0  (sube con la madurez)
#   rest        (discusion/feedback): 1.0 constante
_MULTIPLICADORES = {
    "learning": (2.0, 0.6),
    "achievement": (0.5, 2.0),
    "rest": (1.0, 1.0),
}


def _clasificar_grupo(tipo: str) -> str:
    """Clasifica un tipo de mensaje en su grupo de maduración.

    - pregunta_tecnica -> learning
    - testimonio / logro -> achievement
    - el resto (discusion, feedback) -> rest
    """
    if tipo == "pregunta_tecnica":
        return "learning"
    if tipo in ("testimonio", "logro"):
        return "achievement"
    return "rest"


def _multiplicador_grupo(grupo: str, indice_semana: int, n_semanas: int) -> float:
    """Interpola el multiplicador del grupo para la semana dada.

    indice_semana es 0-indexado (0 = primera semana). Con una sola semana el
    factor temporal t queda en 0 para evitar dividir por cero.
    """
    inicio, fin = _MULTIPLICADORES[grupo]
    if n_semanas <= 1:
        t = 0.0
    else:
        t = indice_semana / (n_semanas - 1)
    return inicio + (fin - inicio) * t


def _pesos_efectivos(indice_semana: int, n_semanas: int) -> List[float]:
    """Calcula el peso efectivo de cada pool: peso original x multiplicador."""
    pesos = []
    for peso, _canal, tipo, _textos in _POOLS:
        grupo = _clasificar_grupo(tipo)
        pesos.append(peso * _multiplicador_grupo(grupo, indice_semana, n_semanas))
    return pesos


def generar_semana(
    indice_semana: int,
    filas: int,
    semilla: int,
    n_semanas: int,
) -> List[dict]:
    """Genera las filas (dicts) de una semana.

    indice_semana es 0-indexado (0 = primera semana). El generador aleatorio es
    random.Random(semilla + indice_semana), de modo que la semana es
    reproducible de forma aislada. El orden de extracción del RNG (pool, autor,
    texto) replica el de generate_dataset.generar.
    """
    rng = random.Random(semilla + indice_semana)
    pesos = _pesos_efectivos(indice_semana, n_semanas)
    generadas = []
    for _ in range(filas):
        _peso, canal, tipo, textos = rng.choices(_POOLS, weights=pesos)[0]
        generadas.append(
            {
                "autor": rng.choice(AUTORES),
                "canal": canal,
                "tipo": tipo,
                "texto": rng.choice(textos),
            }
        )
    return generadas


def generar_timeline(
    semanas: int,
    base_filas: int,
    incremento: int,
    semilla: int,
) -> Dict[int, List[dict]]:
    """Genera la línea de tiempo completa.

    Devuelve un diccionario {numero_de_semana: filas}, con la clave en el rango
    1..semanas. La cantidad de filas de la semana i (1-indexada) es
    base_filas + (i - 1) * incremento, para que la comunidad crezca en volumen
    a medida que avanza la serie.
    """
    timeline: Dict[int, List[dict]] = {}
    for i in range(1, semanas + 1):
        filas = base_filas + (i - 1) * incremento
        timeline[i] = generar_semana(i - 1, filas, semilla, semanas)
    return timeline


def _escribir_semana(destino: Path, filas: List[dict]) -> None:
    """Escribe un CSV semanal con el esquema de ingesta."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_HEADERS)
        writer.writeheader()
        writer.writerows(filas)


def _mezcla_por_tipo(filas: List[dict]) -> Dict[str, int]:
    """Cuenta cuántas filas hay de cada tipo."""
    conteo: Dict[str, int] = {}
    for fila in filas:
        conteo[fila["tipo"]] = conteo.get(fila["tipo"], 0) + 1
    return conteo


def _imprimir_resumen(timeline: Dict[int, List[dict]], salida_dir: Path) -> None:
    """Imprime la cantidad de filas y la mezcla de tipos por semana."""
    print(f"Línea de tiempo generada en: {salida_dir}")
    for numero_semana in sorted(timeline):
        filas = timeline[numero_semana]
        total = len(filas)
        mezcla = _mezcla_por_tipo(filas)
        detalle = " | ".join(
            f"{tipo}={cantidad} ({cantidad / total * 100:.1f}%)"
            for tipo, cantidad in sorted(mezcla.items())
        )
        print(f"  semana {numero_semana:02d}: {total} filas -> {detalle}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera una línea de tiempo semanal sintética para CommunityLab."
    )
    parser.add_argument(
        "--semanas",
        type=int,
        default=DEFAULT_SEMANAS,
        help=f"Cantidad de semanas a generar (default: {DEFAULT_SEMANAS})",
    )
    parser.add_argument(
        "--base-filas",
        type=int,
        default=DEFAULT_BASE_FILAS,
        help=f"Filas de la primera semana (default: {DEFAULT_BASE_FILAS})",
    )
    parser.add_argument(
        "--incremento",
        type=int,
        default=DEFAULT_INCREMENTO,
        help=f"Filas que se suman por semana (default: {DEFAULT_INCREMENTO})",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=DEFAULT_SEMILLA,
        help=f"Semilla base para random.Random (default: {DEFAULT_SEMILLA})",
    )
    parser.add_argument(
        "--salida-dir",
        default=str(DEFAULT_SALIDA_DIR),
        help=f"Directorio de salida (default: {DEFAULT_SALIDA_DIR})",
    )
    args = parser.parse_args()

    salida_dir = Path(args.salida_dir)
    timeline = generar_timeline(
        semanas=args.semanas,
        base_filas=args.base_filas,
        incremento=args.incremento,
        semilla=args.semilla,
    )

    for numero_semana, filas in timeline.items():
        destino = salida_dir / f"semana{numero_semana:02d}.csv"
        _escribir_semana(destino, filas)

    _imprimir_resumen(timeline, salida_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
