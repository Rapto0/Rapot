"""
Algo-Trading Bot - Ana Modül
Modüler yapı ile yeniden düzenlendi.

Modüller:
    - market_scanner.py: Piyasa tarama ve sinyal işleme
    - command_handler.py: Telegram komut işleme
    - scheduler.py: Zamanlama ve ana döngü
    - signals.py: Sinyal hesaplama stratejileri
    - data_loader.py: Veri çekme
    - telegram_notify.py: Telegram bildirimleri
    - ai_analyst.py: AI analizi
    - news_manager.py: Haber çekme
    - config.py: Merkezi konfigürasyon
    - logger.py: Logging

Kullanım:
    python main.py           # Sync mode (varsayılan, daha güvenilir)
    python main.py --async   # Async mode (daha hızlı ama daha fazla timeout)
"""

import signal
import sys

from scheduler import start_bot


def graceful_exit(signum, frame):
    """Ctrl+C için temiz çıkış."""
    print("\n\n🛑 Bot kapatılıyor...")
    sys.exit(0)


# Ctrl+C handler'ı kaydet
signal.signal(signal.SIGINT, graceful_exit)

if __name__ == "__main__":
    # Komut satırından --async flag'i kontrol et
    use_async = "--async" in sys.argv

    try:
        start_bot(use_async=use_async)  # Varsayılan: Sync (daha güvenilir)
    except SystemExit:
        pass  # Temiz çıkış
