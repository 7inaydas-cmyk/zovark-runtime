# Context Compaction Memory

Status: Phase 2A semantic validator note.

The core invariant is: no model receives unbounded raw tool output.

Oversized or high-volume tool output must be stored losslessly in future
investigation_memory before model exposure. The model may receive only a
deterministic bounded envelope plus a `memory_ref_id`.

Retrieval must be bounded, audited, and capability-scoped. A retrieval result
must record returned ranges, returned byte counts, hashes, and whether the
content was model-visible.

LLM summarization is not canonical compaction. Any future summary may be an
analysis artifact, but the canonical compacted view is deterministic and
range-bound.

Phase 2A adds semantic validators for ranges and retrieval-result objects. The
validators check bounded range semantics and retrieval-result consistency in
memory only.

Storage and retrieval services still do not exist. These validators are not
runtime storage or retrieval enforcement. No model receives tool output through
these validators yet. Runtime proof-package generation does not exist yet.
AlertForge integration does not exist yet. Benchmarks and customer-readiness do
not exist yet.
