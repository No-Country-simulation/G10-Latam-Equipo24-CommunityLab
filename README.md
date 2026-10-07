# 🚀 CommunityLab — Motor Inteligente de Transformación y Distribución para Comunidades Digitales

> **Hackathon ONE G10 — Oracle Next Education & Alura**
> Convierte la actividad orgánica de una comunidad digital en activos de marketing listos para publicar.

---

## 🎯 Objetivos

- **Ingerir** interacciones de comunidades digitales (Discord, Slack, foros, Mastodon).
- **Analizar** cada mensaje con LLMs (sentimiento, categoría, relevancia) en **una sola llamada**.
- **Decidir** automáticamente qué activo generar (LinkedIn, FAQ, newsletter) según el `tipo`.
- **Generar** los activos de marketing listos para publicar.
- **Persistir** todo en **OCI Object Storage** (capa Always Free).
- **Automatizar** el flujo completo en un pipeline único y testeable — objetivo 4 del desafío (n8n / LangChain / LangGraph **o equivalentes**: elegimos pipeline Python pura, ver [arquitectura](docs/arquitectura.md)).

---

## ⚠️ Estado actual

| Módulo | Estado |
|---|---|
| Contrato de datos (modelos) | ✅ Listo |
| Cliente LLM (Gemini / OpenAI / Ollama local+nube / rule_based) | ✅ Listo |
| Ingesta (loader + normalizer + Mastodon) | ✅ Listo |
| Detector de dudas recurrentes | ✅ Listo |
| Análisis unificado (sentimiento/categoría/relevancia) | ✅ Listo |
| Motor de decisiones | ✅ Listo (reglas + LLM) |
| Generadores (LinkedIn / newsletter / FAQ) | ✅ PR #86 mergeado |
| Automatización del flujo (pipeline) | 🟡 Cableado S3-005 en PR #90 (en revisión) |
| OCI Object Storage | ✅ Listo (cliente + upload en pipeline con fallback local) |
| Interfaz Streamlit | ✅ Listo (curaduría + edición + descarga de activos) |
| Tests | ✅ 159 tests |

