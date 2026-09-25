# 📋 FICHAS DE HISTORIAS DE USUARIO — CommunityLab v2

> **Instrucciones:** Cada ficha = 1 Issue en GitHub Project.
> Copiar contenido de cada ficha en el body de la issue.
> Distribuidas entre 6 personas × 5 sprints. Todas las personas tienen tarea en cada sprint.

---

## 👥 EQUIPO (6 personas)

| Persona | Rol principal | Tareas totales | Tipo de trabajo |
|---------|---------------|----------------|-----------------|
| **@emanuelperacchia** | Admin, Infra, Despliegue, Docs | 7 | ⬜ Sin Python complejo (gestión, config, cloud) |
| **@Rox-0864** | Senior, Análisis IA, Review | 10 | 🟥 Todo código Python complejo |
| **@Elias** | Ingesta, Integración | 6 | 🟨 Bajo Python (ingesta + apoyo) |
| **@Yis-ai-eng** | Generadores, Prompts, QA | 6 | 🟧 Medio Python (generadores + apoyo) |
| **@Marcelo Rolon** | Frontend/UI, Streamlit | 7 | 🟨 UI/Streamlit + apoyo |
| **@Antonio3051** | Documentación, Videos, Demo | 6 | ⬜ Sin Python (docs, videos) |

---

## 📥 JSON DE ENTRADA (requisito obligatorio)

El sistema debe aceptar este formato via API/Webhook/Archivo:

```json
{
  "batch_id": "batch-001",
  "source": "discord",
  "channel": "#general",
  "processed_at": "2026-09-21T10:00:00Z",
  "interactions": [
    {
      "id": "msg-001",
      "content": "Me encantó el curso de Python, me contrataron!",
      "author": "estudiante-01",
      "channel": "#testimonios",
      "timestamp": "2026-09-15T14:30:00Z",
      "metadata": {
        "reactions": 5,
        "attachments": 0
      }
    }
  ]
}
```

---

## 📤 JSON DE SALIDA (requisito obligatorio)

El sistema debe generar este formato:

```json
{
  "batch_id": "batch-001",
  "processed_at": "2026-09-21T10:05:00Z",
  "summary": {
    "total_messages": 1,
    "sentiment_distribution": { "positivo": 1, "negativo": 0, "neutral": 0 },
    "assets_generated": 1,
    "alerts": 0
  },
  "analysis": [
    {
      "message_id": "msg-001",
      "sentiment": { "type": "positivo", "score": 0.95, "reasoning": "Testimonio positivo" },
      "categorization": { "category": "testimonio", "topics": ["python", "empleo"], "entities": ["Python"] },
      "relevance": { "score": 0.9, "is_marketing_worthy": true }
    }
  ],
  "decisions": [
    { "message_id": "msg-001", "action": "publicar", "asset_type": "linkedin", "reason": "Testimonio positivo relevante" }
  ],
  "assets": [
    { "id": "linkedin-msg-001", "asset_type": "linkedin", "content": "Post generado...", "approved": false }
  ],
  "oci_storage": { "bucket": "communitylab-activos-marketing", "path": "activos/2026-semana-04/paquete-distribucion.json", "status": "uploaded" },
  "alerts": [],
  "visualization": { "streamlit_dashboard": "http://localhost:8501", "charts_available": ["sentiment", "topics", "engagement"] }
}
```

---

## 🗓️ SPRINT 1: FUNDAMENTOS (21/9 - 27/9)

---

### FICHA HU-S1-001
**Título:** Definir modelos de datos del sistema
**Como:** desarrollador del equipo
**Quiero:** tener modelos Python con Pydantic
**Para que:** todos los módulos trabajen con el mismo formato

**Sprint:** 1 | **Epic:** Dominio | **Priority:** 🔴 Alta | **Story Points:** 3
**Due:** @Rox-0864
**Labels:** feat, epic:domain, priority:alta

**Criterios de aceptación:**
- [ ] Modelo InputMessage con campos: id, content, author, channel, source, timestamp, metadata
- [ ] Modelo SentimentResult con campos: message_id, sentiment, score, reasoning
- [ ] Modelo CategorizationResult con campos: message_id, category, topics, entities
- [ ] Modelo AnalysisComplete que combine los 3 anteriores
- [ ] Modelo OutputBatch que sea el JSON de salida completo
- [ ] Todos los modelos serializables a JSON
- [ ] Tests unitarios de validación de modelos
- [ ] Documentación de cada modelo con docstring

**Tareas técnicas:**
- [ ] Crear src/domain/models.py
- [ ] Definir enums: SentimentType, AssetType, RiskLevel, ActionType
- [ ] Crear InputMessage (JSON entrada)
- [ ] Crear OutputBatch (JSON salida)
- [ ] Crear tests en tests/test_models.py

**Descripción técnica:**
- **Qué hacer:** Crear las clases Python que representan los datos del sistema
- **Qué funciona:** Base de todo el sistema. Sin modelos, ningún módulo funciona
- **Dónde:** `src/domain/models.py`

---

### FICHA HU-S1-002
**Título:** Definir interfaces y contratos del sistema
**Como:** desarrollador del equipo
**Quiero:** tener interfaces abstractas para cada módulo
**Para que:** sepamos exactamente qué debe hacer cada componente

**Sprint:** 1 | **Epic:** Dominio | **Priority:** 🔴 Alta | **Story Points:** 2
**Due:** @Rox-0864
**Labels:** feat, epic:domain, priority:alta

**Criterios de aceptación:**
- [ ] Interfaz DataLoader con método `load(source) -> list[InputMessage]`
- [ ] Interfaz SentimentAnalyzer con método `analyze(message) -> SentimentResult`
- [ ] Interfaz Categorizer con método `categorize(message) -> CategorizationResult`
- [ ] Interfaz RelevanceScorer con método `score(message) -> RelevanceResult`
- [ ] Interfaz DecisionEngine con método `decide(analysis) -> Decision`
- [ ] Interfaz AssetGenerator con método `generate(message, analysis) -> Asset`
- [ ] Interfaz StorageClient con métodos `upload` y `download`
- [ ] Cada interfaz documentada con docstring

**Tareas técnicas:**
- [ ] Crear src/domain/interfaces.py
- [ ] Definir todas las interfaces con ABC
- [ ] Documentar cada contrato

**Descripción técnica:**
- **Qué hacer:** Definir contratos abstractos que cada módulo debe cumplir
- **Qué funciona:** Garantiza que todos los módulos se comuniquen de la misma manera
- **Dónde:** `src/domain/interfaces.py`

