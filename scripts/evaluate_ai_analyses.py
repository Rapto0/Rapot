"""
Command line evaluation report for persisted AI analyses.
"""

from __future__ import annotations

import argparse
import json

from ai_evaluation import (
    DEFAULT_EVAL_HORIZONS,
    DEFAULT_PRIMARY_HORIZON_DAYS,
    build_ai_quality_report,
    format_ai_quality_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI analiz kalite raporu uretir.")
    parser.add_argument("--since-days", type=int, default=90, help="Kac gun geriye bakilacak.")
    parser.add_argument(
        "--market-type",
        type=str,
        default=None,
        help="BIST, Kripto veya bos birak.",
    )
    parser.add_argument(
        "--special-tag",
        type=str,
        default=None,
        help="BELES, COK_UCUZ, PAHALI, FAHIS_FIYAT veya bos birak.",
    )
    parser.add_argument(
        "--include-manual",
        action="store_true",
        help="MANUAL_* AI analizlerini de rapora dahil et.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Maksimum analiz kaydi sayisi.")
    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=list(DEFAULT_EVAL_HORIZONS),
        help="Ileri performans gunleri. Ornek: --horizons 3 7 14",
    )
    parser.add_argument(
        "--primary-horizon",
        type=int,
        default=DEFAULT_PRIMARY_HORIZON_DAYS,
        help="Ana KPI olarak kullanilacak horizon.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Raporu JSON olarak yazdir.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_ai_quality_report(
        since_days=args.since_days,
        market_type=args.market_type,
        special_tag=args.special_tag,
        include_manual=args.include_manual,
        limit=args.limit,
        horizons=tuple(sorted(set(args.horizons))),
        primary_horizon_days=args.primary_horizon,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_ai_quality_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
