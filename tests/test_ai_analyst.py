"""
Unit tests for AI analyst Phase 1 runtime configuration.
"""

import json
from contextlib import contextmanager

import pytest

import ai_analyst


def _config_value(config, name: str):
    if isinstance(config, dict):
        return config.get(name)
    return getattr(config, name, None)


class TestAIAnalystPhaseOne:
    @pytest.mark.unit
    def test_generation_config_enforces_json_schema(self, monkeypatch):
        monkeypatch.setattr(ai_analyst.settings, "ai_temperature", 0.2)
        monkeypatch.setattr(ai_analyst.settings, "ai_max_output_tokens", 1024)

        config = ai_analyst._get_generation_config("google.generativeai")

        assert _config_value(config, "response_mime_type") == "application/json"
        response_schema = _config_value(config, "response_schema")
        assert response_schema["type"] == "object"
        assert "sentiment_score" in response_schema["properties"]
        assert "technical_view" in response_schema["properties"]

    @pytest.mark.unit
    def test_generation_config_uses_response_schema_for_google_genai(self, monkeypatch):
        monkeypatch.setattr(ai_analyst.settings, "ai_temperature", 0.2)
        monkeypatch.setattr(ai_analyst.settings, "ai_max_output_tokens", 1024)
        monkeypatch.setattr(ai_analyst.settings, "ai_thinking_budget", 0)

        config = ai_analyst._get_generation_config("google.genai")

        assert _config_value(config, "response_mime_type") == "application/json"
        response_schema = _config_value(config, "response_schema")
        if ai_analyst.google_genai_types is None:
            assert response_schema is ai_analyst.AIAnalysisPayload
            assert _config_value(config, "thinking_config") == {"thinking_budget": 0}
        else:
            assert response_schema is ai_analyst.AIAnalysisPayload
            thinking_config = _config_value(config, "thinking_config")
            assert _config_value(thinking_config, "thinking_budget") == 0

    @pytest.mark.unit
    def test_build_model_candidates_deduplicates_values(self, monkeypatch):
        monkeypatch.setattr(ai_analyst.settings, "ai_model", "gemini-2.5-flash")
        monkeypatch.setattr(ai_analyst.settings, "ai_enable_fallback", True)
        monkeypatch.setattr(ai_analyst.settings, "ai_fallback_model", "gemini-2.5-flash")

        assert ai_analyst.build_model_candidates() == ["gemini-2.5-flash"]

    @pytest.mark.unit
    def test_build_model_candidates_skips_fallback_by_default(self, monkeypatch):
        monkeypatch.setattr(ai_analyst.settings, "ai_model", "gemini-2.5-flash")
        monkeypatch.setattr(ai_analyst.settings, "ai_enable_fallback", False)
        monkeypatch.setattr(ai_analyst.settings, "ai_fallback_model", "gemini-2.5-flash-lite")

        assert ai_analyst.build_model_candidates() == ["gemini-2.5-flash"]

    @pytest.mark.unit
    def test_analyze_with_gemini_uses_fallback_model_only_when_enabled(self, monkeypatch):
        monkeypatch.setattr(ai_analyst.settings, "ai_provider", "gemini")
        monkeypatch.setattr(ai_analyst.settings, "ai_model", "gemini-2.5-flash")
        monkeypatch.setattr(ai_analyst.settings, "ai_enable_fallback", True)
        monkeypatch.setattr(ai_analyst.settings, "ai_fallback_model", "gemini-2.5-flash-lite")
        monkeypatch.setattr(ai_analyst.settings, "gemini_api_key", "test-key")
        monkeypatch.setattr(ai_analyst, "gemini_client", object())
        monkeypatch.setattr(ai_analyst, "legacy_genai", None)

        calls: list[str] = []

        def fake_ensure_backend():
            return "test-key", "google.genai"

        def fake_generate(model_name: str, prompt: str, backend: str):
            calls.append(model_name)
            if model_name == "gemini-2.5-flash":
                raise RuntimeError("primary failed")
            return json.dumps(
                {
                    "sentiment_score": 62,
                    "sentiment_label": "AL",
                    "summary": ["ok"],
                    "explanation": "fallback success",
                    "key_levels": {"support": ["1"], "resistance": ["2"]},
                    "risk_level": "Orta",
                }
            )

        monkeypatch.setattr(ai_analyst, "_ensure_gemini_backend", fake_ensure_backend)
        monkeypatch.setattr(ai_analyst, "_generate_model_response", fake_generate)

        response = ai_analyst.analyze_with_gemini(
            symbol="THYAO",
            scenario_name="Test",
            signal_type="AL",
            technical_data={"PRICE": 1, "RSI": 50, "MACD": 0},
            save_to_db=False,
        )
        payload = json.loads(response)

        assert calls == ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
        assert payload["provider"] == "gemini"
        assert payload["model"] == "gemini-2.5-flash-lite"
        assert payload["backend"] == "google.genai"
        assert payload["prompt_version"] == ai_analyst.AI_PROMPT_VERSION

    @pytest.mark.unit
    def test_analyze_with_gemini_rejects_unsupported_provider(self, monkeypatch):
        monkeypatch.setattr(ai_analyst.settings, "ai_provider", "openai")
        monkeypatch.setattr(ai_analyst.settings, "ai_model", "gpt-5-mini")

        response = ai_analyst.analyze_with_gemini(
            symbol="THYAO",
            scenario_name="Test",
            signal_type="AL",
            technical_data={"PRICE": 1, "RSI": 50, "MACD": 0},
            save_to_db=False,
        )
        payload = json.loads(response)

        assert "Desteklenmeyen AI provider" in payload["error"]
        assert payload["provider"] == "openai"
        assert payload["model"] == "gpt-5-mini"
        assert payload["error_code"] == "unsupported_provider"
        assert payload["prompt_version"] == ai_analyst.AI_PROMPT_VERSION

    @pytest.mark.unit
    def test_analyze_with_gemini_returns_structured_error_for_invalid_json(self, monkeypatch):
        monkeypatch.setattr(ai_analyst.settings, "ai_provider", "gemini")
        monkeypatch.setattr(ai_analyst.settings, "ai_model", "gemini-2.5-flash")
        monkeypatch.setattr(ai_analyst.settings, "ai_enable_fallback", False)
        monkeypatch.setattr(ai_analyst.settings, "ai_fallback_model", None)
        monkeypatch.setattr(ai_analyst.settings, "gemini_api_key", "test-key")
        monkeypatch.setattr(ai_analyst, "gemini_client", object())
        monkeypatch.setattr(ai_analyst, "legacy_genai", None)
        monkeypatch.setattr(
            ai_analyst,
            "_ensure_gemini_backend",
            lambda: ("test-key", "google.generativeai"),
        )
        monkeypatch.setattr(
            ai_analyst,
            "_generate_model_response",
            lambda model_name, prompt, backend: "not-json",
        )

        response = ai_analyst.analyze_with_gemini(
            symbol="THYAO",
            scenario_name="Test",
            signal_type="AL",
            technical_data={"PRICE": 1, "RSI": 50, "MACD": 0},
            save_to_db=False,
        )
        payload = json.loads(response)

        assert payload["error_code"] == "invalid_json"
        assert payload["provider"] == "gemini"
        assert payload["model"] == "gemini-2.5-flash"
        assert payload["prompt_version"] == ai_analyst.AI_PROMPT_VERSION

    @pytest.mark.unit
    def test_normalize_ai_response_uses_parsed_payload_when_available(self):
        class DummyResponse:
            parsed = {
                "sentiment_score": 55,
                "sentiment_label": "NOTR",
                "summary": ["ok"],
                "explanation": "parsed payload",
                "key_levels": {"support": ["1"], "resistance": ["2"]},
                "risk_level": "Orta",
            }
            text = None

        normalized = ai_analyst._normalize_ai_response(
            response=DummyResponse(),
            provider="gemini",
            model_name="gemini-2.5-flash",
            backend="google.genai",
        )
        payload = json.loads(normalized)

        assert payload["provider"] == "gemini"
        assert payload["model"] == "gemini-2.5-flash"
        assert payload["backend"] == "google.genai"
        assert payload["explanation"] == "parsed payload"

    @pytest.mark.unit
    def test_normalize_ai_response_extracts_json_from_mixed_text(self):
        response_text = (
            "Analiz tamamlandi.\n"
            "```json\n"
            '{"sentiment_score":55,"sentiment_label":"NOTR","summary":["ok"],'
            '"explanation":"mixed text","key_levels":{"support":["1"],"resistance":["2"]},'
            '"risk_level":"Orta"}\n'
            "```\n"
            "Bitti."
        )

        normalized = ai_analyst._normalize_ai_response(
            response=response_text,
            provider="gemini",
            model_name="gemini-2.5-flash",
            backend="google.genai",
        )
        payload = json.loads(normalized)

        assert payload["provider"] == "gemini"
        assert payload["explanation"] == "mixed text"

    @pytest.mark.unit
    def test_normalize_ai_response_extracts_json_from_candidate_parts(self):
        class DummyPart:
            text = (
                '{"sentiment_score":55,"sentiment_label":"NOTR","summary":["ok"],'
                '"explanation":"candidate text","key_levels":{"support":["1"],"resistance":["2"]},'
                '"risk_level":"Orta"}'
            )

        class DummyContent:
            parts = [DummyPart()]

        class DummyCandidate:
            content = DummyContent()

        class DummyResponse:
            parsed = None
            text = ""
            candidates = [DummyCandidate()]

        normalized = ai_analyst._normalize_ai_response(
            response=DummyResponse(),
            provider="gemini",
            model_name="gemini-2.5-flash",
            backend="google.genai",
        )
        payload = json.loads(normalized)

        assert payload["provider"] == "gemini"
        assert payload["explanation"] == "candidate text"

    @pytest.mark.unit
    def test_normalize_ai_response_reports_empty_candidate_diagnostics(self):
        class DummyCandidate:
            finish_reason = "SAFETY"
            finish_message = "blocked"
            content = type("DummyContent", (), {"parts": []})()

        class DummyResponse:
            parsed = None
            text = None
            prompt_feedback = "safety block"
            candidates = [DummyCandidate()]

        with pytest.raises(ai_analyst.AIResponseSchemaError) as exc:
            ai_analyst._normalize_ai_response(
                response=DummyResponse(),
                provider="gemini",
                model_name="gemini-2.5-flash",
                backend="google.genai",
            )

        message = str(exc.value)
        assert "Gemini API bos yanit dondurdu" in message
        assert '"finish_reason": "SAFETY"' in message
        assert '"prompt_feedback": "safety block"' in message
        assert exc.value.error_code == "empty_response"

    @pytest.mark.unit
    def test_analyze_with_gemini_embeds_multitimeframe_payload_in_prompt(self, monkeypatch):
        monkeypatch.setattr(ai_analyst.settings, "ai_provider", "gemini")
        monkeypatch.setattr(ai_analyst.settings, "ai_model", "gemini-2.5-flash")
        monkeypatch.setattr(ai_analyst.settings, "ai_enable_fallback", False)
        monkeypatch.setattr(ai_analyst.settings, "ai_fallback_model", None)
        monkeypatch.setattr(ai_analyst.settings, "gemini_api_key", "test-key")
        monkeypatch.setattr(ai_analyst, "gemini_client", object())
        monkeypatch.setattr(ai_analyst, "legacy_genai", None)
        monkeypatch.setattr(
            ai_analyst, "_ensure_gemini_backend", lambda: ("test-key", "google.genai")
        )

        prompts: list[str] = []

        def fake_generate(model_name: str, prompt: str, backend: str):
            prompts.append(prompt)
            return json.dumps(
                {
                    "sentiment_score": 55,
                    "sentiment_label": "NOTR",
                    "summary": ["ok"],
                    "explanation": "context captured",
                    "key_levels": {"support": ["1"], "resistance": ["2"]},
                    "risk_level": "Orta",
                }
            )

        monkeypatch.setattr(ai_analyst, "_generate_model_response", fake_generate)

        technical_data = {
            "symbol": "THYAO",
            "market_type": "BIST",
            "strategy": "HUNTER",
            "signal_type": "AL",
            "special_tag": "BELES",
            "trigger_rule": ["1D", "2W-FRI", "ME"],
            "matched_timeframes": [
                {"code": "1D", "label": "GUNLUK"},
                {"code": "2W-FRI", "label": "2 HAFTALIK"},
                {"code": "ME", "label": "1 AYLIK"},
            ],
            "indicator_order": ["RSI", "RSI_Fast", "MACD"],
            "timeframes": [
                {
                    "code": "1D",
                    "label": "GUNLUK",
                    "signal_status": "AL",
                    "price": 100,
                    "primary_score_label": "Dip Skoru",
                    "primary_score": "7/7",
                    "secondary_score_label": "Tepe Skoru",
                    "secondary_score": "1/10",
                    "active_indicators": "15/15",
                    "indicators": {"RSI": 20, "RSI_Fast": 18, "MACD": -1.2},
                }
            ],
        }

        response = ai_analyst.analyze_with_gemini(
            symbol="THYAO",
            scenario_name="💎💎💎 HUNTER: BELEŞ (TARİHİ FIRSAT)!",
            signal_type="AL",
            technical_data=technical_data,
            save_to_db=False,
        )

        payload = json.loads(response)
        assert payload["error"] is None
        assert payload["prompt_version"] == ai_analyst.AI_PROMPT_VERSION
        assert prompts
        assert "TEKNIK BAGLAM (coklu timeframe)" in prompts[0]
        assert f"Prompt Version: {ai_analyst.AI_PROMPT_VERSION}" in prompts[0]
        assert "Notr Olay Kodu: VALUE_COMPRESSION_EXTREME_BUY" in prompts[0]
        assert "Tetik Kurali: 1D, 2W-FRI, ME" in prompts[0]
        assert "Eslesen Periyotlar: GUNLUK (1D), 2 HAFTALIK (2W-FRI), 1 AYLIK (ME)" in prompts[0]
        assert "JSON Teknik Veri" not in prompts[0]
        assert "Gosterge=RSI=20" in prompts[0]
        assert '"special_tag": "VALUE_COMPRESSION_EXTREME_BUY"' not in prompts[0]
        assert "BELEÅ" not in prompts[0]
        assert "TARÄ°HÄ° FIRSAT" not in prompts[0]

    @pytest.mark.unit
    def test_truncate_news_context_limits_lines_and_length(self):
        news_text = "\n".join(f"Baslik {index} - {'x' * 50}" for index in range(1, 12))

        truncated = ai_analyst._truncate_news_context(news_text, max_lines=3, max_chars=120)

        assert truncated.count("\n") <= 2
        assert len(truncated) <= 120


