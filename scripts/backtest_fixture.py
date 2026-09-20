"""Deterministic fixture data/reports and an isolated offline CLI entry point.

Importing this module does not import application settings, create files or run a backtest.
"""

import argparse
import ast
import hashlib
import json
import logging
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

FIXTURE_ID = "daily-waves-v1"
FIXTURE_START = "2020-05-20"
FIXTURE_END = "2020-06-15"
FIXTURE_AS_OF = "2020-06-16T00:00:00Z"


def daily_frames() -> dict[str, dict[str, Any]]:
    """Build fixed daily OHLCV; this synthetic universe is not historical market data."""
    import numpy as np
    import pandas as pd

    days = np.arange(900, dtype=float)
    dates = pd.date_range("2018-01-01", periods=len(days))
    frames = {}
    for market, symbols in (("BIST", ("FIXAAA", "FIXBBB")), ("CRYPTO", ("FIXBTC", "FIXETH"))):
        frames[market] = {}
        for offset, symbol in enumerate(symbols):
            close = 180 + days * 0.035 + 22 * np.sin(days / 37 + offset) + 8 * np.sin(days / 9)
            # A finite multi-timeframe downswing followed by recovery exercises real signals.
            close -= np.maximum(0, np.minimum(days - 820, 50)) * 1.8
            close += np.maximum(0, days - 870) * 4.5
            scale = (offset + 1) * (10 if market == "CRYPTO" else 1)
            close *= scale
            opened = close * (1 + 0.004 * np.sin(days / 3 + offset))
            frame = pd.DataFrame(
                {
                    "Open": opened,
                    "High": np.maximum(opened, close) * 1.015,
                    "Low": np.minimum(opened, close) * 0.985,
                    "Close": close,
                    "Volume": 10000 + days * 7 + 500 * np.cos(days / 11 + offset),
                },
                index=dates,
            )
            frame.attrs["open_quality"] = "provider"
            frame.attrs["source_hint"] = FIXTURE_ID
            frames[market][symbol] = frame
    return frames


def json_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Unsupported report value: {type(value).__name__}")


