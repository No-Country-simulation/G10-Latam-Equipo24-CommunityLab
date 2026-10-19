# Despliegue del webhook de Telegram en Render

> Alternativa sin VM propia para publicar el webhook de Telegram cuando la
> instancia Always Free de OCI no pudo crearse (error de capacidad al crear la
> instancia). Render expone `scripts/run_webhook.py` en una URL HTTPS pública
> y estable. Ver también
> [Despliegue del dashboard en Streamlit Community Cloud](deploy-streamlit-cloud.md).

---

## Qué resuelve

Una URL HTTPS pública y estable para el webhook de Telegram (`POST /telegram`),
sin crear una VM:

| Necesidad del webhook | Cómo la cubre Render |
|-----------------------|----------------------|
| HTTPS con certificado válido (Telegram no acepta autofirmados) | TLS administrado por Render y dominio estable `https://<servicio>.onrender.com` (la URL exacta la da Render al crear el servicio) |
| Servidor siempre direccionable (la URL del túnel de Cloudflare cambia en cada arranque) | URL fija mientras el servicio exista |
| Ejecutar el mismo código del repo | El Blueprint lee `render.yaml` de la rama `main` y despliega en cada push |

El servicio free tiene **512 MB de memoria y 0.1 CPU**, se duerme a los
**15 minutos sin tráfico** (cold start de ~1 min) y su filesystem es
**efímero** (todo lo escrito en disco se pierde en cada deploy).

---

## Requisitos previos

