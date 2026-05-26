"""Replay compatibility row mapping helpers for canonical failure records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def replay_compatibility_row_id_for_failure_record(
    failure_record: Mapping[str, Any],
    failure_outcome_rows: Iterable[Mapping[str, Any]],
) -> str | None:
    """Map a canonical replay failure record to one architecture row ID."""

    failure_code = failure_record.get("failure_code")
    if not isinstance(failure_code, str):
        return None

    matching_rows = [
        row
        for row in failure_outcome_rows
        if _row_declares_failure_code(row, failure_code)
    ]
    if len(matching_rows) != 1:
        return None

    row = matching_rows[0]
    row_id = row.get("row_id")
    if not isinstance(row_id, str) or not row_id:
        return None

    if not _matches_row_field(
        failure_record,
        failure_record_key="failure_category",
        row=row,
        row_key="compatibility_dimension",
    ):
        return None
    if not _matches_row_field(
        failure_record,
        failure_record_key="component",
        row=row,
        row_key="component",
    ):
        return None

    return row_id


def _row_declares_failure_code(row: Mapping[str, Any], failure_code: str) -> bool:
    failure_codes = row.get("failure_codes")
    return isinstance(failure_codes, list) and failure_code in failure_codes


def _matches_row_field(
    failure_record: Mapping[str, Any],
    *,
    failure_record_key: str,
    row: Mapping[str, Any],
    row_key: str,
) -> bool:
    row_value = row.get(row_key)
    if row_value is None:
        return True
    return isinstance(row_value, str) and failure_record.get(failure_record_key) == row_value
