"""End-to-end deterministic proof-package pipeline (V1 product slice).

Wires the vendored slice001 derivation modules into one offline command, and
records each evidence item into the runtime ``investigation_memory`` store as a
lossless, content-addressed recording substrate. Before the tape is sealed, every
recorded item is re-read and re-hashed from the store (tamper-evidence); a mismatch
aborts the run fail-closed, before any artifact is written.

No network, no live LLM, no wall clock, no randomness. See /DESIGN.md.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from zovark_runtime.investigation_memory.errors import (
    MemoryObjectNotFoundError,
    MemoryObjectTamperError,
    MemoryObjectValidationError,
)
from zovark_runtime.investigation_memory.identity import build_memory_ref_id
from zovark_runtime.investigation_memory.store import LocalInvestigationMemoryStore
from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.audit import attach_audit_entry, derive_audit_entry
from zovark_runtime.proof_package.canonical import canonical_json
from zovark_runtime.proof_package.findings import attach_findings, derive_findings
from zovark_runtime.proof_package.handoff import attach_handoff, derive_handoff
from zovark_runtime.proof_package.ingest import normalize_evidence
from zovark_runtime.proof_package.replay import attach_replay_report, derive_replay_report
from zovark_runtime.proof_package.tape import create_tape
from zovark_runtime.proof_package.timeline import attach_timeline, build_initial_timeline
from zovark_runtime.proof_package.verdict import attach_verdict, derive_verdict
from zovark_runtime.proof_package.writer import EXPECTED_OUTPUT_FILES, write_proof_package


# Logical, content-neutral label for the ingest step that records evidence.
_SOURCE_TOOL_CALL_REF = "edr-ingest"

# Ingestion-security bounds (fail-closed) for the untrusted input file.
_MAX_INPUT_BYTES = 8 * 1024 * 1024  # 8 MiB
_MAX_INPUT_DEPTH = 64


def build_completed_tape(
    raw_input: dict[str, Any],
    *,
    tenant_id: str | None = None,
    memory_store: LocalInvestigationMemoryStore | None = None,
) -> dict[str, Any]:
    """Build the complete replay-sealed proof-package tape from static input.

    Mirrors the architecture slice001 orchestration exactly so the emitted
    artifacts are byte-identical to the oracle. When ``memory_store`` is supplied,
    each evidence item is recorded losslessly and re-verified before sealing.
    """

    evidence_entries = normalize_evidence(raw_input)
    tape = create_tape(raw_input, evidence_entries, tenant_id=tenant_id)
    if memory_store is not None:
        _record_evidence(memory_store, tape)
    timeline = build_initial_timeline(tape)
    tape = attach_timeline(tape, timeline)
    findings, no_findings_flag = derive_findings(tape)
    tape = attach_findings(tape, findings, no_findings_flag)
    verdict = derive_verdict(tape)
    tape = attach_verdict(tape, verdict)
    tape["audit_ref"] = "audit-entry-1"
    handoff = derive_handoff(tape)
    tape = attach_handoff(tape, handoff)
    audit_entry = derive_audit_entry(tape)
    tape = attach_audit_entry(tape, audit_entry)
    if memory_store is not None:
        # Tamper-evidence: re-read + re-hash every recorded item from the store.
        # Any mismatch raises and aborts before artifacts are written.
        _verify_recorded_evidence(memory_store, tape)
    replay_report = derive_replay_report(tape)
    return attach_replay_report(tape, replay_report)


def run_proof_package(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    tenant_id: str | None = None,
    memory_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run the deterministic pipeline from a static input file to 9 artifacts.

    Returns a manifest: written file paths, the replay state, and the
    investigation_memory directory used.
    """

    raw_input = _safe_load_input(Path(input_path))

    out_path = Path(output_dir)
    _assert_output_dir_safe(out_path)
    resolved_memory_dir = (
        Path(memory_dir)
        if memory_dir is not None
        else out_path.parent / f"{out_path.name}.memory"
    )
    store = LocalInvestigationMemoryStore(resolved_memory_dir)

    tape = build_completed_tape(raw_input, tenant_id=tenant_id, memory_store=store)
    manifest = write_proof_package(tape, out_path)
    return {
        "artifacts": manifest,
        "expected_files": list(EXPECTED_OUTPUT_FILES),
        "replay_state": tape["replay_report"]["replay_state"]["state"],
        "memory_dir": str(resolved_memory_dir),
        "tape_id": tape["tape_id"],
        "verdict": tape["verdict"]["value"],
    }


