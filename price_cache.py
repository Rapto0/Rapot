"""
Price Cache Modülü
OHLCV verilerini önbelleğe alarak API çağrılarını azaltır.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from logger import get_logger

logger = get_logger(__name__)

# Cache veritabanı
CACHE_DB_PATH = Path(__file__).parent / "price_cache.db"

# Cache süreleri (saniye)
CACHE_TTL = {
    "BIST": 300,  # 5 dakika (piyasa saatleri dışında daha uzun)
    "Kripto": 60,  # 1 dakika (7/24 açık)
    "default": 180,  # 3 dakika
}


class PriceCache:
    """
    Fiyat verisi önbellek sistemi.
    SQLite tabanlı, TTL destekli cache.
    """

    def __init__(self):
        self._init_database()
        self._stats = {"hits": 0, "misses": 0}
        logger.info(f"PriceCache başlatıldı: {CACHE_DB_PATH}")

    def _get_connection(self) -> sqlite3.Connection:
        """Veritabanı bağlantısı döndürür."""
        conn = sqlite3.connect(str(CACHE_DB_PATH), timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _get_cursor(self):
        """Context manager ile cursor yönetimi."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Cache DB hatası: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def _init_database(self) -> None:
        """Cache tablolarını oluşturur."""
        with self._get_cursor() as cursor:
            # Ana cache tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    market_type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    row_count INTEGER,
                    last_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    UNIQUE(symbol, market_type)
                )
            """)

            # Cache istatistikleri
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stat_date DATE NOT NULL UNIQUE,
                    cache_hits INTEGER DEFAULT 0,
                    cache_misses INTEGER DEFAULT 0,
                    api_calls_saved INTEGER DEFAULT 0
                )
            """)

            # İndeksler
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_symbol ON price_cache(symbol)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_expires ON price_cache(expires_at)"
            )

    def get(self, symbol: str, market_type: str = "BIST") -> pd.DataFrame | None:
        """
        Cache'den veri getirir.

        Args:
            symbol: Sembol (örn: THYAO, BTCUSDT)
            market_type: Piyasa türü (BIST, Kripto)

        Returns:
            DataFrame veya None (cache miss)
        """
        expired_entry = False
        data_json = None

        with self._get_cursor() as cursor:
            cursor.execute(
                """
                SELECT data_json, expires_at FROM price_cache
                WHERE symbol = ? AND market_type = ?
            """,
                (symbol, market_type),
            )

            row = cursor.fetchone()

            if row:
                expires_at = datetime.fromisoformat(row["expires_at"])

                if expires_at > datetime.now():
                    # Cache hit
                    data_json = row["data_json"]
                else:
                    # Expired entry flag
                    expired_entry = True

        # Expired entry varsa ayrı context'te sil (SQLite locking önleme)
        if expired_entry:
            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM price_cache
                    WHERE symbol = ? AND market_type = ?
                """,
                    (symbol, market_type),
                )

        # Cache hit durumu
        if data_json:
            self._stats["hits"] += 1
            self._update_stats(hit=True)

            try:
                data = json.loads(data_json)
                df = pd.DataFrame(data)
                df.index = pd.to_datetime(df.index)
                logger.debug(f"Cache hit: {symbol}")
                return df
            except Exception as e:
                logger.error(f"Cache parse hatası: {e}")
                return None

        # Cache miss
        self._stats["misses"] += 1
        self._update_stats(hit=False)
        logger.debug(f"Cache miss: {symbol}")
        return None

    def set(
        self, symbol: str, market_type: str, df: pd.DataFrame, ttl_seconds: int | None = None
    ) -> bool:
        """
        Veriyi cache'e yazar.

        Args:
            symbol: Sembol
            market_type: Piyasa türü
            df: OHLCV DataFrame
            ttl_seconds: Cache süresi (opsiyonel)

        Returns:
            Başarı durumu
        """
        if df is None or df.empty:
            return False

        try:
            # TTL hesapla
            if ttl_seconds is None:
                ttl_seconds = CACHE_TTL.get(market_type, CACHE_TTL["default"])

            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

            # DataFrame'i JSON'a çevir
            df_copy = df.copy()
            df_copy.index = df_copy.index.astype(str)
            data_json = df_copy.to_json()

            # Son tarih
            last_date = str(df.index[-1]) if len(df) > 0 else None

            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO price_cache
                    (symbol, market_type, data_json, row_count, last_date, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, market_type) DO UPDATE SET
                        data_json = excluded.data_json,
                        row_count = excluded.row_count,
                        last_date = excluded.last_date,
                        created_at = CURRENT_TIMESTAMP,
                        expires_at = excluded.expires_at
                """,
                    (symbol, market_type, data_json, len(df), last_date, expires_at),
                )

            logger.debug(f"Cache set: {symbol} ({len(df)} rows, TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set hatası: {e}")
            return False

    def invalidate(self, symbol: str, market_type: str | None = None) -> int:
        """
        Belirli sembolün cache'ini siler.

        Args:
            symbol: Sembol
            market_type: Piyasa türü (None ise tümü)

        Returns:
            Silinen kayıt sayısı
        """
        with self._get_cursor() as cursor:
            if market_type:
                cursor.execute(
                    """
                    DELETE FROM price_cache
                    WHERE symbol = ? AND market_type = ?
                """,
                    (symbol, market_type),
                )
            else:
                cursor.execute(
                    """
                    DELETE FROM price_cache WHERE symbol = ?
                """,
                    (symbol,),
                )

            deleted = cursor.rowcount
            logger.info(f"Cache invalidated: {symbol} ({deleted} entries)")
            return deleted

    def clear_expired(self) -> int:
        """Süresi dolmuş cache'leri temizler."""
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM price_cache
                WHERE expires_at < ?
            """,
                (datetime.now(),),
            )

            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Expired cache temizlendi: {deleted} entries")
            return deleted

    def clear_all(self) -> int:
        """Tüm cache'i temizler."""
        with self._get_cursor() as cursor:
            cursor.execute("DELETE FROM price_cache")
            deleted = cursor.rowcount
            logger.info(f"Tüm cache temizlendi: {deleted} entries")
            return deleted

    def _update_stats(self, hit: bool) -> None:
        """İstatistikleri günceller."""
        today = datetime.now().date()

        with self._get_cursor() as cursor:
            if hit:
                cursor.execute(
                    """
                    INSERT INTO cache_stats (stat_date, cache_hits)
                    VALUES (?, 1)
                    ON CONFLICT(stat_date) DO UPDATE SET
                        cache_hits = cache_hits + 1,
                        api_calls_saved = api_calls_saved + 1
                """,
                    (today,),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO cache_stats (stat_date, cache_misses)
                    VALUES (?, 1)
                    ON CONFLICT(stat_date) DO UPDATE SET
                        cache_misses = cache_misses + 1
                """,
                    (today,),
                )

    def get_stats(self) -> dict[str, Any]:
        """Cache istatistiklerini döndürür."""
        with self._get_cursor() as cursor:
            # Toplam cache boyutu
            cursor.execute("SELECT COUNT(*) as count, SUM(row_count) as rows FROM price_cache")
            row = cursor.fetchone()
            cache_entries = row["count"] or 0
            total_rows = row["rows"] or 0

            # Bugünün istatistikleri
            today = datetime.now().date()
            cursor.execute(
                """
                SELECT cache_hits, cache_misses, api_calls_saved
                FROM cache_stats WHERE stat_date = ?
            """,
                (today,),
            )
            stat_row = cursor.fetchone()

            hits = stat_row["cache_hits"] if stat_row else 0
            misses = stat_row["cache_misses"] if stat_row else 0
            saved = stat_row["api_calls_saved"] if stat_row else 0

            hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0

            return {
                "cache_entries": cache_entries,
                "total_rows_cached": total_rows,
                "today_hits": hits,
                "today_misses": misses,
                "hit_rate": hit_rate,
                "api_calls_saved": saved,
                "session_hits": self._stats["hits"],
                "session_misses": self._stats["misses"],
            }

    def get_cached_symbols(self, market_type: str | None = None) -> list:
        """Cache'deki sembolleri listeler."""
        with self._get_cursor() as cursor:
            if market_type:
                cursor.execute(
                    """
                    SELECT symbol, row_count, last_date, expires_at
                    FROM price_cache WHERE market_type = ?
                    ORDER BY symbol
                """,
                    (market_type,),
                )
            else:
                cursor.execute("""
                    SELECT symbol, market_type, row_count, last_date, expires_at
                    FROM price_cache ORDER BY symbol
                """)

            return [dict(row) for row in cursor.fetchall()]


# Singleton instance
price_cache = PriceCache()


# ==================== DATA_LOADER ENTEGRASYONU ====================


def cached_get_bist_data(symbol: str, start_date: str = "01-01-2015") -> pd.DataFrame | None:
    """
    Cache destekli BIST veri çekme.
    Önce cache'e bakar, yoksa API'den çeker.
    """
    from data_loader import get_bist_data, is_suspicious_bist_ohlcv

    # Cache'e bak
    cached = price_cache.get(symbol, "BIST")
    if cached is not None:
        if is_suspicious_bist_ohlcv(cached):
            price_cache.invalidate(symbol, "BIST")
            logger.warning(f"BIST cache invalidated (suspicious open profile): {symbol}")
        else:
            return cached

    # API'den çek
    df = get_bist_data(symbol, start_date)

    # Cache'e yaz
    if df is not None and not df.empty and not is_suspicious_bist_ohlcv(df):
        price_cache.set(symbol, "BIST", df)
    elif df is not None and not df.empty:
        logger.warning(f"BIST cache write skipped (suspicious open profile): {symbol}")

    return df


def cached_get_crypto_data(symbol: str, start_str: str = "6 years ago") -> pd.DataFrame | None:
    """
    Cache destekli kripto veri çekme.
    Önce cache'e bakar, yoksa API'den çeker.
    """
    from data_loader import get_crypto_data

    # Cache'e bak
    cached = price_cache.get(symbol, "Kripto")
    if cached is not None:
        return cached

    # API'den çek
    df = get_crypto_data(symbol, start_str)

    # Cache'e yaz
    if df is not None and not df.empty:
        price_cache.set(symbol, "Kripto", df)

    return df


def get_cache_report() -> str:
    """Telegram için cache raporu formatlar."""
    stats = price_cache.get_stats()

    report = "📦 <b>CACHE DURUMU</b>\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n"
    report += f"• Cache'li Sembol: {stats['cache_entries']}\n"
    report += f"• Toplam Satır: {stats['total_rows_cached']:,}\n"
    report += f"• Bugün Hit/Miss: {stats['today_hits']}/{stats['today_misses']}\n"
    report += f"• Hit Oranı: {stats['hit_rate']:.1f}%\n"
    report += f"• API Tasarrufu: {stats['api_calls_saved']} çağrı"

    return report
