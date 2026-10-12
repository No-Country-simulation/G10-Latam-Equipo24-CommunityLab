import json

import pytest

from src.ingest.csv_loader import cargar_csv
from src.ingest.loader import load_batch

CSV_OK = (
    "autor,canal,tipo,texto\n"
    "ana,discord,testimonio,Logré mi primer empleo\n"
    "luis,discord,pregunta_tecnica,¿Cómo hago un merge?\n"
)


def test_cargar_csv_valido(tmp_path):
    ruta = tmp_path / "datos.csv"
    ruta.write_text(CSV_OK, encoding="utf-8")
    payload = cargar_csv(ruta)
    assert payload["origen_comunidad"] == "CSV_datos"
    assert [i["tipo"] for i in payload["interacciones"]] == ["testimonio", "pregunta_tecnica"]
    assert payload["interacciones"][0]["id"] == "datos_2"


def test_cargar_csv_con_bom(tmp_path):
    ruta = tmp_path / "bom.csv"
    ruta.write_text(CSV_OK, encoding="utf-8-sig")
    assert len(cargar_csv(ruta)["interacciones"]) == 2


def test_csv_omite_filas_sin_texto(tmp_path):
    ruta = tmp_path / "vacias.csv"
    ruta.write_text("autor,canal,tipo,texto\nana,discord,otro,\n", encoding="utf-8")
    assert cargar_csv(ruta)["interacciones"] == []


def test_csv_columnas_faltantes(tmp_path):
    ruta = tmp_path / "mal.csv"
    ruta.write_text("autor,texto\nana,hola\n", encoding="utf-8")
    with pytest.raises(ValueError, match="faltan"):
        cargar_csv(ruta)


def test_csv_tipo_invalido(tmp_path):
    ruta = tmp_path / "tipo.csv"
    ruta.write_text("autor,canal,tipo,texto\nana,discord,spam,hola\n", encoding="utf-8")
    with pytest.raises(ValueError, match="línea 2"):
        cargar_csv(ruta)


def test_load_batch_mezcla_json_y_csv(tmp_path):
    ruta_csv = tmp_path / "datos.csv"
    ruta_csv.write_text(CSV_OK, encoding="utf-8")
    ruta_json = tmp_path / "datos.json"
    ruta_json.write_text(json.dumps({
        "origen_comunidad": "demo",
        "periodo_referencia": "Semana_01_2026",
        "interacciones": [{"id": "j1", "canal": "x", "autor": "a", "timestamp": None,
                           "texto": "hola", "tipo": "otro", "metadata": {}}],
    }), encoding="utf-8")
    resultado = load_batch([ruta_json, ruta_csv])
    assert len(resultado) == 3
    assert resultado[0]["id"] == "j1"


def test_load_batch_formato_no_soportado(tmp_path):
    ruta = tmp_path / "datos.txt"
    ruta.write_text("hola", encoding="utf-8")
    with pytest.raises(ValueError, match="no soportado"):
        load_batch([ruta])