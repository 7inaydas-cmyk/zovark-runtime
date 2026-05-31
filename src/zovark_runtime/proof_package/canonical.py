"""
canonical.py — Canonical JSON serialization for Zovark Slice 001.

Produces compact, key-sorted, UTF-8 bytes suitable for deterministic hashing.
Rules match the replay-and-audit spec exactly:

1. Object keys sorted lexicographically (Unicode code point order).
2. Strings UTF-8 encoded.
3. Numbers: integers or finite decimals; NaN and Infinity are rejected.
4. Timestamps are plain strings — ISO-8601 with Z passes through unchanged.
5. Booleans: lowercase true / false.
6. Null: null.
7. Arrays: insertion order preserved.
8. No trailing whitespace. Compact (no pretty-printing).

Two compliant implementations produce byte-identical output for the same
logical object.
"""

from __future__ import annotations

import json
import math
from typing import Any


def canonical_json(obj: Any) -> bytes:
    """Return compact, key-sorted, UTF-8 canonical JSON bytes of *obj*.

    Raises ValueError if *obj* contains NaN or Infinity at any depth.
    """
    return _serialize(obj).encode("utf-8")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> str:
    """Recursively serialize *obj* to a canonical JSON string."""
    if obj is None:
        return "null"

    if isinstance(obj, bool):
        # Must come before int check — bool is a subclass of int in Python.
        return "true" if obj else "false"

    if isinstance(obj, int):
        return str(obj)

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise ValueError(
                f"canonical_json: NaN and Infinity are not allowed; got {obj!r}"
            )
        # Represent as a decimal string.  json.dumps handles finite floats
        # correctly (no trailing zeros beyond what Python produces).
        return json.dumps(obj)

    if isinstance(obj, str):
        # Use json.dumps for correct escaping; it produces double-quoted UTF-8.
        return json.dumps(obj, ensure_ascii=False)

    if isinstance(obj, (list, tuple)):
        # Arrays: preserve insertion order.
        items = ",".join(_serialize(item) for item in obj)
        return f"[{items}]"

    if isinstance(obj, dict):
        # Keys must be strings (JSON requirement).
        # Sort lexicographically by Unicode code point (Python's default str sort).
        pairs = ",".join(
            f"{json.dumps(k, ensure_ascii=False)}:{_serialize(v)}"
            for k, v in sorted(obj.items())
        )
        return "{" + pairs + "}"

    raise TypeError(
        f"canonical_json: unsupported type {type(obj).__name__!r} for value {obj!r}"
    )
