# CLAUDE.md - Rapot Codebase Guide

Bu dosya, Rapot kod tabanıyla çalışan AI asistanları için kapsamlı bir kılavuz sağlar.

## Proje Genel Bakış

**Rapot** 7/24 çalışan otonom bir finansal analiz ve trading bot platformudur:
- BIST (Borsa İstanbul) ve kripto piyasaları için gerçek zamanlı tarama
- Google Gemini ile AI destekli teknik analiz
- TradingView kalitesinde profesyonel web dashboard
- Trading sinyalleri için Telegram bot bildirimleri
- Ekonomik takvim entegrasyonu
- WebSocket ile gerçek zamanlı fiyat akışı

**Ana Dil:** Türkçe (iki dilli UI)

## Mimari

```
┌─────────────────────────────────────────────────────────┐
│                    RAPOT PLATFORM                       │
├─────────────────────────────────────────────────────────┤
│  FRONTEND (Next.js 16)          BACKEND (Python)       │
│  ├─ Dashboard UI                ├─ FastAPI REST API    │
│  ├─ TradingView Charts          ├─ Market Scanner      │
│  ├─ Signal Management           ├─ Signal Calculator   │
│  ├─ Economic Calendar           ├─ AI Analyst (Gemini) │
│  ├─ Portfolio Panel             ├─ Telegram Bot        │
│  └─ WebSocket Client            ├─ WebSocket Manager   │
│                                 ├─ Health Monitoring   │
│                                 ├─ News Manager        │
│                                 └─ Trade Manager       │
│                                                         │
│  DATABASE: SQLite (trading_bot.db)                     │
│  DEPLOYMENT: VPS + PM2 (DigitalOcean 138.68.71.27)    │
└─────────────────────────────────────────────────────────┘
```

## Dizin Yapısı

