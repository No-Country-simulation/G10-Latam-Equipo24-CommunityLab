# Apply Progress: persistencia-oci-estado

Estado acumulado de todos los work units del cambio (OpenSpec store).

## Work Units

| Unidad | Objetivo | PR | Estado | Evidencia |
|--------|----------|----|--------|-----------|
| 1 | OCI JSON storage + credential gate (Domain A) | PR 1 | Done | `src/oci/storage.py`, `src/pipeline.py`; 508 passed; flake8 limpio |
| 2 | PEM bootstrap para Streamlit Cloud (Domain D) | PR 2 | Done | `src/interface/cloud_secrets.py`; test unitario puro |
| 3a | Estado "atendido" OCI-first (Domain B) | PR 3a | Done | `src/interface/state.py` (nuevo), `src/interface/app.py`, `tests/test_interface_app.py`; commit `0a64ce8`; 518 passed; flake8 limpio |
| 3b | Curaduría por lote OCI-first (Domain C) | PR 3b | Done | `src/interface/state.py`, `src/interface/app.py`, `tests/test_interface_app.py`; commit `2b0ad34`; 528 passed; flake8 limpio |
| 4 | Docs / drift de env | PR 4 | Pendiente | Fuera de alcance de este work unit (Phase 4) |

## TDD Cycle Evidence (Strict TDD)

| Task | RED (test escrito primero) | GREEN (implementación) | REFACTOR |
|------|---------------------------|------------------------|----------|
| 3.1 `_load_attended` merge OCI + local | `test_load_attended_merges_oci_and_local_with_local_winning` | `_load_attended` en `src/interface/state.py` | Merge plano (una sola clave por mensaje) |
| 3.2 `set_atendido` escribe mirror + OCI | `test_set_atendido_writes_local_mirror_and_oci`, `test_set_atendido_oci_failure_does_not_raise` | `_save_attended` write-through: mirror local primero, OCI best-effort | Fallo de OCI nunca llega a la UI |
| 3.3 Recarga restaura marcas | `test_fresh_session_state_restores_persisted_attended_marks` | `_attended_cache` cachea en `session_state` | — |
| 3.7 Identidad estable del candidato | `test_candidate_key_is_stable_for_same_content_and_distinct_otherwise` | `_candidate_key` = `sha1(autor\ntexto_original)[:12]` | — |
| 3.8 Round-trip de curaduría | `test_load_set_curation_round_trips_approved_decision` | `load_curation` / `set_curation` | — |
| 3.9 Aislamiento por periodo | `test_curation_is_isolated_by_period` | Clave de cache y archivo por `<periodo>` | — |
| 3.10 Curaduría sin OCI | `test_curation_persists_locally_when_oci_is_unavailable` | `_write_json_dict` al mirror local | — |
| 3.5 / 3.6 Cache + persistencia | `test_build_derivados_entries_marks_attended_state`, `test_reset_batch_state_clears_derivados_state_and_widget_keys` | `build_derivados_entries` lee el estado persistido; `reset_batch_state` suelta el cache | — |
| 3.11 / 3.12 Periodo por lote | `test_process_json_input_stashes_periodo_referencia`, `test_reset_batch_state_clears_periodo_referencia`, `test_extract_periodo_falls_back_to_object_path` | `_resolve_input_periodo` + `_extract_periodo` (envelope → ruta OCI → semana ISO) | — |
| 3.13 Seeding de los radios | `test_curation_radio_seeded_from_persisted_state` | `_curation_radio` siembra la key del widget ANTES de renderizar | Identidad por contenido, no por índice |
| Extra (bug encontrado en review) | `test_load_curation_merges_oci_and_local_keeping_both_decisions` (RED: fallaba) | Merge por canal Y por candidato en `load_curation` | Un merge a nivel de canal borraba decisiones del otro store |
| Extra (degradación) | `test_curation_radio_ignores_unknown_persisted_status` | Streamlit ignora un valor de sesión desconocido | Se descartó un guard extra: la degradación ya es nativa |

## Work Unit Evidence (work unit 3 — `dominios-bc-estado-dashboard`)

### 3a — Domain B (estado "atendido") · commit `0a64ce8`

| Evidencia | Valor |
|-----------|-------|
| Focused test command | `venv/bin/python -m pytest tests/test_interface_app.py -q` → 82 passed; suite completa `venv/bin/python -m pytest tests/ -q` → 518 passed |
| Runtime harness | AppTest (`streamlit.testing.v1.AppTest.from_file`) renderiza la app real con el seam `state.OCIStorageClient` parcheado a un fake en memoria: sin escritura al bucket real (el bucket conserva 7 objetos, sin `estado/*`) |
| Rollback boundary | `src/interface/state.py` (nuevo) + `src/interface/app.py` (wiring) + `tests/test_interface_app.py`. Revertir el commit devuelve la app al estado previo sin tocar Domain A ni Domain D |
| Lint | `venv/bin/python -m flake8 src tests` → exit 0 |
| Ledger nativo | Attempt ordinal 5, work unit `dominio-b-estado-atendido`, `changed_lines=146`, `budget_exceeded=false`, `evidence_revision=sha256:b5173acf…` |

