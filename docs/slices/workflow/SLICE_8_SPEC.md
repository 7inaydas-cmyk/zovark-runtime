# SLICE 8 — runtime-enforced schemas + proof-loop status

Target branch: `slices-5-8-staging` (**STAGE ONLY — do not merge to main**).
Commit message: `feat(slice8): runtime schema enforcement and proof-loop status`

## Goal
Move schema enforcement from tests-only to runtime boundaries **without** replacing
semantic verification.

## Acceptance
- Runtime enforces the relevant contract schemas (the 8 `contracts/proof_package/`
  schemas from Slice 2), not just in tests.
- Schema enforcement is **fail-closed**.
- Schemas never replace `proof-package-verify`. Verification still re-derives evidence →
  findings → verdict; a shape-valid semantic forgery is still rejected.
- If ADR-0053 / `runtime_proof_loop` authority is present and its criteria are met,
  `proof-status` may reflect it **without weakening semantics**. If that authority is
  absent or unclear, **do not invent it** — document the deferment as FAIL-SAFE.
- No false proof-complete status.
- All Phase-0 checks + full suite remain green.
- `proof-package-verify` remains the semantic authority.

## Implementation guidance
- Scout the Slice-2 schemas, existing schema-validation helpers, and `proof_status.py` /
  any ADR-0053 authority in `zovark-architecture` (read-only — do not modify it).
- Add runtime validation at safe boundaries: after artifact generation; before verifier
  success; before emitting final proof-status (if applicable).
- Do not let schemas replace full-chain re-derivation. Do not emit a false complete
  proof-status.

## Tests
- Runtime rejects a schema-invalid emitted artifact (fail-closed).
- Verifier still rejects a shape-valid semantic forgery.
- `proof-status` reports complete only when all authoritative criteria pass.
- Missing/unclear ADR-0053 authority does not produce a false complete status.
- Full suite green; generation deterministic unless explicitly documented.

## Independent audit
- Create a schema-valid semantic forgery → verifier must reject. Create a schema-invalid
  artifact → runtime must fail closed. Try to get `proof-status` complete without the
  required criteria → must fail. Confirm schema validity never masks verifier rejection.
