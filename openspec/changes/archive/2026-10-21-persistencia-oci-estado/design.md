# Design: persistencia-oci-estado

## Technical Approach

Extend `_store`'s proven OCI-first/local-fallback discipline (`src/pipeline.py`) to dashboard operational state: `OCIStorage` gains never-raising `put_json`/`get_json`; `app.py` state helpers become OCI-first with local mirrors cached in `session_state`; `cloud_secrets.py` materializes the PEM secret into a 0600 temp file at import. Implements spec `sdd/persistencia-oci-estado/spec`, domains A–D.

## Architecture Decisions

| # | Decision | Options (tradeoff) | Choice + rationale |
|---|----------|--------------------|--------------------|
| D1 | Client init in `OCIStorage` | eager (construction raises ImportError without SDK) vs lazy | Lazy cached `client` property — construction never raises, methods degrade; `test_connection_and_upload` untouched |
| D2 | Credential-check home | extend pipeline's `_OCI_REQUIRED_ENV` (already duplicated in 3 test files) vs canonical home | `OCI_REQUIRED_ENV` + `oci_credentials_complete()` in `src/oci/storage.py`; pipeline `_oci_credentials_present()` delegates; 7 vars: existing 5 + `OCI_BUCKET_NAME` + `OCI_NAMESPACE` |
| D3 | `OCIStorage` class↔model collision | alias at import | `from src.oci.storage import OCIStorage as OCIStorageClient` in the NEW `src/interface/state.py`; `src/domain/models.py` untouched |
| D4 | Read/write policy | read-through only vs write-through + first-read merge | Write-through: `session_state` + local mirror + OCI best-effort. Read: merge OCI+local (local wins — it only diverged while OCI was down on this machine), merged result re-put to OCI (the in-scope first-read merge). No timestamps → cross-machine conflicts out of scope |
| D9 | Where the persistence layer lives | inside `app.py` vs a shared module | NEW `src/interface/state.py`. Streamlit executes a *copy* of `app.py` (both `streamlit` and `AppTest`), so a seam patched on `src.interface.app` never reaches the running copy. The imported module is shared by every copy, so its seams are read at call time and always agree. `app.py` re-exports the public names through a module `__getattr__` (PEP 562) |
| D10 | Merge granularity of the curation file | whole document vs per channel and per candidate | Per channel AND per candidate (`{**oci[canal], **local[canal]}`). A whole-channel overwrite silently drops the decisions the other store still holds — the local mirror would erase an OCI approval and vice versa |
| D5 | Object granularity | per key (N+1 list calls) vs per state kind | Whole-dict JSON: `estado/derivados-atendidos.json`, `estado/curacion-<periodo>.json`; same shape as local mirrors |
| D6 | Curation identity | widget index (orphaned on reload) vs content hash | `sha1(f"{autor}\n{texto_original}").hexdigest()[:12]` — repo's stable-id convention (`_consolidate_derived`); `\n` avoids concatenation ambiguity. FAQ theme (no single author): `sha1(tema)[:12]` |
| D7 | `<periodo>` source | today's week vs batch envelope | `process_json_input(content, session_state=None)` stashes `periodo_referencia` into `session_state`; `reset_batch_state` clears it. Fallback: parse `almacenamiento_oci.ruta_objeto` (`activos/<p>/`) → current ISO week |
| D8 | PEM bootstrap placement | `app.py` main vs `cloud_secrets.py` import | `bootstrap_oci_private_key()` after `export_secrets_to_environ()` (app.py import order already guarantees it runs before `src.pipeline`/`src.oci`); `mkstemp` 0600, set `OCI_PRIVATE_KEY_PATH`, atexit best-effort unlink; no content validation — invalid PEM degrades via the OCI-unavailable path |