---

### FICHA HU-S1-003
**Título:** Crear loader para JSON de entrada
**Como:** desarrollador del equipo
**Quiero:** poder cargar mensajes desde el JSON de entrada propuesto
**Para qué:** el sistema procese datos reales de comunidades

**Sprint:** 1 | **Epic:** Ingesta | **Priority:** 🔴 Alta | **Story Points:** 5
**Due:** @Elias
**Labels:** feat, epic:ingest, priority:alta

**Criterios de aceptación:**
- [ ] Clase JSONInputLoader que lea el formato JSON de entrada
- [ ] Validar estructura: batch_id, source, channel, interactions[]
- [ ] Retornar lista de InputMessage
- [ ] Manejo de errores: archivo no encontrado, JSON inválido, campos faltantes
- [ ] Tests con JSON válido e inválido
- [ ] Soporte para batch de hasta 1000 mensajes

**Tareas técnicas:**
- [ ] Crear src/ingest/input_loader.py
- [ ] Implementar JSONInputLoader
- [ ] Crear tests en tests/test_input_loader.py
- [ ] Probar con sample JSON

**Descripción técnica:**
- **Qué hacer:** Crear el cargador de archivos JSON que lee el formato de entrada del sistema
- **Qué funciona:** Es la puerta de entrada de datos. Sin esto no hay nada que analizar
- **Dónde:** `src/ingest/input_loader.py`

---

### FICHA HU-S1-004
**Título:** Normalizar datos al formato interno
**Como:** desarrollador del equipo
**Quiero:** convertir el JSON de entrada a objetos Message del sistema
**Para qué:** diferentes fuentes (Discord, Slack, API) usen el mismo formato interno

**Sprint:** 1 | **Epic:** Ingesta | **Priority:** 🔴 Alta | **Story Points:** 4
**Due:** @Elias
**Labels:** feat, epic:ingest, priority:alta

**Criterios de aceptación:**
- [ ] Clase InputNormalizer que convierta JSON → InputMessage
- [ ] Mapeo de campos desde JSON de entrada por fuente
- [ ] Parseo de timestamps ISO 8601
- [ ] Manejo de metadatos (reactions, attachments)
- [ ] Tests para cada tipo de fuente

**Tareas técnicas:**
- [ ] Crear src/ingest/normalizer.py
- [ ] Implementar InputNormalizer
- [ ] Definir field_mapping por fuente
- [ ] Tests en tests/test_normalizer.py

**Descripción técnica:**
- **Qué hacer:** Crear el normalizador que convierte JSON crudo a objetos Message
- **Qué funciona:** Permite que datos de Discord/Slack/API se conviertan al formato interno
- **Dónde:** `src/ingest/normalizer.py`

---

### FICHA HU-S1-005
**Título:** Configurar CI/CD básico
**Como:** administrador del repo
**Quiero:** que los tests se ejecuten automáticamente en cada push
**Para qué:** detectemos errores antes de que afecten al equipo

**Sprint:** 1 | **Epic:** Infraestructura | **Priority:** 🔴 Alta | **Story Points:** 3
**Due:** @emanuelperacchia
**Labels:** chore, epic:infra, priority:alta

**Criterios de aceptación:**
- [ ] `.github/workflows/ci.yml` funcionando
- [ ] Ejecuta `pytest tests/ -v`
- [ ] Ejecuta `flake8 src/`
- [ ] Se ejecuta en cada push a main
- [ ] Se ejecuta en cada PR a main
- [ ] Status check visible en PR

**Tareas técnicas:**
- [ ] Crear `.github/workflows/ci.yml`
- [ ] Configurar Python 3.11
- [ ] Instalar dependencias
- [ ] Ejecutar tests
- [ ] Configurar linting

**Descripción técnica:**
- **Qué hacer:** Configurar GitHub Actions para que tests y linting corran automáticamente
- **Qué funciona:** Detecta errores antes de que entren al código principal
- **Dónde:** `.github/workflows/ci.yml`

---

### FICHA HU-S1-006
**Título:** Configurar environment y dependencias base
**Como:** administrador del repo
**Quiero:** tener el archivo de dependencias y configuración del entorno
**Para qué:** cualquier miembro del equipo pueda levantar el proyecto localmente

**Sprint:** 1 | **Epic:** Infraestructura | **Priority:** 🔴 Alta | **Story Points:** 2
**Due:** @Yis-ai-eng
**Labels:** chore, epic:infra, priority:alta

**Criterios de aceptación:**
- [ ] `requirements.txt` con todas las dependencias
- [ ] `.env.example` con todas las variables de entorno necesarias
- [ ] `.gitignore` configurado (no commitear .env, data, etc.)
- [ ] Instrucciones de setup en README

**Tareas técnicas:**
- [ ] Crear `requirements.txt`
- [ ] Crear `.env.example`
- [ ] Crear `.gitignore`
- [ ] Actualizar `README.md` con instrucciones de setup

**Descripción técnica:**
- **Qué hacer:** Crear requirements.txt, .env.example, .gitignore
- **Qué funciona:** Permite que cualquier miembro instale y configure el proyecto en minutos
- **Dónde:** Raíz del proyecto (requirements.txt, .env.example, .gitignore)

---

### FICHA HU-S1-007
**Título:** Estructura base del proyecto y scaffold
**Como:** administrador del repo + Marcelo (UI)
**Quiero:** tener la estructura de carpetas creada con archivos iniciales
**Para qué:** el equipo pueda empezar a programar inmediatamente

**Sprint:** 1 | **Epic:** Infraestructura | **Priority:** 🔴 Alta | **Story Points:** 2
**Due:** @Marcelo Rolon
**Labels:** chore, epic:infra, priority:alta

**Criterios de aceptación:**
- [ ] Todas las carpetas de `src/` creadas con `__init__.py`
- [ ] Carpeta `tests/` con archivos base
- [ ] Carpeta `data/raw/` y `data/processed/`
- [ ] Carpeta `docs/` con documentación
- [ ] `.github/ISSUE_TEMPLATE/` creado
- [ ] `.github/CODEOWNERS` configurado con `@Rox-0864` y `@emanuelperacchia`; GitHub no permite auto-aprobación
- [ ] Mockup básico de UI en Figma/boceto (preparación para Sprint 4)

**Tareas técnicas:**
- [ ] Crear todas las carpetas
- [ ] Crear __init__.py en cada módulo
- [ ] Crear test base en tests/
- [ ] Diseñar boceto UI básico del dashboard

