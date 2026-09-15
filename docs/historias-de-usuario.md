# 📋 Historias de Usuario — CommunityLab

> Formato listo para copiar a Trello/Jira.
> Cada tarjeta = 1 historia de usuario.

---

## 🏗️ ÉPICA 1: DOMINIO Y MODELOS BASE

### HU-001: Definir modelo de datos Message
**Como** desarrollador del equipo,
**Quiero** tener una clase Message que represente un mensaje de comunidad,
**Para que** todos los módulos trabajen con el mismo formato de datos.

**Criterios de aceptación:**
- [ ] Clase Message con campos: id, content, author, channel, source, timestamp, metadata
- [ ] Validación con Pydantic (campos requeridos, tipos correctos)
- [ ] Soporte para fuentes: discord, slack, github, forum
- [ ] Tests unitarios que validen la estructura
- [ ] Documentación de campos en docstrings

**Tareas técnicas:**
- Crear `src/domain/models.py`
- Definir enums: SentimentType, AssetType, RiskLevel
- Crear modelos: Message, SentimentResult, CategorizationResult, RelevanceResult
- Crear tests en `tests/test_domain.py`

**Prioridad:** 🔴 Alta
**Asignado:** Admin
**Puntos:** 3

---

### HU-002: Definir interfaces/contratos
**Como** desarrollador del equipo,
**Quiero** tener interfaces abstractas para cada módulo,
**Para que** sepamos exactamente qué debe hacer cada componente.

**Criterios de aceptación:**
- [ ] Interfaz DataLoader con método `load(source) -> list[Message]`
- [ ] Interfaz SentimentAnalyzer con método `analyze(message) -> SentimentResult`
- [ ] Interfaz Categorizer con método `categorize(message) -> CategorizationResult`
- [ ] Interfaz RelevanceScorer con método `score(message) -> RelevanceResult`
- [ ] Interfaz DecisionEngine con método `decide(analysis) -> Decision`
- [ ] Interfaz AssetGenerator con método `generate(message, analysis) -> GeneratedAsset`

**Tareas técnicas:**
- Crear `src/domain/interfaces.py`
- Usar ABC (Abstract Base Classes) de Python
- Documentar cada interfaz con docstrings detallados

**Prioridad:** 🔴 Alta
**Asignado:** Admin
**Puntos:** 2

---

## 📥 ÉPICA 2: INGESTA DE DATOS

### HU-003: Cargar mensajes desde JSON
**Como** usuario de CommunityLab,
**Quiero** poder cargar mensajes de Discord/Slack desde archivos JSON,
**Para que** el sistema pueda procesar datos reales de comunidades.

**Criterios de aceptación:**
- [ ] Clase JSONLoader que lea archivos JSON
- [ ] Formato esperado: array de objetos con id, content, author, channel, timestamp
- [ ] Manejo de errores: archivo no existe, JSON malformado, campos faltantes
- [ ] Retorna lista de objetos Message
- [ ] Tests con JSON válido e inválido

**Tareas técnicas:**
- Crear `src/ingest/loader.py`
- Implementar JSONLoader
- Crear DiscordJSONLoader (formato específico de export Discord)
- Tests en `tests/test_ingest.py`

**Prioridad:** 🔴 Alta
**Asignado:** Miembro A
**Puntos:** 5

---

### HU-004: Normalizar datos de diferentes fuentes
**Como** desarrollador,
**Quiero** que los datos de Discord, Slack y GitHub se conviertan a un formato único,
**Para que** el pipeline no se rompa cambien la fuente de datos.

**Criterios de aceptación:**
- [ ] Clase DataNormalizer con mapeo de campos por fuente
- [ ] Soporte para Discord, Slack, GitHub, Forum
- [ ] Parseo de timestamps en múltiples formatos
- [ ] Si un campo falta, usar valor por defecto (no fallar)
- [ ] Tests para cada fuente de datos

**Tareas técnicas:**
- Crear `src/ingest/normalizer.py`
- Definir field_mapping por fuente
- Implementar _parse_timestamp con múltiples formatos
- Tests en `tests/test_ingest.py`

**Prioridad:** 🔴 Alta
**Asignado:** Miembro A
**Puntos:** 5

---

### HU-005: Validar mensajes antes de procesar
**Como** desarrollador,
**Quiero** validar que los mensajes cumplan requisitos mínimos,
**Para que** no procesemos datos basura que rompan el pipeline.

