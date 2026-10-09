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

<!-- Pendiente: migrar acá la tabla "Resumen de decisiones de arquitectura (para DECISIONS.md)"
     que hoy vive en `docs/arquitectura.md`. -->
