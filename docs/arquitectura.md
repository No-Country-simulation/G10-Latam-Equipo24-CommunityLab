# 🏗️ ARQUITECTURA — CommunityLab

> Diagramas en Mermaid, listos para incrustar en el README.md del repositorio.
> Usar con GitHub (soporta Mermaid nativo) o renderizar en mermaid.live.

---

## 📐 DIAGRAMA 1: VISTA GENERAL DEL PIPELINE (para el README principal)

```mermaid
flowchart TB
    subgraph FUENTES["📡 Fuentes de Datos"]
        DISCORD["Discord"]
        SLACK["Slack / Foros"]
        JSON["JSON / CSV"]
        WEBHOOK["Webhook"]
    end

    subgraph INGEST["1️⃣ Ingestión"]
        LOADER["Loader\n(JSON/CSV/API)"]
        NORMALIZER["Normalizador\n(formato estándar)"]
        VALIDATOR["Validador\n(Pydantic)"]
        LOADER --> NORMALIZER --> VALIDATOR
    end

    subgraph ANALYSIS["2️⃣ Análisis IA"]
        SENTIMENT["Análisis de\nSentimiento (LLM)"]
        TOPICS["Categorización\nde Temas (LLM)"]
        RELEVANCE["Puntuación de\nRelevancia (LLM)"]
        SENTIMENT & TOPICS & RELEVANCE --> ANALYZER["Analizador\nConsolidado"]
    end

    subgraph DECISIONS["4️⃣ Motor de Decisiones"]
        ENGINE["Decision Engine"]
        RISK["Detector de\nMiembros en Riesgo"]
        RECURRING["Detector de Dudas\nRecurrentes"]
        ESCALATE["Reglas de\nEscalamiento"]
        ENGINE --> RISK
        ENGINE --> RECURRING
        RECURRING --> ESCALATE
    end

    subgraph ROUTING["3️⃣ Ruteo Condicional"]
        ROUTER["Content Router"]
        ROUTER -->|"sentimiento positivo\n+ relevancia alta"| CASO["Caso de Éxito"]
        ROUTER -->|"duda técnica"| FAQ["FAQ / Tip"]
        ROUTER -->|"historia inspiradora"| NEWS["Newsletter\nHighlight"]
        ROUTER -->|"negativo / riesgo"| ALERT["Alerta\nMember Risk"]
    end

    subgraph GENERATORS["5️⃣ Generadores de Activos"]
        LINKEDIN["Generador\nLinkedIn"]
        NEWSLETTER["Generador\nNewsletter"]
        FAQGEN["Generador\nFAQ"]
        TESTIMONIAL["Generador\nTestimonios"]
        LINKEDIN & NEWSLETTER & FAQGEN & TESTIMONIAL --> PACKAGE["Empaquetador\nde Activos"]
    end

    subgraph STORAGE["6️⃣ OCI Object Storage (Always Free)"]
        BUCKET["communitylab-activos-marketing"]
        PATH1["activos/2026-semana-04/\npaquete-distribucion.json"]
        PATH2["decisiones/\nalertas-semana-04.json"]
        BUCKET --> PATH1
        BUCKET --> PATH2
    end

    subgraph INTERFACE["7️⃣ Interfaz Streamlit"]
        DASH["📊 Dashboard\nMétricas y Sentimiento"]
        CURADURIA["✍️ Panel de Curaduría\n(aprobar / editar)"]
        ALERTS["🚨 Panel de Alertas\n(decisiones)"]
    end

    subgraph LLM["🧠 Proveedor LLM"]
        GEMINI["Google Gemini\n(principal)"]
        OPENAI["OpenAI GPT\n(respaldo)"]
    end

    FUENTES --> INGEST
    INGEST --> ANALYSIS
    ANALYSIS --> DECISIONS
    ANALYSIS --> ROUTING
    DECISIONS --> ROUTING
    ROUTING --> GENERATORS
    GENERATORS --> PACKAGE
    PACKAGE --> STORAGE
    DECISIONS --> STORAGE
    STORAGE --> INTERFACE
    ANALYSIS -->|"prompts"| LLM
    ROUTING -->|"prompts"| LLM
    GENERATORS -->|"prompts"| LLM
    DECISIONS -->|"prompts"| LLM
```

---

## 🧩 DIAGRAMA 2: COMPONENTES DETALLADOS (para docs/architecture.md)

