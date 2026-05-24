from __future__ import annotations

import json
from pathlib import Path

from zovark_runtime import proof_status
from zovark_runtime.cli import main
from zovark_runtime.proof_status import LocalCheckResult


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
        "source_tag": "v3.2.5.0-baseline-consolidated",
        "source_commit": "a8003de839ac3bd8412a7cb520c591f52f4bd64e",
    }
    assert payload["baseline_inventory"] == {
        "adr_files": 26,
        "binding_adrs": 25,
        "proposed_pending_adrs": ["ADR-0043"],
        "invariants": 39,
        "authoritative_schemas": 23,
        "replay_compatibility_contract": "architecture/replay-compatibility.yaml",
    }


def test_cli_proof_status_labels_deferred_capabilities(capsys) -> None:
    payload = _run_cli(["proof-status"], capsys)

    assert "bounded retrieval implementation" in payload["deferred_capabilities"]
    assert "deterministic verdict/proof generation" in payload["deferred_capabilities"]
    assert "AlertForge scenario validation" in payload["deferred_capabilities"]
    assert "benchmark report script" in payload["deferred_capabilities"]
    assert "autonomous-dispatch capability" in payload["deferred_capabilities"]


def test_cli_proof_status_avoids_readiness_claims(capsys) -> None:
    payload = _run_cli(["proof-status"], capsys)
    rendered = json.dumps(payload)

    for prefix in ["customer", "production", "product", "compliance"]:
        assert f"{prefix}-ready" not in rendered


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
