"""Slice 7 — recorded live-AI investigation with offline replay (staging).

Record-time only model call; replay re-validates recorded I/O OFFLINE and never calls a
model; model output is recorded evidence, never verdict authority; tamper fails closed.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from zovark_runtime.investigation_memory.store import LocalInvestigationMemoryStore
from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.adr0046_bridge import load_tape
from zovark_runtime.proof_package.ai_investigation import (
    FakeModelProvider,
    record_ai_investigation,
    replay_ai_investigation,
)
from zovark_runtime.proof_package.pipeline import run_proof_package

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "edr-sample-001.json"


class ExplodingProvider:
    model_id = "explode"
    model_version = "0"

    def complete(self, prompt: str) -> str:
        raise AssertionError("model provider called — must not happen at replay")


def _package(tmp_path):
    out = tmp_path / "pkg"
    run_proof_package(FIXTURE, out, tenant_id="tenant-001")
    return load_tape(out), out


def test_record_then_replay_offline(tmp_path):
    tape, _ = _package(tmp_path)
    store = LocalInvestigationMemoryStore(tmp_path / "mem")
    recorded = record_ai_investigation(tape, FakeModelProvider(), store)
    assert recorded["model_contribution"] is True
    assert recorded["is_verdict_authority"] is False
    assert recorded["model_versions_pin"] == ["fake-deterministic-model@1.0.0"]
    result = replay_ai_investigation(recorded, store)
    assert result["ok"] and result["no_live_llm_call"] is True


def test_replay_refuses_a_provider(tmp_path):
    tape, _ = _package(tmp_path)
    store = LocalInvestigationMemoryStore(tmp_path / "mem")
    recorded = record_ai_investigation(tape, FakeModelProvider(), store)
    with pytest.raises(ZovarkValidationError):
        replay_ai_investigation(recorded, store, provider=FakeModelProvider())


def test_replay_never_calls_model(tmp_path):
    # Even if a recorded artifact is replayed, no provider is ever invoked.
    tape, _ = _package(tmp_path)
    store = LocalInvestigationMemoryStore(tmp_path / "mem")
    recorded = record_ai_investigation(tape, FakeModelProvider(), store)
    # ExplodingProvider would raise if called; replay must not accept/call it.
    with pytest.raises(ZovarkValidationError):
        replay_ai_investigation(recorded, store, provider=ExplodingProvider())
    # And a normal offline replay simply does not touch any provider.
    assert replay_ai_investigation(recorded, store)["ok"]


def test_tampered_output_fails_closed(tmp_path):
    tape, _ = _package(tmp_path)
    store = LocalInvestigationMemoryStore(tmp_path / "mem")
    recorded = record_ai_investigation(tape, FakeModelProvider(), store)
    t = copy.deepcopy(recorded)
    t["model_output"] = t["model_output"] + " TAMPERED"  # hash now mismatches
    with pytest.raises(ZovarkValidationError):
        replay_ai_investigation(t, store)


def test_tampered_hash_fails_closed(tmp_path):
    tape, _ = _package(tmp_path)
    store = LocalInvestigationMemoryStore(tmp_path / "mem")
    recorded = record_ai_investigation(tape, FakeModelProvider(), store)
    t = copy.deepcopy(recorded)
    t["model_output_hash"] = "0" * 64
    with pytest.raises(ZovarkValidationError):
        replay_ai_investigation(t, store)


def test_consistent_tamper_caught_by_store_anchor(tmp_path):
    # Tamper BOTH output and its hash consistently: still caught because the store anchor
    # holds the record-time bytes.
    tape, _ = _package(tmp_path)
    store = LocalInvestigationMemoryStore(tmp_path / "mem")
    recorded = record_ai_investigation(tape, FakeModelProvider(), store)
    t = copy.deepcopy(recorded)
    from zovark_runtime.proof_package.hashing import sha256_of_string
    t["model_output"] = "forged model conclusion"
    t["model_output_hash"] = sha256_of_string(t["model_output"])
    with pytest.raises(ZovarkValidationError):
        replay_ai_investigation(t, store)


def test_model_is_not_verdict_authority(tmp_path):
    tape, _ = _package(tmp_path)
    store = LocalInvestigationMemoryStore(tmp_path / "mem")
    recorded = record_ai_investigation(tape, FakeModelProvider(), store)
    t = copy.deepcopy(recorded)
    t["is_verdict_authority"] = True  # attempt to elevate model to authority
    with pytest.raises(ZovarkValidationError):
        replay_ai_investigation(t, store)


def test_ai_layer_does_not_change_deterministic_verdict(tmp_path):
    # The proof package + its verdict are identical whether or not the AI layer runs.
    out1 = tmp_path / "p1"
    run_proof_package(FIXTURE, out1, tenant_id="tenant-001")
    v_before = (out1 / "verdict.json").read_text()
    tape = load_tape(out1)
    store = LocalInvestigationMemoryStore(tmp_path / "mem")
    record_ai_investigation(tape, FakeModelProvider(), store)
    v_after = (out1 / "verdict.json").read_text()
    assert v_before == v_after  # AI layer never touches the deterministic package
    assert json.loads(v_after)["model_contribution"] is False  # verdict stays rule-based


def test_record_is_deterministic(tmp_path):
    tape, _ = _package(tmp_path)
    s1 = LocalInvestigationMemoryStore(tmp_path / "m1")
    s2 = LocalInvestigationMemoryStore(tmp_path / "m2")
    r1 = record_ai_investigation(tape, FakeModelProvider(), s1)
    r2 = record_ai_investigation(tape, FakeModelProvider(), s2)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
