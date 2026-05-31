# Proof-package JSON Schemas (Slice 2)

Draft 2020-12 JSON Schemas for the **8 JSON** artifacts of the deterministic
proof package. The 9th artifact, `customer-report.md`, is Markdown and intentionally
has **no** JSON Schema.

| Artifact | Schema |
|---|---|
| `investigation-tape.json` | `investigation-tape.schema.json` |
| `evidence-ledger.json` | `evidence-ledger.schema.json` |
| `timeline.json` | `timeline.schema.json` |
| `findings.json` | `findings.schema.json` |
| `verdict.json` | `verdict.schema.json` |
| `edr-handoff.json` | `edr-handoff.schema.json` |
| `audit-chain-entry.json` | `audit-chain-entry.schema.json` |
| `replay-report.json` | `replay-report.schema.json` |

## Boundary: shape vs. semantics

These schemas check **artifact shape only** (presence, types, fixed protocol values,
id/hash/timestamp patterns, field-set closure). They are **not** a security boundary.

`proof-package-verify` remains the semantic boundary: it re-derives evidence hashes ->
findings FROM evidence -> verdict FROM findings and fails closed on mismatch. A
well-shaped but semantically-forged package (e.g. malicious evidence with findings
downgraded to a `benign` verdict) **passes these schemas but is rejected by the
verifier** — see `tests/test_proof_package_schemas.py::
test_semantic_forgery_passes_schema_but_verifier_rejects`. Schemas and the verifier are
verified to agree on genuine packages and to occupy distinct layers.

Verdict/action/severity enums describe the code's vocabulary
(`verdict.APPROVED_VERDICTS`, handoff action types, `findings._ALLOWED_SEVERITIES`).
Which values are actually *derivable* is a semantic property the verifier enforces, not
the shape schema.

## Provenance and authoring decision

- **Authored in `zovark-runtime`** (runtime-original), not in `zovark-architecture`.
  Rationale: architecture is the read-only canonical authority and was not authorized
  to change for this slice; the proof-package artifact contract is implemented and
  owned by the runtime generator today. Promotion of these schemas into the
  architecture authority is a future decision, out of scope for Slice 2.
- Derived from the deterministic generator's own validator field-sets in
  `src/zovark_runtime/proof_package/{tape,timeline,findings,verdict,handoff,audit,replay,writer}.py`
  at runtime `main` `83927ad8b86c5360f708a78413e8d5640b6392f2`.
- These schemas are **not** listed in `contracts/contract-manifest.json` (that manifest
  tracks architecture-vendored contracts with source-commit provenance); they live in
  this subdirectory so they are independent of the top-level architecture-snapshot
  contracts and their meta-validation test.

No network, no live LLM, no connectors. Deterministic generation and strict-verifier
semantics are unchanged by this slice.
