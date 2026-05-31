"""Command-line interface for the Phase 1 runtime skeleton."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .monolith import LocalMonolith
from .proof_status import build_proof_status


def _write_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zovark-runtime",
        description="Zovark runtime Phase 1 skeleton CLI.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("status", help="Print deterministic skeleton status.")
    subcommands.add_parser("doctor", help="Print deterministic skeleton diagnostics.")
    subcommands.add_parser("proof-status", help="Print local proof status.")

    build = subcommands.add_parser(
        "proof-package",
        help="Build the deterministic 9-file proof package from an EDR alert JSON.",
    )
    build.add_argument("--input", required=True, help="Static EDR-style JSON sample")
    build.add_argument("--output", required=True, help="Output proof-package directory")
    build.add_argument("--tenant-id", default="tenant-001", help="Tenant identifier")
    build.add_argument(
        "--memory-dir",
        default=None,
        help="investigation_memory store directory (default: <output>.memory)",
    )

    verify = subcommands.add_parser(
        "proof-package-verify",
        help="Verify an exported proof package offline (re-derivation).",
    )
    verify.add_argument("--package", required=True, help="Proof-package directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    monolith = LocalMonolith()

    if args.command == "status":
        _write_json(monolith.status())
        return 0
    if args.command == "doctor":
        _write_json(monolith.doctor())
        return 0
    if args.command == "proof-status":
        payload, exit_code = build_proof_status()
        _write_json(payload)
        return exit_code
    if args.command == "proof-package":
        return _proof_package_build(args)
    if args.command == "proof-package-verify":
        return _proof_package_verify(args)

    parser.error(f"unsupported command: {args.command}")
    return 2


def _proof_package_build(args: argparse.Namespace) -> int:
    from .proof_package import ZovarkValidationError
    from .proof_package.pipeline import run_proof_package

    input_path = Path(args.input)
    if not input_path.exists() or not input_path.is_file():
        print(f"proof-package input not found: {input_path}", file=sys.stderr)
        return 1
    try:
        result = run_proof_package(
            input_path,
            Path(args.output),
            tenant_id=args.tenant_id,
            memory_dir=args.memory_dir,
        )
    except ZovarkValidationError as exc:
        print(f"proof-package build failed: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"proof-package output error: {exc}", file=sys.stderr)
        return 4
    _write_json(result)
    return 0


def _proof_package_verify(args: argparse.Namespace) -> int:
    from .proof_package import ZovarkValidationError
    from .proof_package.package_verifier import verify_proof_package

    try:
        summary = verify_proof_package(Path(args.package))
    except ZovarkValidationError as exc:
        print(f"proof-package verification failed: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"proof-package verification error: {exc}", file=sys.stderr)
        return 4
    _write_json(dict(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
