#!/usr/bin/env python3
"""
Backfill explicit special_tag values for historical signal rows.

Usage examples:
  python scripts/backfill_special_tags.py --dry-run
  python scripts/backfill_special_tags.py --since-hours 168
  python scripts/backfill_special_tags.py --market-type BIST
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ensure_repo_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill missing special_tag values")
    parser.add_argument(
        "--since-hours",
        type=int,
        default=None,
        help="Only process rows newer than N hours (default: all rows)",
    )
    parser.add_argument(
        "--market-type",
        type=str,
        default="BIST",
        help="Market filter (default: BIST). Use empty string for all markets.",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default=None,
        help="Optional strategy filter",
    )
    parser.add_argument(
        "--window-seconds",
        type=int,
        default=900,
        help="Time intersection window in seconds (default: 900)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not update DB, only print what would change",
    )
    parser.add_argument(
        "--override-existing",
        action="store_true",
        help="Also overwrite non-empty special_tag rows",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON result",
    )
    return parser.parse_args()


def main() -> int:
    _ensure_repo_on_path()

    from database import backfill_special_tags, get_special_tag_coverage

    args = parse_args()
    market_type = args.market_type.strip() or None
    strategy = args.strategy.strip().upper() if args.strategy else None
    if strategy and strategy not in {"COMBO", "HUNTER"}:
        print("Invalid --strategy value. Use COMBO or HUNTER.", file=sys.stderr)
        return 2

    result = backfill_special_tags(
        since_hours=args.since_hours,
        market_type=market_type,
        strategy=strategy,
        window_seconds=args.window_seconds,
        dry_run=args.dry_run,
        override_existing=args.override_existing,
    )

    print(
        f"Backfill done | dry_run={result['dry_run']} "
        f"total_candidates={result['total_candidates']} total_updated={result['total_updated']}"
    )
    for row in result["rows"]:
        if row["candidates"] <= 0:
            continue
        print(
            f"- {row['strategy']} {row['tag']} ({row['target_timeframe']}): "
            f"candidates={row['candidates']} updated={row['updated']}"
        )

    coverage = get_special_tag_coverage(
        since_hours=args.since_hours,
        market_type=market_type,
        strategy=strategy,
        window_seconds=args.window_seconds,
    )
    missing_total = sum(int(row.get("missing", 0)) for row in coverage)
    print(f"Coverage missing_total={missing_total}")

    if args.json:
        print(json.dumps({"backfill": result, "coverage": coverage}, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
