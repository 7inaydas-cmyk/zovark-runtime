"""Tests for the V1 deterministic proof-package pipeline.

These tests are self-contained (no dependency on the architecture repo). The
byte-for-byte conformance proof against the architecture slice001 oracle is a
committed artifact in /CONFORMANCE.md; here we prove determinism, offline
re-derivation validation, fail-closed tamper-evidence, and the no-live-call
invariants.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zovark_runtime.investigation_memory.store import LocalInvestigationMemoryStore
from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.package_verifier import verify_proof_package
from zovark_runtime.proof_package.pipeline import build_completed_tape, run_proof_package

FIXTURE = Path(__file__).parent / "fixtures" / "edr-sample-001.json"
NINE_ARTIFACTS = (
    "investigation-tape.json",
    "evidence-ledger.json",
    "timeline.json",
    "findings.json",
    "verdict.json",
    "edr-handoff.json",
    "audit-chain-entry.json",
    "replay-report.json",
    "customer-report.md",
)


def _combined_bytes(package_dir: Path) -> bytes:
    return b"".join((package_dir / name).read_bytes() for name in NINE_ARTIFACTS)


def test_pipeline_produces_exactly_nine_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    result = run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    written = sorted(p.name for p in out.iterdir())
    assert written == sorted(NINE_ARTIFACTS)
    assert result["replay_state"] == "succeeded"
    assert result["verdict"] == "confirmed_malicious"


def test_pipeline_is_deterministic_byte_identical(tmp_path: Path) -> None:
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    run_proof_package(FIXTURE, out1, tenant_id="tenant-001")
    run_proof_package(FIXTURE, out2, tenant_id="tenant-001")
    assert _combined_bytes(out1) == _combined_bytes(out2)


def test_verify_passes_on_generated_package(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    summary = verify_proof_package(out)
    assert summary["status"] == "verified"
    assert summary["failure_count"] == 0
    assert summary["verdict"] == "confirmed_malicious"
    assert summary["evidence_entries_checked"] == 3


def test_replay_records_no_live_calls(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    replay_state = json.loads((out / "replay-report.json").read_text())["replay_state"]
    assert replay_state["no_live_llm_call"] is True
    assert replay_state["no_live_edr_call"] is True
    assert replay_state["mode"] == "recorded_output"
    assert replay_state["model_versions_pin"] == []


def test_verdict_has_no_model_contribution(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    verdict = json.loads((out / "verdict.json").read_text())
    assert verdict["model_contribution"] is False
    for finding in json.loads((out / "findings.json").read_text()):
        assert finding["model_contribution"] is False


def test_handoff_is_approval_required_nothing_dispatched(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    handoff = json.loads((out / "edr-handoff.json").read_text())
    assert handoff["approval_mode"] == "approval_required"
    assert handoff["execution_result"]["status"] == "pending"
    assert handoff["execution_result"]["started_at"] is None


def test_verify_detects_tampered_verdict(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    verdict_path = out / "verdict.json"
    tampered = json.loads(verdict_path.read_text())
    tampered["value"] = "benign"  # forge a softer verdict
    verdict_path.write_text(json.dumps(tampered, indent=2) + "\n")
    with pytest.raises(ZovarkValidationError):
        verify_proof_package(out)


def test_verify_detects_tampered_evidence_hash(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    ledger_path = out / "evidence-ledger.json"
    ledger = json.loads(ledger_path.read_text())
    ledger[0]["raw_content"]["description"] = "tampered after the fact"
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
    with pytest.raises(ZovarkValidationError):
        verify_proof_package(out)


def test_investigation_memory_records_each_evidence_item(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    memory = tmp_path / "memory"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001", memory_dir=memory)
    objects = list((memory / "objects").rglob("*.bin"))
    assert len(objects) == 3  # one per evidence item, content-addressed
    # Every evidence hash in the ledger is present as a stored object.
    ledger = json.loads((out / "evidence-ledger.json").read_text())
    stored_hashes = {p.stem for p in objects}
    assert {entry["hash"] for entry in ledger} == stored_hashes


def test_investigation_memory_tamper_aborts_fail_closed(tmp_path: Path) -> None:
    out = tmp_path / "pkg"
    memory = tmp_path / "memory"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001", memory_dir=memory)
    # Corrupt one recorded object, then re-run against the same store.
    obj = next((memory / "objects").rglob("*.bin"))
    obj.write_bytes(b"corrupted-bytes")
    with pytest.raises(ZovarkValidationError):
        run_proof_package(FIXTURE, tmp_path / "pkg2", tenant_id="tenant-001", memory_dir=memory)


def test_rejects_non_object_input(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2, 3]")
    with pytest.raises(ZovarkValidationError):
        run_proof_package(bad, tmp_path / "pkg", tenant_id="tenant-001")


def test_build_completed_tape_without_store_is_offline(tmp_path: Path) -> None:
    raw = json.loads(FIXTURE.read_text())
    tape = build_completed_tape(raw, tenant_id="tenant-001", memory_store=None)
    assert tape["state"] == "closed"
    assert tape["verdict"]["value"] == "confirmed_malicious"
    assert tape["replay_report"]["replay_state"]["state"] == "succeeded"
