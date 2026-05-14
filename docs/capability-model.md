# Capability Model

Status: future Phase 2 scope.

No capability enforcement exists in Phase 0.

Future retrieval must require explicit capabilities. Retrieval requests must be
auditable and must not permit unbounded reads such as `all`, `full`, or
unlimited ranges.

Capability-scoped retrieval must preserve deterministic replay by recording the
request, result metadata, ranges, hashes, and model-visible envelope.