**Descripción técnica:**
- **Qué hacer:** Crear la estructura de carpetas con __init__.py y preparar boceto UI
- **Qué funciona:** Define dónde vive cada parte del código. Es el esqueleto del proyecto
- **Dónde:** `src/`, `tests/`, `data/`, `docs/`, `.github/`

---

### FICHA HU-S1-008
**Título:** Documentación técnica inicial del proyecto
**Como:** @Antonio3051
**Quiero:** tener documentación técnica inicial
**Para qué:** el jurado y el equipo entiendan la arquitectura

**Sprint:** 1 | **Epic:** Infraestructura | **Priority:** 🟡 Media | **Story Points:** 3
**Due:** @Antonio3051
**Labels:** docs, epic:infra

**Criterios de aceptación:**
- [ ] `docs/arquitectura.md` con diagramas Mermaid
- [ ] `docs/analisis_datasets.md` con fuentes de datos
- [ ] `README.md` con información del proyecto
- [ ] Diagrama de flujo de datos (JSON in → JSON out)
- [ ] Diagrama de arquitectura general

**Tareas técnicas:**
- [ ] Copiar arquitectura.md a docs/
- [ ] Copiar analisis_datasets.md a docs/
- [ ] Actualizar README.md

**Descripción técnica:**
- **Qué hacer:** Crear la documentación técnica con diagramas y descripciones
- **Qué funciona:** Explica la arquitectura al equipo y al jurado
- **Dónde:** `docs/arquitectura.md`, `docs/analisis_datasets.md`

---

## 🗓️ SPRINT 2: CORE PIPELINE (28/9 - 4/10)

---

### FICHA HU-S2-001
**Título:** Implementar análisis de sentimiento con Gemini
**Como:** desarrollador del equipo
**Quiero:** analizar el sentimiento de cada mensaje automáticamente
**Para qué:** identificar testimonios positivos, dudas y riesgos

**Sprint:** 2 | **Epic:** Análisis | **Priority:** 🔴 Alta | **Story Points:** 8
**Due:** @Rox-0864
**Labels:** feat, epic:analysis, priority:alta

**Criterios de aceptación:**
- [ ] Clase `GeminiSentimentAnalyzer` implementada
- [ ] Usa Google Gemini API (model gemini-pro)
- [ ] Retorna: tipo (positivo/negativo/neutral), score (0-1), reasoning
- [ ] Manejo de errores de API
- [ ] Resultado por defecto en caso de error
- [ ] Tests con mock de Gemini
- [ ] Configurado en `.env` la API key

**Tareas técnicas:**
- [ ] Crear `src/analysis/sentiment.py`
- [ ] Configurar cliente Gemini
- [ ] Crear prompt de análisis
- [ ] Parsear respuesta JSON
- [ ] Tests en `tests/test_sentiment.py`

**Descripción técnica:**
- **Qué hacer:** Implementar el análisis de sentimiento usando Google Gemini API
- **Qué funciona:** Detecta si un mensaje es positivo, negativo o neutro
- **Dónde:** `src/analysis/sentiment.py`

---

### FICHA HU-S2-002
**Título:** Implementar categorización de mensajes
**Como:** desarrollador del equipo
**Quiero:** clasificar cada mensaje en categorías automáticamente
**Para qué:** saber si es duda técnica, testimonio, feedback, etc.

**Sprint:** 2 | **Epic:** Análisis | **Priority:** 🔴 Alta | **Story Points:** 5
**Due:** @Rox-0864
**Labels:** feat, epic:analysis, priority:alta

**Criterios de aceptación:**
- [ ] Clase `GeminiCategorizer` implementada
- [ ] Categorías: duda_tecnica, testimonio, feedback, pregunta_general, discusion, otro
- [ ] Retorna: category, topics (array), entities (array)
- [ ] Tests para cada categoría

**Tareas técnicas:**
- [ ] Crear `src/analysis/categorization.py`
- [ ] Crear prompt de categorización
- [ ] Tests en `tests/test_categorization.py`

**Descripción técnica:**
- **Qué hacer:** Implementar la clasificación de mensajes en categorías usando Gemini
- **Qué funciona:** Clasifica cada mensaje en duda_tecnica, testimonio, feedback, etc.
- **Dónde:** `src/analysis/categorization.py`

---

### FICHA HU-S2-003
**Título:** Implementar evaluación de relevancia
**Como:** desarrollador del equipo
**Quiero:** evaluar qué tan relevante es un mensaje para marketing
**Para qué:** solo publiquemos contenido de alto impacto

**Sprint:** 2 | **Epic:** Análisis | **Priority:** 🔴 Alta | **Story Points:** 5
**Due:** @Rox-0864
**Labels:** feat, epic:analysis, priority:alta

**Criterios de aceptación:**
- [ ] Clase `GeminiRelevanceScorer` implementada
- [ ] Score de 0.0 a 1.0
- [ ] Booleano `is_marketing_worthy` (true si score >= 0.6)
- [ ] Tests con mensajes relevantes y no relevantes

**Tareas técnicas:**
- [ ] Crear `src/analysis/relevance.py`
- [ ] Crear prompt de relevancia
- [ ] Tests en `tests/test_relevance.py`

**Descripción técnica:**
- **Qué hacer:** Implementar la evaluación de relevancia para marketing usando Gemini
- **Qué funciona:** Puntúa qué mensaje vale la pena publicar
- **Dónde:** `src/analysis/relevance.py`

---

### FICHA HU-S2-004
**Título:** Crear orquestador de análisis
**Como:** desarrollador del equipo
**Quiero:** un solo punto de entrada que ejecute los 3 análisis
**Para qué:** el pipeline sea un solo paso

**Sprint:** 2 | **Epic:** Análisis | **Priority:** 🔴 Alta | **Story Points:** 5
**Due:** @Rox-0864
**Labels:** feat, epic:analysis, priority:alta

**Criterios de aceptación:**
- [ ] Clase `AnalysisOrchestrator` implementada
- [ ] Ejecuta: sentimiento → categorización → relevancia (en orden)
- [ ] Retorna `AnalysisComplete` con todos los resultados
- [ ] Método `analyze_batch(messages)` para procesar varios

**Tareas técnicas:**
- [ ] Crear `src/analysis/orchestrator.py`
- [ ] Integrar los 3 analizadores
- [ ] Tests en `tests/test_orchestrator.py`

**Descripción técnica:**
- **Qué hacer:** Crear el orquestador que ejecute los 3 análisis en orden
- **Qué funciona:** Coordina sentimiento + categorización + relevancia en un solo paso
- **Dónde:** `src/analysis/orchestrator.py`

