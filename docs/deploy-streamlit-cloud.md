# ☁️ Despliegue del dashboard en Streamlit Community Cloud

> Alternativa sin infraestructura propia para publicar el dashboard cuando la
> VM Always Free de OCI no está disponible (error de capacidad al crear la
> instancia). Ver también [Deploy y OCI](deploy.md).

---

## Qué despliega y qué no

| Componente | ¿En Community Cloud? |
|------------|----------------------|
| Dashboard de curaduría (`src/interface/app.py`) | ✅ Sí |
| Pipeline de análisis (se ejecuta dentro de la app) | ✅ Sí |
| Charts y panel de alertas | ✅ Sí |
| Webhook de Telegram (servidor HTTP) | ❌ No — sigue local/túnel |
| Subida a OCI Object Storage | ⚠️ Solo si cargás las credenciales OCI en los secrets |

Community Cloud despliega la app Streamlit como proceso; el webhook de
Telegram necesita un servidor con URL pública, por eso queda fuera y se
mantiene con `scripts/run_webhook_tunnel.sh`.

---

## Configuración previa (una sola vez)

### 1. Secrets en la nube

En la consola de Community Cloud: **App → Settings → Secrets**. Pegar el
siguiente bloque completando solo las claves que se usen:

```toml
# Backend de análisis: "rule_based" (sin LLM) | "ollama" | "gemini" | "openai"
COMMUNITYLAB_LLM_BACKEND = "ollama"

# LLM remoto (opcional)
OLLAMA_BASE_URL = "https://ollama.com/v1"
OLLAMA_MODEL = "gemma4:31b"
OLLAMA_API_KEY = ""

# Telegram (publicación desde el dashboard)
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
TELEGRAM_WEBHOOK_ORIGEN = ""
TELEGRAM_WEBHOOK_SECRET = ""

# OCI Object Storage (opcional: sin esto, el pipeline degrada a snapshot local)
OCI_USER_ID = ""
OCI_FINGERPRINT = ""
OCI_TENANCY_ID = ""
OCI_REGION = "sa-valparaiso-1"
OCI_NAMESPACE = "axcyr94oehmi"
OCI_BUCKET_NAME = "communitylab-activos-marketing"

# Clave privada. En la nube no hay archivo .pem: se pega el CONTENIDO del PEM.
# Es multilínea, así que se abre y se cierra con tres comillas.
OCI_PRIVATE_KEY = """
-----BEGIN PRIVATE KEY-----
<contenido de ~/.oci/oci_api_key.pem, sin la última línea "OCI_API_KEY">
-----END PRIVATE KEY-----
"""
```

`src/interface/cloud_secrets.py` copia cada entrada de `secrets.toml` a
`os.environ` al arrancar la app (sin pisar variables ya definidas), así el
mismo código que lee un `.env` local funciona en la nube.

#### Checklist de 7 variables (readiness)

El pipeline sube a OCI solo cuando las 7 variables están presentes y con valor
(`src/oci/storage.py` → `OCI_REQUIRED_ENV` y `oci_credentials_complete()`).
Si falta alguna, degrada a snapshot local con status `pendiente`: no falla,
pero tampoco sube nada.

- [ ] `OCI_USER_ID` — `ocid1.user.oc1..<unique-id>`
- [ ] `OCI_FINGERPRINT` — huella SHA-1 de la clave pública
- [ ] `OCI_TENANCY_ID` — `ocid1.tenancy.oc1..<unique-id>`
- [ ] `OCI_REGION` — `sa-valparaiso-1`
- [ ] `OCI_NAMESPACE` — `axcyr94oehmi`
- [ ] `OCI_BUCKET_NAME` — `communitylab-activos-marketing`
- [ ] La clave privada: `OCI_PRIVATE_KEY` (nube, contenido inline) **o**
      `OCI_PRIVATE_KEY_PATH` (local, ruta al `.pem`)

#### Cómo llega la clave privada a la nube

El SDK de OCI exige una **ruta a un archivo `.pem`**, y en Community Cloud no
hay sistema de archivos. La app lo resuelve sola: `cloud_secrets.py` toma el
secret inline `OCI_PRIVATE_KEY`, lo escribe en un temporal con permisos `0600`
(`bootstrap_oci_private_key()`) y define `OCI_PRIVATE_KEY_PATH` apuntando ahí.
Ese módulo se importa **antes** de `src.pipeline` y `src.oci` (línea 27 de
`src/interface/app.py`), así que el cliente OCI ya nace con la ruta resuelta.
Si `OCI_PRIVATE_KEY_PATH` apunta a un archivo que existe, ese archivo manda y
el bootstrap no hace nada (es el camino normal en local).

> Al copiar el PEM desde `~/.oci/oci_api_key.pem`, **quitá la última línea**
> (`OCI_API_KEY`): es el fingerprint que la CLI de OCI escribe al final del
> archivo y no forma parte de la clave.

