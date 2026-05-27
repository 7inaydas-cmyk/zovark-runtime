from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
PROOF_CHAIN_RUNTIME = ROOT / "proof_chain" / "runtime"
REPLAY_COMPATIBILITY_MATRIX = CONTRACTS / "replay-compatibility.yaml"
SATISFIED_CHECKLIST = PROOF_CHAIN_RUNTIME / "satisfied_checklist.json"
COVERAGE_REGISTRY = PROOF_CHAIN_RUNTIME / "replay_compatibility_coverage.json"
REPLAY_VALIDATION_TEST = ROOT / "tests" / "test_replay_validation.py"
REPLAY_FAILURE_MAPPING_TEST = ROOT / "tests" / "test_replay_failure_mapping.py"
REPLAY_COMPATIBILITY_MAPPING_TEST = ROOT / "tests" / "test_replay_compatibility_mapping.py"

EXPECTED_EVIDENCE_KEYS = {
    "fail_closed",
    "canonical_code_mapping",
    "failure_record_emission",
    "row_mapping",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_matrix() -> dict[str, Any]:
    matrix = yaml.safe_load(REPLAY_COMPATIBILITY_MATRIX.read_text(encoding="utf-8"))
    assert isinstance(matrix, dict)
    return matrix


def _failure_outcome_rows() -> list[dict[str, Any]]:
    rows = _load_matrix()["failure_outcome_rows"]
    assert isinstance(rows, list)
    return rows


def _coverage_registry() -> dict[str, Any]:
    registry = _load_json(COVERAGE_REGISTRY)
    assert registry["proof_marker"] == "REPLAY_COMPATIBILITY_MATRIX_COVERAGE_OK"
    assert registry["declared_rows_source"] == "contracts/replay-compatibility.yaml::failure_outcome_rows"
    assert registry["covered_rows_source"] == "proof_chain/runtime/replay_compatibility_coverage.json::rows"
    assert set(registry["common_evidence"]) == EXPECTED_EVIDENCE_KEYS
    return registry


def _coverage_registry_rows() -> list[dict[str, Any]]:
    rows = _coverage_registry()["rows"]
    assert isinstance(rows, list)
    return rows


def _declared_row_code_map(rows: list[dict[str, Any]] | None = None) -> dict[str, str]:
    row_code_map: dict[str, str] = {}
    for row in rows or _failure_outcome_rows():
        row_id = row["row_id"]
        failure_codes = row["failure_codes"]
        assert isinstance(row_id, str)
        assert isinstance(failure_codes, list)
        assert len(failure_codes) == 1
        assert row_id not in row_code_map
        row_code_map[row_id] = failure_codes[0]
    return row_code_map


def _covered_row_map(rows: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    covered: dict[str, dict[str, Any]] = {}
    for row in rows or _coverage_registry_rows():
        row_id = row["row_id"]
        assert isinstance(row_id, str)
        assert row_id not in covered
        covered[row_id] = row
    return covered


def _assert_coverage_sets_equal(
    declared_rows: dict[str, str],
    covered_rows: dict[str, dict[str, Any]],
) -> None:
    missing_rows = set(declared_rows) - set(covered_rows)
    extra_rows = set(covered_rows) - set(declared_rows)
    assert not missing_rows, f"missing coverage rows: {sorted(missing_rows)}"
    assert not extra_rows, f"undeclared coverage rows: {sorted(extra_rows)}"


def _fail_closed_case_ids() -> set[str]:
    module = _load_module(REPLAY_VALIDATION_TEST, "zovark_runtime_replay_validation_cases_for_coverage")
    return {case["id"] for case in module.REPLAY_VALIDATION_FAIL_CLOSED_CASES}


def _expected_canonical_codes_by_case_id() -> dict[str, str]:
    module = _load_module(REPLAY_FAILURE_MAPPING_TEST, "zovark_runtime_replay_failure_mapping_cases_for_coverage")
    return dict(module.EXPECTED_CANONICAL_CODES_BY_CASE_ID)


def _expected_row_ids_by_case_id() -> dict[str, str]:
    module = _load_module(REPLAY_COMPATIBILITY_MAPPING_TEST, "zovark_runtime_replay_compatibility_rows_for_coverage")
    return dict(module.EXPECTED_ROW_ID_BY_CASE_ID)


def _satisfied_marker_items() -> dict[str, dict[str, Any]]:
    checklist = _load_json(SATISFIED_CHECKLIST)["items"]
    return {item["proof_marker"]: item for item in checklist}


def _assert_evidence_handle(
    *,
    row: dict[str, Any],
    evidence_key: str,
    marker_items: dict[str, dict[str, Any]],
) -> None:
    evidence = row["evidence"][evidence_key]
    marker = evidence["marker"]
    path = evidence["path"]

    assert marker in marker_items
    assert (ROOT / path).is_file()

    marker_item = marker_items[marker]
    marker_paths = {
        marker_item.get("test_file_path"),
        marker_item.get("yaml_artifact_path"),
        marker_item.get("schema_artifact_path"),
    }
    marker_paths.update(marker_item.get("related_test_file_paths", []))
    marker_paths.update(marker_item.get("runtime_artifact_paths", []))
    marker_paths.update(marker_item.get("contract_paths", []))
    assert path in marker_paths


def test_replay_compatibility_matrix_coverage_matches_declared_rows() -> None:
    declared_rows = _declared_row_code_map()
    covered_rows = _covered_row_map()
    fail_closed_case_ids = _fail_closed_case_ids()
    canonical_codes_by_case_id = _expected_canonical_codes_by_case_id()
    row_ids_by_case_id = _expected_row_ids_by_case_id()
    marker_items = _satisfied_marker_items()
    common_evidence = _coverage_registry()["common_evidence"]

    _assert_coverage_sets_equal(declared_rows, covered_rows)

    for row_id, coverage_row in covered_rows.items():
        coverage_row_with_evidence = {**coverage_row, "evidence": common_evidence}
        assert coverage_row["failure_code"] == declared_rows[row_id]
        for evidence_key in EXPECTED_EVIDENCE_KEYS:
            _assert_evidence_handle(
                row=coverage_row_with_evidence,
                evidence_key=evidence_key,
                marker_items=marker_items,
            )

        fail_closed_cases = coverage_row["fail_closed_case_ids"]
        assert isinstance(fail_closed_cases, list)
        assert fail_closed_cases
        for case_id in fail_closed_cases:
            assert case_id in fail_closed_case_ids
            assert canonical_codes_by_case_id[case_id] == coverage_row["failure_code"]
            assert row_ids_by_case_id[case_id] == row_id

        for supplemental_marker in coverage_row.get("supplemental_markers", []):
            assert supplemental_marker in marker_items

    assert covered_rows["tool_compatibility.tool_retired"]["failure_code"] == "REPLAY_TOOL_RETIRED"

    print("REPLAY_COMPATIBILITY_MATRIX_COVERAGE_OK")


def test_coverage_gate_fails_when_yaml_declares_uncovered_row() -> None:
    declared_rows = _declared_row_code_map(
        [
            *_failure_outcome_rows(),
            {
                "row_id": "synthetic_coverage.synthetic_new_row",
                "compatibility_dimension": "synthetic_coverage",
                "component": "synthetic_component",
                "failure_codes": ["REPLAY_SYNTHETIC_UNCOVERED"],
                "outcome": "fail_closed",
                "runtime_evidence_required": ["canonical_replay_failure_record", "failure_code"],
            },
        ]
    )

    with pytest.raises(AssertionError, match="missing coverage rows"):
        _assert_coverage_sets_equal(declared_rows, _covered_row_map())


def test_coverage_gate_fails_when_evidence_omits_declared_row() -> None:
    coverage_rows = [
        row
        for row in _coverage_registry_rows()
        if row["row_id"] != "tool_compatibility.tool_retired"
    ]

    with pytest.raises(AssertionError, match="missing coverage rows"):
        _assert_coverage_sets_equal(_declared_row_code_map(), _covered_row_map(coverage_rows))


def test_coverage_gate_fails_when_evidence_names_undeclared_row() -> None:
    coverage_rows = [
        *_coverage_registry_rows(),
        {
            "fail_closed_case_ids": ["schema_version_incompatible"],
            "failure_code": "REPLAY_SCHEMA_INCOMPATIBLE",
            "row_id": "synthetic_coverage.undeclared_row",
        },
    ]

    with pytest.raises(AssertionError, match="undeclared coverage rows"):
        _assert_coverage_sets_equal(_declared_row_code_map(), _covered_row_map(coverage_rows))
