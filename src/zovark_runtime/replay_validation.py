"""Minimal replay validation proof helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from zovark_runtime.verdict_derivation import canonical_json_bytes


EXPECTED_REPLAY_SCHEMA_VERSION = "1.0.0"
EXPECTED_RECORD_FORMAT_VERSION = "1.0.0"
EXPECTED_REPLAY_COMPATIBILITY_CONTRACT = "architecture/replay-compatibility.yaml"
EXPECTED_FAILURE_POLICY = "fail_closed"

OK = "REPLAY_VALIDATION_OK"
SCHEMA_INCOMPATIBLE = "REPLAY_SCHEMA_INCOMPATIBLE"
FAILURE_POLICY_INCOMPATIBLE = "REPLAY_FAILURE_POLICY_INCOMPATIBLE"
VERDICT_INPUT_MISMATCH = "REPLAY_VERDICT_INPUT_MISMATCH"
VERDICT_INPUT_HASH_MISMATCH = "REPLAY_VERDICT_INPUT_HASH_MISMATCH"
VERDICT_ENVELOPE_HASH_MISMATCH = "REPLAY_VERDICT_ENVELOPE_HASH_MISMATCH"
TOOL_CATALOG_VERSION_MISMATCH = "REPLAY_TOOL_CATALOG_VERSION_MISMATCH"
MODEL_VERSION_MISMATCH = "REPLAY_MODEL_VERSION_MISMATCH"
PROMPT_HASH_MISMATCH = "REPLAY_PROMPT_HASH_MISMATCH"
TENANT_INVESTIGATION_MISMATCH = "REPLAY_TENANT_INVESTIGATION_MISMATCH"
TOOL_RETIRED = "REPLAY_TOOL_RETIRED"

DEFAULT_CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts"
REPLAY_COMPATIBILITY_MATRIX_FILENAME = "replay-compatibility.yaml"
ARCHITECTURE_CATALOG_ARTIFACT_PREFIX = "architecture/replay/catalogs/"
RUNTIME_CATALOG_ARTIFACT_ROOT = Path("replay/catalogs")
TOOL_RETIRED_DETAIL = "recorded tool is retired under current catalog"
TOOL_RETIRED_ROW_ID = "tool_compatibility.tool_retired"
CATALOG_AUTHORITY_MISSING_DETAIL = "replay compatibility matrix artifact is missing"
CATALOG_AUTHORITY_MALFORMED_DETAIL = "replay tool catalog authority is malformed"
CATALOG_PARSER_UNAVAILABLE_DETAIL = "replay tool catalog authority parser is unavailable"
RECORDED_CATALOG_UNDECLARED_DETAIL = "recorded tool catalog version is not declared"
CURRENT_CATALOG_UNDECLARED_DETAIL = "current tool catalog version is not declared"
CATALOG_ARTIFACT_MISSING_DETAIL = "replay tool catalog artifact is missing"
CATALOG_ARTIFACT_MALFORMED_DETAIL = "replay tool catalog artifact is malformed"
RECORDED_TOOL_IDENTITY_MISSING_DETAIL = "recorded tool identity is not present in recorded catalog"
RETIREMENT_LEDGER_MISSING_DETAIL = "recorded tool is absent from current catalog without retirement authority"


@dataclass(frozen=True)
class ReplayValidationResult:
    """Result for the minimal replay proof validation boundary."""

    ok: bool
    code: str
    detail: str


def canonical_sha256_hex(payload: Mapping[str, Any]) -> str:
    """Return the SHA-256 digest of stable canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _success() -> ReplayValidationResult:
    return ReplayValidationResult(ok=True, code=OK, detail="replay record matches expected canonical inputs")


def _failure(code: str, detail: str) -> ReplayValidationResult:
    return ReplayValidationResult(ok=False, code=code, detail=detail)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _sequence(value: Any, field_name: str) -> Sequence[Any]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise TypeError(f"{field_name} must be a non-string sequence")
    return value


def _load_yaml_mapping(
    path: Path,
    *,
    missing_detail: str,
    malformed_detail: str,
) -> tuple[Mapping[str, Any] | None, str | None]:
    try:
        import yaml
    except ImportError:
        return None, CATALOG_PARSER_UNAVAILABLE_DETAIL

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError:
        return None, missing_detail
    except yaml.YAMLError:
        return None, malformed_detail

    if not isinstance(payload, Mapping):
        return None, malformed_detail
    return payload, None


def _runtime_catalog_artifact_path(contracts_root: Path, artifact_path: str) -> Path:
    if artifact_path.startswith(ARCHITECTURE_CATALOG_ARTIFACT_PREFIX):
        catalog_name = artifact_path.removeprefix(ARCHITECTURE_CATALOG_ARTIFACT_PREFIX)
        return contracts_root / RUNTIME_CATALOG_ARTIFACT_ROOT / catalog_name
    return contracts_root / artifact_path


