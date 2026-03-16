# RAPOT CODEX - TAM BAGLAM DOSYASI

Bu dokumanin amaci: bu repoda herhangi bir gorev verildiginde, yeni bir analiz turu acmadan projenin teknik baglamini tek geciste kurabilmek.

Kapsam:
- Sistem mimarisi
- Runtime akislar
- Moduller arasi bagimlilik haritasi
- "Hangi dosyaya dokunursam nereyi etkiler?" etki tablosu
- API + frontend baglantilari
- Veri kaynaklari, DB, deploy, test ve risk noktalari

Not:
- Bu dosya statik import analizi + kod incelemesine gore hazirlandi.
- Dinamik import/cagri yollarinda (ozellikle scheduler/command tarafi) runtime davranisi da ayrica notlandi.

---

## 1) PROJE OZETI

Rapot, BIST ve kripto piyasalari icin:
- periyodik tarama yapan bot (sync/async),
- sinyal ureten strateji motoru (COMBO/HUNTER),
- AI analiz katmani (Gemini),
- REST + realtime API,
- Next.js dashboard
birlesimi olan hibrit bir platformdur.

Ana katmanlar:
1. Bot Core (root Python dosyalari)
2. API Katmani (`api/`)
3. Frontend (`frontend/`)
4. Persistence (SQLite + cache DB)
5. Operasyon (Docker, deploy scriptleri, health/metrics)

---

## 2) DIZIN HARITASI

### Backend core
- `main.py`: bot giris noktasi
- `scheduler.py`: ana dongu, zamanlama, health check tetigi
- `market_scanner.py`: sync tarama + AI + Telegram akisi
- `async_scanner.py`: async tarama (daha ince akis)
- `signals.py`: COMBO/HUNTER hesaplayicilari
- `strategy_inspector.py`: coklu timeframe strateji dump servisi
- `data_loader.py`: BIST/Kripto veri cekme + fallback
- `ai_analyst.py`: Gemini entegrasyonu + parse/normalize + DB save
- `ai_schema.py`: AI response schema/normalize katmani
- `command_handler.py`: Telegram komutlari
- `trade_manager.py`: portfoy/islem komutlari
- `telegram_notify.py`: rate-limited Telegram gonderim/alim

### API
- `api/main.py`: FastAPI endpointleri + startup orchestration
- `api/realtime.py`: websocket + SSE endpointleri
- `api/auth.py`: JWT auth
- `api/calendar_service.py`: ekonomik takvim provider

### Frontend
- `frontend/src/app/*`: sayfalar (landing, scanner, signals, trades, health, chart, ai)
- `frontend/src/lib/api/client.ts`: tum HTTP endpoint cagrilari
- `frontend/src/lib/hooks/*`: React Query + realtime hook katmani
- `frontend/src/components/*`: UI/domain komponentleri

### Veri / altyapi
- `models.py` + `db_session.py`: SQLAlchemy modeli + session yonetimi
- `database.py`: legacy SQLite erisim katmani (dogrudan SQL)
- `price_cache.py`: price cache DB ve cache yardimcilari
- `health_api.py`: Flask health/status servisi (5000)
- `docker-compose.yml`: `api`, `frontend`, `bot`
- `scripts/deploy.ps1`: git + manuel server deploy akisi

---

## 3) CALISMA MODLARI VE ANA AKISLAR

### 3.1 Bot (sync)
`main.py -> scheduler.start_bot(use_async=False) -> market_scanner.scan_market()`

Ozellik:
- daha genis ve agir akis
- AI analizi, haber toplama, Telegram mesaj formatlama, special tag kapsama kontrolleri

### 3.2 Bot (async)
`main.py --async -> scheduler -> async_scanner.scan_market_async()`

Ozellik:
- paralel veri cekme/sinyal hesaplama
- genelde daha hizli, daha dar kapsami var (sync akis kadar zengin degil)

### 3.3 API-only / API+embedded bot
`uvicorn api.main:app` ile:
- API ayaga kalkar
- realtime servisleri baslar (`websocket_manager` + `bist_service`)
- `RUN_EMBEDDED_BOT=1` ise API process icinde scheduler thread'i de baslar