**Criterios de aceptación:**
- [ ] Validar: ID no vacío, contenido entre 10-4000 chars, autor no vacío
- [ ] Validar: fuente en lista permitida, timestamp no nulo
- [ ] Retornar (es_válido, lista_errores)
- [ ] Validación en lote con estadísticas
- [ ] Tests para cada caso de validación

**Tareas técnicas:**
- Crear `src/ingest/validators.py`
- Implementar MessageValidator
- Implementar validate_batch
- Tests en `tests/test_ingest.py`

**Prioridad:** 🟡 Media
**Asignado:** Miembro A
**Puntos:** 3

---

## 🧠 ÉPICA 3: ANÁLISIS IA

### HU-006: Analizar sentimiento con Gemini
**Como** usuario de CommunityLab,
**Quiero** que el sistema detecte si un mensaje es positivo, negativo o neutral,
**Para que** podamos identificar contenido valioso y miembros en riesgo.

**Criterios de aceptación:**
- [ ] Clase GeminiSentimentAnalyzer
- [ ] Usa Google Gemini API (model gemini-pro)
- [ ] Retorna: sentiment (positivo/negativo/neutral), score (0-1), reasoning
- [ ] Manejo de errores de API (timeout, rate limit, API key inválida)
- [ ] Resultado por defecto en caso de error
- [ ] Tests con mock de Gemini

**Tareas técnicas:**
- Crear `src/analysis/sentiment.py`
- Configurar cliente Gemini
- Crear prompt de análisis
- Parsear respuesta JSON
- Tests en `tests/test_analysis.py`

**Prioridad:** 🔴 Alta
**Asignado:** Miembro B
**Puntos:** 8

---

### HU-007: Categorizar mensajes automáticamente
**Como** usuario de CommunityLab,
**Quiero** que el sistema clasifique los mensajes en categorías (duda técnica, testimonio, feedback, etc.),
**Para que** sepamos qué tipo de contenido tenemos y generemos los activos correctos.

**Criterios de aceptación:**
- [ ] Clase GeminiCategorizer
- [ ] Categorías: duda_tecnica, testimonio, feedback, pregunta_general, discusion, otro
- [ ] Retorna: category, topics (array), entities (array)
- [ ] Entidades = herramientas/lenguajes mencionados
- [ ] Tests para cada categoría

**Tareas técnicas:**
- Crear `src/analysis/categorization.py`
- Crear prompt de categorización
- Definir categorías válidas
- Tests en `tests/test_analysis.py`

**Prioridad:** 🔴 Alta
**Asignado:** Miembro B
**Puntos:** 5

---

### HU-008: Evaluar relevancia para marketing
**Como** usuario de CommunityLab,
**Quiero** que el sistema puntúe qué tan relevante es un mensaje para marketing,
**Para que** solo publiquemos contenido de alto impacto.

**Criterios de aceptación:**
- [ ] Clase GeminiRelevanceScorer
- [ ] Score de 0.0 a 1.0
- [ ] Booleano is_marketing_worthy (true si score >= 0.6)
- [ ] Razón de la puntuación
- [ ] Tests con mensajes relevantes y no relevantes

**Tareas técnicas:**
- Crear `src/analysis/relevance.py`
- Crear prompt de relevancia
- Definir umbral de relevancia
- Tests en `tests/test_analysis.py`

**Prioridad:** 🟡 Media
**Asignado:** Miembro B
**Puntos:** 5

---

### HU-009: Orquestar análisis completo
**Como** desarrollador,
**Quiero** tener un orquestador que ejecute sentimiento → categorización → relevancia,
**Para que** el pipeline sea un solo paso y no tengamos que llamar a cada analizador por separado.

**Criterios de aceptación:**
- [ ] Clase AnalysisOrchestrator
- [ ] Ejecuta los 3 análisis en orden
- [ ] Retorna AnalysisComplete (message + sentiment + categorization + relevance)
- [ ] Loggear progreso (opcional)
- [ ] Manejo de errores sin detener el batch

**Tareas técnicas:**
- Crear `src/analysis/orchestrator.py`
- Integrar los 3 analizadores
- Crear modelo AnalysisComplete
- Tests en `tests/test_analysis.py`

**Prioridad:** 🔴 Alta
**Asignado:** Miembro B
**Puntos:** 5

---

## 🚦 ÉPICA 4: MOTOR DE DECISIONES

