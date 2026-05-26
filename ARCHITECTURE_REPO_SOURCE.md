# Architecture Repo Source

Status: provenance note for the Phase 0 runtime skeleton.

## Source

- Source repository: `https://github.com/7inaydas-cmyk/zovark-architecture`
- Architecture source ref: `main`
- Architecture source tag: none for the current copied snapshot. The
  `v3.2.5.0-baseline-consolidated` tag predates the VerdictInput/ReplayRecord
  contract addition, the replay failure contract, and the replay compatibility
  row coverage contract.
- Architecture source commit:
  `5411106481dd843f754dc6a86f7371e1468610fc`

## Baseline Inventory

- 26 ADR files: 25 binding ADRs plus ADR-0043 proposed/pending founder
  sign-off.
- 39 invariants.
- 26 authoritative schemas.
- Replay compatibility contract:
  `architecture/replay-compatibility.yaml`.

## Copied Contracts

Only the following contracts were copied:

- `contracts/context-compaction-envelope-v1.schema.json`
- `contracts/finding.schema.json`
- `contracts/memory-retrieval-request-v1.schema.json`
- `contracts/memory-retrieval-result-v1.schema.json`
- `contracts/recommended_action.schema.json`
- `contracts/replay-compatibility.schema.json`
- `contracts/replay-compatibility.yaml`
- `contracts/replay_failure_record.schema.json`
- `contracts/replay_record.schema.json`
- `contracts/scanner_finding_envelope.schema.json`
- `contracts/verdict_envelope.schema.json`
- `contracts/verdict_input.schema.json`

They remain `draft-architecture-contract` material in this repository until
runtime enforcement exists with implementation, tests, and valid/invalid
fixtures.

## Boundary

This source note does not import adapter behavior, verifier behavior, generated
proof packages, fixtures, AlertForge integration, benchmarks, customer-readiness
material, signing, legal, or compliance scope.
