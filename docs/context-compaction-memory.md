# Context Compaction Memory

Status: Phase 0 architecture note.

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

Phase 0 does not implement memory storage or retrieval.

