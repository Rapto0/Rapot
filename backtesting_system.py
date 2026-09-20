import math
import multiprocessing
import re
import warnings
from collections import deque
from collections.abc import Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime
from heapq import merge
from itertools import groupby
from typing import Any

import numpy as np
import pandas as pd
from isyatirimhisse import fetch_stock_data

from data_loader import (
    get_crypto_data,
    resample_market_data,
)
from infrastructure.time import utc_now_naive
from isyatirim_ssl import ensure_isyatirim_ca_bundle
from signals import calculate_combo_signal, calculate_hunter_signal

warnings.filterwarnings("ignore")


def get_bist_data_isyatirim_only(
    symbol: str, start_date: str = "01-01-2006"
) -> pd.DataFrame | None:
    """
    Backtest tarafında BIST verisini yalnızca İş Yatırım kaynağından kabul eder.
    """
    ensure_isyatirim_ca_bundle()

    try:
        raw_df = fetch_stock_data(symbols=[symbol], start_date=start_date)
    except Exception as exc:
        print(f"[WARN] {symbol}: Is Yatirim veri cekimi basarisiz: {exc}")
        return None

    if raw_df is None or raw_df.empty:
        print(f"[WARN] {symbol}: Is Yatirim veri kaynaginda veri bulunamadi.")
        return None

    rename_map = {
        "HGDG_TARIH": "Date",
        "HGDG_KAPANIS": "Close",
        "HGDG_MIN": "Low",
        "HGDG_MAX": "High",
        "HGDG_HACIM": "Volume",
    }
    df = raw_df.rename(columns=rename_map).copy()

    if "Date" not in df.columns:
        print(f"[WARN] {symbol}: Is Yatirim verisinde tarih kolonu bulunamadi.")
        return None

    open_candidates = (
        "HGDG_ACILIS",
        "HGDG_ACIK",
        "HGDG_OPEN",
        "ACILIS",
        "ACIK",
        "OPEN",
        "HGDG_AOF",
        "HG_AOF",
    )

    open_quality = "provider"
    discovered_open = next((column for column in open_candidates if column in raw_df.columns), None)
    if discovered_open is not None:
        df["Open"] = raw_df[discovered_open]
        if discovered_open in {"HGDG_AOF", "HG_AOF"}:
            open_quality = "aof_proxy"
    elif "Close" in df.columns:
        df["Open"] = df["Close"]
        open_quality = "close_proxy"
    else:
        print(f"[WARN] {symbol}: Is Yatirim verisinde Open/Close kolonu bulunamadi.")
        return None

    required = ("Open", "High", "Low", "Close", "Volume")
    missing = [column for column in required if column not in df.columns]
    if missing:
        print(f"[WARN] {symbol}: Is Yatirim verisinde eksik kolonlar: {', '.join(missing)}")
        return None

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date")

    for column in required:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df[list(required)].dropna().sort_index()
    if df.empty:
        print(f"[WARN] {symbol}: Is Yatirim verisi normalize sonrasi bos kaldi.")
        return None

    fetched_at = utc_now_naive().isoformat()
    df.attrs["source_hint"] = "isyatirim"
    df.attrs["open_quality"] = open_quality
    df.attrs["fetched_at_iso"] = fetched_at

    return df


# ============================================================
# İŞLEM MALİYETLERİ KONFÜGÜRASYONU
# ============================================================
@dataclass
class TradingCosts:
    """Tek yönlü, referans tutar üzerinden toplamsal backtest varsayımları.

    Komisyon ve kayma ayrı nakit maliyetleridir; gerçekleşme fiyatı modeli veya
    güncel bir aracı kurum ücret tarifesi değildir.
    """

    bist_commission: float = 0.001
    crypto_commission: float = 0.001
    bist_slippage: float = 0.0005
    crypto_slippage: float = 0.0003

    def __post_init__(self) -> None:
        self.get_components("BIST")
        self.get_components("CRYPTO")

    def get_components(self, market_type: str) -> tuple[float, float]:
        """Değiştirilebilir ayarları her işlemden önce yeniden doğrula."""
        if market_type == "BIST":
            commission, slippage = self.bist_commission, self.bist_slippage
        elif market_type == "CRYPTO":
            commission, slippage = self.crypto_commission, self.crypto_slippage
        else:
            raise ValueError("market_type must be BIST or CRYPTO")
        if not all(_finite_nonnegative(value) for value in (commission, slippage)):
            raise ValueError("Cost rates must be finite and nonnegative")
        if commission + slippage >= 1:
            raise ValueError("Combined one-way cost rate must be below one")
        return commission, slippage

    def get_total_cost(self, market_type: str) -> float:
        """Toplam işlem maliyeti (tek yön)"""
        return sum(self.get_components(market_type))


def _finite_nonnegative(value: float) -> bool:
    try:
        return not isinstance(value, bool) and math.isfinite(value) and value >= 0
    except (TypeError, ValueError, OverflowError):
        return False


def _valid_trade_input(price: float, date: datetime) -> bool:
    return (
        _finite_nonnegative(price)
        and price > 0
        and isinstance(date, datetime)
        and not pd.isna(date)
    )


# Global trading costs instance
trading_costs = TradingCosts()


class Lot:
    """Tek alışın miktarı, referans fiyatı ve tüm alış maliyetleri."""

    def __init__(
        self,
        symbol: str,
        shares: float,
        price: float,
        date: datetime,
        signal: str,
        *,
        commission: float = 0.0,
        slippage: float = 0.0,
    ) -> None:
        self.symbol = symbol
        self.shares = shares
        self.price = price
        self.date = date
        self.signal = signal
        self.commission = commission
        self.slippage = slippage
        self.invested = shares * price + commission + slippage


