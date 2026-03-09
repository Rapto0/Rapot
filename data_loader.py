import json
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
from isyatirimhisse import fetch_stock_data

from config import rate_limits
from isyatirim_ssl import ensure_isyatirim_ca_bundle
from logger import get_logger
from settings import settings

logger = get_logger(__name__)

# Binance client - lazy initialization (sadece kripto taraması için)
_binance_client = None
_bist_force_yfinance_fallback = False
_bist_yf_failure_cooldown_until: dict[str, float] = {}
_bist_yf_failure_logged_reason: dict[str, str] = {}
_YF_SHORT_COOLDOWN_SECONDS = 60 * 60
_YF_LONG_COOLDOWN_SECONDS = 24 * 60 * 60


def _fetch_bist_data_yfinance(symbol: str, start_date: str = "01-01-2015") -> pd.DataFrame | None:
    """
    isyatirim başarısız olduğunda BIST verisini yfinance ile çekmeye çalışır.
    """
    symbol_root = symbol.upper().replace(".IS", "")
    now_ts = time.time()
    cooldown_until = _bist_yf_failure_cooldown_until.get(symbol_root, 0)
    if cooldown_until > now_ts:
        return None

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
        # yfinance bazı hataları stdout/stderr'e basıyor; bunları yakalayıp log spam'i azaltıyoruz.
        buffer = StringIO()
        with redirect_stdout(buffer), redirect_stderr(buffer):
            df = yf.download(
                tickers=ticker,
                start=start_iso,
                interval="1d",
                progress=False,
                auto_adjust=False,
                threads=False,
            )

        raw_output = buffer.getvalue().strip()
        lower_output = raw_output.lower()
        is_probably_delisted = (
            "possibly delisted" in lower_output or "no price data found" in lower_output
        )
        has_failed_download = "failed download" in lower_output or "nonetype" in lower_output

        if df is None or df.empty:
            cooldown = (
                _YF_LONG_COOLDOWN_SECONDS if is_probably_delisted else _YF_SHORT_COOLDOWN_SECONDS
            )
            reason = "possibly delisted" if is_probably_delisted else "download empty"
            _bist_yf_failure_cooldown_until[symbol_root] = now_ts + cooldown
            previous_reason = _bist_yf_failure_logged_reason.get(symbol_root)
            if previous_reason != reason:
                logger.warning(
                    f"BIST yfinance fallback veri üretemedi ({symbol_root}): {reason}. "
                    f"{int(cooldown / 60)} dakika sonra tekrar denenecek."
                )
                _bist_yf_failure_logged_reason[symbol_root] = reason
            return None

        # yfinance bazı sürümlerde MultiIndex döndürebilir.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(col[0]) for col in df.columns]

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        if not all(col in df.columns for col in required_cols):
            _bist_yf_failure_cooldown_until[symbol_root] = now_ts + _YF_SHORT_COOLDOWN_SECONDS
            return None

        df = df[required_cols].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df.astype(float).sort_index().dropna()
        if df.empty:
            _bist_yf_failure_cooldown_until[symbol_root] = now_ts + _YF_SHORT_COOLDOWN_SECONDS
            return None

        if has_failed_download:
            # Veri geldiyse indirme hatası metnini dikkate almıyoruz.
            pass

        _bist_yf_failure_cooldown_until.pop(symbol_root, None)
        _bist_yf_failure_logged_reason.pop(symbol_root, None)
        return df
    except Exception as e:
        _bist_yf_failure_cooldown_until[symbol_root] = now_ts + _YF_SHORT_COOLDOWN_SECONDS
        previous_reason = _bist_yf_failure_logged_reason.get(symbol_root)
        reason = "exception"
        if previous_reason != reason:
            logger.warning(
                f"yfinance BIST fallback geçici hata ({symbol_root}): {e}. "
                f"{int(_YF_SHORT_COOLDOWN_SECONDS / 60)} dakika sonra tekrar denenecek."
            )
            _bist_yf_failure_logged_reason[symbol_root] = reason
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


_BIST_WEEK_EPOCH = pd.Timestamp("1970-01-05")  # Monday
_BIST_MONTH_EPOCH_INDEX = 1970 * 12
_CRYPTO_DAY_EPOCH = pd.Timestamp("1970-01-01")
_CRYPTO_WEEK_EPOCH = pd.Timestamp("1970-01-05")  # Monday
_CRYPTO_MONTH_EPOCH_INDEX = 1970 * 12


