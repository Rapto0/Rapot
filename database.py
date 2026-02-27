"""
SQLite Veritabanı Modülü
Sinyal geçmişi, trade kayıtları ve piyasa verisi depolama.
"""

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from logger import get_logger

logger = get_logger(__name__)

# Veritabanı dosyası
DB_PATH = Path(__file__).parent / "trading_bot.db"


@dataclass
class Signal:
    """Sinyal veri modeli."""

    id: int | None = None
    symbol: str = ""
    market_type: str = ""  # BIST veya Kripto
    strategy: str = ""  # COMBO veya HUNTER
    signal_type: str = ""  # AL veya SAT
    timeframe: str = ""
    score: str = ""
    price: float = 0.0
    special_tag: str | None = None
    details: str = ""  # JSON string
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class Trade:
    """Trade veri modeli."""

    id: int | None = None
    symbol: str = ""
    market_type: str = ""
    direction: str = ""  # BUY veya SELL
    price: float = 0.0
    quantity: float = 0.0
    signal_id: int | None = None
    status: str = "OPEN"  # OPEN, CLOSED, CANCELLED
    pnl: float = 0.0
    created_at: datetime = None
    closed_at: datetime | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class Database:
    """
    Thread-safe SQLite veritabanı yöneticisi.
    Singleton pattern ile tek instance garantisi.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._local = threading.local()
        self._initialized = True
        self._init_database()
        logger.info(f"Veritabanı başlatıldı: {DB_PATH}")

    def _get_connection(self) -> sqlite3.Connection:
        """Thread-local connection döndürür."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                str(DB_PATH), check_same_thread=False, timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @contextmanager
    def get_cursor(self):
        """Context manager ile cursor yönetimi."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Veritabanı hatası: {e}")
            raise
        finally:
            cursor.close()

    def _init_database(self) -> None:
        """Tabloları oluşturur."""
        with self.get_cursor() as cursor:
            # Signals tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market_type TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    score TEXT,
                    price REAL,
                    special_tag TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, strategy, signal_type, timeframe, created_at)
                )
            """)

            cursor.execute("PRAGMA table_info(signals)")
            signal_columns = {row[1] for row in cursor.fetchall()}
            if "special_tag" not in signal_columns:
                cursor.execute("ALTER TABLE signals ADD COLUMN special_tag TEXT")

            # Trades tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    signal_id INTEGER,
                    status TEXT DEFAULT 'OPEN',
                    pnl REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            """)

            # Bot stats tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stat_name TEXT NOT NULL UNIQUE,
                    stat_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scan history tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_type TEXT NOT NULL,
                    symbols_scanned INTEGER,
                    signals_found INTEGER,
                    duration_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # İndeksler
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_signals_special_tag ON signals(special_tag)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")

    # ==================== SIGNAL OPERATIONS ====================

    def save_signal(self, signal: Signal) -> int:
        """
        Yeni sinyal kaydeder.

        Args:
            signal: Signal dataclass instance

        Returns:
            Oluşturulan kaydın ID'si
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT OR IGNORE INTO signals
                (symbol, market_type, strategy, signal_type, timeframe, score, price, special_tag, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    signal.symbol,
                    signal.market_type,
                    signal.strategy,
                    signal.signal_type,
                    signal.timeframe,
                    signal.score,
                    signal.price,
                    signal.special_tag,
                    signal.details,
                    signal.created_at,
                ),
            )
            return cursor.lastrowid

    def set_latest_signal_special_tag(
        self,
        symbol: str,
        market_type: str,
        strategy: str,
        signal_type: str,
        timeframe: str,
        special_tag: str,
        within_seconds: int = 900,
    ) -> bool:
        """
        En son eslesen sinyal kaydina ozel etiket yazar.
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, created_at
                FROM signals
                WHERE symbol = ? AND market_type = ? AND strategy = ? AND signal_type = ? AND timeframe = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (symbol, market_type, strategy, signal_type, timeframe),
            )
            row = cursor.fetchone()
            if not row:
                return False

            signal_id = row["id"]
            created_at_raw = row["created_at"]
            if created_at_raw is not None and within_seconds > 0:
                try:
                    created_at = (
                        created_at_raw
                        if isinstance(created_at_raw, datetime)
                        else datetime.fromisoformat(str(created_at_raw))
                    )
                    if abs((datetime.now() - created_at).total_seconds()) > within_seconds:
                        return False
                except Exception:
                    # Parse edilemeyen timestamp'te kaydi guncellemeyi atlamiyoruz.
                    pass

            cursor.execute(
                "UPDATE signals SET special_tag = ? WHERE id = ?",
                (special_tag, signal_id),
            )
            return cursor.rowcount > 0

    def get_signals(
        self, symbol: str | None = None, strategy: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Sinyal geçmişini sorgular.

        Args:
            symbol: Filtrelenecek sembol
            strategy: Filtrelenecek strateji
            limit: Maksimum kayıt sayısı

        Returns:
            Sinyal listesi
        """
        query = "SELECT * FROM signals WHERE 1=1"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_signal_count(self, symbol: str | None = None) -> int:
        """Toplam sinyal sayısını döndürür."""
        query = "SELECT COUNT(*) FROM signals"
        params = []

        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)

        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    # ==================== TRADE OPERATIONS ====================

    def save_trade(self, trade: Trade) -> int:
        """Yeni trade kaydeder."""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO trades
                (symbol, market_type, direction, price, quantity, signal_id, status, pnl, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    trade.symbol,
                    trade.market_type,
                    trade.direction,
                    trade.price,
                    trade.quantity,
                    trade.signal_id,
                    trade.status,
                    trade.pnl,
                    trade.created_at,
                ),
            )
            return cursor.lastrowid

    def close_trade(self, trade_id: int, close_price: float) -> bool:
        """Trade'i kapatır ve PnL hesaplar."""
        with self.get_cursor() as cursor:
            # Önce trade bilgilerini al
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            trade = cursor.fetchone()

            if not trade:
                return False

            # PnL hesapla
            direction = trade["direction"]
            entry_price = trade["price"]
            quantity = trade["quantity"]

            if direction == "BUY":
                pnl = (close_price - entry_price) * quantity
            else:
                pnl = (entry_price - close_price) * quantity

            # Trade'i güncelle
            cursor.execute(
                """
                UPDATE trades
                SET status = 'CLOSED', pnl = ?, closed_at = ?
                WHERE id = ?
            """,
                (pnl, datetime.now(), trade_id),
            )

            return True

    def get_open_trades(self, symbol: str | None = None) -> list[dict[str, Any]]:
        """Açık trade'leri listeler."""
        query = "SELECT * FROM trades WHERE status = 'OPEN'"
        params = []

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_trade_stats(self) -> dict[str, Any]:
        """Trade istatistiklerini döndürür."""
        with self.get_cursor() as cursor:
            # Toplam trade sayısı
            cursor.execute("SELECT COUNT(*) FROM trades")
            total = cursor.fetchone()[0]

            # Kazanan trade sayısı
            cursor.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0 AND status = 'CLOSED'")
            winners = cursor.fetchone()[0]

            # Toplam PnL
            cursor.execute("SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE status = 'CLOSED'")
            total_pnl = cursor.fetchone()[0]

            # Win rate
            cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'CLOSED'")
            closed = cursor.fetchone()[0]
            win_rate = (winners / closed * 100) if closed > 0 else 0

            return {
                "total_trades": total,
                "closed_trades": closed,
                "winning_trades": winners,
                "total_pnl": total_pnl,
                "win_rate": win_rate,
            }

    # ==================== SCAN HISTORY ====================

    def log_scan(
        self, scan_type: str, symbols_scanned: int, signals_found: int, duration_seconds: float
    ) -> int:
        """Tarama geçmişi kaydeder."""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO scan_history
                (scan_type, symbols_scanned, signals_found, duration_seconds)
                VALUES (?, ?, ?, ?)
            """,
                (scan_type, symbols_scanned, signals_found, duration_seconds),
            )
            return cursor.lastrowid

    def get_scan_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Son tarama geçmişini döndürür."""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM scan_history
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ==================== BOT STATS ====================

    def set_stat(self, name: str, value: str) -> None:
        """Bot istatistiği kaydeder/günceller."""
        with self.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO bot_stats (stat_name, stat_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(stat_name) DO UPDATE SET
                    stat_value = excluded.stat_value,
                    updated_at = excluded.updated_at
            """,
                (name, value, datetime.now()),
            )

    def get_stat(self, name: str) -> str | None:
        """Bot istatistiği döndürür."""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT stat_value FROM bot_stats WHERE stat_name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None

    def close(self) -> None:
        """Veritabanı bağlantısını kapatır."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            logger.info("Veritabanı bağlantısı kapatıldı")


# Singleton instance
db = Database()


# ==================== CONVENIENCE FUNCTIONS ====================


def save_signal(
    symbol: str,
    market_type: str,
    strategy: str,
    signal_type: str,
    timeframe: str,
    score: str = "",
    price: float = 0.0,
    special_tag: str | None = None,
    details: str = "",
) -> int:
    """Kolaylık fonksiyonu: Sinyal kaydet."""
    signal = Signal(
        symbol=symbol,
        market_type=market_type,
        strategy=strategy,
        signal_type=signal_type,
        timeframe=timeframe,
        score=score,
        price=price,
        special_tag=special_tag,
        details=details,
    )
    return db.save_signal(signal)


def set_signal_special_tag(
    symbol: str,
    market_type: str,
    strategy: str,
    signal_type: str,
    timeframe: str,
    special_tag: str,
    within_seconds: int = 900,
) -> bool:
    """Kolaylik fonksiyonu: Son sinyal kaydina ozel etiket yazar."""
    return db.set_latest_signal_special_tag(
        symbol=symbol,
        market_type=market_type,
        strategy=strategy,
        signal_type=signal_type,
        timeframe=timeframe,
        special_tag=special_tag,
        within_seconds=within_seconds,
    )


def get_recent_signals(symbol: str | None = None, limit: int = 50) -> list[dict]:
    """Kolaylık fonksiyonu: Son sinyalleri getir."""
    return db.get_signals(symbol=symbol, limit=limit)


def get_trade_summary() -> dict[str, Any]:
    """Kolaylık fonksiyonu: Trade özeti."""
    return db.get_trade_stats()
