"""
AI analysis evaluation and reporting helpers.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Any

import pandas as pd

from data_loader import get_bist_data, get_crypto_data
from db_session import get_session
from logger import get_logger
from models import AIAnalysis, Signal

logger = get_logger(__name__)

DEFAULT_EVAL_HORIZONS: tuple[int, ...] = (3, 7, 14)
DEFAULT_PRIMARY_HORIZON_DAYS = 7
CONFIDENCE_BUCKETS: tuple[tuple[int, int, str], ...] = (
    (0, 39, "0-39"),
    (40, 59, "40-59"),
    (60, 79, "60-79"),
    (80, 100, "80-100"),
)

PriceLoader = Callable[[str, str], pd.DataFrame | None]


@dataclass(slots=True)
class AIAnalysisRecord:
    id: int
    symbol: str
    market_type: str
    created_at: datetime
    scenario_name: str | None
    signal_type: str | None
    sentiment_label: str | None
    confidence_score: int | None
    risk_level: str | None
    prompt_version: str | None
    special_tag: str | None
    technical_data: dict[str, Any]


@dataclass(slots=True)
class HorizonOutcome:
    horizon_days: int
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    raw_return_pct: float
    directional_return_pct: float | None
    hit: bool | None
    adverse_move_pct: float | None


@dataclass(slots=True)
class EvaluatedAnalysis:
    record: AIAnalysisRecord
    direction: int
    status: str
    status_reason: str | None
    outcomes: dict[int, HorizonOutcome]


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_market_type(value: str | None) -> str | None:
    if not value:
        return None
    normalized = str(value).strip().upper()
    if normalized == "BIST":
        return "BIST"
    if normalized in {"KRIPTO", "KRYPTO", "CRYPTO"}:
        return "Kripto"
    return value


def _normalize_special_tag(value: str | None) -> str | None:
    if not value:
        return None
    normalized = str(value).strip().upper()
    return normalized or None


def _infer_special_tag(
    linked_special_tag: str | None, technical_data: dict[str, Any]
) -> str | None:
    return _normalize_special_tag(linked_special_tag) or _normalize_special_tag(
        technical_data.get("special_tag")
    )


def _infer_direction(sentiment_label: str | None, signal_type: str | None) -> int:
    normalized_label = (sentiment_label or "").strip().upper()
    if normalized_label:
        if normalized_label in {"AL", "GUCLU AL"}:
            return 1
        if normalized_label in {"SAT", "GUCLU SAT"}:
            return -1
        if normalized_label == "NOTR":
            return 0

    normalized_signal = (signal_type or "").strip().upper()
    if normalized_signal == "AL":
        return 1
    if normalized_signal == "SAT":
        return -1
    return 0


def _normalize_price_frame(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None

    normalized = df.copy()
    normalized.index = pd.to_datetime(normalized.index)
    if getattr(normalized.index, "tz", None) is not None:
        normalized.index = normalized.index.tz_localize(None)
    normalized = normalized.sort_index()

    required_columns = {"Close", "High", "Low"}
    if not required_columns.issubset(set(normalized.columns)):
        return None

    normalized = normalized[
        list(required_columns.union({"Open", "Volume"}).intersection(normalized.columns))
    ]
    return normalized


def _default_price_loader(symbol: str, market_type: str) -> pd.DataFrame | None:
    if market_type == "BIST":
        return get_bist_data(symbol)
    return get_crypto_data(symbol)


def _build_cached_price_loader(base_loader: PriceLoader | None = None) -> PriceLoader:
    loader = base_loader or _default_price_loader
    cache: dict[tuple[str, str], pd.DataFrame | None] = {}

    def _cached(symbol: str, market_type: str) -> pd.DataFrame | None:
        cache_key = (market_type, symbol)
        if cache_key not in cache:
            cache[cache_key] = _normalize_price_frame(loader(symbol, market_type))
        return cache[cache_key]

    return _cached


def load_ai_analysis_records(
    *,
    since_days: int = 90,
    market_type: str | None = None,
    special_tag: str | None = None,
    include_manual: bool = False,
    limit: int | None = None,
) -> list[AIAnalysisRecord]:
    """
    Load persisted AI analysis records for evaluation.
    """
    normalized_market = _normalize_market_type(market_type)
    normalized_special_tag = _normalize_special_tag(special_tag)
    since_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(1, since_days))

    with get_session() as session:
        query = (
            session.query(AIAnalysis, Signal.special_tag)
            .outerjoin(Signal, AIAnalysis.signal_id == Signal.id)
            .filter(AIAnalysis.created_at >= since_at)
        )

        if normalized_market:
            query = query.filter(AIAnalysis.market_type == normalized_market)
        if not include_manual:
            query = query.filter(~AIAnalysis.scenario_name.like("MANUAL_%"))
        if limit:
            query = query.order_by(AIAnalysis.created_at.desc()).limit(limit)
        else:
            query = query.order_by(AIAnalysis.created_at.asc())

        rows = query.all()

    records: list[AIAnalysisRecord] = []
    for analysis, linked_special_tag in rows:
        technical_data = _safe_json_loads(analysis.technical_data)
        resolved_special_tag = _infer_special_tag(linked_special_tag, technical_data)
        if normalized_special_tag and resolved_special_tag != normalized_special_tag:
            continue

        records.append(
            AIAnalysisRecord(
                id=analysis.id,
                symbol=analysis.symbol,
                market_type=_normalize_market_type(analysis.market_type) or analysis.market_type,
                created_at=analysis.created_at,
                scenario_name=analysis.scenario_name,
                signal_type=analysis.signal_type,
                sentiment_label=analysis.sentiment_label,
                confidence_score=analysis.confidence_score,
                risk_level=analysis.risk_level,
                prompt_version=analysis.prompt_version,
                special_tag=resolved_special_tag,
                technical_data=technical_data,
            )
        )

    records.sort(key=lambda current_record: current_record.created_at)
    return records


def _find_position_on_or_after(dates: pd.DatetimeIndex, target: pd.Timestamp) -> int | None:
    position = int(dates.searchsorted(target, side="left"))
    if position >= len(dates):
        return None
    return position


def _calculate_adverse_move_pct(
    window_df: pd.DataFrame,
    direction: int,
    entry_price: float,
) -> float | None:
    if direction == 0 or window_df.empty:
        return None

    if direction > 0:
        min_low = _safe_float(window_df["Low"].min())
        if min_low is None:
            return None
        return max(0.0, (1.0 - (min_low / entry_price)) * 100.0)

    max_high = _safe_float(window_df["High"].max())
    if max_high is None:
        return None
    return max(0.0, ((max_high / entry_price) - 1.0) * 100.0)


def evaluate_ai_records(
    records: list[AIAnalysisRecord],
    *,
    horizons: tuple[int, ...] = DEFAULT_EVAL_HORIZONS,
    price_loader: PriceLoader | None = None,
) -> list[EvaluatedAnalysis]:
    """
    Evaluate stored AI analyses against forward price action.
    """
    cached_loader = _build_cached_price_loader(price_loader)
    evaluated: list[EvaluatedAnalysis] = []

    for record in records:
        direction = _infer_direction(record.sentiment_label, record.signal_type)
        df = cached_loader(record.symbol, record.market_type)
        if df is None or df.empty:
            evaluated.append(
                EvaluatedAnalysis(
                    record=record,
                    direction=direction,
                    status="missing_price_data",
                    status_reason="Fiyat verisi bulunamadi",
                    outcomes={},
                )
            )
            continue

        dates = pd.DatetimeIndex(pd.to_datetime(df.index).normalize())
        analysis_date = pd.Timestamp(record.created_at.date())
        entry_position = _find_position_on_or_after(dates, analysis_date)
        if entry_position is None:
            evaluated.append(
                EvaluatedAnalysis(
                    record=record,
                    direction=direction,
                    status="missing_entry_window",
                    status_reason="Analiz sonrasi fiyat penceresi yok",
                    outcomes={},
                )
            )
            continue

        entry_price = _safe_float(df["Close"].iloc[entry_position])
        if entry_price is None or entry_price <= 0:
            evaluated.append(
                EvaluatedAnalysis(
                    record=record,
                    direction=direction,
                    status="missing_entry_price",
                    status_reason="Giris fiyati gecersiz",
                    outcomes={},
                )
            )
            continue

        entry_date = dates[entry_position]
        outcomes: dict[int, HorizonOutcome] = {}
        for horizon_days in sorted(set(horizons)):
            if horizon_days <= 0:
                continue

            exit_target = entry_date + pd.Timedelta(days=horizon_days)
            exit_position = _find_position_on_or_after(dates, exit_target)
            if exit_position is None:
                continue

            exit_price = _safe_float(df["Close"].iloc[exit_position])
            if exit_price is None or exit_price <= 0:
                continue

            raw_return_pct = ((exit_price / entry_price) - 1.0) * 100.0
            directional_return_pct = raw_return_pct * direction if direction != 0 else None
            hit = directional_return_pct > 0 if directional_return_pct is not None else None
            adverse_move_pct = _calculate_adverse_move_pct(
                df.iloc[entry_position : exit_position + 1],
                direction,
                entry_price,
            )

            outcomes[horizon_days] = HorizonOutcome(
                horizon_days=horizon_days,
                entry_date=entry_date.date().isoformat(),
                exit_date=dates[exit_position].date().isoformat(),
                entry_price=round(entry_price, 6),
                exit_price=round(exit_price, 6),
                raw_return_pct=round(raw_return_pct, 4),
                directional_return_pct=round(directional_return_pct, 4)
                if directional_return_pct is not None
                else None,
                hit=hit,
                adverse_move_pct=round(adverse_move_pct, 4)
                if adverse_move_pct is not None
                else None,
            )

        evaluated.append(
            EvaluatedAnalysis(
                record=record,
                direction=direction,
                status="evaluated" if outcomes else "missing_exit_window",
                status_reason=None if outcomes else "Ileri fiyat penceresi yetersiz",
                outcomes=outcomes,
            )
        )

    return evaluated


def _summarize_horizon(
    samples: list[EvaluatedAnalysis],
    horizon_days: int,
) -> dict[str, Any]:
    horizon_outcomes = [
        sample.outcomes[horizon_days] for sample in samples if horizon_days in sample.outcomes
    ]
    directional_outcomes = [
        sample.outcomes[horizon_days]
        for sample in samples
        if horizon_days in sample.outcomes and sample.direction != 0
    ]

    hit_values = [
        1.0 if outcome.hit else 0.0 for outcome in directional_outcomes if outcome.hit is not None
    ]
    directional_returns = [
        outcome.directional_return_pct
        for outcome in directional_outcomes
        if outcome.directional_return_pct is not None
    ]
    raw_returns = [outcome.raw_return_pct for outcome in horizon_outcomes]
    adverse_moves = [
        outcome.adverse_move_pct
        for outcome in directional_outcomes
        if outcome.adverse_move_pct is not None
    ]

    return {
        "horizon_days": horizon_days,
        "sample_count": len(horizon_outcomes),
        "directional_sample_count": len(directional_outcomes),
        "hit_rate_pct": round(mean(hit_values) * 100.0, 2) if hit_values else None,
        "avg_directional_return_pct": round(mean(directional_returns), 4)
        if directional_returns
        else None,
        "avg_raw_return_pct": round(mean(raw_returns), 4) if raw_returns else None,
        "avg_adverse_move_pct": round(mean(adverse_moves), 4) if adverse_moves else None,
    }


def _summarize_group(
    label: str,
    samples: list[EvaluatedAnalysis],
    *,
    horizons: tuple[int, ...],
    primary_horizon_days: int,
) -> dict[str, Any]:
    horizon_metrics = {
        horizon_days: _summarize_horizon(samples, horizon_days) for horizon_days in horizons
    }
    primary_metrics = horizon_metrics.get(primary_horizon_days, {})

    return {
        "label": label,
        "count": len(samples),
        "evaluated_count": sum(1 for sample in samples if sample.status == "evaluated"),
        "neutral_count": sum(1 for sample in samples if sample.direction == 0),
        "primary_horizon_days": primary_horizon_days,
        "primary_hit_rate_pct": primary_metrics.get("hit_rate_pct"),
        "primary_avg_directional_return_pct": primary_metrics.get("avg_directional_return_pct"),
        "primary_avg_adverse_move_pct": primary_metrics.get("avg_adverse_move_pct"),
        "horizons": horizon_metrics,
    }


def _confidence_bucket(score: int | None) -> str:
    if score is None:
        return "Bilinmiyor"
    for minimum, maximum, label in CONFIDENCE_BUCKETS:
        if minimum <= score <= maximum:
            return label
    return "Bilinmiyor"


def _risk_bucket(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized or "Bilinmiyor"


def _special_tag_bucket(value: str | None) -> str:
    return value or "STANDARD"


def _build_period_summaries(
    samples: list[EvaluatedAnalysis],
    *,
    horizons: tuple[int, ...],
    primary_horizon_days: int,
    period: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[EvaluatedAnalysis]] = defaultdict(list)
    for sample in samples:
        if sample.record.created_at is None:
            continue
        if period == "week":
            iso_year, iso_week, _ = sample.record.created_at.isocalendar()
            label = f"{iso_year}-W{iso_week:02d}"
        else:
            label = sample.record.created_at.strftime("%Y-%m")
        grouped[label].append(sample)

    summaries = [
        _summarize_group(
            label=label,
            samples=group_samples,
            horizons=horizons,
            primary_horizon_days=primary_horizon_days,
        )
        for label, group_samples in sorted(grouped.items())
    ]
    return summaries


def build_ai_quality_report(
    *,
    since_days: int = 90,
    market_type: str | None = None,
    special_tag: str | None = None,
    include_manual: bool = False,
    limit: int | None = None,
    horizons: tuple[int, ...] = DEFAULT_EVAL_HORIZONS,
    primary_horizon_days: int = DEFAULT_PRIMARY_HORIZON_DAYS,
    price_loader: PriceLoader | None = None,
) -> dict[str, Any]:
    """
    Build an aggregate AI quality report from persisted analyses.
    """
    records = load_ai_analysis_records(
        since_days=since_days,
        market_type=market_type,
        special_tag=special_tag,
        include_manual=include_manual,
        limit=limit,
    )
    evaluated_samples = evaluate_ai_records(records, horizons=horizons, price_loader=price_loader)
    evaluated_only = [sample for sample in evaluated_samples if sample.status == "evaluated"]

    by_market: dict[str, list[EvaluatedAnalysis]] = defaultdict(list)
    by_special_tag: dict[str, list[EvaluatedAnalysis]] = defaultdict(list)
    by_confidence: dict[str, list[EvaluatedAnalysis]] = defaultdict(list)
    by_risk: dict[str, list[EvaluatedAnalysis]] = defaultdict(list)
    by_prompt_version: dict[str, list[EvaluatedAnalysis]] = defaultdict(list)

    for sample in evaluated_only:
        by_market[sample.record.market_type].append(sample)
        by_special_tag[_special_tag_bucket(sample.record.special_tag)].append(sample)
        by_confidence[_confidence_bucket(sample.record.confidence_score)].append(sample)
        by_risk[_risk_bucket(sample.record.risk_level)].append(sample)
        by_prompt_version[sample.record.prompt_version or "Bilinmiyor"].append(sample)

    status_counts: dict[str, int] = defaultdict(int)
    for sample in evaluated_samples:
        status_counts[sample.status] += 1

    report = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "filters": {
            "since_days": since_days,
            "market_type": _normalize_market_type(market_type),
            "special_tag": _normalize_special_tag(special_tag),
            "include_manual": include_manual,
            "limit": limit,
        },
        "horizons": list(horizons),
        "primary_horizon_days": primary_horizon_days,
        "totals": {
            "records_total": len(records),
            "evaluated_records": len(evaluated_only),
            "missing_price_data": status_counts.get("missing_price_data", 0),
            "missing_entry_window": status_counts.get("missing_entry_window", 0),
            "missing_entry_price": status_counts.get("missing_entry_price", 0),
            "missing_exit_window": status_counts.get("missing_exit_window", 0),
            "neutral_direction_records": sum(
                1 for sample in evaluated_only if sample.direction == 0
            ),
        },
        "overall": _summarize_group(
            label="overall",
            samples=evaluated_only,
            horizons=horizons,
            primary_horizon_days=primary_horizon_days,
        ),
        "by_market": [
            _summarize_group(
                label=label,
                samples=group_samples,
                horizons=horizons,
                primary_horizon_days=primary_horizon_days,
            )
            for label, group_samples in sorted(by_market.items())
        ],
        "by_special_tag": [
            _summarize_group(
                label=label,
                samples=group_samples,
                horizons=horizons,
                primary_horizon_days=primary_horizon_days,
            )
            for label, group_samples in sorted(by_special_tag.items())
        ],
        "by_confidence_bucket": [
            _summarize_group(
                label=label,
                samples=group_samples,
                horizons=horizons,
                primary_horizon_days=primary_horizon_days,
            )
            for label, group_samples in sorted(
                by_confidence.items(),
                key=lambda item: next(
                    (
                        index
                        for index, (_, _, bucket_label) in enumerate(CONFIDENCE_BUCKETS)
                        if bucket_label == item[0]
                    ),
                    99,
                ),
            )
        ],
        "by_risk_level": [
            _summarize_group(
                label=label,
                samples=group_samples,
                horizons=horizons,
                primary_horizon_days=primary_horizon_days,
            )
            for label, group_samples in sorted(by_risk.items())
        ],
        "by_prompt_version": [
            _summarize_group(
                label=label,
                samples=group_samples,
                horizons=horizons,
                primary_horizon_days=primary_horizon_days,
            )
            for label, group_samples in sorted(by_prompt_version.items())
        ],
        "weekly": _build_period_summaries(
            evaluated_only,
            horizons=horizons,
            primary_horizon_days=primary_horizon_days,
            period="week",
        ),
        "monthly": _build_period_summaries(
            evaluated_only,
            horizons=horizons,
            primary_horizon_days=primary_horizon_days,
            period="month",
        ),
    }
    return report


def format_ai_quality_report(report: dict[str, Any]) -> str:
    """
    Render a console-friendly evaluation report.
    """
    primary_horizon = report.get("primary_horizon_days", DEFAULT_PRIMARY_HORIZON_DAYS)
    totals = report.get("totals", {})
    lines = [
        "AI Evaluation Report",
        f"Generated: {report.get('generated_at')}",
        (
            "Filters: "
            f"since_days={report.get('filters', {}).get('since_days')} "
            f"market={report.get('filters', {}).get('market_type') or 'ALL'} "
            f"special_tag={report.get('filters', {}).get('special_tag') or 'ALL'} "
            f"include_manual={report.get('filters', {}).get('include_manual')}"
        ),
        "",
        "Overview",
        f"- records_total: {totals.get('records_total', 0)}",
        f"- evaluated_records: {totals.get('evaluated_records', 0)}",
        f"- missing_price_data: {totals.get('missing_price_data', 0)}",
        f"- missing_exit_window: {totals.get('missing_exit_window', 0)}",
        f"- neutral_direction_records: {totals.get('neutral_direction_records', 0)}",
        "",
    ]

    overall = report.get("overall", {})
    lines.extend(
        [
            f"Overall ({primary_horizon}d primary)",
            _format_group_line(overall),
            "",
            "By Market",
        ]
    )
    lines.extend(_format_group_section(report.get("by_market", [])))
    lines.extend(["", "By Special Tag"])
    lines.extend(_format_group_section(report.get("by_special_tag", [])))
    lines.extend(["", "By Confidence Bucket"])
    lines.extend(_format_group_section(report.get("by_confidence_bucket", [])))
    lines.extend(["", "By Risk Level"])
    lines.extend(_format_group_section(report.get("by_risk_level", [])))
    lines.extend(["", "Weekly"])
    lines.extend(_format_group_section(report.get("weekly", [])[-8:]))
    lines.extend(["", "Monthly"])
    lines.extend(_format_group_section(report.get("monthly", [])[-6:]))
    return "\n".join(lines)


def _format_group_section(groups: list[dict[str, Any]]) -> list[str]:
    if not groups:
        return ["- veri yok"]
    return [f"- {group.get('label')}: {_format_group_line(group)}" for group in groups]


def _format_group_line(group: dict[str, Any]) -> str:
    return (
        f"count={group.get('count', 0)} "
        f"evaluated={group.get('evaluated_count', 0)} "
        f"hit={group.get('primary_hit_rate_pct')}% "
        f"avg_dir={group.get('primary_avg_directional_return_pct')}% "
        f"avg_adverse={group.get('primary_avg_adverse_move_pct')}%"
    )
