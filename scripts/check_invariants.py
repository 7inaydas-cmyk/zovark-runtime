#!/usr/bin/env python3
"""Verify required Phase 0 invariant text is present."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVARIANTS = ROOT / "INVARIANTS.md"

REQUIRED_PHRASES = [
    "No model receives unbounded raw tool output.",
    "Oversized tool output is stored losslessly before model exposure.",
    "Model-visible context is deterministic envelope plus memory_ref_id.",
    "Retrieval is bounded, audited, and capability-scoped.",
    "Proof packages record hashes, sizes, ranges, and retrieval refs.",
    "No LLM summarization as canonical compaction.",
    "V1 proof package shape is preserved.",
    "V2 is additive and explicit.",
    "Replay never calls live systems.",
    "Customer outreach is gated on benchmark-backed evidence.",
]


def main() -> int:
    text = INVARIANTS.read_text(encoding="utf-8")
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
    if missing:
        raise SystemExit("missing invariant phrases: " + ", ".join(missing))
    print("invariant text check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

