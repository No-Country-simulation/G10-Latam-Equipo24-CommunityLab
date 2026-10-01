# Matriz de pruebas — Análisis y decisiones (Sprint 2)

**Issue:** HU-S2-009 (#48) · **Versión:** v1.3 (incorpora las decisiones de Rox y la review de Elias y Ema)
**Fecha:** 2026-09-30 · **Autor:** itanflores (QA)
**Base revisada:** `main` @ `096125b`; analizador unificado, `DecisionResult` y pipeline en el PR #73 (`feat/unified-analyzer` @ `9530f90`, sin merge); dataset de demo en el PR #77 (sin merge); detector de dudas en `main` (PR #64) con seguimiento en `feat/recurring-topics` @ `c8fb3d1` y en el follow-up #75
**Fixture asociado:** `tests/fixtures/analysis-decisiones.json` (95 casos especificados con datos; los IDs coinciden con este documento)

Este documento es una **matriz de comportamiento**, no una implementación: describe qué debe hacer cada módulo, con qué entrada y qué resultado se espera. No modifica código de análisis, decisiones ni prompts.

En total especifica **102 casos**: 95 tienen datos en el fixture y 7 se describen solo aquí. Son casos **especificados**; se convierten en tests cuando su módulo se implementa. La suite del repositorio la define el CI y crece con cada PR (la rama del analizador ya suma los suyos); esta matriz no la reemplaza.

## Cómo leer esta matriz

| Marca | Significado |
|---|---|
| ✅ | Verificado contra código real y coincide con lo esperado |
| ⚠️ | Verificado contra código real y **difiere** de lo esperado (ver columna de observado) |
| ⏳ | Especificado por las fichas; pendiente de implementación |
| 🟡 | **PROPUESTO**: la ficha no define este criterio; el dueño del módulo debe confirmarlo o corregirlo |
| ⏸️ | **Fuera de alcance**: la ficha se quitó del MVP en la reestructuración del 28/9 ("si hay tiempo"); el caso se conserva para retomarlo |

Estado del código al 30/9: en `main` ya está `RecurringTopicsDetector` (PR #64). El analizador unificado, `DecisionResult`, la firma nueva de `decide()` y el pipeline conectado viven en el PR #73, sin merge, y se verificaron contra esta matriz (secciones A.4 y F). `src/decisions/engine.py` y `src/prompts/templates.py` aún no existen.

## Índice y propietarios

| Sección | Módulo | Propietario | Ficha | Archivo de prueba |
|---|---|---|---|---|
| A | Análisis unificado (sentimiento, categoría, relevancia) | Rox-0864 | #68 (HU-S2-001 fusionada) | `tests/test_unified_analyzer.py` |
| B | Motor de decisiones | Yis-ai-eng (reasignado desde Rox-0864) | #69 (HU-S2-005) | `tests/test_decisions.py` |
| C | Detector de dudas recurrentes | Yis-ai-eng | HU-S2-007 (PR #64) | `tests/test_recurring_topics.py` |
| D | Detector de miembros en riesgo ⏸️ | Elias-J-Guardado | HU-S2-006 (quitada del MVP) | `tests/test_member_risk.py` |
| E | Prompts y configuración | emanuelperacchia | HU-S2-008 | `tests/test_prompts.py` |

## 1. Convenciones

**Definido por las fichas (#68, #69) y por decisiones del equipo:**

| Elemento | Valor |
|---|---|
| Sentimiento | `positivo`, `negativo`, `neutral`; `score` en [0, 1] es la **confianza** de la etiqueta, no la polaridad; `reasoning` |
| Categorías de análisis (6) | Las del enum `InteractionType`: `testimonio`, `pregunta_tecnica`, `feedback`, `logro`, `discusion`, `otro` (**D-C, decidido en código el 29/9**) |
| Alias de categoría | `duda_tecnica` → `pregunta_tecnica`; `pregunta_general` y `comentario_general` → `otro`; cualquier otro valor no reconocido → `otro` |
| Relevancia | `score` en [0, 1], recortado a ese rango; `is_marketing_worthy` se deriva del score: verdadero si `score >= 0.6` |
| Fallback de categoría | `comentario_general` y cualquier valor no reconocido se mapean a `otro` |
| `tipo` en la entrada | **Decidido el 28/9:** `comentario_general` se mapea a `otro`. La ingesta ya emite `otro` y `pregunta_tecnica` (PR #63) |
| Precedencia entre `tipo` y `category` (D-B) | **Decidido por Rox el 29/9 (O-05):** si el `tipo` es explícito y reconocido (`testimonio`, `pregunta_tecnica`, `feedback`, `logro`, `discusion`), prevalece el `tipo`. Si es `otro`, `comentario_general` o vacío, prevalece la `category` del análisis |
| Regla R1 | Testimonio positivo con relevancia ≥ 0.6 → `action="publicar"`, `asset_type="linkedin"` |
| Regla R2 | Pregunta técnica (duda técnica / pregunta frecuente) → `action="crear_faq"`, `asset_type="faq"` |
| Regla R3 | Mensaje neutral o de relevancia < 0.6 → `action="descartar"` |
| Respuesta por defecto del analizador | Sentimiento `neutral`/0.5, categoría `otro`, sin topics ni entities, relevancia 0.0 y no publicable. Implementada así en la rama de Rox |

**🟡 Propuesto (pendiente de las decisiones D-A, D-D y D-E de la sección 2):**

| Tema | Propuesta |
|---|---|
| Orden de reglas (D-A) | Se evalúan en orden R1 → R2 → R3; gana la primera que aplica |

## 2. Decisiones de contrato pendientes

Surgen de la review de Ema al PR #72. La matriz no las decide: propone una opción, indica qué casos dependen de cada una y quién la cierra. Mientras no se decidan, esos casos quedan 🟡.

| ID | Pregunta | Propuesta | Por qué | Casos que dependen | Decide |
|---|---|---|---|---|---|
| D-A | ¿Toda duda técnica genera `crear_faq`, o solo las recurrentes? | Toda duda técnica genera `crear_faq`, con reglas en orden R1 → R2 → R3 | El ejemplo del PDF genera una sugerencia de FAQ desde una sola duda. Sin orden explícito, R3 descarta casi toda duda, porque su sentimiento típico es neutral | DEC-05, DEC-07, DEC-08 | Yis (#69) |
| D-B | ¿Qué prevalece cuando `tipo` y `category` difieren? | ✅ **Decidido por Rox (29/9):** el `tipo` explícito y reconocido prevalece; si es `otro`, `comentario_general` o vacío, manda `category` | Los mensajes de Mastodon con `tipo = comentario_general` no descartan los testimonios que detecte el análisis | DEC-12, DEC-13, DEC-19, DEC-20, DEC-21 | ✅ Rox |
| D-C | Un solo vocabulario de categorías | ✅ **Decidido en código** (rama de Rox, 29/9): el analizador devuelve los valores del enum `InteractionType`, con alias para `duda_tecnica` y `pregunta_general` | Elimina la ambigüedad entre análisis y contrato | CAT-01, CAT-04, ANL-11, ANL-18, ANL-19 | ✅ Rox |
| D-D | ¿Qué hace que una pregunta sea "frecuente" o "recurrente"? | Recurrente = el `RecurringTopicsDetector` la reporta en el mismo lote (`count >= min_occurrences`, por defecto 2). Frecuente es sinónimo | Usa un criterio que ya existe y está probado. El follow-up #75 cambia el origen de los temas (los `topics` del análisis), pero no el umbral | DEC-06, DEC-07, DEC-08, REC-15 | Yis |
| D-E | ¿Un `logro` positivo y relevante se publica como un `testimonio`? | Sí: R1 aplica a `testimonio` y a `logro` | Con D-C, `logro` es una categoría propia. Si R1 solo acepta `testimonio`, una certificación aprobada se descartaría, y es justo el tipo de historia que busca el reto | CAT-08, DEC-18 | Yis (#69) + Rox |

D-B y D-C quedaron decididas por Rox, y esta versión ya las usa en las secciones A y B. Quedan pendientes D-A, D-D y D-E, que dependen de Yis (#69).

## A. Análisis unificado — Rox-0864 (#68)

Módulo: `src/analysis/unified_analyzer.py` · Prueba: `tests/test_unified_analyzer.py` · **Implementado en el PR #73 (`feat/unified-analyzer` @ `9530f90`, sin merge)**

**Estrategia en dos capas.** (1) Las pruebas unitarias con mocks de Gemini (casos ANL) verifican el contrato del analizador y corren siempre, también en CI. (2) Los casos semánticos (SEN, CAT, REL) requieren un LLM real: se recomienda marcarlos con `@pytest.mark.llm` y ejecutarlos a mano, para no gastar cuota del plan gratuito en cada PR. En todos los casos SEN, CAT y REL el `tipo` de entrada se fija en `otro` para aislar la clasificación del LLM.

### A.1 Sentimiento

Invariante en todos los casos: `score` ∈ [0, 1] y `reasoning` no vacío.

| ID | Entrada | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| SEN-01 | "¡Me contrataron como desarrolladora junior! Gracias a toda la comunidad por el apoyo." | Detecta tono positivo | `positivo` | — | `test_sen_01_…` · ⏳ |
| SEN-02 | "Me encantó el taller de ayer, muy claro y útil para el proyecto." | Detecta tono positivo | `positivo` | — | `test_sen_02_…` · ⏳ |
| SEN-03 | "Llevo tres días con este error y nadie responde. Estoy muy frustrado." | Detecta tono negativo | `negativo` | — | `test_sen_03_…` · ⏳ |
| SEN-04 | "El curso está desorganizado, los enlaces no funcionan y estoy pensando en abandonar." | Detecta tono negativo | `negativo` | Insumo también para el detector de riesgo (D) | `test_sen_04_…` · ⏳ |
| SEN-05 | "El taller de LangGraph es el jueves a las 18:00 en el canal de voz." | Mensaje informativo | `neutral` | — | `test_sen_05_…` · ⏳ |
| SEN-06 | "¿Alguien sabe cómo configurar un router condicional en LangGraph?" | Una pregunta técnica no es positiva ni negativa | `neutral` | Es el sentimiento típico de una duda (ver O-01) | `test_sen_06_…` · ⏳ |
| SEN-07 | "El proyecto quedó bien, pero el proceso fue agotador y casi lo dejo." | Mensaje mixto | Solo se valida la estructura: etiqueta válida, score y reasoning | No se exige una etiqueta concreta | `test_sen_07_…` · ⏳ |
| SEN-08 | "Qué genial, otra vez la plataforma caída justo antes de la entrega." | Sarcasmo | `negativo` | Caso difícil, **no bloqueante** | `test_sen_08_…` · 🟡 |
| SEN-09 | "Finally passed my cloud certification exam! Thanks everyone for the study tips." | Texto en inglés | `positivo` | La muestra de Mastodon está mayoritariamente en inglés | `test_sen_09_…` · ⏳ |
| SEN-10 | "OCI Python SDKを試しましたが、エラーが出て困っています。" | Texto en japonés | Estructura válida y `category` dentro de las 6 categorías | La muestra de Mastodon incluye mensajes en japonés | `test_sen_10_…` · 🟡 |

### A.2 Categorización

| ID | Entrada | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| CAT-01 | "Me sale ModuleNotFoundError al importar langgraph aunque ya reinstalé el paquete. ¿Alguna idea?" | Clasifica como pregunta técnica | `pregunta_tecnica`; `topics` no vacío | — | `test_cat_01_…` · ⏳ |
| CAT-02 | "Me contrataron como analista de datos junior. El proyecto final del bootcamp fue clave en la entrevista." | Clasifica como testimonio | `testimonio` | — | `test_cat_02_…` · ⏳ |
| CAT-03 | "Sugiero agregar más ejemplos prácticos en el módulo de OCI, las diapositivas son muy teóricas." | Clasifica como feedback | `feedback` | — | `test_cat_03_…` · ⏳ |
| CAT-04 | "¿A qué hora empieza la sesión del jueves y dónde se comparte el enlace?" | Pregunta logística, no técnica | `otro` | Si el LLM responde `pregunta_general`, el alias la convierte en `otro` (ANL-19) | `test_cat_04_…` · ⏳ |
| CAT-05 | "Yo creo que LangGraph es mejor que n8n para flujos con reintentos, ¿ustedes qué opinan?" | Clasifica como discusión | `discusion` | — | `test_cat_05_…` · ⏳ |
| CAT-06 | "Buenos días a todos 👋" | Sin contenido clasificable | `otro` | — | `test_cat_06_…` · ⏳ |
| CAT-07 | "Usamos LangChain y Oracle Cloud Infrastructure para el proyecto final." | Extrae entidades | `entities` incluye `LangChain` y `Oracle Cloud Infrastructure` | Verificación semántica, se acepta un superset | `test_cat_07_…` · 🟡 |
| CAT-08 | "¡Aprobé la certificación OCI Foundations! Tres semanas de estudio con los materiales del curso." | Logro personal | `logro` o `testimonio` | 🟡 La frontera entre `logro` y `testimonio` no está definida (O-15, D-E) | `test_cat_08_…` · 🟡 |
| CAT-09 | "Consegui mi primer trabajo como desarrollador. Gracias a la comunidad por todo el apoyo." | Texto sin tildes ni signos de apertura | `testimonio` | La clasificación no debe depender de las tildes (la ingesta ya es insensible a ellas, PR #63) | `test_cat_09_…` · ⏳ |

### A.3 Relevancia

| ID | Entrada | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| REL-01 | "Me contrataron como Dev Jr de IA gracias a mi proyecto con LangChain y OCI. ¡Gracias, comunidad!" | Logro concreto y citable | `score >= 0.6`, `is_marketing_worthy = true` | — | `test_rel_01_…` · ⏳ |
| REL-02 | "Después de ocho meses buscando trabajo entré a una fintech. El portafolio con proyectos reales marcó la diferencia." | Historia de superación con detalle | `score >= 0.6`, `is_marketing_worthy = true` | — | `test_rel_02_…` · ⏳ |
| REL-03 | "Gracias!" | Sin contenido publicable | `score < 0.6`, `is_marketing_worthy = false` | — | `test_rel_03_…` · ⏳ |
| REL-04 | "jajaja sí, yo también" | Conversación trivial | `score < 0.6`, `is_marketing_worthy = false` | — | `test_rel_04_…` · ⏳ |
| REL-05 | "¿Alguien sabe si hay sesión hoy?" | Pregunta logística | `score < 0.6`, `is_marketing_worthy = false` | — | `test_rel_05_…` · ⏳ |

### A.4 Contrato del analizador y casos límite (con mock de Gemini)

Las respuestas simuladas están en el fixture (`casos_analizador_mock`). "Respuesta por defecto" es la definida en la sección 1.

Resultado al 30/9 sobre el PR #73 @ `9530f90`: **20 de 20 casos coinciden** con el código de Rox. 15 tienen test dedicado y 5 los verifiqué con un cliente simulado (ANL-05, 07, 11, 19 y 20); conviene convertirlos en tests en el mismo PR.

| ID | Entrada (respuesta simulada de Gemini) | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| ANL-01 | JSON válido con los 3 dominios | Mapea a `AnalysisComplete` | `message_id` del mensaje; la clave `type` se guarda en `SentimentResult.sentiment` | El LLM no devuelve `message_id`: lo inyecta el analizador | `test_maps_valid_json_to_analysis` · ✅ |
| ANL-02 | El mismo JSON válido | Una sola llamada al LLM por mensaje | El mock se invoca exactamente 1 vez | Es el objetivo de la fusión: menos cuota | `test_single_llm_call_per_message` · ✅ |
| ANL-03 | El JSON envuelto en un bloque de código con marcas de tres comillas invertidas | Extrae el JSON | Mismo resultado que ANL-01: `positivo`, `testimonio`, `is_marketing_worthy = true` | Gemini suele devolver el JSON con esas marcas | `test_parses_fenced_json` · ✅ |
| ANL-04 | Texto libre: "Lo siento, no puedo analizar ese mensaje." | Respuesta por defecto | Respuesta por defecto, sin excepción | — | `test_free_text_returns_default` · ✅ |
| ANL-05 | JSON al que le falta el dominio `relevance` | Conserva los dominios presentes | Sentimiento y categoría intactos; relevancia 0.0, no publicable | — | Verificado por QA, sin test dedicado · ✅ |
| ANL-06 | Falla la red | Respuesta por defecto | Respuesta por defecto; 1 llamada al LLM; la excepción no se propaga | Los clientes de `llm.py` convierten cualquier error en `LLMError`, que el analizador captura. Un cliente propio que lance otra excepción **no** queda cubierto (verificado el 30/9 con `ConnectionError` crudo; O-18) | `test_connection_error_returns_default` · ✅ |
| ANL-07 | Cuota agotada (HTTP 429) | Respuesta por defecto | Respuesta por defecto; 1 llamada al LLM (sin reintentos) | Llega como `LLMError`; el analizador no reintenta | Verificado por QA, sin test dedicado · ✅ |
| ANL-08 | `sentiment.type = "mixto"` | Valor no reconocido | `neutral` | — | `test_unknown_sentiment_falls_back_to_neutral` · ✅ |
| ANL-09 | `category = "comentario_general"` | Fallback de #68 | `otro` | — | `test_comentario_general_maps_to_otro` · ✅ |
| ANL-10 | `category = "spam"` | Valor no reconocido | `otro` | — | `test_spam_maps_to_otro` · ✅ |
| ANL-11 | `category = "pregunta_tecnica"` | Valor canónico (D-C) | `pregunta_tecnica` | En la v1.1 esperaba `duda_tecnica`; se invirtió con D-C | Verificado por QA, sin test dedicado · ✅ |
| ANL-18 | `category = "duda_tecnica"` | Alias | `pregunta_tecnica` | Nuevo en v1.2 | `test_duda_tecnica_aliases_to_pregunta_tecnica` · ✅ |
| ANL-19 | `category = "pregunta_general"` | Alias | `otro` | Nuevo en v1.2 | Verificado por QA, sin test dedicado · ✅ |
| ANL-12 | `relevance.score = 0.60` | Borde inclusivo | `is_marketing_worthy = true` | — | `test_relevance_border_inclusive_and_exclusive` · ✅ |
| ANL-13 | `relevance.score = 0.59` | Borde exclusivo | `is_marketing_worthy = false` | — | `test_relevance_border_inclusive_and_exclusive` · ✅ |
| ANL-14 | `relevance.score = 1.3` y `-0.2` | Score fuera de rango | Se recorta a 1.0 y a 0.0 | — | `test_clamps_out_of_range_scores` · ✅ |
| ANL-15 | `score = 0.9` con `is_marketing_worthy = false` | Campos contradictorios | Manda el score: `is_marketing_worthy = true` | El analizador ignora el campo del LLM y lo deriva del score | `test_marketing_worthy_derives_from_score` · ✅ |
| ANL-16 | Texto vacío `""` o solo espacios | No llama al LLM | Respuesta por defecto; 0 llamadas | Ahorra cuota | `test_empty_text_skips_llm` · ✅ |
| ANL-17 | Lote de 3 mensajes (m1, m2, m3); el segundo falla | Un fallo no aborta el lote | `analyze_batch` devuelve 3 resultados en el orden m1, m2, m3; el 2.º con la respuesta por defecto (`otro`, no publicable) | Rox decidió que el lote lo itera el pipeline (PIP-01); aun así el analizador lo implementa | `test_batch_isolates_failures` · ✅ |
| ANL-20 | `sentiment.score = 0.2` con la etiqueta `positivo` | El score es la confianza, no la polaridad (O-08) | La etiqueta sigue siendo `positivo`; el score se conserva en 0.2 | Evita que un score bajo se lea como "negativo" | Verificado por QA, sin test dedicado · ✅ |

## B. Motor de decisiones — Yis-ai-eng (#69)

Módulo: `src/decisions/engine.py` · Prueba: `tests/test_decisions.py`

> Dueña: Yis, según #69 y la reestructuración del 28/9 (la ficha #48 todavía lista a Rox).

Formato de entrada de la tabla: `category · tipo · sentimiento · relevancia · recurrente`. El motor es determinista y no llama al LLM.

| ID | Entrada | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| DEC-01 | testimonio · testimonio · positivo · 0.85 · no | R1 | `publicar` / `linkedin` | Camino feliz | `test_dec_01_…` · ⏳ |
| DEC-02 | testimonio · testimonio · positivo · 0.60 · no | R1, borde inclusivo | `publicar` / `linkedin` | — | `test_dec_02_…` · ⏳ |
| DEC-03 | testimonio · testimonio · positivo · 0.59 · no | R3, borde exclusivo | `descartar` | — | `test_dec_03_…` · ⏳ |
| DEC-04 | testimonio · testimonio · neutral · 0.90 · no | R3: neutral se descarta aunque sea relevante | `descartar` | Literal en #69 | `test_dec_04_…` · ⏳ |
| DEC-05 | pregunta_tecnica · pregunta_tecnica · neutral · 0.40 · no | R2 se evalúa antes que R3 | `crear_faq` / `faq` | 🟡 Depende de D-A | `test_dec_05_…` · 🟡 |
| DEC-06 | pregunta_tecnica · pregunta_tecnica · neutral · 0.70 · sí | R2 | `crear_faq` / `faq` | — | `test_dec_06_…` · ⏳ |
| DEC-07 | otro · otro · neutral · 0.50 · sí | La recurrencia por sí sola no genera FAQ si no es pregunta técnica | `descartar` | 🟡 Depende de D-A y D-D | `test_dec_07_…` · 🟡 |
| DEC-08 | otro · otro · neutral · 0.50 · no | R3 | `descartar` | — | `test_dec_08_…` · ⏳ |
| DEC-09 | feedback · feedback · negativo · 0.80 · no | Ninguna regla aplica | `descartar` con `reason` "sin regla aplicable" | 🟡 Hueco: negativo y relevante. Candidato a alerta (O-03) | `test_dec_09_…` · 🟡 |
| DEC-10 | feedback · feedback · positivo · 0.75 · no | Ninguna regla aplica (R1 es solo para testimonios) | `descartar` con `reason` "sin regla aplicable" | 🟡 El generador de newsletter salió del MVP (S3-002), así que descartar es coherente; ver O-14 | `test_dec_10_…` · 🟡 |
| DEC-11 | discusion · discusion · neutral · 0.20 · no | R3 | `descartar` | — | `test_dec_11_…` · ⏳ |
| DEC-12 | testimonio · pregunta_tecnica · positivo · 0.90 · no | Prevalece el `tipo` explícito y reconocido (D-B) | `crear_faq` / `faq` | La acción está decidida; mencionar la discrepancia en `reason` es una propuesta | `test_dec_12_…` · ⏳ |
| DEC-13 | testimonio · otro · positivo · 0.85 · no | `otro` se trata como "sin tipo": manda `category` | `publicar` / `linkedin` | Decidido por Rox (D-B) | `test_dec_13_…` · ⏳ |
| DEC-14 | Análisis incompleto (`category`, sentimiento o relevancia nulos) | Defensivo | `descartar`, `reason` "análisis incompleto"; no lanza excepción | 🟡 | `test_dec_14_…` · 🟡 |
| DEC-15 | Lote vacío | — | Lista vacía | Sin datos en el fixture | `test_dec_15_…` · ⏳ |
| DEC-16 | La misma entrada dos veces | Determinismo, sin llamadas al LLM | Misma decisión; 0 llamadas al LLM | Sin datos en el fixture | `test_dec_16_…` · ⏳ |
| DEC-17 | Cualquier decisión | Formato de salida | Objeto `DecisionResult` con `message_id`, `action`, `asset_type` (nulo si se descarta) y `reason` no vacío | ✅ El modelo ya existe en la rama de Rox con esos campos. Falta el motor | `test_dec_17_…` · ⏳ |
| DEC-18 | logro · otro · positivo · 0.80 · no | R1 aplicada a `logro` | `publicar` / `linkedin` | 🟡 Depende de D-E | `test_dec_18_…` · 🟡 |
| DEC-19 | testimonio · (vacío) · positivo · 0.85 · no | `tipo` vacío: manda `category` | `publicar` / `linkedin` | Decidido por Rox (D-B) | `test_dec_19_…` · ⏳ |
| DEC-20 | testimonio · comentario_general · positivo · 0.85 · no | `comentario_general` se trata como "sin tipo": manda `category` | `publicar` / `linkedin` | Es el `tipo` que la ingesta de Mastodon emitía para casi todos los mensajes | `test_dec_20_…` · ⏳ |
| DEC-21 | otro · testimonio · positivo · 0.90 · no | El `tipo` explícito y reconocido prevalece sobre el análisis | `publicar` / `linkedin` | Consecuencia de la regla: si la ingesta etiqueta mal un `tipo`, el error llega al motor (O-16) | `test_dec_21_…` · ⏳ |

## C. Dudas recurrentes — Yis-ai-eng (HU-S2-007, PR #64 mergeado; follow-up #75)

Módulo: `src/decisions/recurring_topics.py` · Prueba: `tests/test_recurring_topics.py` (10 tests en `main`)

Resultados reales: los casos se re-ejecutaron el 30/9 sobre `main` @ `096125b` y sobre la rama de seguimiento `feat/recurring-topics` @ `c8fb3d1`, con `min_occurrences=2`. Ambas dan el mismo resultado que el 28/9: el método para elegir el tema no cambió. Ninguna diferencia incumple los criterios de la ficha tal como están escritos (contar, 2+ ocurrencias, ejemplos, título de FAQ); son limitaciones que afectarán la calidad del FAQ con datos reales.

**Convención de tema.** Un tema es un sustantivo del dominio (`docker`, `contraseña`). Las palabras funcionales (stopwords) no son temas, y por eso REC-09 espera `[]` aunque "how" aparezca 3 veces: el umbral de 2 se aplica a temas, no a palabras sueltas. El léxico vive hoy en el código del detector. El follow-up #75 lo reemplaza por los `topics` del análisis unificado; REC-15 anticipa ese cambio y REC-01, 03, 07, 08 y 09 se re-evalúan entonces.

| ID | Entrada | Comportamiento esperado | Resultado esperado | Observado en el código actual | Prueba · estado |
|---|---|---|---|---|---|
| REC-01 | "No recuerdo mi contraseña" · "Olvidé la contraseña de mi cuenta" · "¿Cómo reseteo la contraseña?" | Agrupa mensajes del mismo tema | 1 tema `contraseña`, count 3 | `[]`: cada mensaje toma como tema su **primera** palabra significativa (`recuerdo`, `olvidé`, `reseteo`) | `test_rec_01_…` · ⚠️ |
| REC-02 | "¿Cómo instalo Docker en Windows?" | Un tema con 1 ocurrencia no se reporta | `[]` | `[]` | cubierto por `test_ignores_topics_with_one_occurrence` · ✅ |
| REC-03 | "Error con docker al iniciar" · "docker no arranca" · "docker falla siempre" · "Error de git al hacer push" · "git rechaza mi push" | Ordena por frecuencia | `docker` (3), `git` (2) | `error` (2), `docker` (2): agrupa dos mensajes no relacionados por "error" y subcuenta docker | `test_rec_03_…` · ⚠️ |
| REC-04 | Lista vacía | — | `[]` | `[]` | cubierto por `test_returns_empty_for_empty_message_list` · ✅ |
| REC-05 | "¿Cómo puedo hacer esto?" · "Quiero ayuda para esto" | Solo stopwords: no hay tema | `[]` | `[]` | cubierto por `test_returns_empty_for_stopwords_only_message` · ✅ |
| REC-06 | "Docker no inicia" · "DOCKER da error" · "docker se cierra" | Insensible a mayúsculas | `docker` (3) | `docker` (3) | `test_rec_06_…` · ✅ |
| REC-07 | "Olvidé mi contraseña" · "Olvidé mi clave" · "Perdí la contraseña" | El tema es un sustantivo del dominio | `contraseña` (2) | `olvidé` (2): título "Preguntas frecuentes sobre olvidé" | `test_rec_07_…` · ⚠️ |
| REC-08 | "¿Cómo recupero mi cuenta?" · "No puedo entrar a mi cuenta" · "Mi cuenta fue bloqueada" | Agrupa por el mismo tema | `cuenta` (3) | `cuenta` (2): el primer mensaje quedó como `recupero` | `test_rec_08_…` · ⚠️ |
| REC-09 | "How do I install python packages?" · "How can I use pip with venv?" · "How to run python tests?" | Tres preguntas distintas: no hay tema | `[]` | `how` (3): falso positivo; las stopwords son solo en español | `test_rec_09_…` · ⚠️ |
| REC-10 | "docker falla" · "docker lento" | `min_occurrences` configurable | 2 → `docker` (2); 3 → `[]` | Coincide | cubierto por `test_minimum_occurrences_can_be_configured` · ✅ |
| REC-11 | `min_occurrences=1` | Valor inválido | `ValueError` | `ValueError` | cubierto por `test_rejects_min_occurrences_below_two` · ✅ |
| REC-12 | "¿Cómo puedo cambiar mi contraseña?" · "¿Dónde puedo cambiar la contraseña?" | Estructura de la salida | Objeto `RecurringTopic` con atributos `topic`, `count`, `examples` y `faq_title`; título "Preguntas frecuentes sobre contraseña"; 2 ejemplos | Coincide | cubierto por `test_suggests_faq_title` y `test_includes_message_examples` · ✅ |
| REC-13 | Un `dict` o `None` dentro de la lista | Falla rápido con un error claro | `TypeError` | `AttributeError` (no valida el tipo). 🟡 El comportamiento es una propuesta; Yis decide | `test_rec_13_…` · ⚠️ |
| REC-14 | "docker falla" · "docker lento" · "git falla" · "git lento" | Con empate, orden estable | `docker` (2), `git` (2) | Coincide (orden de inserción) | `test_rec_14_…` · ✅ |
| REC-15 | Topics por mensaje: `[docker]`, `[docker, error]`, `[git]` | Tras el #75, el detector consume los `topics` del análisis | 1 tema `docker` con count 2 | 🟡 Depende del follow-up #75 (aún no implementado) | `test_rec_15_…` · 🟡 |

## D. Miembros en riesgo — Elias-J-Guardado (HU-S2-006)

Módulo: `src/decisions/member_risk.py` · Prueba: `tests/test_member_risk.py`

> ⏸️ **Fuera de alcance del MVP.** HU-S2-006 se quitó en la reestructuración del 28/9 ("si hay tiempo"): no la pide el jurado ni forma parte del contrato de salida. Los casos se conservan por si se retoma; no bloquean nada.

La ficha pide historial de sentimiento por miembro, tendencia negativa en mensajes recientes, niveles bajo/medio/alto y razones, pero no define umbrales. Por eso los umbrales de abajo son una propuesta.

Umbrales propuestos (configurables): ventana de los **últimos 5 mensajes** del miembro; negativos en la ventana: 0–1 sin alerta, 2 **bajo**, 3 **medio**, 4 o más **alto**. Los mensajes neutrales no cuentan como negativos.

Formato de entrada: historial de sentimiento, del más antiguo al más reciente.

| ID | Entrada (historial) | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| RSK-01 | Historial vacío | No hay datos | Sin alerta | No lanza excepción | `test_rsk_01_…` · ⏸️ |
| RSK-02 | positivo, neutral, positivo, negativo, positivo | 1 negativo no es recurrente | Sin alerta | — | `test_rsk_02_…` · ⏸️ |
| RSK-03 | positivo, negativo, neutral, negativo, positivo | 2 negativos en la ventana | Alerta **bajo** | — | `test_rsk_03_…` · ⏸️ |
| RSK-04 | negativo, positivo, negativo, neutral, negativo | 3 negativos no consecutivos | Alerta **medio** | — | `test_rsk_04_…` · ⏸️ |
| RSK-05 | negativo, negativo, positivo, negativo, negativo | 4 negativos | Alerta **alto**; las razones mencionan 4 de los últimos 5 | — | `test_rsk_05_…` · ⏸️ |
| RSK-06 | neutral ×4, negativo | Los neutrales no cuentan | Sin alerta | — | `test_rsk_06_…` · ⏸️ |
| RSK-07 | negativo ×3, positivo ×2 | Mejora reciente | Alerta **medio**: una mejora reciente no baja el nivel | Propuesta; Elias decide | `test_rsk_07_…` · ⏸️ |
| RSK-08 | Miembro A: negativo ×3; miembro B: positivo, positivo, neutral | Historiales independientes | Solo A recibe alerta (medio) | — | `test_rsk_08_…` · ⏸️ |
| RSK-09 | Tres negativos de "Andrés Molina", "andrés molina " y "ANDRÉS MOLINA" | El mismo miembro tras normalizar | 1 miembro, alerta medio | Se normalizan espacios y mayúsculas | `test_rsk_09_…` · ⏸️ |
| RSK-10 | Tres negativos con autor vacío o solo espacios | Sin miembro identificable | Sin alerta, sin excepción | — | `test_rsk_10_…` · ⏸️ |
| RSK-11 | Dos eventos del mismo miembro: negativo a las 12:00 llega antes que positivo a las 10:00 | Ordena por `timestamp`; sin `timestamp`, por orden de llegada | Historial ordenado: [positivo, negativo] | `timestamp` es opcional en el contrato. Con 2 eventos el nivel no cambia; ver RSK-14 | `test_rsk_11_…` · ⏸️ |
| RSK-12 | Cualquier alerta | Formato de salida | Miembro, `nivel` ∈ {bajo, medio, alto} y `reasons` no vacío | Sin datos en el fixture | `test_rsk_12_…` · ⏸️ |
| RSK-13 | Siete mensajes: negativo ×4 y luego positivo ×3 | Solo cuenta la ventana de los últimos 5 | Ventana [negativo, negativo, positivo, positivo, positivo]: alerta **bajo** | Sin la ventana serían 4 negativos (alto) | `test_rsk_13_…` · ⏸️ |
| RSK-14 | Seis eventos del mismo miembro, con `timestamp`, que llegan del más nuevo al más antiguo: negativo ×3 (15:00, 14:00, 13:00) y positivo ×3 (12:00, 11:00, 10:00) | El orden por `timestamp` cambia el nivel | Por `timestamp`: ventana [pos, pos, neg, neg, neg] = alerta **medio**. Por orden de llegada sería **bajo** | Es el caso que distingue ordenar por `timestamp` de ordenar por llegada | `test_rsk_14_…` · ⏸️ |

## E. Prompts y configuración — emanuelperacchia (HU-S2-008)

Módulo: `src/prompts/templates.py` · Prueba: `tests/test_prompts.py`. Fuera del alcance obligatorio de #48, pero el analizador (A) depende del contrato del prompt.

| ID | Entrada | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| PRM-01 | Plantilla del prompt unificado | Pide un JSON con los 3 dominios | Menciona `sentiment`, `categorization` y `relevance`, y pide solo JSON | — | `test_prm_01_…` · ⏳ |
| PRM-02 | Plantilla del prompt unificado | Enumera los valores válidos | Lista las 6 categorías exactas y los 3 valores de sentimiento | Deben coincidir con la sección 1 | `test_prm_02_…` · ⏳ |
| PRM-03 | Mensaje que contiene llaves y comillas (por ejemplo `{"a": 1}` o un `dict` de Python) | El texto del usuario se inserta sin romper el formato | El prompt se construye sin `KeyError` ni `ValueError` | Riesgo típico de `str.format` en una comunidad técnica que pega código | `test_prm_03_…` · 🟡 |

## F. Pipeline y cobertura cruzada — Rox-0864 (HU-S3-005) y QA (ficha #53)

Pedida por Elias: la matriz cubre análisis y decisiones; esta sección indica dónde se prueba el resto. Los casos PIP se verificaron el 30/9 sobre el PR #73 (pipeline conectado al analizador). El motor de decisiones del pipeline todavía es un stub que enruta por `tipo`.

| ID | Entrada | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| PIP-01 | Lote de 3 mensajes; el analizador falla en el 2.º (ver ANL-17) | El pipeline itera el lote y no aborta | `total_interacciones_procesadas = 3` | Rox decidió que el lote lo itera el pipeline | `test_pip_01_…` · ⏳ |
| PIP-02 | 4 análisis: positivo, positivo, negativo, neutral; topics `[empleo, portafolio]`, `[empleo]`, `[error]`, `[]` | Resume la comunidad | 4 interacciones; `sentimiento_predominante = positivo`; `temas_principales = [empleo, error, portafolio]` | Los temas son la unión ordenada alfabéticamente de **todos** los topics, sin ranking ni límite (O-17) | `test_pip_02_…` · ✅ |
| PIP-03 | 2 análisis: positivo y negativo | Empate de sentimientos | `sentimiento_predominante = positivo` | 🟡 Desempate por primera aparición; es lo que hace el código, no está decidido | `test_pip_03_…` · 🟡 |
| PIP-04 | Lote vacío | Resumen vacío | 0 interacciones; `neutral`; sin temas | — | `test_pip_04_…` · ✅ |
| PIP-05 | `data/sample/demo_fixed.json` (PR #77): 12 interacciones | 3 ejemplos de transformación (requisito R6 del jurado) | Mariana Souza (testimonio) → `publicar` / `linkedin`; Lucas Albuquerque (pregunta técnica) → `crear_faq` / `faq`; Pedro Núñez (otro) → `descartar`. Salida con 12 interacciones, `post_linkedin` y `sugerencia_contenido_faq` no nulos | El contrato tiene **un solo** `post_linkedin` y **una sola** FAQ por salida: los 3 ejemplos son 3 transformaciones distintas, no 3 posts a la vez. El archivo se referencia y no se copia aquí | `test_pip_05_…` · ✅ con el stub |

**Cobertura fuera de esta matriz**

| Área | Dónde se prueba | Estado |
|---|---|---|
| Ingesta (loader, normalizador, clasificación por palabras clave, paginación y reintentos 429) | `tests/test_input_loader.py`, `test_normalizer.py`, `test_classification.py` y `test_ingest_robustez.py`, en `main` | ✅ Existen |
| Resumen de la comunidad (`resumen_comunidad`) | PIP-02 a PIP-04 y la ficha #53 (HU-S3-007) | ⏳ |
| Salida completa (`OutputBatch`) | `tests/test_contract.py` en `main` y la ficha #53 | ✅ Parcial |
| Almacenamiento OCI | `tests/test_oci_integration.py` (PR #76) y la ficha #54 (HU-S4-007) | ⏳ |
| Interfaz Streamlit | `tests/test_interface_app.py` (en `main`, PR #74) y la ficha #54 | ✅ Parcial |
| Prompts | Sección E (PRM-01 a PRM-03) | ⏳ |

## Observaciones y decisiones pendientes

| # | Observación | Impacto | A quién |
|---|---|---|---|
| O-01 | **Orden de reglas.** R3 ("neutral → descartar") absorbe casi todas las dudas técnicas, porque el sentimiento típico de una pregunta es neutral. Pasa a la decisión D-A | Alto | Yis (#69) |
| O-02 | "Duda técnica / pregunta frecuente": ¿toda duda técnica genera FAQ, o solo las recurrentes? Pasa a las decisiones D-A y D-D | Alto | Yis / Rox |
| O-03 | Huecos en las reglas: negativo con alta relevancia, feedback positivo y newsletter no tienen regla. Propuesta: `descartar` con `reason` "sin regla aplicable" y valorar una alerta para el caso negativo | Medio | Yis |
| O-04 | ✅ Resuelto en el PR #73: `DecisionResult` (`message_id`, `action`, `asset_type`, `reason`) y la firma `decide(List[AnalysisComplete]) -> List[DecisionResult]`. Falta el motor | — | — |
| O-05 | ✅ Decidido por Rox (D-B). Pendiente de datos: la muestra de `main` (100 mensajes: 81 `otro`, 19 `pregunta_tecnica`) no tiene ningún testimonio; el dataset de demo con testimonios (PR #77) aún no está en `main` | Medio | Rox / Elias |
| O-06 | ✅ Resuelto con D-C: el analizador usa el vocabulario de `InteractionType` y mapea los alias. Aparte: el normalizador de entrada no convierte un `tipo` desconocido en `otro` (`xyz` se conserva) | Bajo | Rox |
| O-07 | ✅ Resuelto: Rox decidió que el lote lo itera el pipeline (PIP-01), y además `analyze_batch` existe en el PR #73 y pasa ANL-17 | — | — |
| O-08 | ✅ Resuelto: `sentiment.score` es la confianza de la etiqueta, no la polaridad (docstring del analizador) | — | — |
| O-09 | Detector de dudas: el tema sigue siendo la primera palabra significativa del mensaje (REC-01, 03, 07, 08; confirmado el 30/9 sobre `main`). Rox abrió el follow-up #75 para usar los `topics` del análisis; la convención de tema está en la sección C. Además las stopwords son solo en español (REC-09) y el detector recibe `list[str]`, no `AnalysisComplete` | Medio | Yis |
| O-10 | ✅ Resuelto: HU-S2-006 salió del MVP el 28/9; la sección D queda fuera de alcance | — | — |
| O-11 | ✅ Resuelto: Ema corrigió el milestone de #69 a Sprint 2 (sesión del 29/9) | — | — |
| O-12 | ✅ Resuelto: la reestructuración confirma a Yis como dueña del motor de decisiones. Solo falta actualizar la ficha #48 | Bajo | Ema |
| O-13 | ✅ Resuelto: la respuesta por defecto se implementó tal como se propuso en la v1 | — | — |
| O-14 | El generador de newsletter (S3-002) salió del MVP, pero `destaque_newsletter_semanal` sigue en el contrato de salida del PDF. Hay que decidir si se entrega `null` o una plantilla simple | Bajo | Rox / Ema |
| O-15 | Frontera entre `logro` y `testimonio` sin definir. Con D-C ambas son categorías, pero R1 solo publica testimonios: una certificación o un proyecto terminado clasificado como `logro` se descartaría. Pasa a D-E | Alto | Yis / Rox |
| O-16 | Con la regla de precedencia (D-B), un `tipo` explícito y reconocido gana sobre el análisis. En Mastodon el `tipo` lo asigna el clasificador por palabras clave de la ingesta (19 de 100 mensajes de la muestra de `main` salen como `pregunta_tecnica`; en una muestra anterior Rosa encontró anuncios de empleo etiquetados así). Un error de la ingesta llega al motor sin que el LLM pueda corregirlo; DEC-21 lo ilustra. El dataset de demo está etiquetado a mano, así que no afecta a la demo | Medio | Rox / Elias |
| O-17 | `temas_principales` es la unión ordenada alfabéticamente de **todos** los topics, sin ranking ni límite, y `sentimiento_predominante` se emite en minúsculas (`positivo`), mientras el ejemplo del PDF muestra una frase ("Altamente Positivo") y una lista corta de temas. Con 100 mensajes la lista puede ser muy larga. Decidir si se limita a los N temas más frecuentes (PIP-02) | Bajo | Rox |
| O-18 | El analizador promete "nunca lanza", pero solo captura `LLMError`: un cliente que lance otra excepción la propaga (verificado el 30/9 con `ConnectionError` crudo). Los clientes de `llm.py` ya envuelven todo en `LLMError`, así que en producción no ocurre. Sugerencia: capturar `Exception` en `analyze` | Bajo | Rox |

## Trazabilidad con los criterios de #48

| Criterio de aceptación | Dónde se cumple |
|---|---|
| Se crea `docs/pruebas/analisis-decisiones.md` | Este documento |
| Casos positivos, negativos y neutrales para sentimiento | A.1 (positivos: SEN-01, 02, 09; negativos: SEN-03, 04, 08; neutrales: SEN-05, 06) |
| Las seis categorías esperadas | A.2 (CAT-01 a CAT-09). Tras D-C, las seis categorías son las del enum `InteractionType`; los nombres de la ficha #48 (`duda_tecnica`, `pregunta_general`) quedan como alias |
| Casos de relevancia alta y baja | A.3 (REL-01 a REL-05) y A.4 (ANL-12 a ANL-15, verificados contra el código) |
| Reglas del motor de decisiones | Sección 1 y B (R1–R3, DEC-01 a DEC-21) |
| Escenarios del detector de miembros en riesgo | D (RSK-01 a RSK-14), documentados aunque la ficha quedó fuera del MVP |
| Escenarios del detector de dudas recurrentes | C (REC-01 a REC-15) |
| Dónde se prueban `resumen_comunidad`, OCI y la ingesta (review de Elias) | Sección F |
| Fixture aislado si es necesario | `tests/fixtures/analysis-decisiones.json`, justificado por cubrir los 4 módulos con datos compartidos y sin duplicar `data/sample/` ni `tests/test_contract.py` |
| No se modifica código de análisis, decisiones ni prompts | Cumplido: este PR solo agrega documentación y un fixture |

## Cómo usar y mantener esta matriz

1. **Nombres de tests.** Cada test lleva el ID del caso: `test_dec_05_duda_neutral_crea_faq`. Así cualquiera ubica el caso en este documento y en el fixture.
2. **Cada dueño valida solo su sección** y comenta en el PR. Los cambios de criterio se hacen por PR sobre este archivo.
3. **Al implementar un módulo:** correr `pytest tests/test_<modulo>.py -v`, actualizar la última columna (⏳ → ✅ o ⚠️) y abrir una observación con pasos para reproducir cada diferencia.
4. **Uso del fixture** en pytest:

```python
import json
import pathlib

import pytest

FX = json.loads(
    pathlib.Path("tests/fixtures/analysis-decisiones.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("caso", FX["casos_decision"]["casos"], ids=lambda c: c["id"])
def test_decisiones(caso):
    ...
```

5. **Alias del fixture.** En `casos_analizador_mock`, un valor que empieza con `@` es una referencia a otra clave de la misma sección, y el test debe sustituirlo antes de usar el caso:
   - `@respuesta_valida` → el objeto `respuesta_valida`.
   - `@respuesta_por_defecto` → el objeto `respuesta_por_defecto`; `@relevancia_por_defecto` → su campo `relevance`.
   - Si el alias está dentro de un texto (ANL-03), se sustituye por el JSON serializado de esa clave.
   - `{"excepcion": "…"}` significa que el mock lanza esa excepción en lugar de devolver texto (ANL-06, ANL-07).
   - Los campos descriptivos, como `lote` en ANL-17, se implementan a mano en el test.

```python
def resolver(valor, seccion):
    """Sustituye un alias '@clave' por el valor de esa clave en la sección."""
    if isinstance(valor, str) and valor.startswith("@"):
        return seccion[valor[1:]]
    return valor
```

6. **Los casos 🟡** pasan a ✅ (o se corrigen) cuando el dueño confirma el criterio; hasta entonces no deben bloquear un PR. Los casos ⏸️ no se ejecutan mientras su ficha esté fuera del MVP.
7. **`skip` y `xfail` según el estado.** Al convertir un caso en test, su estado en el fixture decide la marca: `ESPECIFICADO` corre normal, `PROPUESTO` va con `xfail` (no bloquea el CI y avisa cuando el criterio se confirme) y `FUERA_DE_ALCANCE` con `skip`.

```python
def marca_por_estado(caso):
    if caso["estado"] == "PROPUESTO":
        return pytest.mark.xfail(strict=False, reason="criterio PROPUESTO: pendiente de confirmación")
    if caso["estado"] == "FUERA_DE_ALCANCE":
        return pytest.mark.skip(reason="ficha fuera del MVP")
    return ()


CASOS = [
    pytest.param(c, id=c["id"], marks=marca_por_estado(c))
    for c in FX["casos_decision"]["casos"]
]
```

## Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| v1 | 28/9 | Primera versión, construida sobre las fichas #68 y #69 |
| v1.1 | 29/9 | Alineada con la reestructuración del 28/9: sección D fuera de alcance, `comentario_general` → `otro` y dueña del motor de decisiones confirmada. Atiende la review de Ema: redacción "casos especificados", documentación de los alias del fixture y nueva sección de decisiones pendientes D-A a D-D. Sección C re-ejecutada sobre `021b586` |
| v1.2 | 30/9 | Incorpora el analizador de Rox (`feat/unified-analyzer`): 18 de 19 casos ANL verificados. D-C decidida en código, así que las secciones A y B usan el vocabulario de `InteractionType`, con los alias ANL-18 y ANL-19. Nuevos CAT-08, DEC-18, D-E y O-15 (frontera `logro`/`testimonio`). Resueltas O-06, O-08, O-11 y O-13; O-04 a medias. Sección C re-ejecutada sobre `main` tras el merge del PR #64 |
| v1.3 | 30/9 | Incorpora las decisiones de Rox (D-B: precedencia entre `tipo` y `category`) y la review de Elias y Ema. El PR #73 pasa de 18 a 20 casos ANL verificados (ANL-17 con `analyze_batch`, nuevo ANL-20). Nuevos CAT-09, DEC-19 a DEC-21, RSK-13 y RSK-14, REC-15 y la sección F (pipeline y cobertura cruzada, PIP-01 a PIP-05). Esperados medibles en ANL-03, ANL-06, ANL-07, ANL-17, RSK-07, RSK-11 y REC-13; convención de tema en la sección C; marcas `skip`/`xfail` por estado. Nuevas O-16, O-17 y O-18; resueltas O-04, O-05 y O-07 |