```mermaid
flowchart LR
    subgraph FRONT["🎨 Frontend (Streamlit)"]
        UI_APP["app.py"]
        UI_DASH["pages/1_dashboard.py"]
        UI_CUR["pages/2_curaduria.py"]
        UI_GEN["pages/3_generar.py"]
        UI_CFG["pages/4_config.py"]
    end

    subgraph API["🔌 API Layer"]
        API_EP["src/api/endpoints.py"]
        API_HEALTH["src/api/health.py"]
    end

    subgraph CORE["⚙️ Core Pipeline"]
        PIPE["src/orchestration/pipeline.py"]
        ROUTER2["src/orchestration/router.py"]
        STATE["src/orchestration/state.py"]
    end

    subgraph ING["📥 Ingest"]
        LDR["src/ingest/loader.py"]
        NRM["src/ingest/normalizer.py"]
        VAL["src/ingest/validators.py"]
    end

    subgraph ANL["🧠 Analysis"]
        SENT["src/analysis/sentiment.py"]
        CAT["src/analysis/categorization.py"]
        REL["src/analysis/relevance.py"]
        ORCH["src/analysis/orchestrator.py"]
    end

    subgraph PRM["💬 Prompts"]
        P_SENT["sentiment_prompts.py"]
        P_LINK["linkedin_prompts.py"]
        P_NEWS["newsletter_prompts.py"]
        P_FAQ["faq_prompts.py"]
        P_TMP["templates.py"]
    end

    subgraph GEN["✍️ Generators"]
        G_LINK["linkedin_generator.py"]
        G_NEWS["newsletter_generator.py"]
        G_FAQ["faq_generator.py"]
        G_TEST["testimonial_generator.py"]
    end

    subgraph DEC["🧭 Decisions"]
        D_ENGINE["src/decisions/engine.py"]
        D_RISK["member_risk.py"]
        D_REC["recurring_topics.py"]
        D_ESC["escalation.py"]
        D_NOTIF["notifications.py"]
    end

    subgraph OCI["☁️ OCI (Always Free)"]
        O_CLIENT["src/oci/oci_client.py"]
        O_STORE["src/oci/storage.py"]
        O_PERSIST["src/oci/persistence.py"]
        O_BUCKET["📦 Bucket:\ncommunitylab-activos-marketing"]
    end

    subgraph LLMS["🌐 LLM Providers"]
        L_GEMINI["Gemini"]
        L_OPENAI["OpenAI (resp)"]
    end

    FRONT -->|"HTTP"| API
    API --> CORE
    CORE --> ING
    CORE --> ANL
    CORE --> GEN
    CORE --> DEC
    ANL --> PRM
    GEN --> PRM
    DEC --> PRM
    ANL -->|"análisis"| DEC
    DEC -->|"decisiones"| CORE
    GEN -->|"activos"| OCI
    DEC -->|"alertas"| OCI
    PIPE --> O_PERSIST
    O_CLIENT --> O_STORE --> O_BUCKET
    ANL -->|"prompts + respuestas"| LLMS
    GEN -->|"prompts + respuestas"| LLMS
    DEC -->|"prompts + respuestas"| LLMS
```

---

## 🔄 DIAGRAMA 3: FLUJO DE DATOS TÉCNICO (JSON in → JSON out)

```mermaid
sequenceDiagram
    participant U as Usuario<br/>(Community Manager)
    participant API as Webhook / API
    participant ING as Ingest<br/>(loader+normalize)
    participant ANL as Analysis<br/>(sentimiento+temas)
    participant LLM as LLM<br/>(Gemini)
    participant DEC as Decision Engine
    participant GEN as Generators
    participant OCI as OCI Object Storage
    participant UI as Streamlit

    U->>API: POST /procesar<br/>{interacciones}
    API->>ING: envia lote JSON
    ING->>ING: normaliza + valida
    
    loop Cada mensaje
        ING->>ANL: mensaje normalizado
        ANL->>LLM: prompt de sentimiento
        LLM-->>ANL: {sentimiento, score}
        ANL->>LLM: prompt de temas
        LLM-->>ANL: {temas, entidades}
        ANL->>LLM: prompt de relevancia
        LLM-->>ANL: {score, razon}
        ANL-->>DEC: análisis completo
    end

    DEC->>DEC: riesgo por autor<br/>dudas recurrentes
    DEC-->>GEN: decision: publicar/casificar/derivar
    GEN->>LLM: prompt de copywriting<br/>(LinkedIn/FAQ/Newsletter)
    LLM-->>GEN: activo formateado
    GEN-->>OCI: paquete de activos
    DEC-->>OCI: decisiones y alertas

    OCI-->>UI: datos para dashboard
    U->>UI: revisa, aprueba, publica ✅
    UI-->>OCI: estado de aprobación
```

---

## 🏛️ DIAGRAMA 4: DESPLIEGUE (SI usan OCI Compute — opcional/diferencial)

