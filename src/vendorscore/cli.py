"""Command line entry: python -m vendorscore jobs.csv"""
from __future__ import annotations

import argparse
import sys

from .scorecard import DEFAULT_WEIGHTS, build_scorecard, load_jobs


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(prog="vendorscore", description="Score vendors from job history")
    parser.add_argument("csv", help="vendor job CSV")
    parser.add_argument("--min-jobs", type=int, default=10, help="completed jobs needed for a firm score")
    parser.add_argument("--weights", help="on_time,reopen,cost as fractions, for example 0.5,0.3,0.2")
    args = parser.parse_args(argv)
    try:
        weights = dict(zip(DEFAULT_WEIGHTS, map(float, args.weights.split(",")))) if args.weights else None
        card = build_scorecard(load_jobs(args.csv), weights, args.min_jobs)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    used = weights or DEFAULT_WEIGHTS
    print("weights: " + "  ".join(f"{k} {v:g}" for k, v in used.items()))
    print(card.to_string(index=False))
    return 0
