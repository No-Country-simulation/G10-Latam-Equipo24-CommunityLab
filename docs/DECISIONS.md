# Decisiones — CommunityLab

> Registro de decisiones técnicas y de contrato: qué se decidió, por qué, dónde vive
> en el código y qué evidencia lo respalda. Cuando una decisión se aparta del PDF del
> hackathon, el desvío queda explícito acá.
>
> IDs: `ARQ-NN` para arquitectura; `D-A`, `D-B`, … para contrato y producto. Los IDs no se
> renumeran: los documentos de prueba los referencian.

---

La trazabilidad de cada decisión a sus casos de prueba vive en `docs/pruebas/analisis-decisiones.md`, que mantiene los mismos IDs.

---

## Arquitectura

| ID | Decisión | Opción elegida | Alternativa | Por qué |
|----------|----------------|-------------|---------|---------|
| ARQ-01 | Orquestación | Python puro + async | n8n | Mayor control, testing fácil, integración directa con módulos |
| ARQ-02 | LLM principal | Gemma (Ollama) | Google Gemini | Gratis (local o vía Ollama Cloud) y confiable para JSON |
| ARQ-03 | Interfaz | Streamlit | Gradio | Mejor para paneles de curaduría con estado |
| ARQ-04 | Persistencia | OCI Object Storage | Base de datos | Requisito obligatorio del hackathon + compatible con Always Free |
| ARQ-05 | Módulo de decisiones | Reglas + LLM híbrido | Solo LLM | Determinismo en reglas críticas + contexto en matices |
| ARQ-06 | Deploy | Local + OCI opcional | Solo OCI | MVP rápido + diferencial si hay tiempo |
| ARQ-07 | Clave privada de OCI | Ruta **o** contenido, sin archivo temporal | Solo ruta (archivo temporal en la nube) | El SDK acepta el contenido: no hace falta escribir la clave en disco |

### ARQ-07 — La clave privada llega como archivo o como contenido

**Fecha:** 2026-10-22
**Estado:** decidida

**Qué decide.** Cómo llega la clave privada de OCI a la app y qué exige el gate
de credenciales antes de intentar una llamada a Object Storage.

**Decisión.** La clave tiene **dos formas admitidas** y alcanza con una:

| Variable | Forma | Dónde aplica |
|---|---|---|
| `OCI_PRIVATE_KEY_PATH` | ruta a un archivo `.pem` | checkout local |
| `OCI_PRIVATE_KEY` | el contenido PEM | secrets de Streamlit Cloud |

- Si la ruta apunta a un archivo que **existe**, **gana la ruta**.
- Si no existe, se usa el **contenido**, con los escapes `\n` literales
  convertidos en saltos de línea (un cuerpo PEM es base64 y nunca lleva barra
  invertida, así que un `\n` literal solo puede ser un escape).
- El SDK recibe el contenido por `key_content`: **no se escribe ningún archivo
  en disco**, ni temporal ni de ningún otro tipo.

**El gate** (en `src/oci/storage.py`) pide **cuatro** variables obligatorias —
`OCI_USER_ID`, `OCI_FINGERPRINT`, `OCI_TENANCY_ID`, `OCI_REGION` — y **una de
las dos** formas de la clave. Si falta alguna, la operación degrada al mirror
local y el log dice qué variables faltan.

**Por qué.**

1. **La nube no tiene archivos.** En Community Cloud los secrets son strings;
   la versión anterior resolvía el problema escribiendo la clave en un archivo
   temporal con permisos `0600` y registrándolo en `atexit`. Eso agregaba
   superficie (un archivo con la clave en el disco del contenedor, una limpieza
   que depende del proceso, `chmod` que no existe en Windows) para resolver un
   problema que el SDK ya resuelve solo.
2. **El local no cambia.** Con la ruta a un `.pem` que ya existe, el
   comportamiento es el de siempre: el mismo `key_file` de siempre.
3. **El gate queda explícito.** Antes la clave era obligatoria *como ruta*;
   ahora el gate dice "una de las dos", y el log nombra el grupo completo
   cuando no hay ninguna.

**Alternativas evaluadas.**

| Alternativa | Por qué no |
|---|---|
| Mantener el bootstrap a archivo temporal | Un archivo con la clave en el disco del contenedor, permisos que el SO no siempre aplica, y una limpieza atada al ciclo de vida del proceso |
| Aceptar solo el contenido | Rompe el checkout local, que ya tiene la clave en un `.pem` y la ruta documentada en `docs/oci-setup.md` |
| Aceptar solo la ruta | Obliga a la nube a montar o escribir la clave, que es exactamente lo que se quería evitar |

**Dónde vive.**