### HU-010: Decidir qué hacer con cada mensaje
**Como** usuario de CommunityLab,
**Quiero** que el sistema decida automáticamente si un mensaje debe publicarse, guardarse o descartarse,
**Para que** no tengamos que revisar manualmente cada mensaje.

**Criterios de aceptación:**
- [ ] Clase RuleBasedDecisionEngine
- [ ] Reglas: testimonio positivo relevante → LinkedIn
- [ ] Reglas: duda técnica → FAQ
- [ ] Reglas: no relevante → descartar
- [ ] Retorna: action, asset_type, reason
- [ ] Tests para cada regla

**Tareas técnicas:**
- Crear `src/decisions/engine.py`
- Definir reglas de negocio
- Implementar lógica de decisión
- Tests en `tests/test_decisions.py`

**Prioridad:** 🔴 Alta
**Asignado:** Miembro C
**Puntos:** 8

---

### HU-011: Detectar miembros en riesgo
**Como** community manager,
**Quiero** que el sistema detecte miembros con sentimiento negativo recurrente,
**Para que** podamos intervenir antes de que abandonen la comunidad.

**Criterios de aceptación:**
- [ ] Clase MemberRiskDetector
- [ ] Trackear historial de sentimiento por miembro
- [ ] Detectar tendencia negativa
- [ ] Alertas con nivel: bajo/medio/alto
- [ ] Razones de la alerta

**Tareas técnicas:**
- Crear `src/decisions/member_risk.py`
- Implementar historial por miembro
- Detectar tendencia negativa
- Tests en `tests/test_decisions.py`

**Prioridad:** 🟡 Media
**Asignado:** Miembro C
**Puntos:** 5

---

### HU-012: Detectar dudas recurrentes
**Como** community manager,
**Quiero** que el sistema detecte preguntas que se repiten frecuentemente,
**Para que** creemos FAQs automáticamente y reduzcamos preguntas repetidas.

**Criterios de aceptación:**
- [ ] Clase RecurringTopicsDetector
- [ ] Contar frecuencia de temas
- [ ] Retornar temas con más de N ocurrencias
- [ ] Incluir ejemplos de mensajes por tema
- [ ] Sugerir títulos de FAQ

**Tareas técnicas:**
- Crear `src/decisions/recurring_topics.py`
- Implementar contador de temas
- Crear get_topics_for_faq
- Tests en `tests/test_decisions.py`

**Prioridad:** 🟡 Media
**Asignado:** Miembro C
**Puntos:** 5

---

## ✍️ ÉPICA 5: GENERADORES DE CONTENIDO

### HU-013: Generar posts de LinkedIn
**Como** community manager,
**Quiero** que el sistema genere posts de LinkedIn a partir de testimonios positivos,
**Para que** publiquemos contenido profesional automáticamente.

**Criterios de aceptación:**
- [ ] Clase LinkedInGenerator
- [ ] Estructura: Hook → Historia → Aprendizaje → CTA
- [ ] Tono profesional pero cercano
- [ ] 3-5 emojis estratégicos
- [ ] 3-5 hashtags relevantes
- [ ] 150-300 palabras
- [ ] Tests con mock de Gemini

**Tareas técnicas:**
- Crear `src/generators/linkedin.py`
- Crear prompt de LinkedIn
- Validar formato de salida
- Tests en `tests/test_generators.py`

**Prioridad:** 🔴 Alta
**Asignado:** Miembro D
**Puntos:** 8

---

### HU-014: Generar contenido para newsletters
**Como** community manager,
**Quiero** que el sistema genere contenido para newsletters semanales,
**Para que** mantengamos a la comunidad informada sin esfuerzo manual.

**Criterios de aceptación:**
- [ ] Clase NewsletterGenerator
- [ ] Estructura: Highlight → Contexto → Aprendizaje → Recurso
- [ ] Tono informativo y motivacional
- [ ] Mencionar al miembro de forma positiva
- [ ] 100-200 palabras

**Tareas técnicas:**
- Crear `src/generators/newsletter.py`
- Crear prompt de newsletter
- Tests en `tests/test_generators.py`

**Prioridad:** 🟡 Media
**Asignado:** Miembro D
**Puntos:** 5

---

### HU-015: Generar FAQs
**Como** community manager,
**Quiero** que el sistema genere FAQs a partir de dudas técnicas recurrentes,
**Para que** tengamos una base de conocimiento auto-generada.

