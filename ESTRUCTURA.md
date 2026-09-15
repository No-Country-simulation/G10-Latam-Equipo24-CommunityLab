# 📁 Estructura del Proyecto — CommunityLab

## Organización por carpetas

```
communitylab/
│
├── src/                          ← Código fuente
│   ├── domain/                   ← 🧠 Modelos y contratos del negocio
│   │                           (Message, Sentiment, interfaces)
│   │
│   ├── ingest/                   ← 📥 Paso 1: Entrada de datos
│   │                           (carga JSON/CSV, normalización, validación)
│   │
│   ├── analysis/                 ← 🧠 Paso 2: Análisis con IA
│   │                           (sentimiento, categorización, relevancia)
│   │
│   ├── decisions/                ← 🚦 Paso 3: Motor de decisiones
│   │                           (qué hacer con cada mensaje)
│   │
│   ├── generators/               ← ✍️ Paso 4: Generar activos
│   │                           (LinkedIn, newsletter, FAQ, testimonios)
│   │
│   ├── oci/                      ← ☁️ Integración Oracle Cloud
│   │                           (subir/descargar archivos)
│   │
│   ├── prompts/                  ← 💬 Templates de prompts
│   │                           (plantillas para el LLM)
│   │
│   └── api/                      ← 🔌 API (opcional)
│                               (endpoints FastAPI)
│
├── tests/                        ← 🧪 Tests por módulo
│
├── data/                         ← 📦 Datasets
│   ├── raw/                      ← Datos sin procesar
│   └── processed/                ← Datos ya procesados
│
├── docs/                         ← 📚 Documentación
│                               (diagramas, decisiones, guías)
│
└── .github/workflows/            ← 🤖 CI automático
                                (tests en cada PR)
```

---

## 🎯 Regla de trabajo

**Cada persona trabaja en SU carpeta:**

| Persona | Carpeta | Tarea |
|---------|---------|-------|
| **Miembro A** | `src/ingest/` | Carga y normalización de datos |
| **Miembro B** | `src/analysis/` | Análisis de sentimiento y categorías |
| **Miembro C** | `src/decisions/` | Motor de decisiones |
| **Miembro D** | `src/generators/` | Generadores de contenido |
| **Admin (Tú)** | `src/domain/`, `src/oci/`, `docs/` | Modelos base, cloud, docs |

**Si necesitás algo de otra carpeta → preguntá por Discord, NO toques el archivo.**

---

## 📝 Archivos en cada carpeta

Cada carpeta tiene un `__init__.py` (vacío por ahora) que indica que es un módulo Python.

Cuando arranques a programar, creás los archivos `.py` que necesites dentro de tu carpeta.
