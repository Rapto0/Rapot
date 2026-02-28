import json

from fastapi.testclient import TestClient

import api.main as api_main


def _build_report() -> dict:
    return {
        "symbol": "THYAO",
        "market_type": "BIST",
        "strategy": "HUNTER",
        "indicator_order": ["RSI", "MACD"],
        "indicator_labels": {"RSI": "RSI (14)", "MACD": "MACD"},
        "generated_at": "2026-02-28T12:00:00Z",
        "timeframes": [
            {
                "code": "1D",
                "label": "GUNLUK",
                "available": True,
                "signal_status": "AL",
                "reason": None,
                "price": 307.5,
                "date": "2026-02-27",
                "active_indicators": "15/15",
                "primary_score": "2/7",
                "primary_score_label": "Dip Skoru",
                "secondary_score": "1/10",
                "secondary_score_label": "Tepe Skoru",
                "raw_score": None,
                "indicators": {"RSI": 45.23, "MACD": 2.3386},
            },
            {
                "code": "W-FRI",
                "label": "1 HAFTALIK",
                "available": True,
                "signal_status": "NOTR",
                "reason": None,
                "price": 307.5,
                "date": "2026-02-27",
                "active_indicators": "15/15",
                "primary_score": "0/7",
                "primary_score_label": "Dip Skoru",
                "secondary_score": "4/10",
                "secondary_score_label": "Tepe Skoru",
                "raw_score": None,
                "indicators": {"RSI": 53.05, "MACD": 6.2922},
            },
        ],
    }


def _analysis_json() -> str:
    return json.dumps(
        {
            "sentiment_score": 64,
            "sentiment_label": "AL",
            "confidence_score": 71,
            "risk_level": "Orta",
            "summary": ["Momentum destekliyor", "Haftalik teyit zayif"],
            "explanation": "Teknik gorunum kontrollu pozitif.",
            "technical_view": {
                "bias": "AL",
                "strength": 64,
                "conflicts": ["Haftalik momentum tam teyit vermiyor."],
            },
            "news_view": {
                "bias": "NOTR",
                "strength": 40,
                "headline_count": 2,
            },
            "key_levels": {
                "support": ["302.5", "298.0"],
                "resistance": ["312.0", "318.5"],
            },
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "backend": "google.genai",
            "prompt_version": "v4-neutral-rule-context",
        }
    )


def test_market_analysis_endpoint_uses_selected_timeframe_and_no_db_save(monkeypatch):
    captured: dict = {}

    def fake_inspect_strategy(symbol: str, strategy: str, market_type: str | None = None):
        captured["inspect_args"] = {
            "symbol": symbol,
            "strategy": strategy,
            "market_type": market_type,
        }
        return _build_report()

    def fake_analyze_with_gemini(**kwargs):
        captured["analysis_args"] = kwargs
        return _analysis_json()

    monkeypatch.setattr(api_main, "inspect_strategy", fake_inspect_strategy)
    monkeypatch.setattr("ai_analyst.analyze_with_gemini", fake_analyze_with_gemini)

    client = TestClient(api_main.app)
    response = client.get(
        "/api/market/analysis",
        params={"symbol": "THYAO", "strategy": "HUNTER", "timeframe": "1D"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert captured["inspect_args"]["market_type"] is None
    assert captured["analysis_args"]["save_to_db"] is False
    assert captured["analysis_args"]["technical_data"]["trigger_rule"] == ["1D"]
    assert [
        item["code"] for item in captured["analysis_args"]["technical_data"]["matched_timeframes"]
    ] == ["1D"]
    assert payload["timeframe"] == "1D"
    assert payload["inspection"]["timeframes"][0]["code"] == "1D"
    assert len(payload["inspection"]["timeframes"]) == 1
    assert payload["structured_analysis"]["sentiment_label"] == "AL"


def test_market_analysis_endpoint_returns_all_timeframes_for_default_mode(monkeypatch):
    def fake_inspect_strategy(symbol: str, strategy: str, market_type: str | None = None):
        return _build_report()

    def fake_analyze_with_gemini(**kwargs):
        return _analysis_json()

    monkeypatch.setattr(api_main, "inspect_strategy", fake_inspect_strategy)
    monkeypatch.setattr("ai_analyst.analyze_with_gemini", fake_analyze_with_gemini)

    client = TestClient(api_main.app)
    response = client.get(
        "/api/market/analysis",
        params={"symbol": "THYAO", "strategy": "HUNTER", "market_type": "BIST"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["timeframe"] == "ALL"
    assert len(payload["inspection"]["timeframes"]) == 2
    assert payload["inspection"]["timeframes"][0]["code"] == "1D"
    assert payload["inspection"]["timeframes"][1]["code"] == "W-FRI"
