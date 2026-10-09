"""Despacho de fuentes de ingesta y merge de lotes en una sola corrida.

Permite ingestar una o más fuentes (.json y/o .csv) en un único InputBatch:
las interacciones se concatenan en orden y el envelope consolidado. Es la
puerta de entrada que usa el pipeline (src/pipeline.run_pipeline).
"""
from pathlib import Path
from typing import List, Optional, Union

from src.domain.models import InputBatch
from src.ingest.csv_loader import CSVInputLoader
from src.ingest.input_loader import JSONInputLoader

# Sufijo de archivo -> loader que sabe leerlo.
_LOADERS = {
    ".csv": CSVInputLoader,
    ".json": JSONInputLoader,
}


def load_batch(
    sources: Union[str, List[str]],
    *,
    origen: Optional[str] = None,
    periodo: Optional[str] = None,
) -> InputBatch:
    """Carga una o más fuentes y las mergea en un único InputBatch.

    - Un solo source (str): despacha por sufijo (.csv -> CSVInputLoader,
      .json -> JSONInputLoader; otro sufijo -> ValueError que nombra los
      formatos soportados).
    - Varios sources (List[str]): despacha cada uno y mergea. Las
      `interacciones` se concatenan en orden; `origen_comunidad` queda como
      " + ".join de los orígenes no vacíos únicos (orden alfabético);
      `periodo_referencia` se conserva cuando hay un único valor y si no pasa
      a "combinado". Los kwargs `origen` y `periodo` sobreescriben el
      resultado.
    """
    if isinstance(sources, str):
        sources = [sources]
    if not sources:
        raise ValueError("No se indicaron fuentes de ingesta")

    batches = [_load_one(source) for source in sources]

    if origen is not None:
        origen_final = origen
    else:
        origen_final = " + ".join(
            sorted({b.origen_comunidad for b in batches if b.origen_comunidad})
        )

    if periodo is not None:
        periodo_final = periodo
    else:
        valores_periodo = sorted(
            {b.periodo_referencia for b in batches if b.periodo_referencia}
        )
        periodo_final = (
            valores_periodo[0] if len(valores_periodo) == 1 else "combinado"
        )

    interacciones = [msg for batch in batches for msg in batch.interacciones]

    return InputBatch(
        origen_comunidad=origen_final,
        periodo_referencia=periodo_final,
        interacciones=interacciones,
    )


def _load_one(source: str) -> InputBatch:
    """Despacha una fuente individual según el sufijo del archivo."""
    suffix = Path(source).suffix.lower()
    loader_cls = _LOADERS.get(suffix)
    if loader_cls is None:
        raise ValueError(
            f"Formato no soportado: {source!r} "
            "(formatos soportados: .csv, .json)"
        )
    return loader_cls().load_batch(source)