class Portfolio:
    """FIFO mantığıyla lot bazlı portföy yönetimi - Komisyon destekli"""

    def __init__(
        self,
        initial_cash: float,
        market_type: str,
        trade_amount: float,
        costs: TradingCosts | None = None,
    ) -> None:
        if not all(
            _finite_nonnegative(value) and value > 0 for value in (initial_cash, trade_amount)
        ):
            raise ValueError("Initial cash and trade amount must be finite and positive")
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self._cash_compensation = 0.0
        self.market_type = market_type
        self.trade_amount = trade_amount
        self.costs = costs or trading_costs
        self.costs.get_components(market_type)

        # Sembol bazlı lot kuyrukları (FIFO için)
        self.lots = {}  # {symbol: deque([Lot1, Lot2, ...])}

        # Tüm işlemler
        self.all_trades = []

        # Sembol bazlı performans
        self.symbol_performance = {}

        # Portföy değeri takibi
        self.equity_curve = []
        self.backtest_metadata: dict[str, Any] = {}

        # Kayma komisyon değildir; iki gider ayrı izlenir.
        self.total_commission_paid = 0.0
        self.total_slippage_cost = 0.0

    @property
    def total_transaction_cost(self) -> float:
        return self.total_commission_paid + self.total_slippage_cost

    def _cash_after(self, amount: float) -> tuple[float, float]:
        """Kahan toplamıyla çok sayıda kesirli nakit hareketinin hatasını sınırla."""
        adjusted = amount - self._cash_compensation
        balance = self.cash + adjusted
        return balance, (balance - self.cash) - adjusted

    def buy(self, symbol: str, price: float, date: datetime, signal_type: str) -> bool:
        """Sabit bütçenin içinde referans tutar, komisyon ve kayma bulunur."""
        if not isinstance(symbol, str) or not symbol.strip() or not _valid_trade_input(price, date):
            return False
        commission_rate, slippage_rate = self.costs.get_components(self.market_type)
        cost_rate = commission_rate + slippage_rate
        if not _finite_nonnegative(self.trade_amount) or self.trade_amount <= 0:
            return False
        if not _finite_nonnegative(self.cash):
            return False
        balance, compensation = self._cash_after(-self.trade_amount)
        if balance < 0:
            # Temsil artığı için ULP sınırını ayrıca mevcut bütçeye göre daralt.
            tolerance = min(
                8
                * max(
                    math.ulp(value) for value in (self.initial_cash, self.cash, self.trade_amount)
                ),
                self.trade_amount * 1e-12,
            )
            if balance < -tolerance:
                return False
            balance, compensation = 0.0, 0.0

        shares = self.trade_amount / (price * (1 + cost_rate))
        gross_cost = shares * price
        commission = gross_cost * commission_rate
        slippage = gross_cost * slippage_rate
        if not all(_finite_nonnegative(value) and value > 0 for value in (shares, gross_cost)):
            return False
        # Bütçe doğrudan kullanılır; float çarpımındaki son bit nakdi eksiye indirmez.
        actual_cost = self.trade_amount
        new_lot = Lot(
            symbol, shares, price, date, signal_type, commission=commission, slippage=slippage
        )
        new_lot.invested = actual_cost
        if not all(
            _finite_nonnegative(value)
            for value in (
                balance,
                self.total_commission_paid + commission,
                self.total_slippage_cost + slippage,
            )
        ):
            return False

        # Nakit düş
        self.cash, self._cash_compensation = balance, compensation
        self.total_commission_paid += commission
        self.total_slippage_cost += slippage

        # Sembol için kuyruk yoksa oluştur
        if symbol not in self.lots:
            self.lots[symbol] = deque()

        # Kuyruğa ekle
        self.lots[symbol].append(new_lot)

        # İşlemi kaydet
        self.all_trades.append(
            {
                "Tarih": date,
                "Sembol": symbol,
                "İşlem": "ALIM",
                "Fiyat": round(price, 4),
                "Miktar": round(shares, 6),
                "Tutar": round(gross_cost, 2),
                "Komisyon": round(commission, 2),
                "Kayma Maliyeti": round(slippage, 2),
                "Toplam İşlem Maliyeti": round(commission + slippage, 2),
                "Maliyet Tabanı": round(actual_cost, 2),
                "Nakit Akışı": round(-actual_cost, 2),
                "Sinyal": signal_type,
                "Kalan Nakit": round(self.cash, 2),
                "Toplam Lot": len(self.lots[symbol]),
            }
        )

        return True

    def sell(self, symbol: str, price: float, date: datetime, signal_type: str) -> bool:
        """En eski lot'u sat (FIFO) - Komisyon dahil"""

        # Sembol için lot var mı?
        if (
            not isinstance(symbol, str)
            or not symbol.strip()
            or not _valid_trade_input(price, date)
            or not self.lots.get(symbol)
        ):
            return False

        # Hesaplama/validasyon hatası FIFO kuyruğundan lot kaybettirmemeli.
        oldest_lot = self.lots[symbol][0]
        commission_rate, slippage_rate = self.costs.get_components(self.market_type)
        try:
            if date < oldest_lot.date:
                return False
            holding_days = (date - oldest_lot.date).days
        except (TypeError, ValueError, OverflowError):
            return False

        # İki gider de aynı referans tutardan düşülür; kayma ikinci kez fiyatlanmaz.
        gross_revenue = oldest_lot.shares * price
        commission = gross_revenue * commission_rate
        slippage = gross_revenue * slippage_rate
        net_revenue = gross_revenue - commission - slippage
        if not all(_finite_nonnegative(value) for value in (gross_revenue, net_revenue)):
            return False

        # Kar/Zarar (komisyonlar dahil)
        profit = net_revenue - oldest_lot.invested
        profit_pct = (profit / oldest_lot.invested) * 100
        if not math.isfinite(profit) or not math.isfinite(profit_pct):
            return False
        balance, compensation = self._cash_after(net_revenue)
        if not all(
            _finite_nonnegative(value)
            for value in (
                balance,
                self.total_commission_paid + commission,
                self.total_slippage_cost + slippage,
            )
        ):
            return False

        # Nakde ekle
        self.lots[symbol].popleft()
        self.cash, self._cash_compensation = balance, compensation
        self.total_commission_paid += commission
        self.total_slippage_cost += slippage

        # İşlemi kaydet
        self.all_trades.append(
            {
                "Tarih": date,
                "Sembol": symbol,
                "İşlem": "SATIM",
                "Fiyat": round(price, 4),
                "Miktar": round(oldest_lot.shares, 6),
                "Tutar": round(gross_revenue, 2),
                "Komisyon": round(commission, 2),
                "Kayma Maliyeti": round(slippage, 2),
                "Toplam İşlem Maliyeti": round(commission + slippage, 2),
                "Net Tutar": round(net_revenue, 2),
                "Nakit Akışı": round(net_revenue, 2),
                "Maliyet Tabanı": round(oldest_lot.invested, 2),
                "Alış Komisyonu": round(oldest_lot.commission, 2),
                "Alış Kayma Maliyeti": round(oldest_lot.slippage, 2),
                "Alış Fiyatı": round(oldest_lot.price, 4),
                "Alış Tarihi": oldest_lot.date,
                "Tutma Süresi (Gün)": holding_days,
                "Kar/Zarar": round(profit, 2),
                "Kar/Zarar %": round(profit_pct, 2),
                "Sinyal": signal_type,
                "Kalan Nakit": round(self.cash, 2),
                "Kalan Lot": len(self.lots[symbol]),
            }
        )

        # Sembol performansını güncelle
        if symbol not in self.symbol_performance:
            self.symbol_performance[symbol] = {
                "Toplam Kar/Zarar": 0,
                "Toplam Yatırım": 0,
                "Tamamlanan İşlem": 0,
                "Kazanan": 0,
                "Kaybeden": 0,
                "Toplam Alım": 0,
                "Toplam Satım": 0,
                "Ortalama Tutma Süresi": [],
            }

        self.symbol_performance[symbol]["Toplam Kar/Zarar"] += profit
        self.symbol_performance[symbol]["Toplam Yatırım"] += oldest_lot.invested
        self.symbol_performance[symbol]["Tamamlanan İşlem"] += 1
        self.symbol_performance[symbol]["Toplam Satım"] += 1
        self.symbol_performance[symbol]["Ortalama Tutma Süresi"].append(holding_days)

        if profit > 0:
            self.symbol_performance[symbol]["Kazanan"] += 1
        else:
            self.symbol_performance[symbol]["Kaybeden"] += 1

        # Kuyruk boşaldıysa sil
        if len(self.lots[symbol]) == 0:
            del self.lots[symbol]

        return True

    def get_portfolio_value(self, current_prices: Mapping[str, float]) -> float:
        """Value every open lot at an explicit valid mark, without an entry-price fallback."""
        if not isinstance(current_prices, Mapping):
            raise ValueError("Current prices must be a symbol-to-price mapping")
        values = [self.cash]
        for symbol, lot_queue in self.lots.items():
            if not lot_queue:
                continue
            price = current_prices.get(symbol)
            if not _finite_nonnegative(price) or price <= 0:
                raise ValueError(f"Missing or invalid valuation price for {symbol}")
            values.extend(lot.shares * price for lot in lot_queue)
        if not all(_finite_nonnegative(value) for value in values):
            raise ValueError("Portfolio valuation must remain finite and nonnegative")
        try:
            return math.fsum(values)
        except OverflowError as error:
            raise ValueError("Portfolio valuation overflow") from error

    def record_equity(
        self,
        date: datetime,
        current_prices: Mapping[str, float],
        *,
        price_dates: Mapping[str, datetime] | None = None,
    ) -> None:
        """Record a complete mark; shared runs expose the age of carried closing prices."""
        if not isinstance(date, datetime) or pd.isna(date):
            raise ValueError("Equity date must be a valid timestamp")
        total_value = self.get_portfolio_value(current_prices)
        position_value = total_value - self.cash
        row = {
            "Tarih": date,
            "Toplam Değer": round(total_value, 2),
            "Nakit": round(self.cash, 2),
            "Pozisyon Değeri": round(position_value, 2),
        }
        if price_dates is not None:
            if not isinstance(price_dates, Mapping):
                raise ValueError("Price dates must be a symbol-to-timestamp mapping")
            held_dates = {}
            for symbol, lots in sorted(self.lots.items()):
                if not lots:
                    continue
                mark_date = price_dates.get(symbol)
                try:
                    valid = (
                        isinstance(mark_date, datetime)
                        and not pd.isna(mark_date)
                        and mark_date <= date
                    )
                except TypeError:
                    valid = False
                if not valid:
                    raise ValueError(f"Missing, incompatible or future price date for {symbol}")
                held_dates[symbol] = mark_date
            row.update(
                {
                    "Değerleme Modeli": "last_observed_close",
                    "Fiyat Tarihleri": held_dates,
                    "Eski Fiyatlı Semboller": [
                        symbol for symbol, mark_date in held_dates.items() if mark_date < date
                    ],
                }
            )
        self.equity_curve.append(row)

    def get_open_positions_summary(self):
        """Açık pozisyonların özeti"""
        summary = []
        for symbol, lot_queue in self.lots.items():
            total_shares = sum(lot.shares for lot in lot_queue)
            total_invested = sum(lot.invested for lot in lot_queue)
            reference_value = sum(lot.shares * lot.price for lot in lot_queue)
            avg_price = reference_value / total_shares if total_shares > 0 else 0
            avg_cost = total_invested / total_shares if total_shares > 0 else 0

            summary.append(
                {
                    "Sembol": symbol,
                    "Lot Sayısı": len(lot_queue),
                    "Toplam Miktar": round(total_shares, 6),
                    "Toplam Yatırım": round(total_invested, 2),
                    "Ortalama Fiyat": round(avg_price, 4),
                    "Ortalama Maliyet": round(avg_cost, 4),
                    "Alış Komisyonu": round(sum(lot.commission for lot in lot_queue), 2),
                    "Alış Kayma Maliyeti": round(sum(lot.slippage for lot in lot_queue), 2),
                }
            )

        return summary


