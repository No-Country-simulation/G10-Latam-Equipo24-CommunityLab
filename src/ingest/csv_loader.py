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

# [Mejora 5] codificaciones a probar, en orden. utf-8-sig tolera el BOM de
# Excel; cp1252 cubre los csv exportados desde Excel en Windows.
_ENCODINGS = ("utf-8-sig", "cp1252")

# [Mejora 1] Delimitadores aceptados (Excel en español usa ";").
_DELIMITERS = ",;\t"


def _count_outside_quotes(text: str, separator: str) -> int:
    """Cuenta `separator` ignorando los que caen dentro de comillas."""
    count = 0
    in_quotes = False
    for char in text:
        if char == '"':
            in_quotes = not in_quotes
        elif char == separator and not in_quotes:
            count += 1
    return count


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
            interacciones=self._normalize_rows(path, rows),
        )

    # [Mejora 4] Errores con número de fila
    def _normalize_rows(
        self, path: Path, rows: List[Dict[str, Any]]
    ) -> List[InputMessage]:
        """Normaliza cada fila; si falla, indica qué fila del archivo."""
        messages: List[InputMessage] = []
        for number, row in enumerate(rows, start=2):
            try:
                messages.append(self.normalizer.normalize(path.stem, row))
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"{path.name}, fila {number}: {exc}") from exc
        return messages

    # [Mejora 5] Lectura con reintento de codificación
    def _read_rows(self, path: Path) -> List[Dict[str, Any]]:
        """Lee el CSV probando varias codificaciones"""
        last_error: Optional[UnicodeDecodeError] = None
        for encoding in _ENCODINGS:
            try:
                return self._read_rows_with(path, encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise ValueError(
            f"No se pudo decodificar {path.name} (probando: "
            f"{', '.join(_ENCODINGS)}). Guardalo como CSV UTF-8."
        ) from last_error

    def _read_rows_with(
        self, path: Path, encoding: str
    ) -> List[Dict[str, Any]]:
        """Lee y valida el csv con una codificación dada."""
        with path.open(encoding=encoding, newline="") as handle:
            # [Mejora 1] Detectar el delimitador con una muestra.
            sample = handle.read(4096)
            handle.seek(0)
            reader = csv.DictReader(
                handle, delimiter=self._detect_delimiter(sample)
            )

            if reader.fieldnames is None:
                raise ValueError(f"CSV vacío sin encabezados: {path.name}")

            # [Mejora 2] Normalizar encabezados antes de validar.
            reader.fieldnames = [
                (name or "").strip().lower() for name in reader.fieldnames
            ]

            # [Mejora 6] Avisar de encabezados repetidos (DictReader se
            # quedaría con el último sin decir nada).
            names = reader.fieldnames
            duplicated = sorted({n for n in names if n and names.count(n) > 1})
            if duplicated:
                raise ValueError(
                    "Encabezados duplicados en el CSV: "
                    f"{', '.join(duplicated)}"
                )
            missing = [
                name
                for name, variantes in _REQUIRED_HEADERS.items()
                if not any(v in names for v in variantes)
            ]
            if missing:
                raise ValueError(
                    "Faltan encabezados requeridos en el CSV: "
                    f"{', '.join(missing)}"
                )

            rows = [self._strip_row(row) for row in reader]

        if not rows:
            raise ValueError(f"CSV vacío sin filas de datos: {path.name}")
        return rows
    
    @staticmethod
    def _detect_delimiter(sample: str) -> str:
        """Elige el delimitador más frecuente en la línea de encabezado.

        Solo cuenta las apariciones fuera de celdas citadas: contar el
        carácter a ciegas falla cuando el encabezado trae el otro
        separador adentro de comillas
        (``"nota, a, b, c, d";autor;canal;tipo;texto``), donde las comas
        internas empatan con los punto y coma reales y ganaría la coma
        por orden en ``_DELIMITERS``.
        """
        header = sample.splitlines()[0] if sample else ""
        best_sep, best_count = ",", 0
        for sep in _DELIMITERS:
            count = _count_outside_quotes(header, sep)
            if count > best_count:
                best_sep, best_count = sep, count
        return best_sep

    # [Mejora 3] Descartar la clave None (celdas sobrantes) y tolerar filas
    # cortas.
    @staticmethod
    def _strip_row(row: Dict[Any, Any]) -> Dict[str, Any]:
        """Recorta cada celda; vacíos/faltantes quedan en "" y se ignoran
        las celdas extra que no tienen encabezado."""
        return {
            key: (value.strip() if isinstance(value, str) else "")
            for key, value in row.items()
            if key is not None
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
