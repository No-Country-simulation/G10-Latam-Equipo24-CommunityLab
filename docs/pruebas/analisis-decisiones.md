# Matriz de pruebas — Análisis y decisiones (Sprint 2)

**Issue:** HU-S2-009 (#48) · **Versión:** v1 (borrador para validación de los dueños)
**Fecha:** 2026-09-28 · **Autor:** itanflores (QA)
**Base revisada:** `main` @ `5b5228c`; detector de dudas recurrentes en `feat/recurring-topics` @ `6a3dfcd` (PR #64, sin merge)
**Fixture asociado:** `tests/fixtures/analysis-decisiones.json` (78 casos con datos; los IDs coinciden con este documento)

Este documento es una **matriz de comportamiento**, no una implementación: describe qué debe hacer cada módulo, con qué entrada y qué resultado se espera. No modifica código de análisis, decisiones ni prompts.

## Cómo leer esta matriz

| Marca | Significado |
|---|---|
| ✅ | Verificado contra código real y coincide con lo esperado |
| ⚠️ | Verificado contra código real y **difiere** de lo esperado (ver columna de observado) |
| ⏳ | Especificado por las fichas; pendiente de implementación |
| 🟡 | **PROPUESTO**: la ficha no define este criterio; el dueño del módulo debe confirmarlo o corregirlo |

Estado del código al 28/9: solo existe `RecurringTopicsDetector` (en rama, sin merge). `src/analysis/unified_analyzer.py`, `src/decisions/engine.py`, `src/decisions/member_risk.py` y `src/prompts/templates.py` aún no existen. Por eso solo la sección C tiene resultados reales; el resto queda como especificación y se completará cuando cada módulo se implemente.

## Índice y propietarios

| Sección | Módulo | Propietario | Ficha | Archivo de prueba |
|---|---|---|---|---|
| A | Análisis unificado (sentimiento, categoría, relevancia) | Rox-0864 | #68 (HU-S2-001 fusionada) | `tests/test_unified_analyzer.py` |
| B | Motor de decisiones | Yis-ai-eng (reasignado desde Rox-0864) | #69 (HU-S2-005) | `tests/test_decisions.py` |
| C | Detector de dudas recurrentes | Yis-ai-eng | HU-S2-007 (PR #64) | `tests/test_recurring_topics.py` |
| D | Detector de miembros en riesgo | Elias-J-Guardado | HU-S2-006 | `tests/test_member_risk.py` |
| E | Prompts y configuración | emanuelperacchia | HU-S2-008 | `tests/test_prompts.py` |

## 1. Convenciones

**Definido por las fichas (#68, #69):**

| Elemento | Valor |
|---|---|
| Sentimiento | `positivo`, `negativo`, `neutral`; `score` en [0, 1]; `reasoning` |
| Categorías de análisis (6) | `duda_tecnica`, `testimonio`, `feedback`, `pregunta_general`, `discusion`, `otro` |
| Relevancia | `score` en [0, 1]; `is_marketing_worthy` es verdadero si `score >= 0.6` |
| Fallback de categoría | `comentario_general` y cualquier valor no reconocido se mapean a `otro` |
| Regla R1 | Testimonio positivo con relevancia ≥ 0.6 → `action="publicar"`, `asset_type="linkedin"` |
| Regla R2 | Duda técnica / pregunta frecuente → `action="crear_faq"`, `asset_type="faq"` |
| Regla R3 | Mensaje neutral o de relevancia < 0.6 → `action="descartar"` |

**🟡 Propuesto (ver observaciones O-01 a O-06):**

| Tema | Propuesta |
|---|---|
| Orden de reglas | Se evalúan en orden R1 → R2 → R3; gana la primera que aplica |
| Categoría de análisis vs `tipo` del contrato | Son campos distintos: `tipo` es la señal de entrada, `category` es la salida del análisis. Mapeo: `duda_tecnica`↔`pregunta_tecnica`; `testimonio`↔`testimonio`/`logro`; `feedback`↔`feedback`; `discusion`↔`discusion`; `otro`↔`otro`/`comentario_general`; `pregunta_general` no tiene `tipo` equivalente |
| Precedencia entre `tipo` y `category` | Prevalece el `tipo` explícito (decisión D-02), salvo `otro` y `comentario_general` (que #68 trata como `otro`): se consideran "sin tipo" y manda `category` |
| Respuesta por defecto del analizador | sentimiento `neutral`/0.5, categoría `otro`, sin topics ni entities, relevancia 0.0 y no publicable |

## A. Análisis unificado — Rox-0864 (#68)

Módulo: `src/analysis/unified_analyzer.py` · Prueba: `tests/test_unified_analyzer.py`

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
| SEN-09 | "Finally passed my cloud certification exam! Thanks everyone for the study tips." | Texto en inglés | `positivo` | Unos 32 de 39 mensajes de la muestra de Mastodon están en inglés (conteo aproximado) | `test_sen_09_…` · ⏳ |
| SEN-10 | "OCI Python SDKを試しましたが、エラーが出て困っています。" | Texto en japonés | Estructura válida y `category` dentro de las 6 categorías | La muestra de Mastodon incluye mensajes en japonés | `test_sen_10_…` · 🟡 |

### A.2 Categorización

| ID | Entrada | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| CAT-01 | "Me sale ModuleNotFoundError al importar langgraph aunque ya reinstalé el paquete. ¿Alguna idea?" | Clasifica como duda técnica | `duda_tecnica`; `topics` no vacío | — | `test_cat_01_…` · ⏳ |
| CAT-02 | "Me contrataron como analista de datos junior. El proyecto final del bootcamp fue clave en la entrevista." | Clasifica como testimonio | `testimonio` | — | `test_cat_02_…` · ⏳ |
| CAT-03 | "Sugiero agregar más ejemplos prácticos en el módulo de OCI, las diapositivas son muy teóricas." | Clasifica como feedback | `feedback` | — | `test_cat_03_…` · ⏳ |
| CAT-04 | "¿A qué hora empieza la sesión del jueves y dónde se comparte el enlace?" | Clasifica como pregunta general | `pregunta_general` | Sin `tipo` equivalente en el contrato (O-06) | `test_cat_04_…` · ⏳ |
| CAT-05 | "Yo creo que LangGraph es mejor que n8n para flujos con reintentos, ¿ustedes qué opinan?" | Clasifica como discusión | `discusion` | — | `test_cat_05_…` · ⏳ |
| CAT-06 | "Buenos días a todos 👋" | Sin contenido clasificable | `otro` | — | `test_cat_06_…` · ⏳ |
| CAT-07 | "Usamos LangChain y Oracle Cloud Infrastructure para el proyecto final." | Extrae entidades | `entities` incluye `LangChain` y `Oracle Cloud Infrastructure` | Verificación semántica, se acepta un superset | `test_cat_07_…` · 🟡 |

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

| ID | Entrada (respuesta simulada de Gemini) | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| ANL-01 | JSON válido con los 3 dominios | Mapea a `AnalysisComplete` | `message_id` del mensaje; la clave `type` se guarda en `SentimentResult.sentiment` | El LLM no devuelve `message_id`: lo inyecta el analizador | `test_anl_01_…` · ⏳ |
| ANL-02 | El mismo JSON válido | Una sola llamada al LLM por mensaje | El mock se invoca exactamente 1 vez | Es el objetivo de la fusión: menos cuota | `test_anl_02_…` · ⏳ |
| ANL-03 | El JSON envuelto en un bloque de código con marcas de tres comillas invertidas | Extrae el JSON | Igual resultado que ANL-01 | Gemini suele devolver el JSON con esas marcas | `test_anl_03_…` · 🟡 |
| ANL-04 | Texto libre: "Lo siento, no puedo analizar ese mensaje." | Respuesta por defecto | Respuesta por defecto, sin excepción | — | `test_anl_04_…` · ⏳ |
| ANL-05 | JSON al que le falta el dominio `relevance` | Conserva los dominios presentes | Sentimiento y categoría intactos; relevancia por defecto | — | `test_anl_05_…` · 🟡 |
| ANL-06 | El mock lanza `ConnectionError` | Respuesta por defecto | Respuesta por defecto, sin propagar la excepción | Fallo de red (#68) | `test_anl_06_…` · ⏳ |
| ANL-07 | El mock simula cuota agotada (HTTP 429) | Respuesta por defecto | Respuesta por defecto, sin reintentos infinitos | Fallo de cuota (#68) | `test_anl_07_…` · ⏳ |
| ANL-08 | `sentiment.type = "mixto"` | Valor no reconocido | `neutral` | — | `test_anl_08_…` · 🟡 |
| ANL-09 | `category = "comentario_general"` | Fallback de #68 | `otro` | — | `test_anl_09_…` · ⏳ |
| ANL-10 | `category = "spam"` | Valor no reconocido | `otro` | — | `test_anl_10_…` · ⏳ |
| ANL-11 | `category = "pregunta_tecnica"` (valor del contrato) | Alias de la categoría de análisis | `duda_tecnica` | Sin alias, sería "no reconocido" y caería en `otro` (O-06) | `test_anl_11_…` · 🟡 |
| ANL-12 | `relevance.score = 0.60` | Borde inclusivo | `is_marketing_worthy = true` | — | `test_anl_12_…` · ⏳ |
| ANL-13 | `relevance.score = 0.59` | Borde exclusivo | `is_marketing_worthy = false` | — | `test_anl_13_…` · ⏳ |
| ANL-14 | `relevance.score = 1.3` y `-0.2` | Score fuera de rango | Se recorta a 1.0 y a 0.0 | — | `test_anl_14_…` · 🟡 |
| ANL-15 | `score = 0.9` con `is_marketing_worthy = false` | Campos contradictorios | Manda el score: `is_marketing_worthy = true` | Dos campos redundantes pueden contradecirse | `test_anl_15_…` · 🟡 |
| ANL-16 | Texto vacío `""` o solo espacios | No llama al LLM | Respuesta por defecto; 0 llamadas | Ahorra cuota | `test_anl_16_…` · 🟡 |
| ANL-17 | Lote de 3 mensajes; el segundo provoca `ConnectionError` | Un fallo no aborta el lote | 3 resultados en el mismo orden; el 2.º por defecto | `analyze_batch` estaba en la ficha S2-004 y no aparece en #68 (O-07) | `test_anl_17_…` · 🟡 |

## B. Motor de decisiones — Yis-ai-eng (#69)

Módulo: `src/decisions/engine.py` · Prueba: `tests/test_decisions.py`

> La ficha #48 lista a Rox como dueña del motor de decisiones; #69 lo reasignó a Yis. Esta matriz sigue a #69 (O-12).

Formato de entrada de la tabla: `category · tipo · sentimiento · relevancia · recurrente`. El motor es determinista y no llama al LLM.

| ID | Entrada | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| DEC-01 | testimonio · testimonio · positivo · 0.85 · no | R1 | `publicar` / `linkedin` | Camino feliz | `test_dec_01_…` · ⏳ |
| DEC-02 | testimonio · testimonio · positivo · 0.60 · no | R1, borde inclusivo | `publicar` / `linkedin` | — | `test_dec_02_…` · ⏳ |
| DEC-03 | testimonio · testimonio · positivo · 0.59 · no | R3, borde exclusivo | `descartar` | — | `test_dec_03_…` · ⏳ |
| DEC-04 | testimonio · testimonio · neutral · 0.90 · no | R3: neutral se descarta aunque sea relevante | `descartar` | Literal en #69 | `test_dec_04_…` · ⏳ |
| DEC-05 | duda_tecnica · pregunta_tecnica · neutral · 0.40 · no | R2 se evalúa antes que R3 | `crear_faq` / `faq` | 🟡 Sin orden de reglas, R3 descarta casi toda duda, porque su sentimiento típico es neutral (O-01). Además "duda técnica / pregunta frecuente" se lee como "o" (O-02) | `test_dec_05_…` · 🟡 |
| DEC-06 | duda_tecnica · pregunta_tecnica · neutral · 0.70 · sí | R2 | `crear_faq` / `faq` | — | `test_dec_06_…` · ⏳ |
| DEC-07 | pregunta_general · otro · neutral · 0.50 · sí | R2 por "pregunta frecuente" | `crear_faq` / `faq` | 🟡 | `test_dec_07_…` · 🟡 |
| DEC-08 | pregunta_general · otro · neutral · 0.50 · no | R3 | `descartar` | 🟡 | `test_dec_08_…` · 🟡 |
| DEC-09 | feedback · feedback · negativo · 0.80 · no | Ninguna regla aplica | `descartar` con `reason` "sin regla aplicable" | 🟡 Hueco: negativo y relevante. Candidato a alerta (O-03) | `test_dec_09_…` · 🟡 |
| DEC-10 | feedback · feedback · positivo · 0.75 · no | Ninguna regla aplica (R1 es solo para testimonios) | `descartar` con `reason` "sin regla aplicable" | 🟡 No hay criterio de newsletter (O-03) | `test_dec_10_…` · 🟡 |
| DEC-11 | discusion · discusion · neutral · 0.20 · no | R3 | `descartar` | — | `test_dec_11_…` · ⏳ |
| DEC-12 | testimonio · pregunta_tecnica · positivo · 0.90 · no | Prevalece el `tipo` explícito (D-02) | `crear_faq` / `faq`; `reason` menciona la discrepancia | 🟡 | `test_dec_12_…` · 🟡 |
| DEC-13 | testimonio · comentario_general · positivo · 0.85 · no | `comentario_general` y `otro` se tratan como "sin tipo": manda `category` | `publicar` / `linkedin` | 🟡 En la muestra de Mastodon 37 de 39 mensajes llevan `tipo = comentario_general` (O-05) | `test_dec_13_…` · 🟡 |
| DEC-14 | Análisis incompleto (`category`, sentimiento o relevancia nulos) | Defensivo | `descartar`, `reason` "análisis incompleto"; no lanza excepción | 🟡 | `test_dec_14_…` · 🟡 |
| DEC-15 | Lote vacío | — | Lista vacía | Sin datos en el fixture | `test_dec_15_…` · ⏳ |
| DEC-16 | La misma entrada dos veces | Determinismo, sin llamadas al LLM | Misma decisión; 0 llamadas al LLM | Sin datos en el fixture | `test_dec_16_…` · ⏳ |
| DEC-17 | Cualquier decisión | Formato de salida | `action`, `asset_type` y `reason` (no vacío), conforme a `DecisionResult` | `DecisionResult` **no existe** aún en `src/domain/models.py` (O-04) | `test_dec_17_…` · 🟡 |

## C. Dudas recurrentes — Yis-ai-eng (HU-S2-007, PR #64)

Módulo: `src/decisions/recurring_topics.py` · Prueba: `tests/test_recurring_topics.py` (existen 6 tests en la rama)

Esta es la única sección con resultados reales: los casos se ejecutaron contra `RecurringTopicsDetector` (rama `feat/recurring-topics` @ `6a3dfcd`, `min_occurrences=2`). Ninguna diferencia incumple los criterios de la ficha tal como están escritos (contar, 2+ ocurrencias, ejemplos, título de FAQ); son limitaciones del método que afectarán la calidad del FAQ con datos reales.

| ID | Entrada | Comportamiento esperado | Resultado esperado | Observado en el código actual | Prueba · estado |
|---|---|---|---|---|---|
| REC-01 | "No recuerdo mi contraseña" · "Olvidé la contraseña de mi cuenta" · "¿Cómo reseteo la contraseña?" | Agrupa mensajes del mismo tema | 1 tema `contraseña`, count 3 | `[]`: cada mensaje toma como tema su **primera** palabra significativa (`recuerdo`, `olvidé`, `reseteo`) | `test_rec_01_…` · ⚠️ |
| REC-02 | "¿Cómo instalo Docker en Windows?" | Un tema con 1 ocurrencia no se reporta | `[]` | `[]` | existe `test_ignores_topics_with_one_occurrence` · ✅ |
| REC-03 | "Error con docker al iniciar" · "docker no arranca" · "docker falla siempre" · "Error de git al hacer push" · "git rechaza mi push" | Ordena por frecuencia | `docker` (3), `git` (2) | `error` (2), `docker` (2): agrupa dos mensajes no relacionados por "error" y subcuenta docker | `test_rec_03_…` · ⚠️ |
| REC-04 | Lista vacía | — | `[]` | `[]` | `test_rec_04_…` · ✅ |
| REC-05 | "¿Cómo puedo hacer esto?" · "Quiero ayuda para esto" | Solo stopwords: no hay tema | `[]` | `[]` | `test_rec_05_…` · ✅ |
| REC-06 | "Docker no inicia" · "DOCKER da error" · "docker se cierra" | Insensible a mayúsculas | `docker` (3) | `docker` (3) | `test_rec_06_…` · ✅ |
| REC-07 | "Olvidé mi contraseña" · "Olvidé mi clave" · "Perdí la contraseña" | El tema es un sustantivo del dominio | `contraseña` (2) | `olvidé` (2): título "Preguntas frecuentes sobre olvidé" | `test_rec_07_…` · ⚠️ |
| REC-08 | "¿Cómo recupero mi cuenta?" · "No puedo entrar a mi cuenta" · "Mi cuenta fue bloqueada" | Agrupa por el mismo tema | `cuenta` (3) | `cuenta` (2): el primer mensaje quedó como `recupero` | `test_rec_08_…` · ⚠️ |
| REC-09 | "How do I install python packages?" · "How can I use pip with venv?" · "How to run python tests?" | Tres preguntas distintas: no hay tema | `[]` | `how` (3): falso positivo; las stopwords son solo en español | `test_rec_09_…` · ⚠️ |
| REC-10 | "docker falla" · "docker lento" | `min_occurrences` configurable | 2 → `docker` (2); 3 → `[]` | Coincide | existe `test_minimum_occurrences_can_be_configured` · ✅ |
| REC-11 | `min_occurrences=1` | Valor inválido | `ValueError` | `ValueError` | `test_rec_11_…` · ✅ |
| REC-12 | "¿Cómo puedo cambiar mi contraseña?" · "¿Dónde puedo cambiar la contraseña?" | Estructura de la salida | Llaves `topic`, `count`, `examples`, `faq_title`; título "Preguntas frecuentes sobre contraseña"; 2 ejemplos | Coincide | existen `test_suggests_faq_title` y `test_includes_message_examples` · ✅ |
| REC-13 | Un `dict` o `None` dentro de la lista | Error claro o entrada ignorada | `TypeError`/`ValueError`, o se ignora | `AttributeError` (no valida el tipo) | `test_rec_13_…` · ⚠️ |
| REC-14 | "docker falla" · "docker lento" · "git falla" · "git lento" | Con empate, orden estable | `docker` (2), `git` (2) | Coincide (orden de inserción) | `test_rec_14_…` · ✅ |

## D. Miembros en riesgo — Elias-J-Guardado (HU-S2-006)

Módulo: `src/decisions/member_risk.py` · Prueba: `tests/test_member_risk.py`

La ficha pide historial de sentimiento por miembro, tendencia negativa en mensajes recientes, niveles bajo/medio/alto y razones, **pero no define umbrales**. Todo lo de esta sección es 🟡 PROPUESTO. El módulo no tiene código y la tarjeta no aparece en la columna Todo del tablero (28/9): confirmar si sigue en el sprint.

Umbrales propuestos (configurables): ventana de los **últimos 5 mensajes** del miembro; negativos en la ventana: 0–1 sin alerta, 2 **bajo**, 3 **medio**, 4 o más **alto**. Los mensajes neutrales no cuentan como negativos.

Formato de entrada: historial de sentimiento, del más antiguo al más reciente.

| ID | Entrada (historial) | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| RSK-01 | Historial vacío | No hay datos | Sin alerta | No lanza excepción | `test_rsk_01_…` · 🟡 |
| RSK-02 | positivo, neutral, positivo, negativo, positivo | 1 negativo no es recurrente | Sin alerta | — | `test_rsk_02_…` · 🟡 |
| RSK-03 | positivo, negativo, neutral, negativo, positivo | 2 negativos en la ventana | Alerta **bajo** | — | `test_rsk_03_…` · 🟡 |
| RSK-04 | negativo, positivo, negativo, neutral, negativo | 3 negativos no consecutivos | Alerta **medio** | — | `test_rsk_04_…` · 🟡 |
| RSK-05 | negativo, negativo, positivo, negativo, negativo | 4 negativos | Alerta **alto**; las razones mencionan 4 de los últimos 5 | — | `test_rsk_05_…` · 🟡 |
| RSK-06 | neutral ×4, negativo | Los neutrales no cuentan | Sin alerta | — | `test_rsk_06_…` · 🟡 |
| RSK-07 | negativo ×3, positivo ×2 | Mejora reciente | Nivel máximo **medio** | Elias define si una mejora baja el nivel | `test_rsk_07_…` · 🟡 |
| RSK-08 | Miembro A: negativo ×3; miembro B: positivo, positivo, neutral | Historiales independientes | Solo A recibe alerta (medio) | — | `test_rsk_08_…` · 🟡 |
| RSK-09 | Tres negativos de "Andrés Molina", "andrés molina " y "ANDRÉS MOLINA" | El mismo miembro tras normalizar | 1 miembro, alerta medio | Se normalizan espacios y mayúsculas | `test_rsk_09_…` · 🟡 |
| RSK-10 | Tres negativos con autor vacío o solo espacios | Sin miembro identificable | Sin alerta, sin excepción | — | `test_rsk_10_…` · 🟡 |
| RSK-11 | Dos eventos del mismo miembro con `timestamp` en desorden | Usa el `timestamp` para ordenar; sin `timestamp`, el orden de llegada | Se ordena por `timestamp` | `timestamp` es opcional en el contrato de entrada | `test_rsk_11_…` · 🟡 |
| RSK-12 | Cualquier alerta | Formato de salida | Miembro, `nivel` ∈ {bajo, medio, alto} y `reasons` no vacío | Sin datos en el fixture | `test_rsk_12_…` · 🟡 |

## E. Prompts y configuración — emanuelperacchia (HU-S2-008)

Módulo: `src/prompts/templates.py` · Prueba: `tests/test_prompts.py`. Fuera del alcance obligatorio de #48, pero el analizador (A) depende del contrato del prompt.

| ID | Entrada | Comportamiento esperado | Resultado esperado | Caso de error / nota | Prueba · estado |
|---|---|---|---|---|---|
| PRM-01 | Plantilla del prompt unificado | Pide un JSON con los 3 dominios | Menciona `sentiment`, `categorization` y `relevance`, y pide solo JSON | — | `test_prm_01_…` · ⏳ |
| PRM-02 | Plantilla del prompt unificado | Enumera los valores válidos | Lista las 6 categorías exactas y los 3 valores de sentimiento | Deben coincidir con la sección 1 | `test_prm_02_…` · ⏳ |
| PRM-03 | Mensaje que contiene llaves y comillas (por ejemplo `{"a": 1}` o un `dict` de Python) | El texto del usuario se inserta sin romper el formato | El prompt se construye sin `KeyError` ni `ValueError` | Riesgo típico de `str.format` en una comunidad técnica que pega código | `test_prm_03_…` · 🟡 |

## Observaciones y decisiones pendientes

| # | Observación | Impacto | A quién |
|---|---|---|---|
| O-01 | **Orden de reglas.** R3 ("neutral → descartar") absorbe casi todas las dudas técnicas, porque el sentimiento típico de una pregunta es neutral. Sin un orden explícito (R1 → R2 → R3), el camino FAQ no se activa nunca | Alto | Yis (#69) |
| O-02 | "Duda técnica / pregunta frecuente": ¿toda duda técnica genera FAQ, o solo las recurrentes? El ejemplo del PDF genera una sugerencia de FAQ desde una sola duda, lo que apoya la lectura "o" | Alto | Yis / Rox |
| O-03 | Huecos en las reglas: negativo con alta relevancia, feedback positivo y newsletter no tienen regla. Propuesta: `descartar` con `reason` "sin regla aplicable" y valorar una alerta para el caso negativo | Medio | Yis |
| O-04 | `DecisionResult` no existe en `src/domain/models.py`, y `DecisionEngine.decide()` en `interfaces.py` recibe `List[InputMessage]` y devuelve `List[Dict]`, mientras #69 habla de análisis unificados y de `DecisionResult`. Hay que definir modelo y firma antes de implementar | Alto | Rox (dominio) / Yis |
| O-05 | Precedencia entre `tipo` y `category` (D-02). En la muestra de Mastodon 37 de 39 mensajes llevan `tipo = comentario_general`, y el normalizador lo conserva tal cual (no lo convierte en `otro`). Si ese `tipo` prevaleciera sobre la categoría del análisis, ningún testimonio real llegaría a LinkedIn | Alto | Rox |
| O-06 | Las 6 categorías de análisis no coinciden con el enum `InteractionType` (`pregunta_tecnica`, `logro`…). #68 manda a `otro` todo valor no reconocido, así que un `pregunta_tecnica` devuelto por el LLM caería en `otro`. Hace falta definir el alias. El normalizador tampoco convierte un `tipo` desconocido en `otro` (`xyz` se conserva) | Medio | Rox |
| O-07 | `analyze_batch(messages)` estaba en la ficha S2-004 original y no aparece en #68. ¿Quién procesa lotes? | Medio | Rox |
| O-08 | Semántica de `sentiment.score` sin definir: ¿confianza de la etiqueta o polaridad? Afecta a cualquier umbral que la use | Medio | Rox |
| O-09 | Detector de dudas: el tema es la primera palabra significativa del mensaje (REC-01, 03, 07, 08). Como #68 ya devuelve `topics`, el detector podría usarlos en vez de reinventar la extracción. Además las stopwords son solo en español (REC-09) y el detector recibe `list[str]`, no `AnalysisComplete` | Medio | Yis |
| O-10 | HU-S2-006 (riesgo de miembros): sin código, sin umbrales y sin tarjeta visible en Todo | Medio | Elias / Ema |
| O-11 | #69 tiene el milestone "Sprint 4" (vence 17/10), pero sus fechas son 28/9–4/10 y está en la ruta crítica | Medio | Ema |
| O-12 | #48 lista a Rox como dueña del motor de decisiones; #69 lo reasignó a Yis | Bajo | Ema |
| O-13 | Respuesta por defecto del analizador sin valores definidos (se propone la de la sección 1) | Bajo | Rox |

## Trazabilidad con los criterios de #48

| Criterio de aceptación | Dónde se cumple |
|---|---|
| Se crea `docs/pruebas/analisis-decisiones.md` | Este documento |
| Casos positivos, negativos y neutrales para sentimiento | A.1 (positivos: SEN-01, 02, 09; negativos: SEN-03, 04, 08; neutrales: SEN-05, 06) |
| Las seis categorías esperadas | A.2 (CAT-01 a CAT-06) |
| Casos de relevancia alta y baja | A.3 (REL-01 a REL-05) y A.4 (ANL-12 a ANL-15) |
| Reglas del motor de decisiones | Sección 1 y B (R1–R3, DEC-01 a DEC-17) |
| Escenarios del detector de miembros en riesgo | D (RSK-01 a RSK-12) |
| Escenarios del detector de dudas recurrentes | C (REC-01 a REC-14) |
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

5. **Los casos 🟡** pasan a ✅ (o se corrigen) cuando el dueño confirma el criterio; hasta entonces no deben bloquear un PR.
