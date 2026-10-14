# Cobertura de pruebas — Ingesta multicanal (PR 5 de la cadena)

> Issue #112 (HU-S4-010_PS) · Rama `feat/ingesta-qa` · Autor del documento: @itanflores (QA)
> Verificación local de QA: martes 13/10/2026, 12:30 CDMX, sobre el head de #106 (`7b45dbe`) y de #107 (`74533c2`). Actualizado el miércoles 14/10/2026, 07:30 CDMX, con las ramas nuevas de #116, #117 y #118 (ver tabla de abajo).

## Resultado de la verificación

| Qué se corrió | Dónde | Resultado |
|---|---|---|
| `python -m pytest -q` (suite completa) | #106 (`feat/ingesta-qa`) | 267 passed, 1 skipped |
| `python -m pytest -q` (suite completa) | #107 (`feat/ingesta-ui`, incluye el contrato de #105) | 269 passed, 1 skipped |
| Pruebas de la cadena: CSV, webhook, Telegram, bot y timeline | #106 | 60 passed |
| `flake8 src/ --max-line-length=100 --ignore=E501,E303,W291,W293` (opciones del CI) | #107 | 0 avisos |
| `python scripts/run_timeline_demo.py --offline` | #106 | 4/4 semanas exitosas |
| `python -m pytest -q` (14/10, 06:30 CDMX) | #118 (`feat/dashboard-publicar-en-telegram`, incluye #105 y #107 actualizados) | 316 passed, 1 skipped; flake8 0 avisos |
| `python -m pytest -q` (14/10, 06:30 CDMX) | #117 (`fix/llm-negativo-rulebased`) y #116 (`fix/ingesta-autor-normalizado`), cada uno sobre `main` | 208 passed, 1 skipped y 210 passed, 1 skipped; flake8 0 avisos |

Las dos primeras filas de pytest corresponden a los heads del 13/10; #105 y #107 recibieron commits nuevos esa noche, y la fila de #118 es la medición vigente de esa parte de la cadena. Estas corridas son locales: el CI no corre en los PRs de la cadena porque su base no es `main` (el workflow solo se dispara con `pull_request: branches: [main]`).

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
| `data/sample/corrida-completa-gemma.json`: el 13/10 a las 12:30 no estaba en ninguna rama. **Actualización 14/10:** ya está en las ramas de #107 y #118 (commit `bcc9a25`), pero todavía no en `main` | Se reproduce el panel solo desde esas ramas; llega a `main` cuando se integre la cadena | Rox |
| Tras #117, la demo `--offline` sobre `demo_fixed.json` sigue mostrando `feedback neg.: 0 derivado(s)` (verificado el 14/10 en la rama de #117) | La evidencia de DERIVAR para el video y R6 requiere la corrida en línea con Gemma; no sale del modo offline | Rox / Ema (evidencia manual) |
| El JSON de Gemma usa la clave `neutral` en `distribucion_sentimiento`; el pipeline en `rule_based` emite `Neutro` | Un gráfico que dependa de una de las dos claves ignoraría la otra. No sé si es un efecto del modelo o del contrato | Rox (confirmar) |
| El ejemplo de `docs/propuesta-al-equipo.md` usaba la clave `"Neutral"`; el pipeline emite `"Neutro"` | Quien construya un gráfico desde la doc usaría una clave que no existe | Itan (corregido en este PR) |
| Todas las pruebas usan `rule_based`; no hay evidencia automatizada con el LLM en línea | El demo y el video usan Gemma | Rox / Ema (evidencia manual) |
| El bot (#104) no tiene prueba del caso de varios updates en que falla el envío de una respuesta posterior: `run_bot` no avanza el offset si `_responder_updates` lanza una excepción, así que al reintentar se reenvían las respuestas ya enviadas (verificado en `src/ingest/bot.py`, 14/10; hallazgo de Yis en la revisión de #104) | Mensajes duplicados a los usuarios tras una falla de red | Rox (autora de #104), con Yis |
| No está definido si el bot debe aceptar solo chats privados o también grupos: el código responde a cualquier `chat.id` (pregunta de Yis, sin respuesta aún) | Un bot en un grupo procesaría mensajes de personas ajenas al piloto | Rox (decisión) |
| #117 y el commit `26390e3` (ya en #104) modifican la misma función de `src/utils/llm.py`: al mezclar #117 con `feat/ingesta-contrato` hay conflicto en `src/utils/llm.py` y `tests/test_llm.py` (probado el 14/10). Con `main` solo, #117 mezcla limpio | El orden de merge puede romper uno de los dos cambios | Rox |
