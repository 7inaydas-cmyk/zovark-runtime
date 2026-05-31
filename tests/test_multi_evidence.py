"""Slice 4 — multi-alert / multi-evidence inputs.

The deterministic generator already supports all five source types; this slice adds
deterministic dedup and exercises the richer rule paths (LSASS/SMB). Tests prove each
multi fixture generates + strict-verifies, dedup is deterministic, ordering is
deterministic with reorder-invariant semantics, the one-alert fixture is unchanged, and
the verifier still rejects a semantic forgery. No benign/notify-only verdicts.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.ingest import normalize_evidence
from zovark_runtime.proof_package.pipeline import build_completed_tape, run_proof_package
from zovark_runtime.proof_package.verify import verify_proof_package_strict

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
NINE = (
    "investigation-tape.json", "evidence-ledger.json", "timeline.json", "findings.json",
    "verdict.json", "edr-handoff.json", "audit-chain-entry.json", "replay-report.json",
    "customer-report.md",
)
CANONICAL = "424d858c40e87730a09fc1e9b610194e76dd1e22dc5e219c9f50ca7e412bcf39"
MULTI = ["edr-multi-001", "edr-multi-002", "edr-multi-003"]


def _combined(d: Path) -> str:
    return hashlib.sha256(b"".join((d / n).read_bytes() for n in NINE)).hexdigest()


@pytest.mark.parametrize("name", MULTI)
def test_multi_fixture_generates_and_verifies(tmp_path, name):
    out = tmp_path / name
    result = run_proof_package(FIX / f"{name}.json", out, tenant_id="tenant-001")
    assert result["verdict"] == "confirmed_malicious"
    summary = verify_proof_package_strict(out)
    assert summary["status"] == "verified" and summary["failure_count"] == 0


@pytest.mark.parametrize("name", MULTI)
def test_multi_fixture_deterministic(tmp_path, name):
    a, b = tmp_path / "a", tmp_path / "b"
    run_proof_package(FIX / f"{name}.json", a, tenant_id="tenant-001")
    run_proof_package(FIX / f"{name}.json", b, tenant_id="tenant-001")
    assert _combined(a) == _combined(b)


def test_lsass_and_smb_rules_exercised(tmp_path):
    out = tmp_path / "m1"
    run_proof_package(FIX / "edr-multi-001.json", out, tenant_id="tenant-001")
    rule_ids = {f["rule_id"] for f in json.loads((out / "findings.json").read_text())}
    assert "RULE-LSASS-DUMP" in rule_ids
    assert "RULE-SMB-LATERAL-MOVEMENT" in rule_ids


def test_duplicate_events_deduped_deterministically():
    raw = json.loads((FIX / "edr-multi-002.json").read_text())
    # The fixture has two identical process_events.
    assert len(raw["process_events"]) == 2
    assert raw["process_events"][0] == raw["process_events"][1]
    evidence = normalize_evidence(raw)
    ids = [e["evidence_id"] for e in evidence]
    assert len(ids) == len(set(ids))  # no duplicate evidence_ids
    # 1 alert + 1 (deduped) process + 2 network = 4
    assert len(evidence) == 4


def test_out_of_timestamp_order_input_fails_closed(tmp_path):
    # Ordering is input-order-deterministic AND the timeline enforces non-decreasing
    # timestamps. Reordering events into a timestamp-violating sequence is REJECTED
    # (fail-closed) rather than silently reordered or silently accepted.
    raw = json.loads((FIX / "edr-multi-003.json").read_text())
    bad = copy.deepcopy(raw)
    bad["lateral_movement_events"] = list(reversed(raw["lateral_movement_events"]))
    with pytest.raises(ZovarkValidationError):
        build_completed_tape(bad, tenant_id="tenant-001")


def test_same_timestamp_reorder_keeps_verdict_and_evidence_set(tmp_path):
    # When reordered events share the same timestamp (monotonicity preserved), the byte
    # output may differ but the verdict value and the SET of evidence content hashes are
    # invariant — the documented semantic-equivalence property.
    raw = json.loads((FIX / "edr-multi-003.json").read_text())
    same_ts = raw["lateral_movement_events"][0]["timestamp"]
    base = copy.deepcopy(raw)
    for ev in base["lateral_movement_events"]:
        ev["timestamp"] = same_ts
    swapped = copy.deepcopy(base)
    swapped["lateral_movement_events"] = list(reversed(base["lateral_movement_events"]))
    t1 = build_completed_tape(base, tenant_id="tenant-001")
    t2 = build_completed_tape(swapped, tenant_id="tenant-001")
    assert t1["verdict"]["value"] == t2["verdict"]["value"] == "confirmed_malicious"
    assert {e["hash"] for e in t1["raw_evidence"]} == {e["hash"] for e in t2["raw_evidence"]}


def test_one_alert_fixture_unchanged(tmp_path):
    out = tmp_path / "canon"
    run_proof_package(FIX / "edr-sample-001.json", out, tenant_id="tenant-001")
    assert _combined(out) == CANONICAL


@pytest.mark.parametrize("name", MULTI)
def test_no_benign_or_notify_only(tmp_path, name):
    out = tmp_path / name
    run_proof_package(FIX / f"{name}.json", out, tenant_id="tenant-001")
    verdict = json.loads((out / "verdict.json").read_text())["value"]
    assert verdict == "confirmed_malicious"  # only derivable verdict; never benign/notify
    handoff = json.loads((out / "edr-handoff.json").read_text())
    assert handoff["action_type"] == "isolate_host"


def test_verifier_rejects_forgery_on_multi(tmp_path):
    # Forge a multi package's verdict.json; strict verify must fail closed.
    out = tmp_path / "m1"
    run_proof_package(FIX / "edr-multi-001.json", out, tenant_id="tenant-001")
    verdict = json.loads((out / "verdict.json").read_text())
    verdict["value"] = "benign"
    (out / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")
    with pytest.raises(ZovarkValidationError):
        verify_proof_package_strict(out)
