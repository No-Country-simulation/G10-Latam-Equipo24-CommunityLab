# Archive Report: persistencia-oci-estado

**Change**: `persistencia-oci-estado`
**Archived to**: `openspec/changes/archive/2026-10-21-persistencia-oci-estado/`
**Artifact store**: openspec
**Archived on**: 2026-10-21
**Verdict at close**: PASS (5/5 requirements, 14/14 scenarios, 534 tests passed)

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `persistencia-oci-estado` | Created | The delta spec had no main spec, so it was copied mechanically as the full spec: 5 requirements (3 added, 1 modified, 1 added) and 14 scenarios. |

Main source of truth now: `openspec/specs/persistencia-oci-estado/spec.md`

## Archive Contents

- `proposal.md` ✅
- `specs/persistencia-oci-estado/spec.md` ✅
- `design.md` ✅
- `tasks.md` ✅ (34/34 tasks complete, 0 unchecked)
- `apply-progress.md` ✅
- `verify-report.md` ✅ (`gentle-ai.verify-result/v1`, verdict `pass`, admitted by
  `gentle-ai sdd-verify-validate --requirements 5 --scenarios 14` → `{"valid": true}`)
- `state.yaml` ✅

## Mechanical Copy Evidence

Every copy and move used a native shell command, never a model Read → Write round-trip.

```
$ diff -r openspec/changes/persistencia-oci-estado/specs/persistencia-oci-estado/spec.md <temp>
(no output — empty diff)

$ diff -r <snapshot>/source openspec/changes/archive/2026-10-21-persistencia-oci-estado
(no output — empty diff)
```

Both readbacks were empty, which is the only passing evidence of byte-identity. The source directory no
longer exists under `openspec/changes/`.

## Gates Checked Before Archiving

| Gate | Result |
|---|---|
| Task Completion Gate | ✅ 34/34 tasks checked in `tasks.md`, 0 unchecked |
| Native Review Receipt Gate | ✅ `reviewGate` structurally absent — no review was ever started for this candidate, so archive proceeds under ordinary repository policy (kill switch off) |
| Action Context Guard | ✅ `mode: repo-local`, `allowedEditRoots` = the repository root; all archive operations stayed inside it |
| Verification gate | ✅ no CRITICAL findings; blockers 0, critical findings 0 |

## Final State at Close

Facts below are the state at close, not a snapshot of an earlier phase.

- **Implementation**: 5 requirements delivered across 4 work units, split into the stacked PR chain
  #167 → #168 → #169 → #170 (Domains A, D, B+C, docs/readiness + audit remediation), each with
  conventional commits and green CI.
- **Behavior fixes landed after the intermediate snapshots**: the audit work unit resolved the OCI bucket
  from `OCI_BUCKET_NAME` at call time and made the negative-feedback notice report the real derived count
  instead of the total negative count.
- **Documentation**: `docs/deploy-streamlit-cloud.md` documents the inline `OCI_PRIVATE_KEY` secret flow,
  a 7-variable readiness checklist, and two new troubleshooting cases; `.env.example` documents
  `OCI_PRIVATE_KEY` as an alternative to `OCI_PRIVATE_KEY_PATH`.
- **Contract decisions recorded**: `docs/DECISIONS.md` D-I now states the R4 confidence gate
  (`negative_confidence > 0.8`) and clarifies that `feedback_negativo` and `mensajes_derivados` are two
  distinct populations; `docs/decisiones-contrato.md` gained entry D-K for the additive
  `DistributionAssets` fields `mensajes_derivados` and `temas_faq`.
- **Tests**: 534 passed, 0 failed, 0 skipped (`venv/bin/python -m pytest tests/ -q`, exit 0). The two
  pydantic `UserWarning`s about the `copy` field name are pre-existing and out of scope.
- **Static check**: `venv/bin/flake8 src tests scripts` exit 0, no findings.
- **Runtime ledger**: attempts 1–9 settled; the final verification attempt (ordinal 9) settled as
  `complete` with `evidence_revision sha256:e3b0c442…` (the verification run changed no source file).
- **Open, external to this change**: the PR chain still needs human approvals from a CODEOWNER
  (`@emanuelperacchia` or `@itanflores`; the PR author cannot approve their own PR) before it can land
  on `main`, which requires linear history and therefore squash merges.

## SDD Cycle Complete

The change was planned, implemented, verified and archived. The active changes directory is empty and
`openspec/specs/persistencia-oci-estado/spec.md` is the source of truth for this behavior.
