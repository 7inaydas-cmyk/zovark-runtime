# Runtime Architecture Implementation Map

Status: documentation map only. This document does not implement storage,
retrieval, model context integration, proof generation, AlertForge integration,
benchmarks, customer-readiness, OCSF, RamaLama, signing, legal, or compliance
scope.

## Architecture Sources

This map is based on:

- `7inaydas-cmyk/zovark-architecture` tag
  `arch-v4.1-runtime-phase0`, commit
  `0f4582267ac2a63a90d4c218ad442765785ca63b`.
- Runtime repository `7inaydas-cmyk/zovark-runtime` main commit
  `40b5ced0df9e17d5826e75cd2f940f0a83cffda6`.
- Architecture files:
  - `docs/architecture-current-state.md`
  - `docs/context-compaction-memory.md`
  - `docs/contract-governance.md`
  - `contracts/README.md`
  - `docs/adr-status-table.md`
- Runtime files:
  - `README.md`
  - `PHASE_PLAN.md`
  - `INVARIANTS.md`
  - `ARCHITECTURE_REPO_SOURCE.md`

## Current Implementation State

| Area | State | Notes |
| --- | --- | --- |
| Phase 0 contracts/invariants | implemented | Contract snapshot, manifest check, and invariant text exist. |
| Phase 1 local Monolith skeleton | implemented | Status and doctor commands only. |
| Phase 2A semantic validators | implemented | In-memory semantic validation helpers only. |
| Phase 2B lossless storage | not implemented | No `investigation_memory` storage exists. |
| Bounded retrieval | not implemented | No retrieval service or retrieval execution exists. |
| Deterministic envelope generation | not implemented | Contracts exist; runtime envelope generation does not. |
| Runtime investigation planner/executor/assessor | not implemented | No investigation execution exists. |
| Proof generation from runtime state | not implemented | No runtime proof package generation exists. |
| AlertForge contract/ingest | not implemented | AlertForge remains future upstream scenario source. |
| Benchmarks | not implemented | No benchmark harness or claims exist. |
| Customer-readiness/outreach | not implemented | Outreach remains blocked until evidence-backed readiness. |
| OCSF implementation | not implemented | OCSF is not canonical and has no mapper or ingest path. |
| RamaLama/local inference implementation | not implemented | No live LLM or local inference integration exists. |

## Repository Relationship

```mermaid
flowchart TD
    A[zovark-architecture<br/>reference proof governance repo] --> B[architecture baseline tag<br/>arch-v4.1-runtime-phase0]
    B --> C[zovark-runtime<br/>runtime repo]

    C --> P0[Phase 0 implemented<br/>contracts and invariants]
    C --> P1[Phase 1 implemented<br/>local Monolith skeleton]
    C --> P2A[Phase 2A implemented<br/>semantic validators]

    C -. future .-> P2B[Phase 2B planned<br/>lossless storage]
    P2B -. future .-> P2C[Phase 2C planned<br/>bounded retrieval]
    P2C -. future .-> P2D[Phase 2D planned<br/>deterministic envelopes and model-visible context]
    P2D -. future .-> P3[Phase 3 planned<br/>runtime proof generation]
    P3 -. future .-> P4[Phase 4 planned<br/>AlertForge contract and ingest]
    P4 -. future .-> P5[Phase 5 planned<br/>synthetic validation]
    P5 -. future .-> P6[Phase 6 planned<br/>benchmarks]
    P6 -. future .-> P7[Phase 7 planned<br/>customer readiness]
```

## Future Runtime Data Flow

```mermaid
flowchart LR
    AF[AlertForge future scenario source] -. future .-> ING[Runtime ingest future]
    ING -. future .-> PLAN[Planner future]
    PLAN -. future .-> EXEC[Executor future]
    EXEC -. future .-> ASSESS[Assessor future]
    EXEC -. future .-> MEM[investigation_memory future]
    MEM -. future .-> ENV[Model-visible envelope future]
    ENV -. future .-> MODEL[Model context future]
    MEM -. future .-> PROOF[Proof package future]
    PROOF -. future .-> REPLAY[Offline Replay future]
```

This diagram is a target flow. It is not implemented today.

## Phase Boundaries

Phase 2B should start as lossless storage only unless a later PR explicitly
approves more scope. Bounded retrieval, deterministic envelope/model-visible
context, runtime proof generation, AlertForge ingest, synthetic validation,
benchmarks, and customer-readiness remain separate later phases.

The Context Compaction Memory invariant remains:

```text
No model receives unbounded raw tool output.
```

This document is a map, not implementation.
