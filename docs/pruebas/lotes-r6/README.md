# Lotes de los 5 casos de transformación — R6

Un archivo por caso, en el formato `InputBatch` (`origen_comunidad`,
`periodo_referencia`, `interacciones[]`). Son los lotes exactos con los que se
obtuvieron los casos de [`../ejemplos-transformacion-r6.md`](../ejemplos-transformacion-r6.md).

| Archivo | Caso | Entrada | Decisión esperada |
|---------|------|---------|-------------------|
| `C1.json` | Testimonio de empleo | Mariana Souza, `#logros-y-empleos`, `testimonio` | `publicar` / LinkedIn |
| `C2.json` | Logro (certificación) | Ana Rodríguez, `#logros-y-empleos`, `testimonio` | `publicar` / LinkedIn |
| `C3.json` | Duda técnica | Sofía Lima, `#dudas-langgraph`, `pregunta_tecnica` | `crear_faq` / FAQ |
| `C4.json` | Feedback organizativo | Pedro Núñez, `#general`, `feedback` | `descartar` (sin activo) |
| `C5.json` | Reclamo con carga negativa | Camila Vega, `#general`, `feedback` | `derivar` (con D-I) |

## Reproducirlos

Con el LLM de la demo (Ollama Cloud, `gemma4:31b`), usando el backend de `.env`:

```bash
python scripts/run_demo.py docs/pruebas/lotes-r6/C1.json
```

Con el backend determinista (sin red ni costo):

```bash
python scripts/run_demo.py docs/pruebas/lotes-r6/C1.json --offline
```

`scripts/run_demo.py` acepta varios archivos a la vez.

> **C5 necesita el LLM.** La detección de sentimiento negativo depende del modelo:
> con `rule_based` (`--offline`), el mensaje de C5 no se marca como negativo y
> termina en FAQ. C1–C4 se reproducen con los dos backends.

## Origen de los lotes

C1, C2, C3 y C5 están incluidos **textualmente** en `data/sample/demo_fixed.json`,
la fuente curada de la muestra combinada (12 interacciones). Por eso la corrida
completa y estos lotes coinciden en esos mensajes.

C4 es un lote propio con el mismo perfil que `Pedro Núñez` en las muestras: un
`feedback` neutro que no debe generar activo.

## Nota sobre el canal de C3

El mensaje de C3 vive en `#dudas-langgraph` (canal de la comunidad), no en
`#ayuda`. El canal `#ayuda` que aparece en `docs/deploy.md` y en algunos fixtures
es el del **ejemplo del contrato PDF**, no el de este mensaje.