```mermaid
flowchart TB
    subgraph OCI_TENANCY["☁️ Oracle Cloud — Tenancy ONE Always Free"]
        subgraph COMPUTE["Compute Instance (VM.Standard.E2.1.Micro)"]
            DOCKER["🐳 Docker Container"]
            STREAMLIT["Streamlit App :8501"]
            PIPELINE["Pipeline Python"]
            N8N_OPT["N8N (opcional)"]
            DOCKER --> STREAMLIT
            DOCKER --> PIPELINE
            DOCKER --> N8N_OPT
        end

        subgraph STORAGE_OCI["Object Storage (Always Free)"]
            BUCK["Bucket: communitylab-activos-marketing"]
        end

        subgraph AUTH["IAM / Auth"]
            API_KEY["API Keys\nOCI_USER_ID\nOCI_FINGERPRINT"]
        end

        COMPUTE -->|"SDK OCI - PUT Object"| STORAGE_OCI
        AUTH --> COMPUTE
    end

    subgraph INTERNET["Internet"]
        CM["👨‍💼 Community Manager"]
        MKT["📣 Equipo Marketing"]
    end

    INTERNET -->|"🔗 HTTPS :8501"| STREAMLIT
    INTERNET -->|"POST /webhook"| PIPELINE

    subgraph EXT["Externals"]
        LLM_API["LLM APIs<br/>(Gemini/OpenAI)"]
    end
    PIPELINE -->|"API Calls"| LLM_API
```

---

## 📊 DIAGRAMA 5: BUCKET OCI — Estructura de objetos

```mermaid
graph TD
    ROOT["communitylab-activos-marketing<br/>📦 Bucket Always Free"]
    ROOT --> S1["activos/"]
    ROOT --> S2["decisiones/"]
    ROOT --> S3["informes/"]
    ROOT --> S4["datasets/"]
    ROOT --> S5["estado/"]
    S1 --> S1A["activos/2026-semana-04/"]
    S1 --> S1B["activos/2026-semana-05/"]
    S1A --> S1A1["paquete-distribucion.json"]
    S1A --> S1A2["post-linkedin.json"]
    S1A --> S1A3["newsletter-highlight.json"]
    S1A --> S1A4["faq-tips.json"]
    S2 --> S2A["alertas-miembros/"]
    S2 --> S2B["derivaciones-mentoria/"]
    S2A --> S2A1["2026-semana-04.json"]
    S2B --> S2B1["2026-semana-04.json"]
    S3 --> S3A["sentimiento-mensual.csv"]
    S3 --> S3B["temas-tendencia.json"]
    S4 --> S4A["raw-discord-sample.json"]
    S4 --> S4B["raw-github-issues.json"]
    S5 --> S5A["aprobaciones.json"]
    S5 --> S5B["historial-pipeline.log"]
```

---

## 📋 INSTRUCCIONES DE USO EN EL README

### Para GitHub (render nativo):
```markdown
```mermaid
flowchart TB
    A[Ingesta] --> B[Análisis]
    B --> C[Decisiones]
    C --> D[Generación]
    D --> E[OCI]
```
```

GitHub renderiza Mermaid automáticamente en Markdown desde 2025.

### Para la presentación ejecutiva:
Exportar desde:
- [mermaid.live](https://mermaid.live) → PNG/SVG de alta calidad
- O usar [Mermaid Ink](https://mermaid.ink) para generar URLs de imágenes

### Alternativa offline (sin Mermaid):
Generar el diagrama con **draw.io** (free) usando los mismos componentes. La versión Mermaid es el estándar recomendado.

---

## 🎯 Resumen de decisiones de arquitectura (para DECISIONS.md)

| Decisión | Opción elegida | Alternativa | Por qué |
|----------|----------------|-------------|---------|
| Orquestación | Python puro + async | n8n | Mayor control, testing fácil, integración directa con módulos |
| LLM principal | Google Gemini | OpenAI | Gratis y generoso en capa free, bueno en español/portugués |
| Interfaz | Streamlit | Gradio | Mejor para paneles de curaduría con estado |
| Persistencia | OCI Object Storage | Base de datos | Requisito obligatorio del hackathon + compatible con Always Free |
| Módulo de decisiones | Reglas + LLM híbrido | Solo LLM | Determinismo en reglas críticas + contexto en matices |
| Deploy | Local + OCI opcional | Solo OCI | MVP rápido + diferencial si hay tiempo |

---

*Arquitectura creada para equipo CommunityLab — Oracle ONE Hackathon G10*
*Los diagramas 1-5 están listos para pegar en los documentos del repo.*