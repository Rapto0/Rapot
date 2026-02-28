"""
AI analyst module.
Uses Google Gemini for technical + news assisted analysis.
"""

import json
import threading
import time
import unicodedata
from typing import Any

try:
    from google import genai as google_genai
except Exception:  # pragma: no cover
    google_genai = None
try:
    from google.genai import types as google_genai_types
except Exception:  # pragma: no cover
    google_genai_types = None

from ai_schema import (
    AIAnalysisPayload,
    AIResponseSchemaError,
    build_ai_error_payload,
    dump_ai_payload,
    parse_ai_response,
)
from logger import get_logger
from settings import settings

legacy_genai = None
gemini_client = None
gemini_backend = "none"
_gemini_client_key: str | None = None

logger = get_logger(__name__)

# AI timeout from settings.py
AI_TIMEOUT = settings.ai_timeout
AI_PROMPT_VERSION = "v4-neutral-rule-context"
AI_RESPONSE_SCHEMA = AIAnalysisPayload.model_json_schema()

_SPECIAL_TAG_PROMPT_LABELS = {
    "BELES": "VALUE_COMPRESSION_EXTREME_BUY",
    "COK_UCUZ": "VALUE_COMPRESSION_BUY",
    "PAHALI": "VALUE_EXTENSION_SELL",
    "FAHIS_FIYAT": "VALUE_EXTENSION_EXTREME_SELL",
}

_SIGNAL_DIRECTION_PROMPT_LABELS = {
    "AL": "LONG_BIAS",
    "SAT": "SHORT_BIAS",
}


def _normalize_ai_provider(value: str | None) -> str:
    provider = (value or "gemini").strip().lower()
    aliases = {
        "google": "gemini",
        "google-genai": "gemini",
        "google_genai": "gemini",
    }
    return aliases.get(provider, provider)


def get_ai_runtime_settings() -> dict[str, Any]:
    return {
        "provider": _normalize_ai_provider(settings.ai_provider),
        "model": (settings.ai_model or "gemini-2.5-flash").strip(),
        "enable_fallback": bool(settings.ai_enable_fallback),
        "fallback_model": (settings.ai_fallback_model or "").strip() or None,
        "temperature": settings.ai_temperature,
        "thinking_budget": settings.ai_thinking_budget,
        "max_output_tokens": settings.ai_max_output_tokens,
        "timeout": settings.ai_timeout,
    }


def build_model_candidates(
    primary_model: str | None = None,
    fallback_model: str | None = None,
    enable_fallback: bool | None = None,
) -> list[str]:
    runtime = get_ai_runtime_settings()
    should_use_fallback = (
        enable_fallback if enable_fallback is not None else runtime["enable_fallback"]
    )
    models = [(primary_model or runtime["model"] or "").strip()]
    if should_use_fallback:
        models.append(
            (
                fallback_model if fallback_model is not None else runtime["fallback_model"] or ""
            ).strip()
        )

    unique_models: list[str] = []
    seen: set[str] = set()
    for model_name in models:
        if model_name and model_name not in seen:
            unique_models.append(model_name)
            seen.add(model_name)
    return unique_models


def _get_generation_config(backend: str | None = None) -> Any:
    runtime = get_ai_runtime_settings()
    if backend == "google.genai":
        if google_genai_types is not None:
            thinking_config = None
            if hasattr(google_genai_types, "ThinkingConfig"):
                thinking_config = google_genai_types.ThinkingConfig(
                    thinking_budget=runtime["thinking_budget"]
                )
            return google_genai_types.GenerateContentConfig(
                temperature=runtime["temperature"],
                max_output_tokens=runtime["max_output_tokens"],
                response_mime_type="application/json",
                response_schema=AIAnalysisPayload,
                thinking_config=thinking_config,
            )
        return {
            "temperature": runtime["temperature"],
            "max_output_tokens": runtime["max_output_tokens"],
            "response_mime_type": "application/json",
            "response_schema": AIAnalysisPayload,
            "thinking_config": {"thinking_budget": runtime["thinking_budget"]},
        }
    return {
        "temperature": runtime["temperature"],
        "max_output_tokens": runtime["max_output_tokens"],
        "response_mime_type": "application/json",
        "response_schema": AI_RESPONSE_SCHEMA,
    }


