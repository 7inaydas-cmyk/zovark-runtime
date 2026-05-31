"""Slice 5 — SOC report / handoff narrative traceability (staging).

Asserts the customer report and edr-handoff narrative make no claim that is not backed
by recorded evidence: in particular, no Microsoft-Word / document-open / phishing
framing, and LSASS / SMB language only when the corresponding evidence exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from zovark_runtime.proof_package.pipeline import run_proof_package

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"

# Tokens that were previously asserted without evidence backing.
_UNCONDITIONALLY_FORBIDDEN = ["microsoft word", "opened a document", "phishing", "implant"]


def _narrative(out: Path) -> str:
    report = (out / "customer-report.md").read_text(encoding="utf-8").lower()
    handoff = json.loads((out / "edr-handoff.json").read_text())
    narrative = report + "\n" + handoff["rollback_plan"]["recovery_notes"].lower()
    narrative += "\n" + handoff["blast_radius"]["estimated_business_impact"].lower()
    return narrative


def _has_source_type(out: Path, source_type: str) -> bool:
    ledger = json.loads((out / "evidence-ledger.json").read_text())
    return any(e["source_type"] == source_type for e in ledger)


@pytest.mark.parametrize("name", ["edr-sample-001", "edr-multi-001", "edr-multi-002", "edr-multi-003", "edr-multi-004", "edr-multi-005"])
def test_no_unconditionally_unsupported_claims(tmp_path, name):
    out = tmp_path / name
    run_proof_package(FIX / f"{name}.json", out, tenant_id="tenant-001")
    text = _narrative(out)
    for token in _UNCONDITIONALLY_FORBIDDEN:
        assert token not in text, f"{name}: unsupported claim '{token}' present"


@pytest.mark.parametrize("name", ["edr-sample-001", "edr-multi-001", "edr-multi-002", "edr-multi-003", "edr-multi-004", "edr-multi-005"])
def test_lsass_language_only_when_lsass_evidence(tmp_path, name):
    out = tmp_path / name
    run_proof_package(FIX / f"{name}.json", out, tenant_id="tenant-001")
    text = _narrative(out)
    if not _has_source_type(out, "credential_access"):
        assert "lsass" not in text, f"{name}: LSASS language without credential_access evidence"


def test_edr_sample_handoff_drops_unconditional_lsass(tmp_path):
    # edr-sample-001 has no LSASS evidence; its handoff must not mention LSASS.
    out = tmp_path / "s"
    run_proof_package(FIX / "edr-sample-001.json", out, tenant_id="tenant-001")
    handoff = json.loads((out / "edr-handoff.json").read_text())
    assert "lsass" not in handoff["rollback_plan"]["recovery_notes"].lower()


def test_multi001_keeps_evidence_backed_lsass(tmp_path):
    # edr-multi-001 has LSASS evidence; LSASS language is allowed and present.
    out = tmp_path / "m"
    run_proof_package(FIX / "edr-multi-001.json", out, tenant_id="tenant-001")
    assert _has_source_type(out, "credential_access")
    assert "lsass" in (out / "customer-report.md").read_text().lower()


# Fabricated LSASS *assertions* (distinct from an alert description that merely mentions
# the word, which is evidence-backed quoting).
_LSASS_ASSERTIONS = ["lsass memory", "lsass was accessed", "lsass access event", "given the lsass"]


def test_non_lsass_credential_access_has_no_fabricated_lsass_assertion(tmp_path):
    # edr-multi-004 has credential_access that is SAM-hive (T1003.002), NOT LSASS, and
    # exercises the full report path. The report/handoff must not ASSERT an LSASS event,
    # and must not fabricate a payload path.
    out = tmp_path / "m4"
    run_proof_package(FIX / "edr-multi-004.json", out, tenant_id="tenant-001")
    assert _has_source_type(out, "credential_access")
    report = (out / "customer-report.md").read_text().lower()
    handoff = json.loads((out / "edr-handoff.json").read_text())
    notes = handoff["rollback_plan"]["recovery_notes"].lower()
    for phrase in _LSASS_ASSERTIONS:
        assert phrase not in report, f"fabricated LSASS assertion in report: {phrase}"
        assert phrase not in notes, f"fabricated LSASS assertion in handoff: {phrase}"
    assert "svchost.exe" not in report  # no fabricated payload path


def test_non_smb_lateral_has_no_smb_fabrication(tmp_path):
    # edr-multi-005 has a blocked NON-SMB (RDP T1021.001) lateral movement. No SMB finding
    # may fire, the fabricated "HOST-13" must never appear, and the handoff blast radius
    # must not assert an "SMB attempt" for it.
    out = tmp_path / "m5"
    run_proof_package(FIX / "edr-multi-005.json", out, tenant_id="tenant-001")
    findings = json.loads((out / "findings.json").read_text())
    rule_ids = {f.get("rule_id") for f in findings}
    assert "RULE-SMB-LATERAL-MOVEMENT" not in rule_ids
    assert "HOST-13" not in (out / "findings.json").read_text()
    assert "HOST-13" not in (out / "customer-report.md").read_text()
    handoff = json.loads((out / "edr-handoff.json").read_text())
    blocked = handoff["blast_radius"]["lateral_movement_blocked"]
    assert all("SMB attempt" not in line for line in blocked)


def test_smb_lateral_finding_title_has_no_hardcoded_host(tmp_path):
    # Real SMB fixtures: the SMB finding title must not hardcode a host.
    out = tmp_path / "m1"
    run_proof_package(FIX / "edr-multi-001.json", out, tenant_id="tenant-001")
    smb = [f for f in json.loads((out / "findings.json").read_text())
           if f.get("rule_id") == "RULE-SMB-LATERAL-MOVEMENT"]
    assert smb and "HOST-13" not in smb[0]["title"]
