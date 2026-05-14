# Runtime Invariants

Status: Phase 0 architecture invariants. These are not runtime enforcement yet.

1. No model receives unbounded raw tool output.
2. Oversized tool output is stored losslessly before model exposure.
3. Model-visible context is deterministic envelope plus memory_ref_id.
4. Retrieval is bounded, audited, and capability-scoped.
5. Proof packages record hashes, sizes, ranges, and retrieval refs.
6. No LLM summarization as canonical compaction.
7. V1 proof package shape is preserved.
8. V2 is additive and explicit.
9. Replay never calls live systems.
10. Customer outreach is gated on benchmark-backed evidence.

## Phase 0 Scope

These invariants define the minimum safety boundary for later implementation.
Phase 0 does not implement storage, retrieval, planner/executor/assessor
runtime behavior, sandbox execution, AlertForge ingest, benchmarks, or customer
workflow.

## Phase 1 Skeleton Scope

The Phase 1 local monolith skeleton reports status only. It still does not
enforce runtime behavior, execute investigations, store investigation memory,
retrieve memory ranges, import AlertForge scenarios, run benchmarks, or create
customer-facing artifacts.

## Phase 2A Semantic Validator Scope

Phase 2A adds Context Compaction Memory semantic validators only. These
validators check data structures in memory. They still do not store
investigation_memory, retrieve memory ranges from storage, place tool output in
model context, generate proof packages from runtime state, import AlertForge
scenarios, run benchmarks, or create customer-facing artifacts.
