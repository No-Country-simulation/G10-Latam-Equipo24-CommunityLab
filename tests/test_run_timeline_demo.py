"""Tests del runner de evolución semanal (scripts/run_timeline_demo.py).

Cubren el descubrimiento de semanas, el conteo de composición por tipo, una
corrida funcional de tres semanas y el smoke test del CLI. El pipeline se aísla
con un cwd temporal (escribe el snapshot local cuando no hay credenciales OCI) y
se fuerza el backend rule_based: sin red y sin flakiness.
"""

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_timeline_demo import (  # noqa: E402
    composicion,
    correr_timeline,
    descubrir_semanas,
    leer_filas,
    main,
)

HEADERS = ("autor", "canal", "tipo", "texto")


def _escribir_semana(path, filas):
    """Escribe un CSV semanal con el esquema de ingesta."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(filas)
    return path


def _semana_de_ejemplo(tag, dudas=2, logros=2, discusiones=1):
    """Genera filas determinísticas con dudas, logros y discusiones."""
    filas = []
    for i in range(dudas):
        filas.append(
            {
                "autor": f"Autora{i}",
                "canal": "ayuda",
                "tipo": "pregunta_tecnica",
                "texto": f"¿Cómo hago esto? error {tag}-{i}",
            }
        )
    for i in range(logros):
        filas.append(
            {
                "autor": f"Logrado{i}",
                "canal": "general",
                "tipo": "testimonio",
                "texto": f"Logré un nuevo trabajo, gracias! {tag}-{i}",
            }
        )
    for i in range(discusiones):
        filas.append(
            {
                "autor": f"Charlista{i}",
                "canal": "feedback",
                "tipo": "discusion",
                "texto": f"Comentario de la comunidad {tag}-{i}",
            }
        )
    return filas


def test_descubrir_semanas_ordena_por_nombre(tmp_path):
    for nombre in ("semana03.csv", "semana01.csv", "otro.csv", "semana02.csv"):
        (tmp_path / nombre).write_text("", encoding="utf-8")

    encontradas = [path.name for path in descubrir_semanas(directorio=tmp_path)]

    assert encontradas == ["semana01.csv", "semana02.csv", "semana03.csv"]


def test_descubrir_semanas_respeta_rutas_explicitas(tmp_path):
    primero = tmp_path / "semana02.csv"
    segundo = tmp_path / "semana01.csv"
    primero.write_text("", encoding="utf-8")
    segundo.write_text("", encoding="utf-8")

    encontradas = descubrir_semanas([str(segundo), str(primero)], tmp_path)

    assert encontradas == [segundo, primero]


def test_composicion_cuenta_dudas_y_logros(tmp_path):
    ruta = _escribir_semana(
        tmp_path / "semana01.csv", _semana_de_ejemplo("x", dudas=3, logros=2)
    )

    filas = leer_filas(ruta)
    mezcla = composicion(filas)

    assert len(filas) == 6
    assert mezcla["pregunta_tecnica"] == 3
    assert mezcla["testimonio"] + mezcla.get("logro", 0) == 2


def test_correr_timeline_devuelve_una_fila_por_semana(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    for numero in range(1, 4):
        _escribir_semana(
            tmp_path / f"semana{numero:02d}.csv", _semana_de_ejemplo(numero)
        )

    resultados = correr_timeline([], tmp_path, "rule_based")

    assert len(resultados) == 3
    assert all(fila["ok"] for fila in resultados)
    assert [fila["semana"] for fila in resultados] == [
        "semana01",
        "semana02",
        "semana03",
    ]
    assert all(fila["filas"] > 0 for fila in resultados)


def test_main_cli_smoke(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    _escribir_semana(tmp_path / "semana01.csv", _semana_de_ejemplo(1))
    _escribir_semana(tmp_path / "semana02.csv", _semana_de_ejemplo(2))
    monkeypatch.setattr(
        sys, "argv", ["run_timeline_demo.py", "--offline", "--dir", str(tmp_path)]
    )

    assert main() == 0


def test_main_cli_ruta_inexistente(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    inexistente = tmp_path / "no-existe.csv"
    monkeypatch.setattr(
        sys, "argv", ["run_timeline_demo.py", "--offline", str(inexistente)]
    )

    assert main() == 1
