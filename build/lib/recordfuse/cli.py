"""Command-line interface for RecordFuse."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .adapters import read_records
from .config import DecisionPolicy
from .reconcile import Reconciler


def parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="recordfuse", description="Explainable entity reconciliation")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reconcile_parser = subparsers.add_parser("reconcile", help="Reconcile CSV/JSON/JSONL datasets")
    reconcile_parser.add_argument("files", nargs="*", help="Input files")
    reconcile_parser.add_argument("--input", "-i", dest="inputs", action="append", default=[])
    reconcile_parser.add_argument("--output", "-o", default=None, help="Output JSON path")
    reconcile_parser.add_argument("--match-threshold", type=float, default=0.82)
    reconcile_parser.add_argument("--ambiguous-threshold", type=float, default=0.65)
    reconcile_parser.add_argument("--identifier-threshold", type=float, default=0.55)
    reconcile_parser.add_argument("--pretty", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args(args)


def run_cli(args: Sequence[str] | None = None) -> int:
    parsed = parse_args(args)
    if parsed.command != "reconcile":
        return 1
    input_files = [*parsed.files, *parsed.inputs]
    if not input_files:
        raise SystemExit("reconcile requires at least one input file")

    records = []
    for filepath in input_files:
        records.extend(read_records(filepath))

    policy = DecisionPolicy(
        match_threshold=parsed.match_threshold,
        identifier_match_threshold=parsed.identifier_threshold,
        ambiguous_threshold=parsed.ambiguous_threshold,
    )
    result = Reconciler(policy=policy).reconcile(records)
    payload = json.dumps(
        result.to_dict(),
        indent=2 if parsed.pretty else None,
        sort_keys=True,
        ensure_ascii=False,
    )

    if parsed.output:
        output = Path(parsed.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    print(
        f"Reconciliation completed: {result.metrics['clusters']} clusters, "
        f"{result.metrics['candidate_pairs']} candidate pairs.",
        file=sys.stderr,
    )
    return 0


def main(args: Sequence[str] | None = None) -> None:
    raise SystemExit(run_cli(args))


if __name__ == "__main__":
    main()