def _ensure_gemini_backend() -> tuple[str | None, str]:
    global gemini_client, legacy_genai, gemini_backend, _gemini_client_key

    api_key = settings.gemini_api_key
    if not api_key:
        return None, "none"

    if _gemini_client_key == api_key and (gemini_client is not None or legacy_genai is not None):
        return api_key, gemini_backend

    gemini_client = None
    legacy_genai = None
    gemini_backend = "none"
    _gemini_client_key = api_key

    if google_genai is not None:
        gemini_client = google_genai.Client(api_key=api_key)
        gemini_backend = "google.genai"
        return api_key, gemini_backend

    try:
        import google.generativeai as legacy_genai_module

        legacy_genai = legacy_genai_module
        legacy_genai.configure(api_key=api_key)
        gemini_backend = "google.generativeai"
    except Exception:
        logger.warning("Gemini SDK bulunamadi (google.genai / google.generativeai).")

    return api_key, gemini_backend


def _generate_with_google_genai(model_name: str, prompt: str) -> Any:
    if gemini_client is None:
        raise RuntimeError("Gemini client hazir degil")

    generation_config = _get_generation_config("google.genai")

    try:
        response = gemini_client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=generation_config,
        )
    except TypeError:
        response = gemini_client.models.generate_content(model=model_name, contents=prompt)

    return response


def _generate_with_legacy_genai(model_name: str, prompt: str) -> Any:
    if legacy_genai is None:
        raise RuntimeError("Legacy Gemini client hazir degil")

    generation_config = _get_generation_config("google.generativeai")

    try:
        model = legacy_genai.GenerativeModel(model_name, generation_config=generation_config)
    except TypeError:
        model = legacy_genai.GenerativeModel(model_name)

    try:
        response = model.generate_content(prompt, generation_config=generation_config)
    except TypeError:
        response = model.generate_content(prompt)

    return response


def _generate_model_response(model_name: str, prompt: str, backend: str) -> Any:
    if backend == "google.genai":
        return _generate_with_google_genai(model_name, prompt)
    if backend == "google.generativeai":
        return _generate_with_legacy_genai(model_name, prompt)
    raise RuntimeError("Gemini backend unavailable")


def _extract_json_object(text: str) -> str:
    clean_text = text.replace("```json", "").replace("```", "").strip()
    if not clean_text:
        raise AIResponseSchemaError("Gemini API bos yanit dondurdu", "empty_response")

    try:
        json.loads(clean_text)
        return clean_text
    except (TypeError, json.JSONDecodeError):
        pass

    start = clean_text.find("{")
    end = clean_text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise AIResponseSchemaError("Gemini API bos yanit dondurdu", "invalid_json")

    candidate = clean_text[start : end + 1].strip()
    try:
        json.loads(candidate)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AIResponseSchemaError("AI yaniti gecerli JSON degil", "invalid_json") from exc
    return candidate


def _response_field(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _response_diagnostics(response: Any) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "has_parsed": getattr(response, "parsed", None) is not None,
        "text_length": None,
        "candidate_count": 0,
        "candidates": [],
        "prompt_feedback": None,
        "usage_metadata": None,
    }

    response_text = _response_field(response, "text")
    if isinstance(response_text, str):
        diagnostics["text_length"] = len(response_text)

    prompt_feedback = _response_field(response, "prompt_feedback")
    if prompt_feedback is not None:
        diagnostics["prompt_feedback"] = str(prompt_feedback)

    usage_metadata = _response_field(response, "usage_metadata")
    if usage_metadata is not None:
        diagnostics["usage_metadata"] = str(usage_metadata)

    candidates = _response_field(response, "candidates", []) or []
    diagnostics["candidate_count"] = len(candidates)
    for candidate in candidates:
        content = _response_field(candidate, "content")
        parts = _response_field(content, "parts", []) or []
        part_descriptions: list[dict[str, Any]] = []
        for part in parts:
            part_text = _response_field(part, "text")
            inline_data = _response_field(part, "inline_data")
            function_call = _response_field(part, "function_call")
            part_descriptions.append(
                {
                    "has_text": bool(part_text),
                    "text_length": len(part_text) if isinstance(part_text, str) else 0,
                    "has_inline_data": inline_data is not None,
                    "has_function_call": function_call is not None,
                }
            )

        diagnostics["candidates"].append(
            {
                "finish_reason": str(_response_field(candidate, "finish_reason", "")),
                "finish_message": _response_field(candidate, "finish_message"),
                "parts_count": len(parts),
                "parts": part_descriptions,
            }
        )

    return diagnostics


