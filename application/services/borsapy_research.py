"""Bounded research adapter. No arbitrary attributes, strategies, code or URLs.

The API gateway owns provider initialization, server-side credentials and its
global lock. This module neither imports borsapy nor reads credentials. Its
validation is pure and can run before acquiring the gateway or using the network.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from itertools import islice
from numbers import Real
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from application.services.borsapy_catalog import OPERATIONS

_OPERATIONS = {entry["id"]: entry for entry in OPERATIONS}
MAX_ROWS = 2000
MAX_COLUMNS = 64
MAX_TABLES = 20
MAX_CANDLES = 1500
MAX_CELLS = 20000
MAX_TEXT = 200000
_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9._:-]{0,29}\Z")
_ASSET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,39}\Z")
_SENSITIVE = re.compile(r"password|secret|token|cookie|authorization|sessionid|api_key", re.I)


class ResearchInputError(ValueError):
    """Safe, local validation failure; its message contains no upstream response."""


def _symbol(value: Any, label: str = "Sembol") -> str:
    if not isinstance(value, str) or not _SYMBOL.fullmatch(value.strip().upper()):
        raise ResearchInputError(f"{label}: geçerli bir sembol girin.")
    return value.strip().upper()


def _symbols(value: str | list, maximum: int, label: str, *, evds: bool = False) -> list[str]:
    parts = value.split(",") if isinstance(value, str) else value
    if not isinstance(parts, list) or not 1 <= len(parts) <= maximum:
        raise ResearchInputError(f"{label}: 1–{maximum} değer girin.")
    if evds:
        if any(
            not isinstance(part, str)
            or not re.fullmatch(r"TP\.[A-Z0-9_.]{1,77}", part.strip().upper())
            for part in parts
        ):
            raise ResearchInputError(
                "Geçerli bir EVDS seri kodu girin (TP. ile başlayan en fazla 80 karakter)."
            )
        parsed = [part.strip().upper() for part in parts]
    else:
        parsed = [_symbol(part, label) for part in parts]
    if len(set(parsed)) != len(parsed):
        raise ResearchInputError(f"{label}: aynı değeri iki kez eklemeyin.")
    return parsed


def _finite_number(value: Any, minimum: float, maximum: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ResearchInputError(f"{label}: sayı girin.")
    if not minimum <= value <= maximum or not math.isfinite(value):
        raise ResearchInputError(f"{label}: {minimum:g}–{maximum:g} arasında olmalı.")
    return value


def _positions(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        if len(value) > 20000:
            raise ResearchInputError("Portföy girdisi çok uzun.")
        try:
            value = json.loads(value)
        except (ValueError, RecursionError) as error:
            raise ResearchInputError("Pozisyonlar geçerli bir JSON listesi olmalı.") from error
    if not isinstance(value, list) or not 1 <= len(value) <= 10:
        raise ResearchInputError("Portföy 1–10 pozisyon içermeli.")
    result = []
    seen = set()
    for position in value:
        if not isinstance(position, dict) or set(position) != {
            "symbol",
            "shares",
            "cost",
            "asset_type",
        }:
            raise ResearchInputError("Her pozisyonda symbol, shares, cost ve asset_type gerekli.")
        asset_type = position["asset_type"]
        if asset_type not in ("stock", "fund", "fx", "crypto"):
            raise ResearchInputError("Varlık türü stock, fund, fx veya crypto olmalı.")
        symbol = position["symbol"]
        if asset_type == "fx":
            if not isinstance(symbol, str) or not _ASSET.fullmatch(symbol.strip()):
                raise ResearchInputError("Geçerli bir döviz/maden varlığı girin.")
            symbol = symbol.strip()
        else:
            symbol = _symbol(symbol)
        # borsapy keys its holdings by symbol, not (symbol, asset_type).
        if symbol.upper() in seen:
            raise ResearchInputError("Portföyde aynı sembolü iki kez eklemeyin.")
        seen.add(symbol.upper())
        result.append(
            {
                "symbol": symbol,
                "shares": _finite_number(position["shares"], 0.00000001, 100000000, "Miktar"),
                "cost": _finite_number(position["cost"], 0, 100000000, "Birim maliyet"),
                "asset_type": asset_type,
            }
        )
    return result


def validate_params(operation: str, params: dict[str, Any]) -> dict[str, Any]:
    """Validate a catalog operation without importing or calling any provider."""
    if not isinstance(operation, str) or operation not in _OPERATIONS:
        raise ResearchInputError("Bu araştırma işlemi desteklenmiyor.")
    if not isinstance(params, dict):
        raise ResearchInputError("İşlem parametreleri bir nesne olmalı.")
    fields = _OPERATIONS[operation]["fields"]
    if set(params) - {field["name"] for field in fields}:
        raise ResearchInputError("Bu işlem için tanımsız parametre gönderildi.")
    parsed: dict[str, Any] = {}
    for field in fields:
        name, label = field["name"], field["label"]
        value = params.get(name, field.get("default"))
        if name == "positions":
            parsed[name] = _positions(value)
            continue
        if field["type"] == "number":
            value = _finite_number(value, field["min"], field["max"], label)
            if name in {"limit", "length", "last_n", "category_id", "holding_days"}:
                if value != int(value):
                    raise ResearchInputError(f"{label}: tam sayı girin.")
                value = int(value)
        elif field["type"] == "select":
            if not isinstance(value, str) or value not in {
                option["value"] for option in field["options"]
            }:
                raise ResearchInputError(f"{label}: listedeki seçeneklerden birini seçin.")
        elif name in {"symbols", "fund_codes", "codes"}:
            maximum = {"symbols": 20, "fund_codes": 10, "codes": 5}[name]
            if isinstance(value, str) and len(value) > 600:
                raise ResearchInputError(f"{label}: girdi çok uzun.")
            value = _symbols(value, maximum, label, evds=name == "codes")
            if name == "codes" and any(not re.fullmatch(r"TP\.[A-Z0-9_.]+", c) for c in value):
                raise ResearchInputError("EVDS seri kodları TP. ile başlamalı.")
        else:
            if not isinstance(value, str) or len(value) > 240:
                raise ResearchInputError(f"{label}: en fazla 240 karakter girin.")
            value = value.strip()
            if (field.get("required") and not value) or any(ord(c) < 32 for c in value):
                raise ResearchInputError(f"{label}: geçerli bir değer girin.")
            if name in {"symbol", "fund_code", "pair", "base_symbol"}:
                value = _symbol(value, label)
            if name == "asset" and not _ASSET.fullmatch(value):
                raise ResearchInputError("Geçerli bir döviz/maden varlığı girin.")
            if name == "isin" and not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", value.upper()):
                raise ResearchInputError("Geçerli bir 12 karakterli ISIN girin.")
            if field["type"] == "date":
                try:
                    parsed_date = date.fromisoformat(value)
                except ValueError as error:
                    raise ResearchInputError(f"{label}: YYYY-MM-DD biçimini kullanın.") from error
                if len(value) != 10 or parsed_date > datetime.now(UTC).date():
                    raise ResearchInputError(f"{label}: geçerli bir geçmiş tarih girin.")
        parsed[name] = value

    if operation == "inflation.calculate":
        for name in ("start", "end"):
            if not re.fullmatch(r"(?:19|20)\d{2}-(?:0[1-9]|1[0-2])", parsed[name]):
                raise ResearchInputError("Ayları YYYY-MM biçiminde girin.")
        if parsed["start"] > parsed["end"] or parsed["end"] > datetime.now(UTC).strftime("%Y-%m"):
            raise ResearchInputError("Başlangıç bitişten sonra, bitiş gelecek ay olamaz.")
    # Bound expensive intraday requests, irrespective of provider-side caps.
    days = {"1d": 1, "5d": 5, "1mo": 31, "3mo": 93, "6mo": 186, "1y": 366, "2y": 732}
    maximum_days = {"1m": 5, "5m": 31, "15m": 93, "30m": 186, "1h": 186, "4h": 186}
    if (
        parsed.get("interval") in maximum_days
        and "period" in parsed
        and days[parsed["period"]] > maximum_days[parsed["interval"]]
    ):
        raise ResearchInputError(
            "Seçilen mum periyodu için daha kısa bir geçmiş aralığı seçin (1m: 5d, 5m: 1mo, 15m: 3mo, 30m/1h/4h: 6mo)."
        )
    return parsed


def _scalar(value: Any, depth: int = 0, budget: dict[str, int] | None = None) -> Any:
    if budget is not None:
        if budget["nodes"] <= 0 or budget["text"] <= 0:
            budget["exhausted"] = 1
            return None
        budget["nodes"] -= 1
    if depth > 6:
        return None
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, Real):
        return (
            (int(value) if isinstance(value, (int, np.integer)) else float(value))
            if math.isfinite(value)
            else None
        )
    if isinstance(value, str):
        length = min(1000, budget["text"] if budget is not None else 1000)
        if budget is not None:
            budget["text"] -= min(len(value), length)
            if len(value) > length:
                budget["exhausted"] = 1
        return value[:length]
    if isinstance(value, Mapping):
        return {
            str(key)[:120]: _scalar(item, depth + 1, budget)
            for key, item in islice(value.items(), 20)
            if not _SENSITIVE.search(str(key))
        }
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_scalar(item, depth + 1, budget) for item in value[:20]]
    if isinstance(value, (pd.Timedelta,)):
        return str(value)
    # Never call __repr__, generic getattr, or arbitrary serialization hooks.
    return None


def normalize_result(
    operation: str,
    raw: Any,
    *,
    warnings: list[str] | None = None,
    candles: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Convert known provider output shapes to finite, bounded JSON-safe data."""
    entry = _OPERATIONS[operation]
    result: dict[str, Any] = {
        "operation": operation,
        "source": entry["source"],
        "as_of": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "tables": [],
        "summary": {},
        "warnings": list(warnings or []),
    }

    budget = {"cells": MAX_CELLS, "nodes": MAX_CELLS * 2, "text": MAX_TEXT, "exhausted": 0}

    def table(name: str, frame: pd.DataFrame) -> dict | None:
        if len(result["tables"]) >= MAX_TABLES or budget["cells"] <= 0:
            result["warnings"].append("Ek tablolar sonuç boyutu sınırı nedeniyle gösterilmedi.")
            return
        total_rows = len(frame)
        # Preserve financial row labels and time indexes without reset_index collisions.
        keep_index = not isinstance(frame.index, pd.RangeIndex) or frame.index.name is not None
        columns = ([str(frame.index.name or "index")] if keep_index else []) + [
            str(column) for column in frame.columns
        ]
        selected = []
        used: set[str] = set()
        indices = []
        for index, column in enumerate(columns):
            if _SENSITIVE.search(column):
                continue
            candidate = column[:120]
            suffix = 2
            while candidate in used:
                candidate = f"{column[:110]}_{suffix}"
                suffix += 1
            used.add(candidate)
            selected.append(candidate)
            indices.append(index)
            if len(selected) == MAX_COLUMNS:
                break
        rows = []
        row_limit = min(MAX_ROWS, budget["cells"] // max(1, len(selected)))
        for index, row in frame.head(row_limit).iterrows():
            values = ([index] if keep_index else []) + list(row)
            rows.append(
                {
                    column: _scalar(values[i], budget=budget)
                    for column, i in zip(selected, indices, strict=True)
                }
            )
        budget["cells"] -= len(rows) * max(1, len(selected))
        truncated = total_rows > row_limit or len(columns) > MAX_COLUMNS
        result["tables"].append(
            {
                "name": name,
                "columns": selected,
                "rows": rows,
                "total_rows": total_rows,
                "truncated": truncated,
            }
        )
        if truncated:
            result["warnings"].append(
                f"{name}: tablo en fazla {MAX_ROWS} satır / {MAX_COLUMNS} sütun gösterir."
            )

        return result["tables"][-1]

    def visit(name: str, value: Any, depth: int = 0) -> None:
        if budget["nodes"] <= 0 or len(result["summary"]) >= 2000:
            budget["exhausted"] = 1
            return
        budget["nodes"] -= 1
        if depth > 5 or _SENSITIVE.search(name):
            return
        if isinstance(value, pd.DataFrame):
            table(name, value)
        elif isinstance(value, pd.Series):
            table(name, value.to_frame(name=value.name or "value"))
        elif isinstance(value, Mapping):
            for key, item in islice(value.items(), 100):
                if budget["nodes"] <= 0 or len(result["summary"]) >= 2000:
                    budget["exhausted"] = 1
                    break
                key = str(key)[:120]
                visit(key if name == "result" else f"{name}.{key}", item, depth + 1)
        elif isinstance(value, (list, tuple)):
            if value and all(isinstance(row, Mapping) for row in value):
                # Retain total_rows even when provider supplied a large list.
                limited = [
                    {str(key): item for key, item in list(row.items())[:MAX_COLUMNS]}
                    for row in value[:MAX_ROWS]
                ]
                output = table(name, pd.DataFrame(limited))
                if output is None:
                    return
                output["total_rows"] = len(value)
                if len(value) > len(output["rows"]):
                    output["truncated"] = True
                    result["warnings"].append(f"{name}: yalnız ilk {MAX_ROWS} kayıt gösterilir.")
            elif value and all(isinstance(row, (str, int, float)) for row in value):
                output = table(name, pd.DataFrame({"value": value[:MAX_ROWS]}))
                if output is None:
                    return
                output["total_rows"] = len(value)
                output["truncated"] = len(value) > len(output["rows"])
            else:
                result["summary"][name] = _scalar(value, budget=budget)
        else:
            result["summary"][name] = _scalar(value, budget=budget)

    visit("result", raw)
    if candles is not None:
        result["candles"] = _candles(candles)
        if len(candles) > MAX_CANDLES:
            result["warnings"].append(f"Grafikte son {MAX_CANDLES} mum gösterilir.")
    if budget["exhausted"]:
        result["warnings"].append(
            "Sonuç boyutu sınırı nedeniyle bazı uzun veya iç içe değerler kısaltıldı."
        )
    result["warnings"] = list(dict.fromkeys(result["warnings"]))
    return result


def _candles(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty or not all(column in frame for column in ("Open", "High", "Low", "Close")):
        return []
    result = {}
    for index, row in frame.tail(MAX_CANDLES).iterrows():
        if not isinstance(index, (pd.Timestamp, datetime, date)) or pd.isna(index):
            continue
        timestamp = pd.Timestamp(index)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(ZoneInfo("Europe/Istanbul"))
        values = {
            key: _scalar(row[column])
            for key, column in (
                ("open", "Open"),
                ("high", "High"),
                ("low", "Low"),
                ("close", "Close"),
            )
        }
        if any(not isinstance(value, (int, float)) for value in values.values()):
            continue
        time = int(timestamp.timestamp())
        result[time] = {"time": time, **values, "volume": _scalar(row.get("Volume"))}
    return [result[key] for key in sorted(result)]


def _indicator(bp: Any, frame: pd.DataFrame, name: str, length: int) -> Any:
    # Bound method references are explicit; client text never becomes an attribute path.
    calculators = {
        "rsi": lambda: bp.calculate_rsi(frame, period=length),
        "sma": lambda: bp.calculate_sma(frame, period=length),
        "ema": lambda: bp.calculate_ema(frame, period=length),
        "macd": lambda: bp.calculate_macd(frame),
        "bollinger": lambda: bp.calculate_bollinger_bands(frame, period=length),
        "atr": lambda: bp.calculate_atr(frame, period=length),
        "stochastic": lambda: bp.calculate_stochastic(frame, k_period=length),
        "obv": lambda: bp.calculate_obv(frame),
        "vwap": lambda: bp.calculate_vwap(frame),
        "adx": lambda: bp.calculate_adx(frame, period=length),
        "supertrend": lambda: bp.calculate_supertrend(frame, atr_period=length),
        "tilson_t3": lambda: bp.calculate_tilson_t3(frame, period=length),
        "hhv": lambda: bp.calculate_hhv(frame, period=length),
        "llv": lambda: bp.calculate_llv(frame, period=length),
        "mom": lambda: bp.calculate_mom(frame, period=length),
        "roc": lambda: bp.calculate_roc(frame, period=length),
        "wma": lambda: bp.calculate_wma(frame, period=length),
        "dema": lambda: bp.calculate_dema(frame, period=length),
        "tema": lambda: bp.calculate_tema(frame, period=length),
    }
    value = calculators[name]()
    if isinstance(value, tuple):
        return {f"component_{index + 1}": item for index, item in enumerate(value)}
    return value


def _sma_strategy() -> Any:
    previous: float | None = None

    def sma_20_50_cross(candle: dict, position: str | None, indicators: dict) -> str:
        nonlocal previous
        fast, slow = indicators.get("sma_20"), indicators.get("sma_50")
        if any(not isinstance(value, Real) or not math.isfinite(value) for value in (fast, slow)):
            return "HOLD"
        difference = fast - slow
        before, previous = previous, difference
        if before is None:
            return "HOLD"
        if position is None and before <= 0 < difference:
            return "BUY"
        if position == "long" and before >= 0 > difference:
            return "SELL"
        return "HOLD"

    return sma_20_50_cross


def run_operation(bp_module: Any, operation: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute exactly one allowlisted read-only operation with bounded inputs."""
    p = validate_params(operation, params)
    if _OPERATIONS[operation]["transport"] != "query":
        raise ResearchInputError("Bu işlem canlı akış panelinden başlatılır.")
    bp = bp_module
    warnings = [
        "Veri zamanı ve gecikmesi sağlayıcıya bağlıdır. Güncelleme saati sorgu saatidir; fiyat zamanı değildir."
    ]
    candles = None
    if operation == "search":
        searches = {
            "all": bp.search,
            "bist": bp.search_bist,
            "crypto": bp.search_crypto,
            "forex": bp.search_forex,
            "index": bp.search_index,
            "viop": bp.search_viop,
        }
        raw = searches[p["kind"]](p["query"], limit=p["limit"])
    elif operation == "company.list":
        raw = bp.search_companies(p["query"]) if p["query"] else bp.companies()
    elif operation in {"history", "replay", "heikin_ashi", "ta.indicators"}:
        frame = bp.Ticker(p["symbol"]).history(
            period=p["period"], interval=p["interval"], adjust=True, auto_adjust=False
        )
        raw = {"ohlcv": frame}
        candles = frame
        warnings.append(
            "Fiyatlar sağlayıcının düzeltilmiş serisidir; temettü dahil toplam getiri serisi olarak yorumlamayın."
        )
        if operation == "heikin_ashi":
            transformed = bp.calculate_heikin_ashi(frame)
            raw = {"heikin_ashi": transformed}
            candles = transformed.rename(
                columns={"HA_Open": "Open", "HA_High": "High", "HA_Low": "Low", "HA_Close": "Close"}
            )
            warnings.append("Heikin Ashi mumları sentetiktir; gerçek işlem fiyatı değildir.")
        elif operation == "ta.indicators":
            raw["indicator"] = _indicator(bp, frame, p["indicator"], p["length"])
            warnings.append(
                "MACD 12/26/9; OBV ve VWAP birikimli hesaplanır. Bu üçünde uzunluk alanı uygulanmaz."
            )
        elif operation == "replay":
            warnings.append(
                "Tekrar görünümü geçmiş veri üzerinde ilerler; gelecek veriyi gizlemek tek başına tarafsız backtest değildir."
            )
    elif operation == "company.info":
        raw = bp.Ticker(p["symbol"]).info.todict()
    elif operation == "company.financials":
        ticker = bp.Ticker(p["symbol"])
        methods = {
            "balance_sheet": ticker.get_balance_sheet,
            "income_stmt": ticker.get_income_stmt,
            "cashflow": ticker.get_cashflow,
        }
        raw = methods[p["statement"]](quarterly=p["frequency"] == "quarterly", last_n=p["last_n"])
        warnings.append(
            "Çeyrek etiketli mali tablolar birikimli dönem içerebilir; burada TTM veya çeyrek farkı hesaplanmaz."
        )
    elif operation == "company.actions":
        ticker = bp.Ticker(p["symbol"])
        raw = {"dividends": ticker.dividends, "splits": ticker.splits, "actions": ticker.actions}
        warnings.append(
            "Splits alanı bedelsiz sermaye artışı yüzdesidir; 2:1 gibi fiyat düzeltme katsayısı değildir. Hak kullanımı kapsamını kaynak bildirimiyle doğrulayın."
        )
    elif operation == "company.holders":
        ticker = bp.Ticker(p["symbol"])
        raw = {
            "major_holders": ticker.major_holders,
            "recommendations": ticker.recommendations,
            "price_targets": ticker.analyst_price_targets,
        }
    elif operation == "etf_holders":
        raw = bp.Ticker(p["symbol"]).etf_holders
    elif operation == "kap.news":
        raw = bp.Ticker(p["symbol"]).news
        warnings.append(
            "Kaynak son bildirimlerin sınırlı bir bölümünü sunar; eksiksiz KAP arşivi değildir."
        )
    elif operation == "kap.calendar":
        ticker = bp.Ticker(p["symbol"])
        raw = {"calendar": ticker.calendar, "earnings_dates": ticker.earnings_dates}
    elif operation == "ta.signals":
        raw = bp.Ticker(p["symbol"]).ta_signals(
            interval="1W" if p["interval"] == "1wk" else p["interval"]
        )
    elif operation == "screener.fundamental":
        raw = bp.screen_stocks(template=p["template"])
    elif operation == "screener.criteria":
        raw = {
            "criteria": bp.screener_criteria(),
            "sectors": bp.sectors(),
            "indices": bp.stock_indices(),
        }
    elif operation == "screener.technical":
        conditions = {
            "rsi_below_30": "rsi < 30",
            "rsi_above_70": "rsi > 70",
            "close_above_sma50": "close > sma_50",
            "sma20_crosses_sma50": "sma_20 crosses_above sma_50",
            "macd_above_signal": "macd > signal",
        }
        raw = bp.scan(
            p["symbols"],
            conditions[p["condition"]],
            interval="1W" if p["interval"] == "1wk" else p["interval"],
            limit=20,
        )
    elif operation == "portfolio":
        portfolio = bp.Portfolio(benchmark="XU100")
        for position in p["positions"]:
            portfolio.add(**position)
        # Derive totals from one holdings snapshot, not repeated quote queries.
        holdings = portfolio.holdings
        raw = {
            "holdings": holdings,
            "history": portfolio.history(period=p["period"]),
            "input": portfolio.to_dict(),
            "risk_metrics": portfolio.risk_metrics(
                period=p["period"], risk_free_rate=p["risk_free_rate"]
            ),
        }
        if isinstance(holdings, pd.DataFrame) and "value" in holdings and "pnl" in holdings:
            raw["value"] = holdings["value"].sum(min_count=1)
            raw["pnl"] = holdings["pnl"].sum(min_count=1)
        warnings.append(
            "Bu geçici hesaplama emir göndermez. Eksik veya farklı zamanlı fiyatlar portföy sonucunu etkiler."
        )
    elif operation == "backtest":
        result = bp.backtest(
            p["symbol"],
            _sma_strategy(),
            period=p["period"],
            interval="1d",
            capital=p["capital"],
            commission=p["commission"],
            indicators=["sma_20", "sma_50"],
        )
        raw = {
            "metrics": result.to_dict(),
            "trades": result.trades_df,
            "equity": result.equity_curve,
            "drawdown": result.drawdown_curve,
            "buy_hold": result.buy_hold_curve,
        }
        warnings.append(
            "DENEYSEL: borsapy sinyal ve işlemi aynı mum kapanışında uygular; kayma modeli uygulanmaz. Rapot'un sonraki açılışta işlem yapan yerel motorundan ayrıdır; gerçek performans kanıtı değildir."
        )
    elif operation == "fx.current":
        raw = bp.FX(p["asset"]).current
    elif operation == "fx.history":
        raw = bp.FX(p["asset"]).history(period=p["period"], interval=p["interval"])
        candles = raw
    elif operation == "fx.banks":
        asset = bp.FX(p["asset"])
        raw = {"bank_rates": asset.bank_rates}
        if p["asset"] in {"gram-altin", "gram-gumus", "ons-altin", "gram-platin"}:
            raw["institution_rates"] = asset.institution_rates
    elif operation == "crypto.pairs":
        raw = bp.crypto_pairs(quote=p["quote"])
    elif operation == "crypto.current":
        raw = bp.Crypto(p["pair"]).current
    elif operation == "crypto.history":
        raw = bp.Crypto(p["pair"]).history(period=p["period"], interval=p["interval"])
        candles = raw
    elif operation == "fund.search":
        raw = bp.search_funds(p["query"], limit=p["limit"])
    elif operation == "fund.info":
        fund = bp.Fund(p["fund_code"])
        raw = {
            "info": fund.info,
            "detail": fund.detail,
            "performance": fund.performance,
            "management_fee": fund.management_fee,
        }
    elif operation == "fund.history":
        raw = bp.Fund(p["fund_code"]).history(period=p["period"])
    elif operation == "fund.allocation":
        fund = bp.Fund(p["fund_code"])
        raw = {"current": fund.allocation, "history": fund.allocation_history(period=p["period"])}
        warnings.append(
            "Dağılım varlık sınıfı yüzdeleridir; fonun tuttuğu her hisseyi veya miktarını göstermez."
        )
    elif operation == "fund.screen":
        raw = bp.screen_funds(
            fund_type=p["fund_type"], min_return_1y=p["min_return_1y"], limit=p["limit"]
        )
    elif operation == "fund.compare":
        raw = bp.compare_funds(p["fund_codes"])
    elif operation == "fund.fees":
        raw = bp.management_fees(fund_type=p["fund_type"])
    elif operation == "fund.tax":
        raw = {
            "rate": bp.withholding_tax_rate(
                p["fund_code"], purchase_date=p["purchase_date"], holding_days=p["holding_days"]
            ),
            "reference": bp.withholding_tax_table(),
        }
        warnings.append(
            "Vergi oranı borsapy'deki sabit tarihli tablodan gelir; mevzuatın güncelliği doğrulanmaz. İşlem öncesi güncel resmi düzenlemeyi kontrol edin."
        )
    elif operation == "inflation":
        inflation = bp.Inflation()
        raw = (
            inflation.tufe(limit=p["limit"])
            if p["kind"] == "tufe"
            else inflation.ufe(limit=p["limit"])
        )
    elif operation == "inflation.calculate":
        raw = bp.Inflation().calculate(p["amount"], start=p["start"], end=p["end"])
    elif operation == "evds.categories":
        raw = bp.evds_categories()
    elif operation == "evds.groups":
        raw = bp.EVDS().datagroups(category_id=p["category_id"])
    elif operation == "evds.search":
        raw = bp.evds_search(p["query"], lang="tr", scope="all")
    elif operation == "evds.series":
        raw = bp.evds_download(p["codes"], period=p["period"], frequency=p["frequency"])
    elif operation == "bonds":
        raw = bp.bonds()
    elif operation == "tcmb.rates":
        raw = bp.TCMB().rates
    elif operation == "tcmb.history":
        raw = bp.TCMB().history(rate_type=p["rate_type"], period=p["period"])
    elif operation == "eurobonds":
        raw = bp.eurobonds(currency=p["currency"])
    elif operation == "eurobond.history":
        raw = bp.Eurobond(p["isin"]).history(period=p["period"])
    elif operation == "viop":
        viop = bp.VIOP()
        # Lambdas avoid requesting all categories while selecting one.
        categories = {
            "futures": lambda: viop.futures,
            "stock_futures": lambda: viop.stock_futures,
            "index_futures": lambda: viop.index_futures,
            "currency_futures": lambda: viop.currency_futures,
            "commodity_futures": lambda: viop.commodity_futures,
            "options": lambda: viop.options,
            "stock_options": lambda: viop.stock_options,
            "index_options": lambda: viop.index_options,
        }
        raw = categories[p["kind"]]()
    elif operation == "viop.contracts":
        raw = bp.viop_contracts(p["base_symbol"])
    elif operation == "calendar":
        raw = bp.economic_calendar(
            period=p["period"],
            country=["TR", "US", "EU", "DE", "GB", "JP", "CN"]
            if p["country"] == "all"
            else p["country"],
            importance=None if p["importance"] == "all" else p["importance"],
        )
        warnings.append(
            "İstenen tarih aralığı kaynağın yayımladığı olaylarla sınırlıdır; boş sonuç o gün kesinlikle olay olmadığı anlamına gelmez. Olay saatini kaynakta teyit edin."
        )
    elif operation == "twitter.search":
        raw = bp.search_tweets(p["query"], period=p["period"], limit=p["limit"], lang="tr")
    else:
        raise ResearchInputError("Bu araştırma işlemi desteklenmiyor.")
    return normalize_result(operation, raw, warnings=warnings, candles=candles)