> ⚠️ **Nunca** subas `.streamlit/secrets.toml` al repositorio: contiene
> credenciales reales. El archivo ya está excluido en `.gitignore`; verificá
> igualmente antes de commitear.

### 2. Crear la app

1. Entrar a <https://share.streamlit.io> con la cuenta de GitHub.
2. **Create app → Deploy a public app from GitHub**.
3. Completar:
   - **Repository:** `No-Country-simulation/G10-Latam-Equipo24-CommunityLab`
   - **Branch:** `main`
   - **Main file path:** `src/interface/app.py`
   - **Python version:** 3.11 (la misma que valida el CI en GitHub Actions)
4. **Deploy**. La primera construcción instala `requirements.txt` y tarda
   unos minutos.

---

## Flujo de entrega (la parte "CD")

Con la app conectada al repo, Community Cloud **observa la rama `main`**:
cada merge a `main` redeploya el dashboard automáticamente. El pipeline
completo queda entonces:

```
PR → CI (lint + tests) → code owner review → merge a main → redeploy en la nube
```

> El redeploy lo dispara la plataforma, no un workflow de GitHub Actions: no
> hace falta `deploy.yml` ni secrets de SSH en el repo. La "D" la ejecuta
> Streamlit Cloud sobre el mismo `main` que ya validó el CI.

---

## Verificación

- [ ] La app abre en la URL `https://<nombre>.streamlit.app`.
- [ ] El panel de curaduría muestra la muestra del demo sin errores.
- [ ] Los charts renderizan con la paleta de marca.
- [ ] Si se cargaron credenciales OCI, el estado de almacenamiento es
      `guardado_con_exito`; si no, es `pendiente` (degradación esperada).
- [ ] El log del deploy no muestra errores de autenticación de OCI (con las
      7 variables cargadas, el estado debe ser `guardado_con_exito` y no
      `pendiente`).

---

## Limitaciones conocidas

- **Repo público.** Todo el código queda visible (el repo ya es público).
  Los secrets no se exponen, pero el contenido de `data/` sí.
- **Sin clave privada** (`OCI_PRIVATE_KEY` en la nube, `OCI_PRIVATE_KEY_PATH`
  en local) el pipeline no sube a OCI: degrada a snapshot local con status
  `pendiente`.
- **El webhook de Telegram no corre acá** (ver tabla inicial).
- **Recursos compartidos:** las apps gratuitas pueden dormirse por inactividad.

---

## Si el deploy falla con "Error running app"

Ese mensaje es genérico: siempre hay que mirar los **logs del deploy** (botón
*Manage app* en la esquina inferior derecha de la página de error) para ver la
causa real. Los dos problemas que ya aparecieron:

### 1. La app arranca en otro puerto

En los logs:

```
Uvicorn server started on :::8502
❗️ error while checking the health of the Streamlit app:
   Get "http://localhost:8501/healthz": connect: connection refused
```

Community Cloud verifica la salud de la app en el **puerto 8501**. Si
`.streamlit/config.toml` fija `server.port`, la app escucha en otro puerto y el
health check nunca conecta. **Ese archivo no debe fijar el puerto**: el puerto
local se pasa por línea de comandos (`make run`, ver `PORT` en el `Makefile`).

### 2. `ModuleNotFoundError: No module named 'src'`

Streamlit agrega al `sys.path` únicamente el directorio del archivo principal
(`src/interface/`), nunca la raíz del repo, aunque el directorio de trabajo sea
la raíz. Por eso `src/interface/app.py` inserta la raíz del repo en `sys.path`
antes de importar `src.*`. Si se mueve ese bloque, el panel funciona en local
con `make run` (que exporta `PYTHONPATH`) pero rompe en la nube.

### 3. El PEM pegado con los saltos de línea escapados

En los logs:

```
oci.exceptions.ClientException: Could not parse private key
```

El SDK de OCI no entiende un `\n` literal: el contenido del secret tiene que
llegar con saltos de línea reales. En el editor de secrets eso se logra con una
cadena multilínea de TOML (`OCI_PRIVATE_KEY = """…"""`), no con
`"-----BEGIN…\nMIIE…\n-----END…"` en una sola línea. Revisá que el bloque
arranque con `-----BEGIN PRIVATE KEY-----` y termine con
`-----END PRIVATE KEY-----` en su propia línea.

### 4. La clave pegada con la línea `OCI_API_KEY` al final

El archivo que genera la CLI (`~/.oci/oci_api_key.pem`) termina con una línea
`OCI_API_KEY` que es el fingerprint, no parte de la clave. Si se pega tal cual,
el parseo del PEM falla igual que en el caso anterior. Se borra esa línea: el
fingerprint ya viaja aparte, en `OCI_FINGERPRINT`.

---

*Guía creada para el despliegue de demostración — Oracle ONE Hackathon G10.*