---

### FICHA HU-S2-005
**Título:** Crear motor de decisiones
**Como:** desarrollador del equipo
**Quiero:** decidir automáticamente qué hacer con cada mensaje
**Para qué:** publicar testimonios, crear FAQs, alertar riesgos

**Sprint:** 2 | **Epic:** Decisiones | **Priority:** 🔴 Alta | **Story Points:** 8
**Due:** @Rox-0864
**Labels:** feat, epic:decisions, priority:alta

**Criterios de aceptación:**
- [ ] Clase `RuleBasedDecisionEngine` implementada
- [ ] Regla: testimonio positivo relevante → LinkedIn
- [ ] Regla: duda técnica frecuente → FAQ
- [ ] Regla: no relevante → descartar
- [ ] Retorna: action, asset_type, reason
- [ ] Tests para cada regla

**Tareas técnicas:**
- [ ] Crear `src/decisions/engine.py`
- [ ] Definir reglas de negocio
- [ ] Tests en `tests/test_decisions.py`

**Descripción técnica:**
- **Qué hacer:** Crear el motor de decisiones con reglas de negocio
- **Qué funciona:** Decide si un mensaje debe ser LinkedIn, FAQ, newsletter o descartarse
- **Dónde:** `src/decisions/engine.py`

---

### FICHA HU-S2-006
**Título:** Detector de miembros en riesgo
**Como:** community manager
**Quiero:** recibir alertas cuando un miembro tiene sentimiento negativo recurrente
**Para qué:** intervenir antes de que abandonen la comunidad

**Sprint:** 2 | **Epic:** Decisiones | **Priority:** 🟡 Media | **Story Points:** 5
**Due:** @Elias
**Labels:** feat, epic:decisions, priority:media

**Criterios de aceptación:**
- [ ] Clase `MemberRiskDetector` implementada
- [ ] Trackear historial de sentimiento por miembro
- [ ] Detectar tendencia negativa en mensajes recientes
- [ ] Alertas con nivel: bajo/medio/alto
- [ ] Razones de la alerta
- [ ] Tests

**Tareas técnicas:**
- [ ] Crear `src/decisions/member_risk.py`
- [ ] Implementar historial por miembro
- [ ] Tests en `tests/test_member_risk.py`

**Descripción técnica:**
- **Qué hacer:** Crear el detector de miembros en riesgo
- **Qué funciona:** Alerta cuando un usuario muestra sentimiento negativo recurrente
- **Dónde:** `src/decisions/member_risk.py`

---

### FICHA HU-S2-007
**Título:** Detector de dudas recurrentes
**Como:** community manager
**Quiero:** identificar preguntas que se repiten frecuentemente
**Para qué:** crear FAQs automáticos

**Sprint:** 2 | **Epic:** Decisiones | **Priority:** 🟡 Media | **Story Points:** 5
**Due:** @Yis-ai-eng
**Labels:** feat, epic:decisions, priority:media

**Criterios de aceptación:**
- [ ] Clase `RecurringTopicsDetector` implementada
- [ ] Contar frecuencia de temas
- [ ] Retornar temas con 2+ ocurrencias
- [ ] Incluir ejemplos de mensajes por tema
- [ ] Sugerir títulos de FAQ
- [ ] Tests

**Tareas técnicas:**
- [ ] Crear `src/decisions/recurring_topics.py`
- [ ] Implementar contador de temas
- [ ] Tests en `tests/test_recurring_topics.py`

**Descripción técnica:**
- **Qué hacer:** Crear el detector de dudas recurrentes
- **Qué funciona:** Identifica preguntas repetidas para generar FAQs automáticos
- **Dónde:** `src/decisions/recurring_topics.py`

---

### FICHA HU-S2-008
**Título:** Configurar conexión con Gemini y prompts centralizados
**Como:** administrador del repo
**Quiero:** tener la conexión con Gemini funcionando y prompts organizados
**Para qué:** todos los módulos de IA funcionen correctamente

**Sprint:** 2 | **Epic:** Infraestructura | **Priority:** 🔴 Alta | **Story Points:** 3
**Due:** @emanuelperacchia
**Labels:** feat, epic:infra, priority:alta

**Criterios de aceptación:**
- [ ] `.env` con `GEMINI_API_KEY`
- [ ] Prompts centralizados en `src/prompts/templates.py`
- [ ] Cada prompt documentado con instrucciones claras
- [ ] Manejo de rate limits de Gemini

**Tareas técnicas:**
- [ ] Configurar `GEMINI_API_KEY` en `.env`
- [ ] Crear `src/prompts/templates.py`
- [ ] Documentar cada prompt

**Descripción técnica:**
- **Qué hacer:** Configurar conexión con Gemini API y centralizar prompts
- **Qué funciona:** Todos los módulos de IA usan Gemini. Asegura conexión y prompts organizados
- **Dónde:** `.env` (GEMINI_API_KEY), `src/prompts/templates.py`

---

### 🔧 AUXILIAR S2: Marcelo - Diseñar mockup del dashboard
**Qué hacer:** Crear boceto/mockup del dashboard de Streamlit
**Por qué:** Preparación para Sprint 4 (UI)
**Dónde:** Figma, dibujo o boceto
**Due:** @Marcelo Rolon

### 🔧 AUXILIAR S2: Antonio - Documentar arquitectura de análisis
**Qué hacer:** Escribir documentación de cómo funciona el pipeline de análisis
**Por qué:** Preparación para documentación final
**Dónde:** `docs/analisis-arquitectura.md`
**Due:** @Antonio3051

---

## 🗓️ SPRINT 3: GENERADORES Y PIPELINE (5/10 - 11/10)

---

### FICHA HU-S3-001
**Título:** Generador de posts de LinkedIn
**Como:** community manager
**Quiero:** generar posts de LinkedIn automáticamente desde testimonios
**Para qué:** publicar contenido profesional sin esfuerzo manual

**Sprint:** 3 | **Epic:** Generadores | **Priority:** 🔴 Alta | **Story Points:** 8
**Due:** @Yis-ai-eng
**Labels:** feat, epic:generators, priority:alta

**Criterios de aceptación:**
- [ ] Clase `LinkedInGenerator` implementada
- [ ] Estructura: Hook → Historia → Aprendizaje → CTA
- [ ] Tono profesional pero cercano
- [ ] 3-5 emojis estratégicos, 3-5 hashtags
- [ ] 150-300 palabras
- [ ] Tests con mock de Gemini

