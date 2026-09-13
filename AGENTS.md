# AGENTS.md — Rapot kod tabanı rehberi

Kaynaklarla son karşılaştırma: **13 Eylül 2026 / P1-G2**. İş sırası, kullanıcı
yetkileri, kabul kanıtları ve ertelenen işler [devam planında](docs/RAPOT_DEVAM_PLANI.md)
tutulur. Eski backlog'lardaki boş kutular tek başına eksiklik kanıtı değildir.

## Proje ve çalışma sınırları

Rapot; BIST/kripto taraması, COMBO/HUNTER sinyalleri, isteğe bağlı Gemini analizi,
Telegram bildirimleri ve Next.js dashboard içerir. TradingView webhook'larını
işleyen Binance Spot middleware'i ayrı uygulama/veritabanıdır. Dashboard'un ana
Trade kayıtları middleware emirleriyle aynı veri kümesi değildir.

İşleri **incele → düzelt → doğrula → belgeyi güncelle** sırasıyla ele al.
Commit/push/deploy kapsamı kullanıcının mevcut talimatlarından ve devam planından
okunur; bu dosya kendi başına üretim işlemi veya emir gönderme yetkisi vermez.
Kullanıcı borsa ile ilgili dış kabulü erteledi: gerçek TradingView alarm teslimi
ve testnet/gerçek emir testi açık kalır. Mevcut üretim DRY_RUN, trading/live kapalıdır.
Anahtar, parola, .env içeriği ve gerçek veritabanları rapora/Git'e alınmaz.

## Mimari ve giriş noktaları

| Katman | Kaynak ve görev |
|---|---|
| Bot | `main.py` → `scheduler.py` → `market_scanner.py` veya `async_scanner.py`; `--async` seçimidir |
| Hesaplama | `signals.py`, `config.py`, `strategy_inspector.py`, `data_loader.py` |
| Scanner uygulaması | `application/scanner/signal_handlers.py`, `application/scanner/scan_history.py`; `domain/events/signal_domain_event.py` |
| Ana API | `api/main.py`, `api/routes/`, `api/auth.py`; port 8000 |
| Servis/repository | `application/services/` → `infrastructure/repositories/`; scanner yazıları `infrastructure/persistence/` |
| Ana veri | `models.py`, `db_session.py`, `database.py`; SQLite ve ayrı fiyat önbelleği |
| Realtime | `api/runtime/signal_feed.py` ortak SQLite kayıtlarını okur; `api/realtime.py` WS/SSE sunar |
| Bot sağlık | `health_api.py`, Flask; port 5000 |
| Middleware | `middleware/api/main.py` → `middleware/services/trading_service.py`; port 8001; ayrı PostgreSQL/Alembic |
| Frontend | `frontend/src/app/`, `frontend/src/components/`, `frontend/src/lib/api/client.ts`, `frontend/src/lib/hooks/`; port 3000 |
| Container girişleri | `scripts/runtime.py`: init-main-db, api, bot, migrate-middleware, middleware |

Ana dashboard `/`; diğer sayfalar `/signals`, `/trades`, `/scanner`, `/health`,
`/settings`, `/chart`, `/alarms`, `/ai`, `/calendar`, `/tradingview`, `/login`.
Ayarlar sayfası sunucu/tarayıcı ayarlarının kapsamını açıklar; tarayıcı tercihleri
ilgili ekranlardan düzenlenir. Yerel alarmlar yalnız alarm sayfası
açıkken değerlendirilir; kalıcı sunucu alarmı veya Telegram aboneliği değildir.

Canonical import ve compatibility listesi [paketleme haritasındadır](docs/PACKAGING_REFACTOR_MAP.md).
`application.scanner.signal_handlers` gerçek uygulamadır; `scanner_side_effects`
eski yola uyumluluk sağlar. Wrapper silmek için kullanım ve tüketici göçü kanıtı
gerekir; [takvim](docs/WRAPPER_DEPRECATION_SCHEDULE.md) otomatik silme emri değildir.

## Geliştirme ortamı ve bağımlılıklar

- Python **3.12** (`.python-version`, `pyproject.toml`); yerelde doğrulanan 3.12.8.
- Node **20.20.2**, npm **10.9.9** (`.nvmrc`, `frontend/package.json`).
- Frontend: Next.js **16.3.5**, React **19.2.3**, TypeScript **5.9.3**, Tailwind
  **4.1.18**, Lightweight Charts **5.1.0**, Zustand **5.0.10**, React Query **5.90.19**.
