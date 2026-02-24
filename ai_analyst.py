"""
AI Analyst Modülü
Google Gemini kullanarak teknik analiz ve haber yorumlama.
"""

import json
import threading
from typing import Any

try:
    from google import genai as google_genai
except Exception:  # pragma: no cover
    google_genai = None

from logger import get_logger
from settings import settings

legacy_genai = None

logger = get_logger(__name__)

# Gemini API - settings.py'den credentials alınıyor
api_key = settings.gemini_api_key

gemini_client = None
gemini_backend = "none"

if api_key:
    if google_genai is not None:
        gemini_client = google_genai.Client(api_key=api_key)
        gemini_backend = "google.genai"
    else:
        try:
            import google.generativeai as legacy_genai_module

            legacy_genai = legacy_genai_module
            legacy_genai.configure(api_key=api_key)
            gemini_backend = "google.generativeai"
        except Exception:
            logger.warning("Gemini SDK bulunamadi (google.genai / google.generativeai).")
else:
    logger.warning("GEMINI_API_KEY bulunamadi!")

# AI analizi için timeout - settings.py'den alınıyor
AI_TIMEOUT = settings.ai_timeout


def save_analysis_to_db(
    symbol: str,
    market_type: str,
    scenario_name: str,
    signal_type: str,
    analysis_text: str,
    technical_data: dict[str, Any] | None = None,
    signal_id: int | None = None,
) -> int | None:
    """
    AI analizini veritabanına kaydeder.

    Args:
        symbol: Sembol
        market_type: Piyasa türü (BIST/Kripto)
        scenario_name: Senaryo adı
        signal_type: Sinyal türü (AL/SAT)
        analysis_text: AI tarafından üretilen analiz metni
        technical_data: Teknik göstergeler (opsiyonel)
        signal_id: İlişkili sinyal ID'si (opsiyonel)

    Returns:
        Oluşturulan analiz ID'si veya None
    """
    try:
        import json

        from db_session import get_session
        from models import AIAnalysis

        with get_session() as session:
            analysis = AIAnalysis(
                signal_id=signal_id,
                symbol=symbol,
                market_type=market_type,
                scenario_name=scenario_name,
                signal_type=signal_type,
                analysis_text=analysis_text,
                technical_data=json.dumps(technical_data) if technical_data else None,
            )
            session.add(analysis)
            session.commit()
            logger.info(f"AI analizi kaydedildi: {symbol} (ID: {analysis.id})")
            return analysis.id
    except Exception as e:
        logger.error(f"AI analizi kaydetme hatası ({symbol}): {e}")
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
    Google Gemini kullanarak teknik verileri VE haber akışını yorumlar.

    Args:
        symbol: Sembol
        scenario_name: Senaryo adı
        signal_type: Sinyal türü (AL/SAT)
        technical_data: Teknik veriler
        news_context: Haber metni
        timeout: Maksimum bekleme süresi (saniye)
        market_type: Piyasa türü (BIST/Kripto)
        save_to_db: True ise analizi veritabanına kaydet
        signal_id: İlişkili sinyal ID'si

    Returns:
        AI yorumu veya hata mesajı
    """
    if not api_key:
        return json.dumps(
            {"error": "API Key eksik", "sentiment_score": 50, "summary": ["Analiz yapılamadı."]}
        )

    if gemini_client is None and legacy_genai is None:
        return json.dumps(
            {
                "error": "Gemini SDK eksik",
                "sentiment_score": 50,
                "summary": ["Gemini SDK bulunamadi."],
            }
        )

    result = {"text": None, "error": None}

    def _generate():
        try:
            import json

            model = None

            news_text = "Haber verisi yok veya çekilemedi. Sadece tekniğe odaklan."
            if news_context:
                news_text = news_context

            prompt = f"""
            Sen uzman bir borsa stratejistisin. Elimde teknik olarak '{signal_type}' sinyali veren bir varlık var.
            Bunu detaylı analiz et ve JSON formatında yanıtla.

            Varlık: {symbol}
            Teknik Durum: {scenario_name} (Yön: {signal_type})

            📊 GÜNLÜK Teknik Veriler:
            - Fiyat: {technical_data.get("PRICE", "Yok")}
            - RSI (14): {technical_data.get("RSI", "Yok")}
            - MACD: {technical_data.get("MACD", "Yok")}

            📰 GÜNCEL HABER AKIŞI:
            {news_text}

            GÖREVİN:
            Aşağıdaki JSON şemasına birebir uyarak yanıt ver. Markdown kullanma, sadece saf JSON döndür.
            {{
                "sentiment_score": (0-100 arası sayı, 0=Ayı/Korku, 50=Nötr, 100=Boğa/Açgözlülük),
                "sentiment_label": ("GÜÇLÜ AL", "AL", "NÖTR", "SAT", "GÜÇLÜ SAT"),
                "summary": ["Çarpıcı analiz maddesi 1", "Madde 2", "Madde 3"],
                "explanation": "Yatırımcıya hitap eden, teknik ve temeli birleştiren detaylı paragraf (max 3 cümle).",
                "key_levels": {{
                    "support": ["destek seviyesi 1", "destek seviyesi 2"],
                    "resistance": ["direnç seviyesi 1", "direnç seviyesi 2"]
                }},
                "risk_level": ("Düşük", "Orta", "Yüksek")
            }}
            """

            if gemini_client is not None:
                response = gemini_client.models.generate_content(
                    model="gemini-2.0-flash", contents=prompt
                )
                response_text = getattr(response, "text", None)
            elif legacy_genai is not None:
                model = legacy_genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(prompt)
                response_text = getattr(response, "text", None)
            else:
                raise RuntimeError("Gemini SDK unavailable")

            if not response_text:
                raise ValueError("Gemini API bos yanit dondurdu")
            # Markdown temizliği (bazı modeller ```json ... ``` ile dönebilir)
            clean_text = response_text.replace("```json", "").replace("```", "").strip()

            # JSON doğrulama
            json.loads(clean_text)

            result["text"] = clean_text

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Gemini API hatası ({symbol}): {e}")

    # Thread ile timeout kontrolü
    thread = threading.Thread(target=_generate, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        logger.warning(f"AI analizi timeout ({symbol}, {timeout}s)")
        return json.dumps({"error": "Timeout", "sentiment_score": 50, "summary": ["Zaman aşımı."]})

    if result["error"]:
        return json.dumps(
            {"error": result["error"], "sentiment_score": 50, "summary": ["Hata oluştu."]}
        )

    analysis_text = result["text"] or json.dumps({"error": "Boş yanıt", "sentiment_score": 50})

    # Veritabanına kaydet
    if save_to_db and result["text"]:
        save_analysis_to_db(
            symbol=symbol,
            market_type=market_type,
            scenario_name=scenario_name,
            signal_type=signal_type,
            analysis_text=analysis_text,
            technical_data=technical_data,
            signal_id=signal_id,
        )

    return analysis_text


def analyze_async(
    symbol: str,
    scenario_name: str,
    signal_type: str,
    technical_data: dict[str, Any],
    news_context: str | None = None,
    callback=None,
) -> threading.Thread:
    """
    Non-blocking AI analizi.

    Args:
        callback: Analiz tamamlandığında çağrılacak fonksiyon (result)

    Returns:
        Thread objesi
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