def _normalize_ohlcv_frame(df: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize OHLCV dataframe index/columns for deterministic grouping."""
    if df is None or df.empty:
        return None

    try:
        work = df.copy()
        idx = pd.to_datetime(work.index)
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_convert("Europe/Istanbul").tz_localize(None)
        else:
            idx = idx.tz_localize(None)
        work.index = idx
        work = work.sort_index()
        work = work[~work.index.duplicated(keep="last")]

        keep_columns = [col for col in ["Open", "High", "Low", "Close", "Volume"] if col in work.columns]
        if not keep_columns:
            return None
        work = work[keep_columns]
        work = work.dropna(subset=[col for col in ["Open", "High", "Low", "Close"] if col in work.columns])
        return work
    except Exception as e:
        logger.debug(f"OHLCV normalize error: {e}")
        return None


def _normalize_ohlcv_frame_utc(df: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize OHLCV dataframe in UTC semantics for crypto grouping."""
    if df is None or df.empty:
        return None

    try:
        work = df.copy()
        idx = pd.to_datetime(work.index)
        if getattr(idx, "tz", None) is not None:
            idx = idx.tz_convert("UTC").tz_localize(None)
        else:
            idx = idx.tz_localize(None)
        work.index = idx
        work = work.sort_index()
        work = work[~work.index.duplicated(keep="last")]

        keep_columns = [col for col in ["Open", "High", "Low", "Close", "Volume"] if col in work.columns]
        if not keep_columns:
            return None
        work = work[keep_columns]
        work = work.dropna(subset=[col for col in ["Open", "High", "Low", "Close"] if col in work.columns])
        return work
    except Exception as e:
        logger.debug(f"UTC OHLCV normalize error: {e}")
        return None


def _aggregate_ohlcv_slice(slice_df: pd.DataFrame) -> dict:
    """Aggregate one grouped OHLCV slice into a single candle row."""
    candle = {}
    if "Open" in slice_df.columns:
        candle["Open"] = float(slice_df["Open"].iloc[0])
    if "High" in slice_df.columns:
        candle["High"] = float(slice_df["High"].max())
    if "Low" in slice_df.columns:
        candle["Low"] = float(slice_df["Low"].min())
    if "Close" in slice_df.columns:
        candle["Close"] = float(slice_df["Close"].iloc[-1])
    if "Volume" in slice_df.columns:
        candle["Volume"] = float(slice_df["Volume"].sum())
    return candle


def _aggregate_grouped_ohlcv(df: pd.DataFrame, group_keys: pd.Series) -> pd.DataFrame | None:
    """Build grouped OHLCV candles preserving first trading day as candle timestamp."""
    if df.empty:
        return None

    work = df.copy()
    work["_group_key"] = group_keys.to_numpy()

    rows = []
    for _, block in work.groupby("_group_key", sort=True):
        block = block.drop(columns="_group_key")
        if block.empty:
            continue
        rows.append((block.index[0], _aggregate_ohlcv_slice(block)))

    if not rows:
        return None

    result_index = [idx for idx, _ in rows]
    result_rows = [row for _, row in rows]
    result = pd.DataFrame(result_rows, index=pd.DatetimeIndex(result_index))
    return result.sort_index()


def resample_bist_data(df: pd.DataFrame | None, timeframe: str) -> pd.DataFrame | None:
    """
    BIST ozel zaman dilimi resample kurallari.

    - 2D-6D: Islem gunu sayar (tatiller/hafta sonu sayilmaz).
    - 1W/2W/3W: Takvim haftasi (Pazartesi baslangicli) ve sabit epoch ile gruplar.
    - 1M/2M/3M: Takvim ayi bloklari; mum acilisi ilk islem gunu, kapanis son islem gunu.
    """
    work = _normalize_ohlcv_frame(df)
    if work is None or work.empty:
        return None

    tf_raw = timeframe.strip()
    tf_upper = tf_raw.upper()
    aliases = {
        "GUNLUK": "1d",
        "GÜNLÜK": "1d",
        "D": "1d",
        "HAFTALIK": "1wk",
        "W": "1wk",
        "2 HAFTALIK": "2wk",
        "3 HAFTALIK": "3wk",
        "AYLIK": "1mo",
        "M": "1mo",
    }
    tf = aliases.get(tf_upper, tf_raw.lower())

    if tf == "1d":
        return work

    multi_day_steps = {"2d": 2, "3d": 3, "4d": 4, "5d": 5, "6d": 6}
    multi_week_steps = {"1wk": 1, "2wk": 2, "3wk": 3}
    multi_month_steps = {"1mo": 1, "2mo": 2, "3mo": 3}

    if tf in multi_day_steps:
        step = multi_day_steps[tf]
        trading_counter = pd.Series(range(len(work)), index=work.index, dtype="int64")
        group_keys = trading_counter // step
        return _aggregate_grouped_ohlcv(work, group_keys)

    if tf in multi_week_steps:
        step = multi_week_steps[tf]
        idx = pd.DatetimeIndex(work.index)
        week_start = idx.normalize() - pd.to_timedelta(idx.weekday, unit="D")
        week_counter = ((week_start - _BIST_WEEK_EPOCH) // pd.Timedelta(days=7)).astype("int64")
        group_keys = pd.Series(week_counter // step, index=work.index)
        return _aggregate_grouped_ohlcv(work, group_keys)

    if tf in multi_month_steps:
        step = multi_month_steps[tf]
        idx = pd.DatetimeIndex(work.index)
        month_counter = (idx.year * 12 + idx.month - 1) - _BIST_MONTH_EPOCH_INDEX
        group_keys = pd.Series(month_counter // step, index=work.index)
        return _aggregate_grouped_ohlcv(work, group_keys)

    logger.debug(f"Unsupported BIST resample timeframe: {timeframe}")
    return None


def resample_crypto_data(df: pd.DataFrame | None, timeframe: str) -> pd.DataFrame | None:
    """
    Kripto ozel zaman dilimi resample kurallari (UTC).

    - 2D-6D: Takvim gunu sayar (hafta sonu/tatil atlamaz).
    - 1W/2W/3W: Pazartesi bazli takvim haftasi ve sabit epoch ile gruplar.
    - 1M/2M/3M: Takvim ayi bloklari; ayin ilk gununden itibaren gruplar.
    """
    work = _normalize_ohlcv_frame_utc(df)
    if work is None or work.empty:
        return None

    tf_raw = timeframe.strip()
    tf_upper = tf_raw.upper()
    aliases = {
        "GUNLUK": "1d",
        "GÜNLÜK": "1d",
        "D": "1d",
        "HAFTALIK": "1wk",
        "W": "1wk",
        "2 HAFTALIK": "2wk",
        "3 HAFTALIK": "3wk",
        "AYLIK": "1mo",
        "M": "1mo",
    }
    tf = aliases.get(tf_upper, tf_raw.lower())

    if tf == "1d":
        return work

    multi_day_steps = {"2d": 2, "3d": 3, "4d": 4, "5d": 5, "6d": 6}
    multi_week_steps = {"1wk": 1, "2wk": 2, "3wk": 3}
    multi_month_steps = {"1mo": 1, "2mo": 2, "3mo": 3}
    idx = pd.DatetimeIndex(work.index)

    if tf in multi_day_steps:
        step = multi_day_steps[tf]
        day_start = idx.normalize()
        day_counter = ((day_start - _CRYPTO_DAY_EPOCH) // pd.Timedelta(days=1)).astype("int64")
        group_keys = pd.Series(day_counter // step, index=work.index)
        return _aggregate_grouped_ohlcv(work, group_keys)

    if tf in multi_week_steps:
        step = multi_week_steps[tf]
        week_start = idx.normalize() - pd.to_timedelta(idx.weekday, unit="D")
        week_counter = ((week_start - _CRYPTO_WEEK_EPOCH) // pd.Timedelta(days=7)).astype("int64")
        group_keys = pd.Series(week_counter // step, index=work.index)
        return _aggregate_grouped_ohlcv(work, group_keys)

    if tf in multi_month_steps:
        step = multi_month_steps[tf]
        month_counter = (idx.year * 12 + idx.month - 1) - _CRYPTO_MONTH_EPOCH_INDEX
        group_keys = pd.Series(month_counter // step, index=work.index)
        return _aggregate_grouped_ohlcv(work, group_keys)

    logger.debug(f"Unsupported crypto resample timeframe: {timeframe}")
    return None


def _normalize_strategy_timeframe_code(timeframe: str) -> str:
    """Map legacy strategy timeframe codes to custom candle engine codes."""
    normalized = str(timeframe or "").strip().upper()
    alias_map = {
        "1D": "1d",
        "D": "1d",
        "DAILY": "1d",
        "W-FRI": "1wk",
        "1W": "1wk",
        "2W-FRI": "2wk",
        "2W": "2wk",
        "3W-FRI": "3wk",
        "3W": "3wk",
        "ME": "1mo",
        "1M": "1mo",
        "2ME": "2mo",
        "2M": "2mo",
        "3ME": "3mo",
        "3M": "3mo",
    }
    if normalized in alias_map:
        return alias_map[normalized]
    return str(timeframe or "").strip().lower()


def resample_market_data(
    df: pd.DataFrame | None,
    timeframe: str,
    market_type: str | None,
) -> pd.DataFrame | None:
    """
    Market-aware resample entrypoint for scanner/inspector.

    - BIST uses the custom BIST candle engine.
    - Kripto uses the custom crypto candle engine (UTC calendar).
    - Unknown market falls back to legacy pandas resample behavior.
    """
    if df is None or df.empty:
        return None

    normalized_market = str(market_type or "").strip().upper()
    normalized_timeframe = _normalize_strategy_timeframe_code(timeframe)

    if normalized_market == "BIST":
        result = resample_bist_data(df, normalized_timeframe)
        if result is not None and not result.empty:
            return result

    if normalized_market in {"KRIPTO", "CRYPTO"}:
        result = resample_crypto_data(df, normalized_timeframe)
        if result is not None and not result.empty:
            return result

    # Legacy fallback for compatibility with older or unknown timeframe codes.
    return resample_data(df, timeframe)


def get_bist_data(symbol: str, start_date: str = "01-01-2015") -> pd.DataFrame | None:
    """
    BIST Verisi Çeker (Retry Mekanizmalı)
    Hata alırsa 3 kez tekrar dener.
    """
    ensure_isyatirim_ca_bundle()

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
