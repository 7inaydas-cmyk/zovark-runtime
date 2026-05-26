"""Local proof-status reporting for the runtime repository."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


BASELINE_INVENTORY = {
    "adr_files": 26,
    "binding_adrs": 25,
    "proposed_pending_adrs": ["ADR-0043"],
    "invariants": 39,
    "authoritative_schemas": 26,
    "replay_compatibility_contract": "architecture/replay-compatibility.yaml",
}

DEFERRED_CAPABILITIES = [
    "bounded retrieval implementation",
    "deterministic verdict/proof generation",
    "AlertForge scenario validation",
    "benchmark report script",
    "autonomous-dispatch capability",
    "customer/production rollout",
]

PROOF_CHECK_SCRIPTS = [
    ("contract_manifest", Path("scripts/check_contract_manifest.py")),
    ("invariant_text", Path("scripts/check_invariants.py")),
    ("no_unbounded_model_context", Path("scripts/check_no_unbounded_model_context.py")),
]


INCOMPLETE_REASON = [
    "deferred proof-chain items remain",
    "runtime completion criteria are architecture-owned or not yet explicitly defined",
    "readiness/product/production claims are not made",
]

PROOF_CHAIN_CHECKLIST_SCOPE = {
    "reporting_role": "declarative status explanation",
    "completion_definition": "not-defined-by-runtime",
    "completion_authority": "architecture-owned or undefined until explicitly specified",
    "completion_claim": "not-claimed",
    "proof_execution": "not-run-by-proof-status",
}

PROOF_CHAIN_CHECKLIST = [
    {
        "id": "scanner_fixture_schema_proof",
        "status": "satisfied",
        "proof_marker": "SCANNER_FIXTURE_SCHEMA_OK",
        "test_file_path": "tests/test_scanner_finding_fixture.py",
        "contract_paths": ["contracts/scanner_finding_envelope.schema.json"],
        "fixture_paths": ["tests/fixtures/scanner_finding_minimal.json"],
    },
    {
        "id": "verdict_envelope_fixture_schema_proof",
        "status": "satisfied",
        "proof_marker": "VERDICT_FIXTURE_SCHEMA_OK",
        "test_file_path": "tests/test_verdict_envelope_fixture.py",
        "contract_paths": [
            "contracts/verdict_envelope.schema.json",
            "contracts/recommended_action.schema.json",
            "contracts/finding.schema.json",
        ],
        "fixture_paths": ["tests/fixtures/verdict_envelope_minimal.json"],
    },
    {
        "id": "verdict_input_fixture_schema_proof",
        "status": "satisfied",
        "proof_marker": "VERDICT_INPUT_FIXTURE_SCHEMA_OK",
        "test_file_path": "tests/test_verdict_input_fixture.py",
        "contract_paths": [
            "contracts/verdict_input.schema.json",
            "contracts/scanner_finding_envelope.schema.json",
        ],
        "fixture_paths": ["tests/fixtures/verdict_input_minimal.json"],
    },
    {
        "id": "replay_record_fixture_schema_proof",
        "status": "satisfied",
        "proof_marker": "REPLAY_RECORD_FIXTURE_SCHEMA_OK",
        "test_file_path": "tests/test_replay_record_fixture.py",
        "contract_paths": [
            "contracts/replay_record.schema.json",
            "contracts/verdict_input.schema.json",
        ],
        "fixture_paths": ["tests/fixtures/replay_record_minimal.json"],
    },
    {
        "id": "deterministic_verdict_derivation_proof",
        "status": "satisfied",
        "proof_marker": "DETERMINISTIC_VERDICT_DERIVATION_OK",
        "test_file_path": "tests/test_deterministic_verdict_derivation.py",
        "runtime_artifact_paths": ["src/zovark_runtime/verdict_derivation.py"],
        "contract_paths": [
            "contracts/verdict_input.schema.json",
            "contracts/verdict_envelope.schema.json",
        ],
        "fixture_paths": [
            "tests/fixtures/verdict_input_minimal.json",
            "tests/fixtures/verdict_envelope_expected_from_minimal_input.json",
        ],
    },
    {
        "id": "minimal_replay_validation_proof",
        "status": "satisfied",
        "proof_marker": "REPLAY_VALIDATION_PROOF_OK",
        "test_file_path": "tests/test_replay_validation.py",
        "runtime_artifact_paths": ["src/zovark_runtime/replay_validation.py"],
        "contract_paths": [
            "contracts/replay_record.schema.json",
            "contracts/verdict_input.schema.json",
            "contracts/verdict_envelope.schema.json",
        ],
        "fixture_paths": [
            "tests/fixtures/replay_record_expected_minimal.json",
            "tests/fixtures/verdict_input_minimal.json",
            "tests/fixtures/verdict_envelope_expected_from_minimal_input.json",
        ],
    },
    {
        "id": "replay_validation_fail_closed_cases",
        "status": "satisfied",
        "proof_marker": "REPLAY_VALIDATION_FAIL_CLOSED_CASES_OK",
        "test_file_path": "tests/test_replay_validation.py",
        "runtime_artifact_paths": ["src/zovark_runtime/replay_validation.py"],
        "expected_count": {
            "name": "replay_validation_fail_closed_cases",
            "value": 9,
            "source": "tests/test_replay_validation.py::REPLAY_VALIDATION_FAIL_CLOSED_CASES",
        },
    },
    {
        "id": "replay_compatibility_matrix_schema_validation",
        "status": "satisfied",
        "proof_marker": "REPLAY_COMPATIBILITY_MATRIX_SCHEMA_OK",
        "test_file_path": "tests/test_replay_compatibility_contract.py",
        "yaml_artifact_path": "contracts/replay-compatibility.yaml",
        "schema_artifact_path": "contracts/replay-compatibility.schema.json",
        "architecture_source_commit": "34c42ebb24b69098159ddccbbcae981d0abe74af",
        "source_hashes": {
            "contracts/replay-compatibility.yaml": "be265c93bc9e5f1ea35c6edd3a6bba1b6a44822dae7b807985a5b058fddf0c03",
            "contracts/replay-compatibility.schema.json": "11e6bcf10d54e0e07b51632fa3cc17f8e45311e50be4a4823ca3d53cfa863d92",
        },
    },
    {
        "id": "replay_failure_record_schema_validation",
        "status": "satisfied",
        "proof_marker": "REPLAY_FAILURE_RECORD_SCHEMA_OK",
        "test_file_path": "tests/test_replay_failure_record_contract.py",
        "contract_paths": ["contracts/replay_failure_record.schema.json"],
        "architecture_source_commit": "34c42ebb24b69098159ddccbbcae981d0abe74af",
        "source_hashes": {
            "contracts/replay_failure_record.schema.json": "55e867373d5094f4aae91acd8fc524f6178664fcf64f1a4fa30b9e90b248b2f1",
        },
    },
    {
        "id": "contract_metaschema_validation",
        "status": "satisfied",
        "proof_marker": "CONTRACT_METASCHEMA_OK",
        "test_file_path": "tests/test_contract_schema_meta_validation.py",
        "expected_count": {
            "name": "contract_schema_files",
            "value": 11,
            "source": "contracts/*.schema.json",
        },
    },
    {
        "id": "runtime_replay_compatibility_coverage_mapping",
        "status": "deferred",
        "deferred_reason": "runtime imports replay compatibility and replay failure contracts, but coverage mapping from local validation cases to canonical failure codes and architecture-defined matrix rows remains deferred",
        "milestone_or_queue_position": "after canonical replay failure contract import",
        "architecture_authority": [
            "ADR-0047",
            "INV-036",
            "architecture/replay-compatibility.yaml",
            "architecture/blueprint/schemas/replay_failure_record.schema.json",
            "https://github.com/7inaydas-cmyk/zovark-architecture/issues/55",
        ],
        "authority_required": "runtime mapping proof must land separately before runtime claims replay compatibility coverage",
        "completion_note": "runtime is not claiming proof-loop completion",
    },
    {
        "id": "runtime_replay_failure_code_mapping",
        "status": "deferred",
        "deferred_reason": "canonical replay failure-code authority is imported, but runtime validation result codes are not yet mapped to canonical replay failure records",
        "milestone_or_queue_position": "after canonical replay failure contract import",
        "architecture_authority": [
            "ADR-0047",
            "INV-036",
            "architecture/blueprint/schemas/replay_failure_record.schema.json",
            "https://github.com/7inaydas-cmyk/zovark-architecture/issues/55",
        ],
        "authority_required": "runtime mapping proof must land separately before runtime emits canonical replay failure records",
        "completion_note": "runtime is not claiming proof-loop completion",
    },
    {
        "id": "audit_chain_output",
        "status": "deferred",
        "deferred_reason": "runtime does not emit audit-chain output from investigation state",
        "milestone_or_queue_position": "M5 / after runtime investigation state exists",
        "architecture_authority": ["ADR-0046", "INV-035", "INV-039"],
        "authority_required": "audit-chain runtime scope and storage semantics must be implemented separately",
        "completion_note": "runtime is not claiming proof-loop completion",
    },
    {
        "id": "runtime_investigation_execution",
        "status": "deferred",
        "deferred_reason": "runtime investigation execution is not implemented",
        "milestone_or_queue_position": "after proof-chain contract and fixture proofs; before end-to-end validation",
        "architecture_authority": ["PHASE_PLAN.md"],
        "authority_required": "runtime investigation scope must be explicitly authorized before proof-status can treat it as proof-chain evidence",
        "completion_note": "runtime is not claiming proof-loop completion",
    },
    {
        "id": "alertforge_scenario_validation",
        "status": "deferred",
        "deferred_reason": "AlertForge scenario validation is not imported or executed by runtime",
        "milestone_or_queue_position": "after runtime investigation execution boundary is defined",
        "architecture_authority": ["PHASE_PLAN.md"],
        "authority_required": "AlertForge contract and scenario execution scope must land separately",
        "completion_note": "runtime is not claiming proof-loop completion",
    },
    {
        "id": "benchmark_proof",
        "status": "deferred",
        "deferred_reason": "benchmark proof is not meaningful before end-to-end validation exists",
        "milestone_or_queue_position": "PHASE_PLAN.md Phase 6",
        "architecture_authority": ["ADR-0046", "ADR-0052", "INV-022"],
        "authority_required": "benchmark harness and measured artifacts must land separately",
        "completion_note": "runtime is not claiming proof-loop completion",
    },
    {
        "id": "dashboard_and_external_claims",
        "status": "deferred",
        "deferred_reason": "external claim surfaces are outside the current runtime proof chain",
        "milestone_or_queue_position": "after benchmark-backed evidence and explicit product scope",
        "architecture_authority": ["ADR-0052", "INV-022", "PHASE_PLAN.md"],
        "authority_required": "external claim surfaces require separate architecture/product authorization and evidence",
        "completion_note": "runtime is not claiming proof-loop completion",
    },
    {
        "id": "production_sla_compliance_workflows",
        "status": "deferred",
        "deferred_reason": "operational workflows and commitments are outside this runtime proof repository state",
        "milestone_or_queue_position": "not in current proof-chain queue",
        "architecture_authority": ["ADR-0050", "INV-022"],
        "authority_required": "operational commitment scope requires separate architecture and evidence",
        "completion_note": "runtime is not claiming proof-loop completion",
    },
]


@dataclass(frozen=True)
class LocalCheckResult:
    """Result for one local proof check."""

    name: str
    status: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }


def repo_root() -> Path:
    """Return the repository root for local source-tree execution."""

    return Path(__file__).resolve().parents[2]


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"zovark_runtime_local_check_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _exit_code_from_system_exit(exc: SystemExit) -> int:
    if exc.code is None:
        return 0
    if isinstance(exc.code, int):
        return exc.code
    return 1


def _run_script_main(path: Path) -> tuple[int, str]:
    module = _load_module(path)
    main_func = getattr(module, "main", None)
    if not callable(main_func):
        return 1, f"{path}: missing main()"

    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main_func()
    except SystemExit as exc:
        code = _exit_code_from_system_exit(exc)
        if isinstance(exc.code, str):
            stderr.write(str(exc.code))
    except Exception as exc:  # pragma: no cover - defensive reporting path
        return 1, f"{type(exc).__name__}: {exc}"
    else:
        code = int(result or 0)

    detail = "\n".join(part.strip() for part in (stdout.getvalue(), stderr.getvalue()) if part.strip())
    return code, detail or "completed"


def run_local_check(root: Path, name: str, script_rel_path: Path) -> LocalCheckResult:
    """Run one existing local check script and summarize the result."""

    script_path = root / script_rel_path
    if not script_path.is_file():
        return LocalCheckResult(name=name, status="fail", detail=f"{script_rel_path}: missing")

    code, detail = _run_script_main(script_path)
    status = "pass" if code == 0 else "fail"
    return LocalCheckResult(name=name, status=status, detail=detail)


def pytest_availability() -> dict[str, str]:
    """Report pytest availability without running tests."""

    if importlib.util.find_spec("pytest") is None:
        return {
            "status": "not-run",
            "detail": "PYTEST_NOT_RUN: pytest is not installed in this environment",
        }
    return {
        "status": "available",
        "detail": "pytest is importable; proof-status does not run test suites",
    }


def read_architecture_baseline(root: Path) -> tuple[dict[str, object], bool]:
    manifest_path = root / "contracts" / "contract-manifest.json"
    rel_path = "contracts/contract-manifest.json"

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "source_ref": str(manifest.get("source_ref", "unknown")),
            "source_tag": manifest.get("source_tag"),
            "source_commit": str(manifest["source_commit"]),
        }, True
    except FileNotFoundError:
        return {
            "status": "fail",
            "detail": f"{rel_path}: missing",
        }, False
    except json.JSONDecodeError as exc:
        return {
            "status": "fail",
            "detail": f"{rel_path}: invalid JSON: {exc.msg}",
        }, False
    except KeyError as exc:
        return {
            "status": "fail",
            "detail": f"{rel_path}: missing key {exc.args[0]}",
        }, False


def build_proof_status(
    root: Path | None = None,
    check_runner: Callable[[Path, str, Path], LocalCheckResult] = run_local_check,
) -> tuple[dict[str, object], int]:
    """Build the local proof-status payload and command exit code."""

    actual_root = root or repo_root()
    checks = [check_runner(actual_root, name, script) for name, script in PROOF_CHECK_SCRIPTS]
    failed = [check for check in checks if check.status != "pass"]
    architecture_baseline, baseline_loaded = read_architecture_baseline(actual_root)

    payload: dict[str, object] = {
        "report": "local proof status",
        "runtime_proof_loop": "incomplete",
        "incomplete_reason": INCOMPLETE_REASON,
        "proof_chain_checklist_scope": PROOF_CHAIN_CHECKLIST_SCOPE,
        "proof_chain_checklist": PROOF_CHAIN_CHECKLIST,
        "architecture_baseline": architecture_baseline,
        "baseline_inventory": BASELINE_INVENTORY,
        "local_checks": [check.as_dict() for check in checks],
        "pytest": pytest_availability(),
        "deferred_capabilities": DEFERRED_CAPABILITIES,
        "readiness_boundary": {
            "runtime_investigation_execution": "not-included",
            "live_integrations": "not-included",
            "external_commitments": "not-included",
        },
    }
    return payload, 1 if failed or not baseline_loaded else 0
