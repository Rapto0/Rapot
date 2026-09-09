# Rapot Devam Planı

Bu belge, 6 Eylül 2026 tarihli salt okunur proje incelemesinden çıkan işleri ve uygulama ilerlemesini takip eder. Çalışma yöntemi: **incele → düzelt → doğrula → belgeyi güncelle**.

## Kaldığımız nokta

- **Son yerel çalışma:** P1-3 — Pine Binance Spot/standart grafik koruması, webhook zaman/index sınırları ve v1 tekrar sözleşmesi uygulandı (2026-09-09). Gerçek Pine derlemesi/alarm/testnet kabulü açık.
- **Uygulama durumu:** P0 işleri, P1-1 ve P1-7 doğrulandı. P1-3 sonrası tam Python paketi **403/403**; bir mevcut tarih deprecation warning'i kaldı. 52 backend ve 22 Pine kaynak sözleşmesi testi eklendi. Frontend kodu bu adımda değişmedi; önceki 12/12 ve build/proxy kanıtı P1-2'de kayıtlı.
- **P1-2 durumu:** Yerel kod ve Linux CI imaj kontrolleri doğrulandı; gerçek VPS geçişi SSH erişimi nedeniyle engellendi. Madde bütünüyle tamamlandı sayılmıyor.
- **Uzak doğrulama başlangıcı:** Önceki grup `89890f8` ile main'de; [CI 34369220615](https://github.com/Rapto0/Rapot/actions/runs/34369220615) başarılı. P1-3 değişikliklerinin yeni commit/CI kaydı ayrıca eklenecek. Sunucu deploy'u yapılmadı.
- **Aktif adım:** P1-3 yerel checkpoint'ini commit/push et ve Linux CI sonucunu doğrula. TradingView misafir editörü Add to chart aşamasında giriş istiyor; kullanılabilir oturum yok. Testnet hesabı/DB/izin bilgileri de doğrulanmadı.
- **Sıradaki bağımsız kod işi:** P1-4 — scanner AI ilişkileri ve scan history. P1-2 VPS geçişi ile P1-3 dış kabul testleri erişim/hesap koşulları sağlandığında ayrıca sürdürülecek.
- **Başlangıç kaydı:** Bu belge ilk oluşturulduğunda yalnız belge değişmişti; sonraki uygulama değişiklikleri aşağıda ayrı kaydedildi.
- **Seçilen geliştirme ortamı:** `.venv` / Python 3.12; Node 20.20.2 / npm 10.9.9. Yerelde Python 3.12.8 ile doğrulandı.
- **Commit / yayın düzeni:** Her tamamlanan P maddesi ayrı commit; doğrulanan grup CI için push edilir, sunucu deploy'u CI ve sunucu kontrollerinden sonra yapılır. İlk sunucu yayını eşiği P0 işleri + P1-7 test hatası + P1-2 dağıtım uyumu.
- **Açık kararlar:** VPS erişimi ve mevcut süreç/veri durumu, testnet kabul testinin hesap/izin bilgileri ve ileride middleware'in dashboard'a bağlanıp bağlanmayacağı. Hedef topoloji Compose, Docker Python 3.12.8 ve ayrı middleware PostgreSQL olarak belirlendi.

## Kapsam ve yetki kaydı

Kullanıcının ilk isteği yalnız inceleme ve raporlamaydı; dosya değişikliği, kod yazma ve commit açıkça yasaktı. Sonraki isteği bu takip belgesinin tutulmasını ve uygulamada yukarıdaki dört adımın izlenmesini belirledi.

- Kullanıcının P0-1 isteğiyle bu madde için gerekli yerel kod/test/konfigürasyon değişiklikleri, geliştirme bağımlılıklarının kurulması ve izole doğrulama kapsam dahilindedir. P0-1 tamamlandı; sonraki uygulama yetkisi aşağıda kaydedildi.
- Kullanıcının "Devam et" talimatıyla sıradaki P0-2 başlatıldı; backend yetki kontrolleri, bunları kullanan frontend giriş akışı, test ve belge değişiklikleri kapsam dahilindedir.
- Kullanıcının sonraki talimatı, yapılan geliştirmelerin otomatik commit/push ve sunucu deploy'una izin verdi; zamanlamayı asistana bıraktı. Seçilen düzen: her tamamlanan iş için yerel commit; P0/P1 gibi gruplar tamamlanınca kontrollerin geçtiği commitleri push et ve sunucuda doğrulanmış deploy yap. Aynı kapsam için yeniden onay sorulmaz.
- Belgenin varlığı; bağımlılık kurulumu, kod/konfigürasyon değişikliği, migration, commit/push, deploy, servis başlatma, testnet emri veya gerçek emir için kendi başına yetki oluşturmaz.
- Sonraki kullanıcı talimatıyla kapsam değişirse bu kayıt güncellenir. Daha önce açıkça verilmiş yetki tekrar sorulmaz.
- Gerçek hesap, üretim veritabanı ve VPS üzerinde yapılan işlemler yerel geliştirme/test işlemlerinden ayrı kaydedilir.
- Deploy yetkisi, gerçek/testnet emir gönderme, veri silme, force-push veya sunucudaki bilinmeyen yerel değişiklikleri ezme yetkisi olarak yorumlanmaz.
- Gizli anahtarlar, parolalar ve token değerleri bu belgeye yazılmaz.

### Commit, push ve sunucu deploy düzeni

1. Her P maddesinde **incele → düzelt → doğrula → belgeyi güncelle → yerel commit** sırası uygulanır. Commit yalnız o işe ait dosyaları içerir. P0-1 gibi amacı başlangıç test tabanı kurmak olan işlerde mevcut davranış hataları açık iş ID'leriyle kaydedilerek checkpoint commit'i oluşturulabilir.
2. **Push**, grubun yerel tam testleri, değişen dosya lint'i ve frontend typecheck/build kontrolleri geçince CI doğrulamasını başlatır. 9 Eylül'de yerel Docker motoru açılamadığı için imaj ve geçici PostgreSQL kontrolü Linux CI'ye taşındı. **Sunucu deploy'u** için bu CI sonucu da başarılı olmalı; P0 işleri, P1-7 ve P1-2 dağıtım uyumu kapıları sağlanmalıdır. CI başlatmak için yapılan push sunucu deploy'u sayılmaz.
3. Deploy öncesinde hedef sunucu/branch, çalışan sürüm ve yerel değişiklikler okunarak kontrol edilir. Deploy, doğrulanmış commit ile yapılır; ardından sunucu commit'i, süreçler ve sağlık kontrolleri doğrulanıp buraya kaydedilir. Başarısız adımın ardından yayın zinciri ilerletilmez.
4. Bu düzen kapsamındaki commit/push/deploy için kullanıcıdan her seferinde tekrar onay istenmez. Erişim bilgisi gerçekten eksikse veya kapsam dışı veri işlemi gerekiyorsa yalnız o eksik nokta açıklanır.

**Mevcut mekanizma, koddan doğrulanan (P1-2 sonrası):** `.github/workflows/deploy.yml` release/manual tetiklemeli ve backend/frontend imajlarını tam commit SHA etiketiyle yayımlıyor; sunucu deploy'u yapmıyor. `scripts/deploy.ps1` temiz ağaç ve doğrulanmış tam SHA ister; isteğe bağlı push yapar, manuel sunucu komutlarını yazdırır, SSH çalıştırmaz. Repo içinde normal push'u sunucu deploy'una bağlayan bir workflow yok; sunucuda repo dışı otomasyon bulunup bulunmadığı henüz doğrulanmadı. Yalnız push yapılması deploy başarısı sayılmayacak.

## Başlangıç fotoğrafı

**İnceleme tarihi:** 2026-09-06
**İncelenen branch:** main
**Referans commit:** 62ff6cfff1052252555dce33c4bcbac9e41663f2

Bu bilgiler inceleme anının kaydıdır; güncel runtime veya üretim durumu olarak okunmamalıdır.

| Konu | İncelemede doğrulanan durum |
|---|---|
| Git | Belge oluşturulmadan önce staged, unstaged, untracked değişiklik ve stash yoktu |
| Uzak branch | Yerelde kayıtlı origin/main, main ile aynıydı; fetch yapılmadı |
| Son iş | 16 Haziran: Binance bakiye karşılaştırması, ardından Pine alarm yenilemesi |
| Ana mimari | Python scanner → ana DB → FastAPI → Next.js; AI/Telegram ek akışları |
| Emir mimarisi | TradingView → ayrı middleware → Binance Spot; ayrı mw_* tabloları |
| Entegrasyon | Ana scanner/dashboard ile middleware arasında doğrudan emir/yönetim bağlantısı bulunamadı |
| Yerel AI | AI_ENABLED=0 |
| Yerel ana DB | 3.579 sinyal; trade, AI analizi ve scan history tabloları boş |
| Yerel kayıt tarihi | Son sinyal 2026-02-07; bot istatistiği 2026-04-01 |
| Ortamlar | .venv, venv ve sistem Python bağımlılıkları farklı; aktif Node 22, proje Node 20/npm 10 istiyor |
| Middleware ayarları | Ayrı middleware/.env yoktu; kök .env içinde MW_* ayarları bulunmadı; dışarıdan sağlanan ortam ayarları doğrulanmadı |

### Son çalışmanın kanıtları

| Commit | Tarih | Anlamı |
|---|---|---|
| ed11069 | 2026-05-13 | Osmanlı kapsamı bilinçli kaldırılıp Binance Spot'a odaklanıldı |
| 98ec10c | 2026-05-13 | Her farklı BUY yeni tranche; 10 USDT varsayılan bütçe, opsiyonel limitler |
| 8463fe5 | 2026-06-16 | Binance free/locked bakiye ile açık tranche karşılaştırması eklendi |
| 62ff6cf | 2026-06-16 | Pine dosyasında 577 ekleme / 264 silme; alarm, preset ve çoklu zaman dilimi yenilemesi |

**En son kalınan iş tahmini — yüksek güven:** TradingView Combo+Hunter sinyallerini Binance Spot'ta tekrarlı alış ve FIFO satış yapan otomasyona dönüştürme; bakiye tutarlılığını gözlemleme ve alarm üretimini düzenleme.

### Önceki doğrulama kaydı

Bu sonuçlar 2026-09-06 salt okunur incelemesinde, yukarıdaki commit üzerinde alındı. Plan dosyası hazırlanırken testler yeniden çalıştırılmadı. Sonuçlar bütün sistemin veya canlı emir akışının doğrulandığını göstermez.

| Kontrol | Sonuç ve sınır |
|---|---|
| Frontend TypeScript | tsc --noEmit --incremental false geçti |
| Frontend ESLint | eslint . --no-cache geçti |
| Kaynak temelli mimari/frontend kontrolleri | 23 test geçti; uygulama modülleri/servisleri başlatılmadı |
| Python sözdizimi | 171 dosya bellekte AST ile incelendi; Python 3.10 sözdizimi kontrolünde de hata yok |
| Ruff, ana proje | 8 bulgu; iç Claude worktree dahil edilince aynı bulgularla toplam 16 |
| Tam backend/middleware testleri | Çalıştırılmadı: log, cache ve test DB yazma yolları var |
| Next.js/Docker build | Çalıştırılmadı: derleme çıktısı oluşturuyor |
| Bot/API/migration/backtest/deploy | Çalıştırılmadı: dosya, veri veya dış servis yan etkileri var |
| Testnet/gerçek hesap/TradingView | Doğrulanmadı |

Test envanteri: ana tests dizininde 27 dosya / 152 test fonksiyonu; middleware/tests içinde 10 dosya / 26 test fonksiyonu. Parametrizasyon gerçek yürütme sayısını değiştirebilir.

Kaynak temelli 23 test için kullanılan salt okunur komut:

    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
    python -B -m pytest --noconftest -p no:cacheprovider -o addopts= tests/test_architecture_boundaries.py tests/test_frontend_contracts.py -q

Bu komuttaki --noconftest, yalnız bu iki kaynak okuma test dosyası için kullanıldı. Tam test paketine uygulanarak fixture'lar atlanmamalıdır.

Ruff başlangıç bulguları: main.py:41 SIM105; scripts/backfill_signal_details.py:21-22 iki E402 ve bir I001; signals.py:46 E741 ve :485 B007; tests/test_config.py:38 B017 ve :66 SIM118.