def test_save_analysis_to_db_persists_structured_metadata(monkeypatch):
    captured: dict = {}

    class DummyAnalysis:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.id = 77

    class DummySession:
        def add(self, obj):
            captured["object"] = obj

        def commit(self):
            captured["committed"] = True

    @contextmanager
    def fake_get_session():
        yield DummySession()

    monkeypatch.setattr("db_session.get_session", fake_get_session)
    monkeypatch.setattr("models.AIAnalysis", DummyAnalysis)

    analysis_text = json.dumps(
        {
            "sentiment_score": 63,
            "sentiment_label": "AL",
            "confidence_score": 71,
            "risk_level": "Orta",
            "summary": ["ok"],
            "explanation": "kaydedildi",
            "technical_view": {
                "bias": "AL",
                "strength": 64,
                "conflicts": [],
            },
            "news_view": {
                "bias": "NOTR",
                "strength": 30,
                "headline_count": 2,
            },
            "key_levels": {
                "support": ["1"],
                "resistance": ["2"],
            },
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "backend": "google.genai",
            "prompt_version": ai_analyst.AI_PROMPT_VERSION,
            "error_code": None,
        }
    )

    analysis_id = ai_analyst.save_analysis_to_db(
        symbol="THYAO",
        market_type="BIST",
        scenario_name="TEST",
        signal_type="AL",
        analysis_text=analysis_text,
        technical_data={"foo": "bar"},
        latency_ms=321,
    )

    assert analysis_id == 77
    assert captured["committed"] is True
    assert captured["kwargs"]["provider"] == "gemini"
    assert captured["kwargs"]["model"] == "gemini-2.5-flash"
    assert captured["kwargs"]["backend"] == "google.genai"
    assert captured["kwargs"]["prompt_version"] == ai_analyst.AI_PROMPT_VERSION
    assert captured["kwargs"]["sentiment_score"] == 63
    assert captured["kwargs"]["sentiment_label"] == "AL"
    assert captured["kwargs"]["confidence_score"] == 71
    assert captured["kwargs"]["risk_level"] == "Orta"
    assert captured["kwargs"]["technical_bias"] == "AL"
    assert captured["kwargs"]["technical_strength"] == 64
    assert captured["kwargs"]["news_bias"] == "NOTR"
    assert captured["kwargs"]["news_strength"] == 30
    assert captured["kwargs"]["headline_count"] == 2
    assert captured["kwargs"]["latency_ms"] == 321
