# QA — Evidencia de aceptación del Sprint 1

**Issue:** HU-S1-009 (#47)
**Fecha de ejecución:** 2026-09-25
**Rama evaluada:** `main` @ `58921ec` ("Feat/ci cd sprint1 (#50)", mergeado 2026-09-24)
**Ejecutado por:** itanflores (QA)

## Resumen

| Verificación | Estado |
| --- | --- |
| Estructura base del repo | ✅ Cumple |
| `requirements.txt`, `.gitignore` | ✅ Cumple |
| `.env.example` | ❌ No existe |
| `pytest tests/ -v` | ✅ 22/22 pasan |
| `flake8 src/ --max-line-length=100` | ✅ Sin observaciones |

**Conclusión:** los criterios de aceptación de #47 se cumplen, con un bloqueo (`.env.example` faltante) y observaciones que se documentan abajo para sus propietarios. No se modificó ningún archivo de código ajeno durante esta verificación.

## 1. Estructura del repositorio

Comando: `ls -d src tests data docs .github`

| Carpeta | Esperado | Resultado real |
| --- | --- | --- |
| `src/` | Existe | ✅ Existe |
| `tests/` | Existe | ✅ Existe |
| `data/` | Existe | ✅ Existe |
| `docs/` | Existe | ✅ Existe |
| `.github/` | Existe | ✅ Existe |

## 2. Dependencias y configuración

| Archivo | Esperado | Resultado real | Estado |
| --- | --- | --- | --- |
| `requirements.txt` | Existe | Existe | ✅ |
| `.gitignore` | Existe | Existe | ✅ |
| `.env.example` | Existe (el README lo referencia con `cp .env.example .env`) | **No existe** | ❌ Bloqueo |

## 3. Resultado de `pytest tests/ -v`

```
22 passed, 1 warning in 0.42s
```

Los 22 tests pasan, distribuidos en `test_ci_smoke.py`, `test_contract.py`, `test_input_loader.py`, `test_interfaces.py`, `test_models.py` y `test_normalizer.py`. Se registra una advertencia no bloqueante:

```
src/domain/models.py:140: UserWarning: Field name "copy" in "LinkedInPost" shadows an attribute in parent "BaseModel"
```

**Estado:** ✅ Cumple el criterio de aceptación (resultados reales registrados).

## 4. Resultado de `flake8 src/ --max-line-length=100`

Sin salida — 0 observaciones de estilo.

**Estado:** ✅ Cumple.

## 5. Bloqueos y observaciones

No se modificó código ajeno para producir este resultado; cada punto se documenta con su propietario para que decida cómo resolverlo.

| # | Observación | Evidencia | Propietario | Bloquea #47 |
| --- | --- | --- | --- | --- |
| 1 | Falta `.env.example` en la raíz del repo | El README indica `cp .env.example .env` en la guía de setup, pero el archivo no existe | emanuelperacchia | Sí |
| 2 | El README describe los proveedores LLM como "aún no implementados" | `src/utils/llm.py` ya incluye `GeminiClient`, `OpenAIClient` y `OllamaClient` funcionando | emanuelperacchia | No (documental) |
| 3 | La rama `HU-S1-007-#43` (interfaz de Marcelo) sigue sin rebasar sobre el `main` actual | 5 commits propios, no incluye el historial de `main` (`git merge-base --is-ancestor main` devuelve falso) | Marcelo Rolón / emanuelperacchia (coordinación) | No, pero bloqueará su propio PR |
| 4 | `src/ingest/ingest.py` (rama `feat/ingest-mastodon`) ya corrigió el bug de `_contiene()` reportado antes, pero `calificarTipo()` devuelve `"pregunta tecnica"` y `"comentario general"` — cadenas que no existen en el enum `InteractionType` (`pregunta_tecnica`, `testimonio`, `feedback`, `logro`, `discusion`, `otro`) | Lectura directa de `src/ingest/ingest.py` en `origin/feat/ingest-mastodon` | Elias / Rox-0864 (alinear taxonomía) | No (rama aún no integrada a `main`) |

## 6. Próximo paso

Cerrar #47 adjuntando este archivo como evidencia. El bloqueo #1 (`.env.example`) y las observaciones 2-4 se recomiendan como issues nuevos y separados, para no mezclar el cierre de Sprint 1 con trabajo de otros propietarios.