| Requisito | Detalle |
|-----------|---------|
| Cuenta de Render | [render.com](https://render.com), plan Free |
| Acceso al repo | Permiso para conectar el repositorio de GitHub al Blueprint |
| Credenciales de Telegram | `TELEGRAM_BOT_TOKEN` y `TELEGRAM_WEBHOOK_SECRET` del `.env` local |
| Credenciales OCI | Las tiene Emma (ver tabla del paso 2) y la clave privada `.pem` |
| `.env` local completo | Es la fuente de casi todos los valores a cargar en Render |

---

## Orden importante

Render lee el Blueprint (`render.yaml`) desde la **rama por defecto** del
repositorio. Este cambio debe estar **mergeado a `main` antes de crear el
Blueprint** en Render: si se crea primero, el Blueprint falla porque no
encuentra `render.yaml`.

---

## Paso 1: crear el Blueprint

1. Entrar a [render.com](https://render.com) y abrir el dashboard.
2. **New +** → **Blueprint** → conectar el repositorio
   `No-Country-simulation/G10-Latam-Equipo24-CommunityLab`.
3. Render detecta `render.yaml` y propone un único servicio,
   `communitylab-webhook`.
4. **Apply**. Render hace el primer build (`pip install -r requirements.txt`)
   y arranca el servicio con `python scripts/run_webhook.py --host 0.0.0.0
   --port $PORT`.

Detalles del Blueprint que conviene conocer:

- `plan: free` está declarado explícitamente: el plan por defecto del
  blueprint es de pago (`0.5c-512mb`).
- La región es `oregon`: Render no tiene región en Sudamérica y `oregon` es
  la región por defecto.
- `PYTHON_VERSION=3.11.9` fija el intérprete en la misma versión que valida
  el CI (Python 3.11); sin ese pin, Render usaría su versión por defecto
  (3.14.8 desde el 12/10/2026), más nueva que la del proyecto.
- `autoDeployTrigger` queda sin declarar: Render usa su default (`commit`),
  o sea redespliegue automático en cada push a `main`.

### La URL del servicio

Al terminar el primer build, Render muestra la URL pública en la parte
superior del servicio (y en **Settings → URL**). **Anotala**, porque es la base
que usan los pasos 4, 5 y el keep-warm.

> **La URL NO es necesariamente `communitylab-webhook.onrender.com`.** El campo
> `name` del blueprint nombra el servicio, pero Render puede ajustar el
> subdominio si el nombre ya está tomado (el caso real quedó en
> `g10-latam-equipo24-communitylab.onrender.com`). **No la adivines: copiala
> del panel.**

En todos los comandos de esta guía, `<base>` es esa URL **sin barra final y sin
path**. El health check cuelga de `<base>/health` y el webhook de Telegram se
registra en `<base>/telegram`.

---

## Paso 2: completar las variables de entorno

Al crear el Blueprint, Render pide los valores de las variables marcadas
`sync: false`. **Sólo las pregunta en la creación inicial**: después hay que
cargarlas a mano desde el panel (**Environment** → **Environment Variables**).

| Variable | ¿Secreta? | De dónde sale el valor |
|----------|-----------|------------------------|
| `COMMUNITYLAB_LLM_BACKEND` | Sí (`sync: false`) | `.env` local |
| `OLLAMA_BASE_URL` | Sí (`sync: false`) | `.env` local |
| `OLLAMA_API_KEY` | Sí (`sync: false`) | `.env` local |
| `OLLAMA_MODEL` | Sí (`sync: false`) | `.env` local |
| `GEMINI_API_KEY` | Sí (`sync: false`) | `.env` local |
| `OPENAI_API_KEY` | Sí (`sync: false`) | `.env` local |
| `TELEGRAM_BOT_TOKEN` | Sí (`sync: false`) | `.env` local |
| `TELEGRAM_WEBHOOK_SECRET` | Sí (`sync: false`) | `.env` local |
| `TELEGRAM_WEBHOOK_ORIGEN` | Sí (`sync: false`) | `.env` local |
| `TELEGRAM_CHAT_ID` | Sí (`sync: false`) | `.env` local |
| `OCI_USER_ID` | Sí (`sync: false`) | Emma (credenciales OCI) |
| `OCI_FINGERPRINT` | Sí (`sync: false`) | Emma (credenciales OCI) |
| `OCI_TENANCY_ID` | Sí (`sync: false`) | Emma (credenciales OCI) |

Las variables no secretas (`PYTHON_VERSION`, `OCI_REGION`, `OCI_NAMESPACE`,
`OCI_BUCKET_NAME` y `OCI_PRIVATE_KEY_PATH`) ya vienen con valor en
`render.yaml` y no requieren acción.

> **Nunca** subas el `.env` al repositorio: está en `.gitignore` y contiene
> credenciales reales. Los valores se copian del `.env` local, uno por uno.

---

## Paso 3: subir la clave privada de OCI (Secret File manual)

El archivo `.pem` de la API key de OCI **no se puede declarar en el
Blueprint**; se sube a mano:

1. En el servicio: **Environment** → **Secret Files** → **Add Secret File**.
2. **Filename:** `oci_api_key.pem` (nombre exacto).
3. Pegar el contenido del `.pem` (límite de 1 MB por archivo).
4. Guardar.

El servicio monta el archivo en `/etc/secrets/oci_api_key.pem`, que es
justamente el valor de `OCI_PRIVATE_KEY_PATH` declarado en `render.yaml`.

Dos advertencias sobre el filesystem:

- El filesystem es **efímero**: los snapshots locales del pipeline
  (`storage/`) se pierden en cada deploy. El almacenamiento real es el bucket
  de OCI (`communitylab-activos-marketing`).
- Si falta el Secret File, el pipeline no falla: degrada a snapshot local con
  status `pendiente` (misma degradación que sin credenciales).

---

## Paso 4: verificar el health check

```bash
curl <base>/health
# Esperado: {"status": "ok"}
```

La primera llamada después de 15 min sin tráfico tarda ~1 min (cold start);
si responde, el servicio está vivo y Render marca el health check en verde.

---

## Paso 5: registrar el webhook en Telegram

```bash
scripts/set_webhook_url.sh <base>
```

El script:

1. Lee `TELEGRAM_BOT_TOKEN` y `TELEGRAM_WEBHOOK_SECRET` del `.env` local (el
   token nunca se tipea en el shell, así que no queda en `~/.bash_history`).
2. Registra `<base>/telegram` con `setWebhook` (mismos parámetros que
   `scripts/run_webhook_tunnel.sh`).
3. Consulta `getWebhookInfo` y muestra `url`, `pending_update_count` y
   `last_error_message`.

Verificación manual:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Esperado: `"url": "<base>/telegram"`,
`"pending_update_count": 0` y `"last_error_message": ""`.

---

## Keep-warm: mantener el servicio despierto

El servicio free se duerme a los **15 minutos sin tráfico**. El workflow
`.github/workflows/keep-warm-webhook.yml` hace un ping a `/health` cada
**10 minutos** (`cron: "*/10 * * * *"`), lo que mantiene el servicio
despierto.

- Lee la URL base desde la variable de repositorio **`WEBHOOK_HEALTH_URL`**
  (sin barra final), definida en **Settings → Secrets and variables →
  Actions → Variables**. El valor es `<base>`, la misma URL de los pasos 4 y 5
  (p. ej. `https://g10-latam-equipo24-communitylab.onrender.com`). Tiene que
  ser **la URL real del panel**, no un nombre supuesto: si apunta a un servicio
  inexistente, el ping recibe 404 y el workflow falla sin decir por qué.
- Si la variable no está definida, el workflow lo avisa con un `::notice::`
  y termina sin fallar.
- Los cron sólo corren desde la rama por defecto del repo, y GitHub
  desactiva los workflows programados tras 60 días sin actividad en el
  repositorio.

**Presupuesto (importante):** un servicio siempre despierto consume
**744 h/mes**, casi todo el allowance de **750 instance-hours/mes por
workspace** de Render (compartido entre todos los servicios free del
workspace). Cualquier otro servicio free creado en el mismo workspace puede
quedar suspendido por exceder la cuota. Alternativa sin GitHub Actions:
programar el ping en [cron-job.org](https://cron-job.org) (cada 10 min,
`GET /health`) y desactivar el workflow del repo.

---

## Limitaciones y riesgos

- **Cold start de ~1 min.** Tras 15 min sin tráfico el servicio se apaga;
  Telegram encola los updates hasta 24 h y reintenta mientras no reciba 200,
  así que el primer mensaje después del reposo puede demorar ~1 min en
  responder.
- **Recursos acotados:** 0.1 CPU y 512 MB, compartidos con todo el proceso
  (webhook + pipeline).
- **Sin región en Sudamérica:** se usa `oregon`; la latencia desde Chile
  suma al tiempo de respuesta.
- **Plan free sin SLA:** sin garantía de disponibilidad ni de tiempo de
  respuesta; depósitos y despliegues pueden demorar.
- **Filesystem efímero:** ver paso 3.

---

## Riesgo conocido (trabajo pendiente)

`POST /telegram` ejecuta el pipeline completo **antes** de responder el 200.
Con un modelo remoto (Ollama cloud / Gemini / OpenAI) ese tiempo puede
superar el timeout de lectura de Telegram y la API marca el update como
fallido. El dedupe por `update_id` evita reprocesar los updates que ya
entraron, así que no hay doble ejecución, pero **el mensaje puede no
contestarse**.

La solución correcta es responder 200 de inmediato y procesar el update en
segundo plano. Queda anotado como trabajo pendiente; no está implementado en
este cambio.

---

## Troubleshooting

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| El deploy falla en el build o al arrancar | Versión de Python distinta a la del proyecto | Verificar `PYTHON_VERSION=3.11.9` en **Environment Variables**; el valor debe ir completo (con patch) |
| El pipeline nunca sube a OCI (status `pendiente`) | El Secret File no se lee | Revisar que el archivo se llame `oci_api_key.pem` en **Secret Files** y que `OCI_PRIVATE_KEY_PATH` sea `/etc/secrets/oci_api_key.pem` |
| El health check queda rojo en Render | El proceso no arranca o tarda más que el timeout | Revisar los logs del servicio; verificar localmente `./venv/bin/python scripts/run_webhook.py` |
| `POST /telegram` responde 401 | El `TELEGRAM_WEBHOOK_SECRET` cargado en Render no coincide con el que se registró con `setWebhook` | Re-cargar la variable en Render con el valor del `.env` y volver a correr `scripts/set_webhook_url.sh` |
| El bot no responde en Telegram | El registro del webhook falló o hay error de entrega | Ejecutar `getWebhookInfo` y leer `last_error_message` y `pending_update_count` |
| El primer mensaje tarda ~1 min | El servicio estaba dormido (cold start) | Esperar; con el keep-warm activo casi no ocurre |
| El workflow **Keep-warm del webhook** falla con 404 | `WEBHOOK_HEALTH_URL` apunta a una URL que no es la del servicio (p. ej. un nombre supuesto, o con `/health` pegado) | Copiar la URL exacta del panel de Render, **sin barra final y sin path**, y actualizar la variable de repositorio |

---

*Guía complementaria: [Despliegue del dashboard en Streamlit Community Cloud](deploy-streamlit-cloud.md).*
