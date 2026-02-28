from datetime import UTC, datetime

import pandas as pd

from ai_evaluation import AIAnalysisRecord, build_ai_quality_report, evaluate_ai_records


def build_price_frame(closes: list[float]) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=len(closes), freq="D")
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [value * 1.03 for value in closes],
            "Low": [value * 0.97 for value in closes],
            "Close": closes,
            "Volume": [1000] * len(closes),
        },
        index=dates,
    )


def test_evaluate_ai_records_generates_directional_hits():
    records = [
        AIAnalysisRecord(
            id=1,
            symbol="LONG1",
            market_type="BIST",
            created_at=datetime(2026, 1, 2, tzinfo=UTC).replace(tzinfo=None),
            scenario_name="SPECIAL",
            signal_type="AL",
            sentiment_label="AL",
            confidence_score=82,
            risk_level="Dusuk",
            prompt_version="v4",
            special_tag="BELES",
            technical_data={"special_tag": "BELES"},
        ),
        AIAnalysisRecord(
            id=2,
            symbol="SHORT1",
            market_type="Kripto",
            created_at=datetime(2026, 1, 2, tzinfo=UTC).replace(tzinfo=None),
            scenario_name="SPECIAL",
            signal_type="SAT",
            sentiment_label="SAT",
            confidence_score=67,
            risk_level="Yuksek",
            prompt_version="v4",
            special_tag="PAHALI",
            technical_data={"special_tag": "PAHALI"},
        ),
        AIAnalysisRecord(
            id=3,
            symbol="NEUTRAL1",
            market_type="BIST",
            created_at=datetime(2026, 1, 2, tzinfo=UTC).replace(tzinfo=None),
            scenario_name="SPECIAL",
            signal_type="AL",
            sentiment_label="NOTR",
            confidence_score=45,
            risk_level="Orta",
            prompt_version="v4",
            special_tag=None,
            technical_data={},
        ),
    ]

    prices = {
        ("BIST", "LONG1"): build_price_frame([100, 101, 102, 104, 105, 107, 109, 110, 111, 112]),
        ("Kripto", "SHORT1"): build_price_frame([100, 99, 98, 96, 95, 94, 93, 92, 91, 90]),
        ("BIST", "NEUTRAL1"): build_price_frame([100, 100, 100, 100, 100, 100, 100, 100, 100, 100]),
    }

    evaluated = evaluate_ai_records(
        records,
        horizons=(3, 7),
        price_loader=lambda symbol, market_type: prices.get((market_type, symbol)),
    )

    assert len(evaluated) == 3
    assert all(sample.status == "evaluated" for sample in evaluated)
    assert evaluated[0].outcomes[3].hit is True
    assert evaluated[1].outcomes[7].hit is True
    assert evaluated[2].outcomes[3].hit is None


def test_build_ai_quality_report_groups_by_tag_market_and_confidence(monkeypatch):
    records = [
        AIAnalysisRecord(
            id=1,
            symbol="LONG1",
            market_type="BIST",
            created_at=datetime(2026, 1, 2, tzinfo=UTC).replace(tzinfo=None),
            scenario_name="SPECIAL",
            signal_type="AL",
            sentiment_label="AL",
            confidence_score=85,
            risk_level="Dusuk",
            prompt_version="v4",
            special_tag="BELES",
            technical_data={"special_tag": "BELES"},
        ),
        AIAnalysisRecord(
            id=2,
            symbol="SHORT1",
            market_type="Kripto",
            created_at=datetime(2026, 1, 9, tzinfo=UTC).replace(tzinfo=None),
            scenario_name="SPECIAL",
            signal_type="SAT",
            sentiment_label="SAT",
            confidence_score=62,
            risk_level="Yuksek",
            prompt_version="v4",
            special_tag="PAHALI",
            technical_data={"special_tag": "PAHALI"},
        ),
    ]

    prices = {
        ("BIST", "LONG1"): build_price_frame([100, 102, 103, 104, 106, 108, 110, 112, 114, 116]),
        ("Kripto", "SHORT1"): build_price_frame(
            [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84]
        ),
    }

    monkeypatch.setattr(
        "ai_evaluation.load_ai_analysis_records",
        lambda **kwargs: records,
    )

    report = build_ai_quality_report(
        since_days=30,
        horizons=(3, 7),
        price_loader=lambda symbol, market_type: prices.get((market_type, symbol)),
    )

    assert report["totals"]["records_total"] == 2
    assert report["totals"]["evaluated_records"] == 2
    assert report["overall"]["primary_hit_rate_pct"] == 100.0
    assert any(item["label"] == "BIST" for item in report["by_market"])
    assert any(item["label"] == "Kripto" for item in report["by_market"])
    assert any(item["label"] == "BELES" for item in report["by_special_tag"])
    assert any(item["label"] == "PAHALI" for item in report["by_special_tag"])
    assert any(item["label"] == "80-100" for item in report["by_confidence_bucket"])
    assert any(item["label"] == "60-79" for item in report["by_confidence_bucket"])
    assert report["weekly"]
    assert report["monthly"]
