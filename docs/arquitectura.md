# 🏗️ ARQUITECTURA — CommunityLab

> Diagramas en Mermaid, listos para incrustar en el README.md del repositorio.
> Usar con GitHub (soporta Mermaid nativo) o renderizar en mermaid.live.

---

## 📐 DIAGRAMA 1: VISTA GENERAL DEL PIPELINE (para el README principal)

```mermaid
flowchart TB
    subgraph FUENTES["📡 Fuentes de Datos"]
        TELEGRAM["Telegram\n(webhook / polling)"]
        MASTODON["Mastodon\n(API pública)"]
        CSV["CSV / JSON"]
    end

    subgraph INGEST["1️⃣ Ingestión"]
        LOADER["Loader\n(JSON/CSV)"]
        NORMALIZER["Normalizador\n(formato estándar)"]
        LOADER --> NORMALIZER
    end

    subgraph ANALYSIS["2️⃣ Análisis IA (una sola llamada por mensaje)"]
        ANALYZER["Analizador unificado\nsentimiento + categoría + relevancia"]
    end

    subgraph DECISIONS["3️⃣ Motor de Decisiones (reglas fijas, sin IA)"]
        ENGINE["RuleBasedDecisionEngine"]
        R1["R1: testimonio/logro\npositivo → publicar"]
        R4["R4: feedback negativo\nconfianza > 0.8 → derivar"]
        R2["R2: pregunta técnica\n→ crear FAQ"]
        R3["R3: lo demás → descartar"]
        ENGINE --> R1
        ENGINE --> R4
        ENGINE --> R2
        ENGINE --> R3
    end

    subgraph GENERATORS["4️⃣ Generadores de Activos"]
        LINKEDIN["Generador\nLinkedIn"]
        NEWSLETTER["Generador\nNewsletter"]
        FAQGEN["Generador\nFAQ (temas)"]
        LINKEDIN & NEWSLETTER & FAQGEN --> PACKAGE["Empaquetador\nde Activos"]
    end

    subgraph STORAGE["5️⃣ Persistencia (OCI con degradación local)"]
        OCI_BUCKET["communitylab-activos-marketing\n(OCI Object Storage)"]
        LOCAL_MIRROR["storage/\n(snapshot local)"]
    end

    subgraph INTERFACE["6️⃣ Interfaz Streamlit"]
        DASH["src/interface/app.py\nPanel de curaduría"]
    end

    subgraph LLM["🧠 Proveedor LLM (intercambiable)"]
        GEMMA["Gemini / OpenAI\n(nube)"]
        OLLAMA["Ollama\n(local o nube)"]
        RULE["rule_based\n(sin IA)"]
    end

    FUENTES --> INGEST
    INGEST --> ANALYSIS
    ANALYSIS --> DECISIONS
    DECISIONS --> GENERATORS
    GENERATORS --> PACKAGE
    PACKAGE --> STORAGE
    DECISIONS --> STORAGE
    STORAGE --> INTERFACE
    ANALYSIS -->|"prompt"| LLM
    GENERATORS -->|"prompt"| LLM
```

---

## 🧩 DIAGRAMA 2: COMPONENTES DETALLADOS (para docs/architecture.md)

