import feedparser  # Google News RSS okumak için
import requests

from settings import settings

# CryptoPanic API Key - settings.py'den alınıyor
# Almak için: https://cryptopanic.com/developers/api/
CRYPTOPANIC_KEY = settings.cryptopanic_api_key


def get_crypto_news(symbol: str) -> str:
    """
    CryptoPanic üzerinden ilgili coin ile ilgili son haberleri çeker.
    """
    if not CRYPTOPANIC_KEY:
        return "⚠️ CryptoPanic API Key eksik."

    # USDT veya TRY eklerini temizle (BTCUSDT -> BTC)
    clean_symbol = symbol.replace("USDT", "").replace("TRY", "")

    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_KEY}&currencies={clean_symbol}&filter=important&kind=news"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if "results" in data and len(data["results"]) > 0:
            news_list = []
            # İlk 5 önemli haberi alalım
            for item in data["results"][:5]:
                title = item["title"]
                source = item["domain"]
                news_list.append(f"- {title} ({source})")
            return "\n".join(news_list)
        else:
            return "Son 24 saatte önemli bir haber akışı yok."

    except Exception as e:
        return f"Haber çekilemedi: {str(e)}"


def get_bist_news(symbol: str) -> str:
    """
    Google News RSS üzerinden BIST hissesi ile ilgili son haberleri çeker.
    """
    # Google News RSS URL (Türkçe ve Türkiye odaklı)
    # Şirket ismini veya kodunu aratacağız.
    rss_url = f"https://news.google.com/rss/search?q={symbol}+hisse&hl=tr&gl=TR&ceid=TR:tr"

    try:
        feed = feedparser.parse(rss_url)

        if feed.entries:
            news_list = []
            # En güncel 5 haberi al
            for entry in feed.entries[:5]:
                title = entry.title
                pub_date = entry.published
                news_list.append(f"- {title} ({pub_date})")
            return "\n".join(news_list)
        else:
            return "İlgili hisse için güncel haber bulunamadı."

    except Exception as e:
        return f"Haber çekilemedi: {str(e)}"


def fetch_market_news(symbol: str, market_type: str) -> str:
    """
    Market tipine göre doğru haber kaynağına yönlendirir.
    """
    if market_type == "BIST":
        return get_bist_news(symbol)
    else:
        return get_crypto_news(symbol)
