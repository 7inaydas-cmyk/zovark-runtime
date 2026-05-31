# Role: REPO SCOUT (read-only)

You inspect the repo and report facts. You make **no** product-code changes. Cheap/fast
model is fine. Multiple scouts may run in parallel (cap 8).

For the current slice, read and report (with exact file paths + line numbers + quoted
signatures — never paraphrase a contract):
- `NEXT_SLICES.md` (the slice's acceptance criteria).
- CLI patterns: `src/zovark_runtime/cli.py` (subcommands, arg parsing, exit codes).
- Generator path: `src/zovark_runtime/proof_package/{ingest,tape,timeline,findings,verdict,handoff,audit,replay,writer,pipeline}.py` — exact function names, field-set constants, enums.
- Verifier: `proof_package/package_verifier.py` + `proof_package/verify.py` (the
  semantic boundary; do not propose changes that weaken it).
- ADR-0046 contract assets (Slice 3): `src/zovark_runtime/verdict_derivation.py`
  (`derive_verdict`), `src/zovark_runtime/replay_validation.py`
  (`validate_replay_record`), `contracts/verdict_envelope.schema.json`,
  `contracts/verdict_input.schema.json`, `contracts/replay_record.schema.json`.
- investigation_memory store (Slices 5/7): `src/zovark_runtime/investigation_memory/`.
- Schemas (Slice 8): `contracts/proof_package/*.schema.json`, validator helpers, the
  3 Phase-0 check scripts, CI workflow.
- Fixtures + tests: `tests/fixtures/`, `tests/test_proof_package_*.py`.

Output: `docs/slices/workflow/SCOUT_REPORT.md` (overwrite/append per slice, clearly
sectioned by slice number). Include only verified facts; flag anything ambiguous as an
explicit "UNKNOWN — needs verification" item rather than guessing.