```mermaid
flowchart LR
    subgraph FRONT["🎨 Frontend (Streamlit)"]
        UI_APP["src/interface/app.py"]
        UI_STATE["src/interface/state.py"]
        UI_PUB["src/interface/telegram_publish.py"]
    end

    subgraph CORE["⚙️ Pipeline"]
        PIPE["src/pipeline.py"]
    end

    subgraph ING["📥 Ingest"]
        LDR["src/ingest/loader.py"]
        CSV["src/ingest/csv_loader.py"]
        JSON["src/ingest/input_loader.py"]
        NRM["src/ingest/normalizer.py"]
        BOT["src/ingest/bot.py"]
        WEB["src/ingest/webhook.py"]
        RUNTIME["src/ingest/runtime.py"]
    end

    subgraph ANL["🧠 Analysis"]
        UNI["src/analysis/unified_analyzer.py"]
    end

    subgraph PRM["💬 Prompts"]
        P_TMP["src/prompts/templates.py"]
        P_GEN["src/prompts/generators.py"]
    end

    subgraph GEN["✍️ Generators"]
        G_LINK["src/generators/linkedin.py"]
        G_NEWS["src/generators/newsletter.py"]
        G_FAQ["src/generators/faq.py"]
    end

    subgraph DEC["🧭 Decisions"]
        D_ENGINE["src/decisions/engine.py"]
    end

    subgraph OCI["☁️ OCI"]
        O_CLIENT["src/oci/client.py"]
        O_STORE["src/oci/storage.py"]
    end

    subgraph LLMS["🌐 LLM Providers"]
        L_FACTORY["src/utils/llm.py\n(gemini | openai | ollama | rule_based)"]
    end

    FRONT --> PIPE
    PIPE --> ING
    PIPE --> ANL
    PIPE --> GEN
    PIPE --> DEC
    ANL --> PRM
    GEN --> PRM
    ANL -->|"análisis"| DEC
    DEC -->|"decisiones"| GEN
    GEN -->|"activos"| OCI
    DEC -->|"derivados"| OCI
    ANL -->|"prompt + respuesta"| LLMS
    GEN -->|"prompt + respuesta"| LLMS
    RUNTIME -->|"elige backend"| LLMS
```

---

## 🔄 DIAGRAMA 3: FLUJO DE DATOS TÉCNICO (JSON in → JSON out)

```mermaid
sequenceDiagram
    participant U as Usuario<br/>(Community Manager)
    participant ING as Ingest<br/>(loader + normalize)
    participant ANL as Analysis<br/>(unificado)
    participant LLM as LLM<br/>(intercambiable)
    participant DEC as Decision Engine
    participant GEN as Generators
    participant OCI as OCI / snapshot local
    participant UI as Streamlit

    U->>ING: sube lote CSV/JSON<br/>o llega por Telegram
    ING->>ING: normaliza + valida

    loop Cada mensaje
        ING->>ANL: mensaje normalizado
        ANL->>LLM: prompt unificado<br/>(sentimiento + categoría + relevancia)
        LLM-->>ANL: JSON con los tres campos
        ANL-->>DEC: análisis completo
    end

    DEC->>DEC: reglas R1 → R4 → R2 → R3
    DEC-->>GEN: decisión: publicar / crear FAQ
    GEN->>LLM: prompt de copywriting<br/>(LinkedIn / Newsletter / FAQ)
    LLM-->>GEN: activo formateado
    GEN-->>OCI: paquete de activos
    DEC-->>OCI: mensajes derivados (revisión humana)

    OCI-->>UI: datos para el panel
    U->>UI: revisa, aprueba, publica ✅
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
        LLM_API["LLM APIs<br/>(Ollama/Gemini)"]
    end
    PIPELINE -->|"API Calls"| LLM_API
```

---

## 📊 DIAGRAMA 5: BUCKET OCI — Estructura de objetos

```mermaid
graph TD
    ROOT["communitylab-activos-marketing<br/>📦 Bucket Always Free"]
    ROOT --> S1["activos/"]
    ROOT --> S2["estado/"]
    S1 --> S1A["activos/2026-semana-04/"]
    S1 --> S1B["activos/2026-semana-05/"]
    S1A --> S1A1["paquete-distribucion.json"]
    S2 --> S2A["estado/derivados-atendidos.json"]
    S2 --> S2B["estado/curacion-2026-semana-04.json"]
```

> Nota: sin credenciales OCI, el pipeline degrada a un snapshot local bajo
> `storage/activos/` y `storage/estado/` (mismas claves, espejo local).

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

## 🎯 Decisiones de arquitectura

Las decisiones (orquestación, LLM, interfaz, persistencia, módulo de decisiones, deploy) y su justificación viven en **[`DECISIONS.md`](DECISIONS.md)** — única fuente de verdad. Acá no se duplican.

---

*Arquitectura creada para equipo CommunityLab — Oracle ONE Hackathon G10*
*Los diagramas 1-5 están listos para pegar en los documentos del repo.*