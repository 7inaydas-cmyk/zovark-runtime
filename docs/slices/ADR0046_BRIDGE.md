# ADR-0046 bridge — relationship between the two contracts

This documents how the proof-package contract and the ADR-0046 verdict contract relate.
**No silent divergence.**

## Two distinct contracts
- **Proof-package contract** (slice001 9-artifact): a deterministic, rule-derived
  verdict (`verdict.json.value`, e.g. `confirmed_malicious`), authoritative and enforced
  by `proof-package-verify` (full-chain re-derivation, fail-closed). Unchanged by Slice 3.
- **ADR-0046 contract** (`verdict_input` → `verdict_envelope`, `replay_record`):
  served by `verdict_derivation.derive_verdict` and
  `replay_validation.validate_replay_record`. In this repo today `derive_verdict` is a
  **proof-fixture stub** that always emits `verdict_class="indeterminate"`,
  `confidence_basis_points=0`, `recommended_actions=[]` regardless of evidence.

## What the bridge does (additive, non-lossy)
`proof_package/adr0046_bridge.py` maps a proof-package tape into a schema-valid
`verdict_input`, runs the existing `derive_verdict` to get a `verdict_envelope`, builds a
`replay_record`, and confirms `validate_replay_record` accepts it (offline, hash-based,
fail-closed). It carries the authoritative proof-package verdict into `bridge.json`
(`proof_package_verdict`). Artifacts are written to a **separate** directory and are
never part of the canonical 9-artifact package.

## What the bridge deliberately does NOT do
- It does **not** map the slice001 rule verdict into ADR-0046 `verdict_class`. The
  emitted class is the stub's `indeterminate`; it is **not** the proof-package verdict
  and must never be read as such.
- It does **not** change `proof-package-verify`, `derive_verdict`, generation bytes, or
  the verdict vocabulary.
- It does **not** reconcile or pick a winner between the contracts (that would require an
  authority change → would be a DECISION_NEEDED stop; it is not needed here).

## No-model honesty
The proof package is deterministic and rule-only — no model/tool/db ran. The bridge
represents this honestly: ADR-0046 investigation-I/O arrays (`tool_results`,
`llm_records`, `db_results`, `llm_io`, `tool_io`, `db_snapshots`) are **empty**. The
required scalar model/tool fields (`model_version`, `decoding_params`, `prompt_hash`,
`tool_catalog_version`, `model_id`) carry documented no-model placeholders; they describe
the absence of a model run, not a real model invocation.

## Future work (not this slice)
A real ADR-0046 classifier (one that emits a meaningful `verdict_class`) is out of scope.
If/when it exists, the relationship between it and the slice001 rule verdict will need an
explicit, recorded product decision.
