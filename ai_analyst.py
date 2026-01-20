"""
AI Analyst Modülü
Google Gemini kullanarak teknik analiz ve haber yorumlama.
"""

import threading
from typing import Any

import google.generativeai as genai

from logger import get_logger
from settings import settings

logger = get_logger(__name__)

# Gemini API - settings.py'den credentials alınıyor
api_key = settings.gemini_api_key

if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GEMINI_API_KEY bulunamadı!")

# AI analizi için timeout - settings.py'den alınıyor
AI_TIMEOUT = settings.ai_timeout


def analyze_with_gemini(
    symbol: str,
    scenario_name: str,
    signal_type: str,
    technical_data: dict[str, Any],
    news_context: str | None = None,
    timeout: int = AI_TIMEOUT,
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

    Returns:
        AI yorumu veya hata mesajı
    """
    if not api_key:
        return "⚠️ AI Analizi yapılamadı (API Key eksik)."

    result = {"text": None, "error": None}

    def _generate():
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")

            news_text = "Haber verisi yok veya çekilemedi. Sadece tekniğe odaklan."
            if news_context:
                news_text = news_context

            prompt = f"""
            Sen uzman bir borsa stratejistisin. Elimde teknik olarak '{signal_type}' sinyali veren bir varlık var ama piyasadaki haber akışından endişeliyim.
            Bunu bir yatırımcıya hitap eder gibi, samimi, profesyonel ve uyarıcı bir dille yorumla.

            Varlık: {symbol}
            Teknik Durum: {scenario_name} (Yön: {signal_type})

            📊 GÜNLÜK Teknik Veriler:
            - Fiyat: {technical_data.get("PRICE", "Yok")}
            - RSI (14): {technical_data.get("RSI", "Yok")} (30 altı ucuz, 70 üstü pahalı)
            - MACD: {technical_data.get("MACD", "Yok")}

            📰 GÜNCEL HABER AKIŞI / SOSYAL MEDYA ALGISI:
            {news_text}

            GÖREVİN:
            1. Teknik göstergeler ile haber akışı uyumlu mu? (Örn: Teknik 'AL' diyor ama haberlerde iflas/hack gibi felaketler var mı?)
            2. Bu hareket sadece bir düzeltme mi yoksa haber kaynaklı bir trend değişimi mi?
            3. Yatırımcıya "Fırsat" mı dersin yoksa "Dikkatli ol" mu?

            Yorumun kısa paragraflar halinde olsun. Yatırım tavsiyesi değildir uyarısı ekleme.
            Cümlelerine emojiler ekle. MAX 200 kelime.
            """

            response = model.generate_content(prompt)
            result["text"] = response.text

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Gemini API hatası ({symbol}): {e}")

    # Thread ile timeout kontrolü
    thread = threading.Thread(target=_generate, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        logger.warning(f"AI analizi timeout ({symbol}, {timeout}s)")
        return f"⚠️ AI Analizi zaman aşımına uğradı ({timeout}s)."

    if result["error"]:
        return f"⚠️ AI Hatası: {result['error'][:100]}"

    return result["text"] or "⚠️ AI yanıt vermedi."


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
