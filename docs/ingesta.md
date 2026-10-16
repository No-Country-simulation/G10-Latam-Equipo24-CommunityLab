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

Además de leer archivos, el repositorio tiene *fuentes* que producen un JSON
con el mismo contrato y que luego pueden pasarse a `load_batch`: Mastodon
(`src/ingest/ingest.py`) y Telegram (`src/ingest/telegram.py`, ver más abajo).

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

## Ingesta desde Telegram

La fuente Telegram usa la **Bot API** (HTTP) a través de `requests`, sin
dependencias nuevas. Convierte los mensajes de un grupo/canal en un JSON con el
mismo contrato del pipeline, listo para mergear con las demás fuentes.

### Crear el bot

1. Abrí un chat con **@BotFather** en Telegram y enviá `/newbot`.
2. Elegí un nombre y un usuario para el bot (debe terminar en `bot`).
3. BotFather devuelve el **token** (formato `123456:ABC-DEF...`). Guardalo como
   variable de entorno; no lo subas al repositorio.

### Obtener el chat_id

1. Agregá el bot al grupo o canal (en un canal, como administrador).
2. Enviá un mensaje en ese chat.
3. El chat_id aparece en la respuesta de `getUpdates`
   (`https://api.telegram.org/bot<TOKEN>/getUpdates`) dentro de
   `result[].message.chat.id`. En grupos y supergrupos suele ser negativo.
   También podés reenviar un mensaje del grupo a un bot de utilidades como
   @userinfobot.

### Uso del CLI

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."

# El token toma la variable de entorno si no se pasa --token.
python scripts/ingest_telegram.py --chat -1001234567890 --verbose

# Con origen explícito y salida a medida.
python scripts/ingest_telegram.py --token "123456:ABC-DEF..." \
    --chat -1001234567890 --origen Comunidad_Telegram \
    --out data/sample/telegram_interacciones.json --limit 100
```

Opciones: `--token`, `--chat`, `--out`, `--limit`, `--offset`, `--origen` y
`--verbose`. Sale con código 0 en éxito y 1 ante error (token faltante, error
de red/API o de escritura). El token nunca se imprime en los logs.

El archivo generado se puede mergear con las demás fuentes:

```bash
python scripts/run_demo.py data/sample/telegram_interacciones.json \
    data/sample/sintetico_120.csv --offline
```

### Limitación de getUpdates

- Un bot solo ve los mensajes que llegan **después** de que lo agregaron al
  grupo/canal; no puede leer el historial anterior a su incorporación.
- `getUpdates` entrega únicamente el backlog reciente (ventana por defecto de
  24 h) y cada update se entrega una sola vez salvo que se juegue con
  `offset`. No existe forma de leer historial viejo arbitrario con la Bot API.

Por eso esta fuente es **hacia adelante**: conviene correrla periódicamente y
acumular los mensajes nuevos.

## Webhook de ingesta

El escalón 3 de ingesta expone un servidor HTTP mínimo (solo librería estándar,
`http.server.ThreadingHTTPServer`) que recibe un lote en memoria por
`POST /ingest`, corre el pipeline completo y devuelve el resumen del contrato.
No escribe archivos temporales: el pipeline se ejecuta sobre el `InputBatch`
armado en memoria (helper `_run_with_batch` en `src/pipeline.py`).

Rutas:

- `POST /ingest`: acepta un InputBatch completo (con `interacciones`) o un
  array plano de mensajes crudos (con alias en inglés `author`/`channel`/
  `content`, igual que el CSV). Responde 200 con
  `{status, resumen, activos, almacenamiento}`; 400 si el body es inválido;
  500 si el pipeline falla.
- `POST /telegram`: recibe un Update de la Bot API de Telegram (Fase 1 del
  webhook de Telegram, ver más abajo). Responde 200 con
  `{status, ruta, update_id, resumen, activos, almacenamiento}`.
- `GET /health`: 200 `{"status": "ok"}`.

Cualquier otra ruta o método responde 404/405. El backend LLM lo decide
`COMMUNITYLAB_LLM_BACKEND` (por defecto `rule_based`); el CLI permite
sobreescribirlo.

### Levantarlo

```bash
python scripts/run_webhook.py                          # http://127.0.0.1:8765, backend auto
python scripts/run_webhook.py --port 9000 --backend rule_based
python scripts/run_webhook.py --backend ollama --model gemma4:31b
python scripts/run_webhook.py --secret "mi-secret"     # habilita POST /telegram
```

El server imprime ejemplos de curl al arrancar y se apaga con Ctrl-C (salida 0).
`--secret` setea `TELEGRAM_WEBHOOK_SECRET` (también se puede exportar como
variable de entorno); sin él, `POST /telegram` responde 503.

### Ejemplos con los datasets existentes

```bash
# InputBatch completo desde un archivo del repo.
curl -X POST http://127.0.0.1:8765/ingest \
     -H 'Content-Type: application/json' \
     -d @data/sample/demo_fixed.json

# Array plano de mensajes crudos.
curl -X POST http://127.0.0.1:8765/ingest \
     -H 'Content-Type: application/json' \
     -d '[{"autor":"Ana","canal":"#general","tipo":"testimonio","texto":"Logré mi primer empleo!"}]'