### 3.4 Frontend
`next` app:
- HTTP cagrilar: `lib/api/client.ts` uzerinden `/api/*` (rewrite ile FastAPI)
- health cagrilari: `/health-api/*` (rewrite ile Flask health API)
- realtime: hem backend websocket yolu hem de direkt Binance websocket yolu var

---

## 4) DOMAIN VE VERI AKISI

### 4.1 Strateji katmani
- COMBO: `calculate_combo_signal`
- HUNTER: `calculate_hunter_signal`
- Timeframe seti: `1D, W-FRI, 2W-FRI, 3W-FRI, ME`

### 4.2 Strategy Inspector
`strategy_inspector.py`:
- sembol + market resolve eder
- tum timeframe'lerde stratejiyi calistirir
- API/Telegram/Frontend icin normalize cikti verir

### 4.3 AI katmani
`ai_analyst.py`:
- runtime ayarlari `settings.py`'den gelir
- model aday/fallback mantigi
- JSON extraction + schema parse (`ai_schema.py`)
- DB save (SQLAlchemy path)

### 4.4 Sinyalden UI'ya yol
1. Scanner sinyal uretir
2. DB'ye yazar (legacy ya da SQLAlchemy yolu, akisa gore)
3. API endpointleri bunlari sunar
4. Frontend hooks/sayfalar sorgular ve tablolari cizer

---

## 5) BAGIMLILIK HARITASI (OZET)

## 5.1 Backend yuksek etki merkezleri

En yuksek fan-out (en cok modulu cagirir):
- `api.main` (16)
- `market_scanner` (11)
- `command_handler` (9)
- `scheduler` (9)
- `async_scanner` (7)

En yuksek fan-in (en cok modul tarafindan kullanilir):
- `logger` (19)
- `data_loader` (10)
- `config` (9)
- `database` (7)
- `settings` (7)

## 5.2 Kritik bagimlilik zinciri

1. `main -> scheduler`
2. `scheduler -> (market_scanner | async_scanner | command_handler | health_api)`
3. `market_scanner -> (signals, strategy_inspector, ai_analyst, data_loader, price_cache, database, telegram_notify)`
4. `api.main -> (strategy_inspector, ai_analyst, db_session, models, data_loader, price_cache, realtime servisleri)`

## 5.3 Mimari gercek

Persistence ikiye bolunmus durumda:
- Legacy yol: `database.py` (scanner/health/trade/metrics tarafinda yogun)
- Yeni yol: `db_session.py + models.py` (API/AI/migration tarafinda yogun)

Bu, ayni domaini iki farkli erisim modeli ile yonetme etkisi yaratiyor.

Migration policy (official):
- Alembic kullanilmiyor.
- Schema degisiklikleri: `db_session.py` (`init_db` + `ensure_sqlite_columns`)
- Data/backfill migrationlari: `migrate_db.py`
- Ayrintili kurallar: `docs/DB_MIGRATION_POLICY.md`

---

## 6) ETKI TABLOSU - BACKEND (DOSYAYA DOKUNMANIN ETKISI)

Asagidaki tablo "bu dosyada degisiklik yaparsam hangi modul/senaryolar etkilenir?" sorusunun pratik cevabidir.