**Tareas técnicas:**
- [ ] Crear `src/generators/linkedin.py`
- [ ] Crear prompt de LinkedIn en templates
- [ ] Tests en `tests/test_linkedin.py`

**Descripción técnica:**
- **Qué hacer:** Crear el generador de posts de LinkedIn a partir de testimonios
- **Qué funciona:** Genera contenido profesional para LinkedIn automáticamente
- **Dónde:** `src/generators/linkedin.py`

---

### FICHA HU-S3-002
**Título:** Generador de newsletters
**Como:** community manager
**Quiero:** generar contenido para newsletters semanales
**Para qué:** mantener informada a la comunidad

**Sprint:** 3 | **Epic:** Generadores | **Priority:** 🟡 Media | **Story Points:** 5
**Due:** @Yis-ai-eng
**Labels:** feat, epic:generators, priority:media

**Criterios de aceptación:**
- [ ] Clase `NewsletterGenerator` implementada
- [ ] Estructura: Highlight → Contexto → Aprendizaje → Recurso
- [ ] Tono informativo y motivacional
- [ ] 100-200 palabras

**Tareas técnicas:**
- [ ] Crear `src/generators/newsletter.py`
- [ ] Crear prompt de newsletter
- [ ] Tests en `tests/test_newsletter.py`

**Descripción técnica:**
- **Qué hacer:** Crear el generador de contenido para newsletters
- **Qué funciona:** Genera contenido semanal para mantener informada a la comunidad
- **Dónde:** `src/generators/newsletter.py`

---

### FICHA HU-S3-003
**Título:** Generador de FAQs
**Como:** community manager
**Quiero:** generar FAQs a partir de dudas técnicas recurrentes
**Para qué:** tener una base de conocimiento auto-generada

**Sprint:** 3 | **Epic:** Generadores | **Priority:** 🟡 Media | **Story Points:** 5
**Due:** @Yis-ai-eng
**Labels:** feat, epic:generators, priority:media

**Criterios de aceptación:**
- [ ] Clase `FAQGenerator` implementada
- [ ] Formato: Pregunta → Respuesta → Explicación → Ejemplo
- [ ] Incluir código si es duda de programación
- [ ] Máximo 300 palabras

**Tareas técnicas:**
- [ ] Crear `src/generators/faq.py`
- [ ] Crear prompt de FAQ
- [ ] Tests en `tests/test_faq.py`

**Descripción técnica:**
- **Qué hacer:** Crear el generador de preguntas frecuentes (FAQ)
- **Qué funciona:** Genera FAQs a partir de dudas técnicas recurrentes
- **Dónde:** `src/generators/faq.py`

---

### FICHA HU-S3-004
**Título:** Generador de testimonios
**Como:** community manager
**Quiero:** formatear testimonios de usuarios para redes sociales
**Para qué:** compartir experiencias reales

**Sprint:** 3 | **Epic:** Generadores | **Priority:** 🟡 Media | **Story Points:** 5
**Due:** @Yis-ai-eng
**Labels:** feat, epic:generators, priority:media

**Criterios de aceptación:**
- [ ] Clase `TestimonialGenerator` implementada
- [ ] Formato: Nombre → Contexto → Logro → Recomendación
- [ ] Tono auténtico e inspirador
- [ ] 50-150 palabras

**Tareas técnicas:**
- [ ] Crear `src/generators/testimonial.py`
- [ ] Crear prompt de testimonio
- [ ] Tests en `tests/test_testimonial.py`

**Descripción técnica:**
- **Qué hacer:** Crear el generador de testimonios formateados
- **Qué funciona:** Formatea experiencias positivas como testimonios
- **Dónde:** `src/generators/testimonial.py`

---

### FICHA HU-S3-005
**Título:** Pipeline completo end-to-end
**Como:** desarrollador del equipo
**Quiero:** un pipeline que procese un batch completo de entrada a salida
**Para qué:** demostrar que todo el sistema funciona junto

**Sprint:** 3 | **Epic:** Infraestructura | **Priority:** 🔴 Alta | **Story Points:** 8
**Due:** @Rox-0864
**Labels:** feat, epic:infra, priority:alta

**Criterios de aceptación:**
- [ ] Pipeline: JSON entrada → Ingesta → Análisis → Decisiones → Generadores → JSON salida
- [ ] Incluye todos los campos del schema de salida
- [ ] Manejo de errores en cada paso
- [ ] Tests end-to-end con sample de 10 mensajes

**Tareas técnicas:**
- [ ] Crear `src/pipeline.py`
- [ ] Integrar todos los módulos
- [ ] Crear sample JSON de prueba en `data/raw/sample.json`
- [ ] Tests en `tests/test_pipeline.py`

**Descripción técnica:**
- **Qué hacer:** Crear el pipeline completo que una ingesta, análisis, decisiones y generadores
- **Qué funciona:** Es el punto de entrada principal. Recibe JSON y retorna JSON
- **Dónde:** `src/pipeline.py`

---

### FICHA HU-S3-006
**Título:** Validación del JSON de entrada
**Como:** desarrollador del equipo
**Quiero:** validar que el JSON de entrada sea correcto antes de procesar
**Para qué:** evitar errores en cascada por datos malformados

**Sprint:** 3 | **Epic:** Ingesta | **Priority:** 🟡 Media | **Story Points:** 3
**Due:** @Elias
**Labels:** feat, epic:ingest, priority:media

**Criterios de aceptación:**
- [ ] Validar estructura del JSON de entrada
- [ ] Validar cada interacción (id, content, author, timestamp)
- [ ] Reportar errores sin detener el batch
- [ ] Tests para JSON válido e inválido

**Tareas técnicas:**
- [ ] Crear `src/ingest/validator.py`
- [ ] Implementar validación de batch
- [ ] Tests en `tests/test_validator.py`

**Descripción técnica:**
- **Qué hacer:** Crear validación del JSON de entrada antes de procesar
- **Qué funciona:** Evita que datos malformados rompan el pipeline
- **Dónde:** `src/ingest/validator.py`

---

### 🔧 AUXILIAR S3: Emanuel - Preparar OCI bucket
**Qué hacer:** Crear bucket en OCI y configurar variables de entorno
**Por qué:** Preparación para Sprint 4 (storage)
**Dónde:** Consola OCI + .env
**Due:** @emanuelperacchia

### 🔧 AUXILIAR S3: Marcelo - Preparar UI para curaduría
**Qué hacer:** Diseñar la interfaz de aprobación/editado de activos
**Por qué:** Preparación para Sprint 4 (panel de curaduría)
**Dónde:** Figma, boceto
**Due:** @Marcelo Rolon

