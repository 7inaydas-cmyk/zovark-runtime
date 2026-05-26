from __future__ import annotations

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
    "CONTRACT_METASCHEMA_OK",
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
        "source_commit": "fa58bb16cf0e3209ba8c3310eabbac40f95b6b61",
    }
    assert payload["baseline_inventory"] == {
        "adr_files": 26,
        "binding_adrs": 25,
        "proposed_pending_adrs": ["ADR-0043"],
        "invariants": 39,
        "authoritative_schemas": 25,
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
                "expected_count",
            }
            assert any(item.get(key) for key in evidence_keys)

            if "test_file_path" in item:
                _assert_repo_file_exists(item["test_file_path"])
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

    contract_count_item = _item_by_marker(checklist, "CONTRACT_METASCHEMA_OK")
    assert contract_count_item["expected_count"]["value"] == len(list(CONTRACTS.glob("*.schema.json")))

    fail_closed_item = _item_by_marker(checklist, "REPLAY_VALIDATION_FAIL_CLOSED_CASES_OK")
    assert fail_closed_item["expected_count"]["value"] == len(_load_replay_validation_fail_closed_cases())

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