> Este README describe el **objetivo**. El estado real se rastrea en los issues del repo (#86 y #89 mergeados; el cableado del pipeline viaja en el PR #90).

---

## 📐 Contrato de datos (INNEGOCIABLE)

El sistema consume y produce **exactamente** estos JSON, definidos en el desafío. Los modelos de `src/domain/models.py` reflejan este contrato 1:1. **Si tocás un campo, corré `pytest tests/test_contract.py`.**

### Entrada

```json
{
  "origen_comunidad": "Discord_Grupo_ONE_G10",
  "periodo_referencia": "Semana_04",
  "interacciones": [
    { "autor": "Mariana Souza", "canal": "#logros-y-empleos", "tipo": "testimonio", "texto": "..." },
    { "autor": "Lucas Albuquerque", "canal": "#dudas-langgraph", "tipo": "pregunta_tecnica", "texto": "..." }
  ]
}
```

> **Clave:** el campo `tipo` es la señal que decide qué activo generar. No se pierde ni se re-infere.

### Salida

```json
{
  "status": "exito",
  "resumen_comunidad": { "total_interacciones_procesadas": 2, "sentimiento_predominante": "...", "temas_principales": ["..."] },
  "activos_distribucion_generados": {
    "post_linkedin": { "titulo": "...", "copy": "...", "canal_recomendado": "...", "potencial_engagement": "..." },
    "destaque_newsletter_semanal": { "seccion": "...", "titular": "...", "resumen": "..." },
    "sugerencia_contenido_faq": { "tema": "...", "origen": "...", "status": "..." }
  },
  "almacenamiento_oci": { "bucket": "communitylab-activos-marketing", "ruta_objeto": "...", "status": "guardado_con_exito" }
}
```

---

## 🏗️ Arquitectura

```mermaid
flowchart TB
    IN["InputBatch (contrato)"] --> ING["1. Ingesta (loader + normalizer)"]
    ING --> ANL["2. Análisis unificado (Gemini, 1 llamada)"]
    ANL --> DEC["3. Decisiones (ruteo por tipo)"]
    DEC --> GEN["4. Generadores (LinkedIn, newsletter, FAQ)"]
    GEN --> OCI["5. OCI Object Storage"]
    OCI --> OUT["OutputBatch (contrato)"]
```

**Decisiones de diseño clave** (acordadas con la matriz de pruebas):
- El **contrato es la fuente de verdad** del vocabulario. Las categorías canónicas son `testimonio`, `pregunta_tecnica`, `feedback`, `logro`, `discusion`, `otro`.
- `duda_tecnica` es alias de `pregunta_tecnica`; `comentario_general` y `pregunta_general` mapean a `otro`.
- Ante fallo del LLM, el analizador devuelve un default seguro (neutral + `otro` + relevancia 0) y **nunca crashea**.

---

## 📁 Estructura del proyecto

```
communitylab/
├── src/
│   ├── domain/             # Modelos (contrato) + interfaces
│   ├── ingest/             # Loader + normalizer + Mastodon
│   ├── utils/              # Cliente LLM (gemini/ollama/openai/rule_based)
│   ├── analysis/           # Análisis unificado (GeminiUnifiedAnalyzer)
│   ├── decisions/          # Motor de decisiones (reglas + LLM)
│   ├── generators/         # LinkedIn, newsletter, FAQ
│   ├── oci/                # Object Storage (cliente + fallback local)
│   ├── interface/          # Streamlit (panel de curaduría)
│   └── pipeline.py         # Orquestador end-to-end
├── scripts/run_demo.py     # Runner de demo (online / --offline)
├── tests/                  # 159 tests
├── data/                   # Datos (raw/processed/sample)
├── docs/                   # Documentación
└── README.md
```

---

## 🚀 Cómo ejecutar

### 1. Instalación

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuración

Copiá `.env.example` a `.env` y completá:

```bash
COMMUNITYLAB_LLM_BACKEND=gemini   # gemini | openai | ollama | rule_based
GEMINI_API_KEY=...
```

> Sin credenciales, usá `COMMUNITYLAB_LLM_BACKEND=rule_based` (determinista, ideal para demos y CI).

### 3. Pipeline end-to-end

```bash
python3 -m src.pipeline data/sample/demo_fixed.json
```

### 4. Demo del proyecto

```bash
python3 scripts/run_demo.py --offline    # sin key ni red, determinista (plan B)
python3 scripts/run_demo.py              # online: Ollama Cloud + gemma4:31b
streamlit run src/interface/app.py       # panel de curaduría (editar + aprobar + descargar)
```

> Detalle, salida esperada y troubleshooting en [docs/demo.md](docs/demo.md).

### 5. Tests

```bash
python3 -m pytest tests/ -q
```

---

## 📚 Documentación

- [Arquitectura](docs/arquitectura.md)
- [Deploy y OCI](docs/deploy.md)
- [Análisis de datasets](docs/analisis_datasets.md)
- [Fichas de historias de usuario](docs/fichas-historias-usuario.md)
- [UI design](docs/ui-design.md)
- [Checklist de review](docs/review-checklist.md)
- [Guía de contribución](CONTRIBUTING.md)

---

## ✅ Checklist MVP (del PDF)

- [x] Ingestión funcional de interacciones (loader + normalizer)
- [x] Análisis unificado de sentimiento/categoría/relevancia (1 llamada LLM)
- [x] Generación de 2+ formatos de activos (LinkedIn, newsletter, FAQ)
- [x] Cliente LLM común (Gemini/Ollama local+nube/rule_based)
- [x] Integración OCI Object Storage (con fallback local)
- [x] Interfaz Streamlit (curaduría/edición/descarga)
- [x] Demo de 3+ ejemplos (ver [docs/demo.md](docs/demo.md))
- [x] Repositorio con documentación y diagrama

---

## 👥 Equipo

| Rol | Integrante | Módulos |
|---|---|---|
| Tech Lead / Backend | `emanuelperacchia` | Git, OCI, conexión Gemini, deploy |
| Revisora de código | `Rox-0864` | Contrato, análisis unificado, pipeline, gate de merge |
| Backend | `Elias-J-Guardado` | Ingesta (Mastodon) |
| Data Science | `Yis-ai-eng` | Decisiones + dudas recurrentes |
| Data Analyst | `mrolon09` | Interfaz Streamlit |
| Project Manager / QA | `itanflores` | Matriz de pruebas, QA, planificación |
| Documentación / Demo | `Antonio3051` | Docs finales, video demo |

---

## 🏆 Roadmap

- [x] Motor de decisiones (ruteo por `tipo`)
- [x] Generadores (LinkedIn/newsletter/FAQ) — PR #86 mergeado
- [x] Integrar OCI Object Storage (fallback local incluido)
- [x] Conectar la interfaz Streamlit (edición + descarga)
- [x] Demo final con 3+ ejemplos (runner + runbook)
- [x] Mergear #86 (generadores) y #89 (robustez del analizador)
- [ ] Aprobar y mergear el PR #90 (cableado del pipeline)
- [ ] Subir el snapshot a OCI con credenciales reales desde el panel

---

*Proyecto del Hackathon ONE G10 — Oracle Next Education & Alura*