### 🔧 AUXILIAR S3: Antonio - Templates de documentación
**Qué hacer:** Crear plantillas de documentación para API, despliegue y pipeline
**Por qué:** Preparación para Sprint 5 (docs final)
**Dónde:** `docs/templates/`
**Due:** @Antonio3051

---

## 🗓️ SPRINT 4: OCI + UI (12/10 - 18/10)

---

### FICHA HU-S4-001
**Título:** Implementar cliente de conexión con OCI
**Como:** administrador del repo
**Quiero:** tener conexión con OCI Object Storage funcionando
**Para qué:** guardar activos y resultados en la nube

**Sprint:** 4 | **Epic:** OCI | **Priority:** 🔴 Alta | **Story Points:** 5
**Due:** @emanuelperacchia
**Labels:** feat, epic:oci, priority:alta

**Criterios de aceptación:**
- [ ] Clase `OCIClient` implementada
- [ ] Lee credenciales de variables de entorno
- [ ] Método `test_connection()` verifica conexión
- [ ] Manejo de errores de conexión

**Tareas técnicas:**
- [ ] Crear `src/oci/client.py`
- [ ] Configurar `.env` con variables OCI
- [ ] Tests en `tests/test_oci_client.py`

**Descripción técnica:**
- **Qué hacer:** Implementar el cliente de conexión con Oracle Cloud Infrastructure
- **Qué funciona:** Es la base para todo lo relacionado con OCI
- **Dónde:** `src/oci/client.py`

---

### FICHA HU-S4-002
**Título:** Implementar storage de activos en OCI
**Como:** administrador del repo
**Quiero:** subir y descargar activos generados al bucket de OCI
**Para qué:** cumplir con el requisito obligatorio de OCI

**Sprint:** 4 | **Epic:** OCI | **Priority:** 🔴 Alta | **Story Points:** 8
**Due:** @emanuelperacchia
**Labels:** feat, epic:oci, priority:alta

**Criterios de aceptación:**
- [ ] Clase `OCIStorage` implementada
- [ ] `upload_json(key, data)` → bool
- [ ] `download_json(key)` → dict
- [ ] `upload_text(key, content)` → bool
- [ ] `list_objects(prefix)` → list[str]
- [ ] `save_weekly_assets(week, assets)` → bool
- [ ] `save_decisions(week, decisions)` → bool

**Tareas técnicas:**
- [ ] Crear `src/oci/storage.py`
- [ ] Implementar todos los métodos
- [ ] Tests en `tests/test_oci_storage.py`

**Descripción técnica:**
- **Qué hacer:** Implementar operaciones de subida y descarga de archivos en OCI
- **Qué funciona:** Guarda activos generados en la nube. Requisito obligatorio OCI
- **Dónde:** `src/oci/storage.py`

---

### FICHA HU-S4-003
**Título:** Crear dashboard de métricas en Streamlit
**Como:** community manager
**Quiero:** ver un dashboard visual con métricas de sentimiento y actividad
**Para qué:** tomar decisiones informadas

**Sprint:** 4 | **Epic:** UI | **Priority:** 🔴 Alta | **Story Points:** 8
**Due:** @Marcelo Rolon
**Labels:** feat, epic:ui, priority:alta

**Criterios de aceptación:**
- [ ] Aplicación Streamlit funcionando en `app.py`
- [ ] Gráfico de sentimiento (pie chart o bar)
- [ ] Top 10 temas más discutidos (bar chart)
- [ ] Número de mensajes procesados (metric)
- [ ] Filtros por fecha y fuente
- [ ] URL: `localhost:8501`

**Tareas técnicas:**
- [ ] Crear `src/interface/app.py`
- [ ] Crear página de dashboard
- [ ] Agregar charts con Streamlit
- [ ] Tests manuales

**Descripción técnica:**
- **Qué hacer:** Crear el dashboard de métricas en Streamlit con gráficos
- **Qué funciona:** Es la pantalla principal donde el community manager ve el estado de la comunidad
- **Dónde:** `src/interface/app.py`

---

### FICHA HU-S4-004
**Título:** Crear panel de curaduría en Streamlit
**Como:** community manager
**Quiero:** revisar y aprobar/editar activos antes de publicar
**Para qué:** controlar la calidad del contenido generado

**Sprint:** 4 | **Epic:** UI | **Priority:** 🔴 Alta | **Story Points:** 8
**Due:** @Marcelo Rolon
**Labels:** feat, epic:ui, priority:alta

**Criterios de aceptación:**
- [ ] Lista de activos pendientes de revisión
- [ ] Botones: Aprobar / Editar / Rechazar
- [ ] Preview del contenido generado
- [ ] Editar texto antes de aprobar
- [ ] Guardar estado de aprobación

**Tareas técnicas:**
- [ ] Crear `src/interface/pages/2_curaduria.py`
- [ ] Implementar flujo de aprobación
- [ ] Tests manuales

**Descripción técnica:**
- **Qué hacer:** Crear el panel para aprobar/editar/rechazar activos generados
- **Qué funciona:** Permite al community manager controlar la calidad antes de publicar
- **Dónde:** `src/interface/pages/2_curaduria.py`

---

### FICHA HU-S4-005
**Título:** Crear panel de alertas en Streamlit
**Como:** community manager
**Quiero:** ver alertas de miembros en riesgo y dudas recurrentes
**Para qué:** tomar acción a tiempo

**Sprint:** 4 | **Epic:** UI | **Priority:** 🟡 Media | **Story Points:** 5
**Due:** @Marcelo Rolon
**Labels:** feat, epic:ui, priority:media

**Criterios de aceptación:**
- [ ] Lista de alertas de miembros en riesgo con nivel visual
- [ ] Razón de la alerta
- [ ] Lista de dudas recurrentes con conteo
- [ ] Sugerencia de FAQ para cada duda recurrente

**Tareas técnicas:**
- [ ] Crear `src/interface/pages/3_alertas.py`
- [ ] Conectar con MemberRiskDetector y RecurringTopicsDetector
- [ ] Tests manuales

**Descripción técnica:**
- **Qué hacer:** Crear el panel de alertas de riesgo y dudas recurrentes
- **Qué funciona:** Muestra problemas que necesitan atención inmediata
- **Dónde:** `src/interface/pages/3_alertas.py`

---

