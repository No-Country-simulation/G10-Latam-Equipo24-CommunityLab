# Decisiones de contrato — CommunityLab

> **Objetivo:** dejar claras las 5 decisiones del contrato (D-A a D-E), cuáles resuelve el ejemplo del PDF, y qué hay que decidir en equipo considerando que **la muestra actual de datos de Mastodon es pobre en señales** y **el detector de temas recurrentes es muy exigente**.

## 1. La realidad de los datos (esto condiciona todo)

Verifiqué qué produce cada fuente hoy:

| Fuente | Mensajes | `tipo` presentes |
|---|---|---|
| **Muestra Mastodon actual** (`data/sample/mastodon_interacciones.json`) | 100 | `otro` (81), `pregunta_tecnica` (19), **0 `testimonio`** |
| **Demo sintético** (`data/sample/demo_fixed.json`) | 12 | `testimonio` (6), `pregunta_tecnica` (4), `otro` (2) |
| **Ingesta** (`src/ingest/ingest.py` → `calificar_tipo`) | — | solo `testimonio`, `pregunta_tecnica`, `otro` |
| **Analizador LLM** (`src/analysis/unified_analyzer.py`) | — | las 6: `testimonio`, `pregunta_tecnica`, `feedback`, `logro`, `discusion`, `otro` |

**Dos conclusiones duras:**

1. **`logro`, `feedback` y `discusion` NO existen como `tipo`.** Solo pueden salir del `category` que clasifica el LLM. La ingesta por keywords jamás los produce.
2. **La muestra actual no tiene testimonios.** El valor del sistema ("publicar historias de éxito") depende de que el analizador clasifique bien los logros/testimonios — no de Mastodon.

---

## 2. Las 5 decisiones

### D-A — ¿Toda duda técnica genera FAQ, o solo las recurrentes?

**Qué decide:** si R2 ("pregunta técnica → `crear_faq`") dispara con *toda* duda, o solo con las que se repiten.

**Estado:** 🟡 pendiente (Yis).

**¿En el PDF?** **SÍ, y sin ambigüedad.** El ejemplo genera `sugerencia_contenido_faq` a partir de **una sola** pregunta (Lucas, LangGraph). El batch tiene 2 mensajes y solo 1 es pregunta.

**Factor datos sintéticos:** si gateamos R2 detrás del detector (que exige `count >= 2`), **la pregunta de Lucas no generaría FAQ nunca**, porque una sola duda no es "recurrente". Con la muestra actual (19 preguntas de 100, todas distintas), tampoco.

**Recomendación:** **Toda duda técnica genera `crear_faq`.** Es la única forma de cumplir el requisito de la FAQ del PDF. El orden R1 → R2 → R3 es parte de la misma decisión (R2 debe ir antes que R3, o las preguntas neutrales se descartan).

---

### D-B — ¿Qué prevalece cuando `tipo` y `category` difieren?

**Qué decide:** cuando la ingesta dice un `tipo` y el LLM dice otra `category`, cuál manda.

**Estado:** ✅ **resuelta** (Rox, 29/9). El `tipo` explícito y reconocido prevalece; si es `otro`/`comentario_general`/vacío, manda la `category`.

**¿En el PDF?** **Parcial.** El PDF no muestra un caso de conflicto explícito, pero es defensivo.

**Factor datos sintéticos:** en la muestra actual el `tipo` es casi siempre `otro` (81 de 100), así que **la rama "manda la category" es la que se ejecuta siempre en producción**. La rama "manda el tipo" solo se ejercita con el demo sintético (donde `tipo = testimonio` está puesto a mano).

**Recomendación:** **Mantenerla como está.** Es de bajo riesgo en producción (casi siempre gana la category) pero protege la validación con datos sintéticos. El único pendiente es de código: que #84 reciba el `tipo` (hoy su firma `decide(AnalysisComplete)` no lo ve).

---

### D-C — Un solo vocabulario de categorías

**Qué decide:** que todo el sistema hable el mismo idioma de categorías.

**Estado:** ✅ **resuelta en código** (Rox, 29/9). El analizador devuelve los valores del enum `InteractionType`, con alias (`duda_tecnica` → `pregunta_tecnica`, etc.).

**¿En el PDF?** **Sí.** El PDF usa `testimonio` y `pregunta_tecnica`, que son parte del vocabulario canónico.

**Factor datos sintéticos:** la ingesta solo produce 3 de las 6 categorías, así que D-C se vuelve relevante sobre todo para el **output del LLM** (que sí produce las 6). Es la base para que D-E tenga sentido.

**Recomendación:** **Mantenerla.** El único pendiente es no volver a duplicarla: que el motor de #84 use `InteractionType` en vez de strings sueltos (`"testimonio"`, `"pregunta_tecnica"`).

---

### D-D — ¿Qué hace que una pregunta sea "frecuente" o "recurrente"?

**Qué decide:** la definición del término "recurrente".

**Estado:** 🟡 pendiente (Yis). Propuesta: recurrente = el `RecurringTopicsDetector` la reporta con `count >= min_occurrences` (default 2).

**¿En el PDF?** **No como requisito.** El PDF llama "Duda frecuente" a la pregunta de Lucas, que es **una sola ocurrencia**. O sea, el PDF usa "frecuente" de forma laxa, no como "se repite N veces".

**Factor detector exigente:** el detector pide `count >= 2` del **mismo** keyword normalizado en un lote, y extrae **una sola palabra** por mensaje. Con datos sintéticos dispersos (y la muestra actual aún más), **casi nunca dispara**. Es un agregador de temas repetidos, no el mecanismo que genera la FAQ del PDF.

