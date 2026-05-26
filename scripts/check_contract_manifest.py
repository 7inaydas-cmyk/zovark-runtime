#!/usr/bin/env python3
"""Validate the Phase 0 contract snapshot manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "contracts" / "contract-manifest.json"
VALID_KINDS = {"schema", "data-artifact"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if manifest.get("status") != "draft-architecture-contract":
        raise SystemExit("manifest status must be draft-architecture-contract")

    for entry in manifest.get("contracts", []):
        rel_path = entry.get("path")
        expected_hash = entry.get("sha256")
        status = entry.get("status")
        kind = entry.get("kind")
        source_commit = entry.get("source_commit")
        if not rel_path or not expected_hash:
            raise SystemExit("contract entries must include path and sha256")
        if status != "draft-architecture-contract":
            raise SystemExit(f"{rel_path}: status must be draft-architecture-contract")
        if kind is not None and kind not in VALID_KINDS:
            raise SystemExit(f"{rel_path}: kind must be one of {sorted(VALID_KINDS)}")
        if source_commit is not None:
            if not isinstance(source_commit, str) or len(source_commit) != 40:
                raise SystemExit(f"{rel_path}: source_commit must be a 40-character commit SHA")
            try:
                int(source_commit, 16)
            except ValueError as exc:
                raise SystemExit(f"{rel_path}: source_commit must be hex") from exc

        path = ROOT / rel_path
        if not path.is_file():
            raise SystemExit(f"{rel_path}: missing")
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise SystemExit(
                f"{rel_path}: sha256 mismatch; expected {expected_hash}, got {actual_hash}"
            )

    print("contract manifest check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