### Belirsiz kalanlar

- VPS'de çalışan commit, süreçler, erişim sınırları ve gerçek hesap durumu.
- TradingView'de yüklü Pine sürümü, preset ve alarm ayarları.
- Testnet/canlı kabul testlerinin geçmişte tamamlanıp tamamlanmadığı.
- backup/pre-da7d452-rollback branch'indeki beş ayrı commitin yeniden istenip istenmediği.
- Eski backlog'lardaki boş kutuların güncel karşılığı. Bazı işlerin kodu uygulanmış; kutular doğrudan eksik iş kanıtı değildir.

## İşleme ve doğrulama kuralları

### Durumlar

| Durum | Anlamı |
|---|---|
| Bekliyor | Uygulama başlamadı; önceki inceleme bulgusu mevcut olabilir |
| Devam ediyor | İş aktif; hangi aşamada olduğu ilerleme kaydında yazılı |
| Doğrulandı | Kabul kriterleri sağlandı, ilgili kontroller geçti ve kanıtlar belgeye işlendi |
| Engellendi | Somut bir bağımlılık, eksik bilgi veya dış koşul ilerlemeyi durduruyor; çözülme şartı yazılı |
| Ertelendi | Bilinçli kapsam/ürün kararıyla sonraya bırakıldı; gerekçe yazılı |

### Her iş için dört adım

1. **İncele:** Bulguyu güncel kodda yeniden kontrol et. Mevcut davranışı, beklenen davranışı, etkilenen dosyaları, bağımlılıkları ve test ihtiyacını kaydet. Önceki raporu değişmez gerçek kabul etme.
2. **Düzelt:** İşin kapsamına odaklan. Gerekli kararları ve beklenmeyen etkileri kaydet. Sırf plan maddesi var diye ilgisiz refactor yapma.
3. **Doğrula:** Değişiklikle ilgili testleri/kontrolleri çalıştır. Sonuçları, ortamı ve çalıştırılmayan kontrolleri yaz. Finansal durum, yetki ve migration değişikliklerinde ilgili hata senaryolarını da doğrula.
4. **Belgeyi güncelle:** Özet tablodaki durumu, kabul kutularını, değişen dosyaları, test kanıtlarını, kararları ve sıradaki adımı birlikte güncelle. Doğrulama eksikse işi Doğrulandı yapma.

**Doğrulama katmanları birbirinin yerine geçmez:**

- Kaynak incelemesi / lint / tip kontrolü.
- İzole yerel davranış ve entegrasyon testleri; sahte broker ve test verisi.
- İzin kapsamına alınmış testnet kabul testi.
- Ayrı kapsamı olan gerçek ortam doğrulaması.

Testnet başarısı gerçek hesapta doğrulama anlamına gelmez. Otomatik state onarımı ile yalnız fark raporlama ayrı davranışlardır.

## Öncelik ve bağımlılık özeti

Kapsam tahminleri süre taahhüdü değildir: küçük birkaç dosya; orta bir özellik ve testleri; büyük birden fazla katman veya migration.

| ID | İş | Durum | Kapsam | Bağımlılık |
|---|---|---|---|---|
| P0-1 | Tek ortam ve izole test tabanı | Doğrulandı | Orta | Yok |
| P0-2 | Admin ve kritik API yetkilendirmesi | Doğrulandı | Orta | P0-1 |
| P0-3 | DRY_RUN/LIVE envanter ayrımı | Doğrulandı | Büyük | P0-1; mevcut veri sınıflandırması |
| P0-4 | Emir sonucu ve pozisyon tutarlılığı | Doğrulandı | Büyük | P0-1, P0-3 |
| P1-1 | Komisyon, hassasiyet, limit ve replay doğruluğu | Doğrulandı | Orta/büyük | P0-3, P0-4 |
| P1-2 | Çalıştırma ve dağıtım topolojisi | Kod/imaj CI doğrulandı; VPS erişimi engellendi | Orta | P0-1; gerçek sunucu erişimi |
| P1-3 | Pine sözleşmesi ve testnet kabul akışı | Yerel sözleşme doğrulandı; Pine/testnet kabulü açık | Orta | Tüm P0 işleri, P1-1; dış kabul için P1-2 |
| P1-4 | AI ilişkileri ve scan history | Bekliyor | Orta | P0-1 |
| P1-5 | Süreçler arası realtime ve scanner eşdeğerliği | Bekliyor | Orta/büyük | P0-1, P1-2 |
| P1-6 | PnL, bot durumu ve ayarlar ekranı | Bekliyor | Orta | P0-1; backend ayar sözleşmesi ve P0-2 |
| P1-7 | HUNTER kısa seride ATR hatası | Doğrulandı | Küçük/orta | P0-1 |
| P2-1 | Dışa aktar, alarmlar ve grafik URL davranışı | Bekliyor | Orta | P0-1 |
| P2-2 | Belgeler ve wrapper göçünün kapanışı | Bekliyor | Küçük/orta | İlgili mimari kararlar; kaldırma için kullanım kanıtı |
| P2-3 | Ruff, atıl kod ve araç tarama kapsamı | Bekliyor | Küçük/orta | P0-1 |
| P3-1 | Backtest ve strateji eşdeğerliği | Bekliyor | Büyük | Emir/veri doğruluğu, P1-3, P1-4 |
| P3-2 | Backup branch tasarım değerlendirmesi | Bekliyor | Küçük inceleme | Tasarım tercihi |

**Önerilen sıra:** P0-1 → P0-2 → P0-3 → P0-4. Ardından P1-1 ve P1-2; bunların ardından P1-3. Diğer işler kendi bağımlılıkları sağlandığında yürütülür.

## P0 — Önce tamamlanacak işler

### P0-1 — Tek geliştirme ortamı ve izole test tabanı

**Neden:** Üç Python ortamı farklı; Node sabitlemesiyle aktif sürüm farklı. Middleware fixture'ı sabit bir test DB'si oluşturup siliyor. Ana modül importları log/cache açabiliyor. CI middleware testlerini kapsamıyor.

**Değişen dosyalar:** [requirements-dev.txt](../requirements-dev.txt), [requirements-dev.lock](../requirements-dev.lock), [.python-version](../.python-version), [pyproject.toml](../pyproject.toml), [pytest.ini](../pytest.ini), [kök conftest](../conftest.py), [ana fixture](../tests/conftest.py), [middleware fixture](../middleware/tests/conftest.py), [izolasyon testleri](../tests/test_test_isolation.py), [scanner testleri](../tests/test_market_scanner.py), [database.py](../database.py), [price_cache.py](../price_cache.py), [CI](../.github/workflows/ci.yml), [.nvmrc](../.nvmrc), [frontend/.nvmrc](../frontend/.nvmrc), [frontend/package.json](../frontend/package.json), [.gitignore](../.gitignore), [.dockerignore](../.dockerignore), iki README ve bu belge. `logger.py` değişmedi; loglar test çalışma dizini üzerinden ayrıldı.

**Kabul kriterleri:**

- [x] Seçilen Python/Node ortamı ve yeniden kurulum/test komutları kaydedildi; paket kurulumu tek başına tamamlanma sayılmadı.
- [x] Testlerde DB/log/cache ayrı geçici alanda veya bellekte; gerçek .env anahtarları kullanılmıyor ve dış emir/bildirim bağlantıları kapalı/sahte.
- [x] Test toplama ve import yan etkileri incelendi; fixture atlayarak sahte yeşil sonuç üretilmiyor.
- [x] Ana backend ve middleware testleri çalıştırıldı; başarısızlıklar iş ID'leriyle kaydedildi. Davranış hataları gizlenmeden tekrar üretilebilir bir başlangıç tabanı kuruldu.
- [x] CI middleware testleri ile frontend lint/typecheck kontrollerini kapsıyor; uygun build kontrolü tanımlandı.

**İnceleme sonucu:** `database.py` ve `price_cache.py`, mevcut settings alanlarına rağmen depo içindeki DB dosyalarını sabit açıyordu. Middleware fixture'ı sabit test dosyasını silip yeniden oluşturuyordu. `api.main._market_data_provider` ilk testin mock fonksiyonlarını saklayıp sonraki teste taşıyordu; kripto mum testinin mock'u bu nedenle etkisiz kalıyordu. İki özel sinyal testi ikinci BIST kaynağını taklit etmiyordu.

**Düzeltme:** DB/cache yolları settings üzerinden okunuyor. Göreli yollar çalışma dizinine göre çözülür; normal kullanımda repo kökünden çalıştır veya mutlak yol ver. Kök pytest kurulumu uygulama testleri toplanmadan önce sentetik ortamı, geçici çalışma dizinini, SQLite sınırını ve ağ engelini kuruyor. Alt conftest dosyalarında uygulama/ayar importları fixture içine alındı. Her ana testte ORM/legacy DB/cache ve API sağlayıcı/önbellek durumu yenileniyor. Her middleware testinde ayrı SQLite, varsayılan DRY_RUN ayarları ve sahte broker kullanılıyor; testler modları kendi sentetik verileriyle değiştirebilir. İkinci kaynak mock'una veri tazelik bilgisi eklendi; gerçek doğrulayıcı ilk testte çalışmaya devam ediyor.

**Doğrulama (2026-09-06):**

| Kontrol | Sonuç |
|---|---|
| Python / bağımlılıklar | Python 3.12.8, uv 0.9.26; lock dosyasıyla `.venv` eşitlendi; 120 kurulu paket için bağımlılık tutarlılığı geçti |
| Tam pytest + coverage | 189 test; **185 geçti, 4 başarısız**, 1 deprecation warning; çıkış kodu 1 |
| Ana backend | 163 testin 159'u geçti; dört HUNTER hatası P1-7'ye kaydedildi |
| Middleware | 26/26 geçti; gerçek broker çağrısı yok |
| Yeni izolasyon kontrolleri | 11/11 geçti: sentetik ayarlar, gerçek DB erişiminin reddi, testler arası DB/cache ayrımı, requests/httpx/curl/socket/DNS/async ağ engeli ve MockTransport kullanımı |
| Coverage | `coverage.xml` üretildi; ilk ölçüm 4.674/9.423 satır (%49,6). Tüm davranışların doğrulandığı anlamına gelmez |
| Değişen Python dosyaları | Ruff lint ve format kontrolü geçti (7 dosya); önceki tüm-repo Ruff borcu P2-3'te açık |
| Frontend kurulum | Node 20.20.2 / npm 10.9.9 altında `npm ci`; 424 paket kuruldu |
| Frontend kontrolleri | ESLint, `tsc --noEmit --incremental false` ve Next.js 16.2.1 production build geçti; 14 statik sayfa üretildi |
| Mevcut veriler | `trading_bot.db`, `price_cache.db`, `trading_bot_new.db` SHA-256 değerleri test öncesi/sonrası aynı |

**Açık sonuçlar:** P1-7'deki dört test CI'de de çalışacak ve düzeltilene kadar test job'unu başarısız yapacak. `datetime.utcnow()` uyarısı P2-3'e kaydedildi. Docker/Python 3.10 ile bazı modüllerin `datetime.UTC` importları arasındaki uyumsuzluk P1-2'de ele alınacak; yerel geliştirme ve CI bu aşamada Python 3.12 kullanıyor. GitHub Actions uzaktan çalıştırılmadı; Linux ve Docker build, tarayıcı davranışı, testnet ve canlı hesap doğrulanmadı. Commit/push/deploy yapılmadı.

### Geliştirme ortamı ve komutlar

Tek Python çalışma ortamı `.venv`; eski `venv` ve sistem Python silinmedi veya proje bağımlılıklarıyla güncellenmedi. `requirements.txt` uygulamanın sürüm aralıklarını, `requirements-dev.txt` test araçlarını, `requirements-dev.lock` Python 3.12 için tam sabitlenmiş geliştirme/CI çözümünü tutar. Normal kurulumda lock dosyasını kullan. `pytest.ini` tek pytest ayar kaynağıdır; coverage ayarları `pyproject.toml` içindedir.

Repo kökünde PowerShell (uv 0.9.26 ile doğrulandı):

