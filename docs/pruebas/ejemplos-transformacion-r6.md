# Ejemplos de transformación — R6 (entrada → activo)

**Requisito:** R6 del jurado — "mínimo 3 ejemplos de transformación".
**Fecha:** 2026-10-19 · **Base revisada:** `main` @ `37d7e9c`
**Backend del LLM:** Ollama Cloud, `gemma4:31b` (`COMMUNITYLAB_LLM_BACKEND=ollama`)
**Autoría:** corrida de Rox-0864; documento de itanflores (QA)

Este documento muestra **5 casos reales** de entrada → análisis → activo, obtenidos
corriendo el pipeline con el LLM de la demo (no con el backend determinista).

Tres casos cubren las transformaciones que pide el jurado (testimonio, logro y
duda). Los otros dos muestran **el límite del sistema**: entradas que no deben
generar activos. Un jurado que ve solo casos que funcionan no sabe si el sistema
distingue o si publica cualquier cosa; los casos de contraste lo demuestran.

## Cómo se obtuvieron

Cada caso es un lote real enviado por el pipeline completo (`_run_with_batch`),
con el análisis y las decisiones reales. El pipeline se puede correr por archivo
con el mismo camino:

```bash
PYTHONPATH=. ./venv/bin/python scripts/run_demo.py <lote.json>
```

Los lotes de estos casos incluyen, además del mensaje en foco, los mensajes
necesarios para que el resultado sea el del sistema en uso. El newsletter, por
diseño, se arma con el **primer testimonio publicable del lote**; un lote de un
solo mensaje técnico lo haría caer sobre ese mensaje y confundiría la lectura.
Los lotes de este documento evitan ese artefacto.

## Resumen

| Caso | Entrada | Análisis | Decisión | Activo |
|------|---------|----------|----------|--------|
| C1 | Testimonio de empleo | Positivo, `logro`, relevante (1.0) | `publicar` / LinkedIn | Post de LinkedIn |
| C2 | Logro (certificación) | Positivo, `logro`, relevante (1.0) | `publicar` / LinkedIn | Destaque de newsletter |
| C3 | Duda técnica | Neutro, `pregunta_tecnica`, no relevante (0.3) | `crear_faq` / FAQ | Sugerencia de FAQ |
| C4 | Feedback organizativo | Neutro, `feedback`, no relevante (0.4) | `descartar` | **Ninguno** (por diseño) |
| C5 | Pregunta con carga negativa | Negativo, `pregunta_tecnica` | `derivar` (con D-I) | **Derivado a humano** |

C1, C2 y C3 son las transformaciones de R6. C4 y C5 son los contrastes.

---

## C1 — Testimonio de empleo → post de LinkedIn

**Entrada**

> Comunidad, quedé seleccionada para el puesto de Desarrolladora Junior de IA! El
> proyecto del curso de LangChain y OCI que construí en mi portfolio marcó toda la
> diferencia en la entrevista técnica. Muy agradecida con la comunidad por todo el
> apoyo!
> — Mariana Souza, `#logros-y-empleos`, tipo `testimonio`

**Análisis**

| Campo | Valor |
|-------|-------|
| Sentimiento | `positivo` (score 1.0) |
| Categoría | `logro` |
| `is_marketing_worthy` | `True` (relevancia 1.0) |
| Temas | empleo, ia, portfolio |

**Decisión**

| Campo | Valor |
|-------|-------|
| `action` | `publicar` |
| `asset_type` | `linkedin` |
| Razón | "Testimonio positivo relevante" |

**Activo generado — post de LinkedIn**

| Campo | Valor |
|-------|-------|
| Título | Logro Profesional: Nueva Desarrolladora Junior de IA |
| Canal recomendado | LinkedIn Oficial |
| Potencial de engagement | Alto |

El copy sigue la estructura de un post profesional: gancho, historia, enseñanza y
llamado a la acción. Fragmento literal:

> ¿Cuál es la clave para destacar en una entrevista técnica hoy en día?
>
> Mariana Souza acaba de alcanzar un hito increíble: fue seleccionada como
> Desarrolladora Junior de IA. Pero lo más interesante es cómo lo logró... el
> proyecto de LangChain y OCI que construyó para su portfolio fue el factor
> determinante...
>
> #InteligenciaArtificial #LangChain #PrimerEmpleo #DesarrolloSoftware #TechCareer

