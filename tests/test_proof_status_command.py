from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from zovark_runtime import proof_status
from zovark_runtime.cli import main
from zovark_runtime.proof_status import LocalCheckResult


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"

EXPECTED_PROOF_CHAIN_MARKERS = {
    "SCANNER_FIXTURE_SCHEMA_OK",
    "VERDICT_FIXTURE_SCHEMA_OK",
    "VERDICT_INPUT_FIXTURE_SCHEMA_OK",
    "REPLAY_RECORD_FIXTURE_SCHEMA_OK",
    "DETERMINISTIC_VERDICT_DERIVATION_OK",
    "REPLAY_VALIDATION_PROOF_OK",
    "REPLAY_VALIDATION_FAIL_CLOSED_CASES_OK",
    "REPLAY_COMPATIBILITY_MATRIX_SCHEMA_OK",
    "REPLAY_COMPATIBILITY_ROW_COVERAGE_SCHEMA_OK",
    "REPLAY_FAILURE_RECORD_SCHEMA_OK",
    "REPLAY_FAILURE_RECORD_FIXTURE_SCHEMA_OK",
    "REPLAY_FAILURE_CANONICAL_CODE_MAPPING_OK",
    "REPLAY_FAILURE_RECORD_EMISSION_OK",
    "REPLAY_COMPATIBILITY_MATRIX_ROW_MAPPING_OK",
    "REPLAY_DECODING_PARAMS_FAIL_CLOSED_OK",
    "CONTRACT_METASCHEMA_OK",
}

ARCHITECTURE_SOURCE_COMMIT = "5411106481dd843f754dc6a86f7371e1468610fc"
REPLAY_FAILURE_CONTRACT_SOURCE_COMMIT = "34c42ebb24b69098159ddccbbcae981d0abe74af"
REPLAY_COMPATIBILITY_YAML = "contracts/replay-compatibility.yaml"
REPLAY_COMPATIBILITY_SCHEMA = "contracts/replay-compatibility.schema.json"
REPLAY_FAILURE_RECORD_SCHEMA = "contracts/replay_failure_record.schema.json"
REPLAY_FAILURE_RECORD_FIXTURE = "tests/fixtures/replay_failure_record_minimal.json"
REPLAY_FAILURE_MAPPING_MODULE = "src/zovark_runtime/replay_failure_mapping.py"
REPLAY_FAILURE_RECORDING_MODULE = "src/zovark_runtime/replay_failure_recording.py"
REPLAY_COMPATIBILITY_MAPPING_MODULE = "src/zovark_runtime/replay_compatibility_mapping.py"
REPLAY_VALIDATION_TEST = "tests/test_replay_validation.py"
REPLAY_FAILURE_MAPPING_TEST = "tests/test_replay_failure_mapping.py"
REPLAY_FAILURE_RECORDING_TEST = "tests/test_replay_failure_recording.py"
REPLAY_COMPATIBILITY_MAPPING_TEST = "tests/test_replay_compatibility_mapping.py"
DECODING_PARAMS_CANONICAL_CODE = "REPLAY_DECODING_PARAMS_MISMATCH"
DECODING_PARAMS_ROW_ID = "model_compatibility.decoding_params_mismatch"
REPLAY_COMPATIBILITY_SOURCE_HASHES = {
    REPLAY_COMPATIBILITY_YAML: "3df5232c17fd110629b9f93ec20d283bc10a9735e88c6a45b3b571caadb3deee",
    REPLAY_COMPATIBILITY_SCHEMA: "1b287c117c2f0253f2fac6db8c15332b2e1faa45b289e249aab6d57850f3b172",
}
REPLAY_FAILURE_RECORD_SOURCE_HASHES = {
    REPLAY_FAILURE_RECORD_SCHEMA: "55e867373d5094f4aae91acd8fc524f6178664fcf64f1a4fa30b9e90b248b2f1",
}


