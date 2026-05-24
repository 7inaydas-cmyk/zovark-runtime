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
    "authoritative_schemas": 23,
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


def read_architecture_baseline(root: Path) -> dict[str, str]:
    manifest_path = root / "contracts" / "contract-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "source_tag": str(manifest["source_tag"]),
        "source_commit": str(manifest["source_commit"]),
    }


def build_proof_status(
    root: Path | None = None,
    check_runner: Callable[[Path, str, Path], LocalCheckResult] = run_local_check,
) -> tuple[dict[str, object], int]:
    """Build the local proof-status payload and command exit code."""

    actual_root = root or repo_root()
    checks = [check_runner(actual_root, name, script) for name, script in PROOF_CHECK_SCRIPTS]
    failed = [check for check in checks if check.status != "pass"]

    payload: dict[str, object] = {
        "report": "local proof status",
        "runtime_proof_loop": "incomplete",
        "architecture_baseline": read_architecture_baseline(actual_root),
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
    return payload, 1 if failed else 0
