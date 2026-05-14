# Local Monolith Runtime

Status: future Phase 1 scope.

The local monolith runtime does not exist yet. Phase 1 may introduce a minimal
single-tenant process layout for local development, but it must not silently add
AlertForge integration, benchmark harnesses, live integrations, or customer
workflow.

The monolith must preserve:

- offline Replay;
- V1 proof package compatibility;
- explicit V2 proof package generation;
- bounded model-visible context; and
- no live system calls unless explicitly scoped.

