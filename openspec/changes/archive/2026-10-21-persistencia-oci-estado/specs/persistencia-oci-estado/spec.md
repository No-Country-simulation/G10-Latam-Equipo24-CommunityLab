# Delta Specs: persistencia-oci-estado

## ADDED Requirements

### Requirement: OCIStorage JSON operations

`OCIStorage` MUST expose `put_json(bucket, key, data)` and `get_json(bucket, key, default=None)` that round-trip JSON objects through OCI without raising.

#### Scenario: Round-trip

- GIVEN valid OCI credentials and bucket
- WHEN `put_json` writes a dict and `get_json` reads the same key
- THEN the returned value SHALL equal the original dict

#### Scenario: Missing object returns default

- GIVEN a key absent from OCI
- WHEN `get_json` is called with default `{}`
- THEN it SHALL return `{}` without raising

#### Scenario: OCI unavailable degrades silently

- GIVEN the SDK is missing or credentials are absent
- WHEN `put_json` or `get_json` is called
- THEN the methods SHALL return gracefully without raising

### Requirement: Full credential validation

OCI readiness MUST check `OCI_BUCKET_NAME` and `OCI_NAMESPACE` with the existing five env vars.

#### Scenario: Incomplete credentials disable OCI

- GIVEN `OCI_BUCKET_NAME` is empty and other credentials are present
- WHEN the dashboard checks OCI readiness
- THEN it SHALL treat OCI as unavailable and fall back locally

## MODIFIED Requirements

### Requirement: Globally persisted attended toggle

Each listed derivation SHALL have an "atendido" toggle persisted globally (OCI first, local fallback) and cached in `st.session_state`.
(Previously: toggle was stored only in `st.session_state` and reset on reload.)

#### Scenario: Toggle persists across reload

- GIVEN OCI is configured and the "Derivados" tab is open
- WHEN the operator marks a derived message as attended
- THEN the system SHALL write `estado/derivados-atendidos.json` to OCI and mirror locally
- AND remain checked after reload

#### Scenario: Toggle without OCI

- GIVEN OCI credentials or SDK are missing
- WHEN the operator toggles "atendido"
- THEN the system SHALL write only the local file

#### Scenario: Corrupt state degrades gracefully

- GIVEN the OCI object or local file is unreadable/corrupt
- WHEN the dashboard loads or saves attended state
- THEN it SHALL treat the state as empty

## ADDED Requirements

### Requirement: Per-batch curation decisions by candidate identity

The dashboard SHALL persist LinkedIn, newsletter and FAQ decisions per batch to `estado/curacion-<periodo>.json`, keyed by a stable hash of `autor + texto_original`, with local fallback.

#### Scenario: Approval round-trips

- GIVEN a candidate with known `autor` and `texto_original`
- WHEN the operator sets its status to "Aprobado"
- THEN the decision SHALL save to the batch file and reload as Aprobado

#### Scenario: Candidate identity is stable

- GIVEN the same candidate appears at a different widget index after reload
- WHEN its curation state is loaded
- THEN the decision SHALL bind to the `autor + texto_original` hash

#### Scenario: Per-batch isolation

- GIVEN decisions exist for `Semana_04`
- WHEN the operator opens `Semana_05`
- THEN the system SHALL load `estado/curacion-Semana_05.json` without leaking `Semana_04`

#### Scenario: OCI-less curation works locally

- GIVEN OCI is unavailable
- WHEN the operator approves a candidate
- THEN the decision SHALL save to a local fallback file and the dashboard SHALL continue without errors

## ADDED Requirements

### Requirement: PEM secret materialized to temp file

When `OCI_PRIVATE_KEY` is present and `OCI_PRIVATE_KEY_PATH` is absent, startup SHALL write the PEM content to a temporary file with owner-only permissions and set `OCI_PRIVATE_KEY_PATH` to that path.

#### Scenario: Streamlit Cloud bootstrap

- GIVEN the app runs on Streamlit Cloud with `OCI_PRIVATE_KEY` populated
- WHEN `src.interface.cloud_secrets` loads
- THEN it SHALL create a temp PEM file, set `OCI_PRIVATE_KEY_PATH`, and OCI auth succeeds

#### Scenario: Local path takes precedence

- GIVEN `OCI_PRIVATE_KEY_PATH` already points to a file
- WHEN `OCI_PRIVATE_KEY` is also present
- THEN the system SHALL NOT overwrite the path or create a temp file

#### Scenario: Missing secret skips bootstrap

- GIVEN neither PEM secret nor path is set
- WHEN the module loads
- THEN it SHALL skip bootstrap and OCI SHALL fall back locally
