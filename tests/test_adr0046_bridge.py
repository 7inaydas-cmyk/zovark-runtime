"""Slice 3 — ADR-0046 verdict-contract bridge tests.

The bridge is additive: it maps a proof-package tape to ADR-0046 verdict_input /
verdict_envelope / replay_record, reusing the repo's derive_verdict and
validate_replay_record. It does not change proof-package generation or
proof-package-verify (the semantic authority). Tests prove: schema validity of the
emitted contract artifacts, offline replay validation passes on conformant output and
FAILS CLOSED on tamper, determinism, and that the canonical proof package is unchanged.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
Draft202012Validator = jsonschema.Draft202012Validator

try:
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except Exception:  # pragma: no cover
    Registry = Resource = DRAFT202012 = None

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.adr0046_bridge import (
    build_bridge,
    build_replay_record,
    load_tape,
    tape_to_verdict_input,
)
from zovark_runtime.proof_package.pipeline import run_proof_package
from zovark_runtime.replay_validation import validate_replay_record
from zovark_runtime.verdict_derivation import derive_verdict

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
FIXTURE = ROOT / "tests" / "fixtures" / "edr-sample-001.json"
CANONICAL_COMBINED = "8749bf8af7a403110b3a622a22107cc0645e7fe8c455291da9c945e9513445a0"
NINE = (
    "investigation-tape.json", "evidence-ledger.json", "timeline.json", "findings.json",
    "verdict.json", "edr-handoff.json", "audit-chain-entry.json", "replay-report.json",
    "customer-report.md",
)


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _contract_store():
    store = {}
    for sp in sorted(CONTRACTS.glob("*.schema.json")):
        s = _load(sp)
        sid = s.get("$id")
        if isinstance(sid, str):
            store[sid.split("#", 1)[0]] = s
    return store


def _validator(schema_name: str):
    schema = _load(CONTRACTS / schema_name)
    Draft202012Validator.check_schema(schema)
    if Registry is not None:
        reg = Registry()
        for sid, s in _contract_store().items():
            reg = reg.with_resource(sid, Resource.from_contents(s, default_specification=DRAFT202012))
        return Draft202012Validator(schema, registry=reg)
    resolver = jsonschema.validators.RefResolver.from_schema(schema, store=_contract_store())
    return Draft202012Validator(schema, resolver=resolver)


def _tape(tmp_path: Path) -> dict:
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    return load_tape(out), out


def test_verdict_input_validates_against_schema(tmp_path):
    tape, _ = _tape(tmp_path)
    vi = tape_to_verdict_input(tape)
    errs = list(_validator("verdict_input.schema.json").iter_errors(vi))
    assert errs == [], [e.message for e in errs]


def test_verdict_envelope_validates_against_schema(tmp_path):
    tape, _ = _tape(tmp_path)
    env = derive_verdict(tape_to_verdict_input(tape))
    errs = list(_validator("verdict_envelope.schema.json").iter_errors(env))
    assert errs == [], [e.message for e in errs]
    # The ADR-0046 stub is indeterminate; the proof-package verdict stays authoritative.
    assert env["verdict_class"] == "indeterminate"
    assert tape["verdict"]["value"] == "confirmed_malicious"


def test_replay_record_validates_offline_and_passes(tmp_path):
    tape, _ = _tape(tmp_path)
    vi = tape_to_verdict_input(tape)
    env = derive_verdict(vi)
    rec = build_replay_record(vi, env)
    errs = list(_validator("replay_record.schema.json").iter_errors(rec))
    assert errs == [], [e.message for e in errs]
    result = validate_replay_record(rec, vi, env)
    assert result.ok, f"{result.code}: {result.detail}"


def test_tampered_replay_record_fails_closed(tmp_path):
    tape, _ = _tape(tmp_path)
    vi = tape_to_verdict_input(tape)
    env = derive_verdict(vi)
    rec = build_replay_record(vi, env)
    tampered = copy.deepcopy(rec)
    tampered["verdict_input_hash"] = "0" * 64
    assert validate_replay_record(tampered, vi, env).ok is False


def test_tampered_verdict_envelope_fails_closed(tmp_path):
    tape, _ = _tape(tmp_path)
    vi = tape_to_verdict_input(tape)
    env = derive_verdict(vi)
    rec = build_replay_record(vi, env)
    forged_env = copy.deepcopy(env)
    forged_env["verdict_class"] = "malicious"  # forge a different class
    # The record's envelope hash was computed over the real envelope; validating against
    # the forged expected envelope must fail closed (hash mismatch).
    assert validate_replay_record(rec, vi, forged_env).ok is False


def test_bridge_is_deterministic(tmp_path):
    tape, _ = _tape(tmp_path)
    a = json.dumps(build_bridge(tape), sort_keys=True)
    b = json.dumps(build_bridge(tape), sort_keys=True)
    assert a == b


def test_bridge_carries_authoritative_proof_verdict(tmp_path):
    tape, _ = _tape(tmp_path)
    bridge = build_bridge(tape)
    assert bridge["proof_package_verdict"]["value"] == "confirmed_malicious"
    assert bridge["replay_validation"]["ok"] is True


def test_canonical_proof_package_unchanged(tmp_path):
    # The bridge must not alter proof-package generation bytes.
    import hashlib
    out = tmp_path / "canon"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    combined = hashlib.sha256(b"".join((out / n).read_bytes() for n in NINE)).hexdigest()
    assert combined == CANONICAL_COMBINED


def test_bridge_fails_closed_on_missing_alert(tmp_path):
    tape, _ = _tape(tmp_path)
    broken = copy.deepcopy(tape)
    broken["raw_evidence"] = [e for e in broken["raw_evidence"] if e["source_type"] != "edr_alert"]
    with pytest.raises(ZovarkValidationError):
        tape_to_verdict_input(broken)