def _compact_response_diagnostics(response: Any) -> str:
    diagnostics = _response_diagnostics(response)
    first_candidate = diagnostics["candidates"][0] if diagnostics["candidates"] else {}
    summary = {
        "has_parsed": diagnostics["has_parsed"],
        "text_length": diagnostics["text_length"],
        "candidate_count": diagnostics["candidate_count"],
        "finish_reason": first_candidate.get("finish_reason") or None,
        "finish_message": first_candidate.get("finish_message") or None,
        "parts_count": first_candidate.get("parts_count") or 0,
        "prompt_feedback": diagnostics["prompt_feedback"],
    }
    return json.dumps(summary, ensure_ascii=False, default=str)


def _extract_response_payload(response: Any) -> dict[str, Any] | str:
    parsed = getattr(response, "parsed", None)
    if parsed is not None:
        if isinstance(parsed, dict):
            return parsed
        if hasattr(parsed, "model_dump"):
            return parsed.model_dump(mode="json")

    if isinstance(response, dict):
        return response

    candidates = getattr(response, "candidates", None)
    if candidates:
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) if content is not None else None
            if parts is None and isinstance(content, dict):
                parts = content.get("parts")
            for part in parts or []:
                part_text = getattr(part, "text", None)
                if part_text is None and isinstance(part, dict):
                    part_text = part.get("text")
                if part_text:
                    return _extract_json_object(str(part_text))

    response_text = getattr(response, "text", None) if not isinstance(response, str) else response
    if response_text is None:
        raise AIResponseSchemaError(
            f"Gemini API bos yanit dondurdu | {_compact_response_diagnostics(response)}",
            "empty_response",
        )
    return _extract_json_object(str(response_text))


def _normalize_ai_response(response: Any, provider: str, model_name: str, backend: str) -> str:
    payload = parse_ai_response(_extract_response_payload(response))
    payload.provider = payload.provider or provider
    payload.model = payload.model or model_name
    payload.backend = payload.backend or backend
    payload.prompt_version = payload.prompt_version or AI_PROMPT_VERSION

    return dump_ai_payload(payload)


def _error_response(
    error: str,
    error_code: str,
    provider: str | None = None,
    model_name: str | None = None,
    backend: str | None = None,
    summary: str = "Hata olustu.",
) -> str:
    return build_ai_error_payload(
        error=error,
        error_code=error_code,
        provider=provider,
        model_name=model_name,
        backend=backend,
        prompt_version=AI_PROMPT_VERSION,
        summary=summary,
    )


def _sanitize_prompt_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = text.encode("ascii", "ignore").decode("ascii")
    return " ".join(text.split()) or "Yok"


def _normalize_prompt_special_tag(value: Any) -> str:
    raw_value = _sanitize_prompt_text(value).upper().replace("-", "_").replace(" ", "_")
    if raw_value in _SPECIAL_TAG_PROMPT_LABELS:
        return _SPECIAL_TAG_PROMPT_LABELS[raw_value]
    return raw_value or "STANDARD_SIGNAL"