- Backend: FastAPI/Uvicorn, SQLAlchemy/Pydantic, pandas/NumPy/ta, python-binance,
  isyatirimhisse/yfinance, google-genai, python-telegram-bot, Flask, Alembic/psycopg.
  `requirements.txt` sürüm aralıklarını ve `requirements-security.txt` güvenlik
  kısıtlarını kullanır; kesin geliştirme/CI çözümü
  `requirements-dev.lock`, araç tanımları `requirements-dev.txt` içindedir.
- `ai_analyst.py` öncelikle `google.genai` kullanır. Eski `google.generativeai`
  fallback kodu kalmıştır; eski SDK güncel zorunlu bağımlılık değildir.
- Lock ortamı `ta` kullanır; `signals.py` isteğe bağlı `pandas_ta` importunu ve
  yokluğunda DataFrame `.ta` uyumluluk katmanını içerir. Ortama paket eklemek
  hesaplama yolunu değiştirebilir; Python/TypeScript/Pine eşdeğerliği varsayılmaz.

Kurulum ve Windows Node alternatifi: [ortam komutları](docs/RAPOT_DEVAM_PLANI.md#geliştirme-ortamı-ve-komutlar).
Repo kökünde seçili .venv ile:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest
uv pip check --python .venv/Scripts/python.exe
# Yalnız ilgili Python dosyalarında lint/format kontrolü:
.venv/Scripts/python.exe -m ruff check <dosyalar>
.venv/Scripts/python.exe -m ruff format --check <dosyalar>
```

`pytest.ini` varsayılan olarak `tests/` ve `middleware/tests/` toplar. Kök
`conftest.py` ortam ayarlarını sentetik değerlerle değiştirir, geçici DB/cache
kullanır, HTTP/socket/curl ağını engeller. Bu izolasyon normal API/bot başlatma
komutlarını veya keyfi native subprocess'leri kapsamaz.

Tam pytest paketindeki `tests/test_strategy_comparison.py` ayrıca Node 20 ve
`frontend` içinde `npm ci` ile kurulmuş TypeScript'i gerektirir. Node PATH'te
değilse `NODE_BINARY` tam yürütücü yolunu seçer. Adaptör yalnız sabit sentetik
fixture ve gerçek gösterge kaynağını okur; ağ/uygulama servisi başlatmaz.
İsteğe bağlı `RAPOT_STRATEGY_REPORT` mutlak JSON yolu ölçüm kanıtını üretir;
CI iki runtime'ı kurar ve raporu artifact olarak saklar.

Seçili Node/npm ile frontend klasöründe:

```powershell
npm ci
npm test
npm run lint -- --no-cache
npm run typecheck -- --incremental false
$env:NEXT_TELEMETRY_DISABLED = '1'
npm run build
npm run test:standalone
```

`test:standalone` önceden build edilmiş çıktıyı yerel HTTP/WS mock'larıyla sınar.
`python -m scripts.ci_quality lint`, Git'in izlediği tüm Python kaynaklarında
Ruff lint/format uygular; middleware ve testler dahildir. Ruff/pre-commit sınırları
iç worktree, ortam/bağımlılık ve üretilmiş klasörleri dışarıda tutar.
Bandit ve pip-audit bulguları açıkça report-only raporlanır; araç hatası, geçersiz
rapor veya eksik kapsam CI'yi başarısız yapar. Yeşil CI sıfır güvenlik bulgusu değildir.
Frontend'de `npm run audit:dependencies` bütün kilitli prod/dev/optional/peer
paketlerini public npm registry üzerinden tarar; her bulgu veya araç/rapor/kapsam
hatası CI'yi başarısız yapar. Ham JSON, lock hash'i ve kapsam manifesti saklanır.
`npm test` bu kontrolün ağsız testlerini içerir. npm 10'un Sharp WASM ortak optional
çocukları için iki `npm ls` extraneous uyarısı lock uyuşmazlığı değildir;
[advisory incelemesi](docs/FRONTEND_DEPENDENCY_SECURITY.md) kapsamı açıklar.
Pip içermeyen uv ortamında bağımlılık kontrolü yukarıdaki `uv pip check` ile yapılır.

## Strateji terminolojisi

- AL/SAT = BUY/SELL; BIST/Kripto piyasa adlarıdır.
- Backend tarama periyotları `1D`, `W-FRI`, `2W-FRI`, `3W-FRI`, `ME`;
  chart/API'deki `1d`, `1wk`, `1h`, `4h` biçimleri aynı arayüz değildir.
- COMBO dört göstergeyi puanlar: MACD, RSI, Williams %R, CCI. `Score=+X/-Y`
  alış/satış puanıdır. Günlük/haftalık AL4–SAT3, diğer tanımlı periyotlar
  AL3–SAT3 kullanır; bilinmeyen periyot fallback'i AL4–SAT4'tür.
- HUNTER **15 göstergenin** dip/tepe koşullarını sayar: RSI, hızlı RSI, CMO,
  BOP, MACD, Williams %R, CCI, Ultimate Oscillator, Bollinger %B, ROC,
  DeMarker, PSY, Z-Score, Keltner %B, RSI(2).
  Günlük/haftalık/iki haftalık dip eşiği 7; üç haftalık/aylık 5; tepe eşiği 10.
  `DipScore=7/7`, **7 gösterge puanı / gerekli 7 puan** demektir; gün sayısı değildir.
  `ActiveIndicators=X/15` kullanılabilir gösterge sayısını ayrıca verir.
  NaN göstergeler puanlanmaz; eşik düşürülmez. RSI puanlardan biridir,
  ayrı zorunlu onay değildir.
- `config.py` eşik tanımları içerse de `signals.py` yalnız MIN_PERIODS'i
  ithal eder; eşikler hesaplayıcı fonksiyonlarda sabittir. Yalnız config
  değiştirerek strateji değiştiği varsayılmaz.
- HUNTER kısa ATR serisi P1-7'de düzeltildi. P3-1'in ilk adımında frontend
  `calculateCombo` geçerli sıfırı korur; eksik, NaN ve sonsuz göstergeler puan
  üretmez. Eşikler, 26 mum koşulu ve AL sonrası SAT önceliği değişmedi. Altı yeni
  regresyonla 105 frontend testi, CI ve imaj yayını geçti. Üretimde frontend
  `967f137`, backend/Compose/current `279aa9f`; yalnız frontend yenilendi.
  Tek günlük temizliği ve uygulama kabulü devam planında ayrı kayıtlardır.
  Hesaplayıcı yeterli sonlu göstergeyle puan üretebilir; yerel alarm son kaydın tüm
  göstergeleri sonlu değilse `unknown` döndürür. P3-1 ikinci adımında özel Pine
  EMA/ATR devam döngüleri yalnız seed sonrasında çalışacak biçimde sınırlandı;
  kaynak alt kümesi sayısal testi TradingView derleyicisi değildir. Güncel Pine
  derleme/runtime kabulü ayrıca açık. Gerçek Python/TS ölçümünün kapsamı ve
  varsayılan/formül farkları [karşılaştırma belgesinde](docs/STRATEGY_COMPARISON.md).
  Motorları topluca eşitleme kararı verilmedi; backtest işleri açık.

`backtesting_system.py` ayrı CLI'dir; çalışan servis girişleri onu import etmez.
P3-1 üçüncü adımında `Lot.invested` tüm alış giderlerini içerir; komisyon ve kayma
ayrı izlenir. Eski referans tutar üzerinden toplamsal model ve tek en eski lotu
tam satma FIFO sözleşmesi korunur. Nakit + açık maliyet tabanı = başlangıç +
gerçekleşmiş PnL bağıntısı sentetik testlerle doğrulanır. Float/Kahan ve dar
temsil toleransı Decimal defteri değildir;
[muhasebe belgesi](docs/BACKTEST_ACCOUNTING.md) sınırları açıklar.
Matplotlib ve tqdm kilit ortamda yoktur; yalnız grafik/runner fonksiyonlarında
yüklenir. Muhasebe testleri tam CLI veya grafik çalıştırmış sayılmaz.

P3-1 dördüncü adımında `BacktestEngine(..., as_of=...)` kapanış anını bir kez
sabitler; açıkça verilen an saat dilimli olmalıdır. `run_single_symbol(...,
data=frame)` sabit günlük OHLCV'yi kopyalayıp doğrular ve sağlayıcıya gitmez.
Start/end dahil işlem günü sınırlarıdır; önceki geçmiş ısınmada korunur.
Önceki kapanmış günlük prefix'in sinyali sonraki mevcut mumun gerçek Open
fiyatında yürütülür. Hem sinyal hem işlem satırı, piyasa takviminde sonraki
gece yarısına ulaşmış olmalıdır; bugünkü Open muhafazakâr biçimde dışlanır.
BIST Close/AOF proxy açılışı ve bilinmeyen `open_quality` reddedilir; yalnız
eksik/None veya `provider` metadata kabul edilir. 120 uygun satır ve ilk sinyal
indeksi60 korunur; en erken işlem indeksi61'dir. Günlük prefix'ten gelişen HTF
politikası değişmez. Paralel worker bir kez veri okur ve ortak `as_of` alır.
Çoklu sembol nakit kronolojisi/fiyatlama, benchmark/WFA ve tam CLI kabulü hâlâ
açıktır; [yürütme sözleşmesi](docs/BACKTEST_EXECUTION.md) kapsamı açıklar.

## Veri, erişim ve dağıtım

Ana SQLite: `db_session.init_db()` → create_all + uyumlu kolon/index ekleme;
`migrate_db.py` eski veri taşıma aracıdır. Middleware: ayrı modeller ve
`middleware/infra/alembic/` revision zinciri; üretimde migration önce, startup
revision kontrolü sonra gelir. [Migration politikası](docs/DB_MIGRATION_POLICY.md)
iki yolun ayrıntısını ve eski taşıma aracının sınırlarını açıklar.

P2-4, ana SQLite'a yalnız etiketi NULL olmayan kayıtları kapsayan
`idx_signals_special_tag_created(special_tag, created_at)` kısmi indeksini ekler.
Yeni DB'de metadata, mevcut DB'de `init_db()` bu indeksi oluşturur; başlangıç
sırasında disk/WAL alanı bütçelenmelidir. Kod geri dönüşü uyumlu indeksi korur;
üretim verisini geri yüklemez veya indeksi otomatik kaldırmaz. Eşit `created_at`
değerlerinde liste sırası ve LIMIT sınırındaki seçim deterministik değildir.

Ana DB'nin saat dilimsiz UTC sözleşmesi `infrastructure.time.utc_now_naive`
ile korunur: aware UTC saatinden yalnız tzinfo kaldırılır. Yerel saat kullanılmaz;
değişiklik eski satırları dönüştürmez veya API tarih biçimlerini topluca değiştirmez.

Ana API PyJWT ile yalnız HS256 ve zorunlu `exp` kullanır; frontend token'ı yalnız
sekme belleğinde tutar. TestClient için dev-only httpx2, SDK'lar için httpx
korunur; kök test izolasyonu ikisinin de HTTP transport'unu engeller. Yönetici
işleri admin ister; dashboard okuma endpointlerinin tamamı özel değildir.
Middleware webhook token'ı ve X-Admin-Token yönetim kimliği ana JWT'den ayrıdır.
[README erişim tablosu](README.md#security-notes) ve [middleware rehberi](middleware/README.md)
güncel sözleşmeyi gösterir. Gizli anahtarlar NEXT_PUBLIC değişkenlerine konmaz.

Üretim yolu Docker Compose 2.24+ ve HTTPS Nginx'tir. API/bot/frontend sürekli
servislerdir; main-init bir defalık iştir. Middleware profili PostgreSQL,
middleware-migrate ve middleware'i ekler. API embedded bot'u kapatır; scanner
paylaşılan dosya kilidiyle tek süreçte çalışır. PM2 dosyaları legacy'dir.
Host upstream'leri açıkça 127.0.0.1 kullanır; portlar loopback'e bağlıdır.

`.github/workflows/deploy.yml` imaj yayımlar; sunucu deploy'u yapmaz.
`scripts/deploy.ps1` doğrulanmış SHA'yı kontrol edip komutları yazdırır; SSH
çalıştırmaz. [Dağıtım rehberi](scripts/DEPLOY.md) ve devam planındaki son kabul
kaydı izlenir. Yalnız belge değişikliği servis restart'ı veya migration gerektirmez.

## Kod stili

Python: Ruff, 100 karakter, çift tırnak, standart/third-party/local import sırası,
fonksiyon imzalarında type hints. TypeScript: functional component + hooks,
Zustand client state, React Query server state, Tailwind utility sınıfları.
Lightweight Charts v5 marker'ları `createSeriesMarkers(series, markers)` ile
oluşturulur; temizlemede `detach()` kullanılır, eski `series.setMarkers` kullanılmaz.