```powershell
# Yalnız .venv henüz yoksa oluştur:
uv venv --python 3.12 .venv

# Var olan .venv'yi de lock dosyasındaki paketlerle eşitle:
uv pip sync --python .venv/Scripts/python.exe requirements-dev.lock
uv pip check --python .venv/Scripts/python.exe

# Her iki test dizinini toplar; .env veya gerçek servis gerekmez:
.venv/Scripts/python.exe -X utf8 -B -m pytest
.venv/Scripts/python.exe -X utf8 -B -m pytest --cov=. --cov-report=xml

# Belirli testler için de aynı izolasyon devrede kalır:
.venv/Scripts/python.exe -X utf8 -B -m pytest middleware/tests
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_test_isolation.py
```

Linux/macOS'ta aynı komutlarda yorumlayıcı yolu `.venv/bin/python` olur. CI temiz ortamda `python -m pip install -r requirements-dev.lock` ve `python -m pip check` kullanır. CI Python sürümünü `.python-version` dosyasından okur.

Frontend için `.nvmrc` dosyalarındaki Node 20.20.2 ve `packageManager` alanındaki npm 10.9.9 kullanılır. Bu ortam seçildikten sonra `frontend` klasöründe:

```powershell
npm ci
npm run lint -- --no-cache
npm run typecheck -- --incremental false
$env:NEXT_TELEMETRY_DISABLED = '1'
npm run build
```

Node sürüm yöneticisi olmayan bu Windows makinesinde sistem Node 22'yi değiştirmeden kullanılan alternatif:

```powershell
cd frontend
npm.cmd exec --yes --package=node@20.20.2 --package=npm@10.9.9 -- node --version
npm.cmd exec --yes --package=node@20.20.2 --package=npm@10.9.9 -- npm ci --no-audit --no-fund
npm.cmd exec --yes --package=node@20.20.2 --package=npm@10.9.9 -- npm run lint -- --no-cache
npm.cmd exec --yes --package=node@20.20.2 --package=npm@10.9.9 -- npm run typecheck -- --incremental false
$env:NEXT_TELEMETRY_DISABLED = '1'
npm.cmd exec --yes --package=node@20.20.2 --package=npm@10.9.9 -- npm run build
```

Test kurulumu; mevcut Settings/MiddlewareSettings ortam alanlarını temizler, sentetik değerler verir ve gerçek `.env` bulunmayan geçici dizine geçer. Ana/middleware DB'leri ve ana fiyat önbelleği test başına ayrıdır; import logları ve yfinance önbelleği test koşumuna özel geçici alandadır. SQLite'ın bu alan dışındaki dosyalara bağlanması reddedilir; pytest-cov'un repo içindeki `.coverage*` rapor dosyaları istisnadır. `--basetemp` güvenlik için koşuma özel dizinle değiştirilir. Bağlantılar test sonunda kapatılır; geçici alan koşum sonunda temizlenir. `.coverage`, `coverage.xml`, `.pytest_cache` ve frontend build çıktıları Git dışında tutulur.

Eksik dış servis mock'u, ilgili HTTP/socket/curl katmanında testi başarısız yapar. ASGI `TestClient`, `httpx.MockTransport` ve Windows asyncio iç socketpair'i çalışır. Yeni testlerde uygulama modüllerini alt `conftest.py` dosyasının üst seviyesinde import etme; kök `pytest_configure` korumalarından sonra fixture içinde yükle. Bu, mevcut test paketi için izolasyondur; keyfi subprocess/native programları kapsayan işletim sistemi sandbox'ı değildir. Bot/API'yi normal başlatmak bu test korumalarını kullanmaz.

Bağımlılık güncellemesi gerektiğinde lock'u `uv pip compile requirements-dev.txt --python-version 3.12 --universal --no-header --no-annotate -o requirements-dev.lock` ile yeniden çöz ve tüm kontrolleri tekrar çalıştır. Sıradan test çalıştırmak lock dosyasını yenilemez.

### P0-2 — Admin ve kritik API yetkilendirmesi

**İncelemede doğrulanan sorun:** Admin replay yalnız özellik bayrağı kontrol ediyordu; kimlik doğrulaması yoktu. Ana API'nin log, manuel tarama, strateji inceleme ve AI üretim yollarında mevcut JWT altyapısı uygulanmamıştı. Dashboard'da bu korumaları kullanabilecek giriş akışı bulunmuyordu.