### 3b — Domain C (curaduría por lote) · commit `2b0ad34`

| Evidencia | Valor |
|-----------|-------|
| Focused test command | `venv/bin/python -m pytest tests/test_interface_app.py -q` → 90 passed; suite completa `venv/bin/python -m pytest tests/ -q` → 528 passed |
| Runtime harness | AppTest renderiza la app real: seeding del radio, tab Derivados, curaduría por periodo. El bucket real no recibe escrituras (`estado.OCIStorageClient` parcheado a un fake) |
| Rollback boundary | Mismos tres archivos; revertir el commit deja la curaduría solo en sesión sin tocar el Domain B ya mergeado |
| Lint | `venv/bin/python -m flake8 src tests` → exit 0 |
| Ledger nativo | Attempt ordinal 6, work unit `dominio-c-curaduardia`, `changed_lines=482`, `budget_exceeded=false`, `evidence_revision=sha256:0ff50776…` |

### Por qué el work unit 3 se partió en dos

El attempt único (ordinal 4, `dominios-bc-estado-dashboard`) pasó las pruebas pero cerró con
`changed_line_budget_exceeded=true` → estado `blocked` (`reason: maintainer_decision`).
El mantenedor decidió partirlo en dos work units verdes (`size:exception` no pedido: cada
slice entra por debajo del presupuesto). Se ejecutó `gentle-ai sdd-attempt reset` y se
abrieron los attempts 5 y 6. El árbol final del work unit 3b es idéntico al del commit
único verificado (`76bb4c5…`), así que la partición no cambió un byte de la
implementación: solo la endured de la entrega y el foco de revisión.


## Work unit 5 — remediación de la auditoría del panel (2026-10-21)

Dos defectos detectados al auditar el panel en producción, ambos en el tramo superior
de la cadena: la capa de estado escribía en el bucket equivocado y el aviso de feedback
negativo reportaba una población distinta como si fuera la misma.