def _build_prompt_signal_context(
    scenario_name: str,
    signal_type: str,
    technical_data: dict[str, Any],
) -> str:
    strategy = _sanitize_prompt_text(technical_data.get("strategy") or "STANDARD")
    neutral_direction = _SIGNAL_DIRECTION_PROMPT_LABELS.get(
        signal_type, _sanitize_prompt_text(signal_type)
    )
    source = (
        "rule_engine_special_signal" if technical_data.get("special_tag") else "rule_engine_signal"
    )
    neutral_event_code = (
        _normalize_prompt_special_tag(technical_data.get("special_tag"))
        if technical_data.get("special_tag")
        else _sanitize_prompt_text(scenario_name).upper().replace(" ", "_")
    )

    return (
        "SISTEM BAGLAMI:\n"
        f"- Prompt Version: {AI_PROMPT_VERSION}\n"
        f"- Kaynak: {source}\n"
        f"- Strateji: {strategy}\n"
        f"- Notr Olay Kodu: {neutral_event_code}\n"
        f"- Yon Egilimi: {neutral_direction}\n"
    )


def _build_prompt_technical_payload(technical_data: dict[str, Any]) -> dict[str, Any]:
    prompt_payload = dict(technical_data)
    if "special_tag" in prompt_payload:
        prompt_payload["special_tag"] = _normalize_prompt_special_tag(
            prompt_payload.get("special_tag")
        )
    if "signal_type" in prompt_payload:
        prompt_payload["signal_type"] = _SIGNAL_DIRECTION_PROMPT_LABELS.get(
            str(prompt_payload.get("signal_type") or "").upper(),
            _sanitize_prompt_text(prompt_payload.get("signal_type")),
        )
    if "scenario_name" in prompt_payload:
        prompt_payload["scenario_name"] = _sanitize_prompt_text(prompt_payload.get("scenario_name"))
    return prompt_payload


def _format_rich_timeframe_summary(timeframe: dict[str, Any]) -> str:
    status = timeframe.get("signal_status") or "YOK"
    price = timeframe.get("price", "Yok")
    primary_score_label = timeframe.get("primary_score_label") or "Birincil Skor"
    secondary_score_label = timeframe.get("secondary_score_label") or "Ikincil Skor"
    primary_score = timeframe.get("primary_score", "Yok")
    secondary_score = timeframe.get("secondary_score", "Yok")
    active_indicators = timeframe.get("active_indicators", "Yok")
    raw_score = timeframe.get("raw_score")
    raw_score_text = f" | Ham Skor: {raw_score}" if raw_score else ""
    return (
        f"- {timeframe.get('code', 'YOK')} / {timeframe.get('label', 'Yok')}: "
        f"Durum={status}, Fiyat={price}, "
        f"{primary_score_label}={primary_score}, "
        f"{secondary_score_label}={secondary_score}, "
        f"Aktif={active_indicators}{raw_score_text}"
    )


def _select_prompt_timeframes(technical_data: dict[str, Any]) -> list[dict[str, Any]]:
    timeframes = list(technical_data.get("timeframes", []))
    if not timeframes:
        return []

    matched_codes = {
        str(timeframe.get("code"))
        for timeframe in technical_data.get("matched_timeframes", [])
        if timeframe.get("code")
    }
    if matched_codes:
        selected = [timeframe for timeframe in timeframes if timeframe.get("code") in matched_codes]
        if selected:
            return selected

    return timeframes[:3]


def _compact_indicator_snapshot(
    timeframe: dict[str, Any],
    indicator_order: list[str],
    limit: int = 4,
) -> str:
    indicators = timeframe.get("indicators") or {}
    if not isinstance(indicators, dict) or not indicators:
        return "Yok"

    preferred = ["RSI", "RSI_Fast", "MACD", "W%R", "CCI", "ROC", "RSI2", "BBP", "CMO"]
    selected_keys: list[str] = []
    for key in preferred + indicator_order:
        if key in indicators and key not in selected_keys:
            selected_keys.append(key)
        if len(selected_keys) >= limit:
            break

    parts = []
    for key in selected_keys:
        value = indicators.get(key)
        formatted = f"{value:.2f}" if isinstance(value, float) else str(value)
        parts.append(f"{key}={formatted}")
    return ", ".join(parts) if parts else "Yok"


