"""
Trade Manager Modülü
Gerçek alım/satım işlemlerini yönetir ve takip eder.
"""

from typing import Any

from database import Trade, db
from logger import get_logger
from telegram_notify import send_message

logger = get_logger(__name__)


class TradeManager:
    """
    Trade yönetim sınıfı.
    Açık pozisyonları takip eder, trade kaydeder ve PnL hesaplar.
    """

    def __init__(self):
        self._db = db
        logger.info("TradeManager başlatıldı")

    def open_trade(
        self,
        symbol: str,
        market_type: str,
        direction: str,
        price: float,
        quantity: float,
        signal_id: int | None = None,
    ) -> int:
        """
        Yeni trade açar.

        Args:
            symbol: Sembol (ör: THYAO, BTCUSDT)
            market_type: Piyasa türü (BIST, Kripto)
            direction: İşlem yönü (BUY, SELL)
            price: Giriş fiyatı
            quantity: Adet/Miktar
            signal_id: İlişkili sinyal ID (opsiyonel)

        Returns:
            Oluşturulan trade ID'si
        """
        trade = Trade(
            symbol=symbol,
            market_type=market_type,
            direction=direction,
            price=price,
            quantity=quantity,
            signal_id=signal_id,
            status="OPEN",
        )

        trade_id = self._db.save_trade(trade)

        logger.info(f"Trade açıldı: {symbol} {direction} @ {price} x {quantity}")

        # Telegram bildirimi
        emoji = "🟢" if direction == "BUY" else "🔴"
        msg = (
            f"{emoji} <b>YENİ İŞLEM</b>\n"
            f"• Sembol: #{symbol}\n"
            f"• Yön: {direction}\n"
            f"• Fiyat: {price:.4f}\n"
            f"• Miktar: {quantity}\n"
            f"• Piyasa: {market_type}"
        )
        send_message(msg)

        return trade_id

    def close_trade(self, trade_id: int, close_price: float) -> dict[str, Any] | None:
        """
        Trade'i kapatır ve PnL hesaplar.

        Args:
            trade_id: Kapatılacak trade ID
            close_price: Çıkış fiyatı

        Returns:
            Trade bilgileri ve PnL
        """
        # Trade bilgilerini al
        with self._db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            trade_row = cursor.fetchone()

        if not trade_row:
            logger.error(f"Trade bulunamadı: {trade_id}")
            return None

        trade = dict(trade_row)

        if trade["status"] != "OPEN":
            logger.warning(f"Trade zaten kapalı: {trade_id}")
            return None

        # PnL hesapla
        entry_price = trade["price"]
        quantity = trade["quantity"]
        direction = trade["direction"]

        if direction == "BUY":
            pnl = (close_price - entry_price) * quantity
            pnl_percent = ((close_price / entry_price) - 1) * 100
        else:
            pnl = (entry_price - close_price) * quantity
            pnl_percent = ((entry_price / close_price) - 1) * 100

        # Veritabanını güncelle
        success = self._db.close_trade(trade_id, close_price)

        if success:
            logger.info(f"Trade kapatıldı: {trade_id}, PnL: {pnl:.2f}")

            # Telegram bildirimi
            emoji = "✅" if pnl > 0 else "❌"
            pnl_emoji = "📈" if pnl > 0 else "📉"
            msg = (
                f"{emoji} <b>İŞLEM KAPATILDI</b>\n"
                f"• Sembol: #{trade['symbol']}\n"
                f"• Giriş: {entry_price:.4f}\n"
                f"• Çıkış: {close_price:.4f}\n"
                f"• {pnl_emoji} PnL: {pnl:+.2f} ({pnl_percent:+.1f}%)"
            )
            send_message(msg)

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

        return None

    def get_open_positions(self) -> list[dict[str, Any]]:
        """Tüm açık pozisyonları listeler."""
        return self._db.get_open_trades()

    def get_position(self, symbol: str) -> dict[str, Any] | None:
        """Belirli sembol için açık pozisyon döndürür."""
        positions = self._db.get_open_trades(symbol=symbol)
        return positions[0] if positions else None

    def get_trade_history(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """
        İşlem geçmişini döndürür.

        Args:
            symbol: Filtrelenecek sembol
            limit: Maksimum kayıt sayısı
        """
        query = "SELECT * FROM trades"
        params = []

        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._db.get_cursor() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> dict[str, Any]:
        """Detaylı trade istatistikleri."""
        stats = self._db.get_trade_stats()

        with self._db.get_cursor() as cursor:
            # En iyi trade
            cursor.execute("""
                SELECT symbol, pnl FROM trades
                WHERE status = 'CLOSED'
                ORDER BY pnl DESC LIMIT 1
            """)
            best = cursor.fetchone()

            # En kötü trade
            cursor.execute("""
                SELECT symbol, pnl FROM trades
                WHERE status = 'CLOSED'
                ORDER BY pnl ASC LIMIT 1
            """)
            worst = cursor.fetchone()

            # Ortalama PnL
            cursor.execute("""
                SELECT AVG(pnl) FROM trades
                WHERE status = 'CLOSED'
            """)
            avg_pnl = cursor.fetchone()[0] or 0

        stats["best_trade"] = dict(best) if best else None
        stats["worst_trade"] = dict(worst) if worst else None
        stats["average_pnl"] = avg_pnl

        return stats

    def format_portfolio_report(self) -> str:
        """Telegram için portföy raporu formatlar."""
        open_positions = self.get_open_positions()
        stats = self.get_statistics()

        if not open_positions and stats["total_trades"] == 0:
            return "📊 <b>Portföy Durumu</b>\n\nHenüz işlem yok."

        report = "📊 <b>PORTFÖY DURUMU</b>\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n"

        # Açık pozisyonlar
        if open_positions:
            report += f"\n🔓 <b>Açık Pozisyonlar ({len(open_positions)})</b>\n"
            for pos in open_positions[:5]:  # İlk 5
                emoji = "🟢" if pos["direction"] == "BUY" else "🔴"
                report += f"{emoji} {pos['symbol']}: {pos['quantity']} @ {pos['price']:.4f}\n"
        else:
            report += "\n🔓 Açık pozisyon yok\n"

        # İstatistikler
        report += "\n📈 <b>İstatistikler</b>\n"
        report += f"• Toplam İşlem: {stats['total_trades']}\n"
        report += f"• Kapalı: {stats['closed_trades']}\n"
        report += f"• Başarı Oranı: {stats['win_rate']:.1f}%\n"
        report += f"• Toplam PnL: {stats['total_pnl']:+.2f}\n"

        if stats["best_trade"]:
            report += (
                f"• En İyi: {stats['best_trade']['symbol']} (+{stats['best_trade']['pnl']:.2f})\n"
            )

        return report


# Singleton instance
trade_manager = TradeManager()


# ==================== TELEGRAM KOMUTLARI İÇİN ====================


def handle_portfolio_command() -> None:
    """Telegram /portfoy komutu için."""
    report = trade_manager.format_portfolio_report()
    send_message(report)


def handle_trades_command(symbol: str | None = None) -> None:
    """Telegram /islemler komutu için."""
    trades = trade_manager.get_trade_history(symbol=symbol, limit=10)

    if not trades:
        send_message("📋 Henüz işlem geçmişi yok.")
        return

    msg = "📋 <b>SON İŞLEMLER</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n"

    for t in trades:
        emoji = "🟢" if t["direction"] == "BUY" else "🔴"
        status = "✅" if t["status"] == "CLOSED" else "🔓"
        pnl_str = f" ({t['pnl']:+.2f})" if t["status"] == "CLOSED" else ""
        msg += f"{emoji}{status} {t['symbol']} @ {t['price']:.4f}{pnl_str}\n"

    send_message(msg)
