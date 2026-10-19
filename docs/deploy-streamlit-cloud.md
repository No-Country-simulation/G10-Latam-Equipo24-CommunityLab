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
```

`src/interface/cloud_secrets.py` copia cada entrada de `secrets.toml` a
`os.environ` al arrancar la app (sin pisar variables ya definidas), así el
mismo código que lee un `.env` local funciona en la nube.

> ⚠️ **Nunca** subas `.streamlit/secrets.toml` al repositorio: contiene
> credenciales reales. El archivo ya está excluido en `.gitignore`; verificá
> igualmente antes de commitear.
>
> **Nota sobre `OCI_PRIVATE_KEY_PATH`:** la app espera una **ruta a un archivo
> `.pem`**, que no existe en Community Cloud. Para subir a OCI desde la nube
> hay que montar la clave dentro del contenedor de la app, por ejemplo
> escribiendo el contenido PEM desde un secret a un archivo temporal en un
> arranque previo. Si no se hace, el pipeline degrada a snapshot local con
> status `pendiente` (nada falla).

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

---

## Limitaciones conocidas

- **Repo público.** Todo el código queda visible (el repo ya es público).
  Los secrets no se exponen, pero el contenido de `data/` sí.
- **Sin credenciales PEM** no se puede subir a OCI desde la nube.
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

---

*Guía creada para el despliegue de demostración — Oracle ONE Hackathon G10.*
