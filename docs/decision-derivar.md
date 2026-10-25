# Decisión DERIVAR — testimonios negativos de alta relevancia

> Documento para **@Yis-ai-eng**. Complementa `decisiones-contrato.md` (las
> decisiones D-A a D-E): cierra el follow-up de *"qué hacer con los testimonios
> negativos de alta relevancia (DERIVAR)"* que quedó pendiente en ese doc, junto
> con D-A (orden de reglas).

## El caso

Un mensaje que el analizador clasifica con **sentimiento negativo** y que **no
es una pregunta técnica** (esa ya la cubre R2 → FAQ).

Ejemplo: *"Me prometieron mentoría personalizada y nunca llegó."*

## El problema

Con las reglas actuales del motor (#84), ese mensaje cae en **R3
(`descartar`)**. Se pierde feedback valioso: alguien tuvo una mala experiencia y
el sistema lo borra en vez de enrutarlo.

## Propuesta: regla R4 — DERIVAR

> **Nota (implementación final):** esta regla se implementó con un criterio
> distinto al propuesto acá. El código (`src/decisions/engine.py`) deriva por
> **confianza del sentimiento negativo mayor a 0.8** (`CONFIDENCE_THRESHOLD`),
> no por relevancia, y **sin excluir** las preguntas técnicas: R4 se evalúa
> antes que R2, así que una pregunta técnica con feedback negativo de alta
> confianza también se deriva. El umbral de "alta relevancia" discutido abajo
> quedó descartado; el umbral que quedó es el de confianza.

```
R4 (implementado): sentiment == NEGATIVO AND confianza > 0.8
    → action = DERIVAR, asset_type = None
    → reason = "Feedback negativo: requiere atención personalizada por el community manager"
```

## Qué significa "derivar"

- **NO genera activo de marketing** (nadie publica feedback negativo).
- Se **marca para revisión humana**: un community manager/soporte lo lee y decide
  (responder, escalar, descartar).
- **No es un asset del contrato** → no aparece en `activos_distribucion_generados`.
  Es una salida interna del `DecisionResult`.

## Precedente en el contrato

`FAQSuggestion.status = "derivado_a_mentoria"` — el PDF ya usa "derivar" como
"enrutar a un humano/mentoría". DERIVAR extiende ese patrón a los testimonios
negativos.

## Impacto en #84

- Agregar la regla R4 (una condición más en `RuleBasedDecisionEngine`).
- Usar `ActionType.DERIVAR`, que hoy está **definido pero huérfano**.
- Los generadores **no se tocan** (DERIVAR no genera activo).

## Dos puntos a cerrar

### 1. El umbral de "alta relevancia"

El `relevance.score` actual está definido como *"alto solo si hay historia de
éxito, hito o aporte de valor"* (prompt de #85). Un testimonio **negativo**
difícilmente alcanza relevancia alta con esa definición — son conceptos en
tensión.

**Recomendación:** primera versión con `DERIVAR = negativo y no técnico`, sin
exigir relevancia. Ruta todo feedback negativo al humano. El refinamiento
(distinguir queja importante de venting) queda para después.

### 2. ¿A dónde va el feedback derivado?

- **A:** cola de revisión (nuevo campo en el resumen).
- **B:** conteo en `resumen_comunidad` (ej. `feedback_negativo: 3`), sin exponer contenido.
- **C:** solo log/registro interno.

**Recomendación:** **B** — deja evidencia sin exponer contenido sensible.

## Pedido a Yis

1. Confirmar la regla R4 (o ajustar el umbral).
2. Elegir destino (A/B/C).
3. Implementar R4 en #84, junto con el fix de D-B (la firma `decide()`).
