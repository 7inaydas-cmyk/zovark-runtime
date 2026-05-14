from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from zovark_runtime.context_memory.errors import (
    ContextMemoryValidationError,
    RangeValidationError,
    RetrievalResultValidationError,
)
from zovark_runtime.context_memory.ranges import validate_range, validate_ranges
from zovark_runtime.context_memory.retrieval_result import validate_retrieval_result
from zovark_runtime.phase import CONTEXT_MEMORY_VALIDATOR_STATUS, INVESTIGATION_MEMORY_STATUS


VALID_BYTE_RANGE = {"range_type": "byte", "start": 0, "end": 1}
VALID_LINE_RANGE = {"range_type": "line", "start_line": 1, "end_line": 1}
VALID_RECORD_ID_RANGE = {"range_type": "record", "record_id": "rec-001"}
VALID_RECORD_INDEX_RANGE = {"range_type": "record", "record_index": 0}


def assert_range_invalid(range_obj: object) -> None:
    with pytest.raises(RangeValidationError):
        validate_range(range_obj)  # type: ignore[arg-type]


def assert_result_invalid(result: object) -> None:
    with pytest.raises(RetrievalResultValidationError):
        validate_retrieval_result(result)  # type: ignore[arg-type]


def test_validation_errors_have_expected_inheritance() -> None:
    assert issubclass(RangeValidationError, ContextMemoryValidationError)
    assert issubclass(RetrievalResultValidationError, ContextMemoryValidationError)


@pytest.mark.parametrize(
    "range_obj",
    [
        {"range_type": "byte", "start": 2, "end": 1},
        {"range_type": "byte", "start": 1, "end": 1},
        {"range_type": "byte", "start": -1, "end": 1},
        {"range_type": "byte", "start": 0, "end": -1},
        {"range_type": "byte", "start": True, "end": 1},
        {"range_type": "byte", "start": 0, "end": False},
        {"range_type": "byte", "end": 1},
        {"range_type": "byte", "start": 0},
        {"range_type": "byte", "start": 0, "end": 1, "extra": "bad"},
        {"range_type": "line", "start_line": 2, "end_line": 1},
        {"range_type": "line", "start_line": -1, "end_line": 1},
        {"range_type": "line", "start_line": 0, "end_line": 1},
        {"range_type": "line", "start_line": 1, "end_line": -1},
        {"range_type": "line", "start_line": 1, "end_line": 0},
        {"range_type": "line", "start_line": True, "end_line": 1},
        {"range_type": "line", "start_line": 1, "end_line": False},
        {"range_type": "line", "end_line": 1},
        {"range_type": "line", "start_line": 1},
        {"range_type": "line", "start_line": 1, "end_line": 1, "extra": "bad"},
        {"range_type": "record", "record_id": "rec-001", "record_index": 0},
        {"range_type": "record"},
        {"range_type": "record", "record_id": ""},
        {"range_type": "record", "record_index": -1},
        {"range_type": "record", "record_index": True},
        {"range_type": "record", "record_id": "rec-001", "extra": "bad"},
        {"range_type": "unknown", "start": 0, "end": 1},
        {"start": 0, "end": 1},
        "not-a-range",
    ],
)
def test_invalid_ranges(range_obj: object) -> None:
    assert_range_invalid(range_obj)


@pytest.mark.parametrize(
    "range_obj",
    [
        VALID_BYTE_RANGE,
        VALID_LINE_RANGE,
        VALID_RECORD_ID_RANGE,
        VALID_RECORD_INDEX_RANGE,
    ],
)
def test_valid_ranges(range_obj: dict[str, object]) -> None:
    validate_range(range_obj)


def test_validate_ranges_empty_behavior() -> None:
    validate_ranges([], require_non_empty=False)
    with pytest.raises(RangeValidationError):
        validate_ranges([], require_non_empty=True)


@pytest.mark.parametrize("ranges", ["not-ranges", b"not-ranges", [VALID_BYTE_RANGE, "bad"]])
def test_validate_ranges_rejects_invalid_sequences(ranges: object) -> None:
    with pytest.raises(RangeValidationError):
        validate_ranges(ranges, require_non_empty=False)  # type: ignore[arg-type]


def fulfilled_result(**overrides: object) -> dict[str, object]:
    result = {
        "status": "fulfilled",
        "model_visible": True,
        "returned_ranges": [VALID_BYTE_RANGE],
        "returned_byte_count": 1,
        "model_visible_excerpt": "bounded excerpt",
    }
    result.update(overrides)
    return result


