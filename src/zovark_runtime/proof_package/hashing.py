"""
hashing.py — SHA-256 helpers for Zovark Slice 001.

All hashing uses the canonical JSON serialization from canonical.py.
No third-party dependencies — uses hashlib from the Python standard library.
"""

from __future__ import annotations

import hashlib
from typing import Any

from zovark_runtime.proof_package.canonical import canonical_json


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def sha256_of_string(s: str) -> str:
    """Return the lowercase hex SHA-256 digest of *s* encoded as UTF-8."""
    return sha256_hex(s.encode("utf-8"))


def sha256_of_obj(obj: Any) -> str:
    """Return the lowercase hex SHA-256 digest of canonical_json(*obj*)."""
    return sha256_hex(canonical_json(obj))
