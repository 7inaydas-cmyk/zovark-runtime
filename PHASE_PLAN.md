# Phase Plan

Status: planning document. It does not implement runtime behavior.

## Phase 0: Contracts And Invariants

- Snapshot architecture contracts.
- Record runtime invariants.
- Add manifest and invariant checks.
- Do not add runtime implementation.

## Phase 1: Single-Tenant Local Monolith Runtime Skeleton

- Add a minimal process layout for local execution.
- Keep storage and retrieval mocked or absent unless separately scoped.
- Preserve offline Replay boundaries.

## Phase 2: Context Compaction Memory Storage And Retrieval

- Implement lossless investigation_memory storage.
- Implement bounded, audited, capability-scoped retrieval.
- Enforce deterministic model-visible envelopes.

## Phase 3: Proof Package Generation From Runtime Investigation

- Generate proof packages from runtime investigation state.
- Preserve V1 shape.
- Keep V2 additive and explicit.

## Phase 4: AlertForge Contract And Ingest

- Define the AlertForge output contract.
- Reject unsafe fields before ingestion.
- Keep AlertForge as an upstream synthetic alert/scenario generator.

## Phase 5: End-To-End Synthetic Validation

- Run synthetic alert workflows through the local runtime.
- Verify proof-package output with offline Replay.
- Keep validation deterministic.

## Phase 6: Benchmarks

- Add benchmark harness only after end-to-end validation exists.
- No benchmark claim is allowed without benchmark evidence.

## Phase 7: Customer-Readiness

- Customer-readiness begins only after benchmark-backed evidence exists.
- Outreach remains blocked until evidence-backed readiness exists.

