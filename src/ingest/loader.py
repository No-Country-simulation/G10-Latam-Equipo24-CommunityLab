import json
from pathlib import Path

from src.ingest.csv_loader import cargar_csv

def cargar_json(ruta) -> dict:
    data = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "interacciones" not in data:
        raise ValueError(f"{Path(ruta).name}: el JSON no tiene la clave 'interacciones'")
    return data


cargadores = {".json": cargar_json, ".csv": cargar_csv}


def cargar_fuente(ruta) -> dict:
    ext = Path(ruta).suffix.lower()
    cargador = cargadores.get(ext)
    if cargador is None:
        raise ValueError(f"Formato no soportado '{ext}' en {Path(ruta).name} (usa .json o .csv)")
    return cargador(ruta)


def load_batch(sources) -> list[dict]:
    interacciones: list[dict] = []
    for fuente in sources:
        interacciones.extend(cargar_fuente(fuente)["interacciones"])
    return interacciones