import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from isyatirimhisse import fetch_stock_data

from config import rate_limits
from logger import get_logger
from settings import settings

logger = get_logger(__name__)

# Binance client - lazy initialization (sadece kripto taraması için)
_binance_client = None
_bist_force_yfinance_fallback = False
_isyatirim_ca_bundle_ready = False

ISYATIRIM_INTERMEDIATE_PEM = """-----BEGIN CERTIFICATE-----
MIIElzCCA3+gAwIBAgIRAIPahmyfUtUakxi40OfAMWkwDQYJKoZIhvcNAQELBQAw
TDEgMB4GA1UECxMXR2xvYmFsU2lnbiBSb290IENBIC0gUjMxEzARBgNVBAoTCkds
b2JhbFNpZ24xEzARBgNVBAMTCkdsb2JhbFNpZ24wHhcNMjUwNzE2MDMwNTQ2WhcN
MjcwNzE2MDAwMDAwWjBTMQswCQYDVQQGEwJCRTEZMBcGA1UEChMQR2xvYmFsU2ln
biBudi1zYTEpMCcGA1UEAxMgR2xvYmFsU2lnbiBHQ0MgUjMgRVYgVExTIENBIDIw
MjUwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDEG4l4CpUk556CyXIA
B3ihV2b8sWMNGwnW0wCpuaHHA5rlXpSWE1AD6r9hyGhQOrc45nPOj6Fvsqw8dFZw
FpAJzlk6FxhYP1ve8KPJvIpt6f5v28jOlzfs8c7dJ8ZmqKHB0Zj6RbAvA9vAl2A3
j0mu+ooXN3/QaFvVihDV/SRyOfFBlhPAsRk8y97tLPWx7/4YzfE6NSLKsU1yF+tf
BTttbaXTH/cWY/KQE3ZHTFRo6XouemjPBP9CDXeTR11tm37Bgn3QOj93FHdi1JJp
eNBGEOGvM8qhTV/77kDiUyOvsp4jZOhas6kIRn8nWK7fCPNdFJYi1Ctvd7gnQ1gB
lW71AgMBAAGjggFrMIIBZzAOBgNVHQ8BAf8EBAMCAYYwHQYDVR0lBBYwFAYIKwYB
BQUHAwEGCCsGAQUFBwMCMBIGA1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0OBBYEFGMQ
f+QoM5r4R2BZUn5XEMdN+BcWMB8GA1UdIwQYMBaAFI/wS3+oLkUkrk1Q+mOai97i
3Ru8MHsGCCsGAQUFBwEBBG8wbTAuBggrBgEFBQcwAYYiaHR0cDovL29jc3AyLmds
b2JhbHNpZ24uY29tL3Jvb3RyMzA7BggrBgEFBQcwAoYvaHR0cDovL3NlY3VyZS5n
bG9iYWxzaWduLmNvbS9jYWNlcnQvcm9vdC1yMy5jcnQwNgYDVR0fBC8wLTAroCmg
J4YlaHR0cDovL2NybC5nbG9iYWxzaWduLmNvbS9yb290LXIzLmNybDAtBgNVHSAE
JjAkMAcGBWeBDAEBMAwGCisGAQQBoDIKAQEwCwYJKwYBBAGgMgEBMA0GCSqGSIb3
DQEBCwUAA4IBAQCtcTjIgw+tiW7E+sCTJ36nrC0IOxMpwE+nTaUG1xQJb+QE18vF
cPvEiqv8OonEBkQJFQ1N5YdDu9kydDYXBmIheYD9Z//TlUBnLL7HBje1ugplB0xE
jpU52q0XLxe6nHfeEKnslZ/Q/eDEsjZKxwF51SlGO6ap+09hfdbfMXDkTsfa+yXg
dIxZRCud0QEBTZAow0iCs3rf5wVALhhh2ePEwqxEm1LkUhvkJMLSCobYcJ+vXprK
JijbpPM602H1kqxNcD/nE7aCNm7g5GTaT04SCGYiQJ32r9mhx34peuYz05pY+AA3
aVB22PDvfoNyGZyClRtNt4KKg8dGJlYEhc3D
-----END CERTIFICATE-----"""


def _ensure_isyatirim_ca_bundle() -> None:
    """
    requests/certifi bundle'ina Is Yatirim'in eksik gonderdigi ara sertifikayi ekler.
    Boylece SSL dogrulama requests tarafinda kalici olarak duzelir.
    """
    global _isyatirim_ca_bundle_ready
    if _isyatirim_ca_bundle_ready:
        return

    try:
        import certifi

        base_bundle = Path(certifi.where())
        merged_bundle = Path(tempfile.gettempdir()) / "rapot_requests_ca_bundle_isyatirim.pem"

        base_data = base_bundle.read_bytes()
        intermediate_data = ISYATIRIM_INTERMEDIATE_PEM.encode("ascii")
        if intermediate_data not in base_data:
            merged_bundle.write_bytes(base_data.rstrip() + b"\n" + intermediate_data + b"\n")
        else:
            merged_bundle.write_bytes(base_data)

        os.environ["REQUESTS_CA_BUNDLE"] = str(merged_bundle)
        os.environ["SSL_CERT_FILE"] = str(merged_bundle)
        _isyatirim_ca_bundle_ready = True
    except Exception as e:
        logger.warning(f"Is Yatirim CA bundle hazirlanamadi: {e}")