def _load_replay_validation_fail_closed_cases() -> tuple[dict[str, object], ...]:
    module_path = ROOT / "tests" / "test_replay_validation.py"
    spec = importlib.util.spec_from_file_location("zovark_runtime_replay_validation_cases", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.REPLAY_VALIDATION_FAIL_CLOSED_CASES


def _item_by_marker(checklist: list[dict[str, object]], marker: str) -> dict[str, object]:
    matches = [item for item in checklist if item.get("proof_marker") == marker]
    assert len(matches) == 1
    return matches[0]


def _assert_repo_file_exists(rel_path: str) -> None:
    assert (ROOT / rel_path).is_file(), rel_path


def _sha256(rel_path: str) -> str:
    return hashlib.sha256((ROOT / rel_path).read_bytes()).hexdigest()


def _run_cli(args: list[str], capsys) -> dict[str, object]:
    assert main(args) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return json.loads(captured.out)


def test_cli_proof_status_reports_architecture_baseline(capsys) -> None:
    payload = _run_cli(["proof-status"], capsys)

    assert payload["report"] == "local proof status"
    assert payload["runtime_proof_loop"] == "incomplete"
    assert payload["architecture_baseline"] == {
        "source_ref": "main",
        "source_tag": None,
        "source_commit": ARCHITECTURE_SOURCE_COMMIT,
    }
    assert payload["baseline_inventory"] == {
        "adr_files": 26,
        "binding_adrs": 25,
        "proposed_pending_adrs": ["ADR-0043"],
        "invariants": 39,
        "authoritative_schemas": 26,
        "replay_compatibility_contract": "architecture/replay-compatibility.yaml",
    }


def test_cli_proof_status_labels_deferred_capabilities(capsys) -> None:
    payload = _run_cli(["proof-status"], capsys)

    assert "bounded retrieval implementation" in payload["deferred_capabilities"]
    assert "deterministic verdict/proof generation" in payload["deferred_capabilities"]
    assert "AlertForge scenario validation" in payload["deferred_capabilities"]
    assert "benchmark report script" in payload["deferred_capabilities"]
    assert "autonomous-dispatch capability" in payload["deferred_capabilities"]


def test_cli_proof_status_explains_incomplete_proof_chain(capsys) -> None:
    payload = _run_cli(["proof-status"], capsys)

    assert payload["runtime_proof_loop"] == "incomplete"
    assert payload["incomplete_reason"]
    assert isinstance(payload["incomplete_reason"], list)

    assert payload["proof_chain_checklist_scope"] == {
        "reporting_role": "declarative status explanation",
        "completion_definition": "not-defined-by-runtime",
        "completion_authority": "architecture-owned or undefined until explicitly specified",
        "completion_claim": "not-claimed",
        "proof_execution": "not-run-by-proof-status",
    }

    checklist = payload["proof_chain_checklist"]
    assert checklist

    ids = [item["id"] for item in checklist]
    assert len(ids) == len(set(ids))
    for item_id in ids:
        assert isinstance(item_id, str)
        assert item_id
        assert item_id == item_id.lower()
        assert " " not in item_id

    valid_statuses = {"satisfied", "deferred"}
    for item in checklist:
        assert item["status"] in valid_statuses

        if item["status"] == "satisfied":
            assert item.get("proof_marker")
            evidence_keys = {
                "test_file_path",
                "runtime_artifact_paths",
                "contract_paths",
                "fixture_paths",
                "yaml_artifact_path",
                "schema_artifact_path",
                "related_test_file_paths",
                "expected_count",
            }
            assert any(item.get(key) for key in evidence_keys)

            if "test_file_path" in item:
                _assert_repo_file_exists(item["test_file_path"])
            for rel_path in item.get("related_test_file_paths", []):
                _assert_repo_file_exists(rel_path)
            if "yaml_artifact_path" in item:
                _assert_repo_file_exists(item["yaml_artifact_path"])
            if "schema_artifact_path" in item:
                _assert_repo_file_exists(item["schema_artifact_path"])
            for rel_path in item.get("runtime_artifact_paths", []):
                _assert_repo_file_exists(rel_path)
            for rel_path in item.get("contract_paths", []):
                _assert_repo_file_exists(rel_path)
            for rel_path in item.get("fixture_paths", []):
                _assert_repo_file_exists(rel_path)

        if item["status"] == "deferred":
            assert item.get("deferred_reason")
            assert item.get("architecture_authority") or item.get("authority_required")
            assert item.get("completion_note") == "runtime is not claiming proof-loop completion"

    satisfied_markers = {item["proof_marker"] for item in checklist if item["status"] == "satisfied"}
    assert satisfied_markers == EXPECTED_PROOF_CHAIN_MARKERS
    assert "REPLAY_COMPATIBILITY_MATRIX_COVERAGE_OK" not in json.dumps(payload)

    contract_count_item = _item_by_marker(checklist, "CONTRACT_METASCHEMA_OK")
    assert contract_count_item["expected_count"]["value"] == len(list(CONTRACTS.glob("*.schema.json")))

    fail_closed_item = _item_by_marker(checklist, "REPLAY_VALIDATION_FAIL_CLOSED_CASES_OK")
    assert fail_closed_item["expected_count"]["value"] == len(_load_replay_validation_fail_closed_cases())

    replay_compatibility_item = _item_by_marker(checklist, "REPLAY_COMPATIBILITY_MATRIX_SCHEMA_OK")
    assert replay_compatibility_item["test_file_path"] == "tests/test_replay_compatibility_contract.py"
    assert replay_compatibility_item["yaml_artifact_path"] == REPLAY_COMPATIBILITY_YAML
    assert replay_compatibility_item["schema_artifact_path"] == REPLAY_COMPATIBILITY_SCHEMA
    assert replay_compatibility_item["architecture_source_commit"] == ARCHITECTURE_SOURCE_COMMIT
    assert replay_compatibility_item["source_hashes"] == REPLAY_COMPATIBILITY_SOURCE_HASHES
    for rel_path, expected_hash in REPLAY_COMPATIBILITY_SOURCE_HASHES.items():
        _assert_repo_file_exists(rel_path)
        assert _sha256(rel_path) == expected_hash

    replay_compatibility_row_item = _item_by_marker(checklist, "REPLAY_COMPATIBILITY_ROW_COVERAGE_SCHEMA_OK")
    assert replay_compatibility_row_item["test_file_path"] == "tests/test_replay_compatibility_contract.py"
    assert replay_compatibility_row_item["yaml_artifact_path"] == REPLAY_COMPATIBILITY_YAML
    assert replay_compatibility_row_item["schema_artifact_path"] == REPLAY_COMPATIBILITY_SCHEMA
    assert replay_compatibility_row_item["architecture_source_commit"] == ARCHITECTURE_SOURCE_COMMIT
    assert replay_compatibility_row_item["source_hashes"] == REPLAY_COMPATIBILITY_SOURCE_HASHES
    for rel_path, expected_hash in REPLAY_COMPATIBILITY_SOURCE_HASHES.items():
        _assert_repo_file_exists(rel_path)
        assert _sha256(rel_path) == expected_hash

    replay_failure_item = _item_by_marker(checklist, "REPLAY_FAILURE_RECORD_SCHEMA_OK")
    assert replay_failure_item["test_file_path"] == "tests/test_replay_failure_record_contract.py"
    assert replay_failure_item["contract_paths"] == [REPLAY_FAILURE_RECORD_SCHEMA]
    assert replay_failure_item["architecture_source_commit"] == REPLAY_FAILURE_CONTRACT_SOURCE_COMMIT
    assert replay_failure_item["source_hashes"] == REPLAY_FAILURE_RECORD_SOURCE_HASHES
    for rel_path, expected_hash in REPLAY_FAILURE_RECORD_SOURCE_HASHES.items():
        _assert_repo_file_exists(rel_path)
        assert _sha256(rel_path) == expected_hash

    replay_failure_fixture_item = _item_by_marker(checklist, "REPLAY_FAILURE_RECORD_FIXTURE_SCHEMA_OK")
    assert replay_failure_fixture_item["test_file_path"] == "tests/test_replay_failure_record_fixture.py"
    assert replay_failure_fixture_item["contract_paths"] == [REPLAY_FAILURE_RECORD_SCHEMA]
    assert replay_failure_fixture_item["fixture_paths"] == [REPLAY_FAILURE_RECORD_FIXTURE]
    _assert_repo_file_exists(REPLAY_FAILURE_RECORD_FIXTURE)

    replay_failure_mapping_item = _item_by_marker(checklist, "REPLAY_FAILURE_CANONICAL_CODE_MAPPING_OK")
    assert replay_failure_mapping_item["test_file_path"] == "tests/test_replay_failure_mapping.py"
    assert replay_failure_mapping_item["runtime_artifact_paths"] == [REPLAY_FAILURE_MAPPING_MODULE]
    assert replay_failure_mapping_item["contract_paths"] == [REPLAY_FAILURE_RECORD_SCHEMA]
    assert replay_failure_mapping_item["yaml_artifact_path"] == REPLAY_COMPATIBILITY_YAML
    _assert_repo_file_exists(REPLAY_FAILURE_MAPPING_MODULE)

    replay_failure_recording_item = _item_by_marker(checklist, "REPLAY_FAILURE_RECORD_EMISSION_OK")
    assert replay_failure_recording_item["test_file_path"] == "tests/test_replay_failure_recording.py"
    assert replay_failure_recording_item["runtime_artifact_paths"] == [
        REPLAY_FAILURE_RECORDING_MODULE,
        REPLAY_FAILURE_MAPPING_MODULE,
    ]
    assert replay_failure_recording_item["contract_paths"] == [REPLAY_FAILURE_RECORD_SCHEMA]
    _assert_repo_file_exists(REPLAY_FAILURE_RECORDING_MODULE)

    replay_compatibility_mapping_item = _item_by_marker(checklist, "REPLAY_COMPATIBILITY_MATRIX_ROW_MAPPING_OK")
    assert replay_compatibility_mapping_item["test_file_path"] == REPLAY_COMPATIBILITY_MAPPING_TEST
    assert replay_compatibility_mapping_item["runtime_artifact_paths"] == [
        REPLAY_COMPATIBILITY_MAPPING_MODULE,
        REPLAY_FAILURE_RECORDING_MODULE,
    ]
    assert replay_compatibility_mapping_item["contract_paths"] == [REPLAY_FAILURE_RECORD_SCHEMA]
    assert replay_compatibility_mapping_item["yaml_artifact_path"] == REPLAY_COMPATIBILITY_YAML
    _assert_repo_file_exists(REPLAY_COMPATIBILITY_MAPPING_MODULE)

    decoding_params_item = _item_by_marker(checklist, "REPLAY_DECODING_PARAMS_FAIL_CLOSED_OK")
    assert decoding_params_item["test_file_path"] == REPLAY_VALIDATION_TEST
    assert decoding_params_item["related_test_file_paths"] == [
        REPLAY_FAILURE_MAPPING_TEST,
        REPLAY_FAILURE_RECORDING_TEST,
        REPLAY_COMPATIBILITY_MAPPING_TEST,
    ]
    assert decoding_params_item["runtime_artifact_paths"] == [
        REPLAY_FAILURE_MAPPING_MODULE,
        REPLAY_FAILURE_RECORDING_MODULE,
        REPLAY_COMPATIBILITY_MAPPING_MODULE,
    ]
    assert decoding_params_item["contract_paths"] == [REPLAY_FAILURE_RECORD_SCHEMA]
    assert decoding_params_item["yaml_artifact_path"] == REPLAY_COMPATIBILITY_YAML
    assert decoding_params_item["canonical_code"] == DECODING_PARAMS_CANONICAL_CODE
    assert decoding_params_item["row_id"] == DECODING_PARAMS_ROW_ID

    coverage_item = next(item for item in checklist if item["id"] == "runtime_replay_compatibility_coverage_claim")
    assert coverage_item["status"] == "deferred"
    assert "coverage" in coverage_item["deferred_reason"]
    assert "matrix-row mapping is proven" in coverage_item["deferred_reason"]
    assert "REPLAY_TOOL_RETIRED" in coverage_item["deferred_reason"]
    assert "REPLAY_DECODING_PARAMS_MISMATCH" not in coverage_item["deferred_reason"]
    assert "ADR-0047" in coverage_item["architecture_authority"]
    assert "INV-036" in coverage_item["architecture_authority"]
    assert "architecture/blueprint/schemas/replay_failure_record.schema.json" in coverage_item["architecture_authority"]
    assert "https://github.com/7inaydas-cmyk/zovark-architecture/issues/55" in coverage_item["architecture_authority"]
    assert "https://github.com/7inaydas-cmyk/zovark-architecture/issues/57" in coverage_item["architecture_authority"]
    assert "REPLAY_TOOL_RETIRED" in coverage_item["authority_required"]

    assert not any(item["id"] == "runtime_replay_failure_record_emission" for item in checklist)

    print("PROOF_CHAIN_CHECKLIST_OK")


def test_cli_proof_status_avoids_readiness_claims(capsys) -> None:
    payload = _run_cli(["proof-status"], capsys)
    rendered = json.dumps(payload).lower()

    forbidden_claims = [
        "customer-ready",
        "customer readiness: ready",
        "demo-ready",
        "demo readiness: ready",
        "product-ready",
        "product readiness: ready",
        "production-ready",
        "production readiness: ready",
        "compliance-ready",
        "compliance readiness: ready",
        "sla-ready",
        "sla readiness: ready",
    ]
    for claim in forbidden_claims:
        assert claim not in rendered


def test_build_proof_status_fails_when_a_local_check_fails(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "contracts"
    manifest_dir.mkdir()
    (manifest_dir / "contract-manifest.json").write_text(
        json.dumps(
            {
                "source_tag": "v3.2.5.0-baseline-consolidated",
                "source_commit": "a8003de839ac3bd8412a7cb520c591f52f4bd64e",
            }
        ),
        encoding="utf-8",
    )

    def failing_check(root: Path, name: str, script: Path) -> LocalCheckResult:
        if name == "invariant_text":
            return LocalCheckResult(name=name, status="fail", detail="simulated failure")
        return LocalCheckResult(name=name, status="pass", detail="simulated pass")

    payload, exit_code = proof_status.build_proof_status(tmp_path, check_runner=failing_check)

    assert exit_code == 1
    assert {
        "name": "invariant_text",
        "status": "fail",
        "detail": "simulated failure",
    } in payload["local_checks"]


def test_build_proof_status_reports_missing_manifest(tmp_path: Path) -> None:
    def passing_check(root: Path, name: str, script: Path) -> LocalCheckResult:
        return LocalCheckResult(name=name, status="pass", detail="simulated pass")

    payload, exit_code = proof_status.build_proof_status(tmp_path, check_runner=passing_check)

    assert exit_code == 1
    assert payload["architecture_baseline"]["status"] == "fail"
    assert "contract-manifest.json" in payload["architecture_baseline"]["detail"]
    assert "missing" in payload["architecture_baseline"]["detail"]
    assert "deferred_capabilities" in payload


def test_build_proof_status_reports_malformed_manifest(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "contracts"
    manifest_dir.mkdir()
    (manifest_dir / "contract-manifest.json").write_text("{not json", encoding="utf-8")

    def passing_check(root: Path, name: str, script: Path) -> LocalCheckResult:
        return LocalCheckResult(name=name, status="pass", detail="simulated pass")

    payload, exit_code = proof_status.build_proof_status(tmp_path, check_runner=passing_check)

    assert exit_code == 1
    assert payload["architecture_baseline"]["status"] == "fail"
    assert "invalid JSON" in payload["architecture_baseline"]["detail"]
