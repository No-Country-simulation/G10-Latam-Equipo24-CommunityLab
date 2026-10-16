"""Tests del generador de línea de tiempo semanal (scripts/generate_timeline.py).

Cubren determinismo, crecimiento de volumen, la tendencia de maduración
(baja pregunta_tecnica, sube testimonio+logro), el esquema de las filas y la
interfaz de línea de comandos. Todos usan semillas fijas: no son flaky.
"""

import csv
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SCRIPT = SCRIPTS_DIR / "generate_timeline.py"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from generate_timeline import (  # noqa: E402
    _HEADERS,
    generar_semana,
    generar_timeline,
)

CANALES_VALIDOS = {"general", "ayuda", "feedback"}
TIPOS_VALIDOS = {"testimonio", "logro", "pregunta_tecnica", "discusion", "feedback"}
CAMPOS = {"autor", "canal", "tipo", "texto"}


def _mezcla_por_tipo(filas):
    """Devuelve un conteo {tipo: cantidad} para las filas dadas."""
    conteo = {}
    for fila in filas:
        conteo[fila["tipo"]] = conteo.get(fila["tipo"], 0) + 1
    return conteo


def test_determinismo_misma_semilla_produce_mismas_filas():
    a = generar_timeline(semanas=4, base_filas=50, incremento=20, semilla=7)
    b = generar_timeline(semanas=4, base_filas=50, incremento=20, semilla=7)
    assert a == b


def test_determinismo_semilla_distinta_cambia_las_filas():
    a = generar_timeline(semanas=3, base_filas=40, incremento=10, semilla=1)
    b = generar_timeline(semanas=3, base_filas=40, incremento=10, semilla=2)
    assert a != b


def test_generar_semana_es_determinista():
    a = generar_semana(indice_semana=1, filas=30, semilla=99, n_semanas=4)
    b = generar_semana(indice_semana=1, filas=30, semilla=99, n_semanas=4)
    assert a == b
    assert len(a) == 30


def test_crecimiento_de_volumen_entre_semanas():
    timeline = generar_timeline(semanas=4, base_filas=60, incremento=30, semilla=42)
    assert len(timeline[1]) == 60
    assert len(timeline[4]) == 60 + 3 * 30
    assert len(timeline[4]) > len(timeline[1])
    cantidades = [len(timeline[i]) for i in sorted(timeline)]
    assert cantidades == sorted(cantidades)


def test_tendencia_de_madurez_con_muestra_grande():
    timeline = generar_timeline(semanas=4, base_filas=300, incremento=30, semilla=42)
    primera, ultima = timeline[1], timeline[4]
    mezcla_primera = _mezcla_por_tipo(primera)
    mezcla_ultima = _mezcla_por_tipo(ultima)

    tecnica_primera = mezcla_primera.get("pregunta_tecnica", 0) / len(primera)
    tecnica_ultima = mezcla_ultima.get("pregunta_tecnica", 0) / len(ultima)
    assert tecnica_ultima < tecnica_primera

    logros_primera = (
        mezcla_primera.get("testimonio", 0) + mezcla_primera.get("logro", 0)
    ) / len(primera)
    logros_ultima = (
        mezcla_ultima.get("testimonio", 0) + mezcla_ultima.get("logro", 0)
    ) / len(ultima)
    assert logros_ultima > logros_primera


def test_esquema_de_cada_fila():
    timeline = generar_timeline(semanas=3, base_filas=25, incremento=10, semilla=42)
    for filas in timeline.values():
        for fila in filas:
            assert set(fila.keys()) == CAMPOS
            assert fila["texto"].strip() != ""
            assert fila["autor"]
            assert fila["canal"] in CANALES_VALIDOS
            assert fila["tipo"] in TIPOS_VALIDOS


def test_cli_crea_archivos_por_semana(tmp_path):
    resultado = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--semanas",
            "3",
            "--salida-dir",
            str(tmp_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr

    esperadas_por_semana = {1: 60, 2: 90, 3: 120}
    for numero_semana, esperadas in esperadas_por_semana.items():
        archivo = tmp_path / f"semana{numero_semana:02d}.csv"
        assert archivo.exists()
        with archivo.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames == list(_HEADERS)
            filas = list(reader)
        assert len(filas) == esperadas
