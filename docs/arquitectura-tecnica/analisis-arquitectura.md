# 🏛️ Arquitectura de Análisis y Componentes — CommunityLab

> **Ubicación:** `docs/arquitectura-tecnica/analisis-arquitectura.md`  
> *Documento complementario que detalla la arquitectura en capas y el flujo de procesamiento de datos, diseñado para no superponerse con `docs/llm-pipeline.md`.*

---

## 1. Visión General de la Arquitectura (Screaming Architecture)

El proyecto CommunityLab adopta una arquitectura modular basada en separación de incumbencias y dominio limpio, donde cada paquete dentro de `src/` representa claramente una capacidad de negocio:

```
src/
├── domain/       # Modelos Pydantic (Contratos de entrada/salida y Enums)
├── ingest/       # Carga, validación y normalización de interacciones crudas
├── analysis/     # Analizador unificado (sentimiento, categoría, relevancia)
├── decisions/    # Motor de decisiones determinista
├── generators/   # Generadores de contenido (LinkedIn, FAQ, Newsletter)
├── oci/          # Cliente y almacenamiento Object Storage (OCI)
├── interface/    # Aplicación web interactiva (Streamlit)
└── utils/        # Clientes LLM agnósticos (Gemini, OpenAI, Ollama, RuleBased)
```

---

## 2. Flujo de Datos por Capas

### Capa 1: Dominio y Contratos (`src/domain/`)
- Define el contrato estricto de entrada (`InputBatch`, `InputMessage`) y de salida (`OutputBatch`, `CommunitySummary`, `DistributionAssets`, `OCIStorage`).
- Establece el vocabulario canónico mediante enumeraciones (`InteractionType`, `SentimentType`, `ActionType`, `AssetType`).

### Capa 2: Ingesta y Normalización (`src/ingest/`)
- Se encarga de leer los archivos JSON o CSV de origen (mastodon, dataset de demo
  o mensajes de Telegram).
- Utiliza el `InputNormalizer` para asegurar que los campos opcionales o variantes idiomáticas (inglés/español) se mapen correctamente a los campos obligatorios del contrato.

### Capa 3: Análisis de IA (`src/analysis/`)
- Centralizado en `GeminiUnifiedAnalyzer`.
- Realiza una **única llamada estructurada por mensaje** utilizando los prompts centralizados (`src/prompts/templates.py`).
- Extrae de forma atómica:
  1. Sentimiento (`positivo`, `negativo`, `neutral` + score de confianza + reasoning).
  2. Categorización (mapeando contra `InteractionType` y manejando fallbacks a `otro`).
  3. Relevancia de marketing (`score` + `is_marketing_worthy`).

### Capa 4: Decisiones y Ruteo (`src/decisions/`)
- El motor determinista (`RuleBasedDecisionEngine`) evalúa los resultados del análisis sin consumir cuotas de LLM.
- Aplica las reglas del negocio en este orden:
  - **Regla 1 (R1):** Testimonio o logro positivo y relevante ($\ge 0.6$) $\rightarrow$ Publicar en LinkedIn.
  - **Regla 4 (R4):** Feedback negativo con confianza mayor a 0.8 $\rightarrow$ Derivar a un humano (community manager) para atención personalizada.
  - **Regla 2 (R2):** Duda técnica o pregunta frecuente $\rightarrow$ Crear FAQ.
  - **Regla 3 (R3):** Los casos restantes $\rightarrow$ Descartar.
- Las preguntas que terminan en "crear FAQ" se agrupan después por tema con
  `cluster_faq_targets` (en `src/generators/faq.py`), que consolida las
  preguntas similares en temas con respuesta generada.

### Capa 5: Generadores de Contenido (`src/generators/`)
- Con base en las decisiones del motor, clases especializadas como `LinkedInGenerator`, `NewsletterGenerator` y `FAQThemeGenerator` solicitan al LLM la redacción final de los copys optimizados.

### Capa 6: Persistencia Cloud (`src/oci/`)
- A través de `OCIStorage`, el pipeline empaqueta la salida completa del sistema y la persiste de forma remota en OCI Object Storage bajo la ruta estructurada:
  `activos/YYYY-semana-WW/paquete-distribucion.json` (Requisito R5).
