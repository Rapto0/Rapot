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
            "Kaydedilen İşlem Sayısı": len(self.all_trades),
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

        # Only a fresh portfolio has an unambiguous opening-cash baseline.
        fresh = (
            not portfolio.all_trades
            and not portfolio.equity_curve
            and not any(portfolio.lots.values())
        )
        portfolio.backtest_metadata.update(
            {
                "comparison_start": frame.index[execution_start] if fresh else None,
                "comparison_end": frame.index[-1],
                "comparison_initial_value": portfolio.cash if fresh else None,
                "as_of": self.as_of,
            }
        )
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
            "comparison_start": min(
                (frame.index[starts[symbol]] for symbol, frame in frames.items()), default=None
            ),
            "comparison_end": max((frame.index[-1] for frame in frames.values()), default=None),
            "comparison_initial_value": initial_cash,
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

    def generate_excel_report(self, portfolio_bist, portfolio_crypto, *, output_path=None):
        """Write an optional workbook with NAV and realized-lot results kept separate."""
        from pathlib import Path

        filename = Path(output_path or f"backtest_raporu_{datetime.now():%Y%m%d_%H%M%S}.xlsx")
        try:
            writer = pd.ExcelWriter(filename, engine="openpyxl")
        except ImportError as error:
            raise RuntimeError(
                "Excel output requires optional openpyxl; JSON/CSV/SVG remain available"
            ) from error
        with writer:
            metrics = [
                "Başlangıç Sermayesi",
                "Güncel Nakit",
                "Son Net Varlık Değeri (NAV)",
                "NAV Getiri %",
                "Gerçekleşen Kar/Zarar",
                "Açık Pozisyon Maliyet Tabanı",
                "Açık Pozisyon Değeri",
                "Gerçekleşmemiş Kar/Zarar",
                "Ödenen Komisyon",
                "Kayma Maliyeti",
                "Toplam İşlem Maliyeti",
                "Toplam İşlem",
                "Alım İşlemi",
                "Satım İşlemi",
                "Açık Lot Sayısı",
                "Değerleme Tarihi",
            ]
            summary = {"Metrik": metrics}
            for market, portfolio, currency in (
                ("BIST", portfolio_bist, "TL"),
                ("CRYPTO", portfolio_crypto, "USD"),
            ):
                stats = self._calculate_stats(portfolio)

                def money(value, currency=currency):
                    return "N/A" if value is None else f"{value:,.2f} {currency}"

                nav_return = stats["total_return_pct"]
                summary[market] = [
                    money(portfolio.initial_cash),
                    money(portfolio.cash),
                    money(stats["net_asset_value"]),
                    "N/A" if nav_return is None else f"{nav_return:.2f}%",
                    money(stats["realized_profit"]),
                    money(stats["open_cost_basis"]),
                    money(stats["position_value"]),
                    money(stats["unrealized_profit"]),
                    money(portfolio.total_commission_paid),
                    money(portfolio.total_slippage_cost),
                    money(portfolio.total_transaction_cost),
                    len(portfolio.all_trades),
                    sum(t["İşlem"] == "ALIM" for t in portfolio.all_trades),
                    sum(t["İşlem"] == "SATIM" for t in portfolio.all_trades),
                    stats["open_lots"],
                    str(stats["valuation_date"] or "N/A"),
                ]
            pd.DataFrame(summary).to_excel(writer, sheet_name="Genel Özet", index=False)
            for label, portfolio, currency in (
                ("BIST", portfolio_bist, "TL"),
                ("Crypto", portfolio_crypto, "USD"),
            ):
                if portfolio.all_trades:
                    pd.DataFrame(portfolio.all_trades).to_excel(
                        writer, sheet_name=f"{label} Tüm İşlemler", index=False
                    )
                performance = []
                for symbol, stats in portfolio.symbol_performance.items():
                    invested = stats["Toplam Yatırım"]
                    completed = stats["Tamamlanan İşlem"]
                    holding = stats["Ortalama Tutma Süresi"]
                    performance.append(
                        {
                            "Sembol": symbol,
                            f"Toplam Kar/Zarar ({currency})": round(stats["Toplam Kar/Zarar"], 2),
                            f"Toplam Yatırım ({currency})": round(invested, 2),
                            "Getiri %": round(stats["Toplam Kar/Zarar"] / invested * 100, 2)
                            if invested
                            else None,
                            "Getiri Temeli": "Gerçekleşmiş PnL / kapalı lotların maliyeti",
                            "Tamamlanan İşlem": completed,
                            "Kazanan": stats["Kazanan"],
                            "Kaybeden": stats["Kaybeden"],
                            "Başarı Oranı %": round(stats["Kazanan"] / completed * 100, 2)
                            if completed
                            else 0,
                            "Toplam Alım": stats["Toplam Alım"],
                            "Toplam Satım": stats["Toplam Satım"],
                            "Ort. Tutma Süresi (Gün)": round(float(np.mean(holding)), 1)
                            if holding
                            else 0,
                        }
                    )
                if performance:
                    pd.DataFrame(performance).sort_values(
                        f"Toplam Kar/Zarar ({currency})", ascending=False
                    ).to_excel(writer, sheet_name=f"{label} Sembol Performans", index=False)
                positions = portfolio.get_open_positions_summary()
                if positions:
                    pd.DataFrame(positions).to_excel(
                        writer, sheet_name=f"{label} Açık Pozisyonlar", index=False
                    )
                if portfolio.equity_curve:
                    pd.DataFrame(portfolio.equity_curve).to_excel(
                        writer, sheet_name=f"{label} Portföy Değeri", index=False
                    )
        print(f"💾 Excel Rapor: {filename}")
        return str(filename)

    def plot_results(self, portfolio_bist, portfolio_crypto, *, output_path=None):
        """Render portable SVG, or an optional matplotlib PNG when that suffix is requested."""
        from pathlib import Path

        from scripts.backtest_fixture import write_equity_svg

        filename = Path(output_path or f"backtest_grafik_{datetime.now():%Y%m%d_%H%M%S}.png")
        portfolios = {"BIST": portfolio_bist, "CRYPTO": portfolio_crypto}
        if filename.suffix.lower() == ".svg":
            write_equity_svg(portfolios, filename)
        else:
            try:
                import matplotlib.pyplot as plt
            except ImportError as error:
                raise RuntimeError(
                    "PNG output requires optional matplotlib; use .svg for the portable chart"
                ) from error
            figure, axes = plt.subplots(2, 1, figsize=(12, 8))
            try:
                for axis, (market, portfolio) in zip(axes, portfolios.items(), strict=True):
                    rows = portfolio.equity_curve
                    if rows:
                        axis.plot(
                            [r["Tarih"] for r in rows],
                            [r["Toplam Değer"] for r in rows],
                            label="NAV",
                        )
                    axis.axhline(portfolio.initial_cash, linestyle="--", label="Initial capital")
                    axis.set_title(f"{market} — closing NAV (not realized PnL)")
                    axis.set_ylabel("TL" if market == "BIST" else "USD")
                    axis.legend()
                    axis.grid(alpha=0.3)
                figure.tight_layout()
                figure.savefig(filename, dpi=150)
            finally:
                plt.close(figure)
        print(f"📈 Grafik: {filename}")
        return str(filename)

    def _calculate_stats(self, portfolio):
        """Separate closing NAV from realized FIFO PnL; missing marks stay unavailable."""
        realized = math.fsum(s["Toplam Kar/Zarar"] for s in portfolio.symbol_performance.values())
        completed = sum(s["Tamamlanan İşlem"] for s in portfolio.symbol_performance.values())
        winners = sum(s["Kazanan"] for s in portfolio.symbol_performance.values())
        open_lots = sum(len(queue) for queue in portfolio.lots.values())
        basis = math.fsum(lot.invested for queue in portfolio.lots.values() for lot in queue)
        nav = portfolio.cash if not open_lots else None
        valuation_date = None
        if portfolio.equity_curve:
            last = portfolio.equity_curve[-1]
            last_trade = max(
                (trade["Tarih"] for trade in portfolio.all_trades), default=last["Tarih"]
            )
            # A manual transaction after the last mark must not reuse a stale NAV.
            if (
                last["Tarih"] >= last_trade
                and last.get("Kaydedilen İşlem Sayısı") == len(portfolio.all_trades)
                and math.isclose(last["Nakit"], portfolio.cash, rel_tol=0, abs_tol=0.0051)
            ):
                nav = float(last["Toplam Değer"])
                valuation_date = last["Tarih"]
        position_value = nav - portfolio.cash if nav is not None else None
        total_profit = nav - portfolio.initial_cash if nav is not None else None
        return {
            "profit": realized,  # Legacy consumers use this explicitly realized amount.
            "realized_profit": realized,
            "net_asset_value": nav,
            "total_profit": total_profit,
            "total_return_pct": total_profit / portfolio.initial_cash * 100
            if total_profit is not None
            else None,
            "open_cost_basis": basis,
            "position_value": position_value,
            "unrealized_profit": position_value - basis if position_value is not None else None,
            "valuation_date": valuation_date,
            "return_basis": "last_closing_nav_over_initial_cash",
            "valuation_status": "available" if nav is not None else "missing_current_mark",
            "win_rate": winners / completed * 100 if completed else 0,
            "trades": completed,
            "open_lots": open_lots,
        }

    def print_summary(self, portfolio_bist, portfolio_crypto):
        """Print NAV, realized PnL and remaining cost basis without mixing their returns."""
        print("\n" + "=" * 70 + "\n📊 BACKTEST SONUÇ ÖZETİ")
        for market, portfolio, currency in (
            ("BIST", portfolio_bist, "TL"),
            ("CRYPTO", portfolio_crypto, "USD"),
        ):
            stats = self._calculate_stats(portfolio)
            print(f"\n{market}:")
            for label, value in (
                ("Başlangıç", portfolio.initial_cash),
                ("Güncel Nakit", portfolio.cash),
                ("Son Net Varlık Değeri (NAV)", stats["net_asset_value"]),
                ("Gerçekleşen Kar/Zarar", stats["realized_profit"]),
                ("Açık Pozisyon Maliyet Tabanı", stats["open_cost_basis"]),
                ("Gerçekleşmemiş Kar/Zarar", stats["unrealized_profit"]),
                ("Ödenen Komisyon", portfolio.total_commission_paid),
                ("Kayma Maliyeti", portfolio.total_slippage_cost),
                ("Toplam İşlem Maliyeti", portfolio.total_transaction_cost),
            ):
                print(f"  {label}: " + ("N/A" if value is None else f"{value:,.2f} {currency}"))
            nav_return = stats["total_return_pct"]
            print("  NAV Getiri %: " + ("N/A" if nav_return is None else f"{nav_return:.2f}%"))
            print(f"  Tamamlanan İşlem: {stats['trades']}; Açık Lot Sayısı: {stats['open_lots']}")
        print("\n" + "=" * 70)


