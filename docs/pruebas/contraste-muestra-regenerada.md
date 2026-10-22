# Contraste de la muestra regenerada (corrida completa)

**Archivo:** `data/sample/corrida-completa-gemma.json` (232 interacciones)
**Regenerada con:** pipeline real — backend `ollama` (`gemma4:31b` vía Ollama Cloud)
**Comando:** `python scripts/generar_muestra.py`

La muestra anterior era un snapshot medido sobre un `main` anterior a D-I y al fix
de R1. Esta regeneración captura el comportamiento del head actual: D-I (orden
`R1 → R4 → R2 → R3`), el fix de R1 (logros), el gate de confianza de derivación, la
consolidación semántica del FAQ y el tope de candidatos LinkedIn.

## Contraste de métricas

| Métrica | Anterior | Final | Cambio |
|---|---|---|---|
| Feedback negativo (total) | 22 | 41 | +19 |
| Derivados a humano (gate > 0.8) | 22 | 17 | −5 |
| Derivados consolidados (reclamos únicos) | — | 4 | nuevo |
| Dudas frecuentes (R2) | 78 | 75 | −3 |
| Candidatos LinkedIn | 32 | 25 (top 25) | −7 |
| Temas FAQ | — | 9 | nuevo |
| Preguntas FAQ huérfanas | — | 38 | nuevo |

## Por qué cambió

1. **Gate de confianza de R4.** Antes R4 derivaba *todo* mensaje negativo. Ahora
   deriva solo `sentimiento == negativo` con `score > 0.8`. Con el prompt de
   sentimiento recalibrado, de 41 negativos se derivan 17 (los de alta confianza);
   el resto queda solo en la métrica `feedback_negativo`.

2. **Deduplicación del buzón.** Los 17 derivados se consolidan por texto normalizado
   en 4 reclamos únicos, cada uno con su conteo de menciones (el community manager
   ve 4 problemas, no 17 repeticiones).

3. **D-I — orden `R1 → R4 → R2 → R3`.** R4 evalúa antes que R2, así un mensaje
   negativo que además es pregunta técnica se deriva en vez de caer en FAQ.

4. **Fix de R1 — logros.** R1 acepta `{"testimonio", "logro"}`; los logros positivos
   relevantes se publican.

5. **LinkedIn top 25.** Los candidatos se ordenan por relevancia descendente y se
   limitan a 25 (piso 0.60), en vez de publicar todos los publicables (56).

6. **FAQ consolidado.** Los candidatos se agrupan en 9 temas semánticos con una
   respuesta generada por tema y una pregunta representativa + conteo. Las preguntas
   sin tema claro (38) se listan aparte.

## Notas

- La regeneración depende del LLM (no determinista): los conteos pueden variar unos
  pocos entre corridas.
- La muestra es un snapshot ya calculado (`OutputBatch` serializado); el dashboard la
  carga con "⚡ Cargar muestra de ejemplo" sin ejecutar el LLM.
- Referencias: `docs/DECISIONS.md` (D-F, D-I) y `docs/pruebas/analisis-decisiones.md`.