def _fetch_bist_data_yfinance(symbol: str, start_date: str = "01-01-2015") -> pd.DataFrame | None:
    """
    isyatirim başarısız olduğunda BIST verisini yfinance ile çekmeye çalışır.
    """
    try:
        import yfinance as yf
    except Exception as e:
        logger.error(f"yfinance import hatası ({symbol}): {e}")
        return None

    try:
        start_iso = datetime.strptime(start_date, "%d-%m-%Y").strftime("%Y-%m-%d")
    except Exception:
        start_iso = "2015-01-01"

    ticker = symbol if symbol.endswith(".IS") else f"{symbol}.IS"
    try:
        df = yf.download(
            tickers=ticker,
            start=start_iso,
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if df is None or df.empty:
            return None

        # yfinance bazı sürümlerde MultiIndex döndürebilir.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(col[0]) for col in df.columns]

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        if not all(col in df.columns for col in required_cols):
            return None

        df = df[required_cols].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df.astype(float).sort_index().dropna()
        return df if not df.empty else None
    except Exception as e:
        logger.error(f"yfinance BIST fallback hatası ({symbol}): {e}")
        return None


def _get_binance_client():
    """Binance client'ı lazy olarak başlatır."""
    global _binance_client
    if _binance_client is None:
        from binance.client import Client

        # API Key varsa kullan, yoksa anonim bağlan (Public veri için yeterli)
        api_key = settings.binance_api_key if settings.binance_api_key else None
        secret_key = settings.binance_secret_key if settings.binance_secret_key else None

        _binance_client = Client(api_key, secret_key)

        if api_key:
            logger.info("Binance client başlatıldı (Auth mod)")
        else:
            logger.info("Binance client başlatıldı (Public mod - Sadece veri okuma)")
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
    _ensure_isyatirim_ca_bundle()

    global _bist_force_yfinance_fallback

    if _bist_force_yfinance_fallback:
        return _fetch_bist_data_yfinance(symbol, start_date)

    max_retries = rate_limits.MAX_RETRIES
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            # Veri çekme denemesi
            df = fetch_stock_data(symbols=[symbol], start_date=start_date)

            if df is None or df.empty:
                if attempt == max_retries - 1:
                    logger.warning(f"BIST veri boş döndü ({symbol}), yfinance fallback deneniyor.")
                    fallback = _fetch_bist_data_yfinance(symbol, start_date)
                    if fallback is not None:
                        logger.warning(f"BIST fallback aktif (yfinance): {symbol}")
                        return fallback
                    return None
                time.sleep(rate_limits.RETRY_WAIT)
                continue

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
            last_error = e
            # Eğer son deneme ise pes et
            if attempt == max_retries - 1:
                err = str(e)
                if "CERTIFICATE_VERIFY_FAILED" in err or "SSLError" in err or "SSL" in err:
                    _bist_force_yfinance_fallback = True
                    logger.error(
                        f"BIST SSL doğrulama hatası ({symbol}): {err}. "
                        "Bu süreçte BIST verisi yfinance fallback ile devam edecek. "
                        "Sunucuda ca-certificates ve saat ayarı kontrol edilmeli."
                    )
                else:
                    logger.error(f"BIST veri çekme başarısız ({symbol}): {err}")

                fallback = _fetch_bist_data_yfinance(symbol, start_date)
                if fallback is not None:
                    if (
                        "No data was fetched for any symbol" in err
                        or "CERTIFICATE_VERIFY_FAILED" in err
                        or "SSLError" in err
                        or "SSL" in err
                    ):
                        _bist_force_yfinance_fallback = True
                        logger.warning(
                            "BIST ana veri kaynağı bu süreçte devre dışı bırakıldı. "
                            "Tarama yfinance fallback ile devam edecek."
                        )
                    logger.warning(f"BIST fallback aktif (yfinance): {symbol}")
                    return fallback
                return None
            else:
                # Hata aldı, biraz bekle ve tekrar dene
                logger.warning(f"BIST retry {attempt + 1}/{max_retries} for {symbol}: {e}")
                time.sleep(rate_limits.RETRY_WAIT)
                continue
    if last_error:
        logger.error(f"BIST veri çekme tamamıyla başarısız ({symbol}): {last_error}")
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
        client = _get_binance_client()
        if client is None:
            return None
        # Client.KLINE_INTERVAL_1DAY için Client import edilmeli veya string kullanılmalı
        # String '1d' de çalışır
        klines = client.get_historical_klines(symbol, "1d", start_str)
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