**Recomendación (la más importante de alcance):** ratificar la definición, pero **de-scopearla**: D-D define "recurrente" para una feature de agregación *opcional*, **no es el gate de la FAQ**. La FAQ del requisito ya la cumple D-A. Si queremos que el detector sea útil de verdad, eso es un trabajo aparte (bajar el umbral, extraer más de una palabra), no una decisión de contrato que bloquee.

---

### D-E — ¿Un `logro` positivo y relevante se publica como testimonio?

**Qué decide:** si la regla R1 (publicar LinkedIn/Newsletter) aplica solo a `testimonio` o también a `logro`.

**Estado:** 🟡 pendiente (Yis + Rox). Propuesta: **sí**, R1 aplica a `testimonio` y a `logro`.

**¿En el PDF?** **SÍ, y es la decisión más importante para cumplir el reto.** El "testimonio" de Mariana **es un logro** ("quedé seleccionada para el puesto de Dev Jr"), y es lo que genera el `post_linkedin` y el newsletter ("Logro de la Semana").

**Factor datos sintéticos:** como la muestra actual no trae testimonios, la **única** forma de alimentar el LinkedIn/Newsletter es que el LLM clasifique algo como `logro` y que el motor lo publique. Si R1 exige `category == "testimonio"` y el analizador devuelve `logro` (que ya sabe hacer), **el sistema publica cero historias de éxito**.

**Recomendación:** **Sí, ratificarla.** Es la decisión que hace que el reto tenga sentido con los datos disponibles. En #84 es un `or` de una línea (`category in {"testimonio", "logro"}`).

---

## 3. Qué decidir en el equipo (resumen accionable)

| Decisión | Qué decidir | Por qué |
|---|---|---|
| **D-A** | Toda duda → `crear_faq` | El PDF lo exige; el detector no alcanza para esto |
| **D-B** | Mantener (ya resuelta) | Solo falta que #84 reciba el `tipo` |
| **D-C** | Mantener (ya resuelta) | Que #84 use `InteractionType`, no strings |
| **D-D** | Ratificar `count >= 2`, pero **no como gate** | El detector es nice-to-have; la FAQ sale de D-A |
| **D-E** | `logro` se publica como testimonio | Sin esto, el sistema no publica nada con la muestra actual |

**La decisión-meta:** el equipo debe aceptar que **la señal rica (`logro`, y en gran medida `testimonio`) no viene de Mastodon en la práctica — viene del LLM**. Por lo tanto, la calidad del producto depende de (a) cerrar D-E, y (b) confiar en la clasificación del analizador. El detector de temas recurrentes es un agregador opcional que, con los datos actuales, no va a aportar — y no debe ser lo que desbloquea la FAQ.

---

## 4. Orden de merge recomendado

Dado que #73 y #84 **conflictúan** en `src/domain/interfaces.py` (verificado con `git merge-tree`), y que #85 es independiente (archivos nuevos), el orden más limpio es:

1. **#85** — archivos nuevos (`src/prompts/templates.py` + tests), no choca con nada.
2. **#84** — tras arreglar D-B (firma) y D-E (`logro`). Cambia la firma de `interfaces.py`.
3. **#73** — rebase sobre `main`, resolver el conflicto de `interfaces.py` (quedarse con la versión de #84), adoptar el prompt de #85 y borrar el prompt inline.
4. **#83** — solo necesita review/aprobación; puede mergear en cualquier momento.

---

## 5. Próximos pasos por persona

### Yis — motor de decisiones (#84) + decisiones (#69)

- [ ] Cerrar **D-A, D-D y D-E** en #69 siguiendo las recomendaciones de este documento.
- [ ] **#84 — D-B:** cambiar la firma `decide(AnalysisComplete)` para recibir el `InputMessage` (o su `tipo`) y aplicar la precedencia.
- [ ] **#84 — D-E:** R1 acepta `category in {"testimonio", "logro"}`.
- [ ] **#84 — D-C:** usar `InteractionType` y `SentimentType.POSITIVO` en vez de strings.
- [ ] **#84 — tests:** cubrir los casos DEC-12/13/19/20/21 (precedencia `tipo` vs `category`) y el caso `logro`.
- [ ] Revisar y aprobar **#83** (pluralización).

### Rox — analizador (#73) + pluralización (#83)

- [ ] Revisar **#85** (ya reescrita por Emmanuel) y confirmar que los 3 bloqueantes quedaron resueltos; aprobar.
- [ ] Abrir **issue de DERIVAR** (testimonios negativos de alta relevancia), emparejado con D-A.
- [ ] Tras el merge de #84: **rebasear #73** y resolver el conflicto de `src/domain/interfaces.py`.
- [ ] **#73 — wiring:** adoptar `build_analysis_prompt` de #85, borrar el prompt inline y el `TODO(HU-S2-008)`, resolviendo la divergencia de `is_marketing_worthy`.
- [ ] Pedir **re-aprobación de #73** a Emmanuel (el rebase despide la aprobación actual).

### Emmanuel — prompts (#85)

- [ ] **#85 pendiente — `is_marketing_worthy`:** su prompt la sacó, pero el contrato (`RelevanceResult`) y #73 todavía la piden. Decidir con Rox si el contrato la elimina o el prompt la mantiene.
- [ ] **#85 pendiente — wiring:** `build_analysis_prompt` sigue sin conectarse al analizador. Coordinar quién lo conecta (probablemente en #73) para no chocar dos PRs sobre el mismo `_build_prompt`.
- [ ] **Re-aprobar #73** tras el rebase de Rox.
- [ ] Revisar y aprobar **#83** (pluralización), si Yis no lo hace primero.
