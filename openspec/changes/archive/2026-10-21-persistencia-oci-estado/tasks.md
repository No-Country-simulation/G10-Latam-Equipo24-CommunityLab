# Tasks: Persistencia del estado operativo en OCI

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 700–850 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Domain A) → PR 2 (Domain D) → PR 3 (Domains B+C) → PR 4 (docs/drift) |
| Delivery strategy | ask-on-risk (resolved: the chain is already in flight — PR 3 = Domains B+C on `feat/persistencia-oci-estado-bc`) |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | OCI JSON storage + credential gate | PR 1 | `venv/bin/python -m pytest tests/test_oci_integration.py -q` | Real-cred round-trip stays behind `skipif` | `src/oci/storage.py`, `src/pipeline.py` |
| 2 | PEM bootstrap for Streamlit Cloud | PR 2 | `venv/bin/python -m pytest tests/test_interface_cloud_secrets.py -q` | N/A — pure unit test | `src/interface/cloud_secrets.py` |
| 3 | Attended + curation state OCI-first | PR 3 | `venv/bin/python -m pytest tests/test_interface_app.py -q` | AppTest render + toggle/round-trip tests | `src/interface/app.py` |
| 4 | Docs/env drift cleanup | PR 4 | `venv/bin/python -m pytest tests/ -q` | N/A — docs only | `docs/deploy-streamlit-cloud.md`, `.env.example`, test imports |

## Phase 1: Foundation — OCI JSON primitives

### Domain A (RED)
- [x] 1.1 Add RED test: `put_json`/`get_json` round-trip through a fake `OCIClient` in `tests/test_oci_integration.py`.
- [x] 1.2 Add RED test: `get_json` returns default on missing key and on corrupt JSON.
- [x] 1.3 Add RED test: `put_json`/`get_json` never raise when the SDK is missing.
- [x] 1.4 Add RED test: `oci_credentials_complete()` requires 7 vars; missing `OCI_BUCKET_NAME` returns False.

### Domain A (GREEN)
- [x] 1.5 Implement lazy `client` property, `put_json`, and `get_json` in `src/oci/storage.py`.
- [x] 1.6 Add `OCI_REQUIRED_ENV`, `oci_credentials_complete()`, and `DEFAULT_BUCKET` to `src/oci/storage.py`.
- [x] 1.7 Refactor `src/pipeline.py:_oci_credentials_present()` to delegate to `oci_credentials_complete()` and import `DEFAULT_BUCKET`.
- [x] 1.8 Update `tests/test_webhook.py`, `tests/test_csv_loader.py`, `tests/test_bot.py` to import canonical `OCI_REQUIRED_ENV`.

## Phase 2: Foundation — PEM bootstrap

### Domain D (RED)
- [x] 2.1 Add RED test: `bootstrap_oci_private_key()` writes PEM to a 0600 temp file and sets `OCI_PRIVATE_KEY_PATH` in `tests/test_interface_cloud_secrets.py`.
- [x] 2.2 Add RED test: pre-existing `OCI_PRIVATE_KEY_PATH` is preserved and no temp file is created.
- [x] 2.3 Add RED test: missing secret returns None and skips bootstrap.

### Domain D (GREEN)
- [x] 2.4 Implement `bootstrap_oci_private_key()` in `src/interface/cloud_secrets.py` using `mkstemp`, `os.chmod(0o600)`, `atexit` cleanup.
- [x] 2.5 Call `bootstrap_oci_private_key()` after `export_secrets_to_environ()` on module load.

## Phase 3: Core state persistence

### Domain B (RED)
- [x] 3.1 Add RED test: `_load_attended()` merges OCI + local state, local wins, and OCI failure falls back to local only.
- [x] 3.2 Add RED test: `set_atendido()` writes local mirror and best-effort OCI; OCI failure does not raise.
- [x] 3.3 Add RED test: fresh `session_state` restores persisted attended marks after reload.

### Domain B (GREEN)
- [x] 3.4 Add `OCIStorageClient` aliased import and `_ATTENDED_OCI_KEY` in `src/interface/app.py`.
- [x] 3.5 Refactor `_load_attended()` to OCI-first merge and `_save_attended()` to write-through OCI + local.
- [x] 3.6 Update `is_atendido()` / `set_atendido()` to cache and persist via the new helpers.

### Domain C (RED)
- [x] 3.7 Add RED test: `_candidate_key()` is stable for equal `autor + texto_original` and different otherwise.
- [x] 3.8 Add RED test: `load_curation()`/`set_curation()` round-trip an Aprobado decision per periodo.
- [x] 3.9 Add RED test: `Semana_04` decisions do not leak into `Semana_05`.
- [x] 3.10 Add RED test: OCI-less curation persists locally and keeps the dashboard working.

### Domain C (GREEN)
- [x] 3.11 Implement `_candidate_key()`, `_CURATION_OCI_KEY()`, `load_curation()`, `set_curation()` in `src/interface/state.py`.
- [x] 3.12 Stash `periodo_referencia` in `process_json_input()` and clear it in `reset_batch_state()`; add `_extract_periodo()` fallback.
- [x] 3.13 Seed LinkedIn/Newsletter/FAQ radio keys from persisted curation before rendering, and call `set_curation()` on change.

> **Module note (work unit `dominios-bc-estado-dashboard`)**: the persistence
> layer landed in a NEW module `src/interface/state.py` instead of
> `src/interface/app.py`. Reason: Streamlit executes a *copy* of `app.py`, so a
> seam patched on `src.interface.app` never reaches the running copy — the
> seams and helpers live in the imported module, which every copy shares.
> `src/interface/app.py` re-exports them through a module `__getattr__`
> (PEP 562) so the public surface did not change.

## Phase 4: Cleanup & documentation

- [x] 4.1 Update `docs/deploy-streamlit-cloud.md` with `OCI_PRIVATE_KEY` secret flow and 7-var readiness checklist.
- [x] 4.2 Update `.env.example` to document `OCI_PRIVATE_KEY` as an alternative to `OCI_PRIVATE_KEY_PATH`.
- [x] 4.3 Run full suite `venv/bin/python -m pytest tests/ -q` and fix regressions.
- [x] 4.4 Remove duplicated `_OCI_REQUIRED_ENV` constants from test files after importing the canonical one.

## Phase 5: Remediación de la auditoría del panel (post-implementación)

> **Origen**: auditoría del dashboard en local (2026-10-21), con la cadena
> `persistencia-oci-estado` ya publicada. Dos hallazgos: (a) la capa de estado
> ignora `OCI_BUCKET_NAME` y escribe siempre en el bucket hardcodeado — el
> design D2 ya lo define como la configuración canónica y `src/pipeline.py`
> lo respeta; (b) el aviso de "feedback negativo" afirma que TODAS las
> interacciones negativas se derivaron, cuando solo lo hacen las que superan
> el umbral de confianza de la regla R4.

- [x] 5.1 RED test: la capa de estado resuelve el bucket desde `OCI_BUCKET_NAME` cuando está definida, y cae a `DEFAULT_BUCKET` cuando no.
- [x] 5.2 GREEN: `src/interface/state.py` resuelve el bucket en tiempo de llamada; el fixture de tests neutraliza `OCI_BUCKET_NAME` para que un `.env` real no dirija las pruebas al bucket de producción.
- [x] 5.3 RED test: el aviso de "feedback negativo" informa cuántas interacciones se derivaron de verdad (y avisa cuando ninguna superó el umbral de R4).
- [x] 5.4 GREEN: `src/interface/app.py` reporta el conteo real de mensajes derivados junto con el total de feedback negativo.
