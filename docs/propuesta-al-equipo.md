# Propuesta al equipo — Ingesta multicanal, bot de Telegram y dashboard

**Fecha:** 2026-10-11
**Rama local:** `feat/ingesta-mejoras` (7 commits, sin pushear, sin PR)
**Estado:** borrador para discutir en la reunión

> **Nota de estado (13/10/2026, QA).** La propuesta se aprobó en la sesión del lunes 12/10 y se dividió en una cadena de PRs: #102 CSV → #103 webhook → #104 bot → #105 contrato → #107 dashboard, y #106 docs y timeline (tracker: #108). #94 y #98 ya están en `main`. La rama `feat/ingesta-mejoras` creció a ~4.8k líneas; la suite de la cadena da **267 passed, 1 skipped** (#106) y flake8 limpio. El resto del documento se conserva como registro de la propuesta original.

## 1. Resumen

Traemos para discutir tres cosas que hoy viven **fuera del repositorio**:
parte en una rama local que todavía no subimos y parte en archivos sin
trackear. Nada de esto está en `main` ni tiene PR abierto.

1. Una **capa de ingesta multicanal** (JSON, CSV, Mastodon, Telegram y un
   webhook HTTP) con merge de varias fuentes en una sola corrida.
2. Un **bot de Telegram** que analiza cada mensaje en tiempo real y responde
   con el resultado del pipeline. Es el diferencial de la demo.
3. Una **línea de tiempo semanal** sintética más un runner que muestra cómo
   evoluciona el pipeline semana a semana (dudas, logros, FAQ, LinkedIn).

Además proponemos **un cambio aditivo al contrato de salida** para que el
dashboard de métricas (HU-S4-003) pueda graficar, y explicamos **cómo se
integra el bot con Streamlit**.

El objetivo de la reunión es decidir **qué entra, cómo y en qué orden**. No
pedimos merge todavía: pedimos dirección.

## 2. Qué construimos (fuera del repo)

### 2.1 Ingesta multicanal

El pipeline ya aceptaba el JSON del desafío. Lo que sumamos es entrada por
**CSV** y fuentes alternativas, todas convergiendo al mismo contrato
(`InputBatch`).

| Fuente / formato | Módulo | Notas |
| --- | --- | --- |
| JSON (desafío) | `src/ingest/input_loader.py` | Contrato original. |
| CSV | `src/ingest/csv_loader.py` | Encabezados `autor, canal, tipo, texto`; acepta alias en inglés. |
| Mastodon | `src/ingest/ingest.py` | Ya existía. |
| Telegram | `src/ingest/telegram.py` | Lee mensajes **nuevos** (hacia adelante). |
| Webhook HTTP | `src/ingest/webhook.py` | `POST /ingest` en tiempo real. |

El despacho por sufijo y el **merge de varios lotes** viven en
`src/ingest/loader.py` (`load_batch(sources)`): concatena interacciones, une
orígenes y combina períodos. Se puede correr una sola fuente o varias:

```bash
python scripts/run_demo.py data/sample/demo_fixed.json data/sample/sintetico_120.csv --offline
```

### 2.2 Bot interactivo de Telegram (diferencial de la demo)

`scripts/run_bot.py` levanta un bot que, por cada mensaje, arma un batch de un
solo mensaje **en memoria**, lo pasa al pipeline y responde con un texto corto
en español: sentimiento, temas principales (hasta 3) y decisión
(`PUBLICAR`, `CREAR_FAQ` o `DESCARTAR`), incluyendo el estado del asset FAQ
cuando hay una duda técnica.

- Probado en vivo por chat privado: funciona.
- Diferencial de la demo, **nunca el camino obligatorio**: el camino por
  archivo siempre funciona.
- Reintenta con backoff exponencial ante errores de red o de la Bot API y no
  se cae. El token nunca aparece en logs ni en mensajes de error.

### 2.3 Línea de tiempo semanal + runner de evolución

