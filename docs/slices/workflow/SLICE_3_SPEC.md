# SLICE 3 — ADR-0046 verdict-contract bridge

Target branch: `main` (mergeable if green + audited).
Commit message: `feat(slice3): ADR-0046 verdict-contract bridge`

## Goal
Bridge the proof-package tape to the ADR-0046 verdict contract **without weakening
either contract**. Additive, non-lossy mapping only.

## Acceptance
- Document the mapping from proof-package tape → `verdict_input`.
- Emit/derive a `verdict_envelope` that validates against the repo's actual
  `contracts/verdict_envelope.schema.json` / validator.
- Emit/derive a `replay_record` compatible with the repo's actual
  `validate_replay_record` path (`src/zovark_runtime/replay_validation.py`).
- `validate_replay_record` runs offline, hash-based, fail-closed, and passes on the
  conformant output.
- A tampered `replay_record` fails closed.
- A tampered/forged `verdict_envelope` fails closed if a validator exists.
- Determinism preserved: two runs byte-identical, with committed hashes.
- A clear doc statement explains the relationship between the proof-package contract
  (slice001 9-artifact) and the ADR-0046 contract (verdict_input/envelope/replay_record).
- `proof-package-verify` remains authoritative and **unchanged**.

## Implementation guidance
- Scout the actual names first: `derive_verdict`, `validate_replay_record`,
  `verdict_envelope`/`verdict_input`/`replay_record` schemas, proof-package tape shape.
- Prefer an **additive bridge module/artifact** (e.g. `proof_package/adr0046_bridge.py`)
  + an optional emitted artifact; reuse existing derivation/validation code paths.
- Do not modify verifier semantics. Do not change proof-package output bytes.
- Do not silently pick one contract over another if semantics conflict.

## HARD STOP (T2)
If proof-package and ADR-0046 contracts genuinely conflict and reconciliation requires
changing semantic authority, write `docs/slices/DECISION_NEEDED.md` and STOP. Do not pick
a winner. Build only a purely additive, non-lossy mapping.

## Tests
- Canonical proof package → `verdict_input` → `verdict_envelope` validates.
- `replay_record` validates offline.
- Tampered `replay_record` fails closed.
- Tampered `verdict_envelope` fails closed where a validator exists.
- Two runs byte-identical.
- `proof-package-verify` still passes the conformant package and still rejects a
  shape-valid semantic forgery.

## Independent audit
- Try to make a forged `verdict_envelope` validate; try to make a tampered
  `replay_record` pass. Confirm `derive_verdict`/`proof-package-verify` not weakened.
  Flag any silent contract-semantics change as DANGEROUS-DIRECTION.