def write_equity_svg(portfolios: dict[str, Any], path: Path) -> None:
    """Render actual closing NAV series as a standalone XML SVG without plotting packages."""
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="660" viewBox="0 0 960 660">',
        "<title>Backtest closing NAV and initial capital</title>",
        '<rect width="960" height="660" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#172337">',
        '<text x="65" y="30" font-size="20">Closing NAV — not a return forecast</text>',
    ]
    for panel, (market, portfolio) in enumerate(portfolios.items()):
        top, height, left, width = 80 + panel * 290, 200, 90, 800
        rows = portfolio.equity_curve
        values = [float(row["Toplam Değer"]) for row in rows]
        lo, hi = min([portfolio.initial_cash, *values]), max([portfolio.initial_cash, *values])
        padding = max((hi - lo) * 0.1, portfolio.initial_cash * 0.01)
        lo, hi = lo - padding, hi + padding

        def y(value, top=top, height=height, hi=hi, lo=lo):
            return top + height * (hi - value) / (hi - lo)

        baseline = y(portfolio.initial_cash)
        parts.extend(
            [
                f'<text x="{left}" y="{top - 20}">{escape(market)} NAV ({"TL" if market == "BIST" else "USD"})</text>',
                f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="#f6f8fb" stroke="#ccd3de"/>',
                f'<line x1="{left}" y1="{baseline:.3f}" x2="{left + width}" y2="{baseline:.3f}" stroke="#a34442" stroke-dasharray="6 4"/>',
                f'<text x="5" y="{top + 10}">{hi:.2f}</text>',
                f'<text x="5" y="{top + height}">{lo:.2f}</text>',
            ]
        )
        if rows:
            duration = max((rows[-1]["Tarih"] - rows[0]["Tarih"]).total_seconds(), 1)
            points = " ".join(
                f"{left + width * (row['Tarih'] - rows[0]['Tarih']).total_seconds() / duration:.3f},{y(row['Toplam Değer']):.3f}"
                for row in rows
            )
            parts.extend(
                [
                    f'<polyline points="{points}" fill="none" stroke="#1e62aa" stroke-width="2"/>',
                    f'<text x="{left}" y="{top + height + 22}">{rows[0]["Tarih"].date()}</text>',
                    f'<text x="{left + width - 95}" y="{top + height + 22}">{rows[-1]["Tarih"].date()}</text>',
                ]
            )
        else:
            parts.append(
                f'<text x="{left + 20}" y="{top + 40}">No admitted equity observations</text>'
            )
    parts.extend(
        [
            '<text x="90" y="645">Blue: closing NAV; dashed red: initial capital. Fees included; hypothetical closing fees excluded.</text>',
            "</g></svg>",
        ]
    )
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def write_reports(
    engine: Any, portfolios: dict[str, Any], output: Path, metadata: dict[str, Any]
) -> Path:
    """Write deterministic UTF-8 JSON/CSV, preserving dates and stale-mark metadata."""
    import pandas as pd

    report = {
        "schema_version": 1,
        **metadata,
        "as_of": engine.as_of,
        "markets": {},
        "csv_artifacts": {},
    }
    for market, portfolio in portfolios.items():
        report["markets"][market] = {
            "statistics": engine._calculate_stats(portfolio),
            "backtest_metadata": portfolio.backtest_metadata,
            "transaction_costs": {
                "commission": portfolio.total_commission_paid,
                "slippage": portfolio.total_slippage_cost,
            },
            "trade_count": len(portfolio.all_trades),
            "equity_count": len(portfolio.equity_curve),
        }
        for name, rows, empty_columns in (
            ("trades", portfolio.all_trades, ["Tarih", "Sembol", "İşlem"]),
            ("equity", portfolio.equity_curve, ["Tarih", "Toplam Değer", "Nakit"]),
            ("open_positions", portfolio.get_open_positions_summary(), ["Sembol", "Lot Sayısı"]),
        ):
            frame = pd.DataFrame(rows) if rows else pd.DataFrame(columns=empty_columns)
            for column in frame.columns:
                frame[column] = frame[column].map(
                    lambda value: json.dumps(
                        value, ensure_ascii=False, sort_keys=True, default=json_value
                    )
                    if isinstance(value, (dict, list))
                    else value
                )
            data = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
            filename = f"{market.lower()}_{name}.csv"
            (output / filename).write_bytes(data)
            report["csv_artifacts"][filename] = {
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
    path = output / "report.json"
    path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
            default=json_value,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    """Isolate settings/log paths before importing the legacy application-backed CLI."""
    parser = argparse.ArgumentParser(description="Offline full backtest CLI with synthetic OHLCV")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--as-of", default=FIXTURE_AS_OF)
    parser.add_argument("--excel", action="store_true", help="Also write an openpyxl workbook")
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    root = Path(__file__).resolve().parents[1]
    if "backtesting_system" in sys.modules or "settings" in sys.modules:
        parser.error("Run this isolated entry point in a fresh Python process")
    denied = []

    def audit(event, arguments):
        if event in {
            "socket.connect",
            "socket.getaddrinfo",
            "socket.gethostbyname",
            "sqlite3.connect",
            "subprocess.Popen",
            "os.system",
        }:
            denied.append(event)
            raise RuntimeError(f"Fixture attempted prohibited IO: {event}")

    sys.addaudithook(audit)
    original_directory, original_environment = Path.cwd(), dict(os.environ)
    try:
        with ExitStack() as cleanup:
            isolated = cleanup.enter_context(tempfile.TemporaryDirectory(prefix="rapot-fixture-"))
            # Close Windows log handles and leave cwd before removing the temporary tree,
            # including when argument validation or execution raises an exception.
            cleanup.callback(os.chdir, original_directory)
            cleanup.callback(logging.shutdown)
            # Read field names only, never account settings or dotenv contents.
            tree = ast.parse((root / "settings.py").read_text(encoding="utf-8"))
            fields = {
                item.target.id.upper()
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == "Settings"
                for item in node.body
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
            }
            for key in list(os.environ):
                if key.upper() in fields:
                    del os.environ[key]
            os.environ.update(
                {
                    "TELEGRAM_TOKEN": "fixture-token",
                    "TELEGRAM_CHAT_ID": "fixture-chat",
                    "APP_ENV": "test",
                    "AI_ENABLED": "0",
                    "RUN_EMBEDDED_BOT": "0",
                    "DATABASE_PATH": str(Path(isolated) / "unused.sqlite3"),
                    "CACHE_DATABASE_PATH": str(Path(isolated) / "unused-cache.sqlite3"),
                    "XDG_CACHE_HOME": str(Path(isolated) / "cache"),
                }
            )
            os.chdir(isolated)
            import backtesting_system

            def deny_provider(*args, **kwargs):
                denied.append("provider")
                raise RuntimeError("Fixture attempted provider access")

            backtesting_system.get_bist_data_isyatirim_only = deny_provider
            backtesting_system.get_crypto_data = deny_provider
            # Native HTTP transports need an explicit guard in addition to Python socket audit.
            from curl_cffi import Curl

            Curl.perform = deny_provider
            result = backtesting_system.main(
                [
                    "--fixture",
                    "--output-dir",
                    str(output),
                    "--as-of",
                    args.as_of,
                    *(["--excel"] if args.excel else []),
                ]
            )
            if denied:
                raise RuntimeError(f"Fixture attempted prohibited IO: {sorted(set(denied))}")
            return result
    finally:
        os.chdir(original_directory)
        os.environ.clear()
        os.environ.update(original_environment)


if __name__ == "__main__":
    raise SystemExit(main())