| Dokunulan Dosya | Dogrudan Etkilenenler | Transitif Etki (ornek) | Risk |
|---|---|---|---|
| `config.py` | `signals`, `data_loader`, `scheduler`, `telegram_notify`, `strategy_inspector`, `async_*` | Tarama davranisi, indikatör esikleri, retry/rate-limit, timeframe uyumu | Cok Yuksek |
| `settings.py` | `ai_analyst`, `data_loader`, `telegram_notify`, `news_manager`, `health_api`, `logger` | AI modeli, API key davranisi, DB path, health port, log kurulumu | Cok Yuksek |
| `logger.py` | Neredeyse tum backend modulleri | Tum sistem gozlemlenebilirligi, hata analizi | Yuksek |
| `data_loader.py` | `market_scanner`, `async_scanner`, `strategy_inspector`, `price_cache`, `api.main`, `backtesting` | BIST/kripto veri kalitesi, scanner ve chart verileri | Cok Yuksek |
| `signals.py` | `market_scanner`, `async_scanner`, `strategy_inspector`, `command_handler`, `backtesting` | Tum sinyal uretimi ve skorlamalar | Cok Yuksek |
| `strategy_inspector.py` | `api.main`, `market_scanner`, `command_handler` | `/ops/strategy-inspector`, strategy panel, AI payload kalitesi | Yuksek |
| `ai_schema.py` | `ai_analyst`, `market_scanner`, `api.main` | AI parse, metadata, fallback/error davranisi | Yuksek |
| `ai_analyst.py` | `market_scanner`, `api.main` | AI endpointleri, Telegram AI mesaji, analiz DB kayitlari | Yuksek |
| `database.py` | `market_scanner`, `async_scanner`, `health_api`, `trade_manager`, `prometheus_metrics`, `api.main` | Legacy path'te sinyal/trade/istatistikler | Cok Yuksek |
| `db_session.py` | `api.main`, `ai_analyst`, `ai_evaluation`, `migrate_db`, `scheduler` | ORM tabanli endpointler, migration uyumu | Yuksek |
| `models.py` | `api.main`, `ai_analyst`, `db_session`, `ai_evaluation`, `migrate_db` | DB schema ve API response uyumu | Cok Yuksek |
| `price_cache.py` | `market_scanner`, `health_api`, `prometheus_metrics`, `batch_data_loader`, `api.main` | Candle/source fallback, cache hit-rate, performans | Yuksek |
| `market_scanner.py` | `scheduler`, `command_handler`, `health_api`, `api.main` | Sync tarama davranisinin tamami | Cok Yuksek |
| `async_scanner.py` | `scheduler`, `command_handler`, `api.main` | Async tarama sonucu ve hiz davranisi | Yuksek |
| `command_handler.py` | `scheduler`, `api.main` | Telegram komut semantigi, manuel analiz/inspect akislari | Yuksek |
| `scheduler.py` | `main`, `api.main` (embedded bot) | Bot yasam dongusu, saatlik/periodik task tetikleri | Cok Yuksek |
| `health_api.py` | `scheduler`, `api.main` (dolayli) | `/health-api` endpointleri, scanner/ops ekranlari | Orta-Yuksek |
| `telegram_notify.py` | `market_scanner`, `async_scanner`, `command_handler`, `scheduler`, `trade_manager` | Telegram bildirimleri ve komut polling | Yuksek |
| `trade_manager.py` | `command_handler` | `/portfoy` ve `/islemler` komutlari | Orta |
| `api/main.py` | Tum frontend HTTP katmani, external API clients | Tum REST davranisi + startup orchestration | Cok Yuksek |
| `api/realtime.py` | Realtime UI komponentleri | WebSocket/SSE ticker/signal streamleri | Yuksek |
| `websocket_manager.py` | `api.realtime`, `api.main` startup | Binance stream stabilitesi, reconnect davranisi | Yuksek |
| `bist_service.py` | `api.realtime`, `api.main` startup | BIST realtime cache ve push guncellemeleri | Yuksek |

---

## 7) ETKI TABLOSU - FRONTEND

