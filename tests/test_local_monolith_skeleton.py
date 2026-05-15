from __future__ import annotations

import importlib
import json
from pathlib import Path

from zovark_runtime.cli import main
from zovark_runtime.monolith import LocalMonolith
from zovark_runtime.phase import (
    ALERTFORGE_STATUS,
    BENCHMARK_STATUS,
    CUSTOMER_READINESS_STATUS,
    INVESTIGATION_MEMORY_RETRIEVAL_STATUS,
    INVESTIGATION_MEMORY_STORAGE_STATUS,
    INVESTIGATION_MEMORY_STATUS,
    MODEL_CONTEXT_INTEGRATION_STATUS,
    PHASE,
    RUNTIME_IMPLEMENTATION_STATUS,
)


def _run_cli(args: list[str], capsys) -> dict[str, object]:
    assert main(args) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    return json.loads(captured.out)


def test_status_reports_skeleton_only() -> None:
    status = LocalMonolith().status()

    assert status["phase"] == PHASE
    assert status["runtime_implementation_status"] == RUNTIME_IMPLEMENTATION_STATUS
    assert status["runtime_implementation_status"] == "storage-substrate-only"
    assert status["investigation_memory_status"] == INVESTIGATION_MEMORY_STATUS
    assert status["investigation_memory_status"] == "storage-only-partial"
    assert status["investigation_memory_storage_status"] == INVESTIGATION_MEMORY_STORAGE_STATUS
    assert status["investigation_memory_storage_status"] == "lossless-local-storage-only"
    assert status["investigation_memory_retrieval_status"] == INVESTIGATION_MEMORY_RETRIEVAL_STATUS
    assert status["investigation_memory_retrieval_status"] == "not-implemented"
    assert status["model_context_integration_status"] == MODEL_CONTEXT_INTEGRATION_STATUS
    assert status["model_context_integration_status"] == "not-implemented"
    assert status["alertforge_status"] == ALERTFORGE_STATUS
    assert status["alertforge_status"] == "not-implemented"
    assert status["benchmark_status"] == BENCHMARK_STATUS
    assert status["benchmark_status"] == "not-implemented"
    assert status["customer_readiness_status"] == CUSTOMER_READINESS_STATUS
    assert status["customer_readiness_status"] == "blocked"


def test_status_lists_unimplemented_runtime_components() -> None:
    status = LocalMonolith().status()

    assert status["not_implemented_components"] == [
        "alertforge_ingest",
        "assessor_runtime",
        "benchmark_harness",
        "customer_readiness_workflow",
        "deterministic_envelope_generation",
        "executor_runtime",
        "investigation_memory_retrieval",
        "model_context_integration",
        "planner_runtime",
        "proof_package_generation",
        "sandbox_execute",
    ]


def test_cli_status_is_deterministic(capsys) -> None:
    first = _run_cli(["status"], capsys)
    second = _run_cli(["status"], capsys)

    assert first == second
    assert first["config"] == {
        "tenant_id": "tenant-local-dev",
        "data_dir": ".tmp/zovark-runtime",
    }


def test_cli_doctor_is_deterministic(capsys) -> None:
    first = _run_cli(["doctor"], capsys)
    second = _run_cli(["doctor"], capsys)

    assert first == second
    assert first["checks"] == [
        {
            "name": "runtime_scope",
            "status": "ok",
            "detail": "storage-substrate-only",
        },
        {
            "name": "live_integrations",
            "status": "ok",
            "detail": "not-configured",
        },
        {
            "name": "generated_outputs",
            "status": "ok",
            "detail": "not-created-by-status-or-doctor",
        },
    ]


def test_status_and_doctor_create_no_output_artifacts(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    _run_cli(["status"], capsys)
    _run_cli(["doctor"], capsys)

    assert list(tmp_path.iterdir()) == []


def test_no_network_or_live_dependency_imports_are_introduced() -> None:
    package_root = Path(__file__).resolve().parents[1] / "src" / "zovark_runtime"
    forbidden_imports = [
        "boto3",
        "http.client",
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


def test_package_modules_import_without_side_effects(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    for module in [
        "zovark_runtime",
        "zovark_runtime.cli",
        "zovark_runtime.config",
        "zovark_runtime.errors",
        "zovark_runtime.monolith",
        "zovark_runtime.phase",
    ]:
        importlib.import_module(module)

    assert list(tmp_path.iterdir()) == []
