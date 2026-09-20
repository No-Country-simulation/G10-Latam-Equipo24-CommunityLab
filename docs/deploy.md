# 🚀 GUÍA DE DESPLIEGUE Y CONFIGURACIÓN — CommunityLab

> Paso a paso para tener la aplicación funcionando desde cero hasta el despliegue en OCI.

---

## 📋 FASE 0: PREREQUISITOS

Antes de empezar, necesitás:

| Requisito | Cómo obtenerlo |
|-----------|----------------|
| **Cuenta GitHub** | github.com (ya tenés una) |
| **Cuenta Oracle Cloud** | cloud.oracle.com (gratis, Always Free) |
| **API Key Gemini** | aicentral.google.com o ajusting.google.dev |
| **Python 3.11+** | python.org |
| **Git** | git-scm.com |
| **Node.js** | nodejs.org (opcional para algunas herramientas) |

---

## 🔧 FASE 1: CONFIGURACIÓN LOCAL (Sprint 1)

### Paso 1.1: Clonar el repo

```powershell
git clone https://github.com/emanuelperacchia/communitylab.git
cd communitylab
```

### Paso 1.2: Crear entorno virtual

```powershell
python -m venv venv
venv\Scripts\activate
```

### Paso 1.3: Instalar dependencias

```powershell
pip install -r requirements.txt
```

### Paso 1.4: Configurar variables de entorno

Crear archivo `.env` en la raíz del proyecto:

```env
# Gemini API Key
GEMINI_API_KEY=tu_api_key_aqui

# OCI Credentials (para cuando despliegues)
OCI_USER_ID=ocid1.user.oc1..xxxxx
OCI_TENANCY_ID=ocid1.tenancy.oc1..xxxxx
OCI_FINGERPRINT=xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
OCI_PRIVATE_KEY_PATH=C:\Users\TU_USUARIO\.oci\oci_api_key.pem
OCI_REGION=sa-santiago-1
```

> **IMPORTANTE:** El archivo `.env` está en `.gitignore`. NO se sube al repo.

### Paso 1.5: Verificar que funciona localmente

```powershell
# Verificar Python
python --version
# Debe mostrar: Python 3.11.x

# Verificar dependencias
pytest tests/ -v
# Debe mostrar tests pasando (o 0 failed)
```

---

## ☁️ FASE 2: CONFIGURACIÓN DE OCI (Sprint 4)

### Paso 2.1: Crear cuenta en Oracle Cloud

1. Ir a https://cloud.oracle.com
2. Crear cuenta (gratis, Always Free tier)
3. Verificar email
4. Completar perfil

### Paso 2.2: Crear API Key

1. En Oracle Cloud Console → Menu (☰) → Identity & Security → Users
2. Click en tu usuario
3. Pestaña **"API Keys"**
4. Click **"Add API Key"**
5. Descargar el archivo `.pem` (la clave privada)
6. Copiar la **Fingerprint** (la huella digital)
7. Copiar el **User OCID** (ID del usuario)
8. Copiar el **Tenancy OCID** (ID del tenancy)

### Paso 2.3: Guardar credenciales localmente

```powershell
# Crear carpeta para OCI
mkdir C:\Users\WIN10\.oci

# Mover el archivo .pem descargado ahí
# C:\Users\WIN10\.oci\oci_api_key.pem
```

Actualizar `.env` con los datos de OCI:
```env
OCI_USER_ID=ocid1.user.oc1..xxxxx
OCI_TENANCY_ID=ocid1.tenancy.oc1..xxxxx
OCI_FINGERPRINT=xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
OCI_PRIVATE_KEY_PATH=C:\Users\WIN10\.oci\oci_api_key.pem
OCI_REGION=sa-santiago-1
```

### Paso 2.4: Crear Object Storage Bucket

1. Oracle Cloud Console → Menu → Object Storage
2. Click **"Create Bucket"**
3. Nombre: `communitylab-activos-marketing`
4. Region: sa-santiago-1 (o la más cercana)
5. Storage Tier: Standard
6. Click **"Create"**

### Paso 2.5: Verificar conexión localmente

```powershell
# Activar entorno virtual
venv\Scripts\activate

# Abrir Python
python

# Probar conexión
from src.oci.client import OCIClient
client = OCIClient()
print(client.test_connection())
# Debe mostrar: ✅ Conexión con OCI exitosa
```

