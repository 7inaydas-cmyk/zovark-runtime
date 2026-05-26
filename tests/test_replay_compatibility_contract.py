from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest


jsonschema = pytest.importorskip("jsonschema")
yaml = pytest.importorskip("yaml")
validator_for = jsonschema.validators.validator_for

try:
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except Exception:  # pragma: no cover - exercised only on older local jsonschema stacks.
    Registry = None
    Resource = None
    DRAFT202012 = None


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
REPLAY_COMPATIBILITY_MATRIX = CONTRACTS / "replay-compatibility.yaml"
REPLAY_COMPATIBILITY_SCHEMA = CONTRACTS / "replay-compatibility.schema.json"


def _load_schema() -> dict:
    return json.loads(REPLAY_COMPATIBILITY_SCHEMA.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_store() -> dict[str, dict]:
    schemas: dict[str, dict] = {}
    for schema_path in sorted(CONTRACTS.glob("*.schema.json")):
        schema = _load_json(schema_path)
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            schemas[schema_id.split("#", 1)[0]] = schema
    return schemas


def _contract_registry():
    assert Registry is not None
    assert Resource is not None
    assert DRAFT202012 is not None

    registry = Registry()
    for schema_id, schema in _contract_store().items():
        resource = Resource.from_contents(schema, default_specification=DRAFT202012)
        registry = registry.with_resource(schema_id, resource)
    return registry


def _validator():
    schema = _load_schema()
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)

    if Registry is not None:
        return validator_cls(schema, registry=_contract_registry())

    resolver = jsonschema.validators.RefResolver.from_schema(schema, store=_contract_store())
    return validator_cls(schema, resolver=resolver)


def _load_matrix() -> dict:
    matrix = yaml.safe_load(REPLAY_COMPATIBILITY_MATRIX.read_text(encoding="utf-8"))
    assert isinstance(matrix, dict)
    return matrix


def _failure_code_enum() -> tuple[str, ...]:
    schema = _contract_store()["https://schemas.zovark.io/replay_failure_record/v1.0.0/schema.json"]
    return tuple(schema["$defs"]["ReplayFailureCode"]["enum"])


def test_replay_compatibility_matrix_validates_against_canonical_schema() -> None:
    _validator().validate(_load_matrix())

    print("REPLAY_COMPATIBILITY_MATRIX_SCHEMA_OK")


def test_replay_compatibility_row_coverage_contract_validates_against_canonical_schema() -> None:
    validator = _validator()
    matrix = _load_matrix()
    failure_codes = _failure_code_enum()

    validator.validate(matrix)

    rows = matrix.get("failure_outcome_rows")
    assert isinstance(rows, list)
    assert rows

    row_ids = [row["row_id"] for row in rows]
    assert len(row_ids) == len(set(row_ids))

    row_failure_codes = [code for row in rows for code in row["failure_codes"]]
    assert matrix["structured_failure_codes"] == list(failure_codes)
    assert set(row_failure_codes) == set(failure_codes)
    assert len(row_failure_codes) == len(set(row_failure_codes)) == len(failure_codes)

    rendered = json.dumps(matrix)
    assert "REPLAY_COMPATIBILITY_MATRIX_COVERAGE_OK" not in rendered
    for row in rows:
        assert row["outcome"] == "fail_closed"
        assert row["failure_codes"]
        assert "canonical_replay_failure_record" in row["runtime_evidence_required"]
        assert "runtime_coverage_claim" not in row

    row_with_extra_field = copy.deepcopy(matrix)
    row_with_extra_field["failure_outcome_rows"][0]["runtime_coverage_claim"] = True
    if hasattr(validator, "iter_errors"):
        assert list(validator.iter_errors(row_with_extra_field))
    else:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(row_with_extra_field)

    row_with_unknown_code = copy.deepcopy(matrix)
    row_with_unknown_code["failure_outcome_rows"][0]["failure_codes"] = ["REPLAY_RUNTIME_LOCAL_ONLY"]
    if hasattr(validator, "iter_errors"):
        assert list(validator.iter_errors(row_with_unknown_code))
    else:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(row_with_unknown_code)

    print("REPLAY_COMPATIBILITY_ROW_COVERAGE_SCHEMA_OK")