```
/Rapot
├── frontend/                   # Next.js 16 Dashboard
│   ├── Dockerfile             # Frontend Docker image
│   ├── src/
│   │   ├── app/               # App Router pages
│   │   │   ├── page.tsx       # Landing / ana sayfa
│   │   │   ├── dashboard/     # Ana analiz dashboard
│   │   │   ├── signals/       # Sinyal yönetimi
│   │   │   ├── trades/        # Trade geçmişi
│   │   │   ├── scanner/       # Market tarama durumu
│   │   │   ├── health/        # Bot sağlık izleme
│   │   │   ├── settings/      # Ayarlar
│   │   │   ├── chart/         # TradingView grafikleri
│   │   │   ├── calendar/      # Ekonomik takvim sayfası
│   │   │   └── tradingview/   # TradingView tam ekran
│   │   ├── components/        # React bileşenleri
│   │   │   ├── dashboard/     # Dashboard widget'ları
│   │   │   │   ├── ai-analysis-widget.tsx   # AI analiz paneli
│   │   │   │   ├── bot-dashboard.tsx        # Bot durum paneli
│   │   │   │   ├── economic-calendar.tsx    # Ekonomik takvim widget
│   │   │   │   ├── global-ticker.tsx        # Global fiyat ticker
│   │   │   │   ├── kpi-cards.tsx            # Performans kartları
│   │   │   │   ├── market-overview.tsx      # Piyasa genel bakış
│   │   │   │   ├── portfolio-panel.tsx      # Portföy yönetimi
│   │   │   │   ├── recent-signals.tsx       # Son sinyaller
│   │   │   │   ├── signal-terminal.tsx      # Sinyal terminali
│   │   │   │   └── ticker-tape.tsx          # Kayan fiyat bandı
│   │   │   ├── charts/        # Grafik bileşenleri
│   │   │   │   ├── advanced-chart.tsx       # Ana grafik (Lightweight Charts v5)
│   │   │   │   └── MiniSparkline.tsx        # Mini sparkline grafik
│   │   │   ├── calendar/      # Takvim bileşenleri
│   │   │   │   ├── date-navigator.tsx
│   │   │   │   ├── event-row.tsx
│   │   │   │   └── filter-tabs.tsx
│   │   │   ├── layout/        # Sayfa düzeni
│   │   │   │   ├── header.tsx              # Üst bar (ticker tape + bildirimler)
│   │   │   │   ├── sidebar.tsx             # Sol menü
│   │   │   │   ├── sidebar-context.tsx     # Sidebar state context
│   │   │   │   ├── main-content.tsx        # Ana içerik wrapper
│   │   │   │   └── mobile-nav.tsx          # Mobil navigasyon
│   │   │   ├── tradingview/   # TradingView sayfası bileşenleri
│   │   │   │   ├── filter-bar.tsx
│   │   │   │   ├── nav-rail.tsx
│   │   │   │   ├── right-sidebar.tsx
│   │   │   │   ├── screener-table.tsx
│   │   │   │   ├── sidebar-detail.tsx
│   │   │   │   └── sidebar-watchlist.tsx
│   │   │   ├── shared/        # Paylaşılan bileşenler
│   │   │   │   └── error-boundary.tsx
│   │   │   └── ui/            # Shadcn/UI bileşenleri
│   │   │       ├── badge, button, card, input, scroll-area
│   │   │       ├── separator, skeleton, switch, table, tabs
│   │   │       ├── toast, connection-status
│   │   │       └── ...
│   │   ├── lib/
│   │   │   ├── api/           # API client fonksiyonları
│   │   │   │   ├── client.ts  # Tüm API çağrıları
│   │   │   │   └── index.ts   # Export barrel
│   │   │   ├── hooks/         # Custom React hooks
│   │   │   │   ├── use-analyses.ts      # AI analiz hook
│   │   │   │   ├── use-binance-ticker.ts # Binance WebSocket fiyat
│   │   │   │   ├── use-chart-data.ts    # Grafik veri hook
│   │   │   │   ├── use-dashboard.ts     # Dashboard KPI hook
│   │   │   │   ├── use-health.ts        # Sağlık kontrolü hook
│   │   │   │   ├── use-realtime.ts      # Zustand store + WebSocket
│   │   │   │   ├── use-signals.ts       # Sinyal hook
│   │   │   │   ├── use-trades.ts        # Trade hook
│   │   │   │   └── use-websocket.ts     # WebSocket bağlantı hook
│   │   │   ├── actions/       # Server actions
│   │   │   │   └── market-data.ts
│   │   │   ├── indicators.ts  # COMBO/HUNTER hesaplamaları
│   │   │   ├── mock-data.ts   # Test/demo verileri
│   │   │   ├── utils.ts       # Yardımcı fonksiyonlar
│   │   │   └── stores/        # Zustand state stores
│   │   │       └── index.ts
│   │   └── types/             # TypeScript tanımları
│   └── package.json
│
├── api/                        # FastAPI Backend
│   ├── main.py                # REST endpoints
│   ├── auth.py                # JWT authentication
│   ├── realtime.py            # WebSocket/SSE endpoints
│   └── calendar_service.py    # Ekonomik takvim
│
├── # Python Backend Modülleri (root level)
│   ├── main.py                # Bot giriş noktası
│   ├── scheduler.py           # Görev zamanlama
│   ├── market_scanner.py      # Piyasa tarama motoru
│   ├── signals.py             # Sinyal hesaplama (COMBO/HUNTER)
│   ├── data_loader.py         # Tarihsel veri çekme (sync)
│   ├── async_data_loader.py   # Tarihsel veri çekme (async)
│   ├── async_scanner.py       # Async piyasa tarayıcı
│   ├── batch_data_loader.py   # Toplu veri çekme
│   ├── ai_analyst.py          # Gemini AI entegrasyonu
│   ├── database.py            # Database işlemleri
│   ├── db_session.py          # Database session yönetimi
│   ├── models.py              # SQLAlchemy ORM modelleri
│   ├── config.py              # Trading konfigürasyonu
│   ├── settings.py            # Ortam ayarları (Pydantic)
│   ├── telegram_notify.py     # Telegram bildirimleri
│   ├── command_handler.py     # Telegram komut işleyici
│   ├── backtesting_system.py  # Backtest motoru
│   ├── bist_service.py        # BIST veri servisi
│   ├── trade_manager.py       # Trade yönetimi
│   ├── news_manager.py        # Haber yönetimi
│   ├── price_cache.py         # Fiyat önbellek
│   ├── websocket_manager.py   # WebSocket yönetimi
│   ├── health_api.py          # Sağlık API endpoint'leri
│   ├── logger.py              # Loglama sistemi
│   ├── migrate_db.py          # Database migration
│   ├── prometheus_metrics.py  # Prometheus metrikleri
│   └── test_binance.py        # Binance bağlantı testi
│
├── tests/                      # Test suite
│   ├── conftest.py            # pytest konfigürasyonu
│   ├── test_config.py
│   ├── test_market_scanner.py
│   └── test_signals.py
│
├── data/                       # Veri dosyaları
│   └── bist_symbols.json      # BIST sembolleri
│
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Python container
├── ecosystem.config.js         # PM2 process manager config
├── start-api.sh               # API başlatma scripti (venv)
├── requirements.txt            # Python bağımlılıkları
└── pyproject.toml              # Python proje config
```

