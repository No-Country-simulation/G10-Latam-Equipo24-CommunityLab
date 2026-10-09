# Decisiones — CommunityLab

> Registro de decisiones técnicas y de contrato: qué se decidió, por qué, dónde vive
> en el código y qué evidencia lo respalda. Cuando una decisión se aparta del PDF del
> hackathon, el desvío queda explícito acá.
>
> Formato: `D-NN`, en orden de registro.

---

## D-01 — Sentimiento: 3 clases, no 5

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

---

## D-F — Feedback negativo: ruta a humano (`DERIVAR`)

**Fecha:** 2026-10-09
**Estado:** decidida — implementación pendiente
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

**Visibilidad en el demo.** El dataset de demo no tiene mensajes negativos: sin agregar uno,
`feedback_negativo` sale `0` y la regla queda invisible para el evaluador. Se agrega un mensaje
negativo de ejemplo.

**Dónde vive.**

- `src/decisions/engine.py` — regla R4
- `src/domain/models.py` — `CommunitySummary.feedback_negativo` (aditivo, default `0`)
- `data/sample/demo_fixed.json` — mensaje negativo de ejemplo
- `docs/fichas-historias-usuario.md` — ficha HU que hoy marca DERIVAR como "pendiente"

---

<!-- Pendiente: migrar acá la tabla "Resumen de decisiones de arquitectura (para DECISIONS.md)"
     que hoy vive en `docs/arquitectura.md`. -->
