"""Command-line entry point for Audio2ViolinScore."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .doctor import doctor_report, format_human


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a2vs", description="Audio2ViolinScore Core CLI"
    )
    subparsers = parser.add_subparsers(dest="command")
    doctor_parser = subparsers.add_parser(
        "doctor", help="diagnose the local environment"
    )
    doctor_parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "doctor":
        parser.print_help()
        return 2

    report = doctor_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_human(report))
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
