# SLICE 3 PLAN — ADR-0046 verdict-contract bridge

## State (re-derived)
main `274fcf4`, clean, baseline green (combined `8749bf8a…`, verify verified/0/true).

## T2 (contract-conflict) analysis — NOT a blocker
The two contracts measure different things:
- **proof-package** verdict = `confirmed_malicious`, rule-derived, authoritative for the
  proof package, enforced by `proof-package-verify`.
- **ADR-0046** `verdict_derivation.derive_verdict` is, in this repo today, a *proof-fixture
  stub*: it always emits `verdict_class="indeterminate"`, `confidence_basis_points=0`,
  `recommended_actions=[]` regardless of evidence. It does NOT encode the slice001 rule
  verdict.

NEXT_SLICES Slice 3 acceptance asks for a *documented mapping* + a valid `verdict_envelope`
+ working `replay_record` validation + a *clear statement of how the two contracts relate
— no silent divergence*. It does **not** ask me to make the ADR-0046 class equal the
proof-package verdict. Building the bridge does **not** require changing any semantic
authority (proof-package-verify, derive_verdict, the verdict vocabulary are all left
untouched). Therefore this is **not** the T2 "must pick a winner" case. Divergence is
expected and is documented, not reconciled.

Anti-DANGEROUS-DIRECTION guard: the ADR-0046 "indeterminate" envelope must never be
presented as the authoritative verdict for a malicious package. Mitigations:
1. The bridge artifacts are emitted to a **separate** output dir, never added to the
   canonical 9-artifact package → `main` proof-package bytes unchanged (no T10).
2. The emitted bridge carries the authoritative proof-package verdict as a labeled
   reference (`bridge.json`), so the real verdict is non-lossy.
3. The bridge module docstring + `docs/slices/ADR0046_BRIDGE.md` state plainly that
   ADR-0046 derive_verdict is a fixture stub and the slice001 rule verdict is authoritative.

## Smallest change
- New module `src/zovark_runtime/proof_package/adr0046_bridge.py` (additive; reuses
  `verdict_derivation.derive_verdict`, `replay_validation.validate_replay_record`, and
  their canonical hash helpers — NO new verdict/verifier engine):
  - `tape_to_verdict_input(tape) -> dict` — deterministic mapping; derives UUID-format
    tenant/investigation ids from the tape via the existing deterministic-uuid helper;
    investigation I/O arrays empty (no model/tool/db was used — honest); decoding_params
    = no-model defaults (`seed_policy="no_seed"`); validates against
    `contracts/verdict_input.schema.json`.
  - `build_replay_record(verdict_input, verdict_envelope) -> dict` — deterministic;
    hashes via the repo's canonical helpers; `failure_policy="fail_closed"`.
  - `build_bridge(package_dir) -> {verdict_input, verdict_envelope, replay_record,
    proof_package_verdict}` — reads a generated package's tape, runs derive_verdict +
    validate_replay_record, returns all four (labeled).
- CLI: `adr0046-bridge --package <dir> --output <dir>` emits `verdict_input.json`,
  `verdict_envelope.json`, `replay_record.json`, `bridge.json` to a separate dir.
- Reuse the known-good minimal fixtures' structure for schema-valid construction.

## Tests (fail-closed first)
- tape → verdict_input validates against verdict_input schema.
- verdict_envelope (derive_verdict) validates against verdict_envelope schema.
- build replay_record → validate_replay_record `ok=True` offline.
- tamper replay_record (e.g. verdict_input_hash) → `ok=False` (fail closed).
- tamper verdict_envelope (then rebuild record hash from the tampered one vs expected) →
  validate_replay_record fails on VERDICT_ENVELOPE_HASH_MISMATCH.
- two bridge runs byte-identical (committed hashes).
- proof-package-verify still passes the canonical package and still rejects a forgery;
  canonical 9-artifact combined hash unchanged (`8749bf8a…`).

## Merge
Slice 3 may merge to `main` after green + self-audit + independent audit (zero
DANGEROUS-DIRECTION). Bridge artifacts are NOT part of the canonical package.
