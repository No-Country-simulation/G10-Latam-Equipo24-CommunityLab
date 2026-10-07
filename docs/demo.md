# Demo del pipeline — CommunityLab

> Cómo correr el pipeline completo de CommunityLab en un dataset de ejemplo, con o sin API key. Pensado para la demo del jueves.

## Quick path

1. `cp .env.example .env` (si no existe) y configurá el backend.
2. **Demostración principal (online, con modelo real):** `python scripts/run_demo.py`
3. **Plan B (offline, sin key ni red):** `python scripts/run_demo.py --offline`

Ambos comandos imprimen los activos generados (LinkedIn, newsletter, FAQ), el estado del almacenamiento y el resumen de la comunidad, y salen con código `0` si el pipeline terminó bien.

## Configurando `.env`

| Variable | Valor | Para qué |
|---|---|---|
| `COMMUNITYLAB_LLM_BACKEND` | `ollama` | Backend del demo online |
| `OLLAMA_MODEL` | `gemma4:31b` | Modelo gratuito elegido (rápido y bueno para JSON) |
| `OLLAMA_API_KEY` | tu key de Ollama Cloud | Habilita el modo nube (`https://ollama.com/v1`) |
| `OLLAMA_BASE_URL` | `https://ollama.com/v1` | Default correcto; solo cambiar si usás un gateway |

El archivo `.env` está en `.gitignore`: **nunca se commitea**.

## Qué hace el script

`scripts/run_demo.py` corre el pipeline completo sobre `data/sample/demo_fixed.json`:

1. **Ingesta** del JSON de ejemplo (12 interacciones).
2. **Análisis** de cada mensaje (sentimiento, categoría, relevancia) en una llamada por mensaje.
3. **Decisión** (motor de reglas) → qué activo genera cada mensaje.
4. **Generación** de los activos: post de LinkedIn, destacado de newsletter y FAQ.
5. **Almacenamiento**: OCI Object Storage si hay credenciales (status `guardado_con_exito`, ruta `activos/<año>-semana-<n>/paquete-distribucion.json`); si no, un **snapshot local** en `storage/activos/paquete-distribucion-<fecha>.json` (gitignored) con estado `pendiente`.

### Salida esperada (online)

```
  backend : ollama (Ollama Cloud, modelo gemma4:31b)
  status  : EXITO
  tiempo  : ~14s
  [LinkedIn]   titulo: Caso de éxito: De estudiante a Desarrolladora de IA
  [Newsletter] titular: Nueva Desarrolladora Junior de IA
  [FAQ]        tema: Estructurar nodos condicionales y routers...
  [storage]    status: guardado_con_exito -> activos/2026-semana-04/paquete-distribucion.json
```

Sin credenciales OCI (lo típico en las máquinas del equipo) el último renglón pasa a mostrar el fallback:

```
  [storage]    status: pendiente -> storage/activos/paquete-distribucion-2026-10-07.json (snapshot local)
```

### Salida esperada (offline)

Determinista y ~instantánea (0s): el cliente `rule_based` genera activos simulados para mostrar el flujo sin depender de ningún servicio.

## Checklist antes de la demo

- [ ] `.env` con `COMMUNITYLAB_LLM_BACKEND=ollama`, `OLLAMA_API_KEY` válida y `OLLAMA_MODEL=gemma4:31b`
- [ ] `python scripts/run_demo.py` termina con `status : EXITO` y activos no vacíos
- [ ] `python scripts/run_demo.py --offline` termina en segundos sin red
- [ ] Versión con `openai` instalado en el venv (`pip install openai`)
- [ ] (Opcional, subir a OCI) `OCI_USER_ID`, `OCI_PRIVATE_KEY_PATH`, `OCI_FINGERPRINT`, `OCI_TENANCY_ID` y `OCI_REGION` en `.env` → la demo muestra `guardado_con_exito`

## Troubleshooting

| Síntoma | Causa | Fix |
|---|---|---|
| `Unauthorized` al llamar | Key de Ollama Cloud inválida/revocada | Generar otra en `ollama.com/settings/keys`, actualizar `.env` |
| `openai is not installed` | Falta la dependencia del modo nube | `pip install "openai>=1.0.0"` |
| Analizadores "fall back to default" | Cliente configurado falla | Revisar `COMMUNITYLAB_LLM_BACKEND` y la key en `.env` |
| La demo imprime `rule_based` sin querer | Falta `COMMUNITYLAB_LLM_BACKEND` en `.env` | Agregarla; el default del código es `rule_based` |
| Snapshot con fecha de ayer | El nombre usa la fecha del día | Esperable; borrar `storage/activos` si molesta |

## Notas de modelo

Los modelos **gratis** de la cuenta son `gemma4:31b` (elegido: rápido y confiable para JSON) y `gpt-oss:20b` (alternativa si se quiere más razonamiento, ~5.5s/llamada). `deepseek-v4.1-flash` y `glm-5.3-flash` requieren créditos.

## Next step

Los PRs de base (#86 generadores, #89 robustez del analizador) ya están **mergeados**; el cableado S3-005 — pipeline, clientes y este demo — viaja en el **PR #90**, aprobado cuando quede en verde.