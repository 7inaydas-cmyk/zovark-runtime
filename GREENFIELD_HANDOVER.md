# Greenfield Handover

Status: Phase 0 handover note.

This repository starts after the architecture/reference repository established
the proof-package, Replay, Context Compaction Memory, and governance baseline.
It is intentionally greenfield: no runtime implementation is carried over.

## Carry Forward

- Proof Package V1 must remain stable.
- Proof Package V2 must be additive and explicit.
- Replay must remain offline.
- Context Compaction Memory must prevent unbounded raw tool output from entering
  model context.
- Architecture contracts copied into `contracts/` are draft architecture
  contracts until runtime enforcement exists.

## Do Not Carry Forward As Runtime

- Reference adapter behavior from the architecture repo.
- Reference verifier behavior as an implementation dependency.
- Static fixture generation as production runtime behavior.
- Any customer-readiness, benchmark, legal, signing, or compliance implication.

## Next Work

The next step after Phase 0 is a single-tenant local monolith runtime skeleton.
That future PR must remain scoped and must not silently implement
investigation_memory storage, AlertForge ingest, benchmarks, or live
integrations.

