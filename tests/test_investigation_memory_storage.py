from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from zovark_runtime.investigation_memory import (
    LocalInvestigationMemoryStore,
    MemoryObjectMetadata,
    MemoryObjectNotFoundError,
    MemoryObjectTamperError,
    MemoryObjectValidationError,
    build_memory_ref_id,
    sha256_hex,
)
from zovark_runtime.phase import (
    INVESTIGATION_MEMORY_RETRIEVAL_STATUS,
    INVESTIGATION_MEMORY_STORAGE_STATUS,
)


FORBIDDEN_MODEL_VISIBLE_KEYS = {
    "envelope_hash",
    "model_visible",
    "model_visible_excerpt",
    "proof_package",
    "retrieval_request_id",
    "retrieval_result_id",
    "returned_ranges",
}


def test_store_bytes_losslessly_and_verify(tmp_path: Path) -> None:
    store = LocalInvestigationMemoryStore(tmp_path)
    content = b"exact original bytes\nsecond line\n"

    metadata = store.put_bytes(
        content,
        investigation_id="inv_001",
        source_tool_call_ref="tool_001",
        content_encoding="utf-8",
        source_capability_ref="capability:local",
        execution_status="succeeded",
        trace_ref="trace:001",
        line_range_index_available=True,
        record_range_index_available=False,
    )

    assert metadata.content_hash == sha256_hex(content)
    assert metadata.content_size_bytes == len(content)
    assert metadata.content_encoding == "utf-8"
    assert metadata.line_range_index_available is True
    assert metadata.record_range_index_available is False
    assert store.read_bytes_for_verification(metadata.memory_ref_id) == content
    assert store.verify(metadata.memory_ref_id) == metadata


def test_memory_ref_id_is_deterministic(tmp_path: Path) -> None:
    store = LocalInvestigationMemoryStore(tmp_path)
    content = b"same content"

    first = store.put_bytes(content, investigation_id="inv_001", source_tool_call_ref="tool_001")
    second = store.put_bytes(content, investigation_id="inv_001", source_tool_call_ref="tool_001")

    expected_hash = sha256_hex(content)
    expected_ref = build_memory_ref_id(
        investigation_id="inv_001",
        source_tool_call_ref="tool_001",
        content_hash=expected_hash,
    )
    assert first.memory_ref_id == second.memory_ref_id == expected_ref


def test_same_identity_rejects_conflicting_metadata(tmp_path: Path) -> None:
    store = LocalInvestigationMemoryStore(tmp_path)
    content = b"same content"

    store.put_bytes(content, investigation_id="inv_001", source_tool_call_ref="tool_001")

    with pytest.raises(MemoryObjectValidationError):
        store.put_bytes(
            content,
            investigation_id="inv_001",
            source_tool_call_ref="tool_001",
            source_capability_ref="capability:local",
        )


def test_changed_content_changes_hash_and_memory_ref(tmp_path: Path) -> None:
    store = LocalInvestigationMemoryStore(tmp_path)

    first = store.put_bytes(b"first", investigation_id="inv_001", source_tool_call_ref="tool_001")
    second = store.put_bytes(b"second", investigation_id="inv_001", source_tool_call_ref="tool_001")

    assert first.content_hash != second.content_hash
    assert first.memory_ref_id != second.memory_ref_id


def valid_metadata(**overrides: object) -> MemoryObjectMetadata:
    content = b"metadata"
    content_hash = sha256_hex(content)
    data: dict[str, object] = {
        "memory_ref_id": build_memory_ref_id(
            investigation_id="inv_001",
            source_tool_call_ref="tool_001",
            content_hash=content_hash,
        ),
        "investigation_id": "inv_001",
        "source_tool_call_ref": "tool_001",
        "content_hash": content_hash,
        "content_size_bytes": len(content),
        "content_encoding": "bytes",
    }
    data.update(overrides)
    return MemoryObjectMetadata(**data)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "overrides",
    [
        {"memory_ref_id": ""},
        {"investigation_id": "bad/slash"},
        {"source_tool_call_ref": "bad/slash"},
        {"content_hash": "not-a-hash"},
        {"content_hash": "A" * 64},
        {"content_size_bytes": True},
        {"content_size_bytes": -1},
        {"content_encoding": "vendor-format"},
        {"source_capability_ref": "bad/slash"},
        {"source_input_hash": "not-a-hash"},
        {"source_output_hash": "not-a-hash"},
        {"execution_status": "bad/slash"},
        {"trace_ref": "bad/slash"},
        {"line_range_index_available": "false"},
        {"record_range_index_available": 0},
    ],
)
def test_metadata_validation_rejects_invalid_values(overrides: dict[str, object]) -> None:
    with pytest.raises(MemoryObjectValidationError):
        valid_metadata(**overrides)


