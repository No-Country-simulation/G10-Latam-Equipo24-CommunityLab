# Decisiones — CommunityLab

> Registro de decisiones técnicas y de contrato: qué se decidió, por qué, dónde vive
> en el código y qué evidencia lo respalda. Cuando una decisión se aparta del PDF del
> hackathon, el desvío queda explícito acá.
>
> Formato: `D-NN`, en orden de registro.

---

La trazabilidad de cada decisión a sus casos de prueba vive en `docs/pruebas/analisis-decisiones.md`, que mantiene los mismos IDs.

---

## Arquitectura

| ID | Decisión | Opción elegida | Alternativa | Por qué |
|----------|----------------|-------------|---------|---------|
| ARQ-01 | Orquestación | Python puro + async | n8n | Mayor control, testing fácil, integración directa con módulos |
| ARQ-02 | LLM principal | Google Gemini | OpenAI | Gratis y generoso en capa free, bueno en español/portugués |
| ARQ-03 | Interfaz | Streamlit | Gradio | Mejor para paneles de curaduría con estado |
| ARQ-04 | Persistencia | OCI Object Storage | Base de datos | Requisito obligatorio del hackathon + compatible con Always Free |
| ARQ-05 | Módulo de decisiones | Reglas + LLM híbrido | Solo LLM | Determinismo en reglas críticas + contexto en matices |
| ARQ-06 | Deploy | Local + OCI opcional | Solo OCI | MVP rápido + diferencial si hay tiempo |

---

## Contrato / producto

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

### D-F — Feedback negativo: ruta a humano (`DERIVAR`)

**Fecha:** 2026-10-09
**Estado:** decidida — implementada en PR #98 (regla R4)
**Due:** @Rox-0864

**Qué decide.** Qué hace el motor con un mensaje de **sentimiento negativo que no es pregunta
técnica**. Hoy cae en R3 (`descartar`) y se pierde.

**Decisión.** Se agrega la regla **R4**:

```
R4 (después de R2): sentimiento == negativo
    → action = DERIVAR, asset_type = None
    → reason = "Feedback negativo: requiere atención personalizada por el community manager"
```

- **Sin umbral de relevancia.** El prompt de #85 define relevancia alta como "historia de éxito,
  hito o aporte de valor": una queja nunca califica. Exigir relevancia dejaría R4 como código
  muerto, y lo que se quiere es rutear *todo* el feedback negativo.
- **Destino del feedback: B.** Conteo aditivo en `resumen_comunidad` (`feedback_negativo: N`), sin
  exponer el contenido. Mismo patrón que `analisis_degradados`.
- **Orden:** R1 → R2 → R4 → R3. La condición `!= pregunta_tecnica` del borrador original es
  redundante: R2 ya captura las preguntas técnicas y retorna antes.

**Por qué.**

1. **Producto:** R3 borra quejas en silencio; se pierde la señal y no se le puede responder a la
   persona.
2. **Contrato:** `ActionType.DERIVAR = "derivar"` ya existía en `src/domain/models.py` y estaba
   huérfano. Se usa un valor ya diseñado, no uno inventado.
3. **Precedente del PDF:** ya usa "derivar" como "enrutar a un humano/mentoría"
   (`sugerencia_contenido_faq.status = "derivado_a_mentoria"`, PDF línea 224).
4. **Costo:** una condición en el motor; los generadores **no se tocan** (DERIVAR no genera activo).
5. **Es un plus, no un requisito.** El PDF nunca pide rutear feedback negativo: suma sin tocar las
   claves obligatorias del contrato.

**Desvío respecto al PDF.** Ninguno. Es una capacidad adicional sobre un enum que ya estaba en el
contrato.

**Nota de vocabulario.** El PDF usa "derivar" para decir *"el contenido lo produce un mentor"*
(FAQ → mentoría); R4 lo usa para decir *"este mensaje necesita intervención humana"*. Por eso el
`reason` lo explicita y nombra al community manager.