class BacktestEngine:
    """Backtesting Motoru - FIFO Lot Sistemi"""

    TIMEFRAMES = [
        ("1D", "GÜNLÜK"),
        ("W-FRI", "1 HAFTALIK"),
        ("2W-FRI", "2 HAFTALIK"),
        ("3W-FRI", "3 HAFTALIK"),
        ("ME", "1 AYLIK"),
    ]

    # ============================================================
    # YENİ: Timeframe bazlı minimum periyot ayarları
    # TradingView ile uyumlu hale getirildi
    # ============================================================
    MIN_PERIODS = {
        "1D": 30,  # Günlük: 30 gün yeterli
        "W-FRI": 14,  # Haftalık: 14 hafta (~3.5 ay)
        "2W-FRI": 10,  # 2 Haftalık: 10 periyot (~5 ay)
        "3W-FRI": 8,  # 3 Haftalık: 8 periyot (~6 ay)
        "ME": 8,  # Aylık: 8 ay (ÖNCEKİ: 20 ay - ÇOK UZUNDU!)
    }

    def __init__(
        self,
        start_date: str | date | None = "2006-01-01",
        end_date: str | date | None = None,
        *,
        as_of: str | datetime | None = None,
    ) -> None:
        self.start_date = self._date_bound(start_date, "start_date")
        self.end_date = self._date_bound(end_date, "end_date")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be after end_date")
        self.as_of = self._as_utc(as_of)

    @staticmethod
    def _date_bound(value: str | date | None, name: str) -> pd.Timestamp | None:
        if value is None:
            return None
        if not isinstance(value, (str, date)) or (
            isinstance(value, str) and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
        ):
            raise ValueError(f"{name} must be a date without a time zone or time of day")
        try:
            stamp = pd.Timestamp(value)
            if pd.isna(stamp) or stamp.tzinfo is not None or stamp != stamp.normalize():
                raise ValueError("Not a calendar date")
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"Invalid {name}") from error
        return stamp

    @staticmethod
    def _as_utc(value: str | datetime | None) -> pd.Timestamp:
        if value is None:
            return pd.Timestamp.now(tz="UTC")
        try:
            if not isinstance(value, (str, datetime)):
                raise ValueError("Not a timestamp")
            stamp = pd.Timestamp(value)
            if pd.isna(stamp) or stamp.tzinfo is None:
                raise ValueError("A time zone is required")
            return stamp.tz_convert("UTC")
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("as_of must be a valid timezone-aware timestamp") from error

    def _prepare_daily_data(self, data: pd.DataFrame, market_type: str) -> pd.DataFrame:
        """Validate a copied daily feed before any portfolio mutation.

        Midnight after the labelled market day is a conservative closure bound;
        this deliberately excludes today's open even when it already occurred.
        """
        required = ["Open", "High", "Low", "Close", "Volume"]
        if not isinstance(data, pd.DataFrame):
            raise ValueError("data must be a daily OHLCV DataFrame")
        if not data.columns.is_unique or any(column not in data.columns for column in required):
            raise ValueError("Daily OHLCV columns must be present and unique")
        if not isinstance(data.index, pd.DatetimeIndex) or data.index.hasnans:
            raise ValueError("Daily data requires a DatetimeIndex without NaT")
        zone = "Europe/Istanbul" if market_type == "BIST" else "UTC"
        index = data.index
        if index.tz is not None:
            index = index.tz_convert(zone).tz_localize(None)
        if not index.is_unique or not index.equals(index.normalize()):
            raise ValueError("Daily timestamps must be unique market-calendar midnights")
        if data.attrs.get("open_quality") not in (None, "provider"):
            raise ValueError("next_open requires genuine Open prices; proxy/unknown open_quality")

        work = data.loc[:, required].copy(deep=True)
        work.index = index
        work = work.sort_index()
        # Add a calendar day before localization, so DST days need not last 24 hours.
        closed_at = (work.index + pd.Timedelta(days=1)).tz_localize(zone).tz_convert("UTC")
        admitted = closed_at <= self.as_of
        if self.end_date is not None:
            admitted &= work.index <= self.end_date
        work = work.loc[admitted].copy()

        for column in required:
            values = work[column]
            if (
                not pd.api.types.is_numeric_dtype(values)
                or pd.api.types.is_bool_dtype(values)
                or pd.api.types.is_complex_dtype(values)
            ):
                raise ValueError(f"{column} must contain real numeric values")
        values = work.to_numpy(dtype=float, na_value=np.nan)
        if not np.isfinite(values).all() or (values[:, :4] <= 0).any():
            raise ValueError("OHLC prices must be finite and positive; volume must be finite")
        if (values[:, 4] < 0).any():
            raise ValueError("Volume must be nonnegative")
        if (work["High"] < work[["Open", "Close", "Low"]].max(axis=1)).any() or (
            work["Low"] > work[["Open", "Close", "High"]].min(axis=1)
        ).any():
            raise ValueError("OHLC high/low bounds are inconsistent")
        return work.astype(float)

    def check_signals(self, df_daily, market_type, strategy="combo"):
        """Sinyal kontrolü"""

        signals = {"buy": {"cok_ucuz": False, "beles": False}, "sell": {"pahali": False}}

        hits = {"buy": {}, "sell": {}}

        for tf_code, _ in self.TIMEFRAMES:
            try:
                df_resampled = resample_market_data(df_daily.copy(), tf_code, market_type)

                # ============================================================
                # DÜZELTME: Timeframe'e özel minimum periyot kontrolü
                # ============================================================
                min_periods = self.MIN_PERIODS.get(tf_code, 14)

                if df_resampled is None or len(df_resampled) < min_periods:
                    continue

                if strategy == "combo":
                    result = calculate_combo_signal(df_resampled, tf_code)
                else:
                    result = calculate_hunter_signal(df_resampled, tf_code)

                if result:
                    if result["buy"]:
                        hits["buy"][tf_code] = True
                    if result["sell"]:
                        hits["sell"][tf_code] = True
            except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError):
                continue

        # ALIM SİGNALLERİ
        if "1D" in hits["buy"] and "W-FRI" in hits["buy"] and "3W-FRI" in hits["buy"]:
            signals["buy"]["cok_ucuz"] = True

        if "1D" in hits["buy"] and "2W-FRI" in hits["buy"] and "ME" in hits["buy"]:
            signals["buy"]["beles"] = True

        # SATIM SİGNALLERİ
        if "1D" in hits["sell"] and "W-FRI" in hits["sell"]:
            signals["sell"]["pahali"] = True

        return signals

    def _execution_start(self, frame: pd.DataFrame) -> int | None:
        """Keep the closed-history eligibility gate and the first 0..60 signal prefix."""
        if len(frame) < 120:
            return None
        start = 61
        if self.start_date is not None:
            start = max(start, int(frame.index.searchsorted(self.start_date)))
        return start if start < len(frame) else None

    @staticmethod
    def _load_daily_data(symbol: str, market_type: str) -> pd.DataFrame | None:
        if market_type == "BIST":
            return get_bist_data_isyatirim_only(symbol, start_date="01-01-2006")
        return get_crypto_data(symbol, start_str="8 years ago")

    def _execute_bar(
        self, symbol: str, frame: pd.DataFrame, index: int, portfolio: Portfolio
    ) -> None:
        """Apply the existing strategy/action order at the next observed Open."""
        execution_date = frame.index[index]
        signal_date = frame.index[index - 1]
        execution_price = float(frame["Open"].iloc[index])
        history = frame.iloc[:index].copy(deep=True)
        for strategy in ("combo", "hunter"):
            signals = self.check_signals(history.copy(deep=True), portfolio.market_type, strategy)
            actions = (
                (signals["buy"]["cok_ucuz"], portfolio.buy, "ÇOK UCUZ"),
                (signals["buy"]["beles"], portfolio.buy, "BELEŞ"),
                (signals["sell"]["pahali"], portfolio.sell, "PAHALI"),
            )
            for active, operation, label in actions:
                if active and operation(
                    symbol, execution_price, execution_date, f"{strategy.upper()}: {label}"
                ):
                    portfolio.all_trades[-1].update(
                        {"Sinyal Tarihi": signal_date, "Yürütme Modeli": "next_open"}
                    )

    @staticmethod
    def _execution_events(
        symbol: str, frame: pd.DataFrame, start: int
    ) -> Iterator[tuple[pd.Timestamp, str, int]]:
        for index in range(start, len(frame)):
            yield frame.index[index], symbol, index

    def run_single_symbol(
        self,
        symbol: str,
        market_type: str,
        portfolio: Portfolio,
        pbar: Any = None,
        *,
        data: pd.DataFrame | None = None,
    ) -> bool | None:
        """Execute prior closed-day signals at the next observed day's genuine Open.

        The supplied-data path never calls a provider. All eligible OHLCV rows
        are validated before a trade; dates are market-day labels, not fill times.
        """
        if market_type not in ("BIST", "CRYPTO") or portfolio.market_type != market_type:
            raise ValueError("market_type must match the BIST/CRYPTO portfolio")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("symbol must be a nonempty string")
        if any(lots for held, lots in portfolio.lots.items() if held != symbol):
            raise ValueError("Use run_backtest for a portfolio holding multiple symbols")
        if data is None:
            data = self._load_daily_data(symbol, market_type)
            if data is None:
                print(f"[WARN] {symbol}: Veri cekilemedi")
                return None
        frame = self._prepare_daily_data(data, market_type)
        # Preserve the historical minimum and signal warm-up. Future rows outside
        # end_date/as_of cannot make an otherwise ineligible input pass this gate.
        execution_start = self._execution_start(frame)
        if execution_start is None:
            print(f"[WARN] {symbol}: Yetersiz kapanmis gecmis veya aralikta islem gunu yok")
            return None
        print(
            f"[INFO] {symbol}: next_open, {frame.index[execution_start].date()}"
            f" -> {frame.index[-1].date()}, as_of={self.as_of.isoformat()}"
        )
        if pbar:
            with suppress(Exception):
                pbar.set_postfix({"Islenen": symbol})

        for i in range(execution_start, len(frame)):
            execution_date = frame.index[i]
            self._execute_bar(symbol, frame, i, portfolio)
            # Retain single-symbol sampling; shared runs record every union day.
            if i % 10 == 0 or i == len(frame) - 1:
                portfolio.record_equity(execution_date, {symbol: float(frame["Close"].iloc[i])})
        return True

    def run_backtest(
        self,
        symbols_list: Sequence[str],
        market_type: str,
        initial_cash: float,
        trade_amount: float,
        *,
        data_by_symbol: Mapping[str, pd.DataFrame] | None = None,
        costs: TradingCosts | None = None,
    ) -> Portfolio:
        """Run one market's shared cash in date/symbol order with daily closing marks.

        A supplied mapping must cover exactly the requested symbols and never
        falls back to providers. Validate all admitted feeds before any trade.
        Same-day lexical priority is deterministic, not a signal ranking.
        """
        if isinstance(symbols_list, (str, bytes)) or not isinstance(symbols_list, Sequence):
            raise ValueError("symbols_list must be a sequence of unique symbol strings")
        symbols = list(symbols_list)
        if any(
            not isinstance(symbol, str) or not symbol or symbol != symbol.strip()
            for symbol in symbols
        ) or len(set(symbols)) != len(symbols):
            raise ValueError("Symbols must be nonempty, trimmed and unique")
        symbols.sort()
        if data_by_symbol is not None and (
            not isinstance(data_by_symbol, Mapping) or set(data_by_symbol) != set(symbols)
        ):
            raise ValueError("data_by_symbol must cover exactly the requested symbols")
        portfolio = Portfolio(initial_cash, market_type, trade_amount, costs=costs)

        print(f"\n{'=' * 70}")
        print(f"🔄 {market_type} Backtest Başlatılıyor...")
        print(f"📊 Sembol Sayısı: {len(symbols_list)}")
        print(f"💰 Başlangıç Sermayesi: {initial_cash:,.2f}")
        print(f"💵 İşlem Başına Tutar: {trade_amount:,.2f}")
        print(f"{'=' * 70}\n")

        frames: dict[str, pd.DataFrame] = {}
        starts: dict[str, int] = {}
        skipped: dict[str, str] = {}
        for symbol in symbols:
            data = (
                self._load_daily_data(symbol, market_type)
                if data_by_symbol is None
                else data_by_symbol[symbol]
            )
            if data is None and data_by_symbol is None:
                skipped[symbol] = "provider_returned_none"
                continue
            frame = self._prepare_daily_data(data, market_type)
            start = self._execution_start(frame)
            if start is None:
                skipped[symbol] = (
                    "insufficient_closed_history" if len(frame) < 120 else "no_execution_dates"
                )
                continue
            frames[symbol], starts[symbol] = frame, start

        portfolio.backtest_metadata = {
            "processed_symbols": list(frames),
            "skipped_symbols": skipped,
            "execution_order": "date_then_lexical_symbol_then_existing_strategy_actions",
            "valuation_model": "last_observed_close",
            "as_of": self.as_of,
        }
        events = merge(
            *(
                self._execution_events(symbol, frame, starts[symbol])
                for symbol, frame in frames.items()
            )
        )
        prices: dict[str, float] = {}
        price_dates: dict[str, pd.Timestamp] = {}
        for execution_date, daily_events in groupby(events, key=lambda event: event[0]):
            day = list(daily_events)
            # All Open executions precede all marks for this market-day label.
            for _, symbol, index in day:
                self._execute_bar(symbol, frames[symbol], index, portfolio)
            for _, symbol, index in day:
                prices[symbol] = float(frames[symbol]["Close"].iloc[index])
                price_dates[symbol] = execution_date
            portfolio.record_equity(execution_date, prices, price_dates=price_dates)

        buys: dict[str, int] = {}
        for trade in portfolio.all_trades:
            if trade["İşlem"] == "ALIM":
                buys[trade["Sembol"]] = buys.get(trade["Sembol"], 0) + 1
        for symbol, performance in portfolio.symbol_performance.items():
            performance["Toplam Alım"] = buys.get(symbol, 0)
        print(f"✅ Tamamlandı: {len(frames)}/{len(symbols)} sembol işlendi\n")
        return portfolio

    def generate_excel_report(self, portfolio_bist, portfolio_crypto):
        """Detaylı Excel raporu"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_raporu_{timestamp}.xlsx"

        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            # 1. GENEL ÖZET
            bist_total_profit = sum(
                s["Toplam Kar/Zarar"] for s in portfolio_bist.symbol_performance.values()
            )
            crypto_total_profit = sum(
                s["Toplam Kar/Zarar"] for s in portfolio_crypto.symbol_performance.values()
            )

            bist_open_lots = sum(len(q) for q in portfolio_bist.lots.values())
            crypto_open_lots = sum(len(q) for q in portfolio_crypto.lots.values())

            summary = {
                "Metrik": [
                    "Başlangıç Sermayesi",
                    "Güncel Nakit",
                    "Gerçekleşen Kar/Zarar",
                    "Ödenen Komisyon",
                    "Kayma Maliyeti",
                    "Toplam İşlem Maliyeti",
                    "Getiri %",
                    "Toplam İşlem",
                    "Alım İşlemi",
                    "Satım İşlemi",
                    "Açık Lot Sayısı",
                    "İşlem Gören Sembol",
                ],
                "BIST": [
                    f"{portfolio_bist.initial_cash:,.2f} TL",
                    f"{portfolio_bist.cash:,.2f} TL",
                    f"{bist_total_profit:,.2f} TL",
                    f"{portfolio_bist.total_commission_paid:,.2f} TL",
                    f"{portfolio_bist.total_slippage_cost:,.2f} TL",
                    f"{portfolio_bist.total_transaction_cost:,.2f} TL",
                    f"{(bist_total_profit / portfolio_bist.initial_cash * 100):.2f}%",
                    len(portfolio_bist.all_trades),
                    len([t for t in portfolio_bist.all_trades if t["İşlem"] == "ALIM"]),
                    len([t for t in portfolio_bist.all_trades if t["İşlem"] == "SATIM"]),
                    bist_open_lots,
                    len(portfolio_bist.symbol_performance),
                ],
                "CRYPTO": [
                    f"{portfolio_crypto.initial_cash:,.2f} USD",
                    f"{portfolio_crypto.cash:,.2f} USD",
                    f"{crypto_total_profit:,.2f} USD",
                    f"{portfolio_crypto.total_commission_paid:,.2f} USD",
                    f"{portfolio_crypto.total_slippage_cost:,.2f} USD",
                    f"{portfolio_crypto.total_transaction_cost:,.2f} USD",
                    f"{(crypto_total_profit / portfolio_crypto.initial_cash * 100):.2f}%",
                    len(portfolio_crypto.all_trades),
                    len([t for t in portfolio_crypto.all_trades if t["İşlem"] == "ALIM"]),
                    len([t for t in portfolio_crypto.all_trades if t["İşlem"] == "SATIM"]),
                    crypto_open_lots,
                    len(portfolio_crypto.symbol_performance),
                ],
            }
            pd.DataFrame(summary).to_excel(writer, sheet_name="Genel Özet", index=False)

            # 2. BIST - TÜM İŞLEMLER
            if portfolio_bist.all_trades:
                df = pd.DataFrame(portfolio_bist.all_trades)
                df.to_excel(writer, sheet_name="BIST Tüm İşlemler", index=False)

            # 3. CRYPTO - TÜM İŞLEMLER
            if portfolio_crypto.all_trades:
                df = pd.DataFrame(portfolio_crypto.all_trades)
                df.to_excel(writer, sheet_name="Crypto Tüm İşlemler", index=False)

            # 4. BIST - SEMBOL PERFORMANSI
            if portfolio_bist.symbol_performance:
                perf_data = []
                for symbol, stats in portfolio_bist.symbol_performance.items():
                    avg_holding = (
                        np.mean(stats["Ortalama Tutma Süresi"])
                        if stats["Ortalama Tutma Süresi"]
                        else 0
                    )
                    perf_data.append(
                        {
                            "Sembol": symbol,
                            "Toplam Kar/Zarar (TL)": round(stats["Toplam Kar/Zarar"], 2),
                            "Toplam Yatırım (TL)": round(stats["Toplam Yatırım"], 2),
                            "Getiri %": round(
                                (stats["Toplam Kar/Zarar"] / stats["Toplam Yatırım"]) * 100, 2
                            ),
                            "Tamamlanan İşlem": stats["Tamamlanan İşlem"],
                            "Kazanan": stats["Kazanan"],
                            "Kaybeden": stats["Kaybeden"],
                            "Başarı Oranı %": round(
                                (stats["Kazanan"] / stats["Tamamlanan İşlem"]) * 100, 2
                            )
                            if stats["Tamamlanan İşlem"] > 0
                            else 0,
                            "Toplam Alım": stats["Toplam Alım"],
                            "Toplam Satım": stats["Toplam Satım"],
                            "Ort. Tutma Süresi (Gün)": round(avg_holding, 1),
                        }
                    )

                df = pd.DataFrame(perf_data).sort_values("Toplam Kar/Zarar (TL)", ascending=False)
                df.to_excel(writer, sheet_name="BIST Sembol Performans", index=False)

            # 5. CRYPTO - SEMBOL PERFORMANSI
            if portfolio_crypto.symbol_performance:
                perf_data = []
                for symbol, stats in portfolio_crypto.symbol_performance.items():
                    avg_holding = (
                        np.mean(stats["Ortalama Tutma Süresi"])
                        if stats["Ortalama Tutma Süresi"]
                        else 0
                    )
                    perf_data.append(
                        {
                            "Sembol": symbol,
                            "Toplam Kar/Zarar (USD)": round(stats["Toplam Kar/Zarar"], 2),
                            "Toplam Yatırım (USD)": round(stats["Toplam Yatırım"], 2),
                            "Getiri %": round(
                                (stats["Toplam Kar/Zarar"] / stats["Toplam Yatırım"]) * 100, 2
                            ),
                            "Tamamlanan İşlem": stats["Tamamlanan İşlem"],
                            "Kazanan": stats["Kazanan"],
                            "Kaybeden": stats["Kaybeden"],
                            "Başarı Oranı %": round(
                                (stats["Kazanan"] / stats["Tamamlanan İşlem"]) * 100, 2
                            )
                            if stats["Tamamlanan İşlem"] > 0
                            else 0,
                            "Toplam Alım": stats["Toplam Alım"],
                            "Toplam Satım": stats["Toplam Satım"],
                            "Ort. Tutma Süresi (Gün)": round(avg_holding, 1),
                        }
                    )

                df = pd.DataFrame(perf_data).sort_values("Toplam Kar/Zarar (USD)", ascending=False)
                df.to_excel(writer, sheet_name="Crypto Sembol Performans", index=False)

            # 6. BIST - AÇIK POZISYONLAR (LOT BAZLI)
            open_pos = portfolio_bist.get_open_positions_summary()
            if open_pos:
                pd.DataFrame(open_pos).to_excel(
                    writer, sheet_name="BIST Açık Pozisyonlar", index=False
                )

            # 7. CRYPTO - AÇIK POZISYONLAR (LOT BAZLI)
            open_pos = portfolio_crypto.get_open_positions_summary()
            if open_pos:
                pd.DataFrame(open_pos).to_excel(
                    writer, sheet_name="Crypto Açık Pozisyonlar", index=False
                )

            # 8. PORTFÖY DEĞERİ (BIST)
            if portfolio_bist.equity_curve:
                df = pd.DataFrame(portfolio_bist.equity_curve)
                df.to_excel(writer, sheet_name="BIST Portföy Değeri", index=False)

            # 9. PORTFÖY DEĞERİ (CRYPTO)
            if portfolio_crypto.equity_curve:
                df = pd.DataFrame(portfolio_crypto.equity_curve)
                df.to_excel(writer, sheet_name="Crypto Portföy Değeri", index=False)

        print(f"💾 Excel Rapor: {filename}")
        return filename

    def plot_results(self, portfolio_bist, portfolio_crypto):
        """Görsel raporlar"""
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # 1. BIST Portföy Değeri
        if portfolio_bist.equity_curve:
            ax1 = fig.add_subplot(gs[0, :2])
            df = pd.DataFrame(portfolio_bist.equity_curve)
            ax1.plot(
                df["Tarih"], df["Toplam Değer"], linewidth=2, color="blue", label="Portföy Değeri"
            )
            ax1.axhline(
                y=portfolio_bist.initial_cash,
                color="red",
                linestyle="--",
                label="Başlangıç",
                alpha=0.6,
            )
            ax1.fill_between(
                df["Tarih"], portfolio_bist.initial_cash, df["Toplam Değer"], alpha=0.3
            )
            ax1.set_title("🇹🇷 BIST Portföy Büyümesi", fontsize=12, fontweight="bold")
            ax1.set_ylabel("Değer (TL)")
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis="x", rotation=45)

        # 2. CRYPTO Portföy Değeri
        if portfolio_crypto.equity_curve:
            ax2 = fig.add_subplot(gs[1, :2])
            df = pd.DataFrame(portfolio_crypto.equity_curve)
            ax2.plot(
                df["Tarih"], df["Toplam Değer"], linewidth=2, color="orange", label="Portföy Değeri"
            )
            ax2.axhline(
                y=portfolio_crypto.initial_cash,
                color="red",
                linestyle="--",
                label="Başlangıç",
                alpha=0.6,
            )
            ax2.fill_between(
                df["Tarih"],
                portfolio_crypto.initial_cash,
                df["Toplam Değer"],
                alpha=0.3,
                color="orange",
            )
            ax2.set_title("💰 CRYPTO Portföy Büyümesi", fontsize=12, fontweight="bold")
            ax2.set_ylabel("Değer (USD)")
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.tick_params(axis="x", rotation=45)

        # 3. BIST Top 10 Performans
        if portfolio_bist.symbol_performance:
            ax3 = fig.add_subplot(gs[0, 2])
            sorted_perf = sorted(
                portfolio_bist.symbol_performance.items(),
                key=lambda x: x[1]["Toplam Kar/Zarar"],
                reverse=True,
            )[:10]
            symbols = [x[0] for x in sorted_perf]
            profits = [x[1]["Toplam Kar/Zarar"] for x in sorted_perf]
            colors = ["green" if p > 0 else "red" for p in profits]
            ax3.barh(symbols, profits, color=colors, alpha=0.7)
            ax3.set_title("BIST Top 10", fontsize=10, fontweight="bold")
            ax3.set_xlabel("Kar/Zarar (TL)", fontsize=9)
            ax3.tick_params(labelsize=8)
            ax3.grid(True, alpha=0.3, axis="x")

        # 4. CRYPTO Top 10 Performans
        if portfolio_crypto.symbol_performance:
            ax4 = fig.add_subplot(gs[1, 2])
            sorted_perf = sorted(
                portfolio_crypto.symbol_performance.items(),
                key=lambda x: x[1]["Toplam Kar/Zarar"],
                reverse=True,
            )[:10]
            symbols = [x[0] for x in sorted_perf]
            profits = [x[1]["Toplam Kar/Zarar"] for x in sorted_perf]
            colors = ["green" if p > 0 else "red" for p in profits]
            ax4.barh(symbols, profits, color=colors, alpha=0.7)
            ax4.set_title("Crypto Top 10", fontsize=10, fontweight="bold")
            ax4.set_xlabel("Kar/Zarar (USD)", fontsize=9)
            ax4.tick_params(labelsize=8)
            ax4.grid(True, alpha=0.3, axis="x")

        # 5. İstatistikler
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis("off")

        bist_stats = self._calculate_stats(portfolio_bist)
        crypto_stats = self._calculate_stats(portfolio_crypto)

        stats_text = f"""
        ╔═══════════════════════════════════════════════════════════════════════════════╗
        ║                            📊 BACKTEST İSTATİSTİKLERİ                        ║
        ╠═══════════════════════════════════════════════════════════════════════════════╣
        ║  BIST:                                     │  CRYPTO:                         ║
        ║  • Toplam Kar/Zarar: {bist_stats["profit"]:>10.2f} TL    │  • Toplam Kar/Zarar: {crypto_stats["profit"]:>10.2f} USD ║
        ║  • Başarı Oranı: {bist_stats["win_rate"]:>14.1f}%        │  • Başarı Oranı: {crypto_stats["win_rate"]:>14.1f}%      ║
        ║  • Tamamlanan İşlem: {bist_stats["trades"]:>11}         │  • Tamamlanan İşlem: {crypto_stats["trades"]:>11}       ║
        ║  • Açık Lot: {bist_stats["open_lots"]:>20}         │  • Açık Lot: {crypto_stats["open_lots"]:>20}       ║
        ╚═══════════════════════════════════════════════════════════════════════════════╝
        """
        ax5.text(
            0.5,
            0.5,
            stats_text,
            fontsize=10,
            family="monospace",
            ha="center",
            va="center",
            bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.3},
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_grafik_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"📈 Grafik: {filename}")
        plt.close()

    def _calculate_stats(self, portfolio):
        """İstatistik hesapla"""
        total_profit = sum(s["Toplam Kar/Zarar"] for s in portfolio.symbol_performance.values())

        completed_trades = sum(s["Tamamlanan İşlem"] for s in portfolio.symbol_performance.values())
        winning_trades = sum(s["Kazanan"] for s in portfolio.symbol_performance.values())
        win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0

        open_lots = sum(len(q) for q in portfolio.lots.values())

        return {
            "profit": total_profit,
            "win_rate": win_rate,
            "trades": completed_trades,
            "open_lots": open_lots,
        }

    def print_summary(self, portfolio_bist, portfolio_crypto):
        """Konsol özeti"""

        print("\n" + "=" * 70)
        print("📊 BACKTEST SONUÇ ÖZETİ")
        print("=" * 70)

        # BIST
        bist_stats = self._calculate_stats(portfolio_bist)
        print("\n🇹🇷 BIST:")
        print("-" * 50)
        print(f"  Başlangıç: {portfolio_bist.initial_cash:,.2f} TL")
        print(f"  Güncel Nakit: {portfolio_bist.cash:,.2f} TL")
        print(f"  Gerçekleşen Kar/Zarar: {bist_stats['profit']:,.2f} TL")
        print(f"  Ödenen Komisyon: {portfolio_bist.total_commission_paid:,.2f} TL")
        print(f"  Kayma Maliyeti: {portfolio_bist.total_slippage_cost:,.2f} TL")
        print(f"  Toplam İşlem Maliyeti: {portfolio_bist.total_transaction_cost:,.2f} TL")
        print(f"  Toplam İşlem: {len(portfolio_bist.all_trades)}")
        print(f"  Tamamlanan İşlem: {bist_stats['trades']}")
        print(f"  Başarı Oranı: {bist_stats['win_rate']:.1f}%")
        print(f"  Açık Lot Sayısı: {bist_stats['open_lots']}")

        # CRYPTO
        crypto_stats = self._calculate_stats(portfolio_crypto)
        print("\n💰 CRYPTO:")
        print("-" * 50)
        print(f"  Başlangıç: {portfolio_crypto.initial_cash:,.2f} USD")
        print(f"  Güncel Nakit: {portfolio_crypto.cash:,.2f} USD")
        print(f"  Gerçekleşen Kar/Zarar: {crypto_stats['profit']:,.2f} USD")
        print(f"  Ödenen Komisyon: {portfolio_crypto.total_commission_paid:,.2f} USD")
        print(f"  Kayma Maliyeti: {portfolio_crypto.total_slippage_cost:,.2f} USD")
        print(f"  Toplam İşlem Maliyeti: {portfolio_crypto.total_transaction_cost:,.2f} USD")
        print(f"  Toplam İşlem: {len(portfolio_crypto.all_trades)}")
        print(f"  Tamamlanan İşlem: {crypto_stats['trades']}")
        print(f"  Başarı Oranı: {crypto_stats['win_rate']:.1f}%")
        print(f"  Açık Lot Sayısı: {crypto_stats['open_lots']}")

        print("\n" + "=" * 70 + "\n")


# ============================================================
# BENCHMARK KARŞILAŞTIRMA
# ============================================================
class BenchmarkComparison:
    """Strateji performansını benchmark ile karşılaştırır"""

    BENCHMARKS = {
        # XU100, İş Yatırım hisse veri kaynağında doğrudan desteklenmediği için devre dışı.
        "BIST": None,
        "CRYPTO": "BTCUSDT",  # Bitcoin
    }

    def __init__(self, start_date: str, end_date: str = None):
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        self.benchmark_data = {}

    def fetch_benchmark(self, market_type: str) -> pd.DataFrame | None:
        """Benchmark verisini çeker"""
        symbol = self.BENCHMARKS.get(market_type)
        if not symbol:
            return None

        try:
            if market_type == "BIST":
                df = get_bist_data_isyatirim_only(symbol, start_date="01-01-2006")
            else:
                df = get_crypto_data(symbol, start_str="8 years ago")

            if df is not None and not df.empty:
                self.benchmark_data[market_type] = df
                return df
        except Exception as e:
            print(f"Benchmark veri hatası ({symbol}): {e}")

        return None

    def calculate_benchmark_return(
        self, market_type: str, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> float:
        """Benchmark getirisini hesaplar"""
        df = self.benchmark_data.get(market_type)
        if df is None or df.empty:
            return 0.0

        try:
            # Tarih aralığına filtrele
            mask = (df.index >= start_date) & (df.index <= end_date)
            filtered = df.loc[mask]

            if len(filtered) < 2:
                return 0.0

            start_price = filtered["Close"].iloc[0]
            end_price = filtered["Close"].iloc[-1]

            return ((end_price - start_price) / start_price) * 100
        except Exception:
            return 0.0

    def compare(self, portfolio: Portfolio, market_type: str) -> dict[str, Any]:
        """Portföy vs Benchmark karşılaştırması"""
        # Benchmark verisini çek
        self.fetch_benchmark(market_type)

        # Portföy getirisi
        total_profit = sum(s["Toplam Kar/Zarar"] for s in portfolio.symbol_performance.values())
        portfolio_return = (total_profit / portfolio.initial_cash) * 100

        # Benchmark getirisi (equity curve'dan tarih al)
        benchmark_return = 0.0
        if portfolio.equity_curve:
            start_date = portfolio.equity_curve[0]["Tarih"]
            end_date = portfolio.equity_curve[-1]["Tarih"]
            benchmark_return = self.calculate_benchmark_return(market_type, start_date, end_date)

        # Alpha (fazla getiri)
        alpha = portfolio_return - benchmark_return

        return {
            "portfolio_return": portfolio_return,
            "benchmark_return": benchmark_return,
            "alpha": alpha,
            "benchmark_symbol": self.BENCHMARKS.get(market_type) or "N/A",
        }


# ============================================================
# WALK-FORWARD ANALİZ
# ============================================================
class WalkForwardAnalysis:
    """
    Walk-Forward Optimization/Validation
    Veri: [Train 70% | Test 30%] x N pencere
    """

    def __init__(self, n_splits: int = 5, train_ratio: float = 0.7):
        self.n_splits = n_splits
        self.train_ratio = train_ratio
        self.results = []

    def split_data(self, df: pd.DataFrame) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """Veriyi train/test parçalarına böler"""
        splits = []
        total_len = len(df)
        window_size = total_len // self.n_splits

        for i in range(self.n_splits):
            start_idx = i * (window_size // 2)  # Overlap için yarım kaydır
            end_idx = start_idx + window_size

            if end_idx > total_len:
                break

            window = df.iloc[start_idx:end_idx]
            train_size = int(len(window) * self.train_ratio)

            train = window.iloc[:train_size]
            test = window.iloc[train_size:]

            if len(train) > 30 and len(test) > 10:
                splits.append((train, test))

        return splits

    def run_walk_forward(
        self, symbol: str, market_type: str, strategy: str = "combo"
    ) -> dict[str, Any]:
        """Walk-forward analiz çalıştır"""
        # Veri çek
        if market_type == "BIST":
            df = get_bist_data_isyatirim_only(symbol, start_date="01-01-2006")
        else:
            df = get_crypto_data(symbol, start_str="8 years ago")

        if df is None or len(df) < 120:
            return {"error": "Yetersiz veri"}

        splits = self.split_data(df)

        window_results = []
        for i, (train, test) in enumerate(splits):
            # Test döneminde strateji performansını ölç
            # (Basitleştirilmiş versiyon)
            test_return = (
                (test["Close"].iloc[-1] - test["Close"].iloc[0]) / test["Close"].iloc[0]
            ) * 100

            window_results.append(
                {
                    "window": i + 1,
                    "train_start": train.index[0],
                    "train_end": train.index[-1],
                    "test_start": test.index[0],
                    "test_end": test.index[-1],
                    "test_return": round(test_return, 2),
                }
            )

        self.results = window_results

        # Özet istatistikler
        returns = [w["test_return"] for w in window_results]

        return {
            "symbol": symbol,
            "strategy": strategy,
            "n_windows": len(window_results),
            "avg_return": round(np.mean(returns), 2) if returns else 0,
            "std_return": round(np.std(returns), 2) if returns else 0,
            "min_return": round(min(returns), 2) if returns else 0,
            "max_return": round(max(returns), 2) if returns else 0,
            "windows": window_results,
        }


# ============================================================
# PARALEL BACKTEST
# ============================================================
def _run_symbol_backtest(args: tuple) -> dict[str, Any]:
    """
    Tek sembol için backtest (multiprocessing worker)
    Not: Bu fonksiyon modül seviyesinde olmalı (pickle için)
    """
    if len(args) == 4:
        symbol, market_type, start_date, trade_amount = args
        end_date, as_of = None, None
    elif len(args) == 6:
        symbol, market_type, start_date, trade_amount, end_date, as_of = args
    else:
        raise ValueError("A backtest worker requires 4 legacy or 6 bounded arguments")

    try:
        # Engine oluştur (her worker için ayrı)
        engine = BacktestEngine(start_date=start_date, end_date=end_date, as_of=as_of)
        initial_cash = 100000 if market_type == "BIST" else 20000

        # The engine owns the one provider read and validates that same snapshot.
        portfolio = Portfolio(initial_cash, market_type, trade_amount)
        result = engine.run_single_symbol(symbol, market_type, portfolio)

        if result:
            total_profit = sum(s["Toplam Kar/Zarar"] for s in portfolio.symbol_performance.values())
            return {
                "symbol": symbol,
                "success": True,
                "profit": total_profit,
                "trades": len(portfolio.all_trades),
                "commission_paid": portfolio.total_commission_paid,
                "slippage_cost": portfolio.total_slippage_cost,
                "transaction_cost": portfolio.total_transaction_cost,
            }

        return {"symbol": symbol, "success": False, "error": "İşlem yok"}

    except Exception as e:
        return {"symbol": symbol, "success": False, "error": str(e)}


def run_parallel_backtest(
    symbols: list[str],
    market_type: str,
    start_date: str = "2006-01-01",
    max_workers: int | None = None,
    *,
    end_date: str | date | None = None,
    as_of: str | datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Her sembolü kendi başlangıç sermayesiyle bağımsız çalıştır.

    Args:
        symbols: Sembol listesi
        market_type: BIST veya CRYPTO
        start_date: Başlangıç tarihi
        max_workers: Maksimum worker sayısı (None = CPU sayısı)
        end_date: Son işlem günü (dahil)
        as_of: Tüm worker'lar için sabit, saat dilimli kapanış sınırı

    Returns:
        Her bağımsız sembol deneyi için sonuç listesi; ortak nakit portföyü değildir.
    """
    if market_type not in ("BIST", "CRYPTO"):
        raise ValueError("market_type must be BIST or CRYPTO")
    bounds = BacktestEngine(start_date=start_date, end_date=end_date, as_of=as_of)
    from tqdm import tqdm

    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), 8)

    trade_amount = 1000 if market_type == "BIST" else 100

    # Worker argümanları hazırla
    args_list = [
        (sym, market_type, bounds.start_date, trade_amount, bounds.end_date, bounds.as_of)
        for sym in symbols
    ]

    results = []

    print(f"\n⚡ Paralel Backtest: {len(symbols)} sembol, {max_workers} worker")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_symbol_backtest, args): args[0] for args in args_list}

        with tqdm(total=len(futures), desc="Paralel") as pbar:
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result(timeout=300)  # 5 dakika timeout
                    results.append(result)
                except Exception as e:
                    results.append({"symbol": symbol, "success": False, "error": str(e)})
                pbar.update(1)

    # Özet
    successful = [r for r in results if r.get("success")]
    total_profit = sum(r.get("profit", 0) for r in successful)

    print(f"\n✅ Tamamlandı: {len(successful)}/{len(symbols)} başarılı")
    print(f"💰 Bağımsız sembol kâr/zarar toplamı: {total_profit:,.2f}")

    return results


