# Proposal: persistencia-oci-estado

## Intent

Dashboard operational state is volatile: curation approve/reject decisions live only in Streamlit widget state and vanish on reload; attended derivations persist only to a local JSON lost on cloud redeploy or sleep. Persist both to OCI Object Storage with the local-fallback discipline `_store` already uses, so operator decisions survive sessions, redeploys, and machines.

## Scope

### In Scope
- `put_json`/`get_json` on `src/oci/storage.py:OCIStorage` (reuse `OCIClient`; never raise)
- Attended state: global — OCI object `estado/derivados-atendidos.json`, local fallback to the existing `storage/derivados-atendidos.json`
- Curation (LinkedIn/newsletter/FAQ approve/reject): per-batch — OCI object `estado/curacion-<periodo>.json`, keyed by a hash of `autor + texto_original` (never widget index)
- OCI-first state helpers in `src/interface/app.py` following `_store`'s fallback pattern; never raise to the UI
- PEM bootstrap: write the `OCI_PRIVATE_KEY` secret to a temp file at startup and point `OCI_PRIVATE_KEY_PATH` at it (the OCI SDK requires a file path, not a string)
- Update `docs/deploy-streamlit-cloud.md`; extend `tests/test_interface_app.py` and `tests/test_oci_integration.py`

### Out of Scope
- Local→OCI state migration beyond first-read merge
- Uploading the approved `payload_to_save`
- Changes to `_store` asset-package persistence
- Multi-operator locking/concurrency

## Capabilities

### New Capabilities
- `curacion-persistente`: per-batch curation decisions persisted to OCI by candidate identity hash, with local fallback
- `pem-oci-streamlit`: PEM secret materialized to a temp file at startup so OCI works on Streamlit Community Cloud

### Modified Capabilities
- `buzon-de-derivacion`: the "Session-state attended toggle" requirement becomes a globally persisted toggle (OCI first, local fallback) that survives reloads and machines

## Approach

Extend `OCIStorage` with `put_json`/`get_json`, aliasing the import (name collision with the `OCIStorage` Pydantic model in `src/domain/models.py`). Make `_load_attended`/`_save_attended` and the curation widgets OCI-first in `app.py`: reads try OCI → local → `session_state`; writes persist to OCI and mirror locally, cached via `session_state`. Bootstrap the PEM in the `cloud_secrets.py` flow. Validate the full credential set — `_oci_credentials_present()` ignores `OCI_BUCKET_NAME`/`OCI_NAMESPACE` today.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/oci/storage.py` | Modified | `put_json`/`get_json`; import aliasing |
| `src/interface/app.py` | Modified | OCI-backed state helpers; candidate hash keys |
| `src/interface/cloud_secrets.py` | Modified | PEM temp-file bootstrap |
| `docs/deploy-streamlit-cloud.md` | Modified | Document the secret flow |
| `tests/test_interface_app.py`, `tests/test_oci_integration.py` | Modified | Fallback, hash identity, PEM coverage |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `OCIStorage` class↔model name collision in shared imports | High | Alias at import (explore-flagged) |
| Temp PEM readable on shared cloud host | Low | Restrictive permissions; best-effort cleanup |
| Widget-index→hash switch orphans old curation state | Medium | Accept: pre-change state was session-only |
| OCI latency on each toggle slows the panel | Medium | `session_state` write-through; best-effort calls |

## Rollback Plan

Revert the commits; the app returns to today's local-only behavior. OCI `estado/` objects are inert and removable from the bucket; no data migration ran.

## Dependencies

- OCI env vars, including `OCI_BUCKET_NAME` and `OCI_NAMESPACE` (today's check omits both)
- Streamlit secret `OCI_PRIVATE_KEY` (PEM content) on Community Cloud

## Success Criteria

- [ ] Attended derivations survive reload and a second machine via `estado/derivados-atendidos.json`
- [ ] Curation decisions round-trip via `estado/curacion-<periodo>.json` keyed by `autor+texto_original` hash
- [ ] With OCI unavailable (no creds/SDK/network), the dashboard works fully via local files, no UI exceptions
- [ ] On Streamlit Cloud with `OCI_PRIVATE_KEY` set, OCI state works without a manual PEM file
- [ ] Tests cover fallback paths, hash identity, and PEM bootstrap
