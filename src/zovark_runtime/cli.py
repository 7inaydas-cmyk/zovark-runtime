"""Command-line interface for the Phase 1 runtime skeleton."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

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

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
