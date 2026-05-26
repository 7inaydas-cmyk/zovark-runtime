from __future__ import annotations

import json
from pathlib import Path

import pytest


jsonschema = pytest.importorskip("jsonschema")
yaml = pytest.importorskip("yaml")
validator_for = jsonschema.validators.validator_for


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
REPLAY_COMPATIBILITY_MATRIX = CONTRACTS / "replay-compatibility.yaml"
REPLAY_COMPATIBILITY_SCHEMA = CONTRACTS / "replay-compatibility.schema.json"


def _load_schema() -> dict:
    return json.loads(REPLAY_COMPATIBILITY_SCHEMA.read_text(encoding="utf-8"))


def test_replay_compatibility_matrix_validates_against_canonical_schema() -> None:
    schema = _load_schema()
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)

    matrix = yaml.safe_load(REPLAY_COMPATIBILITY_MATRIX.read_text(encoding="utf-8"))
    validator_cls(schema).validate(matrix)

    print("REPLAY_COMPATIBILITY_MATRIX_SCHEMA_OK")
