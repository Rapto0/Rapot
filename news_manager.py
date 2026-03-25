import feedparser
import requests

from logger import get_logger
from settings import settings

logger = get_logger(__name__)


def get_crypto_news(symbol: str) -> str:
    """Fetch latest important crypto news from CryptoPanic."""
    api_key = str(settings.cryptopanic_api_key or "").strip()
    if not api_key:
        return "⚠️ CryptoPanic API Key eksik."

    clean_symbol = str(symbol).upper().replace("USDT", "").replace("TRY", "")
    base_url = "https://cryptopanic.com/api/v1/posts/"
    params = {
        "auth_token": api_key,
        "currencies": clean_symbol,
        "filter": "important",
        "kind": "news",
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = data.get("results") or []
        if not results:
            return "Son 24 saatte önemli bir haber akışı yok."

        news_list = []
        for item in results[:5]:
            title = str(item.get("title", "Başlıksız"))
            source = str(item.get("domain", "bilinmiyor"))
            news_list.append(f"- {title} ({source})")
        return "\n".join(news_list)
    except Exception:
        logger.exception("Crypto news fetch failed for %s", clean_symbol)
        return "Haber servisine şu anda ulaşılamıyor."


def get_bist_news(symbol: str) -> str:
    """Fetch latest BIST-related news via Google News RSS."""
    rss_url = f"https://news.google.com/rss/search?q={symbol}+hisse&hl=tr&gl=TR&ceid=TR:tr"

    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            return "İlgili hisse için güncel haber bulunamadı."

        news_list = []
        for entry in feed.entries[:5]:
            title = getattr(entry, "title", "Başlıksız")
            pub_date = getattr(entry, "published", "")
            news_list.append(f"- {title} ({pub_date})")
        return "\n".join(news_list)
    except Exception:
        logger.exception("BIST news fetch failed for %s", symbol)
        return "Haber servisine şu anda ulaşılamıyor."


def fetch_market_news(symbol: str, market_type: str) -> str:
    """Route request to the matching news provider by market type."""
    if market_type == "BIST":
        return get_bist_news(symbol)
    return get_crypto_news(symbol)
