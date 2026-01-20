import json
import time
from pathlib import Path

import pandas as pd
from isyatirimhisse import fetch_stock_data

from config import rate_limits
from logger import get_logger
from settings import settings

logger = get_logger(__name__)

# Binance client - lazy initialization (sadece kripto taraması için)
_binance_client = None


def _get_binance_client():
    """Binance client'ı lazy olarak başlatır."""
    global _binance_client
    if _binance_client is None:
        if settings.binance_api_key and settings.binance_secret_key:
            from binance.client import Client

            _binance_client = Client(settings.binance_api_key, settings.binance_secret_key)
            logger.info("Binance client başlatıldı")
        else:
            logger.warning("Binance API key'leri eksik - kripto taraması devre dışı")
    return _binance_client


def _load_bist_symbols() -> list[str]:
    """BIST sembollerini JSON dosyasından yükler."""
    try:
        data_file = Path(__file__).parent / "data" / "bist_symbols.json"
        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(f"BIST sembolleri yüklendi: {len(data['symbols'])} sembol")
        return data["symbols"]
    except FileNotFoundError:
        logger.error("data/bist_symbols.json bulunamadı!")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"BIST JSON parse hatası: {e}")
        return []


# BIST sembolleri JSON'dan yükleniyor
ALL_BIST_TICKERS = _load_bist_symbols()


def get_all_bist_symbols() -> list[str]:
    """Tum BIST hisse sembollerini dondurur."""
    return ALL_BIST_TICKERS


def get_all_binance_symbols() -> list[str]:
    """
    Binance'teki tum aktif USDT ciftlerini dondurur.

    Returns:
        USDT bazli islem ciftleri listesi (orn: ['BTCUSDT', 'ETHUSDT', ...])
        Hata durumunda veya Binance yapılandırılmamışsa bos liste
    """
    client = _get_binance_client()
    if client is None:
        return []

    try:
        info = client.get_exchange_info()
        symbols = [
            s["symbol"]
            for s in info["symbols"]
            if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
        ]
        return symbols
    except Exception as e:
        logger.error(f"Binance symbols fetch error: {e}")
        return []


def resample_data(df: pd.DataFrame | None, timeframe: str) -> pd.DataFrame | None:
    """
    Gunluk veriyi belirtilen timeframe'e resample eder.

    Args:
        df: Gunluk OHLCV verisi
        timeframe: Hedef zaman dilimi (1D, W-FRI, 2W-FRI, 3W-FRI, ME)

    Returns:
        Resample edilmis DataFrame veya None
    """
    if df is None or df.empty:
        return None
    agg_dict = {}
    if "Open" in df.columns:
        agg_dict["Open"] = "first"
    if "High" in df.columns:
        agg_dict["High"] = "max"
    if "Low" in df.columns:
        agg_dict["Low"] = "min"
    if "Close" in df.columns:
        agg_dict["Close"] = "last"
    if "Volume" in df.columns:
        agg_dict["Volume"] = "sum"

    try:
        resampled_df = df.resample(timeframe).agg(agg_dict)
        return resampled_df.dropna()
    except (ValueError, KeyError) as e:
        logger.debug(f"Resample error for {timeframe}: {e}")
        return None


def get_bist_data(symbol: str, start_date: str = "01-01-2015") -> pd.DataFrame | None:
    """
    BIST Verisi Çeker (Retry Mekanizmalı)
    Hata alırsa 3 kez tekrar dener.
    """
    max_retries = rate_limits.MAX_RETRIES
    for attempt in range(max_retries):
        try:
            # Veri çekme denemesi
            df = fetch_stock_data(symbols=[symbol], start_date=start_date)

            if df.empty:
                # Veri boşsa, belki tarih aralığında veri yoktur, tekrar denemeye gerek yok.
                return None

            # Sütun düzeltme işlemleri
            df = df.rename(
                columns={
                    "HGDG_KAPANIS": "Close",
                    "HGDG_MIN": "Low",
                    "HGDG_MAX": "High",
                    "HGDG_HACIM": "Volume",
                    "HGDG_TARIH": "Date",
                }
            )

            if "Open" not in df.columns and "Close" in df.columns:
                df["Open"] = df["Close"]

            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)

            cols_to_fix = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
            df[cols_to_fix] = df[cols_to_fix].astype(float)

            # Başarılı olursa döngüden çık ve veriyi döndür
            return df

        except Exception as e:
            # Eğer son deneme ise pes et
            if attempt == max_retries - 1:
                # Log kirliliği olmasın diye print'i kapattık, isterseniz açabilirsiniz
                # print(f"❌ {symbol} alınamadı: {e}")
                return None
            else:
                # Hata aldı, biraz bekle ve tekrar dene
                logger.warning(f"BIST retry {attempt + 1}/{max_retries} for {symbol}: {e}")
                time.sleep(rate_limits.RETRY_WAIT)
                continue
    return None


def get_crypto_data(symbol: str, start_str: str = "6 years ago") -> pd.DataFrame | None:
    """
    Binance'ten kripto verisi ceker.

    Args:
        symbol: Kripto cift sembolu (orn: BTCUSDT)
        start_str: Baslangic tarihi (varsayilan: 6 yil once)

    Returns:
        OHLCV verisi iceren DataFrame veya None
    """
    try:
        klines = binance_client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, start_str)
        df = pd.DataFrame(
            klines,
            columns=[
                "OpenTime",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "x",
                "y",
                "z",
                "w",
                "q",
                "k",
            ],
        )

        df["Date"] = pd.to_datetime(df["OpenTime"], unit="ms")
        df.set_index("Date", inplace=True)

        cols = ["Open", "High", "Low", "Close", "Volume"]
        df[cols] = df[cols].astype(float)
        return df
    except Exception as e:
        logger.debug(f"Crypto data fetch error for {symbol}: {e}")
        return None
