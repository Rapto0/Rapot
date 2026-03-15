"""
Backfill empty signal.details values in trading_bot.db.

Usage:
    python scripts/backfill_signal_details.py --limit 5000
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_loader import get_bist_data, get_crypto_data, resample_market_data
from signals import calculate_combo_signal, calculate_hunter_signal


DB_PATH = ROOT_DIR / "trading_bot.db"


def _json_default(value: Any):
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def _serialize_details(details: dict[str, Any] | None) -> str:
    if not details:
        return ""
    try:
        return json.dumps(details, ensure_ascii=False, default=_json_default)
    except Exception:
        return ""


def _load_daily_data(symbol: str, market_type: str):
    if market_type == "BIST":
        return get_bist_data(symbol, start_date="01-01-2015")
    return get_crypto_data(symbol, start_str="10 years ago")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill empty signals.details values.")
    parser.add_argument("--limit", type=int, default=5000, help="Max empty rows to process.")
    parser.add_argument(
        "--mode",
        choices=("scanner-latest", "all"),
        default="scanner-latest",
        help="scanner-latest: her sembol/piyasa icin en guncel bos details kaydini doldurur; all: tum bos kayitlari (limit dahilinde) tarar.",
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()

    if args.mode == "scanner-latest":
        cur.execute(
            """
            SELECT s.id, s.symbol, s.market_type, s.strategy, s.timeframe
            FROM signals s
            INNER JOIN (
                SELECT symbol, market_type, MAX(created_at) AS max_created_at
                FROM signals
                GROUP BY symbol, market_type
            ) latest
              ON latest.symbol = s.symbol
             AND latest.market_type = s.market_type
             AND latest.max_created_at = s.created_at
            WHERE s.details IS NULL OR TRIM(s.details) = ''
            ORDER BY s.id DESC
            LIMIT ?
            """,
            (args.limit,),
        )
    else:
        cur.execute(
            """
            SELECT id, symbol, market_type, strategy, timeframe
            FROM signals
            WHERE details IS NULL OR TRIM(details) = ''
            ORDER BY id DESC
            LIMIT ?
            """,
            (args.limit,),
        )
    rows = cur.fetchall()

    if not rows:
        print("No empty details rows found.")
        con.close()
        return

    data_cache: dict[tuple[str, str], Any] = {}
    details_cache: dict[tuple[str, str, str, str], str] = {}
    updated = 0
    skipped = 0

    for signal_id, symbol, market_type, strategy, timeframe in rows:
        market = "BIST" if str(market_type).upper() == "BIST" else "Kripto"
        strat = "COMBO" if str(strategy).upper() == "COMBO" else "HUNTER"
        key_data = (market, symbol)
        key_details = (market, symbol, strat, timeframe)

        if key_details in details_cache:
            details_json = details_cache[key_details]
        else:
            if key_data not in data_cache:
                data_cache[key_data] = _load_daily_data(symbol, market)
            df_daily = data_cache[key_data]
            if df_daily is None or getattr(df_daily, "empty", True):
                details_cache[key_details] = ""
            else:
                # Use real market type for resample rules.
                try:
                    df_resampled = resample_market_data(df_daily.copy(), timeframe, market)
                    if df_resampled is None or len(df_resampled) < 20:
                        details_cache[key_details] = ""
                    else:
                        if strat == "COMBO":
                            result = calculate_combo_signal(df_resampled, timeframe)
                        else:
                            result = calculate_hunter_signal(df_resampled, timeframe)
                        details_cache[key_details] = _serialize_details(
                            result.get("details") if result else None
                        )
                except Exception:
                    details_cache[key_details] = ""
            details_json = details_cache[key_details]

        if not details_json:
            skipped += 1
            continue

        cur.execute("UPDATE signals SET details = ? WHERE id = ?", (details_json, signal_id))
        updated += 1

    con.commit()
    con.close()
    print(f"Mode: {args.mode} | Processed: {len(rows)} | Updated: {updated} | Skipped: {skipped}")


if __name__ == "__main__":
    main()
