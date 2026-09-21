# Rapot mimarisi

Mimari harita P2-2'de kaynakla karşılaştırıldı; sürüm ve kabul notları
**21 Eylül 2026** tarihinde güncellendi. Bu belge mimariyi açıklar;
öncelik, üretim sürümü ve kabul durumu [RAPOT_DEVAM_PLANI.md](RAPOT_DEVAM_PLANI.md)
içindedir. Eski statik fan-in/fan-out sayıları yeniden ölçülmeden güncel kanıt sayılmaz.

## Sistem ve veri akışı

Rapot'un ana uygulaması BIST/kripto verisini tarar, COMBO/HUNTER sinyallerini
kaydeder, isteğe bağlı Gemini analizi ve Telegram bildirimi üretir. Next.js
dashboard bu kayıtları HTTP ve realtime kanallarıyla gösterir. Binance Spot
emir middleware'i ayrı uygulama, erişim kimliği ve veritabanına sahiptir.

```text
main.py → scheduler → sync / async scanner → signals.py
                          ↓ SignalDomainEvent
              application.scanner.signal_handlers
                          ↓
              infrastructure.persistence → ana SQLite
                                               ↓
                  api.runtime.signal_feed → WS/SSE → frontend
                                               ↑
API route → application.services → infrastructure.repositories

TradingView Pine → /webhooks/tradingview → TradingService
                         ↓                         ↓
                 ayrı auth/risk            broker + FIFO/muhasebe
                                                   ↓
                                      middleware PostgreSQL/Alembic
```

Bu iki veri hattı otomatik birleşmez. Ana /trades ve /stats, middleware
pozisyon/emir API'sinin dashboard entegrasyonu değildir. Yerel /alarms da
TradingView webhook'u veya sunucuda 7/24 çalışan alarm aboneliği değildir.

## Dosya ve sorumluluk haritası

| Alan | Başlangıç noktaları | Etki |
|---|---|---|
| Bot yaşam döngüsü | `main.py`, `scheduler.py`, `infrastructure/runtime_lock.py` | Tek scanner, periyodik görevler, Telegram komutları, Flask sağlık |
| Veri/hazırlık | `data_loader.py`, `price_cache.py`, `config.py`, `settings.py` | Kaynaklar, OHLCV, önbellek, periyotlar ve runtime ayarları |
| Hesaplama | `signals.py`, `strategy_inspector.py`, `frontend/src/lib/indicators.ts`, `middleware/pine/` | Python/TypeScript/Pine ayrı uygulamalar; eşdeğerlik test ister |
| Scanner | `market_scanner.py`, `async_scanner.py`, `application/scanner/scan_history.py` | Ortak kayıt/event/scan history; sync AI/haber/Telegram akışı daha geniş |
| Domain event | `domain/events/signal_domain_event.py` | Typed event, kayıt ve yayın payload alanları |
| Kayıt handler'ı | `application/scanner/signal_handlers.py` | Başarılı kayıt sonrası callback ve publisher adapter |
| Ana persistence | `infrastructure/persistence/`, `models.py`, `db_session.py` | Scanner kayıtları, ops/trade yardımcıları ve signal feed okuması |
| API servisleri | `application/services/`, `infrastructure/repositories/` | Sinyal/işlem/analiz/system read-model ve piyasa verisi |
| REST/auth | `api/main.py`, `api/routes/`, `api/auth.py`, `api/rate_limit.py` | DTO, HTTP filtreleri, login ve korunan işlemler |
| Realtime | `api/runtime/realtime_bootstrap.py`, `api/runtime/signal_feed.py`, `api/realtime.py` | Ortak DB sinyal akışı, provider yaşam döngüsü, WS/SSE |
| AI | `ai_analyst.py`, `ai_schema.py`, `ai_evaluation.py` | google.genai, normalize cevap/metadata, kayıt ve değerlendirme |
| Bildirim/komut | `telegram_notify.py`, `command_handler.py`, `trade_manager.py` | Telegram I/O ve ana uygulama işlem kayıtları |
| Middleware | `middleware/api/`, `middleware/services/trading_service.py`, `middleware/risk/`, `middleware/broker_adapters/`, `middleware/repositories/`, `middleware/infra/` | Webhook, idempotency, scoped envanter, emir sonucu, komisyon/FIFO ve recovery |
| Frontend | `frontend/src/app/`, `frontend/src/components/`, `frontend/src/lib/api/client.ts`, `frontend/src/lib/hooks/` | Sayfa → hook/client → REST/WS; bazı bileşenler client'ı doğrudan çağırır |

