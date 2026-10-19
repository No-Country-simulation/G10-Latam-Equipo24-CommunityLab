# Guía de despliegue y configuración — CommunityLab

> Cómo pasar de cero a la aplicación funcionando, y cómo desplegarla en cada
> uno de los entornos disponibles.
>
> Documentos complementarios, con el detalle de cada camino:
> - [Configuración de OCI Object Storage](oci-setup.md)
> - [Despliegue del dashboard en Streamlit Community Cloud](deploy-streamlit-cloud.md)
> - [Despliegue del webhook de Telegram en Render](deploy-render-webhook.md)

---

## 1. Resumen de entornos

CommunityLab puede correr en tres modalidades. No son excluyentes: el dashboard
y el webhook se despliegan por separado porque tienen necesidades distintas.

| Entorno | Qué corre | Dónde | Guía |
|---------|-----------|-------|------|
| Local | Pipeline, panel y pruebas | Tu máquina | Este documento |
| Streamlit Community Cloud | Dashboard de curaduría | Nube administrada | [deploy-streamlit-cloud.md](deploy-streamlit-cloud.md) |
| Render | Webhook de Telegram (`POST /telegram`) | Nube administrada | [deploy-render-webhook.md](deploy-render-webhook.md) |
| OCI (VM) | Reemplazo del despliegue anterior | Oracle Cloud | [oci-setup.md](oci-setup.md) |

> La instancia Always Free de OCI puede no estar disponible (error de capacidad
> al crearla). Las guías de Community Cloud y Render existen justamente como
> alternativa sin VM propia, y son las que usa la demo actual.

---

## 2. Requisitos previos

| Requisito | Detalle |
|-----------|---------|
| Python 3.11+ | El CI usa 3.11 |
| Git | Para clonar y trabajar por ramas |
| Cuenta de Telegram | Solo para el bot y el webhook |
| Cuenta de Oracle Cloud | Solo si vas a usar Object Storage |
| Cuenta de GitHub | Para el repositorio y el CI |

No hace falta Node.js ni ninguna herramienta adicional.

---

## 3. Configuración local

### 3.1. Clonar el repositorio

```bash
git clone https://github.com/No-Country-simulation/G10-Latam-Equipo24-CommunityLab.git
cd G10-Latam-Equipo24-CommunityLab
```

### 3.2. Crear el entorno virtual

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3.3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3.4. Configurar variables de entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
# Backend de análisis: rule_based | ollama | openai | gemini
# rule_based no usa red ni credenciales (determinista, ideal para tests).
COMMUNITYLAB_LLM_BACKEND=rule_based

# Backend Ollama (el que usa la demo)
OLLAMA_BASE_URL=https://ollama.com/v1
OLLAMA_MODEL=gemma4:31b
OLLAMA_API_KEY=tu_api_key_de_ollama

# Telegram (bot y webhook)
TELEGRAM_BOT_TOKEN=tu_token_del_bot
TELEGRAM_WEBHOOK_SECRET=un_texto_secreto_a_eleccion

# OCI Object Storage (opcional; ver docs/oci-setup.md)
OCI_USER_ID=ocid1.user.oc1..xxxxx
OCI_TENANCY_ID=ocid1.tenancy.oc1..xxxxx
OCI_FINGERPRINT=xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
OCI_PRIVATE_KEY_PATH=/home/tu_usuario/.oci/oci_api_key.pem
OCI_REGION=sa-valparaiso-1
```

> **Importante:** `.env` está en `.gitignore`. Nunca se sube al repositorio.

Si no configurás OCI, el pipeline **degrada limpiamente**: guarda el paquete de
distribución en `storage/activos/` (local, ignorado por git) en lugar de subirlo
a Object Storage. Nunca falla por falta de credenciales.

### 3.5. Verificar la instalación

```bash
# Dependencias y versión de Python
python --version

# Suite de pruebas
python -m pytest -q
```

La suite completa pasa en verde sin necesidad de credenciales ni red.

---

## 4. Formas de ejecutar el sistema

### 4.1. Pipeline sobre un archivo (camino principal)

El camino por archivo siempre funciona, con o sin LLM remoto:

```bash
# Con el backend configurado en .env
python scripts/run_demo.py data/sample/demo_fixed.json

# Forzando el backend determinista, sin red ni credenciales
python scripts/run_demo.py data/sample/demo_fixed.json --offline

# Varios archivos a la vez
python scripts/run_demo.py dataset.json dataset2.csv
```

Opciones útiles: `--backend <rule_based|ollama|openai|gemini>` y
`--model <nombre>`. El snapshot queda en
`storage/activos/paquete-distribucion-<fecha>.json` cuando no hay credenciales
OCI configuradas.

### 4.2. Panel de curaduría (Streamlit)

```bash
make run      # cierra instancias previas y abre el panel
make status   # indica si está arriba y en qué puerto
make stop     # cierra las instancias del panel
```

El panel corre en `http://localhost:8502` (puerto fijado en
`.streamlit/config.toml`). `make run` resuelve la ruta del repo y exporta
`PYTHONPATH`, así que funciona aunque lo invoques desde otro directorio.