def _catalog_artifact_path(
    matrix: Mapping[str, Any],
    *,
    catalog_version: str,
    contracts_root: Path,
    undeclared_detail: str,
) -> tuple[Path | None, str | None]:
    tool_catalog = matrix.get("tool_catalog")
    if not isinstance(tool_catalog, Mapping):
        return None, CATALOG_AUTHORITY_MALFORMED_DETAIL

    catalog_entry = tool_catalog.get(catalog_version)
    if not isinstance(catalog_entry, Mapping):
        return None, undeclared_detail

    artifact_path = catalog_entry.get("catalog_artifact")
    if not isinstance(artifact_path, str):
        return None, CATALOG_AUTHORITY_MALFORMED_DETAIL

    return _runtime_catalog_artifact_path(contracts_root, artifact_path), None


def _load_catalog_for_version(
    matrix: Mapping[str, Any],
    *,
    catalog_version: str,
    contracts_root: Path,
    undeclared_detail: str,
) -> tuple[Mapping[str, Any] | None, str | None]:
    catalog_path, error = _catalog_artifact_path(
        matrix,
        catalog_version=catalog_version,
        contracts_root=contracts_root,
        undeclared_detail=undeclared_detail,
    )
    if error is not None:
        return None, error
    assert catalog_path is not None
    return _load_yaml_mapping(
        catalog_path,
        missing_detail=CATALOG_ARTIFACT_MISSING_DETAIL,
        malformed_detail=CATALOG_ARTIFACT_MALFORMED_DETAIL,
    )


