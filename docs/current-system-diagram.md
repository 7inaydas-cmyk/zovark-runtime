# Current System Diagram

Status: visual documentation only. These diagrams do not implement runtime
behavior.

## Diagram A: Current Implemented State

```mermaid
flowchart TD
    R[zovark-runtime]
    R --> P0[Implemented<br/>Phase 0 contracts and invariants]
    R --> P1[Implemented<br/>Phase 1 local Monolith skeleton]
    R --> P2A[Implemented<br/>Phase 2A semantic validators]
    R --> P2B[Implemented<br/>Phase 2B lossless storage substrate]

    R -. not implemented .-> RET[Bounded retrieval service]
    R -. not implemented .-> ENV[Deterministic envelope generation]
    R -. not implemented .-> RUN[Planner executor assessor runtime]
    R -. not implemented .-> PROOF[Runtime proof generation]
    R -. not implemented .-> AF[AlertForge ingest]
    R -. not implemented .-> BENCH[Benchmarks]
    R -. not implemented .-> CUST[Customer readiness and outreach]
```

## Diagram B: Future Runtime Data Flow

```mermaid
flowchart LR
    AF[Planned<br/>AlertForge scenario source] --> ING[Planned<br/>runtime ingest]
    ING --> PLAN[Planned<br/>planner]
    PLAN --> EXEC[Planned<br/>executor]
    EXEC --> MEM[Planned<br/>investigation_memory]
    EXEC --> ASSESS[Planned<br/>assessor]
    MEM --> ENV[Planned<br/>deterministic envelope]
    ENV --> MODEL[Planned<br/>model-visible context]
    MEM --> PROOF[Planned<br/>proof package]
    PROOF --> REPLAY[Planned<br/>offline Replay]
```

All nodes in this diagram are future planned runtime behavior, not current
implementation.

## Diagram C: Context Compaction Memory Lifecycle

```mermaid
flowchart LR
    TOOL[Tool output] --> STORE[Future storage<br/>lossless investigation_memory]
    STORE --> REF[memory_ref_id]
    REF --> ENV[Future deterministic envelope]
    ENV --> MODEL[Future bounded model-visible context]
    REF --> REQ[Future bounded retrieval request]
    REQ --> RES[Future audited retrieval result]
    RES --> PROOF[Future proof and Replay record]
```

Phase 2B implements only the storage portion. Retrieval, envelope generation,
model-visible context, and proof/Replay recording remain later phases.

## Diagram D: Blocked Downstream Items

```mermaid
flowchart TD
    AF[Blocked until contract<br/>AlertForge integration] --> VAL[Blocked<br/>synthetic validation]
    VAL --> BENCH[Blocked<br/>benchmarks]
    BENCH --> READY[Blocked<br/>customer readiness]
    READY --> OUT[Blocked<br/>outreach]

    LIVE[Forbidden until later<br/>live integrations]
    SIGN[Forbidden until later<br/>signing anchoring SLSA in-toto]
    CLAIMS[Forbidden until evidence<br/>legal compliance production claims]
```

These items remain blocked or forbidden until separately scoped, implemented,
tested, and reviewed.
