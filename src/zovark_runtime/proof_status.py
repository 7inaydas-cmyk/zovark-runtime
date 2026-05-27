"""Local proof-status reporting for the runtime repository."""

from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


RUNTIME_PROOF_REGISTRY_DIR = Path("proof_chain/runtime")
STATUS_REGISTRY_FILE = RUNTIME_PROOF_REGISTRY_DIR / "status.json"
SATISFIED_CHECKLIST_REGISTRY_FILE = RUNTIME_PROOF_REGISTRY_DIR / "satisfied_checklist.json"
DEFERRED_CHECKLIST_REGISTRY_FILE = RUNTIME_PROOF_REGISTRY_DIR / "deferred_checklist.json"

PROOF_CHECK_SCRIPTS = [
    ("contract_manifest", Path("scripts/check_contract_manifest.py")),
    ("invariant_text", Path("scripts/check_invariants.py")),
    ("no_unbounded_model_context", Path("scripts/check_no_unbounded_model_context.py")),
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


def _load_registry_json(root: Path, rel_path: Path) -> object:
    return json.loads((root / rel_path).read_text(encoding="utf-8"))


def _load_registry_items(root: Path, rel_path: Path) -> list[dict[str, object]]:
    registry = _load_registry_json(root, rel_path)
    if not isinstance(registry, dict):
        raise RuntimeError(f"{rel_path}: registry must be an object")
    items = registry.get("items")
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise RuntimeError(f"{rel_path}: items must be a list of objects")
    return items


def _assigned_tuple_length(path: Path, assignment_name: str) -> int:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == assignment_name for target in node.targets):
            continue
        if not isinstance(node.value, ast.Tuple):
            raise RuntimeError(f"{path}: {assignment_name} must be a tuple")
        return len(node.value.elts)
    raise RuntimeError(f"{path}: missing {assignment_name}")


def _derived_count(root: Path, source: str) -> int:
    if source == "contracts/*.schema.json":
        return len(list((root / "contracts").glob("*.schema.json")))
    if source == "tests/test_replay_validation.py::REPLAY_VALIDATION_FAIL_CLOSED_CASES":
        return _assigned_tuple_length(
            root / "tests" / "test_replay_validation.py",
            "REPLAY_VALIDATION_FAIL_CLOSED_CASES",
        )
    raise RuntimeError(f"unsupported expected_count source: {source}")


def _hydrate_expected_counts(root: Path, checklist: list[dict[str, object]]) -> None:
    for item in checklist:
        expected_count = item.get("expected_count")
        if not isinstance(expected_count, dict):
            continue
        source = expected_count.get("source")
        if not isinstance(source, str):
            raise RuntimeError(f"{item.get('id', '<unknown>')}: expected_count.source must be set")
        expected_count["value"] = _derived_count(root, source)


def load_runtime_proof_registry(root: Path | None = None) -> dict[str, object]:
    """Load declarative runtime proof-chain registry files."""

    actual_root = root or repo_root()
    status = _load_registry_json(actual_root, STATUS_REGISTRY_FILE)
    if not isinstance(status, dict):
        raise RuntimeError(f"{STATUS_REGISTRY_FILE}: registry must be an object")

    checklist = [
        *_load_registry_items(actual_root, SATISFIED_CHECKLIST_REGISTRY_FILE),
        *_load_registry_items(actual_root, DEFERRED_CHECKLIST_REGISTRY_FILE),
    ]
    _hydrate_expected_counts(actual_root, checklist)

    return {
        "baseline_inventory": status["baseline_inventory"],
        "deferred_capabilities": status["deferred_capabilities"],
        "incomplete_reason": status["incomplete_reason"],
        "proof_chain_checklist_scope": status["proof_chain_checklist_scope"],
        "proof_chain_checklist": checklist,
    }


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
    registry = load_runtime_proof_registry(actual_root)

    payload: dict[str, object] = {
        "report": "local proof status",
        "runtime_proof_loop": "incomplete",
        "incomplete_reason": registry["incomplete_reason"],
        "proof_chain_checklist_scope": registry["proof_chain_checklist_scope"],
        "proof_chain_checklist": registry["proof_chain_checklist"],
        "architecture_baseline": architecture_baseline,
        "baseline_inventory": registry["baseline_inventory"],
        "local_checks": [check.as_dict() for check in checks],
        "pytest": pytest_availability(),
        "deferred_capabilities": registry["deferred_capabilities"],
        "readiness_boundary": {
            "runtime_investigation_execution": "not-included",
            "live_integrations": "not-included",
            "external_commitments": "not-included",
        },
    }
    return payload, 1 if failed or not baseline_loaded else 0
