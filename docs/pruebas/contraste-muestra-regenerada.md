# Contraste de la muestra regenerada (corrida completa)

**Archivo:** `data/sample/corrida-completa-gemma.json` (232 interacciones)
**Regenerada con:** pipeline real — backend `ollama` (`gemma4:31b` vía Ollama Cloud)
**Comando:** `python scripts/generar_muestra.py`
**Motivo:** la muestra anterior era un snapshot medido sobre un `main` **anterior** a
D-I y al fix de R1. Esta regeneración captura el comportamiento del head actual, que
incluye D-I (orden `R1 → R4 → R2 → R3`), el fix de R1 (logros) y la feature de
candidatos FAQ con ranking de frecuencia.

## Contraste de métricas

| Métrica | Anterior | Regenerada | Cambio |
|---|---|---|---|
| Derivados a humano (R4) | 22 | 37 | +15 |
| Dudas frecuentes (R2) | 78 | 64 | −14 |
| Candidatos LinkedIn | 32 | 56 | +24 |
| Candidatos FAQ | — (no existía) | 64 | nuevo |
| Ranking de frecuencia | — (no existía) | presente | nuevo |
| Tipos discrepantes (O-16) | — (no medido) | 56 | nuevo |

## Por qué cambió

1. **D-I — orden `R1 → R4 → R2 → R3`.** R4 (feedback negativo → derivar a humano)
   evalúa *antes* que R2 (pregunta técnica → FAQ). Antes, un mensaje negativo que
   además era pregunta técnica caía en FAQ; ahora se deriva. Por eso los derivados
   suben (22 → 37) y las dudas frecuentes bajan (78 → 64).

2. **Fix de R1 — logros.** R1 acepta `{"testimonio", "logro"}`. Los logros positivos
   relevantes ahora se publican en LinkedIn en vez de descartarse por R3. Por eso
   los candidatos LinkedIn suben (32 → 56).

3. **Feature FAQ.** `candidatos_faq` (64) y el ranking de frecuencia no existían en
   la muestra anterior; son aporte de la feature `feat(faq): temas por candidato y
   ranking de frecuencia`.

## Notas

- La regeneración depende del LLM, por lo que no es determinista: los conteos pueden
  variar unos pocos entre corridas (con `--offline` es determinista, pero no reproduce
  la derivación real ni el sentimiento negativo de los mensajes).
- La muestra es un snapshot ya calculado (`OutputBatch` serializado a JSON); el
  dashboard la carga con el botón "⚡ Cargar muestra de ejemplo" sin ejecutar el LLM.
- `candidatos_faq` y `faq_frecuencia` son campos que produce la feature `feat(faq)`.
  Si esa feature aún no está en `main`, el dashboard los ignora y el resto de la
  muestra se carga con normalidad.
- Referencias: `docs/DECISIONS.md` (D-F, D-I) y `docs/pruebas/analisis-decisiones.md`.