@pytest.mark.parametrize("content_encoding", ["bytes", "utf-8", "json-lines", "json-records", "unknown"])
def test_metadata_accepts_allowed_content_encodings(content_encoding: str) -> None:
    metadata = valid_metadata(content_encoding=content_encoding)
    assert metadata.content_encoding == content_encoding


def test_identity_helpers_validate_hash_and_refs() -> None:
    digest = sha256_hex(b"content")

    assert len(digest) == 64
    assert digest == digest.lower()
    assert build_memory_ref_id(
        investigation_id="inv_001",
        source_tool_call_ref="tool_001",
        content_hash=digest,
    ).startswith("mem:v1:inv_001:tool_001:sha256:")

    with pytest.raises(MemoryObjectValidationError):
        sha256_hex("content")  # type: ignore[arg-type]
    with pytest.raises(MemoryObjectValidationError):
        build_memory_ref_id(investigation_id="bad/slash", source_tool_call_ref="tool_001", content_hash=digest)
    with pytest.raises(MemoryObjectValidationError):
        build_memory_ref_id(investigation_id="inv_001", source_tool_call_ref="tool_001", content_hash="bad")


def test_metadata_json_is_deterministic_and_contains_no_absolute_paths() -> None:
    metadata = valid_metadata(source_capability_ref="cap:001", trace_ref="trace:001")

    parsed = json.loads(metadata.to_json())

    assert list(parsed) == sorted(parsed)
    assert not any(Path(str(value)).is_absolute() for value in parsed.values() if isinstance(value, str))
    assert "created_at" not in parsed
    assert "timestamp" not in parsed
    assert "root_dir" not in parsed
    assert "path" not in parsed


def test_verify_detects_content_tampering(tmp_path: Path) -> None:
    store = LocalInvestigationMemoryStore(tmp_path)
    metadata = store.put_bytes(b"original", investigation_id="inv_001", source_tool_call_ref="tool_001")

    store._content_path(metadata.content_hash).write_bytes(b"tampered")

    with pytest.raises(MemoryObjectTamperError):
        store.verify(metadata.memory_ref_id)


def test_verify_detects_metadata_size_mismatch(tmp_path: Path) -> None:
    store = LocalInvestigationMemoryStore(tmp_path)
    metadata = store.put_bytes(b"original", investigation_id="inv_001", source_tool_call_ref="tool_001")
    metadata_path = store._metadata_path(metadata.memory_ref_id)
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    data["content_size_bytes"] = metadata.content_size_bytes + 1
    metadata_path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")

    with pytest.raises(MemoryObjectTamperError):
        store.verify(metadata.memory_ref_id)


def test_missing_object_raises_not_found(tmp_path: Path) -> None:
    missing_ref = build_memory_ref_id(
        investigation_id="inv_001",
        source_tool_call_ref="tool_001",
        content_hash=sha256_hex(b"missing"),
    )

    with pytest.raises(MemoryObjectNotFoundError):
        LocalInvestigationMemoryStore(tmp_path).load_metadata(missing_ref)


def test_storage_api_does_not_emit_model_visible_or_proof_fields(tmp_path: Path) -> None:
    store = LocalInvestigationMemoryStore(tmp_path)
    metadata = store.put_bytes(b"stored only", investigation_id="inv_001", source_tool_call_ref="tool_001")

    keys = set(metadata.to_dict())

    assert keys.isdisjoint(FORBIDDEN_MODEL_VISIBLE_KEYS)
    assert not hasattr(store, "retrieve")
    assert not hasattr(store, "retrieve_range")
    assert not hasattr(store, "build_envelope")
    assert not hasattr(store, "generate_proof_package")


def test_storage_status_does_not_claim_retrieval() -> None:
    assert INVESTIGATION_MEMORY_STORAGE_STATUS == "lossless-local-storage-only"
    assert INVESTIGATION_MEMORY_RETRIEVAL_STATUS == "not-implemented"


def test_investigation_memory_modules_do_not_import_live_dependencies() -> None:
    package_root = Path(__file__).resolve().parents[1] / "src" / "zovark_runtime" / "investigation_memory"
    forbidden_imports = [
        "anthropic",
        "boto3",
        "httpx",
        "openai",
        "psycopg",
        "pymongo",
        "requests",
        "socket",
        "sqlite3",
        "subprocess",
        "urllib",
    ]
    for source in package_root.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        for name in forbidden_imports:
            assert f"import {name}" not in text
            assert f"from {name}" not in text


def test_investigation_memory_imports_create_no_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    for module in [
        "zovark_runtime.investigation_memory",
        "zovark_runtime.investigation_memory.errors",
        "zovark_runtime.investigation_memory.identity",
        "zovark_runtime.investigation_memory.metadata",
        "zovark_runtime.investigation_memory.store",
    ]:
        importlib.import_module(module)

    assert list(tmp_path.iterdir()) == []
