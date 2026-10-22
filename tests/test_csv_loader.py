"""Tests para el loader de ingesta CSV y el merge de lotes (Escalón 1).

Cubre el Escalón 1 de ingesta: soporte de CSV (sin dependencias nuevas) y la
ingesta de varias fuentes en una sola corrida (merge de lotes en
src/ingest/loader.py). El estilo sigue a tests/test_input_loader.py.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.domain.models import InputBatch, InputMessage
from src.ingest.csv_loader import CSVInputLoader
from src.ingest.loader import load_batch
from src.oci.storage import OCI_CREDENTIAL_ENV
from src.pipeline import run_pipeline

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MUESTRA = FIXTURES / "muestra.csv"
MUESTRA_EN = FIXTURES / "muestra_en.csv"
REPO_ROOT = Path(__file__).resolve().parent.parent


def test_load_csv_happy_path():
    msgs = CSVInputLoader().load(str(MUESTRA))
    assert len(msgs) == 3
    assert all(isinstance(msg, InputMessage) for msg in msgs)
    assert msgs[0].autor == "Mariana Souza"
    assert msgs[0].canal == "#general"
    assert msgs[0].tipo == "testimonio"
    assert msgs[0].texto == "Conseguí mi primer empleo como desarrolladora."


def test_load_batch_envelope_desde_columnas_del_csv():
    batch = CSVInputLoader().load_batch(str(MUESTRA))
    assert isinstance(batch, InputBatch)
    assert batch.origen_comunidad == "Comunidad_Tech"
    assert batch.periodo_referencia == "Periodo_2026-01"


def test_encabezado_faltante_lanza_value_error(tmp_path):
    archivo = tmp_path / "sin_texto.csv"
    archivo.write_text(
        "autor,canal,tipo\nAna,#general,testimonio\n", encoding="utf-8"
    )
    with pytest.raises(ValueError) as exc:
        CSVInputLoader().load(str(archivo))
    assert "texto" in str(exc.value)


def test_csv_vacio_sin_filas_lanza_value_error(tmp_path):
    vacio = tmp_path / "vacio.csv"
    vacio.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        CSVInputLoader().load(str(vacio))

    solo_encabezado = tmp_path / "solo_encabezado.csv"
    solo_encabezado.write_text("autor,canal,tipo,texto\n", encoding="utf-8")
    with pytest.raises(ValueError):
        CSVInputLoader().load(str(solo_encabezado))


def test_alias_en_ingles_resueltos_por_el_normalizer():
    msgs = CSVInputLoader().load(str(MUESTRA_EN))
    assert msgs[0].autor == "Bob Johnson"
    assert msgs[0].canal == "#ayuda"
    assert msgs[0].texto == (
        "¿Cómo conecto el backend con una base de datos en la nube?"
    )
    # "pregunta tecnica" -> forma canónica "pregunta_tecnica".
    assert msgs[0].tipo == "pregunta_tecnica"


def test_url_maps_a_metadata():
    msgs = CSVInputLoader().load(str(MUESTRA))
    assert msgs[0].metadata["url"] == "https://example.com/empleo"
    assert msgs[1].timestamp == "2026-01-11T14:30:00Z"


def test_default_de_envelope_sin_columnas(tmp_path):
    archivo = tmp_path / "sin_envelope.csv"
    archivo.write_text(
        "autor,canal,tipo,texto\n"
        "Ana,#general,testimonio,Hola a todos.\n",
        encoding="utf-8",
    )
    batch = CSVInputLoader().load_batch(str(archivo))
    assert batch.origen_comunidad == "CSV-sin_envelope"
    assert batch.periodo_referencia == "CSV-sin_envelope"


def test_override_del_constructor_gana_a_la_columna():
    batch = CSVInputLoader(
        origen_comunidad="Mi_Comunidad", periodo_referencia="Semana_10"
    ).load_batch(str(MUESTRA))
    assert batch.origen_comunidad == "Mi_Comunidad"
    assert batch.periodo_referencia == "Semana_10"


def test_despacho_por_sufijo_csv_y_json(tmp_path):
    json_path = tmp_path / "lote.json"
    json_path.write_text(
        json.dumps(
            {
                "origen_comunidad": "Discord_Grupo_ONE_G10",
                "periodo_referencia": "Semana_04",
                "interacciones": [
                    {
                        "autor": "Mariana",
                        "canal": "#logros",
                        "tipo": "testimonio",
                        "texto": "Conseguí mi primer trabajo.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    batch_json = load_batch(str(json_path))
    assert batch_json.origen_comunidad == "Discord_Grupo_ONE_G10"
    assert batch_json.periodo_referencia == "Semana_04"
    assert len(batch_json.interacciones) == 1

    batch_csv = load_batch(str(MUESTRA))
    assert len(batch_csv.interacciones) == 3


def test_formato_no_soportado_lanza_value_error(tmp_path):
    txt = tmp_path / "datos.txt"
    txt.write_text("hola", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        load_batch(str(txt))
    mensaje = str(exc.value)
    assert ".csv" in mensaje and ".json" in mensaje


def test_merge_json_mas_csv(tmp_path):
    json_path = tmp_path / "lote.json"
    json_path.write_text(
        json.dumps(
            {
                "origen_comunidad": "Discord_Grupo_ONE_G10",
                "periodo_referencia": "Semana_04",
                "interacciones": [
                    {
                        "autor": "Mariana",
                        "canal": "#logros",
                        "tipo": "testimonio",
                        "texto": "Primer mensaje.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    batch = load_batch([str(json_path), str(MUESTRA)])

    # Concatenación en orden: el mensaje del JSON va primero.
    assert len(batch.interacciones) == 4
    assert batch.interacciones[0].texto == "Primer mensaje."
    # Orígenes únicos no vacíos, orden alfabético, unidos con " + ".
    assert batch.origen_comunidad == "Comunidad_Tech + Discord_Grupo_ONE_G10"
    # Dos periodos distintos -> "combinado".
    assert batch.periodo_referencia == "combinado"


def test_merge_periodo_uniforme_se_conserva(tmp_path):
    json_path = tmp_path / "lote.json"
    json_path.write_text(
        json.dumps(
            {
                "origen_comunidad": "Comunidad_Tech",
                "periodo_referencia": "Periodo_2026-01",
                "interacciones": [
                    {
                        "autor": "Mariana",
                        "canal": "#logros",
                        "tipo": "testimonio",
                        "texto": "Primer mensaje.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    batch = load_batch([str(json_path), str(MUESTRA)])
    assert batch.periodo_referencia == "Periodo_2026-01"


def test_merge_override_explicito(tmp_path):
    json_path = tmp_path / "lote.json"
    json_path.write_text(
        json.dumps(
            {
                "origen_comunidad": "Discord_Grupo_ONE_G10",
                "periodo_referencia": "Semana_04",
                "interacciones": [
                    {
                        "autor": "Mariana",
                        "canal": "#logros",
                        "tipo": "testimonio",
                        "texto": "Primer mensaje.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    batch = load_batch(
        [str(json_path), str(MUESTRA)],
        origen="Batch_Consolidado",
        periodo="Semana_12",
    )
    assert batch.origen_comunidad == "Batch_Consolidado"
    assert batch.periodo_referencia == "Semana_12"


def test_generador_determinista(tmp_path):
    """Misma semilla -> mismo dataset; semilla distinta -> distinto dataset."""
    base_cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "generate_dataset.py"),
        "--filas", "10",
    ]
    salida_a = tmp_path / "a.csv"
    salida_b = tmp_path / "b.csv"
    salida_c = tmp_path / "c.csv"
    subprocess.run(
        base_cmd + ["--salida", str(salida_a), "--semilla", "42"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        base_cmd + ["--salida", str(salida_b), "--semilla", "42"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        base_cmd + ["--salida", str(salida_c), "--semilla", "43"],
        check=True,
        capture_output=True,
        text=True,
    )
    bytes_a = salida_a.read_bytes()
    assert salida_b.read_bytes() == bytes_a
    assert salida_c.read_bytes() != bytes_a


def test_dataset_generado_y_pipeline_offline(tmp_path, monkeypatch):
    """El dataset generado tiene filas y el pipeline lo procesa offline.

    Corre el generador (CLI real) y luego el pipeline con backend rule_based,
    sin red y sin credenciales OCI; el snapshot local cae en tmp_path porque el
    cwd se aísla (mismo patrón que tests/test_pipeline.py).
    """
    salida = tmp_path / "sintetico.csv"
    resultado = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "generate_dataset.py"),
            "--salida", str(salida),
            "--filas", "20",
            "--semilla", "7",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0
    assert salida.is_file()
    with salida.open(encoding="utf-8") as handle:
        filas = list(csv.DictReader(handle))
    assert len(filas) == 20
    assert all(
        fila["autor"] and fila["canal"] and fila["tipo"] and fila["texto"]
        for fila in filas
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COMMUNITYLAB_LLM_BACKEND", "rule_based")
    for var in OCI_CREDENTIAL_ENV:
        monkeypatch.delenv(var, raising=False)

    output = run_pipeline(str(salida))
    assert output.status == "exito"
    assert output.resumen_comunidad.total_interacciones_procesadas == 20
