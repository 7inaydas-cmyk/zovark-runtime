#!/usr/bin/env python3
"""Phase 0 static check for unbounded model-context claims.

This is not runtime enforcement. It only checks that Phase 0 docs and contracts
keep the intended invariant visible and avoid obvious unbounded retrieval words
inside contract schemas.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = [
    ROOT / "contracts" / "context-compaction-envelope-v1.schema.json",
    ROOT / "contracts" / "memory-retrieval-request-v1.schema.json",
    ROOT / "contracts" / "memory-retrieval-result-v1.schema.json",
]
FORBIDDEN_SCHEMA_TOKENS = [
    '"all"',
    '"full"',
    '"unbounded"',
    '"unlimited"',
]


def main() -> int:
    invariant_text = (ROOT / "INVARIANTS.md").read_text(encoding="utf-8")
    if "No model receives unbounded raw tool output." not in invariant_text:
        raise SystemExit("missing no-unbounded-model-context invariant")

    for contract in CONTRACTS:
        text = contract.read_text(encoding="utf-8")
        for token in FORBIDDEN_SCHEMA_TOKENS:
            if token in text:
                raise SystemExit(f"{contract.relative_to(ROOT)} contains {token}")

    print("phase 0 unbounded model-context static check passed")
    print("note: this is not runtime enforcement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

