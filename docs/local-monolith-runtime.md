# Local Monolith Runtime

Status: Phase 1 skeleton introduced.

The local monolith runtime skeleton exists for deterministic status and doctor
commands only. It is a single-tenant local target, not an investigation runtime.

The skeleton currently provides:

- deterministic local config defaults;
- `zovark-runtime status`;
- `zovark-runtime doctor`; and
- explicit planned/not-implemented component reporting.

Phase 2B adds lossless local `investigation_memory` storage substrate status.
The monolith still does not read alerts, retrieve memory, expose model context,
write proof packages, call live systems, create customer artifacts, or generate
runtime investigation output.

The Phase 1 skeleton must not silently add AlertForge integration, benchmark
harnesses, live integrations, or customer workflow.

The monolith must preserve:

- offline Replay;
- V1 proof package compatibility;
- explicit V2 proof package generation;
- bounded model-visible context; and
- no live system calls unless explicitly scoped.

## Not Implemented

- investigation runtime;
- planner runtime;
- executor runtime;
- assessor runtime;
- memory retrieval;
- model context integration;
- proof-package generation from runtime investigations;
- AlertForge ingest;
- benchmarks;
- customer-readiness; and
- outreach workflow.