def _truncate_news_context(
    news_context: str | None, max_lines: int = 6, max_chars: int = 900
) -> str:
    if not news_context:
        return "Haber verisi yok veya cekilemedi. Sadece teknige odaklan."

    lines = [line.strip() for line in str(news_context).splitlines() if line.strip()]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    return text or "Haber verisi yok veya cekilemedi. Sadece teknige odaklan."


def _build_technical_context_prompt(technical_data: dict[str, Any]) -> str:
    if technical_data.get("timeframes") and technical_data.get("strategy"):
        prompt_technical_data = _build_prompt_technical_payload(technical_data)
        trigger_rule = technical_data.get("trigger_rule") or []
        matched_timeframes = technical_data.get("matched_timeframes") or []
        matched_labels = [
            f"{timeframe.get('label', timeframe.get('code', 'YOK'))} ({timeframe.get('code', 'YOK')})"
            for timeframe in matched_timeframes
        ]
        rule_label = "Tetik Kurali" if technical_data.get("special_tag") else "Analiz Periyotlari"
        indicator_order = list(prompt_technical_data.get("indicator_order", []))
        selected_timeframes = _select_prompt_timeframes(prompt_technical_data)
        timeframe_blocks = []
        for timeframe in selected_timeframes:
            summary = _format_rich_timeframe_summary(timeframe)
            indicators = _compact_indicator_snapshot(timeframe, indicator_order)
            timeframe_blocks.append(f"{summary} | Gosterge={indicators}")

        return (
            "TEKNIK BAGLAM (coklu timeframe):\n"
            f"- Strateji: {prompt_technical_data.get('strategy', 'Yok')}\n"
            f"- Ozel Etiket: {prompt_technical_data.get('special_tag', 'Yok')}\n"
            f"- Sinyal Yonu: {prompt_technical_data.get('signal_type', 'Yok')}\n"
            f"- {rule_label}: {', '.join(trigger_rule) if trigger_rule else 'Yok'}\n"
            f"- Eslesen Periyotlar: {', '.join(matched_labels) if matched_labels else 'Yok'}\n"
            "Secili Periyot Ozetleri:\n"
            f"{chr(10).join(timeframe_blocks)}\n"
            "Bu veri yapisinda trigger_rule ve matched_timeframes alanlari ozel sinyalin hangi timeframe"
            " kesisiminden geldigini gosterir. Ozel etiket adlarini otomatik firsat/tehlike kabul etme;"
            " tek bir timeframe yerine tum baglami birlikte ve bagimsiz yorumla."
        )

    return (
        "GUNLUK Teknik Veriler:\n"
        f"- Fiyat: {technical_data.get('PRICE', 'Yok')}\n"
        f"- RSI (14): {technical_data.get('RSI', 'Yok')}\n"
        f"- MACD: {technical_data.get('MACD', 'Yok')}\n"
    )


def save_analysis_to_db(
    symbol: str,
    market_type: str,
    scenario_name: str,
    signal_type: str,
    analysis_text: str,
    technical_data: dict[str, Any] | None = None,
    signal_id: int | None = None,
    latency_ms: int | None = None,
) -> int | None:
    """
    Save AI analysis to the database.
    """
    try:
        from db_session import get_session
        from models import AIAnalysis

        analysis_metadata = extract_analysis_metadata(analysis_text)
        with get_session() as session:
            analysis = AIAnalysis(
                signal_id=signal_id,
                symbol=symbol,
                market_type=market_type,
                scenario_name=scenario_name,
                signal_type=signal_type,
                analysis_text=analysis_text,
                technical_data=json.dumps(technical_data) if technical_data else None,
                provider=analysis_metadata.get("provider"),
                model=analysis_metadata.get("model"),
                backend=analysis_metadata.get("backend"),
                prompt_version=analysis_metadata.get("prompt_version"),
                sentiment_score=analysis_metadata.get("sentiment_score"),
                sentiment_label=analysis_metadata.get("sentiment_label"),
                confidence_score=analysis_metadata.get("confidence_score"),
                risk_level=analysis_metadata.get("risk_level"),
                technical_bias=analysis_metadata.get("technical_bias"),
                technical_strength=analysis_metadata.get("technical_strength"),
                news_bias=analysis_metadata.get("news_bias"),
                news_strength=analysis_metadata.get("news_strength"),
                headline_count=analysis_metadata.get("headline_count"),
                latency_ms=latency_ms,
                error_code=analysis_metadata.get("error_code"),
            )
            session.add(analysis)
            session.commit()
            logger.info(f"AI analizi kaydedildi: {symbol} (ID: {analysis.id})")
            return analysis.id
    except Exception as e:
        logger.error(f"AI analizi kaydetme hatasi ({symbol}): {e}")
        return None


