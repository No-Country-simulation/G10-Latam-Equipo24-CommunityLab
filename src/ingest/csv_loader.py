import csv
from datetime import datetime, timezone
from pathlib import Path

columnas_requeridas = ("autor", "canal", "tipo", "texto")
tipos_validos = {"testimonio", "pregunta_tecnica", "otro"}


def _valor(fila: dict, columna: str) -> str:
    return (fila.get(columna) or "").strip()

def cargar_csv(ruta, origen: str | None = None, periodo: str | None = None) -> dict:
    ruta = Path(ruta)
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        columnas = [c.strip().lower() for c in (lector.fieldnames or [])]
        faltantes = [c for c in columnas_requeridas if c not in columnas]
        if faltantes:
            raise ValueError(f"{ruta.name}: faltan las columnas {faltantes}")
        lector.fieldnames = columnas

        interacciones = []
        for n, fila in enumerate(lector, start=2):
            texto = _valor(fila, "texto")
            if not texto:
                continue
            tipo = _valor(fila, "tipo").lower()
            if tipo not in tipos_validos:
                raise ValueError(f"{ruta.name} línea {n}: tipo inválido '{tipo}'")
            interacciones.append({
                "id": _valor(fila, "id") or f"{ruta.stem}_{n}",
                "canal": _valor(fila, "canal"),
                "autor": _valor(fila, "autor"),
                "timestamp": _valor(fila, "timestamp") or None,
                "texto": texto,
                "tipo": tipo,
                "metadata": {"url": _valor(fila, "url") or None},
            })

    return {
        "origen_comunidad": origen or f"CSV_{ruta.stem}",
        "periodo_referencia": periodo or datetime.now(timezone.utc).strftime("Semana_%V_%G"),
        "interacciones": interacciones,
    }