`database.py` legacy doğrudan SQLite erişimini korur; scanner sinyal yazısının
canonical yolu artık SQLAlchemy repository'dir. Paket ayrımı tüm application
kodunun framework'ten bağımsız olduğu anlamına gelmez: market_data_service
hâlâ FastAPI HTTPException ve api.providers bağımlılığı taşır.

## Uçtan uca akışlar

### Tarama → sinyal → ekran

1. main.py varsayılan sync, --async ile async scanner'ı seçer. Scheduler tarama
   ve bot yaşam döngüsünü yönetir; paylaşılan kilit ikinci botu engeller.
2. Scanner veri alır, periyotları hazırlar, COMBO/HUNTER hesaplar ve veri/sinyal
   korumalarını uygular. Sync ve async her yan etki bakımından özdeş değildir.
3. SignalDomainEvent, canonical handler ve save_signal üzerinden ana SQLite'a
   yazılır. Uniqueness çakışmasında yeni sinyal ID'si üretilmez.
4. Handler başarılı kayıt sonrası callback ve publisher adapter'ını çağırır.
   API bootstrap süreç içi publisher'ı kapalı tutar: üretimde UI yayın kaynağı
   ortak DB'dir; bot içindeki adapter süreçler arası mesaj kuyruğu değildir.
5. API SignalFeed başlangıçta mevcut en büyük ID'yi alır, sonraki commit edilmiş
   satırları periyodik ve thread üzerinden okur; WS/SSE'ye yayınlar.
   Cursor süreç belleğindedir, kalıcı teslim alındısı veya replay offset'i değildir.
6. Frontend bağlantı/yeniden bağlantı sırasında REST ile eşitler; geçmişi WS
   replay garantisine bağlamaz. DB geri yüklenmesi cursor gerilemesi yaratırsa
   resync olayı REST yenilemesini ister.

### Manuel analiz

- GET /ops/strategy-inspector, JWT ile teknik strateji/periyot raporu üretir;
  tek başına Gemini çağırmaz.