## Data Flow

    radio/checkbox → session_state (cache) → local mirror (storage/*.json)
                          └→ put_json → OCI estado/*.json
    load: get_json → merge local → session_state → seed widget key → st.radio

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/oci/storage.py` | Modify | Lazy client; `put_json`/`get_json`; `OCI_REQUIRED_ENV`, `oci_credentials_complete()`, `DEFAULT_BUCKET` |
| `src/pipeline.py` | Modify | `_oci_credentials_present()` delegates; imports `DEFAULT_BUCKET`/`oci_credentials_complete` |
| `src/interface/state.py` | New | Shared persistence layer: seams (`ATTENDED_PATH`, `CURATION_STATE_DIR`, `OCIStorageClient`, `DEFAULT_BUCKET`); OCI-first `_load_attended`/`_save_attended`; `_candidate_key`/`_faq_key`; `load_curation`/`set_curation`; `_extract_periodo`/`_current_periodo` |
| `src/interface/app.py` | Modify | Imports the shared layer and re-exports it via module `__getattr__`; `build_derivados_entries` reads the persisted attended state; `_curation_radio` seeds + persists the 3 curation sites; `_candidate_curation_key`; `process_json_input(content, session_state=None)` stashes `periodo_referencia`; `reset_batch_state` clears it |
| `src/interface/cloud_secrets.py` | Modify | `bootstrap_oci_private_key()` |
| `docs/deploy-streamlit-cloud.md` | Modify | `OCI_PRIVATE_KEY` secret flow; 7-var readiness |
| `tests/test_oci_integration.py` | Modify | Domain A unit tests (fakes) + real-cred round-trip |
| `tests/test_interface_app.py` | Modify | Domains B, C |
| `tests/test_interface_cloud_secrets.py` | Modify | Domain D |
| `tests/test_webhook.py`, `tests/test_csv_loader.py`, `tests/test_bot.py` | Modify | Import canonical `OCI_REQUIRED_ENV` (drift removal) |

## Interfaces / Contracts

```python
class OCIStorage:
    def put_json(self, bucket_name: str, key: str, data) -> bool   # never raises
    def get_json(self, bucket_name: str, key: str, default=None)   # never raises

def oci_credentials_complete() -> bool   # 7 env vars non-empty
DEFAULT_BUCKET = "communitylab-activos-marketing"

# src/interface/state.py (re-exported by app.py through module __getattr__)
def _candidate_key(autor, texto_original) -> str
def _faq_key(tema) -> str
def load_curation(session_state, periodo) -> dict    # {"linkedin": {key: estado}, "newsletter": {...}, "faq": {tema_key: estado}}
def set_curation(session_state, periodo, canal, key, estado) -> None
def is_atendido(session_state, message_id) -> bool
def set_atendido(session_state, message_id, value) -> None

# src/interface/app.py
def process_json_input(content, session_state=None)   # stashes periodo_referencia when given
def _curation_radio(canal, candidate_key, widget_key, periodo) -> str

# cloud_secrets.py
def bootstrap_oci_private_key() -> str | None
```

Widget seeding pattern (must seed BEFORE render — keyed widgets ignore `index=` after first render):

```python
saved = load_curation(st.session_state, periodo).get(canal, {}).get(candidate_key)
if saved and widget_key not in st.session_state:
    st.session_state[widget_key] = saved          # seed BEFORE the widget exists
estado = st.radio(..., key=widget_key)
if estado != (saved or CURATION_STATUS_PENDING):
    set_curation(st.session_state, periodo, canal, candidate_key, estado)
```

## Testing Strategy (strict TDD — RED first per domain, then green)

| Domain | RED tests (written first, fail before implementation) | Green via |
|--------|------------------------------------------------------|-----------|
| A OCI JSON storage | fake `OCIClient` with in-memory object store: round-trip; missing key → default; corrupt JSON → default; ImportError → no raise; `oci_credentials_complete`: `OCI_BUCKET_NAME` empty → False, all 7 → True | `put_json`/`get_json`, lazy client |
| B Buzón | `_load_attended` OCI-first merge; OCI down → local only; both corrupt → `{}`; `set_atendido` writes mirror + OCI; OCI put fails → local written, no raise; fresh `session_state` restores persisted marks (reload simulation) | attended helpers |
| C Curación | `_candidate_key` stable across indexes (same autor/texto → same key; different → different); Aprobado round-trip; `curacion-Semana_04` vs `-Semana_05` isolation; OCI-less local fallback; saved status seeds widget key before radio | curation helpers + seeding |
| D PEM | bootstrap: temp file with exact content, mode 0600, `OCI_PRIVATE_KEY_PATH` set; pre-set path → no file created, path untouched; no secret → no-op, returns None | `bootstrap_oci_private_key()` |

Order: A → D (independent) → B → C (B/C reuse A's primitives). CI stays network-free: fakes via `OCIStorage(oci_client=...)` and `monkeypatch.setattr(state, "OCIStorageClient", ...)` — the seam lives in the shared module (D9), so patching `app` would not reach the running copy; the real-bucket test keeps its `skipif`.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The temp PEM file is 0600, non-executable, best-effort cleaned at exit.

## Migration / Rollout

No data migration. Behavior change: OCI readiness now requires `OCI_BUCKET_NAME` + `OCI_NAMESPACE`; without them `_store` and dashboard state degrade to local snapshots — document in `docs/deploy-streamlit-cloud.md` and `.env.example`. Pre-change curation state was session-only; nothing to migrate.

## Open Questions

- [ ] `<periodo>` format: raw input stamp (`Semana_04`, per spec examples) vs normalized asset folder (`2026-semana-04`). Design uses the raw stamp; sample-loaded batches may resolve to the normalized form via the fallback chain.