**Criterios de aceptación:**
- [ ] Clase FAQGenerator
- [ ] Formato: Pregunta → Respuesta → Explicación → Ejemplo
- [ ] Incluir código si es duda de programación
- [ ] Máximo 300 palabras
- [ ] Alternativas si las hay

**Tareas técnicas:**
- Crear `src/generators/faq.py`
- Crear prompt de FAQ
- Tests en `tests/test_generators.py`

**Prioridad:** 🟡 Media
**Asignado:** Miembro D
**Puntos:** 5

---

### HU-016: Generar testimonios
**Como** community manager,
**Quiero** que el sistema formatee testimonios de usuarios,
**Para que** compartamos experiencias reales en redes sociales.

**Criterios de aceptación:**
- [ ] Clase TestimonialGenerator
- [ ] Formato: Nombre → Contexto → Logro → Recomendación
- [ ] Tono auténtico e inspirador
- [ ] 50-150 palabras
- [ ] Incluir cita textual adaptada

**Tareas técnicas:**
- Crear `src/generators/testimonial.py`
- Crear prompt de testimonio
- Tests en `tests/test_generators.py`

**Prioridad:** 🟡 Media
**Asignado:** Miembro D
**Puntos:** 5

---

## ☁️ ÉPICA 6: INTEGRACIÓN OCI

### HU-017: Conectar con Oracle Cloud
**Como** administrador,
**Quiero** tener un cliente configurado para OCI Object Storage,
**Para que** el sistema pueda guardar y recuperar archivos en la nube.

**Criterios de aceptación:**
- [ ] Clase OCIClient
- [ ] Lee credenciales de variables de entorno
- [ ] Valida que todas las variables estén presentes
- [ ] Método test_connection para verificar
- [ ] Manejo de errores de conexión

**Tareas técnicas:**
- Crear `src/oci/client.py`
- Configurar OCI SDK
- Documentar variables de entorno requeridas
- Tests en `tests/test_oci.py`

**Prioridad:** 🟡 Media
**Asignado:** Admin
**Puntos:** 5

---

### HU-018: Subir y descargar archivos de OCI
**Como** administrador,
**Quiero** poder subir y descargar archivos JSON del bucket,
**Para que** el pipeline guarde activos y decisiones en la nube.

**Criterios de aceptación:**
- [ ] Clase OCIStorage
- [ ] upload_json(key, data) → bool
- [ ] download_json(key) → dict
- [ ] list_objects(prefix) → list[str]
- [ ] save_weekly_assets(week, assets) → bool
- [ ] save_decision(week, decisions) → bool

**Tareas técnicas:**
- Crear `src/oci/storage.py`
- Implementar métodos de upload/download
- Crear helpers para activos semanales
- Tests en `tests/test_oci.py`

**Prioridad:** 🟡 Media
**Asignado:** Admin
**Puntos:** 8

---

## 🖥️ ÉPICA 7: INTERFAZ (STREAMLIT)

### HU-019: Dashboard de métricas
**Como** community manager,
**Quiero** ver un dashboard con métricas de sentimiento y actividad,
**Para que** tome decisiones informadas sobre la comunidad.

**Criterios de aceptación:**
- [ ] Gráfico de sentimiento (positivo/negativo/neutral)
- [ ] Top 10 temas más discutidos
- [ ] Número de mensajes procesados
- [ ] Filtros por fecha y fuente
- [ ] Datos actualizados en tiempo real (o al recargar)

**Tareas técnicas:**
- Crear `src/interface/app.py`
- Crear página de dashboard
- Integrar con Streamlit
- Conectar con datos procesados

**Prioridad:** 🟡 Media
**Asignado:** Equipo
**Puntos:** 8

---

### HU-020: Panel de curaduría
**Como** community manager,
**Quiero** revisar y aprobar/editar los activos generados antes de publicar,
**Para que** controle la calidad del contenido.

**Criterios de aceptación:**
- [ ] Lista de activos pendientes de revisión
- [ ] Botones: Aprobar / Editar / Rechazar
- [ ] Preview del contenido generado
- [ ] Editar texto antes de aprobar
- [ ] Guardar en OCI al aprobar

**Tareas técnicas:**
- Crear página de curaduría en Streamlit
- Implementar flujo de aprobación
- Conectar con OCI storage

**Prioridad:** 🟡 Media
**Asignado:** Equipo
**Puntos:** 8

---

### HU-021: Panel de alertas
**Como** community manager,
**Quiero** ver alertas de miembros en riesgo y dudas recurrentes,
**Para que** tome acción a tiempo.