# Chequeo de vida.
curl http://127.0.0.1:8765/health
```

### Webhook de Telegram (Fase 1)

`POST /telegram` recibe un **Update** de la Bot API de Telegram, lo convierte
en un `InputBatch` con `messages_to_batch` (`src/ingest/telegram.py`) y lo corre
por el mismo helper `_run_with_batch` que `/ingest`. Es la Fase 1 del webhook de
Telegram y hace tres cosas:

1. Valida el header `X-Telegram-Bot-Api-Secret-Token` contra el secret
   configurado en `TELEGRAM_WEBHOOK_SECRET` (comparación en tiempo constante).
2. Deduplica por `update_id`: un update repetido responde 200 `duplicado` sin
   volver a correr el pipeline (Telegram reintenta hasta recibir 2xx).
3. Responde el resumen del pipeline, igual que `/ingest`, más `ruta` y
   `update_id` para correlacionar.

Es **fail closed**: si `TELEGRAM_WEBHOOK_SECRET` no está configurado, la ruta
responde **503** y no acepta input. Si el header falta o no coincide, responde
**401**. Un update sin contenido utilizable (sin `message`, sin texto o un
comando que empieza con `/`) responde 200 `ignorado` y no corre el pipeline; un
body que no sea JSON responde 400; otro método responde 405 con `Allow: POST`.

**Alcance de la Fase 1:** el webhook **no se registra** con Telegram (no se
llama a `setWebhook`) y el camino de polling (`getUpdates`) queda **sin
cambios**. Se prueba localmente con `curl`, simulando un update:

```bash
export TELEGRAM_WEBHOOK_SECRET="mi-secret"
python scripts/run_webhook.py --secret "$TELEGRAM_WEBHOOK_SECRET"

curl -X POST http://127.0.0.1:8765/telegram \
     -H 'Content-Type: application/json' \
     -H 'X-Telegram-Bot-Api-Secret-Token: mi-secret' \
     -d '{
           "update_id": 100001,
           "message": {
             "message_id": 42,
             "date": 1730000000,
             "text": "Logré mi primer empleo como desarrolladora!",
             "from": {"id": 111, "first_name": "Ana"},
             "chat": {"id": -1001234567890, "type": "supergroup", "title": "Comunidad"}
           }
         }'
```

Repetir el `curl` con el mismo `update_id` devuelve `{"status": "duplicado", ...}`
sin reprocesar.

**Limitación conocida:** el pipeline corre **sincrónicamente** dentro del
request. Una entrega real de Telegram debería recibir un 2xx rápido (Telegram
reintenta si tarda o falla), por lo que mover el procesamiento a segundo plano
es un tema de la Fase 2 (junto con registrar el webhook y exponer una URL
pública).

### Convergencia

Este servidor es una demostración local de ingesta en tiempo real. Cuando se
implementen la HU-S4-006 (endpoint de API) y la HU-S5-007 (webhooks), el
webhook converge con ellas: el contrato de entrada (`InputBatch` + array
plano), el helper `_run_with_batch` y la forma de la respuesta se reutilizan
tal cual.

## Bot interactivo

El escalón 4 de ingesta (stretch opcional S5) es un bot de Telegram que
responde en tiempo real a cada mensaje con el análisis del pipeline: arma un
batch de 1 mensaje en memoria (envelope `Telegram-bot-<fecha>`), lo pasa al
helper `_run_with_batch` (el mismo del webhook) y responde con un texto corto
en español con el sentimiento, los temas principales (hasta 3) y la decisión
(PUBLICAR, CREAR_FAQ o DESCARTAR), incluido el estado del activo FAQ cuando
hay una duda técnica.

Este camino es el diferencial de la demo y NUNCA el camino obligatorio: el
camino por archivo siempre funciona.

### Crear el bot

1. Abrí un chat con @BotFather y enviá `/newbot` (igual que la fuente de
   Telegram documentada más arriba).
2. BotFather devuelve el token. Guardalo en la variable de entorno
   `TELEGRAM_BOT_TOKEN`; no lo subas al repositorio.

### Arrancarlo

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."

# rule_based (default): determinista, sin red, sin costo.
python scripts/run_bot.py

# Con otro backend LLM o long polling a medida.
python scripts/run_bot.py --backend ollama --model gemma4:31b
python scripts/run_bot.py --backend rule_based --poll-timeout 60
```

El backend se resuelve igual que el webhook: `--backend` >
`COMMUNITYLAB_LLM_BACKEND` > `rule_based`. `--poll-timeout` ajusta el long
polling de la Bot API (default 30 segundos). El bot imprime "bot listo" y se
apaga con Ctrl-C (salida 0).

### Probarlo

Con el bot corriendo, mandale un mensaje desde Telegram: un testimonio, una
duda técnica o un logro. El bot responde con el análisis del pipeline. Los
comandos `/start` y `/help` muestran la bienvenida; los demás comandos se
ignoran. Ante errores de red o de la Bot API, el bot reintenta con backoff
exponencial (1s, 2s, 4s, tope 30s) y no se cae; el token nunca aparece en los
logs ni en los mensajes de error.

### Convergencia

Este bot es la demostración interactiva del pipeline en tiempo real. Cuando
se implemente la HU-S5-007 (webhooks), reutiliza el mismo helper
`_run_with_batch` y el mismo contrato de entrada (`InputBatch`), por lo que
converge con ella sin cambios de arquitectura.