**Visibilidad en el demo.** El dataset de demo no tiene mensajes negativos: sin uno,
`feedback_negativo` sale `0` y la regla queda invisible para el evaluador. La implementación
reemplazó un mensaje de relleno por un mensaje negativo de ejemplo, así que el lote sigue en 12
mensajes. El demo ahora incluye el mensaje de feedback negativo y el conteo se muestra como `1`
con un backend LLM real.

**Dónde vive.**

- `src/decisions/engine.py` — regla R4
- `src/domain/models.py` — `CommunitySummary.feedback_negativo` (aditivo, default `0`)
- `data/sample/demo_fixed.json` — mensaje negativo de ejemplo
- `docs/fichas-historias-usuario.md` — ficha HU que hoy marca DERIVAR como "pendiente"

---

### D-G — Sentimiento: 3 clases, no 5

**Fecha:** 2026-10-09
**Estado:** cerrada

**Contexto.** El PDF del hackathon muestra `"sentimiento_predominante": "Altamente Positivo"`
en su bloque "Ejemplo de Respuesta (Salida Estructurada)" (línea 188), y menciona "sumamente
positivo" en un ejemplo de bifurcación de condiciones (línea 123). El sistema implementa tres
clases: `positivo`, `negativo`, `neutral`.

**Decisión.** Mantener las 3 clases. No se agrega un nivel "Altamente Positivo" ni se migra a una
escala de 5 puntos (Muy negativo → Muy positivo).

**Por qué.**

1. El PDF **no define un vocabulario cerrado** de sentimientos. "Altamente Positivo" aparece una
   sola vez, dentro de un ejemplo de salida, no en un enum ni en un listado de valores válidos.
   Donde el PDF describe los estados de la comunidad (líneas 72-73) menciona tres:
   "comprometida, satisfecha o con dificultades".
2. El único requisito explícito (checklist de evaluación, línea 240) es *"Análisis de sentimiento y
   extracción de temas utilizando LLMs"*. No fija una cantidad de clases.
3. La bifurcación que pide el PDF (línea 123: `sumamente positivo -> generar Caso de Éxito`) se
   cumple funcionalmente con `sentimiento == positivo` **y** `relevancia >= 0.6`
   (`src/decisions/engine.py`). Es más estricta que el ejemplo del PDF, porque agrega el filtro de
   relevancia para no derivar casos de éxito de mensajes positivos triviales.
4. Migrar a 5 clases tocaría `SentimentType`, el schema del prompt del LLM, `_SENTIMENT_PHRASES`,
   `engine.py`, los tests, la matriz `docs/pruebas/analisis-decisiones.md` y los guiones del demo,
   sin ganar ningún requisito.

**Alternativas evaluadas.**

| Alternativa | Por qué no |
|---|---|
| Escala de 5 puntos (Muy negativo … Muy positivo) | Mayor costo de cambio en todo el pipeline, sin requisito que la exija |
| 3 polaridades + campo de intensidad (`alta`/`media`/`baja`) | Modela el grado sin inflar clases, pero igual requiere un campo nuevo en el schema del LLM |

**Desvío documentado respecto al PDF.** La salida emite `"Positivo"` donde el ejemplo emite
`"Altamente Positivo"`. Es una diferencia de **grado**, no de estado, y el contrato no la exige.
La presentación está aislada en un único punto (`_SENTIMENT_PHRASES`), así que el día que se quiera
cambiar la frase no hace falta tocar el dominio.

**Nota técnica.** El grado **no** puede derivarse de `sentiment.score`: ese campo es la
**confianza del modelo, no la intensidad** de la polaridad (`src/analysis/unified_analyzer.py:12`).
Un mensaje enfático con confianza alta daría "altamente positivo" sin serlo. Un grado real exige un
campo nuevo en el schema del LLM, no un umbral sobre el score.

**Dónde vive.**

- `src/domain/models.py` — `SentimentType` (3 valores)
- `src/pipeline.py` — `_SENTIMENT_PHRASES` (frase de presentación)
- `src/decisions/engine.py` — `is_positive` + `RELEVANCE_THRESHOLD`