- `src/oci/client.py` — `_normalize_pem` y el `config` con `key_file` /
  `key_content` (el archivo gana cuando existe)
- `src/oci/storage.py` — `OCI_REQUIRED_ENV`, `OCI_KEY_ENV`,
  `OCI_CREDENTIAL_ENV` y `missing_oci_credentials()`
- `src/interface/cloud_secrets.py` — exporta los secrets y nada más
- `tests/test_oci_client.py`, `tests/test_oci_integration.py`,
  `tests/test_interface_cloud_secrets.py`

**Desvío respecto al PDF.** Ninguno: sigue siendo OCI Object Storage como
persistencia (ARQ-04) y la app degrada a snapshot local sin credenciales.

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

**Estado:** ✅ **decidida** (Yis + Rox). Implementada: R1 aplica a `testimonio` y a `logro` (`src/decisions/engine.py:55` → `is_publishable_type = effective_type in {"testimonio", "logro"}`).

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

**Visibilidad en el demo.** El dataset de demo no tenía mensajes negativos: sin uno,
`feedback_negativo` salía `0` y la regla quedaba invisible para el evaluador. La implementación
reemplazó un mensaje de relleno por un mensaje negativo de ejemplo, así que el lote sigue en 12
mensajes. El demo muestra el conteo en su resumen y con un backend LLM real se ve como `1`; con el
backend `rule_based` (default de un clon limpio) sale `0`, porque ese cliente nunca emite `negativo`.

**Dónde vive.**

