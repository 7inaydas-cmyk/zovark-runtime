"""Dependency-free runtime enforcement of the proof-package JSON Schemas (Slice 8).

The runtime is zero-dependency (jsonschema is test-only), so this is a small validator
covering exactly the JSON Schema constructs the 8 `contracts/proof_package/` schemas use:
type, required, properties, additionalProperties:false, enum, const, pattern, minItems,
items, minimum, minLength, and local `$ref` into `$defs`.

This enforces artifact SHAPE, fail-closed. It is necessary-not-sufficient:
`proof-package-verify` re-derivation remains the semantic authority and still rejects a
shape-valid semantic forgery.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from zovark_runtime.proof_package import ZovarkValidationError

# Repo root: src/zovark_runtime/proof_package/schema_enforce.py -> parents[3]
_SCHEMA_DIR = Path(__file__).resolve().parents[3] / "contracts" / "proof_package"

# artifact filename -> schema filename (the 8 JSON artifacts; customer-report.md excluded)
ARTIFACT_SCHEMAS = {
    "investigation-tape.json": "investigation-tape.schema.json",
    "evidence-ledger.json": "evidence-ledger.schema.json",
    "timeline.json": "timeline.schema.json",
    "findings.json": "findings.schema.json",
    "verdict.json": "verdict.schema.json",
    "edr-handoff.json": "edr-handoff.schema.json",
    "audit-chain-entry.json": "audit-chain-entry.schema.json",
    "replay-report.json": "replay-report.schema.json",
}

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "null": lambda v: v is None,
}


def _json_equal(a: Any, b: Any) -> bool:
    """JSON-Schema equality: booleans are a distinct type (True != 1, False != 0)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


def validate(instance: Any, schema: dict[str, Any], root: dict[str, Any], path: str = "") -> list[str]:
    """Return a list of human-readable validation errors ([] == valid)."""
    errors: list[str] = []

    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"):
            return [f"{path}: unsupported $ref {ref!r}"]
        target = root.get("$defs", {}).get(ref.split("/")[-1])
        if target is None:
            return [f"{path}: unresolved $ref {ref!r}"]
        return validate(instance, target, root, path)

    if "const" in schema:
        if not _json_equal(instance, schema["const"]):
            errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
        return errors

    if "enum" in schema:
        if not any(_json_equal(instance, member) for member in schema["enum"]):
            errors.append(f"{path}: {instance!r} not in enum {schema['enum']!r}")

    expected_type = schema.get("type")
    if expected_type is not None:
        check = _TYPE_CHECKS.get(expected_type)
        if check is None:
            return [f"{path}: unsupported type {expected_type!r}"]
        if not check(instance):
            return [f"{path}: expected type {expected_type}, got {type(instance).__name__}"]

    if isinstance(instance, str):
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, instance) is None:
            errors.append(f"{path}: {instance!r} does not match pattern {pattern!r}")
        min_length = schema.get("minLength")
        if min_length is not None and len(instance) < min_length:
            errors.append(f"{path}: shorter than minLength {min_length}")

    if isinstance(instance, int) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        if minimum is not None and instance < minimum:
            errors.append(f"{path}: {instance} < minimum {minimum}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    errors.append(f"{path}: additional property {key!r} not allowed")
        for key, subschema in properties.items():
            if key in instance:
                errors.extend(validate(instance[key], subschema, root, f"{path}.{key}"))

    if isinstance(instance, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(instance) < min_items:
            errors.append(f"{path}: fewer than minItems {min_items}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, item_schema, root, f"{path}[{index}]"))

    return errors


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ZovarkValidationError(f"schema_enforce: cannot read {path.name}: {exc}") from exc


def validate_artifact(artifact: Any, schema_filename: str) -> list[str]:
    schema = _load(_SCHEMA_DIR / schema_filename)
    return validate(artifact, schema, schema)


def enforce_proof_package_schemas(package_dir: str | Path) -> dict[str, str]:
    """Validate all 8 JSON artifacts against their schemas. Fail closed on any violation.

    Returns {artifact: "ok"} on success; raises ZovarkValidationError otherwise.
    """
    package = Path(package_dir)
    result: dict[str, str] = {}
    for artifact_name, schema_filename in ARTIFACT_SCHEMAS.items():
        artifact = _load(package / artifact_name)
        errors = validate_artifact(artifact, schema_filename)
        if errors:
            raise ZovarkValidationError(
                f"schema_enforce: {artifact_name} failed schema: {errors[0]}"
            )
        result[artifact_name] = "ok"
    return result