| Dokunulan Dosya | Dogrudan Etkilenen Ekran/Moduller | Transitif Etki | Risk |
|---|---|---|---|
| `frontend/src/lib/api/client.ts` | `use-signals`, `use-trades`, `use-health`, `use-dashboard`, `use-analyses` + bazi sayfalarin direct cagrilari | Neredeyse tum veri beslemeli ekranlar | Cok Yuksek |
| `frontend/src/lib/utils.ts` | 35+ dosya | UI formatlama/class merge/genel utility davranisi | Yuksek |
| `frontend/src/lib/hooks/use-signals.ts` | `signals` sayfasi, header bildirimleri, recent signals, signal terminal, AI terminal | Sinyal listeleri/filtreler | Yuksek |
| `frontend/src/lib/hooks/use-trades.ts` | `trades` sayfasi (+ panel kullanimlari) | Trade listesi ve istatistikler | Orta-Yuksek |
| `frontend/src/lib/hooks/use-health.ts` | `health`, `scanner`, `header` | Bot durum rozetleri ve health ribbonlari | Orta-Yuksek |
| `frontend/src/lib/hooks/use-realtime.ts` | `global-ticker`, `signal-terminal` | Backend WS baglantisi ve canli ticker/signal | Yuksek |
| `frontend/src/lib/hooks/use-binance-ticker.ts` | `landing`, `advanced-chart`, `market-overview` | Direkt Binance fiyat akis ekranlari | Yuksek |
| `frontend/src/components/charts/advanced-chart.tsx` | `chart` sayfasi | Candle/indicator/watchlist/chart etkileşimleri | Cok Yuksek |
| `frontend/src/components/signals/strategy-inspector-panel.tsx` | `signals` sayfasi | Inspector endpoint davranisinin UI yansimasi | Yuksek |
| `frontend/src/components/ai/ai-terminal.tsx` | `ai` sayfasi | Analiz listeleme ve manuel AI akislar | Yuksek |
| `frontend/src/app/scanner/page.tsx` | Scanner ekrani | tarama/log/special-tag-health gorunumu | Yuksek |
| `frontend/src/app/signals/page.tsx` | Signals ekrani | filtreli sinyal tablosu + inspector panel entegrasyonu | Yuksek |
| `frontend/src/app/trades/page.tsx` | Trades ekrani | pozisyon/PnL tablolari | Orta-Yuksek |
| `frontend/src/app/health/page.tsx` | Health ekrani | log + scan history izleme | Orta |
| `frontend/src/components/layout/header.tsx` | tum sayfalarda ust bar | global health/signal rozetleri | Orta-Yuksek |
| `frontend/src/app/layout.tsx` | tum app shell | global provider/layout bozulmasi | Cok Yuksek |

---

## 8) API ENDPOINT KATALOGLARI VE UI BAGLANTISI

Bu kisim, endpoint degisikliklerinin hangi ekranlari vuracagini hizli gormek icin.

### Auth/System
- `POST /auth/token`
- `GET /auth/me`
- `GET /health`
- `GET /ops/special-tag-health`
- `GET /ops/strategy-inspector`
- `GET /scans`
- `GET /logs`

Frontend baglantilari:
- Scanner/Health/Header sayfalari ve panelleri

### Signals/Trades/Stats
- `GET /signals`
- `GET /signals/{id}`
- `GET /trades`
- `GET /stats`
- `GET /signals/{signal_id}/analysis`

Frontend baglantilari:
- `signals`, `trades`, dashboard KPI ve terminal komponentleri

### Market/Analysis
- `GET /market/overview`
- `GET /market/indices`
- `GET /market/ticker`
- `GET /candles/{symbol}`
- `GET /api/market/analysis`
- `GET /analyses`
- `GET /analyses/{id}`
- `GET /symbols/bist`
- `GET /api/calendar`

Frontend baglantilari:
- landing, advanced chart, AI terminal, economic calendar

### Realtime
- WS: `/realtime/ws/ticker`, `/realtime/ws/kline/{symbol}`, `/realtime/ws/trades/{symbol}`, `/realtime/ws/signals`
- SSE: `/realtime/sse/ticker`, `/realtime/sse/signals`

Frontend baglantilari:
- `use-realtime`, global ticker, signal terminal

---

## 9) FRONTEND VERI ERISIM MODEL

1. Ana model:
`page/component -> hook -> lib/api/client.ts -> backend`

2. Istisnalar:
- `scanner/page.tsx`, `advanced-chart.tsx`, `ai-terminal.tsx` bazi API cagrilarini dogrudan `client.ts` ile yapiyor.

3. Realtime iki kollu:
- Backend WS/SSE
- Direkt Binance WS (`use-binance-ticker`)

Etki:
- Realtime bug fix'lerde iki ayri baglanti yolunu birlikte dusunmek gerekir.

---

## 10) PERSISTENCE VE DB NOTLARI

DB dosyalari:
- `trading_bot.db` (ana)
- `price_cache.db` (buyuk cache)

Schema kaynaklari:
- SQLAlchemy: `models.py`
- Legacy SQL: `database.py` tablolari ve indexleri

