# Cobertura de pruebas — Ingesta multicanal (PR 5 de la cadena)

> Issue #112 (HU-S4-010_PS) · Rama `feat/ingesta-qa` · Autor del documento: @itanflores (QA)
> Verificación local de QA: martes 13/10/2026, 12:30 CDMX, sobre el head de #106 (`7b45dbe`) y de #107 (`74533c2`).

## Resultado de la verificación

| Qué se corrió | Dónde | Resultado |
|---|---|---|
| `python -m pytest -q` (suite completa) | #106 (`feat/ingesta-qa`) | 267 passed, 1 skipped |
| `python -m pytest -q` (suite completa) | #107 (`feat/ingesta-ui`, incluye el contrato de #105) | 269 passed, 1 skipped |
| Pruebas de la cadena: CSV, webhook, Telegram, bot y timeline | #106 | 60 passed |
| `flake8 src/ --max-line-length=100 --ignore=E501,E303,W291,W293` (opciones del CI) | #107 | 0 avisos |
| `python scripts/run_timeline_demo.py --offline` | #106 | 4/4 semanas exitosas |

Evolución que muestra el runner con `rule_based` (datos 100 % sintéticos):

| Semana | Filas | % dudas | % logros + testimonios | LinkedIn | FAQ |
|---|---|---|---|---|---|
| semana01 | 60 | 65.0 | 10.0 | No | Sí |
| semana02 | 90 | 42.2 | 34.4 | Sí | Sí |
| semana03 | 120 | 30.0 | 47.5 | Sí | Sí |
| semana04 | 150 | 20.7 | 56.7 | Sí | Sí |

## Qué prueba cubre cada fuente de ingesta

### CSV — `src/ingest/csv_loader.py` y `src/ingest/loader.py` (PR #102) · `tests/test_csv_loader.py`, 16 pruebas

- Camino feliz y armado del sobre (`InputBatch`) desde las columnas del CSV.
- Errores: encabezado faltante, CSV sin filas y formato no soportado lanzan `ValueError`.
- Alias en inglés resueltos por el normalizador; `url` pasa a `metadata`; valores por defecto del sobre y prioridad del parámetro sobre la columna.
- `load_batch`: despacho por sufijo (`.csv` / `.json`), merge de JSON + CSV, período uniforme conservado y override explícito.
- Generador sintético determinista y corrida del pipeline offline con el dataset generado.

### Webhook HTTP — `src/ingest/webhook.py` (PR #103) · `tests/test_webhook.py`, 7 pruebas

- `GET` de salud responde OK.
- `POST /ingest` con un lote válido devuelve el resumen; también acepta un arreglo plano de mensajes.
- Cuerpo inválido o una fila inválida devuelven 400; método equivocado, 405; ruta desconocida, 404.

### Telegram — `src/ingest/telegram.py` (PR #104) · `tests/test_telegram.py`, 11 pruebas

- `fetch_updates` filtra por chat y envía `offset` y `limit`.
- Sin token, o con `ok: false` de la API, falla con un error claro; **el error nunca incluye el token**.
- `messages_to_batch` llena los campos del contrato, descarta mensajes sin texto y comandos, y respeta el sobre por defecto y el override.
- El lote de Telegram se guarda como JSON válido y se mergea con el loader.

### Bot interactivo — `src/ingest/bot.py` (PR #104) · `tests/test_bot.py`, 13 pruebas

- Respuestas: positivo → PUBLICAR; pregunta técnica → FAQ; neutro → DESCARTAR; `/start` y `/help`; comando desconocido ignorado; mensaje vacío y falla del pipeline responden con un texto amable.
- Polling: el `offset` avanza sobre todos los updates y nunca retrocede.
- Resiliencia: reintento con backoff ante errores de red y procesamiento del update; un error de red al enviar **no filtra el token**.

### Línea de tiempo — `scripts/generate_timeline.py` y `scripts/run_timeline_demo.py` (PR #106) · 13 pruebas

- Generador (7): determinismo por semilla, crecimiento del volumen entre semanas, tendencia de madurez, esquema de cada fila y CLI que crea un archivo por semana.
- Runner (6): orden de semanas, rutas explícitas, conteo de dudas y logros, una fila por semana, CLI de humo y ruta inexistente.

## Huecos detectados (para seguimiento, con dueño)

| Hueco | Por qué importa | Dueño sugerido |
|---|---|---|
| El bot no contempla **DERIVAR** (solo PUBLICAR, CREAR_FAQ o DESCARTAR), aunque la regla R4 ya está en `main` (#98) | Un mensaje negativo por Telegram se reportaría como DESCARTAR | Rox (autora de #104), con revisión de Yis |
| No hay prueba del bot con un mensaje **negativo** | Es el caso que cubriría el hueco anterior | Rox |
| `data/sample/corrida-completa-gemma.json`, citado para probar el panel de #107, no está en ninguna rama del remoto (13/10, 12:30) | Sin él no se puede reproducir el panel ni la corrida en línea con Gemma | Rox |
| El ejemplo de `docs/propuesta-al-equipo.md` usa la clave `"Neutral"`; el pipeline emite `"Neutro"` | Quien construya un gráfico desde la doc usaría una clave que no existe | Itan (corrección de doc en este PR) |
| Todas las pruebas usan `rule_based`; no hay evidencia automatizada con el LLM en línea | El demo y el video usan Gemma | Rox / Ema (evidencia manual) |
