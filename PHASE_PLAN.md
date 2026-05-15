# Phase Plan

Status: planning document. It does not implement runtime behavior.

## Phase 0: Contracts And Invariants

- Snapshot architecture contracts.
- Record runtime invariants.
- Add manifest and invariant checks.
- Do not add runtime implementation.

## Phase 1: Single-Tenant Local Monolith Runtime Skeleton

Status: skeleton introduced; runtime behavior is not implemented.

- Add a minimal process layout for local execution.
- Keep storage and retrieval mocked or absent unless separately scoped.
- Preserve offline Replay boundaries.
- Expose deterministic status and doctor commands only.
- Do not implement investigation execution.

## Phase 2A: Context Compaction Memory Semantic Validators

Status: semantic validators introduced; storage and retrieval services are not
implemented.

- Validate range ordering and retrieval-result cross-field consistency.
- Keep validators standard-library only.
- Do not expose tool output to model context.
- Do not implement investigation_memory storage.
- Do not implement memory retrieval service.

## Phase 2B: Context Compaction Memory Lossless Storage

Status: lossless local storage substrate introduced; retrieval and model context
integration are not implemented.

Before Phase 2B implementation, run the architecture-query checklist in
`docs/architecture-query-checklist.md`.

Phase 2B should start as storage-only unless explicitly approved. Retrieval,
model-visible envelope/context integration, proof generation, AlertForge,
benchmarks, and customer-readiness remain separate later phases.

- Implement lossless investigation_memory storage.
- Preserve full content hashes, sizes, and source tool-call linkage.
- Do not expose stored tool output to model context.

## Phase 2C: Context Compaction Memory Bounded Retrieval

- Implement bounded, audited, capability-scoped retrieval.
- Keep failure results explicit and non-model-visible.

## Phase 2D: Deterministic Envelope And Model-Visible Context

- Enforce deterministic model-visible envelopes.
- Record exact ranges and byte counts for anything the model sees.

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
