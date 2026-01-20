from typing import Any

import numpy as np
import pandas as pd

# TA kütüphanesi uyumluluk katmanı
# pandas-ta yerine ta kütüphanesi kullanıyoruz (Docker uyumlu)
try:
    import pandas_ta  # noqa: F401
except ImportError:
    # pandas_ta yoksa ta kütüphanesi ile uyumluluk sağla
    import ta

    class TAAccessor:
        """pandas-ta API'sini taklit eden uyumluluk katmanı."""

        def __init__(self, df):
            self.df = df

        def macd(self, close=None, fast=12, slow=26, signal=9):
            """MACD hesapla."""
            c = close if close is not None else self.df["Close"]
            macd_line = ta.trend.macd(c, window_slow=slow, window_fast=fast)
            macd_signal = ta.trend.macd_signal(
                c, window_slow=slow, window_fast=fast, window_sign=signal
            )
            macd_diff = ta.trend.macd_diff(
                c, window_slow=slow, window_fast=fast, window_sign=signal
            )
            return pd.DataFrame(
                {
                    "MACD_12_26_9": macd_line,
                    "MACDs_12_26_9": macd_signal,
                    "MACDh_12_26_9": macd_diff,
                }
            )

        def rsi(self, close=None, length=14):
            """RSI hesapla."""
            c = close if close is not None else self.df["Close"]
            return ta.momentum.rsi(c, window=length)

        def willr(self, high=None, low=None, close=None, length=14):
            """Williams %R hesapla."""
            h = high if high is not None else self.df["High"]
            l = low if low is not None else self.df["Low"]
            c = close if close is not None else self.df["Close"]
            return ta.momentum.williams_r(h, l, c, lbp=length)

        def cmo(self, close=None, length=14):
            """CMO hesapla - RSI tabanlı yaklaşım."""
            c = close if close is not None else self.df["Close"]
            # CMO = (RSI * 2) - 100 yaklaşımı
            rsi = ta.momentum.rsi(c, window=length)
            return (rsi * 2) - 100 if rsi is not None else None

        def uo(self, fast=7, medium=14, slow=28):
            """Ultimate Oscillator hesapla."""
            return ta.momentum.ultimate_oscillator(
                self.df["High"],
                self.df["Low"],
                self.df["Close"],
                window1=fast,
                window2=medium,
                window3=slow,
            )

        def ema(self, close=None, length=20):
            """EMA hesapla."""
            c = close if close is not None else self.df["Close"]
            return ta.trend.ema_indicator(c, window=length)

        def atr(self, length=20):
            """ATR hesapla."""
            return ta.volatility.average_true_range(
                self.df["High"], self.df["Low"], self.df["Close"], window=length
            )

    # DataFrame'e .ta accessor ekle
    @pd.api.extensions.register_dataframe_accessor("ta")
    class TAPandasAccessor:
        def __init__(self, pandas_obj):
            self._obj = pandas_obj
            self._accessor = TAAccessor(pandas_obj)

        def __getattr__(self, name):
            return getattr(self._accessor, name)


from config import MIN_PERIODS
from logger import get_logger

logger = get_logger(__name__)

# ============================================================
# TIMEFRAME BAZLI MİNİMUM PERİYOT AYARLARI
# ============================================================
# MIN_LIMITS artık config.py'den geliyor: MIN_PERIODS


def safe_get(series: pd.Series, idx: int = -1, default: float = np.nan) -> float:
    """
    Pandas Series'ten guvenli deger alma.

    Index hatasi veya NaN durumunda default deger dondurur.

    Args:
        series: Deger alinacak pandas Series
        idx: Index pozisyonu (varsayilan: -1, son eleman)
        default: Hata durumunda donecek deger

    Returns:
        Series'teki deger veya default
    """
    try:
        if series is None:
            return default
        val = series.iloc[idx]
        return val if not pd.isna(val) else default
    except (IndexError, KeyError, TypeError) as e:
        logger.debug(f"safe_get exception: {e}")
        return default


