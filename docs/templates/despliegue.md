# 🚀 Plantilla de Guía de Despliegue (Deployment)

> **Ubicación:** `docs/templates/despliegue.md`  
> *Plantilla estándar para documentar los pasos de puesta en producción o ejecución local de la aplicación.*

---

## Guía de Despliegue: [Entorno / Componente]

### Prerrequisitos
- Versión de Python requerida (ej. Python 3.11+).
- Cuentas o servicios necesarios (ej. Tenancy de OCI, API Key de Gemini).

### 1. Configuración del Entorno
Crear y activar el entorno virtual:
```bash
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate en Windows
```

Instalar dependencias:
```bash
pip install -r requirements.txt
```

### 2. Configuración de Variables de Entorno
Copiar el archivo de ejemplo y rellenar las credenciales:
```bash
cp .env.example .env
```
*(Completar los valores de `GEMINI_API_KEY`, credenciales OCI, etc.)*

### 3. Ejecución de Verificación (Tests)
Correr la suite de pruebas para validar el estado del sistema:
```bash
pytest tests/ -v
```

### 4. Puesta en Marcha
Comando para levantar la interfaz o el pipeline:
```bash
streamlit run src/interface/app.py
```