- `src/decisions/engine.py` — regla R4
- `src/domain/models.py` — `CommunitySummary.feedback_negativo` (aditivo, default `0`)
- `src/pipeline.py` — conteo de `DERIVAR` en el resumen; `DERIVAR` excluido del fallback del newsletter
- `data/sample/demo_fixed.json` — mensaje negativo de ejemplo
- `scripts/run_demo.py` — muestra el conteo en el resumen del demo
- `docs/fichas-historias-usuario.md` — ficha HU actualizada a R4/D-F (PR #98)

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

---

### D-H — El botón "Publicar en Telegram" depende de la aprobación de LinkedIn

**Fecha:** 2026-10-14
**Estado:** decidida — implementada en PR #119
**Due:** @Rox-0864

**Qué decide.** Si el botón "📨 Publicar en Telegram" del panel exige que el post de LinkedIn esté
Aprobado, o si es una acción independiente.

**Decisión.** El botón está condicionado. Se habilita solo cuando se cumplen las dos condiciones:

```
disabled = (linkedin_estado != Aprobado) or (la firma del candidato ya se publicó en esta sesión)
```

y el handler revalida ambas por su cuenta, para que un click viejo no publique sin la aprobación ni
reenvíe lo ya enviado.

**Por qué.**

1. **Coherencia de curaduría.** El requisito del reto es que el panel de curaduría decida qué sale
   publicado. El mensaje de Telegram sale del mismo contenido que el post de LinkedIn (el copy del
   editor alimenta ambos canales), así que publicarlo sin la aprobación que el humano ya exige para
   LinkedIn saltaría el paso de revisión.
2. **Un solo criterio, no dos.** Sin el gate, el panel tendría dos definiciones de "listo para
   publicar" según el canal, y la de Telegram sería la más laxa.
3. **El bloqueo de reenvío es el mismo gate, no un extra.** La firma (`publish_signature`) es la
   identidad del candidato más el copy editado, y la hora se guarda en
   `st.session_state["telegram_published_times"]`. Editar el copy cambia la firma y vuelve a habilitar
   el envío, que es el caso legítimo.

**Alternativas evaluadas.**

| Alternativa | Por qué no |
|---|---|
| Botón independiente (publicar en Telegram sin aprobar LinkedIn) | Permite publicar afuera contenido sin revisar; el cambio es una línea en `disabled`, pero requiere su propia decisión y su propia guarda |
| Pedir confirmación en vez de deshabilitar | Agrega un paso a cada envío y no cubre el click viejo sobre un estado ya publicado; el deshabilitado por firma sí lo cubre |

**Desvío respecto al PDF.** Ninguno. El reto pide un panel de curaduría con aprobación; el gate
refuerza ese requisito en un canal externo.

**Nota de vocabulario.** La copy del producto va en **español neutro**; el voseo es de la conversación,
no de la interfaz. Se corrigieron los textos del panel ("Aprobá el post de LinkedIn" → "debe estar
aprobado", "definí / Configurá TELEGRAM_BOT_TOKEN" → "se requieren ... en el archivo .env") y los
mensajes de la capa de ingesta que el panel muestra cuando el envío falla ("revisá la conexión y volvé a
intentar" → "revisar la conexión y volver a intentar"), incluidos los del bot. Los mismos mensajes están
duplicados en los scripts de CLI y en las respuestas del webhook; no se tocaron para no mezclar alcance
ni cambiar la respuesta pública de la API.

**Dónde vive.**

- `src/interface/app.py` — bloque de publicación: gate combinado y guarda en el handler
- `src/interface/telegram_publish.py` — `publish_signature`, `publish_candidate`
- `tests/test_interface_app.py` — `test_publish_button_is_gated_by_linkedin_state`,
  `test_publish_button_disables_and_blocks_second_send`,
  `test_publish_button_requires_approval_and_unsent_signature`
- `src/ingest/telegram.py`, `src/ingest/bot.py` — mensajes de error que el panel muestra
- `docs/DECISIONS.md` — esta entrada

---

### D-I — Orden de reglas: R4 antes de R2

**Fecha:** 2026-10-16
**Estado:** decidida

**Qué decide.** El orden de evaluación cuando un mensaje es **negativo y además pregunta
técnica**: si decide R2 (`crear_faq`) o R4 (`derivar`).

**Decisión.** El orden pasa a **R1 → R4 → R2 → R3**. R4 se evalúa antes que R2:

```
R1 → R4 (negativo → DERIVAR) → R2 (pregunta_tecnica → CREAR_FAQ) → R3
```

**Actualización (2026-10-21) — R4 tiene umbral de confianza.** R4 **no deriva todo negativo**:
deriva solo los negativos con `negative_confidence > 0.8` (`CONFIDENCE_THRESHOLD` en
`src/decisions/engine.py`). La regla completa queda:

```
R1 → R4 (negativo con confianza > 0.8 → DERIVAR) → R2 (pregunta_tecnica → CREAR_FAQ) → R3
```

Un negativo que no supera el umbral **no se deriva**: sigue por las reglas siguientes (una
pregunta técnica negativa de baja confianza termina como FAQ, cubierto por
`test_low_confidence_negative_technical_question_goes_to_faq`).

El **orden** decidido arriba no cambia con este ajuste, y el contrato tampoco:
`feedback_negativo` sigue contando **todos** los mensajes con sentimiento negativo (41 en la
muestra de #164), mientras `mensajes_derivados` lista solo los que superaron el umbral (4 en esa
misma muestra). Son **dos poblaciones distintas**, no dos versiones del mismo número.

Esta entrada **reemplaza la nota de orden de D-F** ("Orden: R1 → R2 → R4 → R3" y "la condición
`!= pregunta_tecnica` del borrador original es redundante: R2 ya captura las preguntas técnicas
y retorna antes"). Ese argumento es exactamente el que deja de ser cierto: hoy R2 no retorna
primero, así que una pregunta técnica negativa llega a R4. La condición `!= pregunta_tecnica`
tampoco hace falta ahora, pero por otro motivo: R4 atiende los negativos antes de que R2 corra,
y R2 se queda con las preguntas técnicas no negativas.

**Por qué.**

1. **Producto:** una queja negativa cuyo `tipo` es `pregunta_tecnica` se tragaba en R2 y nunca
   llegaba a un humano. El `tipo` lo asigna el clasificador por palabras clave de la ingesta,
   así que el LLM no podía corregir el error (O-16).
2. **Sin cambios para el resto:** en un mensaje no negativo R4 no se activa y R2 sigue
   capturando las preguntas técnicas, con la misma decisión que antes.
3. **Cobertura:** DEC-22 y `test_dec_22_negative_technical_question_is_derived` cubren el caso;
   DEC-09 queda cubierta por R4.

**Alternativas evaluadas.**

| Alternativa | Por qué no |
|---|---|
| Dejar R2 antes que R4 y agregar la condición `!= pregunta_tecnica` a R4 | Mantiene el hueco: la queja negativa se sigue publicando como FAQ y no llega a un humano |
| Quitar la precedencia del `tipo` (D-B) para que decida el LLM | Arriesga la demo con datos etiquetados a mano y mezcla dos decisiones distintas |

**Desvío respecto al PDF.** Ninguno. Es un reordenamiento de reglas internas; las claves del
contrato no cambian.

**Dónde vive.**

- `src/decisions/engine.py` — orden R1 → R4 → R2 → R3, con `CONFIDENCE_THRESHOLD = 0.8` en R4
- `tests/test_decisions.py` — `test_dec_22_negative_technical_question_is_derived`,
  `test_high_confidence_negative_message_is_derived`,
  `test_low_confidence_negative_message_is_not_derived`
- `docs/pruebas/analisis-decisiones.md` — DEC-22 (nueva) y DEC-09 (actualizada)
- `docs/DECISIONS.md` — esta entrada (reemplaza la nota de orden de D-F)
