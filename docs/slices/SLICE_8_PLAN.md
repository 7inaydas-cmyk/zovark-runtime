# SLICE 8 PLAN — runtime schema enforcement + proof-status (STAGING)

## Constraint
The runtime is zero-dependency (jsonschema is test-only). So runtime schema enforcement
uses a small **dependency-free** validator covering exactly the JSON Schema constructs the
8 `contracts/proof_package/` schemas use (type, required, properties,
additionalProperties:false, enum, const, pattern, minItems, items, minimum, minLength,
local `$ref`/`$defs`).

## Change
- `proof_package/schema_enforce.py`: dependency-free validator +
  `enforce_proof_package_schemas(package_dir)` → validates all 8 JSON artifacts against
  their schemas; raises `ZovarkValidationError` (fail-closed) on any violation.
- Wire as a fail-closed gate:
  - `pipeline.run_proof_package` — after writing artifacts (a schema-invalid emitted
    artifact aborts).
  - `verify.verify_proof_package_strict` — schema gate runs in addition to (NOT instead of)
    the vendored re-derivation + findings re-derivation. **Schemas are
    necessary-not-sufficient; `proof-package-verify` re-derivation remains the semantic
    authority.** A shape-valid semantic forgery is still rejected by re-derivation.
- proof-status: ADR-0053 / `runtime_proof_loop` completion authority is NOT present in
  runtime (proof_status reports `runtime_proof_loop: incomplete`). Slice 8 does NOT invent
  completion authority; the deferment is documented as FAIL-SAFE. No false complete status.

## Tests
- The dependency-free validator accepts the canonical 8 artifacts; rejects mutations
  (missing required, wrong type, extra key, bad enum/const/pattern).
- Runtime rejects a schema-invalid emitted artifact (fail-closed) via verify.
- Verifier still rejects a shape-valid semantic forgery (necessary-not-sufficient).
- The dependency-free validator agrees with jsonschema on the canonical artifacts (parity).
- proof-status never reports `runtime_proof_loop: complete` (authority absent).
- Generation remains deterministic; canonical staging hash unchanged (enforcement is a gate,
  not a generation change).

## Stage only; main untouched.