Dos piezas nuevas, ambas deterministas y sin red:

- `scripts/generate_timeline.py`: genera semanas sintéticas coherentes (la
  mezcla de tipos madura con el tiempo). Con `--semanas`, `--base-filas`,
  `--incremento` y `--semilla`.
- `scripts/run_timeline_demo.py`: corre el pipeline **semana por semana** y
  muestra la evolución en una tabla.

Datos generados (`data/sample/timeline/semana01..04.csv`, 60 / 90 / 120 / 150
filas). La evolución que muestra el runner:

| Indicador | Semana 01 | Semana 04 |
| --- | --- | --- |
| Preguntas técnicas (dudas) | 65 % | ~21 % |
| Testimonios + logros | 10 % | ~57 % |
| Publicación en LinkedIn | No | Sí (desde semana 02) |
| Asset FAQ | Sí | Sí |

```bash
python scripts/generate_timeline.py
python scripts/run_timeline_demo.py --offline
```

### 2.4 Refactor de pipeline (sin cambios de comportamiento)

Extraímos el helper `_run_with_batch` en `src/pipeline.py`: el pipeline corre
sobre un `InputBatch` armado **en memoria**, sin escribir archivos temporales.
Es la pieza que reutilizan el webhook y el bot. También se ajustó
`src/utils/llm.py` para clasificar en `rule_based` sobre el texto del mensaje
(no sobre el batch completo).

### 2.5 Inventario

En la rama (7 commits, **21 archivos, +2.799 líneas**):

| Área | Archivos principales |
| --- | --- |
| Ingesta | `src/ingest/loader.py`, `csv_loader.py`, `telegram.py`, `webhook.py` |
| Bot | `src/ingest/bot.py`, `scripts/run_bot.py` |
| CLIs | `scripts/ingest_telegram.py`, `scripts/run_webhook.py`, `generate_dataset.py` |
| Pipeline | `src/pipeline.py`, `src/utils/llm.py` |
| Docs | `docs/ingesta.md` |
| Tests | `tests/test_csv_loader.py`, `test_telegram.py`, `test_webhook.py`, `test_bot.py` |

Sin trackear (todavía fuera de git): `scripts/generate_timeline.py`,
`scripts/run_timeline_demo.py`, sus tests, `data/sample/timeline/` y las notas
`docs/decisiones-contrato.md`, `docs/decision-derivar.md`,
`docs/git-workflow.md`.

## 3. Propuesta: cambio aditivo al contrato de salida

### 3.1 El problema

El dashboard de la HU-S4-003 pide tres gráficos: torta de sentimiento, barras
de **top 10 temas** y línea temporal. Hoy el contrato **no alcanza** para dos
de ellos:

- `src/pipeline.py` **ya calcula** el `Counter` de sentimientos y de temas
  dentro de `_summarize`, pero **los descarta**: solo expone
  `sentimiento_predominante` (una frase) y `temas_principales` (lista de hasta
  **5** temas, **sin conteo**).
- El gráfico de torta necesita la **distribución** completa; el de barras
  necesita **frecuencias** y **top 10**.

### 3.2 Opción A (recomendada): extender el resumen, aditivo

Agregar al resumen dos campos nuevos, sin tocar los existentes:

```jsonc
{
  "distribucion_sentimiento": { "Positivo": 42, "Negativo": 18, "Neutro": 31 },
  "temas_principales_conteo": [
    { "tema": "empleo", "frecuencia": 12 },
    { "tema": "entrevista", "frecuencia": 9 }
  ]
}
```

- **Aditivo**: los consumidores actuales siguen funcionando igual.
- Los datos ya se calculan; solo hay que exponerlos y subir el tope de temas a
  10.

### 3.3 Opción B: capa de analítica aparte

Dejar el contrato como está y calcular las distribuciones en un módulo aparte
que recorra el `OutputBatch` (los análisis por interacción ya traen sentimiento
y temas). No toca el contrato, pero **re-camina** datos que el pipeline ya
tenía en la mano.