def main():
    """Ana fonksiyon"""

    print("\n" + "=" * 70)
    print("🚀 BACKTEST SİSTEMİ v2.0 - Komisyon + Benchmark + Paralel")
    print("=" * 70)
    print("\n⚙️  Yeni Özellikler:")
    print("   • Komisyon + Slippage desteği (%0.15 toplam)")
    print("   • Benchmark karşılaştırma (Crypto/BTC)")
    print("   • Walk-Forward analiz")
    print("   • Paralel backtest (multiprocessing)\n")

    engine = BacktestEngine(start_date="2006-01-01")

    # Test sembolleri
    bist_symbols = [
        "BSOKE",  # BIST100'den
    ]
    crypto_symbols = ["BTCUSDT"]

    # BIST Backtest (normal)
    portfolio_bist = engine.run_backtest(
        bist_symbols, "BIST", initial_cash=100000, trade_amount=1000
    )

    # Crypto Backtest (normal)
    portfolio_crypto = engine.run_backtest(
        crypto_symbols, "CRYPTO", initial_cash=20000, trade_amount=100
    )

    # Sonuçlar
    engine.print_summary(portfolio_bist, portfolio_crypto)

    # Benchmark karşılaştırma
    print("\n📊 BENCHMARK KARŞILAŞTIRMA")
    print("-" * 50)
    benchmark = BenchmarkComparison(start_date="2006-01-01")

    bist_comp = benchmark.compare(portfolio_bist, "BIST")
    print(f"  BIST Strateji: {bist_comp['portfolio_return']:.2f}%")
    print("  BIST Benchmark: Devre dışı (XU100 İş Yatırım kaynağında yok)")

    crypto_comp = benchmark.compare(portfolio_crypto, "CRYPTO")
    print(f"\n  Crypto Strateji: {crypto_comp['portfolio_return']:.2f}%")
    print(f"  Bitcoin ({crypto_comp['benchmark_symbol']}): {crypto_comp['benchmark_return']:.2f}%")
    print(f"  Alpha: {crypto_comp['alpha']:+.2f}%")

    # Raporlar
    engine.generate_excel_report(portfolio_bist, portfolio_crypto)
    engine.plot_results(portfolio_bist, portfolio_crypto)

    print("\n✅ Backtest tamamlandı!\n")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
