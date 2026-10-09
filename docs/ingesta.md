# Ingesta de datos

Documenta los formatos de entrada que acepta el pipeline y cómo se resuelve el
envelope (los metadatos comunes del lote).

## Formatos soportados

| Formato | Módulo | Notas |
| --- | --- | --- |
| JSON (`.json`) | `src/ingest/input_loader.py` | Contrato original del desafío (`origen_comunidad`, `periodo_referencia`, `interacciones`). |
| CSV (`.csv`) | `src/ingest/csv_loader.py` | Encabezados requeridos: `autor`, `canal`, `tipo`, `texto`; acepta los alias en inglés `author`, `channel`, `content`. |

El despacho por sufijo y el merge viven en `src/ingest/loader.py`
(`load_batch(sources)`), que es la puerta de entrada que usa el pipeline.

## CSV

- Codificación `utf-8-sig` (tolera el BOM de Excel). Sin dependencias extra:
  solo la librería estándar `csv`.
- Encabezados requeridos: `autor`, `canal`, `tipo`, `texto`. Los alias en
  inglés (`author`, `channel`, `content`) los resuelve `InputNormalizer`.
- Columnas opcionales de mensaje: `id`, `timestamp` (o `fecha`) y `url`
  (se mapea a `metadata["url"]`).
- Cada celda se recorta (`strip`). No se filtran filas con texto vacío,
  consistente con el contrato JSON.

### Reglas de envelope

El envelope (`origen_comunidad`, `periodo_referencia`) de un CSV se resuelve en
este orden:

1. Argumento explícito del constructor
   (`CSVInputLoader(origen_comunidad=..., periodo_referencia=...)`).
2. Columna del CSV (el primer valor no vacío).
3. Default `"CSV-<nombre-del-archivo>"` para ambos campos.

En un merge de varias fuentes (`load_batch` con una lista):

- `interacciones`: concatenadas en orden de las fuentes.
- `origen_comunidad`: unión de los orígenes no vacíos, en orden alfabético,
  unidos con `" + "`.
- `periodo_referencia`: se conserva el valor único cuando todas las fuentes
  coinciden; si hay más de uno, pasa a `"combinado"`.
- Los kwargs `origen` y `periodo` sobreescriben el resultado del merge.

## Ejemplos de uso

Una sola fuente: el formato se despacha por sufijo.

```bash
python scripts/run_demo.py data/sample/demo_fixed.json --offline
python scripts/run_demo.py data/sample/sintetico_120.csv --offline
```

Varias fuentes en una sola corrida (merge de lotes):

```bash
python scripts/run_demo.py data/sample/demo_fixed.json data/sample/sintetico_120.csv --offline
```

Generar un dataset sintético determinista (misma semilla -> mismo CSV):

```bash
python scripts/generate_dataset.py                          # data/sample/sintetico_120.csv, 120 filas
python scripts/generate_dataset.py --filas 50 --semilla 7   # otro tamaño y otra semilla
```