---

## 🧪 FASE 3: TESTING LOCAL (Sprint 5 - antes del despliegue)

### Paso 3.1: Crear dataset de prueba

Crear archivo `data/raw/communitylab-sample.json`:

```json
{
  "batch_id": "sample-001",
  "source": "discord",
  "channel": "#testimonios",
  "processed_at": "2026-09-21T10:00:00Z",
  "interactions": [
    {
      "id": "msg-001",
      "content": "Me encantó el curso, me contrataron!",
      "author": "estudiante-01",
      "channel": "#testimonios",
      "timestamp": "2026-09-15T14:30:00Z",
      "metadata": {"reactions": 5}
    },
    {
      "id": "msg-002",
      "content": "No entiendo cómo usar LangGraph",
      "author": "estudiante-02",
      "channel": "#ayuda",
      "timestamp": "2026-09-15T15:00:00Z",
      "metadata": {"reactions": 2}
    },
    {
      "id": "msg-003",
      "content": "Excelente docente, muy claro todo",
      "author": "estudiante-03",
      "channel": "#testimonios",
      "timestamp": "2026-09-15T16:00:00Z",
      "metadata": {"reactions": 8}
    }
  ]
}
```

### Paso 3.2: Ejecutar pipeline completo localmente

```powershell
python -c "
from src.pipeline import run_pipeline

# Cargar dataset
from src.ingest.input_loader import JSONInputLoader
loader = JSONInputLoader()
data = loader.load('data/raw/communitylab-sample.json')

# Ejecutar pipeline
result = run_pipeline(data)

# Mostrar resultados
import json
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

### Paso 3.3: Verificar salida JSON

El resultado debe tener esta estructura:
```json
{
  "batch_id": "sample-001",
  "analysis": [...],
  "decisions": [...],
  "assets": [...],
  "summary": {...},
  "alerts": [...],
  "oci_storage": {...},
  "visualization": {...}
}
```

### Paso 3.4: Probar API localmente

```powershell
# En una terminal, levantar la API
python -c "from src.api.app import app; app.run(port=8000)"

# En otra terminal, probar
curl -X POST http://localhost:8000/procesar \
  -H "Content-Type: application/json" \
  -d @data/raw/communitylab-sample.json
```

### Paso 3.5: Probar Streamlit localmente

```powershell
streamlit run src/interface/app.py --server.port=8501
```

Abrir navegador: `http://localhost:8501`

---

## 🖥️ FASE 4: DESPLIEGUE EN OCI (Sprint 5)

### Paso 4.1: Crear Compute Instance

1. Oracle Cloud Console → Menu → Compute → Instances
2. Click **"Create Instance"**
3. Configuración:
   - **Name:** communitylab
   - **Image:** Ubuntu 22.04 (o la más reciente)
   - **Shape:** VM.Standard.E2.1.Micro (Always Free eligible)
   - **Region:** sa-santiago-1
4. Click **"Create"**

### Paso 4.2: Configurar SSH

```powershell
# Descargar el archivo .pem del Instance (desde OCI Console)
# O usar el que ya tenés

# Conectar al servidor (reemplazar IP)
ssh -i C:\Users\WIN10\.oci\oci_api_key.pem ubuntu@IP_DEL_SERVIDOR
```

### Paso 4.3: Instalar Python en OCI

```bash
# Dentro del servidor OCI
sudo apt update && sudo apt upgrade -y
sudo apt install python3.11 python3.11-venv python3-pip git -y
```

### Paso 4.4: Subir código al servidor

```powershell
# Desde tu PC, subir el código via SCP (reemplazar IP y paths)
scp -i C:\Users\WIN10\.oci\oci_api_key.pem -r ./communitylab ubuntu@IP_DEL_SERVIDOR:/home/ubuntu/communitylab
```

### Paso 4.5: Configurar entorno en OCI

```bash
# Dentro del servidor OCI
cd /home/ubuntu/communitylab

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Crear .env con las mismas variables de tu PC
nano .env
# Pegar las mismas variables (GEMINI_API_KEY, OCI credentials, etc.)
```

### Paso 4.6: Crear bucket en OCI (si no lo creaste)

```bash
# Dentro del servidor OCI, usar OCI CLI
oci os bucket create --namespace-name TU_NAMESPACE --name communitylab-activos-marketing --region sa-santiago-1
```