# ============================================================
# BENCHMARK KARŞILAŞTIRMA
# ============================================================
class BenchmarkComparison:
    """Compare opening cash to closing NAV over identical observed market days.

    The benchmark buys at the first execution Open, including entry costs, and
    remains marked at the final Close. Missing endpoints never become zero return.
    """

    BENCHMARKS = {
        # XU100, İş Yatırım hisse veri kaynağında doğrudan desteklenmediği için devre dışı.
        "BIST": None,
        "CRYPTO": "BTCUSDT",  # Bitcoin
    }

    def __init__(
        self,
        start_date: str | date | None,
        end_date: str | date | None = None,
        *,
        as_of: str | datetime | None = None,
        costs: TradingCosts | None = None,
    ) -> None:
        self.bounds = BacktestEngine(start_date, end_date, as_of=as_of)
        self.start_date, self.end_date = self.bounds.start_date, self.bounds.end_date
        self.costs = costs
        self.benchmark_data: dict[str, pd.DataFrame] = {}
        self.benchmark_status: dict[str, str] = {}

    def fetch_benchmark(
        self, market_type: str, *, data: pd.DataFrame | None = None
    ) -> pd.DataFrame | None:
        """Read once or validate supplied data; discard the previous cache first."""
        if market_type not in self.BENCHMARKS:
            raise ValueError("market_type must be BIST or CRYPTO")
        self.benchmark_data.pop(market_type, None)
        self.benchmark_status[market_type] = "unavailable"
        symbol = self.BENCHMARKS.get(market_type)
        if data is None and symbol is None:
            self.benchmark_status[market_type] = "benchmark_disabled"
            return None
        if data is None:
            data = self.bounds._load_daily_data(symbol, market_type)
        if data is None:
            self.benchmark_status[market_type] = "provider_returned_none"
            return None
        frame = self.bounds._prepare_daily_data(data, market_type)
        if self.start_date is not None:
            frame = frame.loc[frame.index >= self.start_date].copy()
        if frame.empty:
            self.benchmark_status[market_type] = "no_closed_benchmark_data"
            return None
        self.benchmark_data[market_type] = frame
        self.benchmark_status[market_type] = "available"
        return frame.copy(deep=True)

    def calculate_benchmark_return(
        self, market_type: str, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> float | None:
        """Gross Open-to-Close return; absent exact endpoints are unavailable."""
        if market_type not in self.BENCHMARKS:
            raise ValueError("market_type must be BIST or CRYPTO")
        start = BacktestEngine._date_bound(start_date, "start_date")
        end = BacktestEngine._date_bound(end_date, "end_date")
        if start is None or end is None or start > end:
            raise ValueError("A valid benchmark interval is required")
        df = self.benchmark_data.get(market_type)
        if df is None or start not in df.index or end not in df.index:
            return None
        value = (float(df.at[end, "Close"]) / float(df.at[start, "Open"]) - 1) * 100
        if not math.isfinite(value):
            raise ValueError("Benchmark return overflow")
        return value

    def compare(
        self, portfolio: Portfolio, market_type: str, *, data: pd.DataFrame | None = None
    ) -> dict[str, Any]:
        """Return explicit availability and matched-period NAV and benchmark returns."""
        if market_type not in self.BENCHMARKS or portfolio.market_type != market_type:
            raise ValueError("market_type must match the BIST/CRYPTO portfolio")
        result = {
            "status": "unavailable",
            "reason": "missing_portfolio_period",
            "portfolio_return": None,
            "benchmark_return": None,
            "benchmark_gross_return": None,
            "alpha": None,
            "benchmark_symbol": (
                f"supplied:{market_type}" if data is not None else self.BENCHMARKS[market_type]
            ),
            "return_basis": "opening_cash_to_closing_nav",
            "benchmark_model": "first_open_to_last_close_entry_costs_no_liquidation",
        }
        metadata = portfolio.backtest_metadata
        start, end = metadata.get("comparison_start"), metadata.get("comparison_end")
        initial = metadata.get("comparison_initial_value")
        if start is None or end is None or initial is None or not portfolio.equity_curve:
            return result
        start = BacktestEngine._date_bound(start, "comparison_start")
        end = BacktestEngine._date_bound(end, "comparison_end")
        if start > end or not _finite_nonnegative(initial) or initial <= 0:
            raise ValueError("Invalid portfolio comparison baseline")
        last = portfolio.equity_curve[-1]
        nav = last.get("Toplam Değer")
        if last.get("Tarih") != end or not _finite_nonnegative(nav):
            raise ValueError("The final NAV must match the comparison end")
        if last.get("Kaydedilen İşlem Sayısı") != len(portfolio.all_trades) or last.get(
            "Nakit"
        ) != round(portfolio.cash, 2):
            result["reason"] = "stale_portfolio_valuation"
            return result
        value = (nav / initial - 1) * 100
        if not math.isfinite(value):
            raise ValueError("Portfolio return overflow")
        result.update(
            {
                "portfolio_return": value,
                "start_date": start,
                "end_date": end,
                "initial_value": initial,
                "final_nav": nav,
                "stale_symbols": last.get("Eski Fiyatlı Semboller", []),
            }
        )
        frame = self.fetch_benchmark(market_type, data=data)
        if frame is None:
            result["reason"] = self.benchmark_status[market_type]
            return result
        gross = self.calculate_benchmark_return(market_type, start, end)
        if gross is None:
            result["reason"] = "missing_exact_benchmark_endpoints"
            return result
        costs = self.costs if self.costs is not None else portfolio.costs
        entry_rate = costs.get_total_cost(market_type)
        ratio = float(frame.at[end, "Close"]) / float(frame.at[start, "Open"])
        net = (ratio / (1 + entry_rate) - 1) * 100
        result.update(
            {
                "status": "available",
                "reason": None,
                "benchmark_return": net,
                "benchmark_gross_return": gross,
                "benchmark_entry_cost_rate": entry_rate,
                "alpha": value - net,
            }
        )
        return result


# ============================================================
# ROLLING BUY-AND-HOLD ANALİZİ (STRATEJİ OPTİMİZASYONU DEĞİLDİR)
# ============================================================
class RollingBuyAndHoldAnalysis:
    """Independent Open-to-Close holding windows after an initial context prefix.

    The prefix is descriptive history, never training or optimization data.
    Every remaining admitted row belongs to exactly one evaluation window.
    """

    def __init__(
        self,
        n_splits: int = 5,
        history_ratio: float = 0.7,
        *,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        as_of: str | datetime | None = None,
        costs: TradingCosts | None = None,
    ) -> None:
        self.n_splits = n_splits
        self.history_ratio = history_ratio
        self._validate_partition_options()
        if costs is not None and not isinstance(costs, TradingCosts):
            raise ValueError("costs must be TradingCosts")
        self.costs = costs if costs is not None else trading_costs
        self.bounds = BacktestEngine(start_date=start_date, end_date=end_date, as_of=as_of)
        self.results: list[dict[str, Any]] = []

    def _validate_partition_options(self) -> None:
        if (
            isinstance(self.n_splits, bool)
            or not isinstance(self.n_splits, int)
            or self.n_splits < 1
        ):
            raise ValueError("n_splits must be a positive integer")
        if not _finite_nonnegative(self.history_ratio) or not 0 < self.history_ratio < 1:
            raise ValueError("history_ratio must be finite and strictly between zero and one")

    def split_data(
        self, df: pd.DataFrame, market_type: str = "BIST"
    ) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """Return expanding context and consecutive, nonoverlapping holding windows."""
        self._validate_partition_options()
        if market_type not in ("BIST", "CRYPTO"):
            raise ValueError("market_type must be BIST or CRYPTO")
        frame = self.bounds._prepare_daily_data(df, market_type)
        if self.bounds.start_date is not None:
            frame = frame.loc[frame.index >= self.bounds.start_date].copy(deep=True)
        history_rows = int(len(frame) * self.history_ratio)
        remaining = len(frame) - history_rows
        if history_rows < 1 or remaining < self.n_splits:
            raise ValueError("At least one history row and one holding row per split are required")
        size, extra = divmod(remaining, self.n_splits)
        splits = []
        offset = history_rows
        for index in range(self.n_splits):
            stop = offset + size + (index < extra)
            splits.append(
                (frame.iloc[:offset].copy(deep=True), frame.iloc[offset:stop].copy(deep=True))
            )
            offset = stop
        return splits

    def run(
        self, symbol: str, market_type: str, *, data: pd.DataFrame | None = None
    ) -> dict[str, Any]:
        """Evaluate buy-and-hold windows; failures raise and clear previous results."""
        self.results = []
        self._validate_partition_options()
        if not isinstance(symbol, str) or not symbol or symbol != symbol.strip():
            raise ValueError("symbol must be a nonempty trimmed string")
        commission, slippage = self.costs.get_components(market_type)
        if data is None:
            data = BacktestEngine._load_daily_data(symbol, market_type)
            if data is None:
                raise ValueError("Provider returned no daily data")
        splits = self.split_data(data, market_type)
        rate = commission + slippage
        window_results = []
        for index, (context, window) in enumerate(splits):
            entry_open = float(window["Open"].iloc[0])
            exit_close = float(window["Close"].iloc[-1])
            price_ratio = exit_close / entry_open
            entry_notional = 1.0 / (1.0 + rate)
            exit_notional = price_ratio * entry_notional
            total_commission = (entry_notional + exit_notional) * commission
            total_slippage = (entry_notional + exit_notional) * slippage
            final_value = exit_notional * (1.0 - rate)
            gross_return = (price_ratio - 1.0) * 100.0
            net_return = (final_value - 1.0) * 100.0
            if not all(
                math.isfinite(value)
                for value in (
                    total_commission,
                    total_slippage,
                    final_value,
                    gross_return,
                    net_return,
                )
            ):
                raise ValueError("Window return or cost overflow")
            window_results.append(
                {
                    "window": index + 1,
                    "history_start": context.index[0],
                    "history_end": context.index[-1],
                    "history_rows": len(context),
                    "test_start": window.index[0],
                    "test_end": window.index[-1],
                    "test_rows": len(window),
                    "entry_open": entry_open,
                    "exit_close": exit_close,
                    "gross_return": gross_return,
                    "net_return": net_return,
                    "test_return": net_return,
                    "final_value": final_value,
                    "commission_paid": total_commission,
                    "slippage_cost": total_slippage,
                }
            )
        returns = [window["net_return"] for window in window_results]
        average = math.fsum(value / len(returns) for value in returns)
        # Scale before squaring so a finite return distribution does not overflow.
        scale = max(abs(value) for value in returns)
        std = float(np.std([value / scale for value in returns])) * scale if scale else 0.0
        self.results = [dict(window) for window in window_results]
        return {
            "symbol": symbol,
            "market_type": market_type,
            "model": "rolling_buy_and_hold",
            "strategy": "buy_and_hold",
            "strategy_evaluated": False,
            "optimization_performed": False,
            "history_usage": "context_only_no_training",
            "history_ratio": self.history_ratio,
            "as_of": self.bounds.as_of,
            "start_date": self.bounds.start_date,
            "end_date": self.bounds.end_date,
            "execution_model": "first_open_to_last_close",
            "cost_model": "round_trip_additive_reference_notional",
            "cost_rates": {"commission": commission, "slippage": slippage},
            "initial_capital_per_window": 1.0,
            "aggregation": "arithmetic_statistics_of_independent_window_returns",
            "n_windows": len(window_results),
            "avg_return": average,
            "std_return": std,
            "min_return": min(returns),
            "max_return": max(returns),
            "windows": window_results,
        }


class WalkForwardAnalysis(RollingBuyAndHoldAnalysis):
    """Legacy compatibility name; no strategy training or walk-forward optimization."""

    def __init__(self, n_splits: int = 5, train_ratio: float = 0.7, **kwargs: Any) -> None:
        warnings.warn(
            "WalkForwardAnalysis is a legacy name for rolling buy-and-hold window analysis; "
            "no strategy is trained or optimized. Use RollingBuyAndHoldAnalysis.",
            FutureWarning,
            stacklevel=2,
        )
        super().__init__(n_splits=n_splits, history_ratio=train_ratio, **kwargs)

    @property
    def train_ratio(self) -> float:
        """Legacy spelling of the context-only history ratio."""
        return self.history_ratio

    @train_ratio.setter
    def train_ratio(self, value: float) -> None:
        self.history_ratio = value

    def run_walk_forward(
        self,
        symbol: str,
        market_type: str,
        strategy: str = "combo",
        *,
        data: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        """Preserve old calls while explicitly reporting the ignored strategy argument."""
        self.results = []
        message = "run_walk_forward evaluates buy-and-hold windows; strategy is ignored."
        warnings.warn(message, FutureWarning, stacklevel=2)
        result = self.run(symbol, market_type, data=data)
        result.update(
            {"legacy_api": "run_walk_forward", "ignored_strategy": strategy, "warning": message}
        )
        for window in result["windows"]:
            window["train_start"] = window["history_start"]
            window["train_end"] = window["history_end"]
        self.results = [dict(window) for window in result["windows"]]
        return result


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


def main(argv: list[str] | None = None) -> int:
    """Run the provider CLI, or explicitly selected deterministic fixture, and export reports."""
    import argparse
    import hashlib
    import platform
    from pathlib import Path

    from scripts.backtest_fixture import (
        FIXTURE_AS_OF,
        FIXTURE_END,
        FIXTURE_ID,
        FIXTURE_START,
        daily_frames,
        write_reports,
    )

    parser = argparse.ArgumentParser(description="Daily shared-cash backtest with NAV reports")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use synthetic OHLCV; prefer python -m scripts.backtest_fixture for settings isolation",
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--as-of", help="Timezone-aware daily closure cutoff")
    parser.add_argument("--excel", action="store_true", help="Also produce optional openpyxl XLSX")
    args = parser.parse_args(argv)
    if args.fixture and args.output_dir is None:
        parser.error("--fixture requires --output-dir; use python -m scripts.backtest_fixture")
    output = (args.output_dir or Path(f"backtest_output_{datetime.now():%Y%m%d_%H%M%S}")).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error("--output-dir must be absent or empty; reports are never overwritten")
    as_of = args.as_of or (FIXTURE_AS_OF if args.fixture else None)
    engine = BacktestEngine(
        start_date=FIXTURE_START if args.fixture else "2006-01-01",
        end_date=FIXTURE_END if args.fixture else None,
        as_of=as_of,
    )
    frames = daily_frames() if args.fixture else None
    portfolios = {}
    for market, symbols, cash, budget in (
        ("BIST", ["BSOKE"], 100000.0, 1000.0),
        ("CRYPTO", ["BTCUSDT"], 20000.0, 100.0),
    ):
        feeds = frames[market] if frames is not None else None
        portfolios[market] = engine.run_backtest(
            list(feeds) if feeds is not None else symbols,
            market,
            cash,
            budget,
            data_by_symbol=feeds,
        )
    engine.print_summary(portfolios["BIST"], portfolios["CRYPTO"])
    benchmark = BenchmarkComparison(engine.start_date, engine.end_date, as_of=engine.as_of)
    comparisons = {}
    windows = {}
    for market, portfolio in portfolios.items():
        feed = next(iter(frames[market].values())) if frames is not None else None
        comparisons[market] = benchmark.compare(portfolio, market, data=feed)
        if feed is not None:
            windows[market] = RollingBuyAndHoldAnalysis(
                n_splits=3, history_ratio=0.7, as_of=engine.as_of, end_date=engine.end_date
            ).run(next(iter(frames[market])), market, data=feed)
    metadata = {
        "mode": "synthetic_fixture" if args.fixture else "provider",
        "fixture_id": FIXTURE_ID if args.fixture else None,
        "signal_calculators": "real COMBO/HUNTER, default parameters and developing HTF",
        "python_version": platform.python_version(),
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "start_date": engine.start_date,
        "end_date": engine.end_date,
        "benchmark": comparisons,
        "rolling_buy_and_hold": windows,
        "walk_forward_optimization_performed": False,
        "artifacts": {"chart": "equity.svg", "excel": "report.xlsx" if args.excel else None},
        "input_sha256": {
            f"{market}/{symbol}": hashlib.sha256(
                frame.to_csv(lineterminator="\n").encode("utf-8")
            ).hexdigest()
            for market, feeds in (frames or {}).items()
            for symbol, frame in feeds.items()
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    engine.plot_results(portfolios["BIST"], portfolios["CRYPTO"], output_path=output / "equity.svg")
    if args.excel:
        engine.generate_excel_report(
            portfolios["BIST"], portfolios["CRYPTO"], output_path=output / "report.xlsx"
        )
    report = write_reports(engine, portfolios, output, metadata)
    print(f"Report: {report}")
    print(
        "Fixture acceptance is not provider, exchange, TradingView or strategy-profit acceptance."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
