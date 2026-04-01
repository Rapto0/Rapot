"""
Trade management helpers used by Telegram commands and manual trade actions.
"""

from __future__ import annotations

from typing import Any

from infrastructure.persistence.trade_repository import close_trade as repo_close_trade
from infrastructure.persistence.trade_repository import create_trade as repo_create_trade
from infrastructure.persistence.trade_repository import (
    get_average_closed_trade_pnl,
    get_best_trade,
    get_trade_stats,
    get_worst_trade,
    list_open_trades,
    list_trades,
)
from infrastructure.persistence.trade_repository import get_trade as repo_get_trade
from logger import get_logger
from telegram_notify import send_message

logger = get_logger(__name__)


class TradeManager:
    """Tracks open positions and trade performance metrics."""

    def __init__(self):
        logger.info("TradeManager initialized.")

    def open_trade(
        self,
        symbol: str,
        market_type: str,
        direction: str,
        price: float,
        quantity: float,
        signal_id: int | None = None,
    ) -> int:
        trade_id = repo_create_trade(
            symbol=symbol,
            market_type=market_type,
            direction=direction,
            price=price,
            quantity=quantity,
            signal_id=signal_id,
            status="OPEN",
        )

        logger.info("Trade opened: %s %s @ %s x %s", symbol, direction, price, quantity)

        icon = "BUY" if direction == "BUY" else "SELL"
        message = (
            f"<b>NEW TRADE</b>\n"
            f"- Symbol: #{symbol}\n"
            f"- Direction: {icon}\n"
            f"- Price: {price:.4f}\n"
            f"- Quantity: {quantity}\n"
            f"- Market: {market_type}"
        )
        send_message(message)

        return trade_id

    def close_trade(self, trade_id: int, close_price: float) -> dict[str, Any] | None:
        trade = repo_get_trade(trade_id)
        if not trade:
            logger.error("Trade not found: %s", trade_id)
            return None

        if trade["status"] != "OPEN":
            logger.warning("Trade already closed: %s", trade_id)
            return None

        entry_price = float(trade["price"])
        quantity = float(trade["quantity"])
        direction = str(trade["direction"])

        if direction == "BUY":
            pnl = (close_price - entry_price) * quantity
            pnl_percent = ((close_price / entry_price) - 1) * 100 if entry_price else 0.0
        else:
            pnl = (entry_price - close_price) * quantity
            pnl_percent = ((entry_price / close_price) - 1) * 100 if close_price else 0.0

        closed_trade = repo_close_trade(trade_id, close_price)
        if not closed_trade:
            return None

        logger.info("Trade closed: %s, PnL: %.2f", trade_id, pnl)

        pnl_side = "PROFIT" if pnl > 0 else "LOSS"
        message = (
            f"<b>TRADE CLOSED</b>\n"
            f"- Symbol: #{trade['symbol']}\n"
            f"- Entry: {entry_price:.4f}\n"
            f"- Exit: {close_price:.4f}\n"
            f"- {pnl_side}: {pnl:+.2f} ({pnl_percent:+.1f}%)"
        )
        send_message(message)

        return {
            "trade_id": trade_id,
            "symbol": trade["symbol"],
            "direction": direction,
            "entry_price": entry_price,
            "close_price": close_price,
            "quantity": quantity,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
        }

    def get_open_positions(self) -> list[dict[str, Any]]:
        return list_open_trades()

    def get_position(self, symbol: str) -> dict[str, Any] | None:
        positions = list_open_trades(symbol=symbol)
        return positions[0] if positions else None

    def get_trade_history(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        return list_trades(symbol=symbol, limit=limit)

    def get_statistics(self) -> dict[str, Any]:
        stats = get_trade_stats()
        stats["best_trade"] = get_best_trade()
        stats["worst_trade"] = get_worst_trade()
        stats["average_pnl"] = get_average_closed_trade_pnl()
        return stats

    def format_portfolio_report(self) -> str:
        open_positions = self.get_open_positions()
        stats = self.get_statistics()

        if not open_positions and stats["total_trades"] == 0:
            return "<b>Portfolio Status</b>\n\nNo trades yet."

        report = "<b>PORTFOLIO STATUS</b>\n"
        report += "--------------------\n"

        if open_positions:
            report += f"\n<b>Open Positions ({len(open_positions)})</b>\n"
            for pos in open_positions[:5]:
                side = "BUY" if pos["direction"] == "BUY" else "SELL"
                report += f"- {side} {pos['symbol']}: {pos['quantity']} @ {pos['price']:.4f}\n"
        else:
            report += "\nNo open positions.\n"

        report += "\n<b>Stats</b>\n"
        report += f"- Total Trades: {stats['total_trades']}\n"
        report += f"- Closed Trades: {stats['closed_trades']}\n"
        report += f"- Win Rate: {stats['win_rate']:.1f}%\n"
        report += f"- Total PnL: {stats['total_pnl']:+.2f}\n"

        if stats["best_trade"]:
            report += (
                f"- Best Trade: {stats['best_trade']['symbol']} "
                f"(+{stats['best_trade']['pnl']:.2f})\n"
            )

        return report


trade_manager = TradeManager()


def handle_portfolio_command() -> None:
    report = trade_manager.format_portfolio_report()
    send_message(report)


def handle_trades_command(symbol: str | None = None) -> None:
    trades = trade_manager.get_trade_history(symbol=symbol, limit=10)

    if not trades:
        send_message("No trade history yet.")
        return

    message = "<b>LATEST TRADES</b>\n"
    message += "--------------------\n"

    for trade in trades:
        side = "BUY" if trade["direction"] == "BUY" else "SELL"
        closed = trade["status"] == "CLOSED"
        status = "CLOSED" if closed else "OPEN"
        pnl_text = f" ({trade['pnl']:+.2f})" if closed else ""
        message += f"- {side} {status} {trade['symbol']} @ {trade['price']:.4f}{pnl_text}\n"

    send_message(message)