### 4.3. Webhook HTTP (ingesta en tiempo real)

```bash
python scripts/run_webhook.py
python scripts/run_webhook.py --backend ollama --model gemma4:31b
python scripts/run_webhook.py --host 0.0.0.0 --port 8765 --secret mi_secreto
```

Rutas expuestas:

| Ruta | Método | Respuesta |
|------|--------|-----------|
| `/health` | GET | `{"status": "ok"}` |
| `/ingest` | POST | `{status, resumen, activos, almacenamiento}` |
| `/telegram` | POST | Resumen del pipeline; sin el secret configurado responde 503 |

Ejemplo de verificación local:

```bash
curl http://localhost:8765/health
# -> {"status": "ok"}
```

### 4.4. Bot interactivo de Telegram

```bash
python scripts/run_bot.py
python scripts/run_bot.py --backend ollama --model gemma4:31b
```

El bot responde a cada mensaje con el análisis del pipeline. Es un diferencial
del demo, nunca el camino obligatorio.

### 4.5. Otros scripts

| Script | Para qué |
|--------|----------|
| `scripts/run_timeline_demo.py` | Demo sobre datos de línea de tiempo |
| `scripts/ingest_telegram.py` | Ingesta puntual desde Telegram |
| `scripts/generar_muestra.py` | Genera una muestra de datos sintéticos |
| `scripts/run_webhook_tunnel.sh` | Publica el webhook vía túnel (ver advertencia abajo) |

> **Advertencia sobre el túnel:** `run_webhook_tunnel.sh start` re-registra el
> webhook de Telegram contra la URL de Cloudflare. Si ya hay un webhook activo
> en Render, **lo pisa**. No corras `start` si el webhook de producción está en
> uso; `stop` no toca Telegram.

---

## 5. Estructura de la salida

El pipeline produce un `OutputBatch` con esta forma:

```json
{
  "batch_id": "sample-001",
  "analysis": [],
  "decisions": [],
  "assets": {},
  "summary": {},
  "alerts": [],
  "oci_storage": {},
  "visualization": {}
}
```

El campo `assets` (activos de distribución) puede venir vacío: eso significa que
el lote no calificó para generar activos, no que el LLM haya fallado. La señal
correcta está en `analysis[].relevance.is_marketing_worthy` y en
`analysis[].categorization.category`.

---

## 6. Verificación antes de la demo

```
[ ] La suite de pruebas pasa: python -m pytest -q
[ ] El pipeline procesa un dataset de ejemplo sin errores
[ ] El panel carga en http://localhost:8502
[ ] El panel de curaduría permite aprobar y descargar activos
[ ] /health responde {"status": "ok"}
[ ] Si hay credenciales OCI: el paquete se sube a Object Storage
[ ] Si no hay credenciales OCI: se guarda el snapshot local sin romper
[ ] El CI pasa en GitHub Actions
[ ] La protección de rama y CODEOWNERS están activos (ver sección 7)
```

---

## 7. Configuración de GitHub

| Elemento | Estado |
|----------|--------|
| Repositorio | `github.com/No-Country-simulation/G10-Latam-Equipo24-CommunityLab` |
| Rama por defecto | `main` |
| Protección de `main` | 1 aprobación + code owner + check `test` + estricto al día |
| CODEOWNERS | `@emanuelperacchia`, `@Rox-0864`, `@itanflores` |
| CI | `.github/workflows/ci.yml` |
| Validación de PR | `.github/workflows/pr-validation.yml` (exige exactamente un label `type:*`) |

> La protección de `main` tiene `dismiss_stale_reviews` activo: **no conviene
> pushear a un PR ya aprobado**, porque la aprobación se descarta. Para dejar un
> PR listo para mergear conviene actualizarlo con `main` antes de pedir review.

---

## 8. Solución de problemas comunes

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| `ModuleNotFoundError: No module named 'src'` | Falta `PYTHONPATH` | Usar `make run` (lo exporta) o exportarlo a mano |
| El panel responde 200 pero muestra un error | Falta `PYTHONPATH` al invocar streamlit directo | Usar `make run` |
| `OCI credentials not configured` | Faltan variables de OCI | Es esperado sin credenciales; guarda snapshot local |
| El puerto 8502 sigue ocupado | Quedó una instancia previa | `make stop` |
| El webhook responde 503 en `/telegram` | Falta `TELEGRAM_WEBHOOK_SECRET` | Definirlo en `.env` o pasarlo con `--secret` |
| `409 Conflict` en `getUpdates` | Hay un webhook activo | Es una protección: Telegram no permite long polling con webhook activo |
| Los tests fallan | Dependencias faltantes | `pip install -r requirements.txt` |

---

*Guía de despliegue de CommunityLab — Oracle ONE Hackathon G10.*