**Recomendación:** Opción A. Es menos código, no rompe nada y el dato ya está
calculado en el lugar correcto. Si prefieren no tocar el contrato compartido,
la B es viable como capa de la interfaz.

> Detalle de las decisiones de contrato: `docs/decisiones-contrato.md`.

## 4. Integración bot ↔ Streamlit

Una aclaración importante para no prometer algo imposible: **el bot no puede
"vivir dentro" de Streamlit**. El bot es un proceso con long polling
persistente; Streamlit re-ejecuta el script de arriba abajo en cada
interacción y no hospeda un poller continuo. Son dos procesos.

Lo que sí comparten es el **código** (los módulos de ingesta) y el **destino**
de los datos (sink OCI/snapshot), nunca el proceso. Formas de integrarlos:

1. **Pull (demo, recomendado):** un botón en el dashboard que trae los
   mensajes nuevos de Telegram (`fetch_updates` + `messages_to_batch`), corre
   el pipeline y refresca los gráficos. El token iría en `st.secrets`.
2. **Push (futuro, converge con HU-S5-007):** Telegram apunta su webhook a
   nuestro endpoint `POST /ingest` (ya construido) y el dashboard lee del
   sink. El webhook ya es, de hecho, el punto de convergencia.

```text
Telegram ──(pull: fetch_updates)──►  Streamlit (dashboard)  ──► gráficos
   │                                      ▲
   └──(push futuro: webhook)──► POST /ingest ──► sink ─────────┘
```

## 5. Lo que necesitamos del equipo

1. **Contrato:** ¿aprobamos la Opción A (extender el resumen, aditivo) o
   preferimos la Opción B (capa separada)? Es lo único que bloquea los
   gráficos de la HU-S4-003.
2. **Alcance del bot:** ¿lo dejamos como demo interactiva o entra al scope del
   S5? Hoy es un stretch.
3. **Cómo entra el código:** la rama tiene **+2.799 líneas**, por encima del
   presupuesto de review de 400. Si queremos mergearla, proponemos **PRs
   encadenados** por escalón (CSV → Telegram → webhook → bot), cada uno
   revisable por separado.
4. **Orden de merge:** sugerimos cerrar primero `#94` (`feat/decision-engine`,
   ya aprobado) y recién después subir la rama de ingesta. *(Hecho: #94 se mergeó el 11/10.)*

## 6. Cómo reproducirlo (evidencia)

Todo funciona en modo offline (`--offline` = `rule_based`: determinista, sin
red, sin costo). El backend por defecto del `.env` es Ollama, así que para
demos conviene forzar `--offline`.

```bash
# Suite completa al cierre de esta sesión:
#   230 passed, 1 skipped (al 11/10; en la cadena del 13/10: 267 passed, 1 skipped)
venv/bin/python -m pytest -q

# Demo por archivo y merge de fuentes
venv/bin/python scripts/run_demo.py data/sample/demo_fixed.json --offline
venv/bin/python scripts/run_demo.py data/sample/sintetico_120.csv --offline

# Línea de tiempo
venv/bin/python scripts/generate_timeline.py
venv/bin/python scripts/run_timeline_demo.py --offline

# Webhook y bot (requieren token solo el bot / la fuente Telegram)
venv/bin/python scripts/run_webhook.py --backend rule_based
TELEGRAM_BOT_TOKEN="..." venv/bin/python scripts/run_bot.py
```

## Anexo — Relación con las historias de usuario

| HU | Relación |
| --- | --- |
| HU-S4-003 (dashboard de métricas) | **Bloqueada** por la decisión de contrato (sección 3). |
| HU-S4-006 (endpoint de API) | El webhook converge con ella (mismo `InputBatch`). |
| HU-S5-007 (webhooks) | Reutiliza `_run_with_batch` y el contrato de entrada sin cambios. |
| HU-S4-004 (panel de curaduría) | Ya implementada en `src/interface/app.py`. |