**Criterios de aceptación:**
- [ ] Lista de alertas de miembros en riesgo
- [ ] Nivel de riesgo (bajo/medio/alto)
- [ ] Razón de la alerta
- [ ] Última actividad del miembro
- [ ] Sugerencia de acción

**Tareas técnicas:**
- Crear página de alertas en Streamlit
- Conectar con MemberRiskDetector
- Mostrar detalles del miembro

**Prioridad:** 🟡 Media
**Asignado:** Equipo
**Puntos:** 5

---

## 🔧 ÉPICA 8: INFRAESTRUCTURA

### HU-022: Configurar CI automático
**Como** desarrollador,
**Quiero** que los tests se ejecuten automáticamente en cada PR,
**Para que** detectemos errores antes de merge.

**Criterios de aceptación:**
- [ ] GitHub Actions ejecuta pytest en cada PR
- [ ] Verifica linting con flake8
- [ ] Bloquea merge si falla
- [ ] Tiempo de ejecución < 5 minutos

**Tareas técnicas:**
- Crear `.github/workflows/ci.yml`
- Configurar Python 3.11
- Instalar dependencias
- Ejecutar tests

**Prioridad:** 🔴 Alta
**Asignado:** Admin
**Puntos:** 3

---

### HU-023: Configurar branch protection
**Como** admin,
**Quiero** proteger la rama main,
**Para que** nadie haga force push o merge sin review.

**Criterios de aceptación:**
- [ ] Requiere PR para merge
- [ ] Mínimo 1 aprobación
- [ ] No permite force push
- [ ] Requiere status checks (tests pasando)

**Tareas técnicas:**
- Configurar en GitHub → Settings → Branches
- Documentar en CONTRIBUTING.md

**Prioridad:** 🔴 Alta
**Asignado:** Admin
**Puntos:** 2

---

## 📊 RESUMEN POR PRIORIDAD

### 🔴 Alta (MVP)
| ID | Historia | Asignado | Puntos |
|----|----------|----------|--------|
| HU-001 | Modelo Message | Admin | 3 |
| HU-002 | Interfaces | Admin | 2 |
| HU-003 | Cargar JSON | Miembro A | 5 |
| HU-004 | Normalizar datos | Miembro A | 5 |
| HU-006 | Sentiment Analysis | Miembro B | 8 |
| HU-007 | Categorización | Miembro B | 5 |
| HU-009 | Orquestador | Miembro B | 5 |
| HU-010 | Motor decisiones | Miembro C | 8 |
| HU-013 | Generador LinkedIn | Miembro D | 8 |
| HU-022 | CI automático | Admin | 3 |
| HU-023 | Branch protection | Admin | 2 |

**Total Alta:** 54 puntos

### 🟡 Media (Post-MVP)
| ID | Historia | Asignado | Puntos |
|----|----------|----------|--------|
| HU-005 | Validación | Miembro A | 3 |
| HU-008 | Relevancia | Miembro B | 5 |
| HU-011 | Miembros riesgo | Miembro C | 5 |
| HU-012 | Dudas recurrentes | Miembro C | 5 |
| HU-014 | Newsletter | Miembro D | 5 |
| HU-015 | FAQ | Miembro D | 5 |
| HU-016 | Testimonios | Miembro D | 5 |
| HU-017 | Cliente OCI | Admin | 5 |
| HU-018 | Storage OCI | Admin | 8 |
| HU-019 | Dashboard | Equipo | 8 |
| HU-020 | Curaduría | Equipo | 8 |
| HU-021 | Alertas | Equipo | 5 |

**Total Media:** 67 puntos

---

## 🎯 SPRINT SUGERIDO (Hackathon)

### Sprint 1 (Días 1-2): Fundamentos
- HU-001, HU-002 (Admin)
- HU-003, HU-004 (Miembro A)
- HU-022, HU-023 (Admin)

### Sprint 2 (Días 3-4): Core Pipeline
- HU-006, HU-007, HU-009 (Miembro B)
- HU-010 (Miembro C)
- HU-013 (Miembro D)

### Sprint 3 (Días 5-6): Completar y Integrar
- HU-005, HU-008 (Miembro A/B)
- HU-011, HU-012 (Miembro C)
- HU-014, HU-015, HU-016 (Miembro D)

### Sprint 4 (Días 7-8): OCI + UI + Demo
- HU-017, HU-018 (Admin)
- HU-019, HU-020, HU-021 (Equipo)
- Preparar demo