def analyze_with_gemini(
    symbol: str,
    scenario_name: str,
    signal_type: str,
    technical_data: dict[str, Any],
    news_context: str | None = None,
    timeout: int = AI_TIMEOUT,
    market_type: str = "BIST",
    save_to_db: bool = True,
    signal_id: int | None = None,
) -> str:
    """
    Analyze technical and news context with the configured AI model.
    """
    runtime = get_ai_runtime_settings()
    provider = runtime["provider"]
    primary_model = runtime["model"]
    started_at = time.perf_counter()

    if provider != "gemini":
        return _error_response(
            error=f"Desteklenmeyen AI provider: {provider}",
            error_code="unsupported_provider",
            provider=provider,
            model_name=primary_model,
            summary="Desteklenmeyen AI provider.",
        )

    api_key, backend = _ensure_gemini_backend()
    if not api_key:
        logger.warning("GEMINI_API_KEY bulunamadi!")
        return _error_response(
            error="API Key eksik",
            error_code="missing_api_key",
            provider=provider,
            model_name=primary_model,
            backend=backend,
            summary="Analiz yapilamadi.",
        )

    if gemini_client is None and legacy_genai is None:
        return _error_response(
            error="Gemini SDK eksik",
            error_code="sdk_missing",
            provider=provider,
            model_name=primary_model,
            backend=backend,
            summary="Gemini SDK bulunamadi.",
        )

    result: dict[str, Any] = {"text": None, "error": None, "error_code": None, "model": None}

    def _generate():
        try:
            news_text = _truncate_news_context(news_context)

            signal_context = _build_prompt_signal_context(
                scenario_name, signal_type, technical_data
            )
            technical_context = _build_technical_context_prompt(technical_data)

            prompt = f"""
            Sen uzman bir borsa stratejistisin. Elimde teknik olarak '{signal_type}' sinyali veren bir varlik var.
            Bunu detayli analiz et ve JSON formatinda yanitla.

            Varlik: {symbol}
            {signal_context}

            {technical_context}

            GUNCEL HABER AKISI:
            {news_text}

            GOREVIN:
            - Ozel etiketleri pazarlama dili olarak degil, kural motoru siniflandirmasi olarak ele al.
            - Teknik veri ile haber akisi celisiyorsa bunu acikca belirt ve confidence skorunu dusur.
            - Sadece saglanan teknik veri ve haber akisi uzerinden bagimsiz yorum yap.
            - Sadece gecerli JSON dondur. Markdown, aciklama metni veya code fence kullanma.
            - JSON mutlaka su alanlari icersin:
              sentiment_score, sentiment_label, confidence_score, summary, explanation,
              technical_view, news_view, key_levels, risk_level
            - summary en fazla 3 kisa madde olsun.
            - key_levels.support ve key_levels.resistance en fazla 2 seviye olsun.
            """

            last_error: Exception | None = None
            last_error_code = "generation_error"
            for model_name in build_model_candidates():
                diagnostics: dict[str, Any] = {}
                try:
                    response_payload = _generate_model_response(model_name, prompt, backend)
                    if not response_payload:
                        raise AIResponseSchemaError(
                            "Gemini API bos yanit dondurdu", "empty_response"
                        )

                    diagnostics = _response_diagnostics(response_payload)

                    result["text"] = _normalize_ai_response(
                        response=response_payload,
                        provider=provider,
                        model_name=model_name,
                        backend=backend,
                    )
                    result["model"] = model_name
                    logger.info(
                        "AI analizi uretildi: %s via %s/%s (%s)",
                        symbol,
                        provider,
                        model_name,
                        backend,
                    )
                    return
                except AIResponseSchemaError as e:
                    last_error = e
                    last_error_code = e.error_code
                    logger.warning(
                        "AI model denemesi schema hatasi (%s, %s/%s): %s [%s]",
                        symbol,
                        provider,
                        model_name,
                        e,
                        e.error_code,
                    )
                    logger.warning(
                        "AI response diagnostics (%s, %s/%s): %s",
                        symbol,
                        provider,
                        model_name,
                        json.dumps(diagnostics, ensure_ascii=False, default=str),
                    )
                except Exception as e:
                    last_error = e
                    last_error_code = "generation_error"
                    logger.warning(
                        "AI model denemesi basarisiz (%s, %s/%s): %s",
                        symbol,
                        provider,
                        model_name,
                        e,
                    )

            if last_error is not None:
                if isinstance(last_error, AIResponseSchemaError):
                    raise last_error
                raise AIResponseSchemaError(str(last_error), last_error_code)
            raise RuntimeError("Model aday listesi bos")

        except AIResponseSchemaError as e:
            result["error"] = str(e)
            result["error_code"] = e.error_code
            logger.error(f"Gemini schema hatasi ({symbol}): {e} [{e.error_code}]")
        except Exception as e:
            result["error"] = str(e)
            result["error_code"] = "generation_error"
            logger.error(f"Gemini API hatasi ({symbol}): {e}")

    thread = threading.Thread(target=_generate, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        logger.warning(f"AI analizi timeout ({symbol}, {timeout}s)")
        return _error_response(
            error="Timeout",
            error_code="timeout",
            provider=provider,
            model_name=primary_model,
            backend=backend,
            summary="Zaman asimi.",
        )

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    if result["error"]:
        return _error_response(
            error=result["error"],
            error_code=result["error_code"] or "generation_error",
            provider=provider,
            model_name=result["model"] or primary_model,
            backend=backend,
            summary="Hata olustu.",
        )

    analysis_text = result["text"] or _error_response(
        error="Bos yanit",
        error_code="empty_response",
        provider=provider,
        model_name=result["model"] or primary_model,
        backend=backend,
        summary="Bos yanit.",
    )

    if save_to_db and result["text"]:
        save_analysis_to_db(
            symbol=symbol,
            market_type=market_type,
            scenario_name=scenario_name,
            signal_type=signal_type,
            analysis_text=analysis_text,
            technical_data=technical_data,
            signal_id=signal_id,
            latency_ms=latency_ms,
        )

    return analysis_text


def extract_analysis_metadata(analysis_text: str) -> dict[str, Any]:
    """Normalize stored AI JSON into DB-friendly metadata fields."""
    payload = parse_ai_response(analysis_text)
    return {
        "provider": payload.provider,
        "model": payload.model,
        "backend": payload.backend,
        "prompt_version": payload.prompt_version,
        "sentiment_score": payload.sentiment_score,
        "sentiment_label": payload.sentiment_label,
        "confidence_score": payload.confidence_score,
        "risk_level": payload.risk_level,
        "technical_bias": payload.technical_view.bias,
        "technical_strength": payload.technical_view.strength,
        "news_bias": payload.news_view.bias,
        "news_strength": payload.news_view.strength,
        "headline_count": payload.news_view.headline_count,
        "error_code": payload.error_code,
    }


def analyze_async(
    symbol: str,
    scenario_name: str,
    signal_type: str,
    technical_data: dict[str, Any],
    news_context: str | None = None,
    callback=None,
) -> threading.Thread:
    """
    Non-blocking AI analysis.
    """

    def _run():
        result = analyze_with_gemini(
            symbol, scenario_name, signal_type, technical_data, news_context
        )
        if callback:
            callback(result)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread
