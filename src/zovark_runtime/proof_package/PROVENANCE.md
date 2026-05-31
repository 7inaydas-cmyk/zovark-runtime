# Provenance — vendored proof-package pipeline

The deterministic derivation modules in this package
(`canonical, hashing, ingest, tape, timeline, findings, verdict, handoff, audit,
replay, writer, package_verifier`, and the `ZovarkValidationError` in `__init__`)
were vendored verbatim from the architecture authority repo's reference pipeline:

- Source repo: `7inaydas-cmyk/zovark-architecture`
- Source path: `zovark/slice001/`
- Architecture `main` commit at copy time: `d16935bd354b0e55984b7548e2ce4cca3385feea`
- Transform applied: import path `zovark.slice001` → `zovark_runtime.proof_package`
  (no logic changes).

Only the stdlib-only, deterministic modules were vendored. `cli.py`,
`local_testbed.py`, and `v3_adapter.py` were intentionally **not** vendored.

`pipeline.py` (orchestration + `investigation_memory` recording/verification +
fail-closed input loader + output symlink guard) and `verify.py` (strict offline
verification that re-derives findings from evidence — closing a dangerous-direction
gap in the vendored `package_verifier`, see DESIGN.md §2) are **runtime-original**
and are **not** vendored. They are layered on top of the verbatim vendored modules,
so the vendored code stays byte-identical to the oracle source.

Rationale and the full design reconciliation are in `/DESIGN.md` (§3). Vendoring
is read-only on architecture: the source was copied, never modified.

Conformance to the architecture oracle is proven byte-for-byte in `/CONFORMANCE.md`.