## Teknoloji Stack

### Frontend
| Teknoloji | Versiyon | Amaç |
|-----------|----------|------|
| Next.js | 16.1.4 | React framework (App Router) |
| React | 19.2.3 | UI kütüphanesi |
| TypeScript | 5 | Tip güvenliği |
| Tailwind CSS | v4 | Stil |
| Lightweight Charts | 5.1.0 | Profesyonel mum grafikleri |
| Zustand | 5.0.10 | State yönetimi |
| React Query | 5.x | Server state |
| Shadcn/UI | - | Bileşen kütüphanesi |

### Backend
| Teknoloji | Versiyon | Amaç |
|-----------|----------|------|
| Python | 3.10+ | Dil |
| FastAPI | 0.109.0 | REST API framework |
| SQLAlchemy | 2.0.0 | ORM |
| Pydantic | 2.5.0+ | Validation & settings |
| google-generativeai | 0.3.0+ | AI analizi |
| python-telegram-bot | 20.0+ | Bildirimler |
| python-binance | 1.0.0 | Kripto verisi |
| isyatirimhisse | 1.2.0+ | BIST verisi |
| ta | 0.10.0+ | Teknik analiz |
| pandas | 2.0.0+ | Veri işleme |

## Geliştirme Komutları

### Frontend
```bash
cd frontend
npm run dev          # Development server :3000
npm run build        # Production build
npm run start        # Production server
npm run lint         # ESLint kontrolü
npx tsc --noEmit     # TypeScript kontrolü
```

### Backend
```bash
# Trading bot çalıştır
python main.py              # Sync mod
python main.py --async      # Async mod

# API server çalıştır
uvicorn api.main:app --reload --port 8000

# Testleri çalıştır
pytest                      # Tüm testler
pytest -v                   # Verbose
pytest tests/test_signals.py  # Belirli dosya
```

### Kod Kalitesi
```bash
ruff check .               # Lint kontrolü
ruff format .              # Auto-format
pre-commit run --all-files # Tüm pre-commit hooks
```

### VPS Deployment (PM2)
```bash
# SSH ile VPS'e bağlan
ssh root@138.68.71.27

# Kodu güncelle ve deploy et
cd /home/user/Rapot
git pull origin main
cd frontend && npm run build
pm2 restart all

# PM2 komutları
pm2 status                 # Tüm servislerin durumu
pm2 logs api               # API logları
pm2 logs frontend          # Frontend logları
pm2 restart api            # API yeniden başlat
pm2 restart frontend       # Frontend yeniden başlat
```

### Docker (Alternatif Deployment)
```bash
docker-compose up -d           # Tüm servisleri başlat
docker-compose logs -f api     # API loglarını izle
docker-compose logs -f frontend # Frontend loglarını izle
docker-compose down            # Servisleri durdur
docker-compose build --no-cache # Yeniden build
```

## PM2 Servisleri

`ecosystem.config.js` içinde iki servis:
1. **api** (port 8000): FastAPI backend (`start-api.sh` üzerinden)
2. **frontend** (port 3000): Next.js dashboard (`npm run dev -- -H 0.0.0.0`)

VPS: DigitalOcean Droplet `138.68.71.27`
- Python venv: `/opt/rapot-venv`
- Proje dizini: `/home/user/Rapot`

## Docker Servisleri

`docker-compose.yml` içinde üç servis:
1. **api** (port 8000): FastAPI backend
2. **frontend** (port 3000): Next.js dashboard
3. **bot**: Market scanner ve sinyal üretici

## Kod Stili Kuralları

### Python
- **Satır uzunluğu:** 100 karakter
- **Formatter/Linter:** Ruff
- **Tırnak stili:** Çift tırnak
- **Import sırası:** Standart, third-party, local (isort)
- **Type hints:** Fonksiyon imzalarında zorunlu

### TypeScript/React
- **Bileşenler:** Functional components + hooks
- **State:** Zustand (client), React Query (server)
- **Stil:** Tailwind utility classes
- **Dosya isimlendirme:** kebab-case, PascalCase bileşenler