### FICHA HU-S4-006
**Título:** Crear API endpoint JSON
**Como:** desarrollador del equipo
**Quiero:** tener un endpoint que reciba JSON y retorne JSON procesado
**Para qué:** cumplir con el formato de entrada/salida del sistema

**Sprint:** 4 | **Epic:** Infraestructura | **Priority:** 🔴 Alta | **Story Points:** 5
**Due:** @Rox-0864
**Labels:** feat, epic:infra, priority:alta

**Criterios de aceptación:**
- [ ] Endpoint `POST /procesar` que recibe JSON de entrada
- [ ] Retorna JSON de salida completo
- [ ] Validación de entrada con Pydantic
- [ ] Health check endpoint `GET /health`
- [ ] Documentación del API

**Tareas técnicas:**
- [ ] Crear `src/api/app.py`
- [ ] Crear `POST /procesar` y `GET /health`
- [ ] Modelo request/response con Pydantic
- [ ] Tests en `tests/test_api.py`

**Descripción técnica:**
- **Qué hacer:** Crear el API endpoint que recibe JSON y retorna JSON procesado
- **Qué funciona:** Permite integración con sistemas externos
- **Dónde:** `src/api/app.py`

---

### 🔧 AUXILIAR S4: Yis - Preparar tests de generadores
**Qué hacer:** Escribir tests unitarios para los 4 generadores creados en Sprint 3
**Por qué:** Garantizar calidad antes de Sprint 5
**Dónde:** `tests/test_generators.py`
**Due:** @Yis-ai-eng

### 🔧 AUXILIAR S4: Elias - Preparar datos para upload OCI
**Qué hacer:** Crear dataset de prueba para validar upload a OCI
**Por qué:** Probar la integración OCI en Sprint 5
**Dónde:** `data/raw/oci-test.json`
**Due:** @Elias

### 🔧 AUXILIAR S4: Antonio - Documentar setup OCI
**Qué hacer:** Escribir instrucciones de configuración de OCI
**Por qué:** Preparación para documentación final
**Dónde:** `docs/oci-setup.md`
**Due:** @Antonio3051

---

## 🗓️ SPRINT 5: RELEASE FINAL (19/10 - 27/10)

---

### FICHA HU-S5-001
**Título:** Desplegar en OCI Compute
**Como:** administrador del repo
**Quiero:** tener la aplicación corriendo en OCI
**Para qué:** cumplir con el requisito obligatorio de despliegue en OCI

**Sprint:** 5 | **Epic:** Despliegue | **Priority:** 🔴 Alta | **Story Points:** 8
**Due:** @emanuelperacchia
**Labels:** feat, epic:oci, priority:alta

**Criterios de aceptación:**
- [ ] Aplicación desplegada en OCI Compute (VM.Standard.E2.1.Micro)
- [ ] Streamlit corriendo en puerto 8501
- [ ] Pipeline corriendo en OCI
- [ ] Bucket `communitylab-activos-marketing` con datos
- [ ] URL pública accesible
- [ ] Documentación de despliegue en `docs/deploy.md`

**Tareas técnicas:**
- [ ] Configurar OCI Compute Instance
- [ ] Instalar Python + dependencias en OCI
- [ ] Subir código (git clone en OCI)
- [ ] Configurar .env en OCI
- [ ] Levantar Streamlit
- [ ] Configurar firewall (allow port 8501)
- [ ] Documentar en `docs/deploy.md`

**Descripción técnica:**
- **Qué hacer:** Desplegar la aplicación en OCI Compute y dejarla corriendo
- **Qué funciona:** Cumple el requisito obligatorio de despliegue en OCI
- **Dónde:** OCI Compute Instance (VM.Standard.E2.1.Micro)

---

### FICHA HU-S5-002
**Título:** Finalizar documentación técnica completa
**Como:** @Antonio3051
**Quiero:** documentación completa del proyecto
**Para qué:** que el jurado entienda la arquitectura

**Sprint:** 5 | **Epic:** Documentación | **Priority:** 🔴 Alta | **Story Points:** 5
**Due:** @Antonio3051
**Labels:** docs, epic:infra, priority:alta

**Criterios de aceptación:**
- [ ] `README.md` actualizado con descripción, stack, setup, links
- [ ] `docs/arquitectura.md` con diagramas Mermaid actualizados
- [ ] `docs/api.md` documentación de endpoints
- [ ] `docs/deploy.md` instrucciones de despliegue
- [ ] `docs/pipeline.md` flujo completo del pipeline
- [ ] Todos los docstrings en código
- [ ] Licencias de datasets documentadas

**Tareas técnicas:**
- [ ] Actualizar README.md
- [ ] Verificar arquitectura.md
- [ ] Crear docs/api.md
- [ ] Crear docs/deploy.md
- [ ] Crear docs/pipeline.md

**Descripción técnica:**
- **Qué hacer:** Finalizar toda la documentación técnica del proyecto
- **Qué funciona:** Documentación que jurado y equipo usarán
- **Dónde:** `docs/` (arquitectura.md, api.md, deploy.md, pipeline.md)

---

### FICHA HU-S5-003
**Título:** Grabar video demostrativo
**Como:** @Antonio3051
**Quiero:** un video mostrando el funcionamiento del sistema
**Para qué:** presentación al jurado

**Sprint:** 5 | **Epic:** Demo | **Priority:** 🔴 Alta | **Story Points:** 5
**Due:** @Antonio3051
**Labels:** docs, epic:ui, priority:alta

**Criterios de aceptación:**
- [ ] Video de 5-10 minutos
- [ ] Muestra: carga de JSON → procesamiento → resultados
- [ ] Muestra: dashboard interactivo
- [ ] Muestra: panel de curaduría
- [ ] Muestra: panel de alertas
- [ ] Narración clara
- [ ] Subido a YouTube (no público)

**Descripción técnica:**
- **Qué hacer:** Grabar un video demostrativo del sistema funcionando
- **Qué funciona:** Es la forma de mostrar el proyecto al jurado sin estar presente
- **Dónde:** YouTube (no público) — grabación de pantalla

---

### FICHA HU-S5-004
**Título:** Preparar presentación final
**Como:** @Yis-ai-eng
**Quiero:** tener la presentación lista para el jurado
**Para qué:** defender el proyecto ante el jurado

**Sprint:** 5 | **Epic:** Demo | **Priority:** 🔴 Alta | **Story Points:** 3
**Due:** @Yis-ai-eng
**Labels:** docs, epic:ui, priority:alta

**Criterios de aceptación:**
- [ ] Presentación con: problema, solución, arquitectura, demo, resultados
- [ ] Máximo 10 slides
- [ ] Cada miembro sabe qué presentar
- [ ] Tiempo: 15 minutos + 5 minutos Q&A