**Değişen dosyalar:** [middleware dependencies](../middleware/api/dependencies.py), [middleware routes](../middleware/api/routes), [middleware settings](../middleware/infra/settings.py), [middleware env örneği](../middleware/.env.example), [api/auth.py](../api/auth.py), [api/main.py](../api/main.py), [auth routes](../api/routes/auth_routes.py), [system routes](../api/routes/system_routes.py), [OpenAPI snapshot](contracts/openapi.snapshot.json), [giriş ekranı](../frontend/src/app/login/page.tsx), [oturum modülü](../frontend/src/lib/auth/session.ts), [oturum hook'u](../frontend/src/lib/hooks/use-session.ts), [auth API istemcisi](../frontend/src/lib/api/auth-api.ts), [ortak API istemcisi](../frontend/src/lib/api/core.ts), [providers](../frontend/src/components/providers.tsx), [oturum kontrolleri](../frontend/src/components/auth/session-controls.tsx), desktop/mobile header, iki test fixture'ı, ana API yetki/analiz/sözleşme testleri, middleware yetki testleri, frontend oturum testleri, frontend package.json, CI, üç README ve bu belge.

**Kabul kriterleri:**

- [x] Tokensız/geçersiz yetkili admin replay isteği emir niyeti veya broker çağrısı oluşturmadan reddediliyor.
- [x] Geçerli yetki ve admin kapalı senaryoları ayrı test edildi; replay idempotency bypass yetkisi açıkça tanımlandı.
- [x] Ana API'deki log, analiz ve yönetim işlemleri için erişim ve rate-limit politikası uygulandı; meşru istemci akışı korunuyor.
- [x] Değişen işlem yollarına enjekte edilen gizli hata metinlerinin HTTP yanıtı/loglara taşınmadığı test edildi. Bu, tüm uygulama ve geçmiş loglar için genel sızıntı denetimi değildir; gerçek sunucu maruziyeti doğrulanmadı.

**Düzeltme ve erişim politikası:**

| Yol / işlem | Gereken yetki | Limit / davranış |
|---|---|---|
| Ana API `POST /auth/token` | Kullanıcı adı/parola | 5/dakika; yanlış parola veya devre dışı kullanıcı 401 |
| Ana API `/logs` | Admin JWT | 30/dakika; satır sınırı 1–500 |
| Ana API `POST /analyze/{symbol}` | Admin JWT | 2/dakika |
| Ana API `/ops/strategy-inspector` | Kullanıcı/admin JWT | 30/dakika |
| Ana API `/market/analysis` ve `/api/market/analysis` | Kullanıcı/admin JWT | İki alias için ortak 2/dakika |
| Middleware `/admin/replay-signal`, `/admin/reconcile/{symbol}` | Admin bayrağı açık + ayrı `X-Admin-Token` | Bayrak kapalı 403; eksik/yanlış istek token'ı 401; eksik veya webhook ile aynı sunucu anahtarı 503 |
| Middleware `/orders`, `/positions`, `/positions/{symbol}`, `/signals` | Ayrı `X-Admin-Token` | Webhook token'ı ve URL token'ı kabul edilmez; admin bayrağından bağımsız kimlik doğrulama |

Ana API limitleri mevcut SlowAPI yapısında istemci IP'sine ve süreç içi belleğe bağlıdır; çoklu worker/ortak proxy sınırı merkezi değildir. Bu dağıtım kısıtı P1-2'de dikkate alınacak. JWT `exp` alanı zorunlu; süresi geçmiş/geçersiz JWT 401, geçerli JWT'ye sahip devre dışı kullanıcı 403, normal kullanıcının admin işlemi 403 döner.

Middleware yönetim anahtarı `MW_ADMIN_AUTH_TOKEN` ile sunucuda ayrıca tanımlanmalıdır. Örnek dosyada boş bırakıldı; gerçek `.env` değiştirilmedi. Anahtar Pine'a veya frontend'e verilmez. Webhook kendi anahtarını kullanmaya devam eder. Replay'de varsayılan `bypass_idempotency=false`; yalnız yetkili admin açıkça `true` gönderirse aynı sinyal yeniden işlenebilir ve yürütme modu/trading kontrollerine göre yeni emir oluşturabilir.

Dashboard `/login` → `/auth/token` → `/auth/me` akışı kullanır. Token yalnız sekme belleğinde yaşar. Yenileme, süre dolumu ve çıkış oturumu kapatır; oturum değişikliği sorgu önbelleğini ve bileşenlerdeki özel veriyi temizler. Token yalnız yapılandırılmış ana API origin/path sınırına eklenir. Geç gelen eski token 401'i yeni oturumu kapatmaz; 403 oturumu korur. Mevcut ana dashboard okumaları ve kayıtlı analizler herkese açık kalır; tüm dashboard'un özel hale geldiği iddia edilmez.

**Doğrulama (2026-09-07, Python 3.12.8 / Node 20.20.2 / npm 10.9.9):**

- Tam komut: `.venv/Scripts/python.exe -X utf8 -B -m pytest --cov=. --cov-report=xml -q --tb=line`. 243 testin 239'u geçti; önceki dört `tests/test_strategy_inspector.py` HUNTER/ATR hatası ve bir `datetime.utcnow()` uyarısı devam ediyor. Yeni regresyon yok; testler atlanmadı, başarısız çıkış kodu korunuyor.
- [Ana API yetki testleri](../tests/test_api_authorization.py): 36/36; eksik/geçersiz/süresi geçmiş/son kullanma tarihi olmayan JWT, devre dışı kullanıcı, roller, gerçek login→me akışı, giriş/AI alias/manuel tarama limitleri ve hata metni sızıntısı.
- [Middleware yetki testleri](../middleware/tests/test_admin_auth.py): 18/18; tüm middleware paketi 44/44. Yetkisiz istekte broker fabrikası çağrılmadığı ve emir/sinyal kaydı yazılmadığı kontrol edildi; tüm emir işlemleri sahte broker/izole DB üzerinde.
- `npm test`: 9/9; oturum oluşturma, hatalı login/me, API origin/path sınırı, header override, 401/403 ayrımı, geç gelen yanıt ve süre dolumu. `npm run lint`, `tsc --noEmit --incremental false` ve `npm run build` geçti; build 15 statik sayfa üretti.
- Tarayıcıda üretim frontend build'i ile yerel sahte HTTP servisleri kullanıldı: yanlış parola mesajı, admin login→sağlık ekranı dönüşü, özel test logunun görünmesi, çıkışta temizlenmesi, normal kullanıcı 403 mesajı ve yenilemede oturum kaybı doğrulandı. Backend/bot veya gerçek hesap bu kontrolde çalıştırılmadı. Geçici servisler ve tarayıcı sekmesi kapandı; 8000/5000/3012 portlarında dinleyici kalmadığı kontrol edildi.
- OpenAPI snapshot test izolasyonu içinde üretildi; snapshot ve frontend auth endpoint sözleşmeleri tam pakette geçti. Frontend oturum testleri CI'ye eklendi. Değişen dosyalar için pre-commit/Ruff kontrolleri uygulandı.
- Üç mevcut DB'nin SHA-256 değerleri P0-1 kaydıyla aynı: gerçek DB değişikliği yok. Gerçek/testnet emir, migration, push ve deploy yapılmadı.

**Yayın sınırı:** P0-2 yerel commit'i `fix(auth): protect admin and analysis operations` başlığıyla tutulur; kimliği Git geçmişinden okunur. Push/deploy ilk grup eşiğini bekler. VPS erişimi, HTTPS/proxy davranışı ve sunucu anahtarlarının kurulumu bu yerel doğrulamayla tamamlanmış sayılmaz. Sonraki iş **P0-3**.

### P0-3 — DRY_RUN/LIVE envanter ayrımı

**İncelemede doğrulanan sorun:** Emirlerde `mode` vardı fakat tranche'larda ve repository sorgularında kapsam yoktu. FIFO, açık pozisyon/exposure, günlük emir/PnL sayımı, listeleme ve reconciliation aynı DB'deki bütün modları okuyordu. Ayrıca global sinyal/order idempotency anahtarı aynı alarmın ayrı ortamda işlenmesini engelleyebilirdi.

**Değişen dosyalar:** [middleware modelleri](../middleware/infra/models.py), [ayarlar](../middleware/infra/settings.py), [tranche repository](../middleware/repositories/tranche_repository.py), [order repository](../middleware/repositories/order_repository.py), [TradingService](../middleware/services/trading_service.py), [20260907_0004 migration](../middleware/infra/alembic/versions/20260907_0004_scope_inventory.py), middleware API ana giriş/yanıt modelleri/order-position route'ları, `.env.example`, README, Binance yürütme planı, test fixture'ı, [kapsam testleri](../middleware/tests/test_inventory_scope.py), [migration testi](../middleware/tests/test_inventory_migration.py), ayar testleri ve bu belge.

**Kabul kriterleri:**

- [x] Envanter kapsamı mod ve gerekli hesap/ortam kimliğiyle tanımlandı; testnet ile gerçek hesap kayıtlarının da karışmaması sağlandı.
- [x] FIFO, exposure, günlük risk sayımı, listeleme ve reconciliation aynı kapsamı kullanıyor.
- [x] DRY_RUN alış → LIVE satış geçişinde sanal pozisyonun seçilmediği izole testle gösterildi.
- [x] Eski kayıtların sınıflandırılması, belirsiz kayıtların davranışı ve migration/geri dönüş yolu örnek veri üzerinde doğrulandı.
- [x] Gerçek DB'ye uygulanmamış migration, uygulanmış olarak raporlanmadı.

**Düzeltme ve kapsam sözleşmesi:** Her yeni order ve tranche aynı `inventory_scope` değerini taşır. DRY_RUN kapsamı `DRY_RUN|broker|MW_APP_ENV|hesap-etiketi`, LIVE kapsamı `LIVE|broker|MW_BINANCE_BASE_URL-host|MW_INVENTORY_ACCOUNT_ID` biçimindedir. Hesap etiketi gizli anahtar değildir; LIVE için zorunlu, 1–64 güvenli karakterle sınırlı ve aynı hesap için kararlı olmalıdır. Testnet/üretim hostları ve farklı hesap etiketleri doğal olarak farklı kapsam üretir. DRY_RUN'da boş etiket `simulation-default` olur.

Aktif kapsam; FIFO seçimi/kilidi, cross-scope tranche güncelleme engeli, açık tranche sayısı, sembol exposure'ı, günlük order/PnL toplamı, order/position/tranche listeleri ve reconciliation için repository seviyesinde uygulanır. Order/pozisyon/reconciliation yanıtları mod ve kapsamı açıkça gösterir. Webhook signal tablosu global denetim geçmişi olarak kalır; order idempotency anahtarı kapsamla hash'lendiği için aynı alarm her kapsamda bir kez işlenebilir ve aynı kapsamda duplicate kalır.

Migration `20260907_0004`, geçmiş order'larda hesap/venue kimliği kanıtlanamadığı için hepsini `LEGACY_UNCLASSIFIED` kapsamına alır; tranche `mode` bilgisini ilişkili açılış order'ından taşır, ilişkisiz satırı `LEGACY` yapar. Bu kayıtlar silinmez ve hiçbir aktif kapsamda görünmez/seçilmez. Broker geçmişiyle doğrulanmadan otomatik olarak güncel hesaba atanmaz. Downgrade yeni kolon/indeksleri kaldırır ve satırları korur.

**Doğrulama (2026-09-07, Python 3.12.8):**

- Tam komut: `.venv/Scripts/python.exe -X utf8 -B -m pytest --cov=. --cov-report=xml -q --tb=line`. 249 testin 245'i geçti; yalnız önceden P1-7'ye kaydedilen dört HUNTER/ATR hatası ve bir `datetime.utcnow()` uyarısı devam ediyor. Yeni regresyon yok.
- Middleware paketi 50/50 geçti. Üç entegrasyon testi DRY_RUN alış→LIVE satış izolasyonunu; aynı sinyalin kapsam bazlı idempotency'sini; açık tranche, exposure ve günlük order risk toplamlarını; testnet/üretim ve iki hesap ayrımını; kapsamlı order/position listesi ile reconciliation'ı sahte broker ve geçici SQLite üzerinde doğruladı. Hiçbir borsa isteği/emri yapılmadı.
- Migration testi geçici eski şema ve üç örnek tranche üzerinde upgrade/downgrade yaptı: DRY_RUN/LIVE mode bilgisi taşındı, bilinmeyen hesap/venue `LEGACY_UNCLASSIFIED` kaldı, kolonlar NOT NULL oldu ve downgrade sonrası üç satır korundu.
- Alembic PostgreSQL offline `upgrade head --sql` ve `20260907_0004:20260501_0003` downgrade SQL üretimi geçti. Bu yalnız SQL derleme kontrolüdür; PostgreSQL sunucusuna bağlanılmadı ve gerçek DB'ye migration uygulanmadı.
- `ruff check middleware`, değişen dosya hook'ları ve `git diff --check` geçti. Üç mevcut DB'nin SHA-256 değerleri P0-1/P0-2 kayıtlarıyla aynı kaldı.

**Operasyon sınırı:** Yeni kod mevcut bir middleware DB üzerinde migration çalışmadan başlatılmamalıdır; `Base.metadata.create_all()` mevcut tablolara yeni kolon eklemez. Deploy akışı P1-2'de migration-before-start adımını güvenceye almalıdır. P0-3 yerel commit'i `fix(middleware): isolate inventory by execution scope` başlığıyla tutulur; push/deploy P0 grubu ve kayıtlı yayın koşullarını bekler. Sonraki iş **P0-4**.

### P0-4 — Emir sonucu ve pozisyon tutarlılığı

**Neden:** Adapter EXPIRED/CANCELED cevabını accepted=false yapıyor; servis bu dalda gerçekleşen miktarı uygulamadan dönüyor. Timeout sonrası borsadaki gerçek sonucu sorgulayan kurtarma yolu bulunamadı.

**Dosyalar:** [Binance adapter](../middleware/broker_adapters/binance_spot.py), [TradingService](../middleware/services/trading_service.py), [order repository](../middleware/repositories/order_repository.py), [execution report repository](../middleware/repositories/execution_report_repository.py), [tranche repository](../middleware/repositories/tranche_repository.py), [middleware testleri](../middleware/tests).

**Kabul kriterleri:**

- [x] Hem BUY hem SELL için kısmi gerçekleşme + EXPIRED/CANCELED sonucu envantere doğru miktarda yansıyor.
- [x] Tam gerçekleşme ve sıfır gerçekleşme davranışı korunuyor; yinelenen cevap/kurtarma işlemi aynı gerçekleşmeyi yalnız bir kez uyguluyor.
- [x] Timeout sonrası belirsiz emir sonucu kesin başarısız sayılıp körlemesine yeni emir üretilmiyor; client order ID üzerinden sonucu bulma yolu var.
- [x] Yeniden başlatma, yinelenen webhook ve ilgili eşzamanlılık senaryoları envanter/işlem günlüğü tutarlılığını koruyor.
- [x] Testler sahte broker ve izole DB üzerinde geçti; borsa sonucu ile yerel kayıt eşleştirmesi kanıtlandı.

**Uygulanan davranış:** Tam idempotency anahtarı SHA-256 ile 36 karakterlik Binance client order ID'ye çevrilip emir gönderilmeden önce order satırına yazılıyor. Timeout, bozuk cevap, sunucu hatası veya yeniden başlatma sonrası yinelenen client ID cevabı aynı kimlikle sorgulanıyor. Sonuç bulunamazsa durum `unknown` kalıyor; yeni emir gönderilmiyor. Yetkili `POST /admin/recover-order/{order_id}` aynı sorguyu daha sonra tekrar çalıştırıyor. Broker'ın `executedQty` değeri kümülatif kabul ediliyor; order satırındaki önceki toplamdan yalnız pozitif fark tranche'a uygulanıyor. Son durum geriye gitmiyor ve bilinen broker order ID sonraki boş cevapla silinmiyor.

**Doğrulama:** Middleware paketi 61/61 geçti. Dokuz yeni recovery testi; kısmi BUY+CANCELED, kısmi SELL+EXPIRED, sıfır fill, yinelenen webhook, belirsiz timeout, tekrarlı kurtarma, ardışık kümülatif fill ve ağırlıklı fiyat, yeniden başlatma sonrası yinelenen client ID ile bulma ve PostgreSQL `FOR UPDATE` kilidini doğruladı; ek yetki testi recovery'nin doğrulamadan önce broker/DB işine başlamadığını gösterdi. Tam paket 256/260; başarısız dört test yalnız kayıtlı P1-7 HUNTER/ATR sorunu. Ruff lint/format geçti. SQLite migration upgrade/downgrade iki eski order satırını korudu; PostgreSQL offline ileri/geri SQL üretimi `20260907_0005` dahil geçti. Gerçek PostgreSQL, Binance testnet/canlı hesap ve çok süreçli yarış testi çalıştırılmadı.

**Migration ve işletim sınırı:** `20260907_0005`, `client_order_id` kolonunu eski satırlar için nullable ekler ve `(inventory_scope, client_order_id)` benzersizliğini uygular. Eski satırlar otomatik bir Binance kimliği kazanmaz ve recovery endpoint'i bunlar için `409` döner. Deploy öncesi Alembic zorunluluğu P1-2'de güvenceye alınacaktır. Yerel commit başlığı: `fix(middleware): reconcile cumulative broker fills`; push/deploy yayın eşiğini bekler. Sonraki iş **P1-1**.

## P1 — Önemli tamamlamalar

### P1-1 — Komisyon, hassasiyet, limit ve replay doğruluğu

**Neden:** Komisyon net miktara işlenmiyor; fiyatlar altı ondalıkla sınırlı. Günlük sayım aday emri içerdiği için limit=1 ilk emri reddedebilir. Reconciliation şu an yalnız rapor. Replay suffix'inin eski client ID kısaltmasında kaybolması P0-4'te tam anahtar hash'iyle giderildi; kalan doğruluk sınırları bu maddede açık.

**Dosyalar:** [adapter](../middleware/broker_adapters/binance_spot.py), [modeller](../middleware/infra/models.py), [risk](../middleware/risk/checks.py), [order repository](../middleware/repositories/order_repository.py), [tranche repository](../middleware/repositories/tranche_repository.py), [TradingService](../middleware/services/trading_service.py), [execution plan](../middleware/docs/BINANCE_SPOT_EXECUTION_PLAN.md).

**Kabul kriterleri:**

- [x] Base/quote/başka varlıkla komisyon senaryolarında net miktar, maliyet ve PnL tutarlı.
- [x] Desteklenen fiyat/miktar hassasiyeti DB round-trip ve filtre sınırlarında test edildi.
- [x] Günlük limitin aday, reddedilen, simülasyon ve canlı emirleri nasıl saydığı tanımlı; 0/1/N sınır testleri var.
- [x] Replay için broker client ID davranışı açık; farklı işlem niyetleri yanlışlıkla aynı kimliğe kesilmiyor.
- [x] Reconciliation farkları sınıflandırılıyor; otomatik onarımın güvenli sınırı ve kaynağı tanımlı. Onarım uygulanırsa tekrar çalıştırılması çift etki üretmiyor; rapor-only bırakılırsa gerekçe ve takip işi kaydediliyor.

**Uygulanan davranış:** Binance `FULL` cevabındaki fill komisyonları varlık bazında kümülatif saklanıyor. Recovery, order sorgusuna ek olarak order ID ile `/api/v3/myTrades` okuyor; komisyon doğrulanamazsa nonzero fill `unknown` kalıyor. BUY base ücreti net envanterden düşüyor, BUY quote ücreti maliyete ekleniyor, SELL quote ücreti gelir/PnL'den düşüyor. Üçüncü varlık ücreti ayrı saklanıyor; güvenilir işlem-anı dönüşüm fiyatı olmadığı için quote PnL'ye uydurma değer eklenmiyor. SELL base ücreti takip edilen miktarı aşarsa otomatik uygulama yapılmıyor.

Fiyat/maliyet alanları `NUMERIC(28,12)` oldu; sekiz ondalıklı fiyat izole SQLite/API turunda birebir korundu ve modelin 12 ondalık şeması doğrulandı. `MW_MAX_ORDERS_PER_DAY=0` tüm gönderimleri durduruyor; pozitif kota yalnız broker submission aşamasına ulaşan önceki order'ları sayıyor. Mevcut aday ve riskte reddedilen order kotayı tüketmiyor; açık broker reddi/unknown sonuç tüketiyor. PostgreSQL'de scope bazlı transaction advisory lock eşzamanlı sayımı seri hale getiriyor.

Reconciliation `REPORT_ONLY` olarak sabitlendi. Bakiye farkı; manuel işlemler, transferler, başka scope'lar ve üçüncü varlık ücretlerinden kaynaklanabileceği için tek başına otomatik DB mutasyonu için yeterli kanıt sayılmıyor. API onarım politikasını ve duruma göre önerilen eylemi döndürüyor.

**Son incelemenin ek bulguları ve düzeltmeleri:** Binance client ID yalnız açık emirlerde benzersiz; önceki emir FILLED ise aynı kimlikle yeni emir kabul edilebiliyor. Bu nedenle P0-4'teki hash tek başına crash güvenliği kanıtı değildi. Artık riskten geçmiş `submitted` niyet broker POST'undan önce commit ediliyor, sonuç ayrı transaction'da işleniyor. Çökme sonrası normal tekrar ikinci emir göndermiyor. Aynı symbol/scope'taki açık veya belirsiz emir çözülmeden yeni emir reddediliyor. Henüz gönderilmemiş olabilecek crash niyeti de körlemesine yeniden gönderilmiyor; doğrulanamıyorsa yönetici incelemesi gerekiyor.

Recovery işlem geçmişini ilk trade ID'den itibaren 1.000'lik sayfalarla okuyor (en fazla 10 sayfa); emir/sembol, benzersiz trade ID, komisyon alanları ve kümülatif miktar eşleşmeli. Eksik geçmiş, NaN/sonsuz değer, kaybolan önceki komisyon varlığı ve geçersiz artan notional muhasebeyi değiştirmiyor. Küçük bakiye/dust açık envanterde korunuyor; SELL filtreleri karşılayan en eski tranche'ı seçiyor. Yetkili bypass replay'den sonraki normal tekrarın çoklu order nedeniyle hata vermesi de giderildi.

**Doğrulama:** Tam paket **305/309**, yalnız P1-7'deki aynı dört HUNTER/ATR hatası ve önceki bir deprecation warning açık. Middleware **110/110**; yeni muhasebe/limit 11, muhasebe sınırları 15, eksiksiz komisyon recovery 13 ve kalıcı dispatch 6 test geçti. Ruff lint/format ve diff kontrolleri geçti. `20260907_0006` SQLite upgrade/downgrade testi satırları korudu; PostgreSQL offline ileri/geri SQL doğrulandı. Üç mevcut DB'nin SHA-256 değerleri başlangıçla aynı. Gerçek PostgreSQL/Binance hesabı ve üçüncü varlık kur dönüşümü çalıştırılmadı.

**Migration ve sınır:** `20260907_0006`, eski order komisyonlarını tahmin etmez; bunları boş toplam ve `commission_complete=false` ile işaretler. Üçüncü varlık ücretinin quote para karşılığı ileride güvenilir fiyat kaynağıyla ayrıca ele alınmalıdır. Yerel commit başlığı: `fix(middleware): account for commissions and order limits`; push/deploy P1-2 ve P1-7 yayın eşiğini bekler. Sonraki iş **P1-2**.

### P1-2 — Çalıştırma ve dağıtım topolojisi

**2026-09-09 uygulaması:** Canonical topoloji Compose 2.24+: tek worker API + ayrı tek bot + Next standalone; opsiyonel middleware + ayrı PostgreSQL + tek seferlik Alembic servisi. Ana SQLite dizini `RAPOT_DATA_DIR` ile WAL/SHM ve bot kilidi dahil paylaşılır; kaynak kod image'dan gelir. Python 3.12.8/runtime constraint lock, Node 20.20.2/npm 10.9.9, build sırasında API/health Compose DNS hedefleri ve aynı origin üzerinden WebSocket yolu uygulandı. Ana DB hazırlığı ve middleware migration başarı koşulları başlatmaya bağlandı; üretimde Alembic head kontrol edilir, sürümsüz eski mw_* tabloları otomatik stamp edilmez. Doğrudan ve embedded bot girişleri ortak dosya kilidiyle korunur. Eski kilitsiz VPS süreçlerinin ilk geçişte tespit edilmesi hâlâ gerekir.

**Araç/doküman:** `scripts/runtime.py`, Compose, Dockerfile'lar, build-context dışlama kuralları, legacy PM2 launcher'ları, CI image kontrolleri ve `scripts/DEPLOY.md` güncellendi. Deploy scripti temiz ağaç + tam doğrulanmış SHA ister; isteğe bağlı push ve gerçek davranışını açıkça belirten manuel sunucu komutları üretir. Stage-all, stash ve reset kaldırıldı. Workflow'un image yayınlaması sunucu deploy'u olarak sunulmuyor.

**Geçen kontroller:** Yeni Python kilit/topoloji/şema testleri 10/10; tam paket 315/319 ve yalnız önceki P1-7 hataları. Frontend 12/12, ESLint, TypeScript dahil production standalone build; gerçek standalone sunucuda sahte localhost API/bot ile HTML, statik JS, Authorization/query aktarımı, health ve WebSocket 101 testi geçti. Compose config ve PowerShell AST doğrulandı; değişen Python dosyalarında Ruff lint/format geçti.

**Açık ortam engelleri:** Docker Desktop 4.70.0 motoru başlamıyor. 9 Eylül logunda `starting services: initializing Inference manager ... dockerInference ... Sistem dosyaya erişemiyor` hatası var. Factory reset, Docker verisi silme veya sistem ayarı değiştirme yapılmadı; gerekli Linux imaj/migration doğrulaması GitHub CI'de tamamlandı. VPS SSH kimlik doğrulaması reddedildi; `.ssh` altında yalnız known_hosts dosyaları bulundu, kullanılabilir SSH agent veya bu host için kayıtlı PuTTY oturumu bulunamadı. Kullanıcı erişim bilgisini bilmediğini belirtti. Sunucu süreçleri, veri yolu ve deploy sonucu doğrulanamadı. Erişimin yetkili SSH anahtarı/kullanıcı bilgisi veya hosting paneli konsolu üzerinden sağlanması gerekir.

**CI doğrulama eklemesi:** GitHub Linux runner'ında backend imajından ağsız import kontrolü, izole Docker ağı ve geçici PostgreSQL 16 ile sıfırdan Alembic migration, production middleware şema kapısı ve DRY_RUN/işlem kapalı health kontrolü eklendi. Test kaynakları koşum sonunda kaldırılır; gerçek DB/hesap bilgisi kullanılmaz. PostgreSQL readiness, init sırasında yalnız Unix socket'te çalışan geçici sunucuyu hazır saymamak için TCP `127.0.0.1` kullanır; Compose kontrolü de aynı düzeltmeyi içerir. İki workflow YAML ve tüm shell blokları `bash -n` kontrolünden geçti; push grubundaki 55 Python dosyası Ruff lint/format kontrolünden geçti. Gerçek başarılı koşum aşağıda kayıtlı.

**İlk Linux koşumu (tarihsel):** [34366928776](https://github.com/Rapto0/Rapot/actions/runs/34366928776), `5449aae` üzerinde Python/lint başarılı; frontend build sonrası standalone smoke adımında bekledi. Logda işlevsel kontrollerin geçtiği, kapanışın takıldığı doğrulandı. Test, Linux Next.js graceful shutdown'ı beklemeden önce mock upstream soketlerini kapatacak şekilde düzeltildi; statik yanıt gövdesi tüketiliyor, HTTP/süreç beklemeleri ve CI smoke adımı süre sınırına sahip. Yerel smoke ve ESLint tekrar geçti; takılan kendi koşumumuz iptal edildi. Bu test düzeltmesi uygulamanın çalışma davranışını değiştirmiyor.

**İkinci Linux koşumu (tarihsel):** [34367517745](https://github.com/Rapto0/Rapot/actions/runs/34367517745), `86718fc` üzerinde Python 329/329 ve frontend'in tüm adımları geçti; standalone kapanışı düzeldi. Backend imajı üretildi fakat import smoke ortamında `JWT_SECRET_KEY` eksikti. Yalnız bu ağsız test için sahte anahtar eklendi; uygulamanın zorunlu anahtar kontrolü korundu. Aynı importlar yerelde test izolasyonuyla geçti. Ayrıca frontend imajının gerçekten başlayıp HTML/statik JS sunduğunu ağsız container ile doğrulayan adım eklendi.

**Başarılı Linux koşumu:** [34368224479](https://github.com/Rapto0/Rapot/actions/runs/34368224479), tam kaynak SHA `3b9bbbf84c7a7b37e61b80042647b50c30ef8f90`, 2026-09-09. Python/lint/frontend işleri ve Docker işi başarılı. Backend imajı Python 3.12.8 altında ağsız import edildi; PostgreSQL 16 üzerinde tüm altı revision `20260907_0006`'ya kadar uygulandı. Production middleware DRY_RUN ve `trading_enabled=false` ile açılıp health kontrolünü geçti. Frontend standalone imajı üretildi, ağsız container içinde HTML ve statik JS sunumu geçti. Frontend'in 12 testi, lint/typecheck/build ve localhost HTTP/health/WebSocket proxy smoke testi de başarılı. Security işi sonucu, P2-3'te açıklanan `|| true` sınırı nedeniyle temiz güvenlik raporu olarak yorumlanmıyor.

**Kanıt sınırı:** CI imaj import/startup ve **boş PostgreSQL** migration'ını sınar; mevcut üretim verisinin yükseltilmesini kanıtlamaz. HTTP/WebSocket proxy testi localhost sahte servislerle, frontend imaj testi ağsız HTML/statik dosyalarla çalışır. Compose içindeki `api`/`bot` DNS entegrasyonu, tüm topolojinin birlikte açılması, paylaşılan gerçek SQLite dizini/izinleri, bot döngüsü ve container restart sonrası kalıcılık VPS doğrulamasında açık kalır. Reverse proxy/TLS, üretim ortam dosyaları, sunucu commit'i ve gerçek broker/testnet işlemleri doğrulanmadı.

**P0-1 sırasında kaydedilen ve P1-2'de giderilen bulgu:** Geliştirme/CI Python 3.12'ye geçmişken Docker Python 3.10'daydı; `datetime.UTC` importları bu sürümde çalışmıyordu. Container Python 3.12.8 ve `pyproject.toml` destek beyanı birlikte düzeltildi; yalnız build değil, ağsız imaj importu da doğrulandı.

**Başlangıç sorunu:** Frontend Dockerfile standalone çıktı bekliyor fakat Next config bunu açmıyordu. Health proxy frontend localhost'una gidiyordu; middleware Compose'ta yoktu. Bu uyumsuzluklar ve deploy workflow'unun yanıltıcı adı giderildi.

**Dosyalar:** [docker-compose.yml](../docker-compose.yml), [frontend Dockerfile](../frontend/Dockerfile), [Next config](../frontend/next.config.ts), [ecosystem.config.js](../ecosystem.config.js), [start-api.sh](../start-api.sh), [deploy workflow](../.github/workflows/deploy.yml), [deploy rehberi](../scripts/DEPLOY.md), [middleware README](../middleware/README.md).

**Kabul kriterleri:**

- [x] Hedef topoloji, süreçler, portlar, DB ayrımı ve health yönlendirmeleri kaydedildi.
- [ ] Frontend image/build ve izole proxy kontrolü geçti; gerçek Compose/VPS ağındaki API/health hedefleri henüz doğrulanmadı.
- [x] Middleware'in başlatma, migration, health, log ve durdurma adımları mevcut; desteklenen bot girişleri ortak kilitle korunuyor. Eski VPS süreçlerinin tespiti açık.
- [x] Dağıtım workflow'u gerçek davranışına uygun: açıkça manuel sunucu akışı, ayrı imaj yayınlama.
- [x] Yerel/izole CI kontrolü ile erişim yüzünden yapılmayan gerçek VPS deploy'u ayrı kaydedildi.

### P1-3 — Pine sözleşmesi ve testnet kabul akışı

**2026-09-09 incelemesi:** `normalizeTicker()` `.P` sonekini silerek futures grafiğini Spot sembolüne çevirebiliyordu. `barTime=2**63` modelden geçip repository tarih dönüşümünde, sınırı aşan `barIndex` ise BIGINT saklamasında hata üretebiliyordu. Unicode harfler `.upper()` sonrasında ASCII'ye dönüşerek önceki sembol kontrolünü geçebiliyordu. Bunlar yerel uygulamada giderildi.

**Uygulama:** Pine yalnız `BINANCE`, `crypto`, base/quote birleşimine uyan ham ASCII ticker ve `chart.is_standard` koşullarında dispatch yapar; tek `alert()` çağrısı da aynı korumaya bağlıdır. `.P`/borsa/sonek silme kaldırıldı; tabloda uygunsuz grafik açıklanır. Backend ham sembolde ASCII kontrolünü büyük harf dönüşümünden önce yapar; separator/sonek reddedilir. `barTime` JSON integer `1..253402300799999`, `barIndex` JSON integer `0..2**63-1` ile sınırlandı. Boolean/float/sayısal metin ve taşmalar webhook/admin replay'de işleme başlamadan `422`; geçerli fakat eski/gelecek olaylar önceki gibi denetlenip `200/rejected` olarak kaydedilir. UTC dönüşümü epoch + integer timedelta ile milisaniyeyi korur.

**Uyumluluk kararı:** `schemaVersion=1`, hash algoritması, geçerli örnek payload/hash ve sinyal eşikleri değişmedi; migration yok. `barTime=timenow` olay üretim zamanıdır, bar açılışı değildir. Aynı normalize payload tek emir, aynı bar/kodda yeni olay zamanı veya farklı kod ayrı emir/tranche üretir. Fiyatın ondalık yazımı, metin ve timeframe alias farkları v1'de ayrı hash olabilir; retry aynı payload'u korumalıdır. Bu davranışı değiştirmek geçmiş idempotency kayıtlarıyla uyumlu sürüm tasarımı gerektirir. Kasıtlı BUY biriktirme korunur.

**Doğrulama:** 52 backend sınır/hash/freshness/retry testi + 22 Pine kaynak sözleşmesi testi; tam `.venv/Scripts/python.exe -m pytest -q` **403/403** (27,42 saniye), bir mevcut P2-3 tarih uyarısı. Yedi değişen Python dosyası Ruff lint/format ve diff kontrolünden geçti. Üç gerçek DB SHA-256 değeri başlangıçla aynı. Gerçek/testnet emir ve migration çalıştırılmadı.

**Dış doğrulama sınırı:** Bağlı tarayıcıda oturum yoktu. TradingView misafir Pine editöründe geçici yalnız-grafik-koruması kontrolünün Add to chart adımı **Sign in** ekranı istedi; derleme başarısı alınmadı, sekme kapatıldı. Kaynak testleri Pine derleyicisi/tick yürütücüsü değildir. Asıl scriptin Pine derlemesi, BINANCE Spot/futures/sentetik grafik runtime doğrulaması, gerçek örnek alarm JSON'u ve ayrılmış testnet BUY → FIFO SELL → reconcile kabulü açık. Alarm/hesap oluşturulmadı, oturum açılmadı, broker emri gönderilmedi. TradingView çalışan alarmlarının eski script kopyasını kullanabileceği README'de açıklandı.

**Neden:** Son Pine commit'i büyük; derleme/alarm testi doğrulanmadı. Varsayılan Manuel/günlük/saat filtresi ile Kripto 24/7 preset'i farklı. barTime=timenow ve tüm payload hash'i, aynı bar/sinyalin tekrar semantiğini etkiliyor.

**Dosyalar:** [Pine](../middleware/pine/combo_hunter_binance.pine), [Pine README](../middleware/pine/README.md), [payload modeli](../middleware/domain/events.py), [signal repository](../middleware/repositories/signal_repository.py), [middleware README](../middleware/README.md), [webhook testleri](../middleware/tests/test_webhook_validation.py).

**Kabul kriterleri:**

- [x] Spot sembolü, sinyal kodu/yönü, timeframe ve v1 olay zamanı sözleşmesi açık; ayrı bar açılış alanı olmadığının sınırı belgeli.
- [x] Birebir HTTP tekrarının korunması ile aynı bar/sinyalin yeniden üretilmesi ayrıldı; eski hash ve kasıtlı tekrarlı BUY davranışı test edildi.
- [ ] Manuel/Kripto 24/7, saat dilimi ve ALL/FIRST kaynak sözleşmesi test edildi; gerçek Pine runtime/alarm doğrulaması bekliyor.
- [ ] Pine derlemesi ve örnek alarm JSON'u doğrulandı; strategy() başlığı tek başına çalışan backtest kanıtı sayılmadı.
- [ ] İlgili izin verildiğinde yalnız ayrılmış testnet hesabı/DB ile BUY → FIFO SELL → reconcile kabul akışı kaydedildi; tokenlar kayda alınmadı.
- [x] Yerel test sonucu testnet/gerçek hesap doğrulaması veya otomatik canlıya geçiş olarak işaretlenmedi.

### P1-4 — AI ilişkileri ve scan history

**Neden:** Scanner AI çağrısı market_type/signal_id göndermiyor; varsayılan BIST/None. Scan history okuyucusu var, aktif scanner yazma bağlantısı bulunamadı.

**Dosyalar:** [market_scanner.py](../market_scanner.py), [async_scanner.py](../async_scanner.py), [ai_analyst.py](../ai_analyst.py), [system repository](../infrastructure/repositories/system_repository.py), [ops repository](../infrastructure/persistence/ops_repository.py), [modeller](../models.py).

**Kabul kriterleri:**

- [ ] Kripto/BIST analizi doğru piyasa ve uygun sinyal kimliğiyle saklanıyor; sinyalden analize erişim doğrulandı.
- [ ] AI_ENABLED=0 davranışı ve AI başarısızlığında taramanın davranışı korunuyor.
- [ ] Tamamlanan/başarısız taramanın geçmiş kaydı politikası belirli; sayım/süre/kayıt tekrarları test edildi.
- [ ] /scans ve ilgili read-model'ler yeni tarama kaydını sunuyor; eski boş yerel tablo üretim geçmişi olarak yorumlanmıyor.

### P1-5 — Süreçler arası realtime ve scanner eşdeğerliği

**Neden:** Signal dispatcher süreç içi callback; ayrı bot/API süreçleri arasında taşıma yok. Async akış special_tag=None kullanıyor ve sync özellikleriyle aynı değil.

**Dosyalar:** [signal_dispatcher.py](../signal_dispatcher.py), [realtime bootstrap](../api/runtime/realtime_bootstrap.py), [api/realtime.py](../api/realtime.py), [signal handlers](../application/scanner/signal_handlers.py), [market_scanner.py](../market_scanner.py), [async_scanner.py](../async_scanner.py), [frontend realtime](../frontend/src/lib/realtime).

**Kabul kriterleri:**

- [ ] Seçilen ayrı süreç topolojisinde yeni kayıt frontend sinyal kanalına ulaşıyor; taşıma hatası DB kaydını kaybettirmiyor.
- [ ] Reconnect/yeniden başlatma ve yinelenen olay davranışı test edildi; frontend yenileme/fallback davranışı açık.
- [ ] Kline/trade yayın callback'lerinin gerçekten bağlı olup olmadığı kontrol edildi; desteklenen kanallar doğrulandı.
- [ ] Sync/async özel etiket, AI, ek kaynak doğrulaması ve notify kapsamı karşılaştırıldı; eşitlenen veya bilinçli farklı kalan davranışlar belgeli.

### P1-6 — PnL, bot durumu ve ayarlar ekranı

**Neden:** currentPrice giriş fiyatına eşitleniyor; PnL yüzdesi miktarı içermiyor. Bot durumu yokken isRunning=true varsayılıyor. Ayarlar yalnız localStorage'a, secret alanlarıyla birlikte yazılıyor.

**Dosyalar:** [normalizers](../frontend/src/lib/api/normalizers.ts), [health hook](../frontend/src/lib/hooks/use-health.ts), [ayarlar sayfası](../frontend/src/app/settings/page.tsx), [ops API](../frontend/src/lib/api/ops-api.ts), [backend modelleri](../models.py), [settings.py](../settings.py), [config.py](../config.py).

**Kabul kriterleri:**

- [ ] PnL yüzdesi miktar/giriş değeriyle tutarlı; sıfır ve farklı miktar örnekleri doğrulandı.
- [ ] Güncel fiyat yokken giriş fiyatı güncel fiyat gibi sunulmuyor; API bağlantısı bot çalışıyor bilgisiyle karıştırılmıyor.
- [ ] Botun bilinmeyen/kapalı/çalışan durumları doğru gösteriliyor.
- [ ] Kalıcı bot ayarları için yetkili backend sözleşmesi uygulandı veya ekranın yalnız tarayıcı tercihi olduğu açıklaştırıldı; seçilen kapsam kaydedildi.
- [ ] Secret alanları düz localStorage'a kaydedilmiyor; ayarın gerçek hesaplamaya etkisi gösterildi. Config eşik nesnelerinin üretim hesaplayıcısına bağlı olmadığı bulgusu dikkate alındı.

### P1-7 — HUNTER kısa seride ATR hatası

**Kaynak:** P0-1 tam test koşumu; önceki salt okunur incelemede davranış testleri çalıştırılmadığı için raporlanmamıştı. **2026-09-09'da uygulandı ve doğrulandı.**

**Doğrulanan eski hata:** 480 günlük örnek veri aylık seride 17 muma düşüyordu. `calculate_hunter_signal` → Keltner %B → `df.ta.atr(length=20)` → `ta.volatility.AverageTrueRange` yolu `IndexError: index 19 is out of bounds for axis 0 with size 17` üreterek AI/inspector raporunu ve tam test paketini kesiyordu.

**Dosyalar / kapsam / bağımlılık:** [signals.py](../signals.py), [strategy_inspector.py](../strategy_inspector.py), [test_strategy_inspector.py](../tests/test_strategy_inspector.py), [test_signals.py](../tests/test_signals.py); küçük/orta; P0-1 tamamlandıktan sonra bağımsız ele alınabilir.

**Önceki tekrar üretme:** `.venv/Scripts/python.exe -m pytest tests/test_strategy_inspector.py` (düzeltme öncesi 2 geçti / 4 başarısız). Artık geçen dört test:

- `test_inspect_strategy_dataframe_hunter_structure`
- `test_build_strategy_inspector_chunks_contains_symbol_and_strategy`
- `test_build_strategy_inspector_chunks_detail_single_timeframe`
- `test_build_strategy_ai_payload_contains_multitimeframe_context`

**Kabul kriterleri:**

- [x] ATR için yetersiz mum davranışı belirlenip uygulandı; eksik gösterge geçerli sinyal gibi değerlendirilmedi.
- [x] 19/20 mum sınırı, aylık kısa seri, boş veri ve yeterli veri senaryoları doğrulandı.
- [x] Yukarıdaki dört test ve tam backend/middleware paketi geçti; skor/rapor sözleşmesi korundu.

**Davranış:** Kilitli `ta` bağımlılığı için uyumluluk accessor'ı, 20 mumdan kısa seride aynı indeksli NaN ATR döndürüyor; yeterli serinin ilk 19 ısınma değeri de NaN. Ölçülmüş gerçek sıfır ATR korunuyor. HUNTER eksik Keltner değerini `N/A` gösteriyor ve puana katmıyor; mevcut dip/tepe eşikleri değişmedi.

**Doğrulama:** `tests/test_hunter_warmup.py` içinde 10 yeni test: 0/19/20/80 mum, gerçek sıfır, aktif gösterge/puan sınırları ve 17 mumluk aylık rapor. HUNTER/inspector/signals seçimi **37/37**, tam `.venv/Scripts/python.exe -m pytest -q` **329/329** (28,23 saniye). Tek mevcut `datetime.utcnow()` uyarısı P2-3'te açık. Ruff lint/format ve diff kontrolü geçti. Strateji performansı veya canlı hesap doğrulaması yapılmadı.

## P2 — İyileştirmeler

### P2-1 — Dışa aktar, alarmlar ve grafik URL davranışı

**P0-1 doğrulaması:** Node 20.20.2 altında production build geçti; önceki olası derleme riski bu koşumda gerçekleşmedi. Grafik URL'sinin tarayıcıdaki davranışı henüz doğrulanmadı.

**Neden:** Sinyal dışa aktar düğmesinde işlem yok. Alarmlar açık sayfada çalışıyor. Chart searchParams kullanımı için Next runtime uyumluluk riski var; önceki typecheck başarısı bu davranışı kanıtlamıyor.

**Dosyalar:** [signals page](../frontend/src/app/signals/page.tsx), [alarms page](../frontend/src/app/alarms/page.tsx), [watchlist alarms](../frontend/src/lib/watchlist-alarms.ts), [chart page](../frontend/src/app/chart/page.tsx).

**Kabul kriterleri:**

- [ ] Dışa aktarma görünür filtrelerle uyumlu veri üretiyor veya desteklenmeyen işlem UI'dan kaldırılmış.
- [ ] Alarmın sayfa açıkken çalışma sınırı UI'da anlaşılır; arka planda 7/24 hizmet istenirse ayrı kapsam ve iş olarak kaydedilmiş.
- [ ] Grafik URL'sindeki symbol/market, doğrudan giriş ve sayfa geçişinde doğru uygulanıyor; geçersiz değer fallback'i test edilmiş.
- [ ] İlgili UI davranışları ile lint/typecheck/build kontrolleri doğrulanmış.

### P2-2 — Belgeler ve wrapper göçünün kapanışı

**Neden:** HUNTER açıklaması, Alembic kapsamı ve bazı bağımlılık notları eski. Paketleme aşama 5 açık; kaldırma takviminde canonical handler da legacy listesinde.

**Dosyalar:** [AGENTS.md](../AGENTS.md), [README](../README.md), [Codex bağlamı](Codex.md), [paketleme haritası](PACKAGING_REFACTOR_MAP.md), [wrapper takvimi](WRAPPER_DEPRECATION_SCHEDULE.md), [DB politikası](DB_MIGRATION_POLICY.md), [eski spot backlog](ALGOTRADING_SPOT_BACKLOG.md), [compat telemetry](../infrastructure/compat/wrapper_telemetry.py).

**Kabul kriterleri:**

- [ ] Ana SQLite migration yolu ile middleware Alembic yolu doğru ayrıldı; HUNTER 15 gösterge puanı ve güncel bağımlılıklar açıklandı.
- [ ] Canonical import yolları ile compatibility wrapper listesi gerçek kodla eşleşiyor.
- [ ] Wrapper kaldırma kararı tarih takvimine tek başına dayanmıyor; kullanım/import kanıtı ve regression kontrolleri var.
- [ ] Eski backlog'lar bu planla çelişmiyor; uygulanmış maddeler sırf kutusu boş diye yeniden yapılmıyor.

### P2-3 — Ruff, atıl kod ve araç tarama kapsamı

**P0-1 doğrulaması:** Değişen yedi Python dosyası Ruff lint/format kontrolünden geçti; tüm-repo borcu açık. Tam pytest'te `tests/test_async_scanner.py::test_scan_market_async_returns_failed_status_on_fatal_error` sırasında SQLAlchemy model varsayılanının `datetime.utcnow()` kullanımı için bir deprecation warning görüldü. Zaman damgası saklama/okuma sözleşmesini koruyarak ele alınmalı.

**9 Eylül CI ek bulguları:** Checkout kapanışı, Git'e gitlink olarak kayıtlı `.claude/worktrees/festive-bartik-1395fb` için `.gitmodules` URL'si bulamadığını uyarı olarak bildiriyor. Yerel worktree silinmedi/değiştirilmedi; kayıt/kapsam kararı bu işte verilecek. Bazı action sürümlerinin Node 20 runtime bildirimi GitHub tarafından Node 24'e yönlendiriliyor ve deprecation uyarısı üretiyor; bu, frontend testinde seçilen Node sürümünden ayrı bir konu. Action sürümü güncellemesi burada takip edilecek. Security işi araç hata/bulgularını `|| true` ile yuttuğundan yeşil olması güvenlik bulgusu yok demek değildir.

**Neden:** Ana projede 8 Ruff bulgusu; iç worktree'de tekrarları var. PortfolioPanel TODO'ları ve bazı eski mock/dashboard bileşenleri için aktif kullanım bulunamadı.

**Dosyalar:** [main.py](../main.py), [backfill scripti](../scripts/backfill_signal_details.py), [signals.py](../signals.py), [test_config.py](../tests/test_config.py), [pyproject.toml](../pyproject.toml), [dashboard bileşenleri](../frontend/src/components/dashboard), [mock data](../frontend/src/lib/mock-data.ts).

**Kabul kriterleri:**

- [ ] Ana proje Ruff bulguları kapatıldı; davranışı etkileyen değişiklik varsa ilgili doğrulama yapıldı.
- [ ] İç Claude worktree ve üretilmiş/bağımlılık klasörlerinin lint/build kapsamı bilinçli tanımlandı.
- [ ] Atıl sayılan kodun dinamik/import kullanım ihtimali kontrol edildi; aktif özellik yanlışlıkla kaldırılmadı.
- [ ] İç worktree/backup branch otomatik silinmedi veya birleştirilmedi; kapsam değişikliği varsa karar kaydı var.

## P3 — Daha sonra değerlendirilecek işler

### P3-1 — Backtest ve strateji eşdeğerliği

**Neden:** Python, frontend ve Pine hesaplayıcıları ayrı implementasyonlar. Backtest kodunun varlığı performans/strateji doğruluğu kanıtı değil.

**Dosyalar:** [backtest](../backtesting_system.py), [signals.py](../signals.py), [frontend indicators](../frontend/src/lib/indicators.ts), [Pine](../middleware/pine/combo_hunter_binance.pine).

**Kabul kriterleri:**

- [ ] Aynı örnek veri, zaman dilimi ve kapanmış/açık mum kurallarıyla hesaplayıcı farkları ölçüldü.
- [ ] Komisyon, kayma, veri kaynağı ve ileriye bakış etkileri kontrol edildi; sonuçlar tekrarlanabilir.
- [ ] Bilinçli strateji farkları belgeli; performans raporu canlı kazanç garantisi olarak sunulmuyor.

### P3-2 — Backup branch tasarım değerlendirmesi

**Neden:** backup/pre-da7d452-rollback branch'inde main'e girmeyen beş eski commit var. Bunlar kayıp/geri alınması gereken iş olarak varsayılmamalı.

**Kapsam:** Branch diff'i ve etkilenen frontend dosyaları; uygulama kararı henüz yok.

**Kabul kriterleri:**

- [ ] Beş commitin güncel main'deki karşılıkları ve tasarım farkları özetlendi.
- [ ] Kullanılacak veya bırakılacak parçalar için karar kaydedildi.
- [ ] Seçilen değişiklik varsa güncel API/UI ile uyumu doğrulandı; otomatik toplu merge yapılmadı.

## Karar kaydı

| Tarih | Karar | Gerekçe / sınır |
|---|---|---|
| 2026-09-06 | Bu dosya güncel iş takibi için kullanılacak | Öncelik, kanıt ve sonraki adım tek yerde tutulacak; eski belgeler tarihsel kaynak |
| 2026-09-06 | Her iş incele → düzelt → doğrula → belgeyi güncelle sırasıyla yürütülecek | Kullanıcının çalışma yöntemi |
| 2026-09-06 | Uygulama işleri Bekliyor başlayacak | Önceki inceleme ve belge hazırlığı, kod düzeltmesi değildir |
| 2026-09-06 | Önceki test sonuçları başlangıç kaydı olarak korunacak | Yeni değişiklikleri otomatik olarak doğrulamaz |
| 2026-09-06 | P0-1 için yerel uygulama ve doğrulama yapıldı | Kullanıcı P0-1'i seçti; gerçek veri, servis, deploy ve commit kapsam dışında kaldı |
| 2026-09-06 | Geliştirme/CI `.venv`, Python 3.12 ve kilitli bağımlılıkları kullanacak | Python 3.12.8 ile doğrulandı; eski `venv` ve sistem Python korundu; Docker uyumu P1-2 |
| 2026-09-06 | Node 20.20.2 ve npm 10.9.9 kullanılacak | Repo sürüm dosyaları/CI eşitlendi; yerelde npm exec ile global Node değiştirilmeden doğrulandı |
| 2026-09-06 | Tam test başarısızlıkları açık iş olarak kaydedilecek | 4 HUNTER/ATR hatası P1-7; CI tüm testleri çalıştırıyor ve başarısız çıkış kodunu koruyor |
| 2026-09-06 | Her iş yerel commit; push+deploy doğrulanmış gruplarda | Kullanıcı otomatik commit/push/deploy yetkisi ve zamanlama tercihini verdi; ilk yayın P0 + P1-7 + P1-2 koşullarına bağlı |
| 2026-09-06 | Commit araçları da tek geliştirme ortamına dahil | `.venv` içindeki mevcut hook için pre-commit 4.5.1 eklendi; Ruff hook'u 0.14.13 ile yerel/CI sürümüne eşitlendi; bağımlılık kontrolü 128 paket için geçti |
| 2026-09-07 | Middleware yönetimi webhook'tan ayrı anahtarla korunacak | `MW_ADMIN_AUTH_TOKEN`; header-only; eksik/aynı anahtar kapalı davranır; replay bypass yalnız doğrulanmış admin için |
| 2026-09-07 | Ana API kritik işlemleri rol ve rate-limit ile korunacak | Dashboard giriş akışı eklendi; token sekme belleğinde; mevcut public okumalar korunuyor; dağıtım/proxy doğrulaması P1-2 |
| 2026-09-07 | Envanter mod, broker, venue/ortam ve hesap etiketiyle ayrılacak | DRY_RUN/LIVE, testnet/üretim ve farklı hesaplar aynı DB'de birbirinin FIFO/risk/list/reconciliation durumunu göremez |
| 2026-09-07 | Kanıtlanamayan eski middleware satırları karantinada kalacak | Migration geçmiş account/venue bilgisini varsaymaz; `LEGACY_UNCLASSIFIED` satırları saklanır fakat aktif işlem kapsamına girmez |
| 2026-09-07 | Broker gerçekleşmeleri kümülatif görüntü olarak uygulanacak | Terminal CANCELED/EXPIRED kısmi fill'leri kaybolmaz; tekrar sorgu yalnız yeni farkı uygular; belirsiz sonuç `unknown` kalır |
| 2026-09-07 | Binance client order ID tam yerel niyetin hash'inden üretilecek | 36 karakter sınırı korunurken replay son eki ve kapsam bilgisi kimliğe katılır; yeniden başlatma sonrası broker kaydı aynı kimlikle bulunabilir |
| 2026-09-07 | Emir komisyonu doğrulanmadan envanter değiştirilmeyecek | Query Order komisyon döndürmez; recovery `myTrades` ile doğrular. Eksik bilgi `unknown`, base/quote ücretleri net envanter ve quote PnL'ye uygulanır |
| 2026-09-07 | Reconciliation report-only kalacak | Toplam hesap bakiyesi tek bir middleware scope'unun kaynağını kanıtlamaz; otomatik düzeltme yanlış envanter üretebilir |
| 2026-09-09 | Yerel kontrolleri geçen ilk grup CI için push edilecek | Docker Desktop motor hatası nedeniyle Linux imaj/migration doğrulaması CI'de yapılacak; bu push deploy veya testnet emri değildir. Kullanıcı zamanlama seçimini asistana bıraktı |
| 2026-09-09 | P1-3 v1 olay/hash sözleşmesi korunacak | `barTime` olay zamanı olarak kalır; fiyat yazımı/timeframe alias gibi sunum farklarını birleştirmek veya bar başına tek BUY yapmak geçmiş hash'leri ve kasıtlı biriktirmeyi değiştirebilir; ayrıca sürümlendirilmeden uygulanmaz |

## İlerleme günlüğü

| Tarih | İş | Aşama / sonuç | Değişiklik ve doğrulama |
|---|---|---|---|
| 2026-09-06 | Hazırlık | Proje incelemesi tamamlandı; plan hazırlandı | Referans HEAD yeniden kontrol edildi. Yalnız bu belge eklendi; uygulama testleri bu adımda yeniden çalıştırılmadı |
| 2026-09-06 | P0-1 | İncele | Ortam farkları, import sırasında sabit DB yolları, sabit middleware test DB'si, API sağlayıcı durumu sızıntısı ve eksik BIST ikinci kaynak mock'ları doğrulandı |
| 2026-09-06 | P0-1 | Düzelt | Python dev lock ve sürüm dosyası; Node/npm sabitlemesi; root/core/middleware fixture'ları, ağ/SQLite sınırı, 11 izolasyon testi ve CI kapsamı eklendi; DB/cache settings alanlarına bağlandı |
| 2026-09-06 | P0-1 | Doğrula | Tam pytest + coverage: 185 geçti / 4 HUNTER hatası / 1 warning; middleware 26/26. Frontend lint/typecheck/build ve değişen Python dosyaları Ruff kontrolleri geçti. CI YAML/gömülü Python sözdizimi ve git diff --check kontrol edildi; üç mevcut DB'nin SHA-256 değerleri değişmedi |
| 2026-09-06 | P0-1 | Belgeyi güncelle — Doğrulandı | Ortam/komutlar ve sonuçlar bu belgeye işlendi. Davranış hatası P1-7, Docker sürüm uyumu P1-2, warning P2-3. Sonraki ana iş P0-2; commit/push/deploy yok |
| 2026-09-06 | P0-1 / yayın düzeni | Yerel checkpoint commit kapsamı | `chore(dev): establish isolated P0-1 test baseline` başlıklı commit; bu plan ve P0-1 dosyaları, pre-commit bağımlılığı/sürüm uyumu dahil. Push/deploy ilk grup doğrulamasını bekliyor. Commit kimliği Git geçmişinden okunur |
| 2026-09-07 | P0-2 | İncele | Admin replay özellik bayrağıyla açıktı; ana API kritik yollarında JWT koruması ve dashboard'da login akışı eksikti |
| 2026-09-07 | P0-2 | Düzelt | Ayrı middleware yönetim anahtarı, ana API rol/limit kontrolleri, generic işlem hataları, bellek oturumu ve login/logout UI eklendi; OpenAPI/CI/README güncellendi |
| 2026-09-07 | P0-2 | Doğrula | 239/243 Python testi geçti; yalnız önceki dört P1-7 hatası açık. Yeni yetki testleri 54/54, middleware 44/44; frontend 9/9, lint/typecheck/build ve sahte API ile tarayıcı akışı geçti; gerçek DB özetleri değişmedi |
| 2026-09-07 | P0-2 | Belgeyi güncelle — Doğrulandı | Erişim/limit matrisi, yeni anahtar kurulumu, replay bypass, komut/kanıt ve yayın sınırı kaydedildi. Yerel commit başlığı: `fix(auth): protect admin and analysis operations`; push/deploy yok. Sonraki iş P0-3 |
| 2026-09-07 | P0-3 | İncele | Order mode bilgisinin tranche/FIFO/risk/list/reconciliation sorgularına uygulanmadığı ve global idempotency'nin ortam geçişini karıştırdığı doğrulandı |
| 2026-09-07 | P0-3 | Düzelt | Kapsam anahtarı ve LIVE hesap etiketi zorunluluğu, order/tranche kolonları, repository filtreleri, kapsamlı idempotency, API alanları ve karantina migration'ı eklendi |
| 2026-09-07 | P0-3 | Doğrula | Tam paket 245/249; yalnız önceki dört P1-7 hatası. Middleware 50/50 ve Ruff geçti; izolasyon ile SQLite migration round-trip ve PostgreSQL offline upgrade/downgrade SQL doğrulandı; gerçek DB/emir yok |
| 2026-09-07 | P0-3 | Belgeyi güncelle — Doğrulandı | Kapsam sözleşmesi, eski veri davranışı, migration-before-start şartı ve test kanıtı kaydedildi. Yerel commit başlığı: `fix(middleware): isolate inventory by execution scope`; push/deploy yok. Sonraki iş P0-4 |
| 2026-09-07 | P0-4 | İncele | CANCELED/EXPIRED dalının fill'i uygulamadan döndüğü, broker miktarının servisçe delta gibi toplandığı ve timeout/restart kurtarma kimliğinin bulunmadığı doğrulandı |
| 2026-09-07 | P0-4 | Düzelt | Kalıcı hash tabanlı client order ID, kümülatif fill-delta uygulaması, terminal durum koruması, `unknown` durumu, timeout/duplicate sorgusu, yetkili recovery endpoint'i ve `20260907_0005` migration'ı eklendi |
| 2026-09-07 | P0-4 | Doğrula | Middleware 61/61; yeni recovery testleri 9/9; tam paket 256/260 ve yalnız önceki dört P1-7 hatası. Ruff, SQLite migration round-trip ve PostgreSQL offline ileri/geri SQL geçti; gerçek DB/borsa emri yok |
| 2026-09-07 | P0-4 | Belgeyi güncelle — Doğrulandı | Kısmi terminal fill, exact-once delta, timeout/restart recovery, yönetim sınırı ve migration davranışı kaydedildi. Yerel commit başlığı: `fix(middleware): reconcile cumulative broker fills`; push/deploy yok. Sonraki iş P1-1 |
| 2026-09-07 | P1-1 | İncele | Binance FULL fill komisyonu ile Query Order sınırı resmi dokümanda doğrulandı; komisyonun kaybolduğu, fiyatın 6 ondalık olduğu ve gün limitinin mevcut adayı saydığı kodda yeniden üretildi |
| 2026-09-07 | P1-1 | Düzelt | Varlık bazlı kümülatif komisyon, myTrades recovery, net base/maliyet/PnL hesabı, 12 ondalık fiyat migration'ı, gönderilmiş-order kotası ve PostgreSQL scope kilidi eklendi; reconciliation report-only sözleşmesi açıklaştırıldı |
| 2026-09-08 | P1-1 | Doğrula | Tam paket 305/309; middleware 110/110; yalnız önceki dört P1-7 hatası ve bir warning. Kalıcı dispatch/crash, bypass tekrar, komisyon sayfalama, dust ve hatalı muhasebe regresyonları geçti. Ruff, SQLite migration round-trip ve PostgreSQL offline ileri/geri SQL geçti; üç gerçek DB hash'i aynı |
| 2026-09-07 | P1-1 | Belgeyi güncelle — Doğrulandı | Komisyon varlığı semantiği, üçüncü varlık PnL sınırı, 0/1/N kota politikası, hassasiyet ve report-only gerekçesi kaydedildi. Commit başlığı `fix(middleware): account for commissions and order limits`; sonraki iş P1-2 |
| 2026-09-08 | P1-1 | Son inceleme ve belge kapanışı | Client ID'nin açık emir sınırı resmi Binance sözleşmesiyle doğrulandı; P0-4 crash garantisi kalıcı dispatch ile tamamlandı. Recovery geçmişinin eksiksizliği, dust/FIFO, bilinmeyen sonuç rezervasyonu ve manuel inceleme sınırı belgelendi |
| 2026-09-09 | P1-2 | İncele → düzelt | Tek Compose topolojisi, sürüm/bağımlılık uyumu, standalone HTTP/WS/health proxy, ayrı DB/migration servisleri ve tek bot kilidi uygulandı; deploy aracı gerçek manuel davranışına göre düzenlendi |
| 2026-09-09 | P1-2 | Doğrula → belgeyi güncelle (kısmi) | Python 315/319, yeni testler 10/10; frontend 12/12, lint/build ve standalone proxy smoke geçti. Docker motor hatası ve SSH erişimi imaj/VPS doğrulamasını engelliyor; madde Doğrulandı olarak kapatılmadı |
| 2026-09-09 | P1-7 | İncele → düzelt | ATR kısa seride indeks hatası ve `ta` ısınma sıfırları doğrulandı; eksik ölçümler NaN oldu, gerçek sıfır korundu. HUNTER eşikleri ve rapor biçimi değişmedi |
| 2026-09-09 | P1-7 | Doğrula → belgeyi güncelle — Doğrulandı | 10 yeni sınır/rapor testi, hedefli 37/37 ve tam Python 329/329 geçti; Ruff lint/format temiz. P2-3 tarih uyarısı sürüyor; önceki dört HUNTER hatası kapandı |
| 2026-09-09 | P1-2 | CI hazırlığı | İzole PostgreSQL migration/production startup smoke adımı eklendi; CI/Compose TCP readiness yarışı giderildi. P1-7 `dc433a7` kaydedildi; tam Python 329/329 ve frontend kontrolleri sonrası doğrulama push'u hazırlanıyor. Sunucu erişimi hâlâ eksik |
| 2026-09-09 | P1-2 | Push → Linux CI → test düzeltmesi | `5449aae` main'e gönderildi. İlk CI Python/lint geçti; frontend smoke kapanışı takıldı. Mock soketleri önce kapatma, yanıt gövdesini tüketme ve süre sınırları eklendi; yerel smoke/ESLint geçti. İlk koşum iptal edildi; sonraki Linux/Docker doğrulaması bekliyor. Üç gerçek DB hash'i hâlâ aynı |
| 2026-09-09 | P1-2 | Linux smoke düzeldi; imaj test ortamı düzeltildi | `86718fc` push edildi; Python/lint/frontend geçti, backend imajı üretildi. Ağsız import testine eksik sahte JWT eklendi; frontend container başlangıç/statik varlık testi eklendi. Güvenlik kontrolü gevşetilmedi; sonraki CI sonucu bekleniyor |
| 2026-09-09 | P1-2 | Doğrula → belgeyi güncelle — CI tamam; VPS engellendi | `3b9bbbf` push edildi; CI 34368224479 başarılı. Backend/frontend imajları, ağsız import, boş PostgreSQL'de altı migration ve production middleware health, frontend container HTML/statik dosyaları geçti. Veri korundu; server deploy'u ve gerçek/testnet emir yok. Sıradaki bağımsız kod adımı P1-3 Spot/tarih sözleşmesi |
| 2026-09-09 | P1-3 | İncele → düzelt | Futures soneki silme, taşan zaman/index ve Unicode büyük harf dönüşümü doğrulandı; Pine Spot/standart grafik kapısı, backend ham ASCII ve integer tarih/index sınırları ile hassas UTC dönüşümü uygulandı |
| 2026-09-09 | P1-3 | Doğrula → belgeyi güncelle — yerel tamam | 74 yeni test; tam 403/403 ve bir mevcut warning. Ruff lint/format/diff geçti; DB hash'leri aynı. v1 eski hash, ayrı BUY ve retry testleri geçti. TradingView Add to chart giriş istiyor; Pine derlemesi/alarm/testnet açık. Sonraki bağımsız kod işi P1-4 |

Uygulama sırasında her iş için bu bilgileri günlüğe ekle:

- İş ID'si, tarih, aşama ve sonuç.
- Yeniden doğrulanan bulgu; önceki rapordan farklı çıkan durum varsa düzeltmesi.
- Değişen dosyalar ve değişikliğin davranışa etkisi.
- Çalıştırılan komut, kullanılan ortam, test sonucu ve ilgili çıktı özeti.
- Çalıştırılmayan kontroller ve nedenleri.
- Açık karar/engel, çözülme şartı ve sıradaki somut adım.
- Commit yalnız gerçekten oluşturulmuş ve kapsam dahilindeyse hash; aksi halde commit yok.

## Ara verdikten sonra devam etme

1. Bu belgedeki Kaldığımız nokta, Kapsam ve yetki kaydı ile son ilerleme kayıtlarını oku.
2. Branch/HEAD, staged/unstaged/untracked durumu ve kullanıcı değişikliklerini kontrol et; kayıttan farklıysa not düş.
3. Kullanıcı talimatlarının güncel kapsamını uygula; önceki verilmiş yetkiyi veya kısıtı varsayımla değiştirme.
4. Aktif işin bulgusunu ve bağımlılıklarını güncel kodda kontrol et. İncelemeyi baştan tekrarlamak yerine ilgili kanıttan devam et.
5. İşin dört adımını tamamla veya engeli somutlaştır; ardından durum tablosu, günlük ve Kaldığımız nokta bölümünü güncelle.

**P0-1–P0-4, P1-1 ve P1-7 tamamlandı. P1-3 yerel sözleşmesi doğrulandı; tam Python paketi 403/403. P1-2 VPS erişimi ve P1-3 Pine/testnet dış kabulü açık. Sıradaki bağımsız kod işi P1-4 AI ilişkileri/scan history.**