## Veritabanı Modelleri

SQLite veritabanı (`trading_bot.db`) tabloları:

### Signal
- `symbol`, `market_type` (BIST/Kripto), `strategy` (COMBO/HUNTER)
- `signal_type` (AL/SAT), `timeframe`, `score`, `price`, `details` (JSON)

### Trade
- `symbol`, `market_type`, `direction` (BUY/SELL)
- `price`, `quantity`, `pnl`, `status` (OPEN/CLOSED/CANCELLED)

### ScanHistory
- `scan_type`, `mode`, `symbols_scanned`, `signals_found`, `duration_seconds`

## Trading Stratejileri

### COMBO Stratejisi
Multi-indikatör momentum tespiti:
- **Alış koşulları:** MACD < 0, RSI < 40, Williams %R < -80
- **Satış koşulları:** MACD > 0, RSI > 80, Williams %R > -10
- Skor formatı: "+4/-0" (4 alış, 0 satış indikatörü)

### HUNTER Stratejisi
Dip/tepe tespiti RSI doğrulaması ile:
- 7-gün/10-gün dip/tepe pattern tespiti
- RSI doğrulaması (DIP < 30, TOP > 70)
- Skor formatı: "7/7" (pattern içindeki gün, gereken gün)

## Lightweight Charts v5 Notları

**Markers API değişti!** v5'te:
```typescript
// ESKİ (v4) - ÇALIŞMIYOR:
series.setMarkers(markers)

// YENİ (v5):
import { createSeriesMarkers } from 'lightweight-charts'
const markersInstance = createSeriesMarkers(series, markers)
// Temizlemek için: markersInstance.detach()
```

## API Endpoints

**Base URL:** `http://localhost:8000`

```
GET  /signals              # Sinyalleri listele (filtrelenebilir)
GET  /signals/{id}         # Sinyal detayı
GET  /trades               # Trade geçmişi
GET  /stats                # Portföy istatistikleri
GET  /symbols/bist         # BIST sembolleri
GET  /symbols/crypto       # Kripto sembolleri
GET  /candles/{symbol}     # OHLCV verisi
GET  /market/ticker        # Canlı fiyatlar
GET  /market/analysis      # AI analizi
POST /analyze/{symbol}     # Analiz tetikle
GET  /health               # Sağlık kontrolü
```

## Ortam Değişkenleri

`.env` dosyasında gerekli:
```bash
# Telegram (Zorunlu)
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Binance (Opsiyonel - kripto için)
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret

# AI (Opsiyonel)
GEMINI_API_KEY=your_gemini_key

# Database
DATABASE_PATH=trading_bot.db
```

## Önemli Kurallar

1. **Türkçe terminoloji:**
   - AL = BUY, SAT = SELL
   - Günlük = Daily, Haftalık = Weekly
   - BIST = Borsa İstanbul, Kripto = Cryptocurrency

2. **Sinyal skorları:**
   - COMBO: "+X/-Y" formatı
   - HUNTER: "X/Y" formatı

3. **Timeframe'ler:**
   - `1d` = Günlük, `1wk` = Haftalık
   - `1h`, `4h` = Saatlik
   - `15m`, `30m` = Dakikalık

4. **Renk şeması (dark theme):**
   - Background: `#0e1117`
   - Cards: `#161b22`
   - Bullish: `#00c853`
   - Bearish: `#ff3d00`

## Performans Kuralları

Dashboard performansı için dikkat edilecek noktalar:
- **Polling interval'ları:** Minimum 30sn (bot status), 60sn (health, stats, trades)
- **Global refetchInterval:** Kapalı - her query kendi interval'ını yönetir
- **WebSocket dependency:** `JSON.stringify` yerine `useMemo` ile stabil key kullan
- **useAnimatedNumber:** `displayValue`'yu dependency array'e KOYMA (sonsuz döngü yapar)
- **Indicator hesaplamaları:** `calculateCombo`/`calculateHunter` mutlaka `useMemo` ile sarılmalı
- **Header saat:** 10sn interval yeterli, 1sn tarayıcıyı kilitler

## Debugging

- PM2 logları: `pm2 logs api` / `pm2 logs frontend`
- Docker logları: `docker-compose logs -f api` / `frontend` / `bot`
- Browser: DevTools + React DevTools
- Health check: `http://localhost:8000/health`
- VPS erişim: `http://138.68.71.27:3000` (dashboard) / `:8000` (API)
