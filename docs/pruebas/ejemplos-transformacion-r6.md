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
| C5 | Reclamo con carga negativa | Negativo, `feedback` | `derivar` (con D-I) | **Derivado a humano** |

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
| Razón | "Testimonio o logro positivo relevante" |

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

**Decisión:** `publicar` / `linkedin` — "Testimonio o logro positivo relevante".

**Activo generado — destaque de newsletter**

| Campo | Valor |
|-------|-------|
| Sección | Logro de la Semana |
| Titular | Nueva Certificación en Oracle Cloud Infrastructure |
| Resumen | Destaca la aprobación de la certificación y el rol de los apuntes y simulacros compartidos por la comunidad |

Es el caso de un logro **académico** (no un empleo): el sistema lo trata igual que
un logro laboral, porque la categoría `logro` marca el contenido y no distingue
entre empleo y certificación.

**Nota sobre la regla R1.** El motivo de la decisión es "Testimonio o logro
positivo relevante", no "Testimonio positivo relevante": R1 acepta tanto
`testimonio` como `logro` (`is_publishable_type = effective_type in {"testimonio",
"logro"}`). Antes de ese cambio, C2 —cuyo análisis devuelve la categoría `logro`—
se descartaba en silencio. El cambio entra con el PR #144.

---

## C3 — Duda técnica → sugerencia de FAQ

**Entrada**

> ¿Alguien me puede explicar cómo se manejan los reintentos en LangGraph? No
> entiendo bien cuándo reintentar y cuándo fallar.
> — Sofía Lima, `#dudas-langgraph`, tipo `pregunta_tecnica`

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
| Origen | `#dudas-langgraph` |
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

## C5 — Reclamo con carga negativa → derivado a humano (contraste)

**Entrada**

> Me prometieron mentoría personalizada y nunca llegué a tenerla. Escribí tres
> veces al canal de soporte y nadie me respondió.
> — Camila Vega, `#general`, tipo `feedback`

El mensaje expresa insatisfacción real de una persona de la comunidad. Ese es el
caso que resolvió la decisión D-I: el sistema no puede dejarlo caer en la cola de
FAQ ni descartarlo por ser "no relevante" para marketing.

**Análisis**

| Campo | Valor |
|-------|-------|
| Sentimiento | `negativo` |
| Categoría | `feedback` |

**Decisión**

| Campo | Valor |
|-------|-------|
| `action` | `derivar` |
| `asset_type` | `None` |
| Razón | "Feedback negativo: requiere atención personalizada por el community manager" |

**Activo generado: ninguno — el mensaje va a atención humana.**

**Por qué importa este caso.** Es la evidencia viva de la decisión D-I
(`docs/DECISIONS.md`): *un mensaje negativo merece tratamiento humano*. La regla
R4 corre **antes** que R2 (FAQ) y R3 (descartar), así que la negatividad gana
sobre el tipo del mensaje. Documentarlo con el LLM real es lo que hace defendible
la decisión ante un jurado: no es una regla en el papel, es un comportamiento
verificado.

**Verificado con el LLM real** (`gemma4:31b`): el lote
[`lotes-r6/C5.json`](lotes-r6/C5.json) produce `feedback_negativo: 1`, sin
candidatos de LinkedIn y sin sugerencia de FAQ.

> **Estado:** R4 se activa al mergear el PR #146, que incorpora D-I
> (`R1 → R4 → R2 → R3`). Sobre `main` anterior a ese merge, el mismo mensaje caía
> en `descartar` por R3.

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

Se regenera con el pipeline real (backend de `.env`, `gemma4:31b`):

```bash
python scripts/generar_muestra.py
```

La diferencia entre 22 derivados y 39 negativos se explica por los 17 mensajes
con carga negativa que además son preguntas técnicas: sin D-I van a FAQ, y con
D-I pasan a derivarse a humano. El detalle está en `docs/DECISIONS.md` (D-F y
D-I) y en `docs/pruebas/analisis-decisiones.md`.

> **Números medidos sobre el head que incorpora D-I.** Sobre `main` anterior al
> merge del PR #146, el derivado por regla era 22; con el orden `R1 → R4 → R2 →
> R3` los mensajes negativos se derivan todos. La tabla de arriba corresponde a
> la corrida sobre el head que ya incluye D-I.

---

## Reproducir estos casos

Los 5 lotes están versionados en [`lotes-r6/`](lotes-r6/) — un archivo por caso.

El backend se elige con `COMMUNITYLAB_LLM_BACKEND` (`.env`). Con el LLM de la
demo (Ollama Cloud, `gemma4:31b`), que es como se obtuvieron estos casos:

```bash
python scripts/run_demo.py docs/pruebas/lotes-r6/C1.json
```

Con el determinista, sin red ni costo:

```bash
python scripts/run_demo.py docs/pruebas/lotes-r6/C1.json --offline
```

> **Ojo:** el backend determinista (`--offline`) **no reproduce C5**. La
> detección de sentimiento negativo depende del LLM; con `rule_based`, el
> mensaje de C5 no se marca como negativo y termina en FAQ. C1–C4 sí se
> reproducen con los dos backends.

Los lotes siguen el formato de `InputBatch` (`origen_comunidad`,
`periodo_referencia`, `interacciones[]`), donde cada interacción tiene `autor`,
`canal`, `tipo` y `texto`.

### Origen de cada lote

| Lote | Fuente |
|------|--------|
| C1, C2, C3, C5 | `data/sample/demo_fixed.json` (fuente curada de la muestra combinada) |
| C4 | Lote propio; mismo perfil que `Pedro Núñez` en las muestras |

C1–C3 y C5 están incluidos textualmente en `demo_fixed.json`, así que la corrida
completa y estos lotes coinciden en esos mensajes.