def _safe_load_input(input_path: Path) -> dict[str, Any]:
    """Load + parse the untrusted input file with fail-closed bounds.

    Rejects oversized input, non-finite numbers (NaN/Infinity), excessive nesting,
    and non-object top-level values. All failures raise ZovarkValidationError so the
    CLI never emits a partial package or an uncaught traceback.
    """

    try:
        raw_bytes = input_path.read_bytes()
    except OSError as exc:
        raise ZovarkValidationError(f"input could not be read: {input_path}") from exc
    if len(raw_bytes) > _MAX_INPUT_BYTES:
        raise ZovarkValidationError(
            f"input exceeds the {_MAX_INPUT_BYTES}-byte limit"
        )
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ZovarkValidationError("input must be UTF-8 encoded JSON") from exc

    def _reject_constant(token: str) -> Any:
        raise ZovarkValidationError(f"input contains a non-finite number: {token}")

    try:
        parsed = json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise ZovarkValidationError(f"input is not valid JSON: {input_path}") from exc
    except RecursionError as exc:
        raise ZovarkValidationError("input nesting is too deep") from exc
    except ValueError as exc:
        # e.g. an integer literal exceeding Python's int-string conversion limit.
        raise ZovarkValidationError(f"input contains an out-of-range value: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ZovarkValidationError("proof-package input must be a JSON object")
    _assert_bounded_and_finite(parsed, _MAX_INPUT_DEPTH)
    return parsed


def _assert_bounded_and_finite(value: Any, max_depth: int, _depth: int = 0) -> None:
    if _depth > max_depth:
        raise ZovarkValidationError(
            f"input nesting exceeds the {max_depth}-level limit"
        )
    # Reject non-finite floats that bypass parse_constant (e.g. 1e999 -> inf), which
    # would otherwise raise an uncaught ValueError during canonicalization.
    if isinstance(value, float) and not math.isfinite(value):
        raise ZovarkValidationError("input contains a non-finite number")
    # Reject strings that cannot be UTF-8 encoded (e.g. lone surrogates from \uXXXX
    # escapes), which would otherwise raise an uncaught UnicodeEncodeError later.
    if isinstance(value, str):
        _assert_utf8_encodable(value)
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_utf8_encodable(key)
            _assert_bounded_and_finite(item, max_depth, _depth + 1)
    elif isinstance(value, list):
        for item in value:
            _assert_bounded_and_finite(item, max_depth, _depth + 1)


def _assert_utf8_encodable(text: str) -> None:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ZovarkValidationError(
            "input contains a string that is not valid UTF-8 (e.g. a lone surrogate)"
        ) from exc


def _assert_output_dir_safe(out_path: Path) -> None:
    """Refuse to write through symlinks (no overwrite outside the output dir)."""

    if out_path.is_symlink():
        raise ZovarkValidationError("output directory must not be a symlink")
    if out_path.exists() and not out_path.is_dir():
        raise ZovarkValidationError("output path must be a directory")
    for filename in EXPECTED_OUTPUT_FILES:
        target = out_path / filename
        if target.is_symlink():
            raise ZovarkValidationError(
                f"refusing to write through a symlink: {filename}"
            )


def _record_evidence(
    store: LocalInvestigationMemoryStore, tape: dict[str, Any]
) -> None:
    investigation_id = tape["tape_id"]
    for entry in tape["raw_evidence"]:
        content = canonical_json(entry["raw_content"])
        try:
            metadata = store.put_bytes(
                content,
                investigation_id=investigation_id,
                source_tool_call_ref=_SOURCE_TOOL_CALL_REF,
                content_encoding="utf-8",
            )
        except (MemoryObjectValidationError, MemoryObjectTamperError) as exc:
            raise ZovarkValidationError(
                f"investigation_memory recording failed: {exc}"
            ) from exc
        # The store hashes the exact recorded bytes; this must equal the
        # content-addressed evidence hash derived during ingestion.
        if metadata.content_hash != entry["hash"]:
            raise ZovarkValidationError(
                "investigation_memory content hash does not match evidence hash"
            )


def _verify_recorded_evidence(
    store: LocalInvestigationMemoryStore, tape: dict[str, Any]
) -> None:
    investigation_id = tape["tape_id"]
    for entry in tape["raw_evidence"]:
        memory_ref_id = build_memory_ref_id(
            investigation_id=investigation_id,
            source_tool_call_ref=_SOURCE_TOOL_CALL_REF,
            content_hash=entry["hash"],
        )
        try:
            metadata = store.verify(memory_ref_id)
        except (
            MemoryObjectNotFoundError,
            MemoryObjectTamperError,
            MemoryObjectValidationError,
        ) as exc:
            raise ZovarkValidationError(
                f"investigation_memory verification failed for {entry['evidence_id']}: {exc}"
            ) from exc
        if metadata.content_hash != entry["hash"]:
            raise ZovarkValidationError(
                "investigation_memory verified hash does not match evidence hash"
            )