def partial_result(**overrides: object) -> dict[str, object]:
    result = {
        "status": "partial",
        "model_visible": True,
        "returned_ranges": [VALID_LINE_RANGE],
        "returned_byte_count": 1,
        "model_visible_excerpt": "bounded excerpt",
    }
    result.update(overrides)
    return result


def denied_result(**overrides: object) -> dict[str, object]:
    result = {
        "status": "denied",
        "model_visible": False,
        "returned_ranges": [],
        "returned_byte_count": 0,
        "model_visible_excerpt": None,
        "data_unavailable_reason": "access_denied",
    }
    result.update(overrides)
    return result


def without_key(result: dict[str, object], key: str) -> dict[str, object]:
    result.pop(key)
    return result


@pytest.mark.parametrize(
    "result",
    [
        {},
        {"status": "fulfilled"},
        fulfilled_result(extra="bad"),
        fulfilled_result(status="unknown"),
        fulfilled_result(status=1),
        fulfilled_result(model_visible="true"),
        fulfilled_result(returned_ranges="not-ranges"),
        fulfilled_result(returned_byte_count=True),
        fulfilled_result(returned_byte_count=-1),
        fulfilled_result(model_visible=True, returned_ranges=[]),
        fulfilled_result(model_visible=True, returned_byte_count=0),
        without_key(fulfilled_result(model_visible=True), "model_visible_excerpt"),
        fulfilled_result(model_visible=True, model_visible_excerpt=None),
        fulfilled_result(model_visible=True, model_visible_excerpt=""),
        fulfilled_result(returned_ranges=[]),
        fulfilled_result(returned_byte_count=0),
        fulfilled_result(model_visible=False),
        partial_result(returned_ranges=[]),
        partial_result(returned_byte_count=0),
        partial_result(model_visible=False),
        denied_result(model_visible=True),
        denied_result(model_visible_excerpt="visible"),
        denied_result(returned_byte_count=1),
        without_key(denied_result(), "data_unavailable_reason"),
        denied_result(data_unavailable_reason=None),
        denied_result(data_unavailable_reason=""),
        denied_result(data_unavailable_reason="wrong_reason"),
        denied_result(status="not_found", data_unavailable_reason="access_denied"),
        denied_result(status="not_found", data_unavailable_reason="memory_not_found", model_visible=True),
        denied_result(status="range_invalid", data_unavailable_reason="access_denied"),
        denied_result(status="range_invalid", data_unavailable_reason="range_invalid", returned_byte_count=1),
        denied_result(status="unavailable", data_unavailable_reason="access_denied"),
        denied_result(
            status="unavailable",
            data_unavailable_reason="content_not_exported",
            model_visible_excerpt="visible",
        ),
        fulfilled_result(returned_ranges=[{"range_type": "byte", "start": 1, "end": 1}]),
        fulfilled_result(returned_ranges=["bad"]),
    ],
)
def test_invalid_retrieval_results(result: object) -> None:
    assert_result_invalid(result)


@pytest.mark.parametrize(
    "result",
    [
        fulfilled_result(),
        partial_result(),
        denied_result(),
        denied_result(status="not_found", data_unavailable_reason="memory_not_found"),
        denied_result(status="range_invalid", data_unavailable_reason="range_invalid"),
        denied_result(status="unavailable", data_unavailable_reason="content_not_exported"),
        denied_result(status="unavailable", data_unavailable_reason="not_applicable"),
    ],
)
def test_valid_retrieval_results(result: dict[str, object]) -> None:
    validate_retrieval_result(result)


def test_validator_status_does_not_imply_storage_or_retrieval() -> None:
    assert CONTEXT_MEMORY_VALIDATOR_STATUS == "semantic-validators-only"
    assert INVESTIGATION_MEMORY_STATUS == "not-implemented"


def test_validator_calls_create_no_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    validate_range(VALID_BYTE_RANGE)
    validate_ranges([VALID_BYTE_RANGE, VALID_LINE_RANGE], require_non_empty=True)
    validate_retrieval_result(fulfilled_result())

    assert list(tmp_path.iterdir()) == []


def test_context_memory_modules_do_not_import_live_dependencies() -> None:
    package_root = Path(__file__).resolve().parents[1] / "src" / "zovark_runtime" / "context_memory"
    forbidden_imports = [
        "boto3",
        "httpx",
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


def test_context_memory_imports_create_no_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    for module in [
        "zovark_runtime.context_memory",
        "zovark_runtime.context_memory.errors",
        "zovark_runtime.context_memory.ranges",
        "zovark_runtime.context_memory.retrieval_result",
    ]:
        importlib.import_module(module)

    assert list(tmp_path.iterdir()) == []
