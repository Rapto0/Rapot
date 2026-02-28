"""
Shared AI response schemas and normalization helpers.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

SentimentLabel = Literal["GUCLU AL", "AL", "NOTR", "SAT", "GUCLU SAT"]
RiskLevel = Literal["Dusuk", "Orta", "Yuksek"]
ErrorCode = Literal[
    "timeout",
    "invalid_json",
    "schema_validation",
    "empty_response",
    "unsupported_provider",
    "missing_api_key",
    "sdk_missing",
    "generation_error",
    "unknown",
]

_SENTIMENT_DEFAULT = "NOTR"
_RISK_DEFAULT = "Orta"
_SUMMARY_DEFAULT = "Ozet maddesi uretilemedi."
_EXPLANATION_DEFAULT = "Detayli aciklama uretilemedi."

_SENTIMENT_MAP = {
    "GUCLU AL": "GUCLU AL",
    "STRONG BUY": "GUCLU AL",
    "AL": "AL",
    "BUY": "AL",
    "NOTR": "NOTR",
    "NEUTRAL": "NOTR",
    "SAT": "SAT",
    "SELL": "SAT",
    "GUCLU SAT": "GUCLU SAT",
    "STRONG SELL": "GUCLU SAT",
}

_RISK_MAP = {
    "DUSUK": "Dusuk",
    "LOW": "Dusuk",
    "ORTA": "Orta",
    "MEDIUM": "Orta",
    "YUKSEK": "Yuksek",
    "HIGH": "Yuksek",
}

_ERROR_CODES: set[str] = {
    "timeout",
    "invalid_json",
    "schema_validation",
    "empty_response",
    "unsupported_provider",
    "missing_api_key",
    "sdk_missing",
    "generation_error",
    "unknown",
}


class AIResponseSchemaError(ValueError):
    def __init__(self, message: str, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code if error_code in _ERROR_CODES else "unknown"


def _normalize_token(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = text.encode("ascii", "ignore").decode("ascii")
    text = " ".join(text.upper().split())
    return text


def _coerce_bounded_int(value: Any, default: int, minimum: int = 0, maximum: int = 100) -> int:
    try:
        if value is None or value == "":
            raise ValueError
        number = int(round(float(value)))
        return max(minimum, min(maximum, number))
    except (TypeError, ValueError):
        return default


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        return []

    normalized: list[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


class AIKeyLevels(BaseModel):
    support: list[str] = Field(default_factory=list)
    resistance: list[str] = Field(default_factory=list)

    @field_validator("support", "resistance", mode="before")
    @classmethod
    def _validate_level_list(cls, value: Any) -> list[str]:
        return _normalize_string_list(value)


class AITechnicalView(BaseModel):
    bias: SentimentLabel = _SENTIMENT_DEFAULT
    strength: int = Field(default=0, ge=0, le=100)
    conflicts: list[str] = Field(default_factory=list)

    @field_validator("bias", mode="before")
    @classmethod
    def _validate_bias(cls, value: Any) -> SentimentLabel:
        normalized = _SENTIMENT_MAP.get(_normalize_token(value), _SENTIMENT_DEFAULT)
        return normalized  # type: ignore[return-value]

    @field_validator("strength", mode="before")
    @classmethod
    def _validate_strength(cls, value: Any) -> int:
        return _coerce_bounded_int(value, default=0)

    @field_validator("conflicts", mode="before")
    @classmethod
    def _validate_conflicts(cls, value: Any) -> list[str]:
        return _normalize_string_list(value)


class AINewsView(BaseModel):
    bias: SentimentLabel = _SENTIMENT_DEFAULT
    strength: int = Field(default=0, ge=0, le=100)
    headline_count: int = Field(default=0, ge=0, le=100)

    @field_validator("bias", mode="before")
    @classmethod
    def _validate_bias(cls, value: Any) -> SentimentLabel:
        normalized = _SENTIMENT_MAP.get(_normalize_token(value), _SENTIMENT_DEFAULT)
        return normalized  # type: ignore[return-value]

    @field_validator("strength", "headline_count", mode="before")
    @classmethod
    def _validate_ints(cls, value: Any) -> int:
        return _coerce_bounded_int(value, default=0)


class AIAnalysisPayload(BaseModel):
    sentiment_score: int = Field(default=50, ge=0, le=100)
    sentiment_label: SentimentLabel = _SENTIMENT_DEFAULT
    confidence_score: int = Field(default=50, ge=0, le=100)
    risk_level: RiskLevel = _RISK_DEFAULT
    summary: list[str] = Field(default_factory=list)
    explanation: str = _EXPLANATION_DEFAULT
    key_levels: AIKeyLevels = Field(default_factory=AIKeyLevels)
    technical_view: AITechnicalView = Field(default_factory=AITechnicalView)
    news_view: AINewsView = Field(default_factory=AINewsView)
    provider: str | None = None
    model: str | None = None
    backend: str | None = None
    prompt_version: str | None = None
    error: str | None = None
    error_code: ErrorCode | None = None

    @field_validator("sentiment_score", "confidence_score", mode="before")
    @classmethod
    def _validate_scores(cls, value: Any) -> int:
        return _coerce_bounded_int(value, default=50)

    @field_validator("sentiment_label", mode="before")
    @classmethod
    def _validate_sentiment_label(cls, value: Any) -> SentimentLabel:
        normalized = _SENTIMENT_MAP.get(_normalize_token(value), _SENTIMENT_DEFAULT)
        return normalized  # type: ignore[return-value]

    @field_validator("risk_level", mode="before")
    @classmethod
    def _validate_risk_level(cls, value: Any) -> RiskLevel:
        normalized = _RISK_MAP.get(_normalize_token(value), _RISK_DEFAULT)
        return normalized  # type: ignore[return-value]

    @field_validator("summary", mode="before")
    @classmethod
    def _validate_summary(cls, value: Any) -> list[str]:
        summary = _normalize_string_list(value)
        return summary or [_SUMMARY_DEFAULT]

    @field_validator("explanation", mode="before")
    @classmethod
    def _validate_explanation(cls, value: Any) -> str:
        text = str(value or "").strip()
        return text or _EXPLANATION_DEFAULT

    @field_validator("error", mode="before")
    @classmethod
    def _validate_error(cls, value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    @field_validator("error_code", mode="before")
    @classmethod
    def _validate_error_code(cls, value: Any) -> ErrorCode | None:
        if value is None or value == "":
            return None
        normalized = str(value).strip().lower()
        if normalized not in _ERROR_CODES:
            normalized = "unknown"
        return normalized  # type: ignore[return-value]


def dump_ai_payload(payload: AIAnalysisPayload) -> str:
    return json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)


def parse_ai_payload(payload: dict[str, Any]) -> AIAnalysisPayload:
    try:
        return AIAnalysisPayload.model_validate(payload)
    except ValidationError as exc:
        raise AIResponseSchemaError(str(exc), "schema_validation") from exc


def parse_ai_response(ai_response: str | dict[str, Any]) -> AIAnalysisPayload:
    if isinstance(ai_response, dict):
        return parse_ai_payload(ai_response)

    try:
        raw_payload = json.loads(ai_response)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AIResponseSchemaError("AI yaniti gecerli JSON degil", "invalid_json") from exc

    if not isinstance(raw_payload, dict):
        raise AIResponseSchemaError("AI yaniti JSON object olmali", "schema_validation")

    return parse_ai_payload(raw_payload)


def build_ai_error_payload(
    *,
    error: str,
    error_code: str,
    provider: str | None = None,
    model_name: str | None = None,
    backend: str | None = None,
    prompt_version: str | None = None,
    summary: str = "Hata olustu.",
    explanation: str | None = None,
) -> str:
    payload = AIAnalysisPayload(
        error=error,
        error_code=error_code if error_code in _ERROR_CODES else "unknown",
        provider=provider,
        model=model_name,
        backend=backend,
        prompt_version=prompt_version,
        confidence_score=0,
        summary=[summary],
        explanation=explanation or summary,
    )
    return dump_ai_payload(payload)