| Aspecto | Detalle |
|---------|---------|
| Alcance | `src/interface/state.py`, `src/interface/app.py`, `tests/test_interface_app.py` |
| TDD | RED: 3 tests fallan (`test_state_layer_targets_the_bucket_configured_by_env`, `test_negative_feedback_notice_reports_the_real_derived_count`, `test_negative_feedback_notice_says_when_none_was_derived`); `test_state_layer_falls_back_to_default_bucket_without_env` ya pasaba (guarda el fallback) |
| GREEN | 4 passed → suite completa en la rama B: 521 passed + 1 skipped; en la rama C (con la curaduría mergeada): 532 passed |
| Aislamiento | La fixture `_isolate_persisted_state` ahora hace `monkeypatch.delenv("OCI_BUCKET_NAME", raising=False)`: `src/oci/client.py` carga el `.env` real con `load_dotenv()`, que filtraba el bucket de producción al proceso de tests |
| Lint | `venv/bin/flake8 src tests scripts` → exit 0 |
| Commits | `3d3c86f` fix(state): resolve the OCI bucket from OCI_BUCKET_NAME · `876402b` fix(interface): report the real derived count in the negative-feedback notice |
| Worktree | `../G10-Latam-Equipo24-CommunityLab-worktrees/wu-bucket` sobre `feat/persistencia-oci-estado-b` (PR #169); merge de B en C: `cc8688e` |
| Ledger nativo | Attempt ordinal 7, work unit `w5-remediacion-auditoria-panel`, `state: complete`, `changed_lines` dentro de `max_changed_lines=200`, `evidence_revision=sha256:0e5ed089…` |
| PRs | #169 (Domain B) y #170 (Domain C) actualizados con la remediación |

### Por qué los fixes van en la rama B y no en la punta de la cadena

La capa de estado es propiedad del Domain B (PR #169). Publicar un fix de B desde la
punta obligaría a un forward-merge por cada PR intermedio de la cadena. Los dos fixes
viajan juntos en B (mismo origen, misma auditoría, un solo work unit) y B se fusiona en
C con un merge local, así que el diff de #170 sigue siendo exactamente el del Domain C.

### Hallazgos de la auditoría que NO son bugs

- El status `pendiente` del panel viene de `data/sample/corrida-completa-gemma.json`,
  que trae el `almacenamiento_oci` horneado del 20-oct 21:58. El botón "Cargar muestra de
  ejemplo" carga ese JSON sin correr el pipeline ni subir a OCI; con un lote real el
  status es `guardado_con_exito` (el cliente OCI funciona).
- `feedback_negativo` (41) y `mensajes_derivados` (4) son poblaciones distintas por
  diseño: la primera cuenta todo mensaje con sentimiento NEGATIVO (`src/pipeline.py`),
  la segunda solo las decisiones DERIVAR de la regla R4 (`is_negative and
  negative_confidence > 0.8`, `src/decisions/engine.py`). El bug era el copy, no el dato.

## Work unit 4 — documentación de despliegue y readiness (2026-10-21)

Cierra el cambio con la documentación que faltaba para que el deploy en Streamlit
Cloud sea reproducible sin conocimiento tribal: el flujo del secret inline, la
checklist de readiness y la alternativa en `.env.example`.

| Aspecto | Detalle |
|---------|---------|
| Alcance | `docs/deploy-streamlit-cloud.md`, `.env.example` |
| 4.1 | La guía deja de tratar `OCI_PRIVATE_KEY_PATH` como bloqueante: documenta el secret inline `OCI_PRIVATE_KEY` (PEM multilínea de TOML), la checklist de 7 variables (`OCI_REQUIRED_ENV` → `oci_credentials_complete()`), cómo la clave llega a la nube (`bootstrap_oci_private_key()` → temporal 0600 → `OCI_PRIVATE_KEY_PATH`), y los dos modos de falla del PEM (newlines escapados, línea final `OCI_API_KEY`) |
| 4.2 | `.env.example` declara las dos formas de la clave privada, con la regla de una-o-la-otra |
| 4.3 | Suite completa: 532 passed; flake8 `src tests scripts` → exit 0; sin regresiones |
| 4.4 | Las constantes `_OCI_REQUIRED_ENV` duplicadas en los tests ya no existen: el commit `6ac1e9d` (Domain A, PR #167) las eliminó al introducir el `OCI_REQUIRED_ENV` canónico en `src/oci/storage.py`. Verificado con `grep -rn "_OCI_REQUIRED_ENV" tests/` → 0 coincidencias; los 5 archivos de test importan la constante canónica |
| Commit | `4ebe3c5` docs(deploy): document the inline OCI_PRIVATE_KEY secret flow |
| Ledger nativo | Attempt ordinal 8, work unit `w4-docs-readiness`, `state: complete`, `evidence_revision=sha256:78a1a4f8…` |
| PR | #170 actualizado |

### El dato que la guía tenía mal

La versión anterior de la guía decía que sin montar un `.pem` dentro del contenedor
la nube no podía subir a OCI. Eso era cierto antes del bootstrap de
`src/interface/cloud_secrets.py` (commit `281f643`): hoy la app resuelve sola la
ruta que el SDK exige, y el status `pendiente` que se veía en el panel era
consecuencia de la credencial ausente, no de una limitación de la plataforma.

## Desviaciones respecto al diseño original

1. **La capa de persistencia vive en `src/interface/state.py`, no en `app.py`** (decisión D9 en `design.md`).
   Motivo: Streamlit ejecuta una *copia* de `app.py`, así que un seam parcheado en `src.interface.app` nunca llega a la copia que corre — y lo probó el propio harness: los patches sobre `app` no se observaban. El módulo importado por nombre es compartido por todas las copias, así que sus seams se leen en tiempo de llamada y siempre coinciden.
   `app.py` reexporta los nombres públicos mediante un `__getattr__` de módulo (PEP 562), de modo que la superficie pública no cambia.
2. **El merge de la curaduría es por canal Y por candidato** (decisión D10 en `design.md`).
   Motivo: un merge a nivel de canal descartaba las decisiones que el otro store todavía tenía (una aprobación guardada en OCI desaparecía si el mirror local existía sin esa clave).
3. **Se descartó un guard extra** para un estado de curaduría desconocido en el archivo: la propia API de `st.radio` lo degrada a "Pendiente" y la siguiente renderización lo reescribe. Cubierto por `test_curation_radio_ignores_unknown_persisted_status`.

## Pendiente

- Cadena publicada (tracker #166): #167 `feat/persistencia-oci-estado-a` (Domain A, base `feat/derivacion-faq-d`) → #168 `feat/persistencia-oci-estado-d` (Domain D) → #169 `feat/persistencia-oci-estado-b` (Domain B) → #170 `feat/persistencia-oci-estado-bc` (Domain C). Cada PR toma como base la rama del anterior (patrón `feature branch chain` del repo, como los PRs #161–#164) y lleva exactamente un label `type:feature`.
- Work unit 5 (remediación de la auditoría del panel) aplicado y mergeado en la cadena: el estado resuelve el bucket desde `OCI_BUCKET_NAME` y el aviso de feedback negativo reporta el conteo real de derivadas.
- El usuario debe pegar el bloque de secrets de OCI en App → Settings → Secrets de Streamlit Cloud y luego borrar `/tmp/opencode/oci-secrets-block.toml`.