def _catalog_tool_identities(catalog: Mapping[str, Any], key: str) -> list[tuple[str, str]]:
    entries = catalog.get(key)
    if not isinstance(entries, Sequence) or isinstance(entries, str):
        return []

    identities: list[tuple[str, str]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        tool_name = entry.get("tool_name")
        tool_version = entry.get("tool_version")
        if isinstance(tool_name, str) and isinstance(tool_version, str):
            identities.append((tool_name, tool_version))
    return identities


def _retired_tools_by_identity(catalog: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    entries = catalog.get("retired_tools")
    if not isinstance(entries, Sequence) or isinstance(entries, str):
        return {}

    retired_tools: dict[tuple[str, str], Mapping[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        tool_name = entry.get("tool_name")
        tool_version = entry.get("tool_version")
        if isinstance(tool_name, str) and isinstance(tool_version, str):
            retired_tools[(tool_name, tool_version)] = entry
    return retired_tools


def _tool_io_identity(tool_io_entry: Any, index: int) -> tuple[str, str]:
    entry = _mapping(tool_io_entry, f"tool_io[{index}]")
    tool_name = entry.get("tool_name")
    tool_version = entry.get("tool_version")
    if not isinstance(tool_name, str) or not isinstance(tool_version, str):
        raise TypeError(f"tool_io[{index}] must include tool_name and tool_version")
    return tool_name, tool_version


def _retired_tool_validation_failure(
    replay_record: Mapping[str, Any],
    tool_io: Sequence[Any],
    contracts_root: Path,
) -> ReplayValidationResult | None:
    recorded_catalog_version = replay_record.get("tool_catalog_version")
    if not isinstance(recorded_catalog_version, str):
        return _failure(TOOL_CATALOG_VERSION_MISMATCH, RECORDED_CATALOG_UNDECLARED_DETAIL)

    matrix, error = _load_yaml_mapping(
        contracts_root / REPLAY_COMPATIBILITY_MATRIX_FILENAME,
        missing_detail=CATALOG_AUTHORITY_MISSING_DETAIL,
        malformed_detail=CATALOG_AUTHORITY_MALFORMED_DETAIL,
    )
    if error is not None:
        return _failure(TOOL_CATALOG_VERSION_MISMATCH, error)
    assert matrix is not None

    current_catalog_version = matrix.get("current_tool_catalog_version")
    if not isinstance(current_catalog_version, str):
        return _failure(TOOL_CATALOG_VERSION_MISMATCH, CURRENT_CATALOG_UNDECLARED_DETAIL)

    recorded_catalog, error = _load_catalog_for_version(
        matrix,
        catalog_version=recorded_catalog_version,
        contracts_root=contracts_root,
        undeclared_detail=RECORDED_CATALOG_UNDECLARED_DETAIL,
    )
    if error is not None:
        return _failure(TOOL_CATALOG_VERSION_MISMATCH, error)
    assert recorded_catalog is not None

    current_catalog, error = _load_catalog_for_version(
        matrix,
        catalog_version=current_catalog_version,
        contracts_root=contracts_root,
        undeclared_detail=CURRENT_CATALOG_UNDECLARED_DETAIL,
    )
    if error is not None:
        return _failure(TOOL_CATALOG_VERSION_MISMATCH, error)
    assert current_catalog is not None

    recorded_active_tools = _catalog_tool_identities(recorded_catalog, "tools")
    current_active_tools = _catalog_tool_identities(current_catalog, "tools")
    current_retired_tools = _retired_tools_by_identity(current_catalog)

    for index, tool_io_entry in enumerate(tool_io):
        try:
            identity = _tool_io_identity(tool_io_entry, index)
        except TypeError as exc:
            return _failure(SCHEMA_INCOMPATIBLE, str(exc))

        if identity not in recorded_active_tools:
            return _failure(TOOL_CATALOG_VERSION_MISMATCH, RECORDED_TOOL_IDENTITY_MISSING_DETAIL)
        if identity in current_active_tools:
            continue

        retired_entry = current_retired_tools.get(identity)
        if retired_entry is None:
            return _failure(TOOL_CATALOG_VERSION_MISMATCH, RETIREMENT_LEDGER_MISSING_DETAIL)
        if (
            retired_entry.get("failure_code") == TOOL_RETIRED
            and retired_entry.get("row_id") == TOOL_RETIRED_ROW_ID
        ):
            return _failure(TOOL_RETIRED, TOOL_RETIRED_DETAIL)
        return _failure(TOOL_CATALOG_VERSION_MISMATCH, RETIREMENT_LEDGER_MISSING_DETAIL)

    return None


def validate_replay_record(
    replay_record: Mapping[str, Any],
    expected_verdict_input: Mapping[str, Any],
    expected_verdict_envelope: Mapping[str, Any],
    *,
    contracts_root: str | Path | None = None,
) -> ReplayValidationResult:
    """Validate one recorded replay proof against already-loaded expected artifacts."""

    try:
        recorded_verdict_input = _mapping(replay_record.get("verdict_input"), "verdict_input")
    except TypeError as exc:
        return _failure(SCHEMA_INCOMPATIBLE, str(exc))

    if "prompt_hashes" not in replay_record:
        return _failure(PROMPT_HASH_MISMATCH, "prompt hashes are missing")
    try:
        prompt_hashes = _sequence(replay_record.get("prompt_hashes"), "prompt_hashes")
    except TypeError as exc:
        return _failure(PROMPT_HASH_MISMATCH, str(exc))

    if replay_record.get("schema_version") != EXPECTED_REPLAY_SCHEMA_VERSION:
        return _failure(SCHEMA_INCOMPATIBLE, "replay schema_version is incompatible")
    if replay_record.get("record_format_version") != EXPECTED_RECORD_FORMAT_VERSION:
        return _failure(SCHEMA_INCOMPATIBLE, "replay record_format_version is incompatible")
    if replay_record.get("replay_compatibility_contract") != EXPECTED_REPLAY_COMPATIBILITY_CONTRACT:
        return _failure(SCHEMA_INCOMPATIBLE, "replay compatibility contract is incompatible")
    if replay_record.get("failure_policy") != EXPECTED_FAILURE_POLICY:
        return _failure(FAILURE_POLICY_INCOMPATIBLE, "replay record does not fail closed")

    if canonical_json_bytes(recorded_verdict_input) != canonical_json_bytes(expected_verdict_input):
        return _failure(VERDICT_INPUT_MISMATCH, "recorded verdict_input differs from expected verdict input")

    verdict_input_hash = canonical_sha256_hex(expected_verdict_input)
    if replay_record.get("verdict_input_hash") != verdict_input_hash:
        return _failure(VERDICT_INPUT_HASH_MISMATCH, "verdict_input_hash does not match canonical input")

    verdict_envelope_hash = canonical_sha256_hex(expected_verdict_envelope)
    if replay_record.get("verdict_envelope_hash") != verdict_envelope_hash:
        return _failure(
            VERDICT_ENVELOPE_HASH_MISMATCH,
            "verdict_envelope_hash does not match canonical envelope",
        )

    if replay_record.get("tool_catalog_version") != expected_verdict_input.get("tool_catalog_version"):
        return _failure(TOOL_CATALOG_VERSION_MISMATCH, "tool catalog version differs from verdict input")
    tool_io_value = replay_record.get("tool_io")
    if tool_io_value:
        try:
            tool_io = _sequence(tool_io_value, "tool_io")
        except TypeError as exc:
            return _failure(SCHEMA_INCOMPATIBLE, str(exc))
        retired_tool_failure = _retired_tool_validation_failure(
            replay_record,
            tool_io,
            Path(contracts_root) if contracts_root is not None else DEFAULT_CONTRACTS_ROOT,
        )
        if retired_tool_failure is not None:
            return retired_tool_failure

    if replay_record.get("model_version") != expected_verdict_input.get("model_version"):
        return _failure(MODEL_VERSION_MISMATCH, "model version differs from verdict input")
    if replay_record.get("decoding_params") != expected_verdict_input.get("decoding_params"):
        return _failure(MODEL_VERSION_MISMATCH, "decoding parameters differ from verdict input")
    if list(prompt_hashes) != [expected_verdict_input.get("prompt_hash")]:
        return _failure(PROMPT_HASH_MISMATCH, "prompt hashes do not match verdict input prompt hash")

    for field_name in ("tenant_id", "investigation_id"):
        if replay_record.get(field_name) != expected_verdict_input.get(field_name):
            return _failure(TENANT_INVESTIGATION_MISMATCH, f"{field_name} differs from verdict input")
        if replay_record.get(field_name) != expected_verdict_envelope.get(field_name):
            return _failure(TENANT_INVESTIGATION_MISMATCH, f"{field_name} differs from verdict envelope")

    return _success()