**Tareas técnicas:**
- [ ] Crear presentación (Google Slides)
- [ ] Slide 1: Problema
- [ ] Slide 2: Solución CommunityLab
- [ ] Slide 3: Arquitectura
- [ ] Slide 4: JSON entrada/salida
- [ ] Slide 5-6: Demo screenshots
- [ ] Slide 7: Stack tecnológico
- [ ] Slide 8: Resultados
- [ ] Slide 9: Team
- [ ] Slide 10: Q&A

**Descripción técnica:**
- **Qué hacer:** Preparar la presentación final para el jurado
- **Qué funciona:** Es la defensa verbal del proyecto
- **Dónde:** Google Slides

---

### FICHA HU-S5-005
**Título:** Crear dataset de prueba completo
**Como:** desarrollador del equipo
**Quiero:** tener un dataset de prueba que demuestre todas las funcionalidades
**Para qué:** que el jurado vea el sistema funcionando con datos reales

**Sprint:** 5 | **Epic:** Datos | **Priority:** 🔴 Alta | **Story Points:** 3
**Due:** @Elias
**Labels:** feat, epic:ingest, priority:alta

**Criterios de aceptación:**
- [ ] JSON de entrada con mínimo 50 mensajes
- [ ] Incluir: testimonios, dudas técnicas, feedback, discusiones
- [ ] Colocar en `data/raw/communitylab-sample.json`
- [ ] JSON de salida esperado en `data/processed/communitylab-expected.json`

**Descripción técnica:**
- **Qué hacer:** Crear un dataset de prueba con 50 mensajes diversos
- **Qué funciona:** Permite demostrar todas las funcionalidades con datos reales
- **Dónde:** `data/raw/communitylab-sample.json`

---

### FICHA HU-S5-006
**Título:** QA final y corrección de bugs
**Como:** @Rox-0864
**Quiero:** que el sistema funcione sin errores críticos
**Para qué:** que la demo no falle durante la presentación

**Sprint:** 5 | **Epic:** QA | **Priority:** 🔴 Alta | **Story Points:** 5
**Due:** @Rox-0864
**Labels:** fix, epic:infra, priority:alta

**Criterios de aceptación:**
- [ ] Pipeline completo procesa sample sin errores
- [ ] Dashboard carga correctamente
- [ ] Panel de curaduría funciona
- [ ] Panel de alertas muestra datos correctos
- [ ] API `/procesar` retorna JSON válido
- [ ] OCI upload/download funciona
- [ ] Tests pasan: `pytest tests/ -v`
- [ ] Cada miembro prueba el sistema completo

**Descripción técnica:**
- **Qué hacer:** Probar todo el sistema end-to-end y corregir bugs críticos
- **Qué funciona:** Garantiza que la demo no falle
- **Dónde:** Todo el código — testing completo

---

### FICHA HU-S5-007
**Título:** Crear webhooks para notificaciones
**Como:** administrador del repo
**Quiero:** que el sistema notifique cuando hay nuevos resultados o alertas
**Para qué:** el equipo pueda reaccionar rápido

**Sprint:** 5 | **Epic:** Infraestructura | **Priority:** 🟡 Media | **Story Points:** 3
**Due:** @emanuelperacchia
**Labels:** feat, epic:infra, priority:media

**Criterios de aceptación:**
- [ ] Webhook que envía notificación cuando batch se procesa
- [ ] Webhook que envía alertas de riesgo
- [ ] Configurable en `.env`
- [ ] Tests del webhook

**Descripción técnica:**
- **Qué hacer:** Crear webhooks para notificaciones
- **Qué funciona:** Notifica al equipo cuando algo importante pasa
- **Dónde:** `src/notifications/webhook.py`

---

### 🔧 AUXILIAR S5: Marcelo - Preparar presentación visual
**Qué hacer:** Crear slides visuales o apoyo gráfico para la presentación
**Por qué:** La presentación necesita ser visualmente atractiva
**Dónde:** Google Slides / Canva
**Due:** @Marcelo Rolon

---

## 📊 RESUMEN POR PERSONA (despues de actualizar)

| Persona | S1 | S2 | S3 | S4 | S5 | Total |
|---------|----|----|----|----|----|-------|
| **@emanuelperacchia** | HU-S1-005 | HU-S2-008 | Aux: OCI prep | HU-S4-001,002 | HU-S5-001,007 | **7** |
| **@Rox-0864** | HU-S1-001,002 | HU-S2-001,002,003,004,005 | HU-S3-005 | HU-S4-006 | HU-S5-006 | **10** |
| **@Elias** | HU-S1-003,004 | HU-S2-006 | HU-S3-006 | Aux: OCI data | HU-S5-005 | **6** |
| **@Yis-ai-eng** | HU-S1-006 | HU-S2-007 | HU-S3-001,002 | Aux: tests | HU-S5-004 | **6** |
| **@Marcelo Rolon** | HU-S1-007 | Aux: mockup | Aux: curaduria | HU-S4-003,004,005 | Aux: presentacion | **7** |
| **@Antonio3051** | HU-S1-008 | Aux: docs | Aux: templates | Aux: OCI docs | HU-S5-002,003 | **6** |

---

## 📊 RESUMEN POR EPIC

| Epic | Fichas | Prioridad máxima |
|------|--------|-------------------|
| Dominio | 2 (S1) | 🔴 Alta |
| Ingesta | 4 (S1, S3) | 🔴 Alta |
| Análisis | 4 (S2) | 🔴 Alta |
| Decisiones | 3 (S2) | 🔴 Alta |
| Generadores | 4 (S3) | 🔴 Alta |
| Infraestructura | 4 (S2, S3, S5) | 🔴 Alta |
| OCI | 3 (S4, S5) | 🔴 Alta |
| UI | 4 (S4) | 🔴 Alta |
| Despliegue | 1 (S5) | 🔴 Alta |
| Documentación | 1 (S5) | 🔴 Alta |
| Demo | 2 (S5) | 🔴 Alta |
| Datos | 1 (S5) | 🔴 Alta |
| QA | 1 (S5) | 🔴 Alta |
| Infra (aux) | 5 | 🟡 Media |

**Total fichas:** 35 principales + 10 auxiliares = 45 tareas

---

*Documento generado para CommunityLab — Oracle ONE Hackathon G10*
*Distribución: 6 personas × 5 sprints con tarea en cada sprint*
*Fecha límite: 27/10*