Onemli:
- `db_session.init_db()` backward-compatible kolon ekleme yapiyor.
- Legacy ve ORM birlikte kullanildigi icin, tablo/kolon degisiklikleri iki yolu da test etmeli.

---

## 11) OPERASYON VE CALISTIRMA

### Lokal calistirma
- Bot sync: `python main.py`
- Bot async: `python main.py --async`
- API: `uvicorn api.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`

### Test
- `pytest`
- hedefli testler:
  - `tests/test_signals.py`
  - `tests/test_strategy_inspector.py`
  - `tests/test_api_market_analysis.py`
  - `tests/test_ai_analyst.py`
  - `tests/test_db_session.py`

### Docker
- `docker-compose up -d`
- servisler: `api`, `frontend`, `bot`

### Deploy
- `scripts/deploy.ps1`:
  - local commit/push
  - server komutlarini manuel bastirir

### Git commit dili
- GitHub commit mesajlari bundan sonra Turkce yazilir.
- Onerilen format: `tip: kisa Turkce ozet` (ornek: `duzeltme: RSI hesaplama tutarliligi`).

---

## 12) DEGISTIRME ONCESI HIZLI KONTROL LISTESI (CODEX ICIN)

Her gorevde bu checklist ile ilerle:

1. Gorev hangi katmanda?
- Bot core / API / Frontend / Infra / DB

2. Dokunulacak dosya bu tabloda yuksek riskli mi?
- Cok Yuksek ise, once etki alanini netle

3. Persistency yolu hangisi?
- `database.py` mi `db_session+models` mi?
- Ikisini birden etkiliyor mu?

4. Realtime etkisi var mi?
- Backend WS mi, direkt Binance WS mi, ikisi birden mi?

5. Endpoint degisiyorsa:
- `client.ts` + ilgili hook + sayfa/component zincirini kontrol et

6. Strateji/sinyal degisiyorsa:
- `signals.py` + `strategy_inspector.py` + scanner + testler

7. AI degisiyorsa:
- `ai_schema.py` + `ai_analyst.py` + `api/main.py` market analysis endpointi + AI testleri

8. DB/Model degisiyorsa:
- migration/backward compatibility
- hem legacy hem ORM akislarini test et

9. En az bir smoke test:
- ilgili endpoint/sayfa/komut davranisini elle dogrula

10. Son kontrol:
- etkilenen tablo satirlarina bak ve "beklenen yan etki" var mi kontrol et

---

## 13) BILINEN KIRILGAN NOKTALAR

1. Legacy + ORM birlikte yasiyor:
- Ayni domaine iki farkli persistence modeli.

2. API ve bot ayni process'te calisabilir (embedded):
- scheduler degisiklikleri API davranisini da dolayli bozabilir.

3. Realtime iki kaynakli:
- Backend realtime + direkt Binance WS ayrimi, bug triage'i zorlastirir.

4. `api/main.py` asiri merkezilesmis:
- fan-out yuksek, degisiklikler kolayca yayilir.

5. `market_scanner.py` buyuk ve cok sorumluluklu:
- sinyal, AI, formatlama, cache, DB, Telegram bir arada.

---

## 14) HIZLI ETKI KURALLARI (KISA HAFIZA)

- `config.py` degisirse: tum hesap ve tarama davranisi degisebilir.
- `data_loader.py` degisirse: scanner + chart + inspector birlikte etkilenir.
- `signals.py` degisirse: tum sinyal zinciri etkilenir.
- `api/main.py` degisirse: frontendin cogu endpointi etkilenir.
- `client.ts` degisirse: frontendin cogu veri akis yolu etkilenir.
- `layout.tsx` degisirse: tum UI iskeleti etkilenir.
- `database.py`/`models.py` degisirse: veri tutarliligini iki farkli erisim yolunda birlikte test et.

---

## 15) BU DOSYAYI NASIL KULLANMALI?

Her yeni gorevde:
1. Once "Etki Tablosu"nda dokunulacak dosyayi bul.
2. O satirdaki dogrudan/transitif etkiyi kapsam olarak al.
3. Sonra "Kontrol Listesi" adimlariyla uygulamaya gec.

Bu sayede her seferinde tum repo taramasi yapmadan tutarli ve guvenli degisiklik alinabilir.
