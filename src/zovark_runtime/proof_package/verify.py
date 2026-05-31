"""Strict offline verification for proof packages (runtime-original).

The vendored ``package_verifier`` re-derives the handoff/audit/replay/report chain
and re-derives the verdict *from* the recorded findings, and re-checks every
evidence hash. It does **not** re-derive the findings themselves from the evidence
— so a self-consistent package whose ``findings`` were fabricated or suppressed
would pass. That is a dangerous-direction gap: the findings are the actual
reasoning step that determines the verdict and the recommended EDR action.

This module closes the chain: after the vendored re-derivation passes (which
hash-verifies the evidence), it re-derives the findings from the recorded,
hash-verified evidence ledger and requires them to match the package's
``findings.json``. Only then is a package "verified" — every artifact, including
findings, is re-derived from the recorded inputs.

Read-only; offline; no network, no model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError
from zovark_runtime.proof_package.findings import derive_findings
from zovark_runtime.proof_package.package_verifier import verify_proof_package


def verify_proof_package_strict(package_dir: str | Path) -> dict[str, Any]:
    """Verify a proof package and additionally re-derive findings from evidence.

    Raises ``ZovarkValidationError`` if the package is internally inconsistent
    (vendored verifier) OR if the recorded findings do not follow from the
    recorded evidence. Returns the verifier summary augmented with
    ``findings_rederived_from_evidence: True``.
    """

    package_path = Path(package_dir)
    # Step 1: the vendored verifier re-derives the verdict/handoff/audit/replay
    # chain and re-checks every evidence content hash. Raises on any mismatch.
    # Bound malformed-package failure modes (e.g. a maliciously deep JSON file) to a
    # clean ZovarkValidationError instead of an uncaught RecursionError/ValueError.
    try:
        summary = dict(verify_proof_package(package_path))
    except RecursionError as exc:
        raise ZovarkValidationError("malformed_json: package JSON nesting is too deep") from exc
    except ValueError as exc:
        if isinstance(exc, ZovarkValidationError):
            raise
        raise ZovarkValidationError(f"malformed_json: package contains an invalid value: {exc}") from exc

    # Step 2: re-derive findings from the (now hash-verified) evidence ledger and
    # require an exact match. This is the link the vendored verifier omits.
    ledger = _load_json(package_path / "evidence-ledger.json")
    if not isinstance(ledger, list):
        raise ZovarkValidationError(
            "findings_not_derived_from_evidence: evidence-ledger.json must be a list"
        )
    findings_artifact = _load_json(package_path / "findings.json")

    expected_findings, _expected_no_findings_flag = derive_findings({"raw_evidence": ledger})
    if findings_artifact != expected_findings:
        raise ZovarkValidationError(
            "findings_not_derived_from_evidence: findings.json does not follow from "
            "the recorded evidence ledger"
        )

    summary["findings_rederived_from_evidence"] = True
    return summary


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ZovarkValidationError(f"malformed_json: {path.name} is missing") from exc
    except json.JSONDecodeError as exc:
        raise ZovarkValidationError(f"malformed_json: {path.name} is not valid JSON") from exc
    except RecursionError as exc:
        raise ZovarkValidationError(f"malformed_json: {path.name} nesting is too deep") from exc
    except OSError as exc:
        raise ZovarkValidationError(f"malformed_json: {path.name} could not be read") from exc
