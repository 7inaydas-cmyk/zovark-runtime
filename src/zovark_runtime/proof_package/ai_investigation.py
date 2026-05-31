"""Recorded live-AI investigation (Slice 7) — additive, record-time only.

A model may be called ONLY at record time. Its input/output are recorded losslessly with
hashes and the output bytes are anchored in the investigation_memory store
(content-addressed). Replay re-validates the recorded artifact OFFLINE and NEVER calls a
model or network. The model is recorded EVIDENCE, never verdict authority: the
deterministic 9-artifact proof package and its rule-based verdict are unchanged.

No network in this module: the FakeModelProvider is deterministic and offline; a real
provider would be supplied by the caller at record time only, and is never used at replay.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from zovark_runtime.investigation_memory.errors import (
    MemoryObjectNotFoundError,
    MemoryObjectTamperError,
    MemoryObjectValidationError,
)
from zovark_runtime.investigation_memory.store import LocalInvestigationMemoryStore
from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.hashing import sha256_of_string

_FAKE_MODEL_ID = "fake-deterministic-model"
_FAKE_MODEL_VERSION = "1.0.0"
_AI_TOOL_CALL_REF = "ai-investigation"


@runtime_checkable
class ModelProvider(Protocol):
    model_id: str
    model_version: str

    def complete(self, prompt: str) -> str: ...


class FakeModelProvider:
    """Deterministic, offline provider for CI/tests. Output is a pure function of prompt."""

    model_id = _FAKE_MODEL_ID
    model_version = _FAKE_MODEL_VERSION

    def complete(self, prompt: str) -> str:
        digest = sha256_of_string(prompt)
        return (
            "AI investigation note (deterministic, advisory only; not verdict authority). "
            f"prompt_sha256={digest[:16]}."
        )


def _build_prompt(tape: dict[str, Any]) -> str:
    if not isinstance(tape, dict) or "raw_evidence" not in tape or "verdict" not in tape:
        raise ZovarkValidationError("ai_investigation: tape missing raw_evidence/verdict")
    evidence = [
        {"source_type": e["source_type"], "hash": e["hash"]}
        for e in tape["raw_evidence"]
    ]
    return json.dumps(
        {
            "tape_id": tape["tape_id"],
            "deterministic_verdict": tape["verdict"]["value"],
            "evidence": evidence,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def record_ai_investigation(
    tape: dict[str, Any],
    provider: ModelProvider,
    store: LocalInvestigationMemoryStore,
) -> dict[str, Any]:
    """RECORD-TIME ONLY: call the provider once and record its I/O losslessly + anchored."""
    prompt = _build_prompt(tape)
    output = provider.complete(prompt)  # the ONLY model call; record-time only
    if not isinstance(output, str) or not output:
        raise ZovarkValidationError("ai_investigation: model output must be non-empty text")

    investigation_id = tape["tape_id"]
    try:
        metadata = store.put_bytes(
            output.encode("utf-8"),
            investigation_id=investigation_id,
            source_tool_call_ref=_AI_TOOL_CALL_REF,
            content_encoding="utf-8",
        )
    except (MemoryObjectValidationError, MemoryObjectTamperError) as exc:
        raise ZovarkValidationError(f"ai_investigation: store anchor failed: {exc}") from exc

    model_id = getattr(provider, "model_id", _FAKE_MODEL_ID)
    model_version = getattr(provider, "model_version", _FAKE_MODEL_VERSION)
    return {
        "schema": "zovark-ai-investigation/v1",
        "tape_id": investigation_id,
        "model_id": model_id,
        "model_version": model_version,
        "model_versions_pin": [f"{model_id}@{model_version}"],
        "prompt": prompt,
        "prompt_hash": sha256_of_string(prompt),
        "model_output": output,
        "model_output_hash": sha256_of_string(output),
        "model_output_memory_ref": metadata.memory_ref_id,
        "model_contribution": True,
        "is_verdict_authority": False,
        "advisory_note": (
            "Recorded model evidence. Advisory only; never overrides the deterministic "
            "rule-based verdict."
        ),
        "deterministic_verdict": tape["verdict"]["value"],
        "no_live_llm_call_at_replay": True,
        "no_live_edr_call_at_replay": True,
    }


def replay_ai_investigation(
    recorded: dict[str, Any],
    store: LocalInvestigationMemoryStore,
    provider: ModelProvider | None = None,
) -> dict[str, Any]:
    """OFFLINE replay: re-validate recorded model I/O. NEVER calls a model/network.

    Passing a `provider` is rejected (a replay must not be able to call a model). The model
    output is re-read from the investigation_memory store (record-time anchor) and all
    hashes re-checked. Fails closed on any tamper.
    """
    if provider is not None:
        raise ZovarkValidationError("ai replay must not be given a live provider")
    if not isinstance(recorded, dict):
        raise ZovarkValidationError("ai replay: recorded artifact must be an object")
    for key in (
        "prompt", "prompt_hash", "model_output", "model_output_hash",
        "model_output_memory_ref", "model_contribution", "is_verdict_authority",
    ):
        if key not in recorded:
            raise ZovarkValidationError(f"ai replay: recorded artifact missing {key}")

    if recorded["is_verdict_authority"] is not False:
        raise ZovarkValidationError("ai replay: model output must not be verdict authority")

    # Recompute hashes from the recorded prompt/output.
    if sha256_of_string(recorded["prompt"]) != recorded["prompt_hash"]:
        raise ZovarkValidationError("ai replay: prompt hash mismatch (tamper)")
    if sha256_of_string(recorded["model_output"]) != recorded["model_output_hash"]:
        raise ZovarkValidationError("ai replay: model_output hash mismatch (tamper)")

    # Anchor: the recorded output must match the bytes stored at record time. store.verify
    # re-hashes the stored bytes against recorded metadata (store-layer integrity), then we
    # re-decode + re-hash here (defense in depth).
    try:
        store.verify(recorded["model_output_memory_ref"])
        stored = store.read_bytes_for_verification(recorded["model_output_memory_ref"])
    except (MemoryObjectNotFoundError, MemoryObjectTamperError, MemoryObjectValidationError) as exc:
        raise ZovarkValidationError(f"ai replay: store anchor missing/invalid: {exc}") from exc
    if stored.decode("utf-8") != recorded["model_output"]:
        raise ZovarkValidationError("ai replay: recorded output does not match stored anchor (tamper)")
    if sha256_of_string(stored.decode("utf-8")) != recorded["model_output_hash"]:
        raise ZovarkValidationError("ai replay: stored anchor hash mismatch (tamper)")

    return {
        "ok": True,
        "no_live_llm_call": True,
        "no_live_edr_call": True,
        "model_contribution": recorded["model_contribution"],
        "is_verdict_authority": False,
    }


def write_ai_investigation(
    tape: dict[str, Any],
    provider: ModelProvider,
    output_path: str | Path,
    store: LocalInvestigationMemoryStore,
) -> dict[str, Any]:
    recorded = record_ai_investigation(tape, provider, store)
    Path(output_path).write_text(
        json.dumps(recorded, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return recorded