El mismo lote produce también el **destaque de newsletter** ("Logro de la
Semana"), porque el newsletter se arma con el primer testimonio publicable.

---

## C2 — Logro (certificación) → destaque de newsletter

**Entrada**

> Acabo de aprobar la certificación Oracle Cloud Infrastructure Foundations. Los
> apuntes y los simulacros que compartieron acá me salvaron.
> — Ana Rodríguez, `#logros-y-empleos`, tipo `testimonio`

**Análisis**

| Campo | Valor |
|-------|-------|
| Sentimiento | `positivo` (score 1.0) |
| Categoría | `logro` |
| `is_marketing_worthy` | `True` |
| Temas | certificación, estudio |

**Decisión:** `publicar` / `linkedin` — "Testimonio positivo relevante".

**Activo generado — destaque de newsletter**

| Campo | Valor |
|-------|-------|
| Sección | Logro de la Semana |
| Titular | Nueva Certificación en Oracle Cloud Infrastructure |
| Resumen | Destaca la aprobación de la certificación y el rol de los apuntes y simulacros compartidos por la comunidad |

Es el caso de un logro **académico** (no un empleo): el sistema lo trata igual que
un logro laboral, porque la categoría `logro` marca el contenido y no distingue
entre empleo y certificación.

---

## C3 — Duda técnica → sugerencia de FAQ

**Entrada**

> ¿Alguien me puede explicar cómo se manejan los reintentos en LangGraph? No
> entiendo bien cuándo reintentar y cuándo fallar.
> — Sofía Lima, `#ayuda`, tipo `pregunta_tecnica`

**Análisis**

| Campo | Valor |
|-------|-------|
| Sentimiento | `neutro` (score 0.9) |
| Categoría | `pregunta_tecnica` |
| `is_marketing_worthy` | `False` (relevancia 0.3) |
| Temas | manejo de error, reintento |

**Decisión**

| Campo | Valor |
|-------|-------|
| `action` | `crear_faq` |
| `asset_type` | `faq` |
| Razón | "Duda técnica o pregunta frecuente" |

**Activo generado — sugerencia de FAQ**

| Campo | Valor |
|-------|-------|
| Tema | Manejo de reintentos en LangGraph |
| Origen | `#ayuda` |
| Estado | `derivado_a_mentoria` |

El activo FAQ es una **sugerencia**, no la FAQ final: el sistema propone el tema
para que un curador escriba la respuesta. Es intencional — la FAQ publicada
requiere criterio humano.

---

## C4 — Feedback organizativo → sin activo (contraste)

**Entrada**

> La comunidad necesita un taller presencial de OCI. Hay voluntarios dispuestos a
> coordinar el espacio.
> — Pedro Núñez, `#general`, tipo `feedback`

**Análisis**

| Campo | Valor |
|-------|-------|
| Sentimiento | `neutro` (score 0.9) |
| Categoría | `feedback` |
| `is_marketing_worthy` | `False` (relevancia 0.4) |

**Decisión**

| Campo | Valor |
|-------|-------|
| `action` | `descartar` |
| `asset_type` | `None` |
| Razón | "Mensaje neutral o no relevante" |

**Activo generado: ninguno.**

**Por qué importa este caso.** Es un pedido legítimo y útil para la comunidad,
pero no es material de marketing ni una duda técnica: es una propuesta
organizativa. El sistema lo descarta **a propósito** y no inventa un activo.

Un mensaje descartado aparece en el resumen como parte del lote, pero **no genera
ningún activo**. Que el pipeline se niegue a generar es tan importante como que
genere: sin este caso, no hay evidencia de que discrimine.

---

## C5 — Pregunta con carga negativa → derivado a humano (contraste)

**Entrada**

> Estoy frustrado, nada de lo que pruebo funciona. ¿Cómo configuro el SDK de OCI?
> Ya seguí la guía y no me reconoce la API key.
> — Miguel Torres, `#ayuda`, tipo `pregunta_tecnica`

Este mensaje es a la vez **una duda técnica** y **una expresión de frustración**.
Ese cruce es justo el que resolvió la decisión D-I.

**Análisis**

| Campo | Valor |
|-------|-------|
| Sentimiento | `negativo` |
| Categoría | `pregunta_tecnica` |

**Decisión — depende del orden de reglas**

| Versión | `action` | Razón |
|---------|----------|-------|
| `main` actual (R1→R2→R4→R3) | `crear_faq` | La regla de FAQ corre antes que la de derivar |
| Con D-I — PR #146 (R1→**R4**→R2→R3) | `derivar` | "Feedback negativo: requiere atención personalizada por el community manager" |

**Activo generado: ninguno — el mensaje va a atención humana.**

**Por qué importa este caso.** Es la evidencia viva de la decisión D-I
(`docs/DECISIONS.md`): *una duda con carga negativa merece tratamiento humano, no
FAQ*. Documentarlo con el LLM real es lo que hace defendible la decisión ante un
jurado: no es una regla en el papel, es un comportamiento verificado.

> **Estado:** el comportamiento derivado se activa al mergear el PR #146, que
> incorpora D-I. En `main` actual, este mensaje todavía genera una sugerencia de
> FAQ. Este caso debe citarse junto con el merge de #146.

---

## Contraste con la muestra completa

Los 5 casos son lotes chicos y controlados. La corrida completa de la demo (232
interacciones, `data/sample/corrida-completa-gemma.json`) confirma que el
comportamiento escala:

| Métrica | Valor |
|---------|-------|
| Interacciones procesadas | 232 |
| Sentimiento negativo (mensajes) | 39 |
| Derivados a humano | 22 |
| Preguntas frecuentes detectadas | 78 |
| Candidatos a post de LinkedIn | 32 |
| Sugerencia de FAQ materializada | 1 |

La diferencia entre 22 derivados y 39 negativos se explica por los 17 mensajes
con carga negativa que además son preguntas técnicas: en `main` van a FAQ, y con
D-I pasan a derivarse a humano. El detalle está en `docs/DECISIONS.md` (D-F y
D-I) y en `docs/pruebas/analisis-decisiones.md`.

---

## Reproducir estos casos

El backend se elige con `COMMUNITYLAB_LLM_BACKEND` (`.env`). Para el
determinista, sin red ni costo:

```bash
python scripts/run_demo.py mi_lote.json --offline
```

Los lotes de estos 5 casos siguen el formato de `InputBatch`
(`origen_comunidad`, `periodo_referencia`, `interacciones[]`), donde cada
interacción tiene `autor`, `canal`, `tipo` y `texto`.
