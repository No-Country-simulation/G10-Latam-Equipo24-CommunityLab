"""Carga de interacciones desde archivos CSV (formato de ingesta).

El CSV es uno de los formatos de entrada que exige el desafío. Este loader
imita la interfaz de JSONInputLoader (load / load_batch) y reutiliza
InputNormalizer para resolver los alias en inglés (author/channel/content),
mapear fecha a timestamp y url a metadata["url"].
"""
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain.models import InputBatch, InputMessage
from src.ingest.normalizer import InputNormalizer

# Cabeceras requeridas y sus variantes aceptadas. Las alternativas en inglés
# las resuelve InputNormalizer; "tipo" no tiene variante en inglés.
_REQUIRED_HEADERS = {
    "autor": ("autor", "author"),
    "canal": ("canal", "channel"),
    "tipo": ("tipo",),
    "texto": ("texto", "content"),
}


class CSVInputLoader:
    """Carga un lote de interacciones desde un CSV (solo stdlib, sin pandas).

    - Codificación utf-8-sig (tolera el BOM de Excel).
    - Cabeceras requeridas: autor, canal, tipo, texto (con alias en inglés
      autor/author, canal/channel, texto/content).
    - Columnas opcionales de mensaje: id, timestamp o fecha, url
      (se mapea a metadata["url"]).
    - Cada celda se recorta (strip); no se filtran filas con texto vacío,
      consistente con el contrato JSON.
    - Envelope: las columnas opcionales origen_comunidad y periodo_referencia
      se toman de la primera fila con valor; el constructor permite
      sobreescribirlas. Orden de resolución: argumento explícito > columna del
      CSV > default "CSV-<stem>".
    """

    def __init__(
        self,
        origen_comunidad: Optional[str] = None,
        periodo_referencia: Optional[str] = None,
    ) -> None:
        self.origen_comunidad = origen_comunidad
        self.periodo_referencia = periodo_referencia
        self.normalizer = InputNormalizer()

    def load(self, source: str) -> List[InputMessage]:
        """Devuelve la lista de interacciones (compatible con DataLoader)."""
        return self.load_batch(source).interacciones

    def load_batch(self, source: str) -> InputBatch:
        """Devuelve el lote completo (InputBatch) con el envelope resuelto."""
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        rows = self._read_rows(path)

        return InputBatch(
            origen_comunidad=self._resolve_envelope(
                "origen_comunidad", self.origen_comunidad, rows, path.stem
            ),
            periodo_referencia=self._resolve_envelope(
                "periodo_referencia", self.periodo_referencia, rows, path.stem
            ),
            interacciones=[
                self.normalizer.normalize(path.stem, row) for row in rows
            ],
        )

    def _read_rows(self, path: Path) -> List[Dict[str, Any]]:
        """Lee y valida el CSV, devolviendo las filas con celdas recortadas."""
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError(f"CSV vacío sin encabezados: {path.name}")

            missing = [
                name
                for name, variantes in _REQUIRED_HEADERS.items()
                if not any(v in reader.fieldnames for v in variantes)
            ]
            if missing:
                raise ValueError(
                    f"Faltan encabezados requeridos en el CSV: {', '.join(missing)}"
                )

            rows = [self._strip_row(row) for row in reader]

        if not rows:
            raise ValueError(f"CSV vacío sin filas de datos: {path.name}")
        return rows

    @staticmethod
    def _strip_row(row: Dict[str, Any]) -> Dict[str, Any]:
        """Recorta cada celda; valores vacíos o columnas extra quedan en vacío."""
        return {
            key: (value.strip() if isinstance(value, str) else "")
            for key, value in row.items()
        }

    @classmethod
    def _resolve_envelope(
        cls,
        column: str,
        override: Optional[str],
        rows: List[Dict[str, Any]],
        stem: str,
    ) -> str:
        """Resuelve una columna de envelope: argumento > CSV > default."""
        return override or cls._first_value(rows, column) or f"CSV-{stem}"

    @staticmethod
    def _first_value(rows: List[Dict[str, Any]], column: str) -> Optional[str]:
        """Devuelve el primer valor no vacío de la columna entre las filas."""
        for row in rows:
            value = row.get(column)
            if value:
                return value
        return None
