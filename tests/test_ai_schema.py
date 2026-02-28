"""
Unit tests for shared AI response schema normalization.
"""

import json

import pytest

from ai_schema import AIResponseSchemaError, build_ai_error_payload, parse_ai_response


class TestAISchema:
    @pytest.mark.unit
    def test_parse_ai_response_fills_defaults_for_sparse_payload(self):
        payload = parse_ai_response(
            json.dumps(
                {
                    "sentiment_score": 61,
                    "sentiment_label": "AL",
                    "summary": ["ilk madde"],
                    "explanation": "ornek aciklama",
                    "key_levels": {"support": "10.5", "resistance": ["11.2"]},
                    "risk_level": "Orta",
                }
            )
        )

        assert payload.confidence_score == 50
        assert payload.technical_view.bias == "NOTR"
        assert payload.news_view.headline_count == 0
        assert payload.key_levels.support == ["10.5"]

    @pytest.mark.unit
    def test_parse_ai_response_normalizes_legacy_labels(self):
        payload = parse_ai_response(
            json.dumps(
                {
                    "sentiment_score": 75,
                    "sentiment_label": "GÜÇLÜ AL",
                    "confidence_score": 88,
                    "summary": ["madde"],
                    "explanation": "aciklama",
                    "key_levels": {"support": [], "resistance": []},
                    "risk_level": "Düşük",
                }
            )
        )

        assert payload.sentiment_label == "GUCLU AL"
        assert payload.risk_level == "Dusuk"

    @pytest.mark.unit
    def test_parse_ai_response_raises_for_non_json_text(self):
        with pytest.raises(AIResponseSchemaError) as exc:
            parse_ai_response("duz metin")

        assert exc.value.error_code == "invalid_json"

    @pytest.mark.unit
    def test_build_ai_error_payload_produces_schema_valid_json(self):
        payload = parse_ai_response(
            build_ai_error_payload(
                error="Timeout",
                error_code="timeout",
                provider="gemini",
                model_name="gemini-2.5-flash",
                backend="google.generativeai",
            )
        )

        assert payload.error == "Timeout"
        assert payload.error_code == "timeout"
        assert payload.provider == "gemini"
        assert payload.prompt_version is None