# ==========================================
# 1. STRATEJİ: COMBO (NaN TOLERANSLI, SABİT LİMİT)
# ==========================================
def calculate_combo_signal(df: pd.DataFrame, timeframe: str) -> dict[str, Any] | None:
    """
    COMBO stratejisi sinyal hesaplayici.

    4 temel indikator kullanir: MACD, RSI, Williams %R, CCI.
    Timeframe'e gore degisen esik degerleriyle AL/SAT sinyali uretir.

    Args:
        df: OHLCV verisi iceren DataFrame
        timeframe: Zaman dilimi (1D, W-FRI, 2W-FRI, 3W-FRI, ME)

    Returns:
        Sinyal sozlugu {'buy': bool, 'sell': bool, 'details': dict}
        Yetersiz veri durumunda None
    """
    min_limit = MIN_PERIODS.get(timeframe, 14)

    if df is None or len(df) < min_limit:
        return None

    close, high, low = df["Close"], df["High"], df["Low"]

    # Eşik değerleri - SABİT
    buy_limit, sell_limit = 4, 4
    if timeframe in ["1D", "D", "Daily"] or timeframe == "W-FRI":
        buy_limit, sell_limit = 4, 3
    elif timeframe in ["2W-FRI", "3W-FRI", "ME"]:
        buy_limit, sell_limit = 3, 3

    last_date = df.index[-1]
    last_price = close.iloc[-1]

    # ============================================================
    # İNDİKATÖRLER - HER BİRİ AYRI TRY-EXCEPT İÇİNDE
    # ============================================================

    # 1. MACD
    try:
        macd = df.ta.macd(close=close, fast=12, slow=26, signal=9)
        if macd is not None:
            macd_line = macd.iloc[:, 0]
            v_macd = safe_get(macd_line)
        else:
            v_macd = np.nan
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"MACD calculation error: {e}")
        v_macd = np.nan

    # 2. RSI
    try:
        rsi = df.ta.rsi(close=close, length=14)
        v_rsi = safe_get(rsi)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"RSI calculation error: {e}")
        v_rsi = np.nan

    # 3. Williams %R
    try:
        wr = df.ta.willr(high=high, low=low, close=close, length=14)
        v_wr = safe_get(wr)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"Williams %R calculation error: {e}")
        v_wr = np.nan

    # 4. CCI
    try:
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(20).mean()
        mad = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        cci = (tp - sma_tp) / (0.015 * mad)
        v_cci = safe_get(cci)
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"CCI calculation error: {e}")
        v_cci = np.nan

    # ============================================================
    # PUANLAMA - NaN TOLERANSLI, SABİT LİMİT
    # ============================================================
    buy_score = 0
    sell_score = 0
    active_count = 0

    # MACD
    if not np.isnan(v_macd):
        active_count += 1
        if v_macd < 0:
            buy_score += 1
        if v_macd > 0:
            sell_score += 1

    # RSI
    if not np.isnan(v_rsi):
        active_count += 1
        if v_rsi < 40:
            buy_score += 1
        if v_rsi > 80:
            sell_score += 1

    # W%R
    if not np.isnan(v_wr):
        active_count += 1
        if v_wr < -80:
            buy_score += 1
        if v_wr > -10:
            sell_score += 1

    # CCI
    if not np.isnan(v_cci):
        active_count += 1
        if v_cci < -100:
            buy_score += 1
        if v_cci > 200:
            sell_score += 1

    # En az 1 aktif indikatör olmalı
    if active_count < 1:
        return None

    # SABİT LİMİT - 4/4 veya 3/4 (timeframe'e göre)
    return {
        "buy": buy_score >= buy_limit,
        "sell": sell_score >= sell_limit,
        "details": {
            "Score": f"+{buy_score}/-{sell_score}",
            "BuyScore": f"{buy_score}/{buy_limit}",
            "SellScore": f"{sell_score}/{sell_limit}",
            "ActiveIndicators": f"{active_count}/4",
            "DATE": str(last_date.date()),
            "PRICE": last_price,
            "MACD": round(v_macd, 4) if not np.isnan(v_macd) else 0,
            "RSI": round(v_rsi, 2) if not np.isnan(v_rsi) else 0,
            "WR": round(v_wr, 2) if not np.isnan(v_wr) else 0,
            "CCI": round(v_cci, 2) if not np.isnan(v_cci) else 0,
        },
    }