- GET /market/analysis (ve servis içi /api/market/analysis alias'ı), JWT →
  strategy_inspector → ai_analyst/ai_schema → UI cevabı yoludur. Bu endpoint
  analyze_with_gemini'yi save_to_db=False ile çağırır; cevap DB'ye kaydedilmez.
- Admin POST /analyze/{symbol}, command_handler.analyze_manual üzerinden
  Telegram mesajları da içeren manuel tarama/analiz akışını başlatır.
- Scanner'ın kayıtlı AI analizi gerçek sinyal ID'sine bağlanır. AI_ENABLED=0
  kapalı durumu üretir; kayıtlı analizleri okumak yeni sağlayıcı isteği değildir.

### TradingView → ayrı emir hattı

`middleware/api/routes/webhooks.py::ingest_tradingview_webhook` payload/auth
doğrulamasından sonra `TradingService.process_webhook` çağırır. Sinyal
idempotency, zaman/risk/Spot filtreleri ve execution-mode/account kapsamı
kontrol edilir; broker sonucu emir durumu ve gerçekleşen miktar/komisyon/FIFO
kayıtlarına uygulanır. Belirsiz sonuçlar recovery yolu gerektirir; istemciye
başarı dönmesi tek başına pozisyonun tamamen dolduğu anlamına gelmez.

DRY_RUN simülasyon kapsamı ile LIVE/testnet envanteri ayrıdır. Kullanıcı dış
alarm ve emir kabulünü erteledi; derlenmiş Pine ve mock testleri gerçek emir
kabulünün tamamlandığı anlamına gelmez. Ayrıntı [middleware README](MIDDLEWARE.md),
[Spot backlog durum eşlemesi](ALGOTRADING_SPOT_BACKLOG.md) ve plandaki P1-3'tedir.

## Strateji puanları ve bağımlılıklar

COMBO MACD, RSI, Williams %R ve CCI için en fazla dört alış/satış puanı üretir.
+4/-0 dört alış puanıdır. Günlük/haftalık AL4–SAT3, diğer tanımlı periyotlar
AL3–SAT3; bilinmeyen periyot fallback'i AL4–SAT4'tür. Kesin eşitsizlikler
`signals.py::calculate_combo_signal` içindedir.

HUNTER 15 gösterge koşulunu sayar: RSI, hızlı RSI, CMO, BOP, MACD, Williams %R,
CCI, Ultimate Oscillator, Bollinger %B, ROC, DeMarker, PSY, Z-Score, Keltner %B,
RSI(2). Dip eşiği 1D/W-FRI/2W-FRI için 7, 3W-FRI/ME için 5; tepe eşiği 10'dur.
DipScore=7/7 gösterge puanı/gerekli puan, ActiveIndicators=X/15 kullanılabilir
gösterge sayısıdır. NaN atlanır; eşik azaltılmaz. RSI bağımsız zorunlu onay değildir.
Signals.py config'ten yalnız MIN_PERIODS ithal eder; eşikler fonksiyonlarda
sabittir. Config eşik nesnesini değiştirmek hesaplamayı değiştirmez.

Tarama periyotları pandas resample adlarıdır; API/chart zaman dilimi
parametreleriyle aynı metinler değildir. HUNTER kısa ATR düzeltildi;
frontend COMBO'nun geçerli sıfır değer fallback'i ve Pine EMA/ATR başlangıç
sınırları P3-1'de düzeltildi. Güncel Pine'ın 21 Eylül derleme/grafik kabulü
[ayrı kayıttadır](PINE_RUNTIME_ACCEPTANCE.md); üç motorun bütünüyle eşdeğer
olduğu doğrulanmadı. [Ölçülen farklar](STRATEGY_COMPARISON.md) korunur.

Seçili ortam Python 3.12, Node 20.20.2/npm 10.9.9; frontend Next 16.3.5 /
React 19.2.3 / TS 5.9.3. Kesin paket kaynakları requirements-dev.lock ve
frontend/package-lock.json'dır; requirements.txt alt/üst sınırlar içerir.
Gemini'nin öncelikli SDK'sı google-genai; eski SDK yalnız opsiyonel fallback'tir.
Signals.py, opsiyonel pandas_ta yokluğunda lock'taki ta ile accessor sağlar.

## Frontend veri ve erişim sınırları

- Ana ekran /; sayfalar frontend/src/app altındaki App Router klasörleridir.
  HTTP /api, bot sağlığı /health-api proxy'sinden gelir.
- Backend WS/SSE ve doğrudan Binance WS ayrı kanallardır. Birindeki hata
  diğerinin de bozuk olduğunu kanıtlamaz; bağlantılar ayrı incelenir.
- /chart?symbol=BTCUSDT&market=Kripto başlangıç seçimini taşır. Route helper
  girdiyi normalize eder; sembolün borsada listeli olduğuna dair kontrol yapmaz.
- /signals CSV çıktısı yüklenmiş ve filtrelenmiş satırlardır; tüm tarihsel DB
  export'u değildir. Hatalı/yüklenen/boş veri durumunda export devre dışıdır.
- /alarms RSI/Williams %R/COMBO/HUNTER kurallarını sayfa açıkken 60 saniyelik tur veya
  manuel kontrolle değerlendirir. Kural/watchlist tarayıcıda saklanır; farklı
  sekmeler eşgüdümlenir fakat localStorage eşzamanlı yazılarda transaction sağlamaz.
  Veri yok/hata/kapalı/koşul sağlandı durumları ayrıdır; sunucuda sürekli alarm yoktur.
- /settings sunucu ve tarayıcı ayarlarının kapsamını açıklar; tarayıcı tercihleri
  ilgili ekranlardan düzenlenir. Backend API anahtarları veya trading yetkisi
  buradan yönetilmez. Token yalnız sekme belleğindedir; refresh/expiry/logout
  oturumu bitirir, hesap değişimi özel sorgu/component durumunu temizler.
- POST /analyze/{symbol} ve /logs admin; inspector ve yeni AI analizi user/admin
  JWT ister. Dashboard okuma endpointlerinin tamamı özel değildir. Middleware
  X-Admin-Token ve webhook kimliği bu JWT hattından ayrıdır.

## Veritabanı ve compatibility

| Veri yolu | Şema kaynağı | Migration/startup |
|---|---|---|
| Ana SQLite | `models.py`, `db_session.py`; legacy `database.py` de var | init_db, create_all, uyumlu kolon/index ekleme; Compose main-init |
| Fiyat önbelleği | `price_cache.py`, ayrı SQLite dosyası | Kendi cache şeması; emir ledger'ı değildir |
| Middleware | `middleware/infra/models.py`, ayrı PostgreSQL | `middleware/infra/alembic/` revision zinciri; migrate-middleware, sonra güncel revision kontrolü |

Ana migrate_db.py eski kayıt taşıma aracıdır; genel deploy/middleware migration
komutu değildir. Kaynak/hedef, WAL yedeği ve tekrar çalıştırma sınırları
[DB politikasında](DB_MIGRATION_POLICY.md) açıklanır. Ana SQLite için yazılmış
eski “Alembic yok” yorumları bütün repository'ye genellenmez.

Canonical servisler application.services, API repository'leri
infrastructure.repositories, scanner persistence infrastructure.persistence
altındadır. api.services.*, api.repositories.* ve belirli root dosyaları
compatibility yüzeyidir. db_session.py/models.py root'ta gerçek uygulamadır;
paketlenmiş oldukları varsayılmaz. Tam liste [haritada](PACKAGING_REFACTOR_MAP.md).
Wrapper telemetry süreç içi modül kayıtlarını sayar; sıfır snapshot dış tüketici
yokluğunu kanıtlamaz. Kaldırma kararı [kanıt kapılarına](WRAPPER_DEPRECATION_SCHEDULE.md) bağlıdır.

## Test ve operasyon

Kurulum/komut kaynağı [README](../README.md) ve [geliştirme ortamı](RAPOT_DEVAM_PLANI.md#geliştirme-ortamı-ve-komutlar).
Kök conftest.py, pytest.ini ile iki Python test dizinini gerçek .env/DB/ağdan
izole eder. Node testleri ayrıca npm test ile çalışır. Frontend build ardından
npm run test:standalone, yerel HTTP/WS proxy mock'larını sınar. Bu testler gerçek
AI/Telegram/emir hizmetlerinin dış kabulünün yerine geçmez.

Üretim Compose 2.24+, API/bot/frontend ve opsiyonel middleware/PostgreSQL;
main-init/middleware-migrate başlangıç işleridir. API ve bot ayrıdır, embedded
bot kapalıdır. Aynı DB dizini WAL/SHM/kilit dahil paylaşılır; middleware bu dizini
bağlamaz. Kullanılmayan eski PM2/API launcher dosyaları 21 Eylül repo
temizliğinde kaldırıldı; desteklenen dağıtım yolu Docker Compose'dur.

Nginx HTTPS proxy host'ta 127.0.0.1:3000/8000/5000/8001 kullanır. Next container
build hedefleri http://api:8000, http://bot:5000 olur; container içi localhost
ile host loopback'i karıştırılmaz. [DEPLOY.md](DEPLOY.md) doğrulanmış SHA,
yedek, migration, health ve rollback adımlarının kaynağıdır.

Push CI çalıştırır; deploy.yml imaj yayınıdır, SSH deploy'u değildir.
Scripts/deploy.ps1 sunucu komutlarını yazdırır. Frontend, backend ve belge
commit'i farklı olabilir; yalnız belge yayını uygulama sürümünü değiştirmez.
Commit mesajları için mevcut bağlamdaki tercih: tip: kısa Türkçe özet.

## Doğrulama ve teknik sınırlar

P2-3 kaynak düzeltmeleri: tüm tracked Python'da Ruff lint/format, ortak
`infrastructure.time.utc_now_naive` ile mevcut UTC-naive tarih sözleşmesi,
kanıtlanan atıl frontend dosyalarının temizliği ve iç worktree'nin korunarak
ana repository kapsamından ayrılması. Python Bandit/pip-audit bulguları
report-only raporlanır; araç/rapor/kapsam hataları CI'yi başarısız yapar.
Frontend kilitli bağımlılık audit'i bulgularda da başarısız olur;
[güvenlik incelemesi](FRONTEND_DEPENDENCY_SECURITY.md) kapsamı açıklar.
P2-4'ün eşzamanlı API/WS ve ilk mum yükleme kabulü devam planında kayıtlıdır;
tek başarılı health isteği yük testinin yerine geçmez. P3-1'in altı geliştirme
adımı ve güncel Pine grafik kabulü tamamlandı; gerçek piyasa getirisi veya tam
motor eşdeğerliği iddia edilmez. P1-3 gerçek alarm/filtre/testnet/emir kabulü
kullanıcı tarafından ertelidir.

Değişiklik yaparken ilgili API → servis → repository → frontend hook/component
zincirini birlikte kontrol et; DB ve strateji değişikliklerinde ilgili motor/
legacy okuyucu etkisini doğrula. Güncel kabul kanıtını devam planına ekle;
bu belgeye tekrar ölçülmemiş performans veya tamamlanma iddiası ekleme.
