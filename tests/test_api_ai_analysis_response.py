import json
from types import SimpleNamespace

from api.main import _build_ai_analysis_response


def test_build_ai_analysis_response_derives_metadata_from_legacy_json():
    analysis = SimpleNamespace(
        id=1,
        signal_id=11,
        symbol="THYAO",
        market_type="BIST",
        scenario_name="TEST",
        signal_type="AL",
        analysis_text=json.dumps(
            {
                "sentiment_score": 61,
                "sentiment_label": "AL",
                "confidence_score": 74,
                "risk_level": "Orta",
                "summary": ["ok"],
                "explanation": "legacy record",
                "technical_view": {
                    "bias": "AL",
                    "strength": 68,
                    "conflicts": [],
                },
                "news_view": {
                    "bias": "NOTR",
                    "strength": 35,
                    "headline_count": 3,
                },
                "key_levels": {
                    "support": ["1"],
                    "resistance": ["2"],
                },
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "backend": "google.genai",
                "prompt_version": "v4-neutral-rule-context",
            }
        ),
        technical_data='{"foo":"bar"}',
        provider=None,
        model=None,
        backend=None,
        prompt_version=None,
        sentiment_score=None,
        sentiment_label=None,
        confidence_score=None,
        risk_level=None,
        technical_bias=None,
        technical_strength=None,
        news_bias=None,
        news_strength=None,
        headline_count=None,
        latency_ms=None,
        error_code=None,
        created_at=None,
    )

    response = _build_ai_analysis_response(analysis)

    assert response.provider == "gemini"
    assert response.model == "gemini-2.5-flash"
    assert response.backend == "google.genai"
    assert response.prompt_version == "v4-neutral-rule-context"
    assert response.sentiment_score == 61
    assert response.sentiment_label == "AL"
    assert response.confidence_score == 74
    assert response.risk_level == "Orta"
    assert response.technical_bias == "AL"
    assert response.technical_strength == 68
    assert response.news_bias == "NOTR"
    assert response.news_strength == 35
    assert response.headline_count == 3