# ==========================================
# 2. STRATEJİ: HUNTER (NaN TOLERANSLI, SABİT LİMİT)
# ==========================================
def calculate_hunter_signal(df: pd.DataFrame, timeframe: str) -> dict[str, Any] | None:
    """
    HUNTER stratejisi sinyal hesaplayici.

    15 farkli indikator kullanir: RSI, RSI Fast, CMO, BOP, MACD,
    Williams %R, CCI, Ultimate Oscillator, Bollinger %B, ROC,
    DeMarker, PSY, Z-Score, Keltner %B, RSI(2).

    Args:
        df: OHLCV verisi iceren DataFrame
        timeframe: Zaman dilimi (1D, W-FRI, 2W-FRI, 3W-FRI, ME)

    Returns:
        Sinyal sozlugu {'buy': bool, 'sell': bool, 'details': dict}
        Yetersiz veri durumunda None
    """
    min_limit = MIN_PERIODS.get(timeframe, 14)

    if df is None or len(df) < min_limit:
        return None

    # Eşik değerleri - SABİT
    req_dip, req_tepe = 7, 10
    if timeframe in ["1D", "D", "Daily"] or timeframe == "W-FRI" or timeframe == "2W-FRI":
        req_dip, req_tepe = 7, 10
    elif timeframe == "3W-FRI" or timeframe == "ME":
        req_dip, req_tepe = 5, 10

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    open_p = df["Open"] if "Open" in df.columns else df["Close"]

    last_date = df.index[-1]
    last_price = close.iloc[-1]

    # ============================================================
    # İNDİKATÖR HESAPLAMALARI - HEPSİ AYRI TRY-EXCEPT İÇİNDE
    # ============================================================

    # 1. RSI (14)
    try:
        rsi = df.ta.rsi(close=close, length=14)
        v_rsi = safe_get(rsi)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"RSI-14 calc error: {e}")
        v_rsi = np.nan

    # 2. RSI Fast (7)
    try:
        rsi_fast = df.ta.rsi(close=close, length=7)
        v_rsi_fast = safe_get(rsi_fast)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"RSI-Fast calc error: {e}")
        v_rsi_fast = np.nan

    # 3. CMO (14)
    try:
        cmo = df.ta.cmo(close=close, length=14)
        v_cmo = safe_get(cmo)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"CMO calc error: {e}")
        v_cmo = np.nan

    # 4. BOP
    try:
        range_hl = high - low
        range_hl = range_hl.replace(0, np.nan)
        bop = (close - open_p) / range_hl
        bop = bop.fillna(0)
        v_bop = safe_get(bop, default=0)
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"BOP calc error: {e}")
        v_bop = np.nan

    # 5. MACD
    try:
        macd_df = df.ta.macd(close=close, fast=12, slow=26, signal=9)
        if macd_df is not None:
            macd_line = macd_df.iloc[:, 0]
            v_macd = safe_get(macd_line)
        else:
            v_macd = np.nan
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"MACD calc error: {e}")
        v_macd = np.nan

    # 6. W%R
    try:
        wr = df.ta.willr(high=high, low=low, close=close, length=14)
        v_wr = safe_get(wr)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"WR calc error: {e}")
        v_wr = np.nan

    # 7. CCI
    try:
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(20).mean()
        mad = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        cci = (tp - sma_tp) / (0.015 * mad)
        v_cci = safe_get(cci)
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"CCI calc error: {e}")
        v_cci = np.nan

    # 8. ULT (Ultimate Oscillator)
    try:
        ult = df.ta.uo(fast=7, medium=14, slow=28)
        v_ult = safe_get(ult)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"ULT calc error: {e}")
        v_ult = np.nan

    # 9. Bollinger %B
    try:
        bb_basis = close.rolling(20).mean()
        bb_dev = close.rolling(20).std()
        bb_u = bb_basis + (2.0 * bb_dev)
        bb_l = bb_basis - (2.0 * bb_dev)
        bbp = 100 * (close - bb_l) / (bb_u - bb_l + 1e-10)
        v_bbp = safe_get(bbp)
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"BBP calc error: {e}")
        v_bbp = np.nan

    # 10. ROC
    try:
        roc = close.pct_change(periods=14) * 100
        v_roc = safe_get(roc)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"ROC calc error: {e}")
        v_roc = np.nan

    # 11. DeM (DeMarker)
    try:
        de_max = high.diff()
        de_min = -low.diff()
        de_max = de_max.where(de_max > 0, 0)
        de_min = de_min.where(de_min > 0, 0)
        dm_up = de_max.rolling(14).mean()
        dm_dn = de_min.rolling(14).mean()
        dem = 100 * dm_up / (dm_up + dm_dn + 1e-10)
        v_dem = safe_get(dem)
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"DeM calc error: {e}")
        v_dem = np.nan

    # 12. PSY (Psychological Line)
    try:
        psy = (close > close.shift(1)).astype(float).rolling(12).mean() * 100
        v_psy = safe_get(psy)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"PSY calc error: {e}")
        v_psy = np.nan

    # 13. Z-Score
    try:
        z_mean = close.rolling(20).mean()
        z_std = close.rolling(20).std()
        zscore = (close - z_mean) / (z_std + 1e-10)
        v_z = safe_get(zscore)
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"ZScore calc error: {e}")
        v_z = np.nan

    # 14. Keltner %B
    try:
        ke_base = df.ta.ema(close=close, length=20)
        ke_atr = df.ta.atr(length=20)
        if ke_base is not None and ke_atr is not None:
            ke_u = ke_base + (2.0 * ke_atr)
            ke_l = ke_base - (2.0 * ke_atr)
            kpb = 100 * (close - ke_l) / (ke_u - ke_l + 1e-10)
            v_kpb = safe_get(kpb)
        else:
            v_kpb = np.nan
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as e:
        logger.debug(f"Keltner calc error: {e}")
        v_kpb = np.nan

    # 15. RSI(2)
    try:
        rsi2 = df.ta.rsi(close=close, length=2)
        v_rsi2 = safe_get(rsi2)
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"RSI2 calc error: {e}")
        v_rsi2 = np.nan

    # ============================================================
    # PUANLAMA - NaN TOLERANSLI, SABİT LİMİT
    # NaN olan indikatörler atlanır ama limit sabit kalır (7/15 veya 5/15)
    # ============================================================

    dip_c = 0
    top_c = 0
    active_count = 0

    # Her indikatör için: NaN değilse aktif say ve koşulu kontrol et
    indicators = [
        ("rsi", v_rsi, lambda x: x <= 30, lambda x: x >= 70),
        ("rsi_fast", v_rsi_fast, lambda x: x <= 20, lambda x: x >= 80),
        ("cmo", v_cmo, lambda x: x <= -50, lambda x: x >= 50),
        ("bop", v_bop, lambda x: x <= -0.7, lambda x: x >= 0.7),
        ("macd", v_macd, lambda x: x < 0, lambda x: x > 0),
        ("wr", v_wr, lambda x: x <= -80, lambda x: x >= -20),
        ("cci", v_cci, lambda x: x <= -100, lambda x: x >= 100),
        ("ult", v_ult, lambda x: x <= 30, lambda x: x >= 70),
        ("bbp", v_bbp, lambda x: x <= 0, lambda x: x >= 100),
        ("roc", v_roc, lambda x: x <= -5, lambda x: x >= 5),
        ("dem", v_dem, lambda x: x <= 30, lambda x: x >= 70),
        ("psy", v_psy, lambda x: x <= 25, lambda x: x >= 75),
        ("z", v_z, lambda x: x <= -2.0, lambda x: x >= 2.0),
        ("kpb", v_kpb, lambda x: x <= 0, lambda x: x >= 100),
        ("rsi2", v_rsi2, lambda x: x <= 10, lambda x: x >= 90),
    ]

    for name, value, dip_cond, top_cond in indicators:
        if not np.isnan(value):
            active_count += 1
            if dip_cond(value):
                dip_c += 1
            if top_cond(value):
                top_c += 1

    # En az 1 aktif indikatör olmalı
    if active_count < 1:
        return None

    # SABİT LİMİT - 7/15 veya 5/15 (timeframe'e göre)
    return {
        "buy": dip_c >= req_dip,
        "sell": top_c >= req_tepe,
        "details": {
            "DipScore": f"{dip_c}/{req_dip}",
            "TopScore": f"{top_c}/{req_tepe}",
            "ActiveIndicators": f"{active_count}/15",
            "DATE": str(last_date.date()),
            "PRICE": last_price,
            "RSI": round(v_rsi, 2) if not np.isnan(v_rsi) else "N/A",
            "RSI_Fast": round(v_rsi_fast, 2) if not np.isnan(v_rsi_fast) else "N/A",
            "CMO": round(v_cmo, 2) if not np.isnan(v_cmo) else "N/A",
            "BOP": round(v_bop, 2) if not np.isnan(v_bop) else "N/A",
            "MACD": round(v_macd, 4) if not np.isnan(v_macd) else "N/A",
            "W%R": round(v_wr, 2) if not np.isnan(v_wr) else "N/A",
            "CCI": round(v_cci, 2) if not np.isnan(v_cci) else "N/A",
            "ULT": round(v_ult, 2) if not np.isnan(v_ult) else "N/A",
            "BBP": round(v_bbp, 2) if not np.isnan(v_bbp) else "N/A",
            "ROC": round(v_roc, 2) if not np.isnan(v_roc) else "N/A",
            "DeM": round(v_dem, 2) if not np.isnan(v_dem) else "N/A",
            "PSY": round(v_psy, 2) if not np.isnan(v_psy) else "N/A",
            "ZScore": round(v_z, 2) if not np.isnan(v_z) else "N/A",
            "KeltPB": round(v_kpb, 2) if not np.isnan(v_kpb) else "N/A",
            "RSI2": round(v_rsi2, 2) if not np.isnan(v_rsi2) else "N/A",
        },
    }