> **Para obtener TU_NAMESPACE:**
> ```bash
> oci os namespace get
> ```

### Paso 4.7: Levantar Streamlit

```powershell
# Dentro del servidor OCI, en la carpeta del proyecto
source venv/bin/activate
streamlit run src/interface/app.py --server.port=8501 --server.address=0.0.0.0
```

### Paso 4.8: Configurar Firewall (puerto 8501)

En Oracle Cloud Console:
1. Net → Virtual Cloud Networks → tu VCN
2. Security Lists → Default
3. Add Ingress Rules:
   - Source: 0.0.0.0/0
   - Protocol: TCP
   - Destination Port: 8501
4. Save

### Paso 4.9: Verificar despliegue

```powershell
# Desde tu PC, abrir el navegador
http://IP_DEL_SERVIDOR:8501
```

Debe mostrar el dashboard de CommunityLab.

---

## 📋 FASE 5: CONFIGURACIÓN GITHUB COMPLETA

### Paso 5.1: Repo (ya configurado)
- Repo: github.com/emanuelperacchia/communitylab
- Branch Protection: configurado en main
- CODEOWNERS: configurado (Rox revisa código)
- CI/CD: .github/workflows/ci.yml

### Paso 5.2: Invitar equipo
Settings → Collaborators → Add:
- @Elias → Write
- @Rox-0864 → Write
- @Yis-ai-eng → Write
- @Marcelo Rolon → Write
- @Antonio3051 → Write
- @emanuelperacchia → Admin

### Paso 5.3: Configurar GitHub Projects
1. Projects → New Project → Board
2. Nombre: CommunityLab - Hackathon ONE
3. Columnas: Backlog, Todo, En Progreso, Review, Done
4. Campos: Sprint, Priority, Epic, Assignees

### Paso 5.4: Crear las 45 issues
Copiar de `docs/fichas-historias-usuario-v2.md`

### Paso 5.5: Labels y Milestones
Ya creados (verificar en Issues → Labels/Milestones)

---

## 🔍 FASE 6: VERIFICACIÓN FINAL (antes de la demo)

### Checklist de verificación

```
✅ Pipeline procesa sample sin errores
✅ Dashboard carga en localhost:8501
✅ Dashboard carga en IP:8501 (OCI)
✅ Panel de curaduría funciona
✅ Panel de alertas muestra datos
✅ API /procesar retorna JSON válido
✅ API /health retorna {"status": "healthy"}
✅ OCI upload/download funciona
✅ Tests pasan: pytest tests/ -v
✅ CI/CD pasa en GitHub Actions
✅ Branch protection activa
✅ CODEOWNERS funciona
✅ README.md actualizado
✅ docs/deploy.md documentado
```

---

## 📊 RESUMEN DE COMANDOS POR FASE

### Localmente (tu PC)
```powershell
# Setup inicial
cd communitylab
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Testear
pytest tests/ -v

# Pipeline local
python -c "from src.pipeline import run_pipeline; ..."

# API local
python -c "from src.api.app import app; app.run(port=8000)"

# Streamlit local
streamlit run src/interface/app.py --server.port=8501
```

### En OCI (servidor)
```bash
# Instalar Python
sudo apt install python3.11 python3.11-venv git -y

# Subir código (desde tu PC)
scp -r ./communitylab ubuntu@IP:/home/ubuntu/

# Configurar (en servidor)
cd /home/ubuntu/communitylab
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run src/interface/app.py --server.port=8501 --server.address=0.0.0.0
```

---

## 🆘 SOLUCIÓN DE PROBLEMAS COMUNES

| Problema | Causa | Solución |
|----------|-------|----------|
| ModuleNotFoundError | Entorno virtual no activado | `venv\Scripts\activate` |
| OCI connection error | .env mal configurado | Verificar variables de entorno |
| Streamlit no abre | Puerto bloqueado | Verificar firewall (8501) |
| Tests fallan | Dependencias faltantes | `pip install -r requirements.txt` |
| API no responde | No está corriendo | Verificar proceso con `ps aux \| grep python` |
| Bucket no se crea | Namespace incorrecto | `oci os namespace get` para obtener namespace |

---

*Guía de despliegue para CommunityLab — Oracle ONE Hackathon G10*
*Actualizado: Sprint 5*
