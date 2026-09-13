# Rapot Devam Planı

Bu belge, 6 Eylül 2026 tarihli salt okunur proje incelemesinden çıkan işleri ve uygulama ilerlemesini takip eder. Çalışma yöntemi: **incele → düzelt → doğrula → belgeyi güncelle**.

## Kaldığımız nokta

- **Son çalışma:** **P3-1 dördüncü adımın kod, CI ve kaynak yayını doğrulandı:** `f937744`, [CI 34755778327](https://github.com/Rapto0/Rapot/actions/runs/34755778327). Sabit günlük OHLCV, dahil start/end, tek UTC as_of ve önceki kapanmış günlük sinyalden sonraki gerçek Open yürütmesi; yeni 48/48, tam 878 Python testi / 1 isteğe bağlı performans testi atlandı, uyarı yok. Altı kaynak/kanıt dosyası 12:02:42 UTC'de sunucuya aktarıldı. BIST Close/AOF proxy açılışı reddedilir; gelişen HTF politikası korunur. Tam CLI veya canlı sağlayıcı kabulü değildir.
- **Uygulama durumu:** P0-1–P0-4, P1-1, P1-2, P1-4–P1-7, P1-G1, P2-1, P2-3 ve **P2-4 doğrulandı**; P2-2 belge/karar kapsamı tamam. İç worktree ve 12 wrapper koruma kararı değişmedi.
- **P1-2 durumu — Doğrulandı:** **8f60f8e üretim geçişi ve [HTTPS](https://138.68.71.27) kabulü tamamlandı.** API, bot, frontend, middleware ve PG16 sağlıklı; veri korunumu, dış HTTPS/auth/WSS, yetkisiz webhook reddi ve sertifika yenileme dry-run testi geçti. Eski supervisor'lar devre dışı; özgün DB/checkout ve geri dönüş kaynakları korundu.
- **Önceki sürümün uzak doğrulaması — 11 Eylül:** `ccd61544` için [CI 34641121926](https://github.com/Rapto0/Rapot/actions/runs/34641121926) ve [imaj yayını 34641767731](https://github.com/Rapto0/Rapot/actions/runs/34641767731) başarılı. Üretimde API health 47 ms/200; `/`, `/signals`, `/alarms`, `/chart` SSR 200. Beş servis healthy/restart0; SignalFeed hazır, Binance/BIST sağlayıcıları başlamış. Scheduler 47,298 saniyede unknown → running oldu. 1.733.137 sinyal, 6 tarama geçmişi, 26.393 AI kaydı ve diğer ana sayılar; PostgreSQL kimliği ve 135/135/28/383 sayıları korundu. DRY_RUN/false/false ve AI kapalı; dış Windows HTTPS API/bot kontrolleri ayrı ayrı 203 ms/200. Sonraki `aadde728` ve güncel `279aa9f` geçişlerinin 13 Eylül kanıtı P2-4 bölümündedir.
- **P2-2 doğrulaması ve belge yayını:** Python 3.12.8'de üç ayrı hedefli koşum toplam **98/98** geçti (wrapper/boundary/read-model 37, DB/migration 30, sinyal/config 31); DB grubunda mevcut 10 UTC warning var. 11 Eylül 15:44:58 UTC salt okunur sunucu ön kontrolünde beş servis healthy/restart0, HTTPS API/bot health 200 (0,051/0,043 saniye). Bu yalnız belge commit'inin tam SHA/CI sonucu, Git blob SHA256'ları ve sunucuya aktarım sonrası korunma kanıtı `/root/rapot-ops/20260911-p22/release-record.json` içinde sürüm bazında tutulur. İmaj yayını, servis restart'ı veya migration bu belge yayınının parçası değildir.
- **Aktif kapanış:** P3-1 dördüncü adımın kabulü aşağıda kaydedildi; bu kapanış belgesinin kendi SHA/CI ve sunucu aktarımı `/root/rapot-ops/20260913-p31-execution-closure/release-record.json` içinde tutulur. Kaynak yayını sonrası 12:03:32 UTC kontrolünde 620.085.248 B boş alan, beş sağlıklı servis ve dış HTTPS 200 doğrulandı; frontend967/backend279 aynı. CI'deki npm bildirimi için **P1-G2 bağımlılık güvenliği incelemesi** açıldı; 11 bildirimin etki ve düzeltme kapsamı doğrulanmadan temiz güvenlik sonucu denmez. Sonraki backtest kod işi ortak nakit kronolojisi ve tutarlı çoklu sembol fiyatlamasıdır. Benchmark/WFA, yeni Pine dış kabulü ve borsa emirleri açık/erteli kalır.
- **P3-1 ikinci adımın yayın kapanışı:** `48be08e6d3717693e601c9f62c3e1b6665a8c85a`, [CI34749745272](https://github.com/Rapto0/Rapot/actions/runs/34749745272) beş job başarılı. 09:40:19 UTC'de 11 canonical kaynak/rapor dosyası488.483B ve12.462B kayıt sunucuda hash/gzip ile doğrulandı; `/root/rapot-ops/20260913-p31-indicators/release-record.json` SHA256 `426a3041f78c22ecb0328c260bbf956178af2be39262b8757522f88e207866b0`. Beş servis/config aynı, dış HTTPS200; frontend967/backend279 aynı kaldı. TradingView script/alarm kopyası değiştirilmedi.
- **Ertelenen dış kabul:** Gerçek TradingView alarm teslimi, ALL/FIRST/saat filtresi runtime kabulü ve sınırlı testnet emir testi tamamlanmış sayılmıyor. Hazır test araçları korunuyor; testnet onayı ve Webhook URL erişimi için artık yanıt beklenmiyor, bu işler kullanıcı yeniden seçtiğinde ele alınacak. Borsa emri gönderilmedi; geçici test servisleri kapalı.
- **Başlangıç kaydı:** Bu belge ilk oluşturulduğunda yalnız belge değişmişti; sonraki uygulama değişiklikleri aşağıda ayrı kaydedildi.
- **Seçilen geliştirme ortamı:** `.venv` / Python 3.12; Node 20.20.2 / npm 10.9.9. Yerelde Python 3.12.8 ile doğrulandı.
- **Commit / yayın düzeni:** Her tamamlanan P maddesi ayrı commit; doğrulanan grup CI için push edilir, sunucu deploy'u CI ve sunucu kontrollerinden sonra yapılır. İlk sunucu yayını eşiği P0 işleri + P1-7 test hatası + P1-2 dağıtım uyumu.
- **Açık işler:** P1-G2, P3-1/P3-2 ve kullanıcı isteğiyle ertelenmiş gerçek TradingView alarm/filtre ve testnet emir kabulü. Ücretli yükseltme veya diğer yedek, imaj, release ve günlükler için toplu silme yapılmaz. İlk P3-1 frontend geçişi kabulünde boş disk **562.618.368 B (yaklaşık 537 MiB)**; sabit 528 MiB pay korundu. Her yeni yayından önce büyüyen veriler, imaj katmanları ve çalışma payı yeniden ölçülmelidir.

## Kapsam ve yetki kaydı

Kullanıcının ilk isteği yalnız inceleme ve raporlamaydı; dosya değişikliği, kod yazma ve commit açıkça yasaktı. Sonraki isteği bu takip belgesinin tutulmasını ve uygulamada yukarıdaki dört adımın izlenmesini belirledi.

- Kullanıcının P0-1 isteğiyle bu madde için gerekli yerel kod/test/konfigürasyon değişiklikleri, geliştirme bağımlılıklarının kurulması ve izole doğrulama kapsam dahilindedir. P0-1 tamamlandı; sonraki uygulama yetkisi aşağıda kaydedildi.
- Kullanıcının "Devam et" talimatıyla sıradaki P0-2 başlatıldı; backend yetki kontrolleri, bunları kullanan frontend giriş akışı, test ve belge değişiklikleri kapsam dahilindedir.
- Kullanıcının sonraki talimatı, yapılan geliştirmelerin otomatik commit/push ve sunucu deploy'una izin verdi; zamanlamayı asistana bıraktı. Seçilen düzen: her tamamlanan iş için yerel commit; P0/P1 gibi gruplar tamamlanınca kontrollerin geçtiği commitleri push et ve sunucuda doğrulanmış deploy yap. Aynı kapsam için yeniden onay sorulmaz.
- 2026-09-09'da kullanıcı, somut root SSH anahtarı ekleme ve kurulum komutunu çalıştırma sorusuna "Her şeye onayım var devam et" yanıtını verdi. Bu erişim kurulumunun açık onayı alındı; önceki otomatik onay engeli yeni yetkiyle çözüldü. Emir/testnet kapsamı aşağıdaki ayrı sınırlarını korur.
- Kullanıcı 2026-09-09'da alan adı olmadan IP HTTPS kurulmasını ayrıca onayladı; sertifika/nginx işlemleri bu kapsamdadır.
- Kullanıcı 2026-09-10'da borsa hesabında parası olmadığını belirterek bunu ilgilendiren adımları erteledi, diğer görevlere devam istedi. P1-3 dış alarm/emir kabulü ertelendi; test araçları çalıştırılmayacak. P1-4 ve diğer borsa emri gerektirmeyen işler için incele/düzelt/doğrula/belge ve önceki commit/push/deploy yetkisi sürüyor.
- Kullanıcı 2026-09-11'de **“Hayır, ücretli yükseltme yapma”** dedi. DigitalOcean plan seçimi iptal edildi; mevcut $6/ay plan korunur. Kalıcı özel bilgisayar klasörüne eski yedeklerin kopyalanması ve bağımsız doğrulanması ücretsiz kapasite hazırlığıdır; sunucu kopyalarının silinmesi için dosyaları açıkça belirten ayrı onay gerekir.
- Kullanıcı, üç dosyanın tam yollarının sunulduğu silme onayı sorusu ve bu kararı bekleyen son yanıttan sonra **“Kaldığın yerden devam et”** dedi. Bu doğrudan devam talimatı yalnız listelenen üç eski sunucu kopyası için onay olarak yorumlandı ve işlem öncesinde kullanıcıya açıklandı. Asıl kullanıcı ifadesi, bağlam ve doğrulama manifesti hash'i ayrı operator onay kaydına yazıldı; ücretli yükseltme, diğer yedekler/imajlar/release'ler ve borsa işlemleri kapsam dışı kaldı.
- Kullanıcı 2026-09-13'te dört eski kapalı sistem günlüğünün somut kaldırma önerisine **“Eğer projemiz aksamayacaksa silinmesi gerekenleri sil ve kaldığın yerden devam et”** yanıtını verdi. Bu onay, `four-file-removal-proposal.json` içindeki yalnız dört sunucu dosyasını kapsar (öneri SHA256 `3934235b2e80c856313975f073a019a238276f91e5046605785f7a6d51d7fd98`). Özel bilgisayar arşivi, tüm üye hash'leri/CRC/ACL ve sunucu dosyalarının sabit kimliği, ARCHIVED durumu ve kullanılmadığı yeniden doğrulanmadan silme yapılmaz. Uygulama/veritabanı dosyaları, diğer sekiz yedeklenmiş günlük, diğer yedek/imaj/release'ler ve ücretli kapasite artışı bu onayın kapsamında değildir. Günlük temizliği servis restart'ı gerektirmez; önceden yetkilendirilmiş uygulama geçişinin kısa kesinti gerektirebileceği ayrıca açıklandı.
- Kullanıcı 2026-09-13'te, aşağıdaki tek eski günlük dosyasını kaldırıp frontend dağıtımını tamamlama sorusuna **“Kaldığın yerden deavm et”** yanıtını verdi. Bu doğrudan yanıt, yalnız `p31-one-journal-removal-proposal.json` önerisindeki tek dosyanın onayı olarak yorumlandı ve işlem öncesinde kullanıcıya açıklandı. Yeni onay kaydı 08:52:50 UTC'de, öneri SHA256 `9f88d6e7c18307c3dcd080ecedd9b4f6c38a1c3fb299b60255f2a1b0ddf64e65` ve tam hedef yoluyla bağlandı. Diğer yedi arşiv günlüğü, yedekler, imajlar, veriler ve ücretli yükseltme bu onaya dahil değildir.
- Belgenin varlığı; bağımlılık kurulumu, kod/konfigürasyon değişikliği, migration, commit/push, deploy, servis başlatma, testnet emri veya gerçek emir için kendi başına yetki oluşturmaz.
- Kullanıcı 2026-09-13'te muhasebe kaynak yayını için önerilen tek ek eski günlüğün kaldırılması sorusuna **“Kaldığın yerden devam et”** yanıtını verdi. Bu doğrudan yanıt yalnız `p31-accounting-one-journal-removal-proposal-final.json` içindeki dosya için onay olarak yorumlandı ve işlem öncesinde açıklandı. Öneri SHA256 `6040593375bfbbc127b334e4cccc8346c5ee49222b81c4083e2b8f2dd10f5407`; yeni yetki kaydı SHA256 `eb2121308c7b99a6ce1841e35914b56db4fd9d2a358dc3d391ce782f2d9d414c`. Kayıttaki 11:22:36 UTC, yanıt okunduktan sonraki kayıt zamanıdır. Diğer altı eski günlük ve özel yedek korunur; ücretli yükseltme veya borsa emri yetkisi eklenmez. Disk zaten yayın rezervinin altında olduğundan yalnız bu kurtarma temizliği için sınırlı audit kaydı yazılır; 528 MiB yayın rezervi düşürülmez ve aktarım öncesinde gerçek boş alan ayrıca doğrulanır.
- Sonraki kullanıcı talimatıyla kapsam değişirse bu kayıt güncellenir. Daha önce açıkça verilmiş yetki tekrar sorulmaz.
- Gerçek hesap, üretim veritabanı ve VPS üzerinde yapılan işlemler yerel geliştirme/test işlemlerinden ayrı kaydedilir.
- Deploy yetkisi, gerçek/testnet emir gönderme, veri silme, force-push veya sunucudaki bilinmeyen yerel değişiklikleri ezme yetkisi olarak yorumlanmaz.
- Gizli anahtarlar, parolalar ve token değerleri bu belgeye yazılmaz.

### Commit, push ve sunucu deploy düzeni

1. Her P maddesinde **incele → düzelt → doğrula → belgeyi güncelle → yerel commit** sırası uygulanır. Commit yalnız o işe ait dosyaları içerir. P0-1 gibi amacı başlangıç test tabanı kurmak olan işlerde mevcut davranış hataları açık iş ID'leriyle kaydedilerek checkpoint commit'i oluşturulabilir.
2. **Push**, grubun yerel tam testleri, değişen dosya lint'i ve frontend typecheck/build kontrolleri geçince CI doğrulamasını başlatır. 9 Eylül'de yerel Docker motoru açılamadığı için imaj ve geçici PostgreSQL kontrolü Linux CI'ye taşındı. **Sunucu deploy'u** için bu CI sonucu da başarılı olmalı; P0 işleri, P1-7 ve P1-2 dağıtım uyumu kapıları sağlanmalıdır. CI başlatmak için yapılan push sunucu deploy'u sayılmaz.
3. Deploy öncesinde hedef sunucu/branch, çalışan sürüm ve yerel değişiklikler okunarak kontrol edilir. Deploy, doğrulanmış commit ile yapılır; ardından sunucu commit'i, süreçler ve sağlık kontrolleri doğrulanıp buraya kaydedilir. Başarısız adımın ardından yayın zinciri ilerletilmez.
4. Bu düzen kapsamındaki commit/push/deploy için kullanıcıdan her seferinde tekrar onay istenmez. Erişim bilgisi gerçekten eksikse veya kapsam dışı veri işlemi gerekiyorsa yalnız o eksik nokta açıklanır.

**Yalnız belge değişiklikleri:** Kaynak/bağlantı ve ilgili mevcut regression kontrolleri yapılır; tam SHA CI sonucu doğrulanır. Değişen belgeler Git blob'larından alınarak sunucuda sürümlü operator kaydına aktarılır ve SHA256 karşılaştırılır. Uygulama imajı/pointer/config veya veritabanı değiştirilmez, servis yeniden başlatılmaz. Son belge commit'inin kendisine referans döngüsü yaratmamak için tam commit/CI sonucu ve aktarım sonrası kabul, ilgili `/root/rapot-ops/<tarih-iş>/release-record.json` kaydında tutulur; yalnız push sunucuya belge aktarımı sayılmaz.

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
| P1-2 | Çalıştırma ve dağıtım topolojisi | Doğrulandı — üretim Compose, veri göçü, HTTPS/auth/WSS ve yenileme kabulü geçti | Orta | P0-1 |
| P1-3 | Pine sözleşmesi ve testnet kabul akışı | Yerel/CI, kullanıcı derleme/grafik ve izole VPS HTTPS/simülasyon kabulü tamam; dış alarm/emir kabulü kullanıcı isteğiyle ertelendi | Orta | Tüm P0 işleri, P1-1; dış kabul için P1-2 |
| P1-4 | AI ilişkileri ve scan history | Doğrulandı — yerel/CI ve fce5d01 üretim yayını tamam | Orta | P0-1 |
| P1-5 | Süreçler arası realtime ve scanner eşdeğerliği | Doğrulandı — yerel/CI ve a513af9 üretim kabulü tamam | Orta/büyük | P0-1, P1-2 |
| P1-6 | PnL, bot durumu ve ayarlar ekranı | Doğrulandı — üretim ve dış kabul tamam | Orta | P0-1; backend ayar sözleşmesi ve P0-2 |
| P1-7 | HUNTER kısa seride ATR hatası | Doğrulandı | Küçük/orta | P0-1 |
| P2-1 | Dışa aktar, alarmlar ve grafik URL davranışı | Doğrulandı — yerel/CI ve db98915 frontend üretim kabulü tamam | Orta | P0-1 |
| P2-2 | Belgeler ve wrapper göçünün kapanışı | Doğrulandı — kaynak/belge/98 hedefli test; 12 wrapper korunacak | Küçük/orta | Fiziksel kaldırma için dış tüketici ve süreç kanıtı ayrıca gerekli |
| P2-3 | Ruff, atıl kod ve araç tarama kapsamı | Doğrulandı — yerel/CI, bacbfab8 imajları ve üretim kabulü tamam | Küçük/orta | P0-1 |
| P2-4 | Eşzamanlı API yükünde realtime gecikmesi | Doğrulandı: 279aa9f, 735 Python testi, büyük veri ölçümü, CI ve üretimde 24 REST / 3 WSS kabulü | Orta | P1-5 |
| P0-G1 | Standalone sağlık sunucusu debug varsayılanını kapat | Doğrulandı — loopback/debug/reloader düzeltmesi P2-3 ile üretimde; yerel/CI HIGH=0 | Küçük | P2-3 raporu ve entrypoint kontrolü |
| P1-G1 | Kilitli Python bağımlılığı advisory incelemesi | Doğrulandı — 710/710, sıfır dependency bulgusu; CI/imaj/üretim ve auth13/13 geçti | Orta | P2-3 raporu; uygulama/test bağımlılığı ayrımı |
| P3-1 | Backtest ve strateji eşdeğerliği | COMBO üretimde; motor/Pine, FIFO ve günlük yürütme kaynak kabulü tamam. Günlük yürütme 48/tam 878-skip1, exact CI ve altı dosya hash doğrulaması geçti. Ortak nakit kronolojisi/fiyatlama, benchmark/WFA ve Pine dış kabulü açık | Büyük | Emir/veri doğruluğu, P1-3, P1-4 |
| P3-2 | Backup branch tasarım değerlendirmesi | Bekliyor | Küçük inceleme | Tasarım tercihi |
| P1-G2 | Frontend bağımlılık güvenliği | npm ci 11 bildirim: 1 düşük, 2 orta, 7 yüksek, 1 kritik; etki/düzeltme incelemesi açık | İlk inceleme küçük; düzeltme kapsamı henüz belirsiz | Lock/üretim erişilebilirliği ve CI |

**Önerilen sıra:** Başlangıç sırası P0-1 → P0-2 → P0-3 → P0-4, ardından P1-1/P1-2/P1-3 idi. P1-G1 ve P2-4 tamamlandı; yeni npm bildirimlerinin **P1-G2** etki/düzeltme incelemesi, P3-1 beşinci adımdan önce ele alınır. Ardından P3-1 → P3-2; P1-3 dış kabulü kullanıcı yeniden seçene kadar ertelidir.

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

Tek Python çalışma ortamı `.venv`; eski `venv` ve sistem Python silinmedi veya proje bağımlılıklarıyla güncellenmedi. `requirements.txt` uygulamanın sürüm aralıklarını ve `requirements-security.txt` transitif güvenlik kısıtlarını, `requirements-dev.txt` test araçlarını, `requirements-dev.lock` Python 3.12 için tam sabitlenmiş geliştirme/CI çözümünü tutar. Normal kurulumda lock dosyasını kullan. `pytest.ini` tek pytest ayar kaynağıdır; coverage ayarları `pyproject.toml` içindedir.

Repo kökünde PowerShell (uv 0.9.26 ile doğrulandı):

```powershell
# Yalnız .venv henüz yoksa oluştur:
uv venv --python 3.12 .venv

# Var olan .venv'yi de lock dosyasındaki paketlerle eşitle:
uv pip sync --python .venv/Scripts/python.exe requirements-dev.lock
uv pip check --python .venv/Scripts/python.exe

# Önce aşağıdaki Node 20 / frontend npm ci kurulumu da hazır olmalı.
# Her iki test dizinini toplar; .env veya gerçek servis gerekmez:
.venv/Scripts/python.exe -X utf8 -B -m pytest
.venv/Scripts/python.exe -X utf8 -B -m pytest --cov=. --cov-report=xml

# Belirli testler için de aynı izolasyon devrede kalır:
.venv/Scripts/python.exe -X utf8 -B -m pytest middleware/tests
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_test_isolation.py
```

Linux/macOS'ta aynı komutlarda yorumlayıcı yolu `.venv/bin/python` olur. CI temiz ortamda `python -m pip install -r requirements-dev.lock` ve `python -m pip check` kullanır. CI Python sürümünü `.python-version` dosyasından okur.

P3-1 ikinci adımından itibaren tam pytest, gerçek Python/TypeScript gösterge
karşılaştırmasını da içerir: Node 20 ve frontend kilit bağımlılıkları gerekir.
PATH farklı bir Node sürümünü gösteriyorsa `NODE_BINARY` değişkenine Node 20
yürütücüsünün tam yolunu ver. Bu kontrol sessizce atlanmaz. İsteğe bağlı
`RAPOT_STRATEGY_REPORT` mutlak JSON yoluyla sentetik ölçüm kanıtı yazılır;
[karşılaştırma belgesi](STRATEGY_COMPARISON.md) kapsamı ve komutu açıklar.

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

**2026-09-09 uygulaması:** Canonical topoloji Compose 2.24+: tek worker API + ayrı tek bot + Next standalone; opsiyonel middleware + ayrı PostgreSQL + tek seferlik Alembic servisi. Ana SQLite dizini `RAPOT_DATA_DIR` ile WAL/SHM ve bot kilidi dahil paylaşılır; kaynak kod image'dan gelir. Python 3.12.8/runtime constraint lock, Node 20.20.2/npm 10.9.9, build sırasında API/health Compose DNS hedefleri ve aynı origin üzerinden WebSocket yolu uygulandı. Ana DB hazırlığı ve middleware migration başarı koşulları başlatmaya bağlandı; üretimde Alembic head kontrol edilir, sürümsüz eski mw_* tabloları otomatik stamp edilmez. Doğrudan ve embedded bot girişleri ortak dosya kilidiyle korunur. Eski kilitsiz VPS süreçleri ilk geçişte tespit edildi; yedek ve sahiplik kontrolünden sonra eski supervisor'lar devre dışı bırakıldı.

**Araç/doküman:** `scripts/runtime.py`, Compose, Dockerfile'lar, build-context dışlama kuralları, legacy PM2 launcher'ları, CI image kontrolleri ve `scripts/DEPLOY.md` güncellendi. Deploy scripti temiz ağaç + tam doğrulanmış SHA ister; isteğe bağlı push ve gerçek davranışını açıkça belirten manuel sunucu komutları üretir. Stage-all, stash ve reset kaldırıldı. Workflow'un image yayınlaması sunucu deploy'u olarak sunulmuyor.

**Geçen kontroller:** Yeni Python kilit/topoloji/şema testleri 10/10; tam paket 315/319 ve yalnız önceki P1-7 hataları. Frontend 12/12, ESLint, TypeScript dahil production standalone build; gerçek standalone sunucuda sahte localhost API/bot ile HTML, statik JS, Authorization/query aktarımı, health ve WebSocket 101 testi geçti. Compose config ve PowerShell AST doğrulandı; değişen Python dosyalarında Ruff lint/format geçti.

**İlk ortam engeli kaydı (tarihsel):** Docker Desktop 4.70.0 motoru başlamıyor. 9 Eylül logunda `starting services: initializing Inference manager ... dockerInference ... Sistem dosyaya erişemiyor` hatası var. Factory reset, Docker verisi silme veya sistem ayarı değiştirme yapılmadı; gerekli Linux imaj/migration doğrulaması GitHub CI'de tamamlandı. VPS SSH kimlik doğrulaması reddedildi; `.ssh` altında yalnız known_hosts dosyaları bulundu, kullanılabilir SSH agent veya bu host için kayıtlı PuTTY oturumu bulunamadı. Kullanıcı erişim bilgisini bilmediğini belirtti. Bu aşamada sunucu süreçleri, veri yolu ve deploy sonucu doğrulanamadı; sonraki konsol erişimi aşağıda kayıtlı.

**2026-09-09 ilk konsol envanteri (tarihsel):** Kullanıcı DigitalOcean'a giriş yaptı; `rapot-server`, droplet `546670708`, `138.68.71.27`, FRA1, Ubuntu 22.04, 1 GB RAM / 25 GB disk doğrulandı. `/droplets/546670708/console` mevcut root konsolunu açıyor. Panel CPU %99,9–100; `ps` örneğinde uvicorn PID `3345682` %80,2 CPU ile PM2 PID `748` altında, ayrıca parent PID 1 altında uvicorn PID `2509` var. Bu aşamada süreç sahipliği açık, PM2 `api`, `frontend`, `rapot-bot` online ve API restart sayısı tam okunamamıştı. Bellek 957 MiB toplam / yaklaşık 308 MiB kullanılabilir; 2 GiB swap'ın yaklaşık 987 MiB'ı kullanımda, disk 7,8 GB boştu. Docker/Compose kurulu değildi; sonraki SSH envanteri ve işlemler aşağıda kayıtlı.

**İlk checkout/erişim kaydı (tarihsel):** `/root/Rapot`, branch `main`, HEAD `62ff6cf`. Git status yalnız `middleware/.env.bak-before-osmanli-proxy-20260504-143218` ve iki Alembic `__pycache__` kaydını untracked gösterdi; içerikleri okunmadı, silinmedi. Uzun VNC tuş komutları bozuluyordu; kendi salt okunur `systemctl` sorgumuz kapanmamış tırnakla `>` devam isteminde kaldı. Ctrl+C işlemi otomatik onay incelemesince iki kez reddedildi; kullanıcıdan satırı temizlemesi istendi. Yerelde, repo dışında bu bilgisayara özel `rapot_deploy_ed25519` anahtarı oluşturuldu; dosya ACL'si kullanıcı, SYSTEM ve yerel Administrators ile sınırlı. Bu aşamada SSH reddi sürüyor ve anahtar ekleme onayı bekleniyordu; aşağıdaki açık onayla çözüldü.

**Sunucuda build yükünü önleme:** Mevcut `deploy.yml` ile main `8f60f8ece7b728f832b0bf2d9d5ba5a7949c47be` için [34378537277](https://github.com/Rapto0/Rapot/actions/runs/34378537277) başarılı. `ghcr.io/rapto0/rapot/backend` digest `sha256:e9e2128590ef3d11b5f17e28f19c531642a7f9de61c31097c7ff5eebdec1be3e`; frontend digest `sha256:e43efa6ed90c522dd0b7d7d25160028962199baa88f494f2d820c3c24d81526b`. İki imaj için anonim HEAD erişimi başarılı. Yayın anında sunucuda pull/build/deploy, yedek, migration veya servis değişikliği yapılmamıştı; sonraki sunucu işlemleri ayrı kayıtlı.

**Onay öncesi son erişim kontrolü (tarihsel):** Kullanıcı önceki konsol satırını temizledi; normal `root@rapot-server:~#` istemi doğrulandı. Kopan VNC oturumu aynı konsol üzerinden yeniden bağlandı. Özel Rapot anahtarıyla tek salt okunur SSH denemesi yine `Permission denied (publickey,password)` döndü. Otomatik onay denetimi bu kez konsolda hazırlanmış `date` komutunun Enter ile çalıştırılmasını reddetti; alternatif tuşla veya yapıştırılan satır sonuyla çalıştırma denenmedi. Uzun yapıştırma da bozulduğu için yalnız çalıştırılmamış satır temizlendi; konsol boş bırakıldı. `runtime-data/rapot-ssh-bootstrap.txt` mevcut anahtarları koruyan, symlink hedefini reddeden, tekrar eklendiğinde çoğaltmayan ve yeni public key'i `restrict` ile sınırlayan kullanıcı kurulum bloğudur; Bash `-n` kontrolü geçti ve dosya Git tarafından yok sayılıyor. Private key repo dışında kalır. Bu aşamada kullanıcı kurulumu bekleniyordu; henüz sunucu ayar/veri değişikliği, deploy veya emir yoktu.

**Açık onay sonrası SSH ve süreç tespiti:** Kullanıcının somut SSH kurulum sorusuna açık onayından sonra public key root hesabına `restrict` ile eklendi; fingerprint `SHA256:ogt/eyP7aOPtltDAkl+GHBz2P7kSFCwzz447lEEGoKI`. SSH üzerinden `id` sonucu `uid=0` doğrulandı. Eski checkout `main/62ff6cf` ve untracked kayıtları korundu. PM2 API logunda port çakışması ve **1.485.202 restart** doğrulandı. Müdahale öncesi süreçler: legacy API PID `2509` → 8000; legacy `main.py` PID `2508` → 5000; aynı DB'yi kullanan PM2 bot PID `2512`; frontend PID `3850` → 3000; systemd middleware PID `1378047` → 8010.

**Koruma ve ilk servis müdahalesi (tarihsel):** Önce `/root/rapot-ops/20260909-8f60f8e/config-backup` altında yalnız root erişimli env, PM2 jlist/dump, `nginx.tar` ve systemd unit yedekleri alındı. Sonra yalnız port çakışan PM2 API ve ikinci PM2 bot durduruldu; diğer legacy servisler bu aşamada çalışmaya devam etti. Üretim checkout'u değiştirilmedi; `8f60f8e` kaynak arşivi ayrı ops dizinine aktarıldı. Tam geçişin sonraki durumu aşağıda kayıtlı.

**İlk veri yedek kanıtı:** Aynı ops dizininin `db-backup` alanında online SQLite backup alındı; iki dosyada `quick_check=ok`. Ana DB **1.169.977.344 bayt**, SHA-256 `c12b828b04c5aa75bd0ec3d7f5aa5fa3f25705c1adc66681c5ae7a70f83ac35d`; cache **988.483.584 bayt**, SHA-256 `26bbeae3c728c6db18c657e18b3ad09f18676a9c9752873bcde6c9640c9220e9`. Ana yedek anındaki sayılar: signals **1.721.138**, ai_analyses **26.393**, bot_stats **4**; trades/orders/scan_history **0**. Bunlar yedek anının sayılarıdır, yerel başlangıç DB'siyle karıştırılmamalı. PostgreSQL `middleware.dump` **57.554 bayt**; `pg_restore --list` geçti, yalnız `runuser` çalışma dizini uyarısı görüldü. Bu aşamada restore testi yapılmamıştı; sonraki izole ve üretim restore sonuçları aşağıda.

**Docker kurulumu öncesi durum (tarihsel):** Middleware PostgreSQL 14 / localhost:5432 üzerinde; `DRY_RUN`, trading/live kapalı ve `testnet.binance.vision` ayarları doğrulandı. Bu aşamada migration/emir gönderilmemişti. `nginx -t` enabled yedek config dosyaları nedeniyle iki çakışan server_name uyarısıyla geçti. Docker apt kurulumu sürüyor; izole smoke/geçiş bekliyordu. Sonraki işlemler bu engelleri aşağıdaki kapsamda giderdi.

**2026-09-09 üretim sürümü ve topoloji:** Resmi kaynaktan **Docker 29.8.0 / Compose 5.5.1** kuruldu. `8f60f8ece7b728f832b0bf2d9d5ba5a7949c47be` sürümü `/opt/rapot/releases/` altında; `/opt/rapot/current` bu release'e bağlı. `/etc/rapot/main.env`, `middleware.env`, `release.env` yalnız root erişimli `0600`; `/etc/rapot/compose.images.yml` imajları digest ile sabitliyor. Üretimde yukarıda kayıtlı backend/frontend digest'leri ve PostgreSQL digest `sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685` kullanılıyor. API:8000, bot:5000, frontend:3000 ve middleware:8001 yalnız loopback'e bağlı; PG16 host portu yayımlamıyor. **Beş production konteyner sağlıklı.** Eski PM2 süreçlerinin tümü durduruldu, `pm2-root` devre dışı; eski `rapot-middleware` systemd servisi durduruldu/devre dışı.

**Ana veri ve geri dönüş:** Eski `/root/Rapot` checkout'u (`62ff6cf`), untracked kayıtlar ve asıl eski DB dosyaları korundu. Yazıcılar durdurulduktan sonra son veri kopyaları `/var/lib/rapot/main` altına alındı; SQLite `quick_check` ve **1.721.138 sinyal** korunumu doğrulandı. Mevcut giriş bilgileri/Telegram hedefi korundu; yeni ortamda Binance kimlik bilgileri boş. Ops `db-backup` alanındaki SQLite yedekleri gzip ile sıkıştırıldı; geri açılan ham içerik hash'leri yukarıdaki SHA-256 değerleriyle aynı. Sıkıştırılmış ana yedek 229.557.912 bayt, cache 4.887.808 bayt; yalnız doğrulanan yeni ham yedek kopyaları kaldırıldı. `rollback-main.sh` eski PM2 dump'ını kullanacak şekilde hazırlandı ve `bash -n` geçti; rollback uygulanmadı.

**Ana smoke ve dış HTTP kabulü:** Ayrı env/port/SQLite kopyasıyla HTML/rotalar/health, tokensız **401**, login/admin ve WebSocket **101** kontrolleri geçti. API restart sonrası 1.721.138 sinyal değişmedi. Smoke durduruldu, yalnız ona ait veri kopyası kaldırıldı; JSON sonuçlar ve loglar ops dizininde saklandı. Üretimde dış HTTP'den beş rota **200**, nginx üzerinden yetki ve WebSocket kontrolleri geçti. Çakışan iki nginx yedek config'i `ops/disabled-nginx-configs` altına taşındı; `nginx -t` uyarısız ve reload başarılı. Webhook upstream'i 8010'dan 8001'e geçirildi.

**Middleware restore ve üretim göçü:** Önce ayrı PG16 volume'unda PG14 `middleware.dump` restore edildi, Alembic **0003 → 0006** ve kapalı işlem health kabulü geçti. Ardından eski middleware yazıcısı durdurulduktan sonra alınan `middleware-cutover.dump`, ayrı production PG16 volume'una restore edildi ve aynı migration uygulandı. **135 sinyal / 135 emir / 28 tranche / 383 execution report** korundu; tüm eski emir/tranche'lar `LEGACY_UNCLASSIFIED` kapsamına alındı. Bekleyen emir **0**; **19 açık DRY_RUN tranche** silinmeden karantinada tutuluyor. Üretim middleware health sonucu `DRY_RUN`, trading/live kapalı. `ops/middleware-production-results.json` sonucu `verified`. Gerçek veya testnet emri gönderilmedi.

**Son P1-2 kabulü — HTTPS doğrulandı:** Kullanıcının açık onayıyla Certbot **5.8.0** ve Let's Encrypt IP sertifikası nginx:443'e kuruldu; TLS 1.2/1.3, SAN `138.68.71.27`, geçerlilik `2026-09-09 17:11:26 UTC` → `2026-09-16 09:11:25 UTC`. HTTP:80, ACME challenge yolu dışında aynı URI ile HTTPS'ye **308** yönlendiriyor. Windows dış istemcisinden sertifika kontrolü atlanmadan `/`, `/login`, `/signals`, `/api/health`, `/api/signals?limit=1`, `/health-api/health` olmak üzere **altı HTTPS rota 200**; HTTP yönlendirmesi 308. HTTPS admin login ve `/auth/me` geçti, anonim erişim 401. WSS `/api/realtime/ws/signals` **101** ve düzgün kapanış doğrulandı. Yetkisiz HTTPS `/webhooks/tradingview` POST'u **401**; middleware sayıları öncesi/sonrası **135/135/28/383** ile aynı, emir oluşmadı. Ana env'e yalnız HTTPS CORS origin'i eklendi, diğer değerlerin eşitliği kontrol edildi ve API yeniden oluşturulup sağlıklı oldu.

**Yenileme ve kapanış kanıtı:** `certbot renew --dry-run --run-deploy-hooks --no-random-sleep-on-renew` exit **0**; `snap.certbot.renew.timer` enabled/active. Çalıştırılabilir `/etc/letsencrypt/renewal-hooks/deploy/rapot-nginx.sh`, `nginx -t` sonrası reload yapıyor. Ops `https-production-results.json` sonucu `verified`; beş konteyner healthy / restart **0** / `unless-stopped`, ana DB **1.721.138 sinyal**, eski boot servisleri devre dışı. `nginx-before-tls.conf` ve `main-before-tls.env` özel yedekleri saklandı. IP sertifikası ve otomatik yenileme düzeninin resmi dayanakları: [Let's Encrypt IP sertifikaları](https://letsencrypt.org/2026/03/11/shorter-certs-certbot), [Certbot yenileme rehberi](https://eff-certbot.readthedocs.io/en/stable/using.html#renewing-certificates).

**İşletim sınırı:** Son ölçümde disk **2,7 GB boş / %89 dolu**, RAM **312 MiB kullanılabilir**, swap **439 MiB kullanımda**. Yeni imaj veya yedekten önce kapasite yeniden kontrol edilmeli; veri ve rollback kaynakları temizlenmedi. P1-2 üretim geçişi/kabulü tamamlandı; Pine derlemesi, gerçek alarm teslimi ve testnet emir kabulü P1-3'te ayrı açık kalır.

**Belge kapanışı:** Bu dağıtım/TLS adımında takipli uygulama kaynağı değişmedi; yalnız devam planı güncellendi. Yerel üç gerçek DB hash'i başlangıçla, tam Pine TXT kopyasının SHA-256'sı orijinal kaynakla aynı. Belge commit/push sonrasında operasyon dizinine ayrıca kopyalanacak; çalışan `8f60f8e` imajları yalnız belge değişikliği için yeniden üretilmeyecek. Sertifika yenileme logunda hem tüm deneme yenilemelerinin başarısı hem nginx hook'unun başarılı config testi doğrulandı; hook hata işareti yok.

**İlk açılış öncesi veri kapısı:** `scripts/runtime.py` içindeki `init-main-db`, `db_session.init_db()` ile şemaya yazabilir. `api/main.py::_run_startup_sequence` ayrıca `reconcile_active_orders_on_startup()` çalıştırır; eski aktif emirleri STALE, Binance sorgusuna göre bazılarını UNKNOWN yapabilir. Mevcut DB yolu/sahibi ve tutarlı yedek doğrulanmadan main-init/API başlatılmamalı. Pine/alarm/testnet kabulü ve emir izinleri bu sunucu erişimiyle tamamlanmış sayılmaz.

**CI doğrulama eklemesi:** GitHub Linux runner'ında backend imajından ağsız import kontrolü, izole Docker ağı ve geçici PostgreSQL 16 ile sıfırdan Alembic migration, production middleware şema kapısı ve DRY_RUN/işlem kapalı health kontrolü eklendi. Test kaynakları koşum sonunda kaldırılır; gerçek DB/hesap bilgisi kullanılmaz. PostgreSQL readiness, init sırasında yalnız Unix socket'te çalışan geçici sunucuyu hazır saymamak için TCP `127.0.0.1` kullanır; Compose kontrolü de aynı düzeltmeyi içerir. İki workflow YAML ve tüm shell blokları `bash -n` kontrolünden geçti; push grubundaki 55 Python dosyası Ruff lint/format kontrolünden geçti. Gerçek başarılı koşum aşağıda kayıtlı.

**İlk Linux koşumu (tarihsel):** [34366928776](https://github.com/Rapto0/Rapot/actions/runs/34366928776), `5449aae` üzerinde Python/lint başarılı; frontend build sonrası standalone smoke adımında bekledi. Logda işlevsel kontrollerin geçtiği, kapanışın takıldığı doğrulandı. Test, Linux Next.js graceful shutdown'ı beklemeden önce mock upstream soketlerini kapatacak şekilde düzeltildi; statik yanıt gövdesi tüketiliyor, HTTP/süreç beklemeleri ve CI smoke adımı süre sınırına sahip. Yerel smoke ve ESLint tekrar geçti; takılan kendi koşumumuz iptal edildi. Bu test düzeltmesi uygulamanın çalışma davranışını değiştirmiyor.

**İkinci Linux koşumu (tarihsel):** [34367517745](https://github.com/Rapto0/Rapot/actions/runs/34367517745), `86718fc` üzerinde Python 329/329 ve frontend'in tüm adımları geçti; standalone kapanışı düzeldi. Backend imajı üretildi fakat import smoke ortamında `JWT_SECRET_KEY` eksikti. Yalnız bu ağsız test için sahte anahtar eklendi; uygulamanın zorunlu anahtar kontrolü korundu. Aynı importlar yerelde test izolasyonuyla geçti. Ayrıca frontend imajının gerçekten başlayıp HTML/statik JS sunduğunu ağsız container ile doğrulayan adım eklendi.

**Başarılı Linux koşumu:** [34368224479](https://github.com/Rapto0/Rapot/actions/runs/34368224479), tam kaynak SHA `3b9bbbf84c7a7b37e61b80042647b50c30ef8f90`, 2026-09-09. Python/lint/frontend işleri ve Docker işi başarılı. Backend imajı Python 3.12.8 altında ağsız import edildi; PostgreSQL 16 üzerinde tüm altı revision `20260907_0006`'ya kadar uygulandı. Production middleware DRY_RUN ve `trading_enabled=false` ile açılıp health kontrolünü geçti. Frontend standalone imajı üretildi, ağsız container içinde HTML ve statik JS sunumu geçti. Frontend'in 12 testi, lint/typecheck/build ve localhost HTTP/health/WebSocket proxy smoke testi de başarılı. Security işi sonucu, P2-3'te açıklanan `|| true` sınırı nedeniyle temiz güvenlik raporu olarak yorumlanmıyor.

**Kanıt sınırı:** İlk CI yalnız boş PostgreSQL ve sahte/ağsız servisleri sınamıştı. Sonraki VPS kabulü gerçek Compose ağını, DB kopyalarını, mevcut PostgreSQL verisinin migration'ını, HTTPS/auth/WSS ve yenileme zincirini, ana smoke'ta API restart sonrası kayıt korunumunu ayrıca doğruladı. Gerçek Pine/alarm ve broker/testnet işlemleri açık. Servis health veya yetkisiz webhook reddi strateji/borsa gerçekleşmesi ya da gerçek TradingView alarm teslimi kanıtı değildir.

**P0-1 sırasında kaydedilen ve P1-2'de giderilen bulgu:** Geliştirme/CI Python 3.12'ye geçmişken Docker Python 3.10'daydı; `datetime.UTC` importları bu sürümde çalışmıyordu. Container Python 3.12.8 ve `pyproject.toml` destek beyanı birlikte düzeltildi; yalnız build değil, ağsız imaj importu da doğrulandı.

**Başlangıç sorunu:** Frontend Dockerfile standalone çıktı bekliyor fakat Next config bunu açmıyordu. Health proxy frontend localhost'una gidiyordu; middleware Compose'ta yoktu. Bu uyumsuzluklar ve deploy workflow'unun yanıltıcı adı giderildi.

**Dosyalar:** [docker-compose.yml](../docker-compose.yml), [frontend Dockerfile](../frontend/Dockerfile), [Next config](../frontend/next.config.ts), [ecosystem.config.js](../ecosystem.config.js), [start-api.sh](../start-api.sh), [deploy workflow](../.github/workflows/deploy.yml), [deploy rehberi](../scripts/DEPLOY.md), [middleware README](../middleware/README.md).

**Kabul kriterleri:**

- [x] Hedef topoloji, süreçler, portlar, DB ayrımı ve health yönlendirmeleri kaydedildi.
- [x] Frontend image/build ve gerçek Compose/VPS ağındaki API/health, HTTP/auth/WebSocket kontrolleri geçti.
- [x] Middleware restore/migration/health ile ana DB kopya geçişi doğrulandı; eski supervisor'lar devre dışı, geri dönüş kaynakları korundu.
- [x] IP HTTPS nginx kurulumu, dış TLS/auth/WSS, yetkisiz webhook reddi ve sertifika yenileme dry-run/timer/hook zinciri doğrulandı.
- [x] Dağıtım workflow'u gerçek davranışına uygun: açıkça manuel sunucu akışı, ayrı imaj yayınlama.
- [x] Yerel/CI, izole VPS smoke, üretim HTTPS deploy'u ve açık kalan Pine/testnet kabulü ayrı kaydedildi.

### P1-3 — Pine sözleşmesi ve testnet kabul akışı

**Güncel karar — 2026-09-10:** Kullanıcı borsa hesabıyla ilgili adımları sonraya bırakıp diğer görevlere devam edilmesini istedi. Aşağıdaki önceki “onay/yanıt bekleniyor” ve “P1-4 başlamayacak” kayıtları tarihsel kaldı. Gerçek alarm ve testnet emir kabulü **ertelendi**; hazırlanmış araçlar çalıştırılmayacak, kabul kutuları açık kalacak. Bu kararla geçilen P1-4 tamamlandı; sıradaki iş P1-5.

**2026-09-09 incelemesi:** `normalizeTicker()` `.P` sonekini silerek futures grafiğini Spot sembolüne çevirebiliyordu. `barTime=2**63` modelden geçip repository tarih dönüşümünde, sınırı aşan `barIndex` ise BIGINT saklamasında hata üretebiliyordu. Unicode harfler `.upper()` sonrasında ASCII'ye dönüşerek önceki sembol kontrolünü geçebiliyordu. Bunlar yerel uygulamada giderildi.

**Uygulama:** Pine yalnız `BINANCE`, `crypto`, base/quote birleşimine uyan ham ASCII ticker ve `chart.is_standard` koşullarında dispatch yapar; tek `alert()` çağrısı da aynı korumaya bağlıdır. `.P`/borsa/sonek silme kaldırıldı; tabloda uygunsuz grafik açıklanır. Backend ham sembolde ASCII kontrolünü büyük harf dönüşümünden önce yapar; separator/sonek reddedilir. `barTime` JSON integer `1..253402300799999`, `barIndex` JSON integer `0..2**63-1` ile sınırlandı. Boolean/float/sayısal metin ve taşmalar webhook/admin replay'de işleme başlamadan `422`; geçerli fakat eski/gelecek olaylar önceki gibi denetlenip `200/rejected` olarak kaydedilir. UTC dönüşümü epoch + integer timedelta ile milisaniyeyi korur.

**Uyumluluk kararı:** `schemaVersion=1`, hash algoritması, geçerli örnek payload/hash ve sinyal eşikleri değişmedi; migration yok. `barTime=timenow` olay üretim zamanıdır, bar açılışı değildir. Aynı normalize payload tek emir, aynı bar/kodda yeni olay zamanı veya farklı kod ayrı emir/tranche üretir. Fiyatın ondalık yazımı, metin ve timeframe alias farkları v1'de ayrı hash olabilir; retry aynı payload'u korumalıdır. Bu davranışı değiştirmek geçmiş idempotency kayıtlarıyla uyumlu sürüm tasarımı gerektirir. Kasıtlı BUY biriktirme korunur.

**Doğrulama:** 52 backend sınır/hash/freshness/retry testi + 22 Pine kaynak sözleşmesi testi; tam `.venv/Scripts/python.exe -m pytest -q` **403/403** (27,42 saniye), bir mevcut P2-3 tarih uyarısı. Yedi değişen Python dosyası Ruff lint/format ve diff kontrolünden geçti. Üç gerçek DB SHA-256 değeri başlangıçla aynı. Gerçek/testnet emir ve migration çalıştırılmadı.

**Commit ve Linux CI:** `ea2d0a579d997a0ca1e13e98f4a4ea358ae3e938` main'e push edildi. [CI 34375597532](https://github.com/Rapto0/Rapot/actions/runs/34375597532) beş job ile başarılı: Python **403/403** (26,28 saniye, aynı mevcut warning), lint/format, frontend lint/type/build/proxy, Docker ve güvenlik taraması. Docker job'u backend/frontend imajlarını, ağsız importları, boş geçici PostgreSQL'de altı migration ile middleware DRY_RUN health kontrolünü ve frontend container HTML/statik dosyalarını doğruladı. Bu migration yalnız CI test veritabanında çalıştı. Güvenlik taramasının hata toleranslı olması, mevcut action runtime ve gitlink temizleme uyarıları P2-3'te açık; yeşil job güvenlik borcunun kapandığını göstermez. CI koşumu anında VPS deploy'u yapılmamıştı; sonraki `8f60f8e` üretim geçişi ve HTTPS kabulü P1-2'de kayıtlı.

**İlk dış doğrulama sınırı (tarihsel):** Bağlı tarayıcıda oturum yoktu. TradingView misafir Pine editöründe geçici yalnız-grafik-koruması kontrolünün Add to chart adımı **Sign in** ekranı istedi; derleme başarısı alınmadı, sekme kapatıldı. Kaynak testleri Pine derleyicisi/tick yürütücüsü değildir. Bu aşamada alarm/hesap oluşturulmadı veya broker emri gönderilmedi. TradingView çalışan alarmlarının eski script kopyasını kullanabileceği README'de açıklandı.

**2026-09-09 kullanıcı derleme adımı:** Tarayıcıdan editör işlemi politika engeline takıldı. Kullanıcı **CE10244** bildirdi ve editördeki kaynağın kısa olduğunu, `plotshape` içermediğini doğruladı; eksik kopya tespit edildi. Git dışında `runtime-data/TradingView_TAM_KOD.txt`, orijinal Pine ile aynı SHA-256'ya sahip **1.089 satır / 6 plotshape** içeren tam kopya olarak hazırlanıp açıldı. Kullanıcı, **BINANCE:BTCUSDT / standart mum / 1D / Add to chart** kontrol sorusunu seçerek **“derlendi”** yanıtını verdi. Bu, kullanıcı tarafından bildirilen gerçek TradingView derleme başarısıdır; araçla alınmış derleyici çıktısı değildir. CE10244 için yeni kod değişikliği gerekmedi. Ardından kullanıcı futures ve Heikin Ashi kontrollerini **yapamadığını** belirtti; grafik korumalarının gerçek runtime sonucu, alarm JSON'u ve testnet emir kabulü hâlâ açık.

**2026-09-10 kullanıcı grafik kabulü:** Önceki yapılamayan kontroller tek tek tekrar soruldu. Kullanıcı `BINANCE:BTCUSDT.P` / 1D için **“Grafik Engelli yazıyor”**, `BINANCE:BTCUSDT` / Heikin Ashi / 1D için **“Evet, Grafik Engelli yazıyor”** bildirdi. Standart `BINANCE:BTCUSDT` / 1D'ye dönüp **Kripto 24/7** seçtiğinde `TF OK` ve `Alert Acik` sorusuna **“Evet, ikisi de görünüyor”** yanıtını verdi. Bunlar kullanıcı gözlemidir; tam uyarı metninin araçla okunması veya engellenmiş grafikten HTTP gönderilmediğinin ağ kanıtı değildir. ALL/FIRST ve saat filtresinin gerçek alarm davranışı ayrıca açık. P1-4 dış kabul işleri kapanmadan başlamayacak.

**2026-09-10 izole VPS HTTPS/simülasyon kabulü — doğrulandı:** Dağıtılmış `8f60f8e` backend digest'i ve PostgreSQL 16 ile ayrı ağ/DB/kapsam kullanıldı. Boş DB'de gerçek Alembic `0001 → 20260907_0006` çalıştı. Middleware `DRY_RUN`, trading/live kapalı, Binance anahtarları boş; örnek payload kaynağı **operatör/sentetik**, `isRealtime=false`. Geçici 443 rotasında **query-token** doğrulamasıyla yetkisiz `401`, geçersiz payload `422`, aynı bar/kodda farklı olay zamanıyla iki BUY ve iki FIFO SELL geçti: **4 simülasyon emri / 2 tranche / kalan miktar 0 / FIFO hedefleri 1 → 2**. Birebir tekrar hem restart öncesinde hem sonrasında aynı order'a döndü. Üretim middleware sayıları test öncesi/sonrası **135 / 135 / 28 / 383** ile aynı. Borsa emri çalıştırma yolu DRY_RUN ve boş kimlik bilgileriyle kapalıydı; fiyat/sembol bilgisi için public GET kullanıldı. Bu test gerçek TradingView teslimi veya hesap reconciliation kanıtı değildir.

**Simülasyon kanıtı ve temizlik:** Başarılı sonuç `/root/rapot-ops/20260910-p13-dry-r2/result.json` içinde `status=verified`; audit volume `rapot-p13-dry-20260910-r2-pgdata` korundu. Geçici HTTPS rotası, test middleware/PG konteynerleri ve ağı kaldırıldı. Son kontrolde test konteyneri yok, `nginx -t` başarılı, beş üretim konteyneri healthy, dış `/chart` ve middleware `/health` 200. İlk deneme `/root/rapot-ops/20260910-p13-dry` altında HTTPS yanıtını JSON okurken durdu; kabul edildi sayılmadı, kaynakları temizlenip kanıt/DB volume'u korundu. İkinci denemede nginx reload sonrası rota hazır olana kadar bekleme eklendi; gözlenen `404 → 401` geçişi sonuçta kayıtlı. Yerel operatör aracı `runtime-data/remote-p13-dry-acceptance.py` Git dışında; iki denemenin dizinleri birbirinin üzerine yazılmadı.

**Testnet aracı — hazır, emir çalıştırılmadı:** Git dışında `runtime-data/remote-p13-testnet-acceptance.py` hazırlandı; SHA-256 `8B0B707129F382AE274ABD2BDADE610D25664EE738A85E1E20DF97B7DCFD69B6`. Python 3.10 AST, Ruff lint/format, bağımsız kaynak incelemesi ve varsayılan `plan_only_not_executed` çalıştırması geçti. Varsayılan mod env/anahtar okumaz, ağ veya sunucu işlemi yapmaz; `--execute-testnet` çalıştırılmadı. Hazırlanan kapsam yalnız `https://testnet.binance.vision`, BTCUSDT, **25 sanal USDT × 2 BUY, ardından 2 FIFO SELL; en fazla 4 yeni emir**. Teste özel PostgreSQL 16 dizini/ağı/kapsamı, loopback `18103`, 51 sanal USDT serbest bakiye ön koşulu, başlangıç/aşama bazında açık emir ve bakiye kontrolleri var. Dolum/komisyon, BUY maliyeti, SELL PnL, restart/duplicate ve REPORT_ONLY reconciliation doğrulanacak. Partial/unknown/expired/eksik komisyon halinde sonraki emir durur; otomatik recovery, iptal veya ek temizlik emri yok; dust ve audit DB korunur. Kullanıcıya bu somut testnet kapsamı için ayrı onay soruldu; yanıt bekleniyor. Üretim DB/nginx/işlem bayrakları bu araçla değiştirilmez.

**Testnet erişim ön kontrolü:** VPS'den yalnız izin verilen `https://testnet.binance.vision` hedefine `GET /api/v3/time` ve imzalı `GET /api/v3/account` yapıldı; yönlendirme takibi kapalıydı. Mevcut middleware kimlik bilgileriyle hesap okundu: `accountType=SPOT`, `canTrade=true`, USDT bakiye alanı mevcut. Bu, bakiye tutarının yeterli olduğunu veya hesabın başka işlerce kullanılmadığını kanıtlamaz. Emir isteği **0**; üretim ayarları/DB değiştirilmedi. Anahtarlar, imza ve bakiye tutarları log/belgeye yazılmadı. Sonuç `/root/rapot-ops/20260909-8f60f8e/testnet-readiness.json` içinde. Resmi sözleşme: [Binance Spot Testnet REST API](https://developers.binance.com/en/docs/products/spot/testnet/rest-api). Hazırlanan kapsamın kullanıcı onayı, ayrı test DB'sinin kurulması ve emir kabulünün çalıştırılması bekleniyor.

**Gerçek alarm alıcısı — hazır, dışa açılmadı:** Git dışında `runtime-data/p13-tradingview-capture.py`, yalnız `TradingViewWebhookPayload` doğrulayıp kayıt tutar; DB/broker/işlem servisi kullanmaz. Ayrı test tokenı, en fazla 24 saatlik bitiş, TradingView kaynak IP listesi, loopback proxy, 8 KB gövde/2 saniye okuma ve 20 kayıt sınırı var. Üretim tokenı/ortamı kullanılmaz. Canonical payload, alınma zamanı, kaynak IP ve hash özel dosyaya atomik yazılır; bu hash üretim idempotency kimliği değildir. Python AST/Ruff ve bağımsız inceleme geçti. Sabit backend imajında `--network=none`, salt okunur root ve yalnız geçici `/capture-data` ile sentetik ASGI kontrolü **exit 0**: auth/IP, scope, gerçek JSON boolean, gövde/tekrarlı JSON alanı, özel dosya izinleri, dedup, 20 kayıt sınırı, expiry ve eksik ayarda kapalı davranış geçti. Konteyner çıkışta kaldırıldı; dinleyen HTTP portu veya nginx rotası açılmadı. Kullanıcının Webhook URL alanına erişim yanıtından sonra ayrı geçici HTTPS rotası kurulacak; gerçek teslim TradingView alarm günlüğüyle eşleştirilecek. Resmi teslim koşulları: [TradingView webhook belgesi](https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/).

**Önceki belge yayını:** P1-2 kapanışını kaydeden `7473975` commit'i main'e gönderildi, aynı dosya hash'iyle sunucu ops dizinine kopyalandı. [CI 34389057669](https://github.com/Rapto0/Rapot/actions/runs/34389057669) başarılı tamamlandı. Uygulama imajları `8f60f8e` kaynak sürümünde kaldı.

**Alarm kabulünde veri sınırı:** `DRY_RUN` ve `MW_TRADING_ENABLED=false`, simülasyon kayıtlarını engellemez; geçerli ve riskten geçen alarm simülasyon emri/tranche oluşturabilir. Gerçek Binance emir POST'u yapılmaz. Bu yüzden tekrar/FIFO kabulü ayrı DB/kapsamda yürütülmeli; production'a deneme alarmı gönderilmesi salt okunur kontrol olarak sunulmamalı.

**HTTPS alarm adresi:** Mevcut tokenlı HTTP TradingView webhook URL'leri, token korunarak doğrudan `https://138.68.71.27/webhooks/tradingview` adresine güncellenmeli; token değeri bu belgeye yazılmamalı. Sunucu 308 yönlendirme yapıyor, fakat TradingView'ın yönlendirmeyi takip ettiği doğrulanmadı. Yetkisiz HTTPS isteğinin 401 dönmesi P1-2 kanıtıdır; gerçek alarmın doğru auth/payload ile teslimi ve idempotency kabulü bu maddede açık.

**Neden:** Son Pine commit'i büyük; başlangıçta derleme/alarm testi doğrulanmamıştı. Derleme artık kullanıcı bildirimiyle kayıtlı, alarm/runtime kabulü açık. Varsayılan Manuel/günlük/saat filtresi ile Kripto 24/7 preset'i farklı. barTime=timenow ve tüm payload hash'i, aynı bar/sinyalin tekrar semantiğini etkiliyor.

**Dosyalar:** [Pine](../middleware/pine/combo_hunter_binance.pine), [Pine README](../middleware/pine/README.md), [payload modeli](../middleware/domain/events.py), [signal repository](../middleware/repositories/signal_repository.py), [middleware README](../middleware/README.md), [webhook testleri](../middleware/tests/test_webhook_validation.py).

**Kabul kriterleri:**

- [x] Spot sembolü, sinyal kodu/yönü, timeframe ve v1 olay zamanı sözleşmesi açık; ayrı bar açılış alanı olmadığının sınırı belgeli.
- [x] Birebir HTTP tekrarının korunması ile aynı bar/sinyalin yeniden üretilmesi ayrıldı; eski hash ve kasıtlı tekrarlı BUY davranışı test edildi.
- [ ] Manuel/Kripto 24/7, saat dilimi ve ALL/FIRST kaynak sözleşmesi test edildi; gerçek Pine runtime/alarm doğrulaması bekliyor.
- [x] Tam Pine kaynağı için BINANCE:BTCUSDT / standart mum / 1D derlemesi kullanıcı tarafından bildirildi; araç çıktısı veya çalışan backtest kanıtı olarak sunulmadı.
- [x] Futures ve Heikin Ashi için `Grafik Engelli`; standart BTCUSDT/1D/Kripto 24/7 için `TF OK` ve `Alert Acik` kullanıcı tarafından bildirildi.
- [x] Ayrı VPS PostgreSQL/kapsamında sentetik HTTPS/query-token, iki BUY → FIFO SELL ve restart sonrası birebir tekrar kabulü tamamlandı; üretim kayıtları korundu.
- [ ] Gerçek alarm JSON'u, HTTPS teslimi ve tekrar davranışı doğrulandı.
- [ ] İlgili izin verildiğinde yalnız ayrılmış testnet hesabı/DB ile BUY → FIFO SELL → reconcile kabul akışı kaydedildi; tokenlar kayda alınmadı.
- [x] Yerel test sonucu testnet/gerçek hesap doğrulaması veya otomatik canlıya geçiş olarak işaretlenmedi.

### P1-4 — AI ilişkileri ve scan history

**2026-09-10 — Doğrulandı:** Kullanıcı P1-3 dış kabulünü erteleyerek bu işe geçilmesini istedi. `fce5d01` commit/push, Linux CI, imaj yayını ve üretim geçişi tamamlandı; aşağıdaki eski ön inceleme uygulama öncesi kayıttır.

**Sinyal–AI ilişkisi:** `_save_signal_and_publish` başarılı eklemenin ID'sini strateji/yön/timeframe anahtarıyla aynı turda saklıyor. `mark_special_signal` ve AI çağrısı tam hedef ID'yi, AI ayrıca `market_type` bilgisini kullanıyor. ID yok/0 veya ekleme hatası varsa eski eşleşen satır etiketlenmiyor/analize bağlanmıyor. Repository'nin eski latest-match çağrıları korunurken scanner ID + tüm kimlik alanlarıyla filtreliyor. AI kapalı/hatalı, haber/rapor/Telegram hatalı olduğunda kaydedilmiş sinyaller korunuyor; sonraki özel analiz denenebiliyor.

**Tarama kaydı sözleşmesi:** Yeni `application/scanner/scan_history.py` her kabul edilmiş çağrıda ContextVar ile ayrı sayaç tutar ve terminal durumda bir history INSERT dener. `status`: normal `success`; veri yok/bayat, boş sembol listesi, sembol/TF hatasıyla devam edilmişse `partial`; turu durduran hata `failed`; kooperatif iptal/KeyboardInterrupt/SystemExit `cancelled`. Sync fatal hata/iptal çağırana yayılır; async fatal hata mevcut sözleşmedeki failed yanıtını verir, iptal yayılır ve `is_scanning` sıfırlanır. Async reentry yeni tarama/history açmaz; sync çağrıları ayrı kabul edilmiş çağrılardır. Süre monotonic saatle ölçülür; duvar saati değişimi sonucu bozmaz.

**Sayaç sınırı:** `signals_found`, kalıcı eklemede dönen pozitif ID sayısıdır; repository'nin 0/None sonucunu saymaz. Bu, ana sinyal tablosuna yeni dedup kuralı getirmez; her yeni ekleme sayılır. Sayım ortak handler'da save dönüşünün hemen ardından, payload/publish/global-stat adımlarından önce yapılır; o aşamalarda iptal olsa da önceki INSERT sayılır. Eski global sayaçlar yeniden hesaplanmadı; bundan sonraki artışlar yalnız yeni kayıtlardır. `symbols_scanned` taramaya alınan hedef sayısıdır: sync veri çekimine girilen, async batch sağlayıcıya verilen semboller; eksik/hatalı veri hedefleri dahildir. `errors_count` veri/sembol/TF hata olaylarıdır; bir sembolde birden çok TF hatası sayılabilir. AI/bildirim eksikliği çekirdek sinyal taramasını failed yapmaz. Komut callback'inden çalışan manuel analizler taramanın sayacına eklenmez.

**Şema/okuma/UI:** `ScanHistory.status` eklendi. `db_session.init_db` legacy SQLite tablolarında eksik `mode`, `errors_count`, `status` kolonlarını idempotent tamamlıyor; eski durum `unknown`, eksik hata sayısı `NULL` kalıyor. Veri/durum geçmişi uydurulmadı. `/scans`, overview ve activity projection yeni kayıtları okuyor. `/health` ve `/scanner` sonucu/hata sayısını gösteriyor; bilinmeyen/başarısız/iptal taramayı yeşil başarı olarak göstermiyor. Async `notify=False` başlangıç/sonuç/hata mesajlarına da uygulanıyor; bildirim hatası history kaydını değiştirmiyor.

**Doğrulama:** Hedefli **92/92**, tam `.venv/Scripts/python.exe -X utf8 -B -m pytest -q` **471/471** (29,83 saniye), mevcut UTC uyarıları **193**. Yeni testler: 23 AI/etiket kimliği ve API ilişkisi; 25 writer/legacy-first migration/read-model; 20 tarama lifecycle/sayaç/iptal testi. 14 değişen/yeni Python dosyası Ruff lint/format, diff kontrolü temiz. Frontend Node 20.20.2/npm 10.9.9 ile **15/15**, ESLint/typecheck/production build geçti; üç yeni test gerçek health bileşenini SSR ile sınadı. Gerçek AI, Telegram mesajı veya borsa emri gönderilmedi; testler geçici DB ve sahte sağlayıcılarla çalıştı.

**Commit / CI / üretim:** `fce5d011ddaf6444be30735dc2a26129ade6c62e` — `fix(scanner): link AI analyses and record scan outcomes`. [CI 34510880779](https://github.com/Rapto0/Rapot/actions/runs/34510880779) ve [imaj yayını 34510920665](https://github.com/Rapto0/Rapot/actions/runs/34510920665) başarılı. Backend digest `sha256:505bdd4172165f698ce6790032e36e16e8b59488f07506128f17058436733e2b`; frontend digest `sha256:8b0f7dab232e781650cd9cb4d4dc815fd9b0156bc895fcfeee0f61b343beebba`. OCI revision ve çalışan imaj ID'leri bu commit ile eşleşti. `/opt/rapot/current` yeni release'e bağlı; PostgreSQL imajı ve şeması değişmedi.

**Veri / geçiş kanıtı:** `/root/rapot-ops/20260910-fce5d01/` altında kaynak, root erişimli config yedekleri, `preparation.json`, `deployment.json` ve `post-deploy-check.json` kayıtları var. Tutarlı SQLite online backup quick_check'ten geçti; 190.509.245 bayt gzip kopyası açılarak SHA-256 doğrulandı (ham DB: `d012dd3b0b3b1bac11b4fd7903d6a0d414d5d9db6d77acf43f117f3d45d9a674`). API/bot durdurularak migration uygulandı; önce/sonra **1.726.925 sinyal, 26.393 AI analizi, 4 bot_stats; trade/order/scan_history=0** aynı kaldı. `mode/errors_count/status` kolonları ve SQLite quick_check geçti. Middleware sayıları **135/135/28/383** değişmedi; `main.env` ve `middleware.env` yedekle birebir aynı.

**Üretim kabulü / sınırı:** 10 Eylül **18:11:57 UTC / 21:11:57 İstanbul** itibarıyla beş servis healthy, restart=0, OOM yok. `/health`, `/scanner`, `/chart`, `/api/health`, `/api/scans` ve overview HTTPS okumaları geçti; ayrıca bu bilgisayardan scanner HTML/JavaScript varlığı 200 ve API healthy/database connected doğrulandı. Middleware **DRY_RUN / trading=false / live=false** kaldı. Üretimde henüz yeni tamamlanan tarama olmadığı için `/scans` boş döndü; yazma/sonuç gösterimi izole davranış testleriyle doğrulandı, üretime test sinyali/tarama/emir eklenmedi. AI sunucuda kapalı kaldı; bu yayın gerçek Gemini kabulü değildir. İlk deploy ön kontrolünde `release.env` içinde opsiyonel `RAPOT_RELEASE` olmadığından işlem servisleri değiştirmeden durdu; araç mevcut anahtarları koruyarak bu satırı ekleyecek şekilde düzeltildi. İzole dosyalarda config/symlink değiştirme hatası, yeniden deneme ve log/durum yazım hatası sınandı; üretimde rollback gerekmedi. Eski release/config ve veri yedeği korunuyor.

**Sınırlar:** `finally` SIGKILL/güç kesilmesinde çalışamaz; bu bir kalıcı job kuyruğu değildir. History yazıcısının normal hatası loglanır, asıl hatayı ezmez veya eski sinyalleri geri almaz; async `history_id=None` olarak görünür. Tamamlanmamış history yazımı başarılı kabul edilmez. Senkron/async AI/özel etiket eşdeğerliği ve süreçler arası realtime P1-5'te; burada async strateji hesapları değiştirilmedi.

**Neden:** Scanner AI çağrısı market_type/signal_id göndermiyor; varsayılan BIST/None. Scan history okuyucusu var, aktif scanner yazma bağlantısı bulunamadı.

**Dosyalar:** [market_scanner.py](../market_scanner.py), [async_scanner.py](../async_scanner.py), [ai_analyst.py](../ai_analyst.py), [system repository](../infrastructure/repositories/system_repository.py), [ops repository](../infrastructure/persistence/ops_repository.py), [modeller](../models.py).

**2026-09-09 ön incelemesi — uygulama başlamadı:** `market_scanner.py::process_symbol` içindeki dört `_save_signal_and_publish()` çağrısının döndürdüğü kimlik kullanılmıyor; `trigger_ai_analysis()` → `analyze_with_gemini()` zincirine `market_type` ve `signal_id` aktarılmıyor. Gerçek yazıcı `infrastructure/persistence/signal_repository.py::save_signal`, başarılı eklemede ID, uniqueness çatışmasında `0` döndürüyor; `application/scanner/signal_handlers.py` bu değeri koruyor. `mark_special_signal()` son eşleşen satırı güncellediğinden, başarısız yeni kayıt sonrasında eski sinyali etiketlememek/analize bağlamamak için aynı turdaki başarılı kayıt ID'si kullanılmalı. Kök repository dosyaları wrapper; değişiklik gerçek uygulama dosyalarında yapılmalı.

**Ön incelemede önerilen uygulama (tarihsel):** Önce `process_symbol` içinde strateji/yön/timeframe bazında başarılı ID'leri tutup özel sinyalin hedef timeframe ID'sini ve piyasa türünü AI'a geçir. Ardından `infrastructure/persistence/ops_repository.py` üzerinden sync/async kabul edilmiş tarama çağrısı başına tek terminal history kaydı tasarla; `finally` içinde monotonic süre, sayaçlar ve hata/iptal durumu ele alınmalı. Async "zaten çalışıyor" dönüşü yeni tarama sayılmamalı. İnceleme anında `ScanHistory` modelinde açık başarı alanı yoktu; yukarıdaki uygulama `status` alanını ve sayım politikasını ekledi. Async AI eşdeğerliği P1-5 kapsamında kalıyor.

**Hedef doğrulama:** BIST/Kripto doğru AI ilişkisi ve `/signals/{id}/analysis`; insert=`0` iken eski satıra bağlanmama; AI kapalı/hatalı iken sinyalin korunması; sync/async başarı, sembol hatası, fatal hata, iptal ve reentry durumlarında tek history kaydı; `/scans` ve overview görünürlüğü. Mevcut scanner mock'larının çoğu ID yerine `None` döndürüyor; testler gerçek ID sözleşmesini kapsamalı. Ön incelemede DB açılmadı ve dış AI/veri çağrısı yapılmadı.

**Kabul kriterleri:**

- [x] Kripto/BIST analizi doğru piyasa ve uygun sinyal kimliğiyle saklanıyor; sinyalden analize erişim doğrulandı.
- [x] AI_ENABLED=0 davranışı ve AI başarısızlığında taramanın davranışı korunuyor.
- [x] Tamamlanan/başarısız taramanın geçmiş kaydı politikası belirli; sayım/süre/kayıt tekrarları test edildi.
- [x] /scans ve ilgili read-model'ler yeni tarama kaydını sunuyor; eski boş yerel tablo üretim geçmişi olarak yorumlanmıyor.

### P1-5 — Süreçler arası realtime ve scanner eşdeğerliği

**Neden:** Signal dispatcher süreç içi callback; ayrı bot/API süreçleri arasında taşıma yok. Async akış special_tag=None kullanıyor ve sync özellikleriyle aynı değil.

**Dosyalar:** [signal_dispatcher.py](../signal_dispatcher.py), [realtime bootstrap](../api/runtime/realtime_bootstrap.py), [api/realtime.py](../api/realtime.py), [signal handlers](../application/scanner/signal_handlers.py), [market_scanner.py](../market_scanner.py), [async_scanner.py](../async_scanner.py), [frontend realtime](../frontend/src/lib/realtime).

**2026-09-10 ön incelemesi (tarihsel):** API ve bot ayrı süreçlerde aynı SQLite'ı kullanıyor; callback kaydı bot sürecine taşınmıyor. Sinyal socket'i frontend'de ticker açılışına bağlı; reconnect REST sorgularını yenilemiyor. Store aynı ID'yi tekrar ekleyebiliyor, eski realtime satırı sonradan REST'ten gelen özel etiketi gölgeleyebiliyor. Kline/trade callback'leri bootstrap'te bağlı değil. Async hesaplayıcılar ortak olsa da özel etiket/AI/ikinci kaynak ve sync BIST 90 saniye tazelik kapısı eşdeğer değil.

**Uygulanan sinyal yolu:** Ayrı bot süreci SQLite'a commit eder → API `SignalFeed` bir saniyede bir, en fazla 100 yeni satırı `id > cursor ORDER BY id` ile okur → API WebSocket/SSE yayını → provider altındaki tek `RealtimeBridge` → ID ile güncellenen store ve REST görünümü. Başlangıç MAX değeri socket kabulünden önce alınır; thread içindeki salt DB okuması await'ler arasında session tutmaz. Cursor yayımlanan son satırdan ilerler; DB/yayın hatasında kayıt DB'de kalır, sonraki poll yeniden dener. Süreç içi publisher kapalıdır, aynı kayda ikinci yayın üretilmez. `/realtime/status` feed running/ready/cursor ve güvenli hata türünü, piyasa sağlayıcı durumlarından ayrı gösterir.

**İstemci ve bağlantılar:** Ticker/sinyal bağlantıları bağımsız açılır ve yeniden bağlanır; constructor hatası dahil tekrar deneme üst sınırı 30 saniyedir. Kapanmış bağlantının gecikmiş callback'i yeniden bağlantı başlatamaz. Açılış/reconnect/reset geçici sinyalleri temizleyip REST'i hemen yeniler. Normal yoğun sinyal akışı REST yenilemesini 30 saniyelik pencerede bir kez tetikler; mevcut 45 saniyelik REST polling korunur. Aynı ID için REST satırı önceliklidir; geç özel etiket/AI verisi eski realtime satırının arkasında kalmaz. Yavaş WS istemcisi iki saniye sonunda ayrılır; SSE taşması resync işareti üretir. Kline/trade callback'leri bağlıdır; kendi URL'leri, normalize sembol/interval, referans sayılı abonelik ve cleanup kullanılır. Binance kontrol mesajları 0,35 saniye arayla gönderilir, 1.024 stream sınırı uygulanır; sunucu reddi loglanır ve yeniden bağlanılır.

**Tarayıcı eşdeğerliği:** `market_scanner.finalize_symbol_signals` sync/async için aynı kesin ID, özel etiket, ikinci kaynak, haber ve AI yolunu çalıştırır. `notify=False` yalnız Telegram/mesaj biçimlendirmesini susturur. Async BIST 30, kripto 50 sembollük grupları alıp işler; BIST verisi hem gelişte hem sembolün ilk yazımından hemen önce tazelik kapısından geçer. Önceki sembolün AI süresinde yaşlanan veri kaydedilmez, tarama partial olur; yeni batch işlenebilir. İptal checkpoint'leri commit sayısını/history'yi korur; arka planda bırakılmış yazıcı yoktur. RSS HTTP isteği ve yfinance çağrısı açık 10 saniyelik timeout kullanır; bu, toplam çoklu sağlayıcı/AI evresinin kesin süre sınırı değildir. Paylaşılan senkron finalizasyon async event loop'u çağrı bitene kadar meşgul edebilir; worker/kuyruk dönüşümü bu değişikliğin kapsamı değildir.

**Taşıma sınırları:** Bu bir kalıcı outbox/teslim alındı sistemi değildir. API kapalıyken kaçanlar açılıştaki REST görünümünden toparlanır; sorgu limitleri bütün tarihsel olayların teslimini garanti etmez. `id` taraması sonraki tag/AI güncellemelerini yayınlamaz; REST bu yüzden korunur. Üretim tablosu `INTEGER PRIMARY KEY`, `AUTOINCREMENT` içermiyor: en yüksek satır silinirse ID yeniden kullanılabilir. MAX cursor'un altına düşerse `signal_feed_reset` gönderilir, eski satırlar yeni olay olarak tekrarlanmaz. Aynı/yüksek MAX ile DB değiştirme veya aradaki silme-yeniden ekleme otomatik anlaşılmaz; REST ve kontrollü API restart gerekir. [SQLite transaction izolasyonu](https://www.sqlite.org/isolation.html) ve [ROWID tekrar kullanım sınırı](https://www.sqlite.org/autoinc.html) başka veritabanları için genellenmez.

**Doğrulama:** Yeni subprocess kabulü `scripts/smoke_signal_feed.py`, geçici DB'de gerçek repository kullanan ayrı yazıcıdan gerçek ASGI WebSocket rotasına beş sıralı olay, rollback'in görünmemesi, feed yeniden başlatma sonrası iki satırın REST read model'de bulunması ve bir yeni canlı olay doğrular. Üretim DB'sine test satırı eklemez. CI Docker adımı aynı aracı `--network none` ile çalıştırdı ve geçti; tam tarayıcı/ağ testi diye sunulmaz. Frontend **23/23**, lint/typecheck/build geçti. Scanner testleri gerçek COMBO/HUNTER hesaplarıyla aynı OHLCV üzerinde BIST/Kripto AL/SAT, dört özel etiket, AI satır bağlantısı, ikinci kaynak/hata/notify/iptal ve yaşlanan batch davranışını karşılaştırır. Son tam Python paketi **542/542 — 52,35 saniye**, 862 mevcut UTC deprecation warning; değişen 21 Python dosyası Ruff lint/format ve diff kontrolünden geçti. Bağımsız inceleme yeni bir yayın engeli bulmadı.

**Commit / CI / üretim:** `a513af9c60e1be1df646bf7acf841e8a9f4c3d89` — `fix(realtime): bridge committed signals and align scanner pipelines`. [CI 34516407676](https://github.com/Rapto0/Rapot/actions/runs/34516407676) ve [imaj yayını 34516429765](https://github.com/Rapto0/Rapot/actions/runs/34516429765) başarılı. CI ağsız Docker subprocess kabulü, boş PostgreSQL migration/middleware health ve frontend container HTML/JS kontrolünü de geçti. Backend digest `sha256:4bc2d474ad21dd85491b736232dc52f078ddd147eb66ad3b91a30feda5e7dae2`; frontend digest `sha256:f5877852cca61896fe448352e4303c967295b7669927ea776c263193a3401111`. Çalışan imaj ID/OCI revision ve `/opt/rapot/current` kaynağı eşleşti; PostgreSQL değişmedi.

**Veri / geçiş:** `/root/rapot-ops/20260910-p15` içinde root-only config yedekleri ve 186.493.190 bayt sıkıştırılmış tutarlı SQLite yedeği var. Açılmış arşiv tek başına salt okunur/immutable SQLite ile quick_check ve tablo sayılarından geçti; ham SHA256 `0a502ac8819b2f61764172f178fba05b794f0374dee5e1d1bb44ae1c0e762af4`. API/bot durdurularak idempotent main-init ve quick_check doğrulandı; yeni şema değişikliği yok. Önce/sonra **1.726.925 sinyal, 26.393 AI, 4 bot_stats; trade/order/scan_history=0** aynı kaldı. Middleware **135/135/28/383**, `main.env`/`middleware.env` ve **DRY_RUN/false/false** korundu. `deployment.json` verified; rollback gerekmedi. Son kontrolde beş servis healthy/restart=0, feed running/ready, cursor=1.739.961, hata yok; Binance bağlı ve BIST servisi çalışıyor.

**Dış kabul / sınırı:** TLS doğrulaması açık HTTPS health/status ve WSS `/signals` heartbeat, `/kline/btcusdt?interval=1m`, `/trades/btcusdt` geçti. Mum/işlem payload'ları sembol, interval, tip ve sayısal alanlarla kontrol edildi; sinyal heartbeat'i 30,219 saniye, toplam kabul 31,187 saniye sürdü. Kapanışta kanal sayaçları sıfıra döndü. Tarayıcıda `/signals` 300 kayıt ve BELEŞ/ÇOK UCUZ/PAHALI etiketlerini gösterdi. Bu, üretimde yeni sinyal/AI/tarama/emir ekleme kabulü değildir; INSERT yolu izole süreç testindedir. İlk koşumda root→signals ekranı yüklenirken tüm WSS handshake'leri yaklaşık 7,5 saniyede zaman aşımına uğradı; ekran kapatıldıktan sonraki koşum geçti. İlk sonuç saklandı, neden kesinleştirilmedi ve eşzamanlı yük altında gecikme giderilmiş sayılmadı. Her iki JSON ve `post-deploy-check.json` aynı ops dizininde; performans takibi P2-4'te.

**Kabul kriterleri:**

- [x] Seçilen ayrı süreç topolojisinde yeni kayıt sinyal kanalına ulaşıyor; taşıma hatası DB kaydını kaybettirmiyor (izole ASGI ve frontend davranış testleri).
- [x] Reconnect/feed yeniden başlatma ve yinelenen olay davranışı test edildi; frontend yenileme/fallback davranışı açık.
- [x] Kline/trade callback'leri izole testlerde, BTCUSDT kanalları üretim WSS üzerinden doğrulandı; kapanış sayaçları sıfırlandı.
- [x] Sync/async özel etiket, AI, ek kaynak doğrulaması ve notify kapsamı karşılaştırıldı; eşitlenen veya bilinçli farklı kalan davranışlar belgeli.

### P1-6 — PnL, bot durumu ve ayarlar ekranı

**Neden:** currentPrice giriş fiyatına eşitleniyor; PnL yüzdesi miktarı içermiyor. Bot durumu yokken isRunning=true varsayılıyor. Ayarlar yalnız localStorage'a, secret alanlarıyla birlikte yazılıyor.

**2026-09-10 uygulama kapsamı:** Gerçek bot eşiği/anahtar yönetimi eklenmedi. Etkisiz ayarlar formu ve kullanılmayan Settings store kaldırıldı; sayfa sunucudan yönetilen ayarları açıklıyor, çalışan tarayıcı tercihleri için `/scanner` ekranına bağlantı veriyor. Her sayfanın başlangıcında yalnız `rapot.settings.v1` ve `rapot-settings` kayıtları temizleniyor: dört sayısal tercih ve bildirim boolean'ı etkisiz geçmiş olarak kalabilir; bağlantı kimlikleri, secret ve diğer alanlar kaldırılır. Bozuk kayıt yalnız kendi anahtarından silinir; başka localStorage kayıtları okunmaz/temizlenmez. Depolama erişim hatası tamamlanmış sayılmaz, hassas içerik loga veya ağa aktarılmaz.

**PnL sözleşmesi:** Yalnız CLOSED satırın kayıtlı gerçekleşmiş PnL'si kullanılır; yüzde `pnl / (entryPrice × quantity) × 100`. OPEN, CANCELLED, bilinmeyen durum ve eksik/sonsuz/sıfır payda için ölçülmemiş değerler `null` / `—`. API güncel fiyat taşımadığı için giriş fiyatından türetilmez. Geçersiz tarih şu anın tarihiyle doldurulmaz. `/stats.closed_trades` gerçek CLOSED sayısını taşır; `total - open` hesabı iptal edilmiş işlemleri kapalı saymaz. Overview sağlamadığı kazanma oranı/kapalı işlem sayısını uydurmaz. Ana DB'nin BIST/Kripto PnL toplamında kur dönüşümü yoktur; ortak toplama tek para birimi simgesi eklenmez. Canlı değerleme, FX dönüşümü ve middleware portföy entegrasyonu bu işte eklenmez.

**Bot durumu kapsamı:** Eski `runtime_is_running` kaydının güncelliği kanıtlanamıyor; gerçek yazar bulunmadı. Aynı süreçteki scheduler lifecycle ve thread sahipliği kullanılıyor; standalone health veya yalnız eski kayıt çalışan bot kanıtı sayılmıyor. Veritabanı, HTTP, yüklenme ve eskimiş istemci verisi ayrı ele alınır. Süresi dolmamış eski tarama kilidi tek başına canlı tarama kanıtı değildir. Son tarama zamanı ile herhangi bir sayaç güncelleme zamanı birbirine eşitlenmez. Docker `/health` veritabanı bağlantısı temelli 200/503 anlamını korur.

**Dosyalar:**

- Frontend: [normalizers](../frontend/src/lib/api/normalizers.ts), [ölçüm gösterimi](../frontend/src/lib/metric-display.ts), [trade hook](../frontend/src/lib/hooks/use-trades.ts), [bot durum sözleşmesi](../frontend/src/lib/health-status.ts), [health hook](../frontend/src/lib/hooks/use-health.ts), [ayarlar sayfası](../frontend/src/app/settings/page.tsx), [eski tarayıcı tercihlerini temizleme](../frontend/src/lib/browser-preferences.ts), [uygulama başlangıcı](../frontend/src/components/providers.tsx).
- Backend: [API](../api/main.py), [trade servisi](../application/services/signal_trade_service.py), [DB sağlık probe'u](../db_session.py), [health API](../health_api.py), [scheduler](../scheduler.py), [manuel komutlar](../command_handler.py).
- Testler: [trade API sözleşmesi](../tests/test_trade_stats_contract.py), [bot durum doğruluğu](../tests/test_bot_status_truth.py), [API sağlık hazırlığı](../tests/test_api_health_readiness.py), [trade gösterimi](../frontend/tests/trade-metrics.test.mjs), [health gösterimi](../frontend/tests/health-status.test.mjs), [tarayıcı temizliği](../frontend/tests/browser-preferences.test.mjs).

**2026-09-10 salt okunur başlangıç kanıtı:** `transformTrade` yüzdeyi `pnl / entryPrice` ile hesaplıyor; modelin PnL'si miktarı zaten içerdiğinden giriş 100, miktar 5, PnL 50 örneği %10 yerine %50 gösteriyor. API güncel fiyat taşımadığı halde `currentPrice` girişe eşitleniyor. `useBotHealth` eksik veride `isRunning=true` kullanıyor; backend `health_api.py` de eksik runtime bilgisini çalışıyor sayabiliyor. Ayarlar yalnız `rapot.settings.v1` localStorage anahtarına yazılıyor; backend çağrısı yok. Kullanılmayan `frontend/src/lib/stores/index.ts::useSettingsStore` içinde ikinci `rapot-settings` saklama yolu var; ikisi de secret alanlarını içerebiliyor. İlk dar uygulama: secret alanlarını ve iki bilinen eski anahtardaki secret saklamasını kaldırmak, ekranın yalnız gerçekten çalışan tarayıcı tercihlerini sunduğunu açıklaştırmak; ardından PnL/bilinmeyen fiyat ve bot durum sözleşmesi. Gerçek bot eşiği yönetimi yetkili backend ve hesaplayıcı bağlantısı gerektirir. Bu ön incelemede kod değişmedi.

**Ek API/UI düzeltmeleri:** Şemada mümkün olan legacy `pnl=NULL`, `/trades` response modelinde de kabul edilir; artık 500 üretmez. OpenAPI snapshot güncellendi. Kullanılmayan PortfolioPanel içindeki yalnız `console.log` yapan AL/SAT/kapat yolları ve sahte Paper/Real seçimi kaldırıldı; düğmeler devre dışı, işlem gönderiminin bağlı olmadığı açık. Yeni borsa emri yolu eklenmedi.

**Doğrulama:** `.venv` / Python 3.12.8 tam pytest **578/578**, mevcut UTC kullanımlarından 874 warning. Node 20.20.2 / npm 10.9.9 altında **52/52 frontend**, ESLint, incremental kapalı typecheck ve production build geçti. Yeni backend testleri gerçek izole DB ile closed/open/cancelled/legacy sayımını ve nullable PnL HTTP sözleşmesini; health testleri lifecycle/owner thread, sync/async/manual giriş, nested scan/failure cleanup, eski lease/bayrak, eksik/bozuk/sıfır sayaç ve ScanHistory zamanını kapsıyor. Frontend testleri normalizer ve gerçek sayfa/bileşen SSR çıktısını, eski cache/hata/yüklenme durumunu, iki formatta secret temizliğini ve disabled/onClick'siz işlem düğmelerini sınadı. Başka tarayıcı depolaması, gerçek emir, Telegram veya AI test çağrısı kullanılmadı. Değişen yedi Python dosyasında Ruff lint/format temiz.

**Kanıt sınırı:** Thread canlılığı görevlerin ilerlediğine dair heartbeat değildir; uptime süreç/import süresidir. İstemci 30 saniyede bir yeniler ve yenileme sırasında yükleniyor gösterebilir. Bot health, kendi süreç taramalarını gözlemler; ayrı API sürecinden başlatılmış işlerin küresel tarama durumu değildir. Dört kalıcı sayaçtan biri eksikse toplam sayaç grubu bilinmiyor kalır; son ScanHistory zamanı bundan bağımsızdır. Storage cleanup erişilebilen mevcut tarayıcı/origin'de yeni sürüm açıldığında çalışır; başka cihazlar, kapalı tarayıcılar ve eski HTTP origin'i temizlenmiş sayılmaz. PnL yüzdesi giriş tutarına göre gerçekleşmiş değerdir; canlı portföy getirisi/komisyonlu muhasebe/kur dönüşümü sağlamaz.

**İlk yayın denemesi:** `f61e1697a773572aed955319130907ac46f6414b` main'e gönderildi; [CI34520120793](https://github.com/Rapto0/Rapot/actions/runs/34520120793) ve [imaj34520142341](https://github.com/Rapto0/Rapot/actions/runs/34520142341) başarılı. `/root/rapot-ops/20260910-p16` altında config ve bağımsız açılarak doğrulanmış SQLite gzip (230.224.427 bayt) var. Init tablo sayıları korundu; `/api/scans`, `/api/ops/read-model/overview`, `/health`, `/scanner`, `/chart` 200 döndü. `/api/health` 20 saniyede yanıt vermedi; nginx499 kaydı ve operatör traceback'i eşleşti. Operatör a513af9 kaynak/config/imajlarına döndü, beş servis tekrar sağlıklı; veritabanı yedekle ezilmedi, middleware135/135/28/383 ve DRY_RUN/false/false korundu. Bu deneme başarılı deploy sayılmıyor. Ana tablo sayıları aynı olsa da son ham DB hash'i önceki yedekten farklı; veri byte-byte değişmedi denmiyor. Yeniden denemeden önce yeni snapshot alınacak.

**Ek düzeltme / yeniden doğrulama:** P2-4'ün yalnız health yoluna ait dar kısmı öne alındı: `get_table_stats()` altı COUNT çalıştırıyor, sağlık yanıtı sonucu kullanmıyor ve yardımcı hataları sıfıra çeviriyor. `db_session.probe_database_readiness()` tek session ile altı zorunlu tabloda `SELECT 1 ... LIMIT 0` yapar, cursor'ları kapatır ve hatayı iletir. Route `asyncio.to_thread` kullanır; startup/realtime kapıları ve 200/503 sözleşmesi korunur. Yeni testlerle her eksik tablo, query hatası, session/connection cleanup ve bekleyen probe sırasında event-loop ilerlemesi doğrulandı. Hedefli13/13, tam **588/588**, üç değişen Python dosyasında Ruff temiz. İlk20s gecikmenin yalnız COUNT kaynaklı olduğu kanıtlanmadı; kabul süre sınırı gevşetilmedi. Önceki yalnız-belge commit `9a7d149` için CI **34517948297 başarılı**; P1-5 ops release-record güncellendi.

**İkinci yayın denemesi:** `2cf05a8413d560024bfb37cb8e932e0fad97a9fb` için [CI 34521979155](https://github.com/Rapto0/Rapot/actions/runs/34521979155) ve [imaj yayını 34522034163](https://github.com/Rapto0/Rapot/actions/runs/34522034163) başarılı. Yeni snapshot yerelde bağımsız açıldı; sunucuya dönen gzip hash'i doğrulandı. `/root/rapot-ops/20260910-p16-r2` kaydında `/api/health` 200 ve **0,051 saniye**; diğer HTTPS yolları da geçti. Bu kez HTTP isteği takılmadı: `/health-api/status` yaklaşık üç saniyede bir 200 dönerken scheduler'ın `running` durumuna geçmesi için operatörün tanıdığı **65 saniye** doldu. `/api/stats` aşamasına ulaşılmadı. Uygulama tekrar a513af9'a döndü; beş servis sağlıklı, DB restore yapılmadı. Eski botun loglarında sağlık sunucusu 23:05:56, kapsam kontrolünün bitişi 23:07:01, gerçek döngü başlangıcı 23:07:02 (TR): başlangıç için 65 saniye garantisi olmadığı somut olarak görüldü. Başlangıç gözlem penceresi 180 saniyeye çıkarılıyor; tek HTTP isteği sınırları ve gerçek `running` şartı korunuyor, her gözlem güvenli alanlarla kaydedilecek.

**Başlangıç gecikmesinin sınırı:** Aynı üretim snapshot'ında yalnız seçilmiş repository işlevleriyle, ağ/uygulama importu olmadan `mode=ro&immutable=1` altında gerçek 16 kapsam sorgusu **2,484 saniyede** tamamlandı; tek sorgu 0,031–0,391 saniye, sekiz grubun eksik etiket sayısı sıfır. Her sorguda 25 saniyelik kesme sınırı vardı. Bu yerel ölçüm VPS gecikmesinin nedenini kanıtlamaz. Sıralı welcome Telegram çağrısı, kapsam sorguları ve scheduler hazırlığı ayrı sürelerle ölçülmeden SQL/index veya erken `running` değişikliği yapılmadı; P2-4 takibi açık.

**Üçüncü deneme / proxy düzeltmesi:** Aynı 2cf05a8 imajları ve 180 saniyelik scheduler gözlemiyle `/root/rapot-ops/20260910-p16-r3` denemesi, scheduler kabulüne gelmeden `/api/scans` için HTTP502 aldı; a513af9'a veri restore edilmeden döndü. Nginx kaydı 20:14:59 UTC'de `http://[::1]:8000` bağlantı reddi ve ardından `no live upstreams` gösterdi. Docker yalnız IPv4 loopback yayımlıyor: 8000/5000/3000/8001 TCP kontrollerinde 127.0.0.1 açık, ::1 bağlantısı errno111. Beklenmeyen konteyner restart/OOM olayı görülmedi. `/etc/nginx/sites-available/default` yedeklendi; üç `proxy_pass localhost` hedefi 127.0.0.1 yapıldı, zaten IPv4 olan middleware yolu korundu. `nginx -t` ve reload geçti; eski uygulamada strict HTTPS scans/health/status/settings 200. Bu bulgu üçüncü denemenin 502 nedenidir; önceki tüm gecikmelerin tek nedeni diye genellenmiyor.

**Yeniden deneme yedeği:** r3/r4, r2'nin 19:50 UTC tarihli bağımsız doğrulanmış snapshot arşivini hash kontrolü ve hard link ile kullanır; bunlar yeni snapshot değildir. Yerelde gzip ve açılmış SQLite kopyası korunur. Sinyal1.726.925, AI26.393, trade/order/scan_history0; rutin sağlık metadata kaydı nedeniyle bot_stats4→5 oldu. Güncel beş bot_stats satırı ayrıca özel ops dosyasına yedeklendi; fresh config yedekleri var. Tablo sayıları satır içeriklerinin byte-byte aynı olduğunu kanıtlamaz. Uygulama geçişi şema değiştirmiyor; rollback DB restore yapmıyor. r4 öncesi boş disk1.284.038.656 bayt; eski veri/imaj/yedek silinmedi.

**Üretim kabulü — tamamlandı:** `/root/rapot-ops/20260910-p16-r4/deployment.json` 20:23:37 UTC'de `verified`. Kaynak `2cf05a8413d560024bfb37cb8e932e0fad97a9fb`; backend digest `sha256:28d2a58302c3ce362096896ce46d72a670e3a8e32ebdbc83a327c21e7e63c026`, frontend digest `sha256:7fb6a6cf93ce349dc86411aa2a6e9abce32b9d048f235152b5ccc2bda87c84d7`. Beş servis healthy/restart0, init ve yayın sonrası tablo sayıları aynı; middleware135/135/28/383, runtime env dosyaları ve DRY_RUN/false/false korundu. Scheduler gözlemi 46,766 saniyede `unknown` → `running / local_lifecycle / is_scanning=false` gördü. Ayrı health isteği 0,148 saniye; sonraki üç istek 0,048/0,034/0,029 saniye. Bu değerler startup toplam süresi veya eşzamanlı yük altında performans garantisi değildir.

**Tarayıcı / dış akış kabulü:** Anonim `/settings` sunucuda yönetilen ayarlar açıklaması ve scanner bağlantısı; `/health` ÇALIŞIYOR/API Bağlı, eksik sayaçlar `--`, boş tarama geçmişi ve loglar için giriş gereksinimi; `/trades` boş kayıt, sıfır işlem sayıları ve kur dönüşümsüz gerçekleşmiş PnL açıklaması gösterdi. Gerçek storage içeriği/anahtar okunmadı. İlk WSS kontrolünde ekranlar açıkken kline/trade geçti; sinyal kanalı açıldı ama 31,297 saniyede heartbeat görülmedi, sayaç kapanışı eşzamanlı istemciler nedeniyle sonuçsuz kaldı. Yalnız açtığımız üç sekme kapatıldıktan sonra aynı TLS/URL/süre sınırlarıyla yeniden kontrol geçti: BTCUSDT/1m mum, işlem ve sinyal heartbeat30,250 saniye; toplam31,125 saniye. Kanal sayıları başlangıç/son kline0, trade0, signals1; tüm sunucu istemcilerinin kapalı olduğu iddia edilmiyor. İki JSON, `browser-acceptance.json` ve `post-deploy-check.json` ops dizininde korunuyor. Yeni sinyal, AI çağrısı veya emir üretilmedi; eşzamanlı yük konusu P2-4'te açık.

**Kabul kriterleri:**

- [x] PnL yüzdesi miktar/giriş değeriyle tutarlı; sıfır ve farklı miktar örnekleri doğrulandı.
- [x] Güncel fiyat yokken giriş fiyatı güncel fiyat gibi sunulmuyor; API bağlantısı bot çalışıyor bilgisiyle karıştırılmıyor.
- [x] Botun bilinmeyen/kapalı/çalışan durumları doğru gösteriliyor.
- [x] Kalıcı bot ayarları için yetkili backend sözleşmesi uygulandı veya ekranın yalnız tarayıcı tercihi olduğu açıklaştırıldı; seçilen kapsam kaydedildi.
- [x] Secret alanları düz localStorage'a kaydedilmiyor; ayarın gerçek hesaplamaya etkisi gösterildi. Config eşik nesnelerinin üretim hesaplayıcısına bağlı olmadığı bulgusu dikkate alındı.

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

**P1-6 sırasında salt okunur başlangıç incelemesi (aşağıdaki uygulamadan önce):**

- `frontend/src/app/chart/page.tsx` parametreleri senkron nesne gibi okuyor; kurulu Next kaynak kodu Promise geçiriyor. Parametreli URL'nin varsayılan THYAO/BIST'e düşmesi koddan beklenen sonuç; gerçek tarayıcı kabulü henüz yapılmadı. **İlk başlanacak dosya bu:** Promise çözümleme ve symbol/market normalizasyonu. `advanced-chart.tsx` yeni initialSymbol/initialMarket değerlerini state'e zaten taşıyor; URL geçişi mekanizmasını baştan yazma. Doğrudan URL ve aynı sayfada geçiş, eksik/tekrarlı/geçersiz parametreler test edilmeli.
- `signals/page.tsx` Dışa aktar düğmesinde `onClick` yok. Görünür filtre/arama sonucunun `rows` verisi kullanılabilir; en fazla yüklenen 300 satır olduğu açık olmalı, tüm arşiv gibi sunulmamalı. Türkçe/CSV kaçışları, filtre/arama, boş/hatalı veri ve spreadsheet formül enjeksiyonu sınırı ele alınmalı.
- `alarms/page.tsx::evaluateRules` yalnız sayfa açıkken ilk kontrol + 60 saniyelik timer ile çalışıyor; kurallar localStorage'da. Arka planda 7/24 bildirim servisi yok. UI, son kontroldeki eşleşmeler ile sürekli bildirim hizmetini karıştırmamalı.
- Alarm kontrollerinde eşzamanlılık koruması yok; eski sonuç yeni kontrolü ezebilir. Henüz kontrol edilmemiş veya verisi alınamamış kuralın “Tetik yok” görünmesi de açık. Geciktirilmiş istekler, silinen/değişen/kapalı kural, hata ve unmount timer cleanup testleri gerekli.

**Dosyalar:** [signals page](../frontend/src/app/signals/page.tsx), [alarms page](../frontend/src/app/alarms/page.tsx), [watchlist alarms](../frontend/src/lib/watchlist-alarms.ts), [chart page](../frontend/src/app/chart/page.tsx).

**P2-1 uygulaması (10 Eylül UTC / 11 Eylül TSİ; yerel, CI ve yayın kabulü tamam):**

- Chart sayfası Next'in Promise `searchParams` değerini bekliyor. Sembol trim/büyük harf/1–32 ASCII harf veya rakam kontrolünden geçiyor; boş veya geçersiz sözdizimi seçilen piyasada THYAO/BTCUSDT'ye düşüyor. Piyasa büyük/küçük harften bağımsız `Kripto`, diğer değerlerde BIST. Tekrarlı parametrelerde ilk değer kullanılıyor. Bu bir sembol kayıt servisi değil; sözdizimi geçerli fakat listelenmeyen sembol korunuyor. Var olan aynı sayfa prop→state geçişi korunuyor.
- CSV, mevcut filtre/arama sonucunun görünen `rows` değerlerini aynı sırayla indiriyor. Yüklenen en fazla 300 kayıt sınırı ekranda açık; dışa aktar düğmesi yeni veri istemiyor. UTF-8 BOM, noktalı virgül ayracı, CRLF, Türkçe sütunlar/ondalık ve UTC tarih kullanılıyor. Metin hücrelerinde CSV kaçışı ve formül başlangıcına apostrof koruması; geçersiz sayı/tarih boş. Yükleme/yenileme/hata/boş sonuçta indirme engelleniyor, geçici URL bırakılıyor.
- Yerel alarm monitor'ü ilk kontrol + yaklaşık 60 saniye kontrolünü yönetiyor. Aynı anda gelen manuel/periyodik tetikler aktif koşuma katılıyor; en fazla dört mum isteği ve istek başına 20 saniye sınırı var. Kural/liste değişmesi, silinmesi, kapanması veya sayfadan ayrılma eski koşumu iptal ediyor; iptali dikkate almayan adaptörün geç yanıtı yeni sonucu değiştiremiyor. Mum okuma adaptörüne opsiyonel `AbortSignal` eklendi.
- Veri yok, bilinmiyor, hata, kısmi kontrol, kapalı, tetik var/yok durumları ayrıldı. Geçersiz OHLCV veya en son göstergenin hesaplanamaması eski bir geçerli değerle gizlenmiyor. Sayfanın yerel saklama ve yalnız açıkken çalışma sınırı ekranda yazıyor; kalıcı bildirim hizmeti eklenmedi. COMBO/HUNTER eşikleri değiştirilmedi; mevcut COMBO sıfır değer bulgusu P3-1'de açık.
- Bağımsız inceleme, açık chart sekmesinin başka sekmede silinen/kapatılan alarmı eski state kaydıyla geri getirebildiğini gösterdi. Chart ve alarms artık kullanıcı niyetini güncel depoya uyguluyor; hydration/storage event yolu yalnız okuyor. Ekleme, açık/kapalı hedefi, silme, liste yeniden adlandırma/silme bu adaptöre bağlı. Bozuk/okunamayan kayıt üzerine boş dizi yazılmıyor; başarısız yazı ekranda başarılı gibi uygulanmıyor. Gecikmiş storage olayının eski `newValue` içeriği oynatılmıyor. localStorage için gerçek eşzamanlı yazımlarda işlem garantisi yok; son yazan davranışı sürüyor.
- İlk derlenmiş tarayıcı kabulünde React `#418` metin hydration hatası görüldü. `Header` tarih/saatini ilk render'da `new Date()` ile üretmesi sunucu ve tarayıcıda farklı metne neden olabiliyor; bu satırlar `78f74e7b` (24 Şubat) kaynaklı. P2-1'in hatayı oluşturduğu iddia edilmiyor. Sabit ilk render ve effect sonrası saat güncellemesi bu runtime kabulü kapsamında düzeltildi; son yerel ve üretim tarayıcı konsollarında hata görülmedi.

**İlk bütünleşik yerel doğrulama:** Node 20.20.2/npm 10.9.9 ile **93/93 frontend**, lint, TypeScript ve Next production build geçti. Gerçek Next standalone üzerinde beş chart URL/fallback örneği, RSC/Flight parametreleri, HTML/static asset, API yetki header proxy'si, bot health proxy'si ve WebSocket upgrade geçti. Bu sayım sonradan eklenen header saat testlerini henüz içermez.

**İlk tarayıcı kabulü:** Yalnız sentetik GET servisli `127.0.0.1:64554` üzerinde doğrudan BTCUSDT/Kripto → aynı sayfa Next bağlantısıyla ETHUSDT/Kripto geçişi, iki sekmede kapalı/silinmiş kuralın geri gelmemesi, kontrol sırasında silme, düğme kilidi, boş veri/hata etiketleri ve boş aramada indirme engeli doğrulandı. Gerçek CSV dosyası bağımsız ayrıştırıldı: bir BTCUSDT satırı, 185 bayt, SHA256 `10ed1bf8738410c4c57ea5c49a0fd27f6324ce4f35f9e7377164c8362087015c`; BOM/ÇOK UCUZ/korunan skor/123,45/UTC tarih doğru. İndirme olayı bekleyen araç iki kez zaman aşımı verdi; iki gerçek indirilmiş dosya aynı hash ile doğrulandı. 140 mock isteğinin tümü GET; gerçek DB/broker çağrısı yok. Mevcut tarayıcı Binance halka açık kotasyon akışı ayrıca bağlandı; bu akış sentetik test verisi olarak sunulmadı. İki test sekmesi ve yerel servisler kapatıldı. İlk kanıtlar `runtime-data/p21-browser-first.json` ve `p21-browser-requests-first.json` içinde korunuyor. Header saat düzeltmesinden sonraki kabul aşağıda ayrıca kaydedilecek.

**Dağıtım sınırı ve sonuç:** Değişiklik frontend kapsamındadır. `db98915` kaynak arşivi ve frontend imajı yayımlandı; backend `2cf05a8` digest'i korundu. Yalnız frontend `up --no-deps --no-build --pull never` uygulandı. API/bot/middleware/PG container kimliği, başlangıcı ve restart sayısı ile ortam dosyaları/Nginx birebir aynı kaldı. DB migration, restore, broker işlemi veya bot yeniden başlatması yapılmadı. `current` kaynak symlink'i frontend commit'ine ilerledi; `release.env` backend SHA'sını koruyor. Bu yüzden bileşen kaynakları tek SHA diye raporlanmıyor.

**Header düzeltmesi sonrası son yerel kabul:** **95/95 frontend** (43 yeni test durumu), tüm frontend ESLint, Next 16.2.1 production build içindeki TypeScript ve standalone HTTP/static/RSC/auth proxy/health proxy/WS upgrade geçti. Önceki açık `tsc --noEmit --incremental false` kontrolü de geçmişti. Yeni saat testleri SSR ve tarayıcı için farklı an/zaman diliminde aynı `-- | --` başlangıcını, mount sonrası hemen saat dolmasını, saniyelik tick ve cleanup'ı doğruluyor. Son derleme ile `127.0.0.1:59447` tarayıcı kabulünde BTCUSDT/Kripto → aynı sayfada ETHUSDT/Kripto, ` asels /bist` → ASELS/BIST ve mount sonrası gerçek saat görüldü; hata konsolu boş. 23 mock isteğinin tümü GET; sekme ve test servisleri kapandı. Kanıt `runtime-data/p21-browser-final.json`. Bu tur Python/bağımlılık/Compose değişmedi; yeni SHA üzerinde tam Python CI işi ve Docker/PG/standalone kontrolleri de geçti.

**Kabul kriterleri:**

- [x] Dışa aktarma görünür filtrelerle uyumlu veri üretiyor veya desteklenmeyen işlem UI'dan kaldırılmış.
- [x] Alarmın sayfa açıkken çalışma sınırı UI'da anlaşılır; arka planda 7/24 hizmet istenirse ayrı kapsam ve iş olarak kaydedilmiş.
- [x] Grafik URL'sindeki symbol/market, doğrudan giriş ve sayfa geçişinde doğru uygulanıyor; geçersiz değer fallback'i test edilmiş.
- [x] İlgili UI davranışları ile lint/typecheck/build kontrolleri doğrulanmış.
- [x] Exact-SHA CI/imaj yayını ve yalnız frontend üretim geçişi, korunan servisler ve dış HTTPS kabulü tamamlandı.

**Üretim kaydı:** Uygulama commit'i `db989155aaad22897e7333bfc11f4bbf78bc1e99`; [CI 34530618110](https://github.com/Rapto0/Rapot/actions/runs/34530618110) ve [yayın 34530649980](https://github.com/Rapto0/Rapot/actions/runs/34530649980) başarılı. Frontend `ghcr.io/rapto0/rapot/frontend@sha256:bdd84c03df4586db1d4c50bc4d5b9e74c3124cfc319708efa47ccb1899c89c25`; backend `ghcr.io/rapto0/rapot/backend@sha256:28d2a58302c3ce362096896ce46d72a670e3a8e32ebdbc83a327c21e7e63c026`. Yeni frontend 21:14:52 UTC'de başladı; 21:15:01 UTC'de geçiş doğrulandı. Dört korunan servis yeniden başlatılmadı. Middleware DRY_RUN/trading=false/live=false korundu; API/bot anahtar ve AI ayarları değiştirilmedi. Kaynak arşivi 23.834.700 bayt, SHA256 `291f42bc961df98b9d7687b3081fc689680ea87a3ca12bb078e1e121afec727a`; 399 kaynak dosyası/21 fark ve beş özel config yedeği doğrulandı.

**Dış kabul:** Yerel container HTTP health, gerçek HTTPS `/api/health`, `/health-api/status`, `/signals`, `/alarms`, chart SSR/RSC parametreleri geçti. Ek üç health 0,046/0,019/0,018 saniye; beş servis healthy/restart0. Üretim tarayıcısında doğru BTCUSDT/Kripto, çalışan saat, CSV kapsam metni ve etkin düğme, yerel alarm sınırı görüldü; kullanıcı alarmı oluşturulmadı/değiştirilmedi. İlk kısa grafik gözleminde mum isteği henüz bitmemişti; Nginx aynı yol için 21:15:50 UTC'de 200/100.656 bayt kaydetti. Ayrı tekrar gözleminde 1.000 mum ve `Kaynak: binance` görüldü, konsol boş; son test sekmesi kapandı. Bu bir gecikme benchmark'ı değildir ve P2-4'ü kapatmaz.

**Kanıt ve geri dönüş:** `/root/rapot-ops/20260910-p21/` içindeki `preparation.json`, `deployment.json`, `post-deploy-check.json`, `browser-chart-followup.json`, yerel kabul JSON'ları ve özel config yedekleri korunuyor. Yerel aynalar `runtime-data/p21-*.json`; operator hazırlama/yayın yardımcıları Git dışındaki aynı klasörde. Eski `2cf05a8` frontend digest'i/kaynak ağacı ve önceki DB yedekleri silinmedi. Yeni belge commit'i için canonical plan/deploy dokümanı bu operator klasöründe ayrıca hash ile eşitlenecek; uygulama arşivi değiştirilmez.

### P2-2 — Belgeler ve wrapper göçünün kapanışı

**Durum:** **Doğrulandı — 11 Eylül 2026.** Belge ve karar kapsamı kapandı; wrapper dosyalarını silme kapsamı açılmadı. Kaynak tabanı `ee49508`; çalışma sırasında uygulama, test, bağımlılık veya config kodu değiştirilmedi.

**Neden:** HUNTER açıklaması, Alembic kapsamı ve bazı bağımlılık notları eski. Paketleme aşama 5 açık; kaldırma takviminde canonical handler da legacy listesinde.

**Dosyalar:** [AGENTS.md](../AGENTS.md), [README](../README.md), [Codex bağlamı](Codex.md), [paketleme haritası](PACKAGING_REFACTOR_MAP.md), [wrapper takvimi](WRAPPER_DEPRECATION_SCHEDULE.md), [DB politikası](DB_MIGRATION_POLICY.md), [eski spot backlog](ALGOTRADING_SPOT_BACKLOG.md), [compat telemetry](../infrastructure/compat/wrapper_telemetry.py).

**Kabul kriterleri:**

- [x] Ana SQLite migration yolu ile middleware Alembic yolu doğru ayrıldı; HUNTER 15 gösterge puanı ve güncel bağımlılıklar açıklandı.
- [x] Canonical import yolları ile compatibility wrapper listesi gerçek kodla eşleşiyor.
- [x] Wrapper kaldırma kararı tarih takvimine tek başına dayanmıyor; kullanım/import kanıtı ve regression kontrolleri var.
- [x] Eski backlog'lar bu planla çelişmiyor; uygulanmış maddeler sırf kutusu boş diye yeniden yapılmıyor.

**İnceleme ve düzeltme:**

- AGENTS/README/Codex; Python 3.12, Node20.20.2/npm10.9.9, Next16.2.1/React19.2.3/TS5.9.3, `google-genai` ve lock/requirements ayrımıyla güncellendi. HUNTER'ın 15 koşul sayımı olduğu, `7/7` alanının puan/eşik anlamı, NaN ve sabit eşikler açıklandı; RSI ayrı zorunlu veto değil. COMBO CCI dahil dört gösterge, bilinen/bilinmeyen timeframe eşikleri ve fonksiyon içi sabitler belgede doğru ayrıldı.
- Ana SQLite `db_session.init_db`/eklemeli kolon yolu ile ayrı PG16/Alembic `20260907_0006` yolu ayrıldı. `migrate_db.py` genel deploy adımı değil: sabit kaynak dosya, tekrar trade/history ekleme ve raw copy2/WAL yedek sınırları var. Eski “Alembic yok” yorumları yalnız ana SQLite kapsamına alındı; runtime dosyaları değiştirilmedi.
- 211 tracked Python dosyası import edilmeden AST ile incelendi: telemetry kaydı yapan **12 wrapper**; runtime/script tarafında doğrudan legacy import bulunmadı. Test tüketicileri ve dinamik telemetry reload örnekleri haritada açıkça listelendi. Canonical `application.scanner.signal_handlers` kaldırma listesinden çıkarıldı, gerçek wrapper `scanner_side_effects` gösterildi.
- Telemetry import/reload sayımıdır; süreç belleğinde yaşar, request/fonksiyon sayımı veya tüm deployment envanteri değildir. Boş snapshot dış tüketici yokluğunu kanıtlamaz. **Karar: 12 wrapper'ı koru**, yeni kodda canonical import kullan. Eski tarih metadata'sı otomatik silmez; fiziksel kaldırma için sürüm/süreç/gözlem penceresi/harici tüketici kanıtları ve dar regression/yayın/geri dönüş gerekir. Bu tur canlı telemetry çağrısı yapılmadı.
- Spot backlog'un 20 ALG kimliği korunarak kod/izole kabul, kısmi özellik ve ertelenen dış kabul eşlemesi yazıldı. İki eski mimari planına tarihsel P kimlikleri ve kaynakta mevcut parçaların sınırları eklendi. Frontend README; ayarlar kapsamı, 300 yüklenmiş/görünür CSV satırı, RSI/WR/COMBO/HUNTER yerel alarmı, sayfa-açık sınırı ve sekme yarışlarını açıklar. Middleware README'deki eski “üretime uygulanmadı” ifadesi tarihli PG16/0006 kabulüyle düzeltildi.
- Mimari bağlam, ortak SQLite SignalFeed → API WS/SSE → REST resync yolunu anlatır; süreç içi publisher'ın ayrı API sürecine doğrudan teslim yaptığı iddia edilmez. Manuel inspector, kaydetmeyen GET AI analizi ve Telegram yan etkili admin manuel tarama ayrı gösterildi. Ana dashboard ile middleware emir verisi ayrımı korunur.

**Doğrulama:** Mevcut testlerde 37/37 wrapper/boundary/telemetry/read-model/handler, 30/30 ana DB/scan history/middleware schema gate/inventory migration, 31/31 signals/config; toplam **98/98**, üç ayrı izole koşum. DB grubunun mevcut **10 UTC deprecation warning** kaydı P2-3 borcu. Yerel belge hedefleri/anchor ve diff whitespace kontrol edildi. Yeni uygulama/test kodu yok; frontend kodu değişmediği için bu tur yerelde build tekrar edilmedi. Tam Python/frontend/build/PostgreSQL/container smoke kontrolleri belge commit'inin CI'sinde çalışır; sonuç tam SHA ile operator kaydına bağlanır.

**Belge yayını:** Hedef `/root/rapot-ops/20260911-p22/`; Git blob'larından alınan Markdown snapshot'ları, SHA256 manifesti ve `release-record.json` kullanılır. Ön kontrol 11 Eylül 15:44:58 UTC: beş servis sağlıklı/restart0; API/bot HTTPS health 200. Kaynak pointer'ı db98915, frontend db98915/backend2cf05a8 imajları ve config hash'leri aktarım sonunda tekrar karşılaştırılır. Bu belgenin kendi commit/CI kimliği, kanıtın kendisine referans döngüsü oluşturmaması için ayrı operator kaydında tutulur. Yeni imaj, servis restart'ı, migration/backfill, emir veya dış AI/Telegram testi yapılmaz.

**Açık kalan sınır:** Wrapper kaldırılması dış kullanım kanıtı gelmeden yapılmaz; bu, P2-2 belge kabulünün eksikliği değildir. P1-3 dış alarm/emir kabulü kullanıcı isteğiyle erteli; P2-4 yük/gecikme ve P3-1 motor sınırları açıktır. P2-2 kapanışında açık olan lint/araç işi, aşağıdaki P2-3 kabulüyle tamamlandı.

### P2-3 — Ruff, atıl kod ve araç tarama kapsamı

**Durum — 11 Eylül 2026: Doğrulandı.** `bacbfab814bb659f093a33733934b56f2bf5b19a` commit/push, Linux CI/imaj ve **19:14:51 UTC üretim kabulü tamam**; API/bot/middleware/frontend aynı kaynak sürümünde. Güvenlik bulguları report-only kalır; bu P2-3 kabulünde P1-G1 henüz açıkken, sonraki P1-G1 sonucu aşağıda kaydedildi. Son belge commit/CI ve aktarım kanıtı ayrı operator kaydında tutulur; uygulama imajını değiştirmez.

**İnceleme:** İlk fotoğraftaki sekiz Ruff bulgusunun ikisi önceki strateji çalışmalarında kapanmıştı. Bu tur ana kaynakta kalan altı bulgu (`main.py`, backfill scripti, `tests/test_config.py`) ve iç worktree tekrarları ayrıldı. Git’te takip edilen 211 Python dosyasından yalnız iki test dosyası format gerektiriyordu. Önceki testlerdeki `datetime.utcnow()` kullanımı, offset içermeyen UTC saklama/API sözleşmesiyle birlikte incelendi. Eski güvenlik işi hem bulguyu hem araç hatasını `|| true` ile yutuyor, tarama kapsamını veya raporunu korumuyordu.

**Düzeltme ve sınırlar:**

- Altı Ruff bulgusu ve iki testin formatı düzeltildi. CI artık yalnız değişen dosyaları değil, Git’in takip ettiği tüm Python kaynaklarını ve middleware/test dosyalarını tarıyor. `pyproject.toml` exclusions + `force-exclude=true` ile pre-commit kapsamı; iç worktree, venv, bağımlılık, çalışma verisi/log ve üretilen çıktı dizinlerini dışarıda tutuyor. Yeni [CI aracı](../scripts/ci_quality.py) aynı takipli kaynak listesini kullanır; boş/eksik kaynak listesi başarı sayılmaz.
- `.claude/worktrees/festive-bartik-1395fb` gitlink’i yalnız ana repo index’inden kaldırıldı ve `.claude/` ignore edildi. İç dosyalar, detached `f752ee2` HEAD’i ve Git worktree kaydı korundu; iç worktree veya backup branch silinmedi/birleştirilmedi.
- Statik/dinamik import ve export kullanımı araştırılan altı atıl frontend dosyası kaldırıldı: `ai-analysis-widget.tsx`, `global-ticker.tsx`, `recent-signals.tsx`, `signal-terminal.tsx`, `ticker-tape.tsx` ve tarihsel `frontend/src/lib/mock-data.ts` yolu. Toplam **1.568 satır** kaldırıldı; aktif dashboard ve uygulanan P2-1 akışları korunuyor. PortfolioPanel TODO’ları P1-6’da zaten çözülmüştü; eski backlog kaydı kaldırma kanıtı sayılmadı, test tüketicisi bulunan panel korundu.
- [UTC yardımcı işlevi](../infrastructure/time.py) `datetime.now(UTC).replace(tzinfo=None)` kullanıyor. Model varsayılanları/güncellemeleri, signal-tag yaş sınırı, lease/counter/coverage, veri sağlayıcı zamanları, takvim önbelleği, eski taşıma ve backtest çağrıları buna bağlandı. Ana DB’nin offset içermeyen UTC biçimi ve mevcut API/JSON biçimleri korunuyor; şema migration’ı veya geçmiş zaman damgalarının yeniden yazımı yok.
- Checkout/setup-python/setup-node v6, Docker setup-buildx/login v4, build-push v7 ve upload-artifact v6 sürümlerinin Node24 runtime’ı resmî `action.yml` kaynaklarından doğrulandı. Bunlar Actions çalışma motorudur; uygulamanın Node20.20.2/npm10.9.9 ve Python3.12 seçimi değişmedi.
- CI-only Bandit **1.9.4**, pip-audit **2.10.1** ve parser için packaging **26.0** doğrudan sürümle sabitlendi; uygulama lock’u değiştirilmedi. Bandit tüm takipli Python kaynaklarını, pip-audit `requirements-dev.lock` içindeki çalıştıran Python/platform marker’larına uygulanabilen exact paketleri denetler. `--no-deps --disable-pip --strict` kullanılır; paket kurma/düzeltme veya `--fix` yok. npm, container OS paketleri, runtime config ve anahtar taraması bu kapsamda değildir.
- Güvenlik **bulguları report-only**: uyarı, sayılı job özeti, JSON raporları ve taranan dosya/paket manifestleri 14 gün artifact olarak saklanır. Araç kurulumu/çağrı hatası, timeout, plugin hatası, bozuk/eksik JSON, atlanan dosya/paket, kapsam veya exit-code uyuşmazlığı CI’yi başarısız yapar. Bir tarayıcı hata verse de diğerinin raporu alınmaya çalışılır. Bu politika güvenlik bulgularını çözülmüş saymaz.

**İlgili dosyalar:** [health_api.py](../health_api.py), [pyproject.toml](../pyproject.toml), [pre-commit](../.pre-commit-config.yaml), [CI](../.github/workflows/ci.yml), [imaj workflow’u](../.github/workflows/deploy.yml), [CI aracı](../scripts/ci_quality.py), [CI politika testleri](../tests/test_ci_quality.py), [main.py](../main.py), [backfill scripti](../scripts/backfill_signal_details.py), [test_config.py](../tests/test_config.py), [UTC yardımcı işlevi](../infrastructure/time.py), [UTC testleri](../tests/test_utc_timestamps.py), [models.py](../models.py), [signal repository](../infrastructure/persistence/signal_repository.py), [ops repository](../infrastructure/persistence/ops_repository.py), [data_loader.py](../data_loader.py), [calendar service](../api/calendar_service.py), [migrate_db.py](../migrate_db.py), [backtest](../backtesting_system.py) ve yukarıda tarihsel yollarıyla listelenen altı frontend dosyası.

**Yerel doğrulama:**

| Kontrol | Sonuç ve sınır |
|---|---|
| Python son bütünleşik paket | **642/642, uyarısız; 65,85 saniye**. 21 yeni UTC ve 33 CI politika testi dahil; önceki 609 testlik koşumun üzerine son kaynaklar birlikte doğrulandı |
| UTC sözleşmesi | **21 yeni test**: legacy DB/JSON/API biçimi, ORM insert/update, tag yaşı/lease/coverage sınırları, provider/cache/taşıma zamanları; önceki 874 UTC warning bu tam koşumda görülmedi |
| CI güvenlik politikası | Ayrı koşum **33/33**; bozuk/eksik JSON, eksik/fazla/atlanan dosya-paket, yanlış sürüm/exit, plugin hatası, timeout, report-only bulgu ve ikinci tarayıcının devamı |
| Ruff ve yapı | Tüm kaynakta lint/format; yeni Python dosyaları, `force-exclude` ve pre-commit kapsam kontrolü; YAML parse/diff kontrolü geçti. Son güvenlik manifesti 215 Python dosyası içeriyor |
| Bağımlılık | `uv pip check` **128 paket** için geçti; uygulama bağımlılığı yükseltilmedi |
| Frontend | **95/95**, ESLint, TypeScript, production build ve gerçek standalone HTTP/RSC/WS kabulü geçti |
| Operator hazırlığı | 9/9 sentetik codec testi geçti; gerçek yedek/CI/geçiş kabulü aşağıda ayrıca kayıtlı |

**Gerçek yerel güvenlik tabanı ve son tarama:** Ana `.venv` değiştirilmeden Git dışında `runtime-data/p23-security-tools` ortamıyla kaynak/lock tarandı. İlk tabanın ardından eklenen dört Python dosyası ve standalone debug düzeltmesini içeren **son tarama 215/215 dosyada 1.490 Bandit bulgusu: 0 HIGH / 15 MEDIUM / 1.475 LOW** verdi. Son pip-audit **128/128 paket, 24 etkilenen paket, 203 advisory kaydı**; sayı değişmedi. Son kanıtlar `runtime-data/p23-security-final/` altında; iki araç da tam raporla report-only politikası kapsamında exit0 verdi. Aşağıdaki ilk taban silinmeden tarihsel karşılaştırma için korunuyor. Bandit **211/211 dosya**, **1.422 bulgu**: **1 HIGH / 12 MEDIUM / 1.409 LOW**; bunların **1.374’ü B101 assert** uyarısı. pip-audit, yerel Windows/Python3.12 marker kapsamındaki **128/128 paket** içinde **24 pakette 203 advisory kaydı** raporladı. Bunlar doğrulanmış istismar veya birbirinden bağımsız 203 CVE sayısı değildir; test kodu, geliştirici bağımlılığı ve çalışma yolundaki erişilebilirlik ayrıca incelenecek. Linux CI marker kapsamı farklı paket sayısı üretebilir. İki tarama da tam rapor verdi; başarı çıkışı yalnız tanımlı report-only politikasını gösterir. Kanıtlar Git dışındaki `runtime-data/p23-security-baseline/` altında `summary.json`, `summary.md`, `bandit.json`, `pip-audit.json`, dosya/paket manifestleri ve araç loglarıdır. Hiçbir anahtar, hesap, DB veya borsa emri bu taramaya dahil edilmedi; pip-audit yalnız halka açık PyPI advisory kayıtlarını sorguladı.

**Güvenlik bulgularının durumu — P2-4 performans işinden ayrı:**

- **P0-G1 — Standalone Flask debug — Doğrulandı:** İlk Bandit B201/HIGH raporu [health_api.py](../health_api.py) dosyasının `__main__` yolundaki `app.run(debug=True, port=5000)` satırına işaret ediyordu (ilk raporda satır 442). Bu yol artık açıkça `host="127.0.0.1", debug=False, use_reloader=False` ile başlıyor. Üretimdeki `start_health_server()` zaten debug/reloader kapalıydı; başlangıç raporu üretimde erişilebilir debugger kanıtı değildi. Yerel ve Linux CI Bandit **HIGH=0**; düzeltme `bacbfab8` imajlarıyla üretime taşındı.
- **P1-G1 — Python bağımlılık advisory’leri — sıradaki iş, P2-4’ten önce:** [requirements-dev.lock](../requirements-dev.lock) raporundaki 24 paketi runtime/test aracı ve gerçek kullanılan özellik açısından sınıflandır; alias/tekrarlı kayıtları ayır, uygulanabilir güvenlik düzeltmesi sürümlerini resmi advisory/release kaynaklarıyla doğrula. `aiohttp`, `cryptography`, `starlette`, `requests/urllib3`, `Flask/Werkzeug` gibi kullanılan yollar öncelikle incelenecek; geniş ve otomatik toplu upgrade yapılmayacak. Her seçilen küçük yükseltme için lock, uyumluluk testleri ve imaj kabulü gerekir. Kapsam orta; bağımlılık paket kullanım incelemesi ve izole regression tabanıdır. **Bu P2-3 başlangıç kaydıdır:** 24 paket/203 kayıt vardı; P1-G1 yerel düzeltme sonucu aşağıdadır. Başlangıç kanıtı tam SHA CI artifact’i ve hash’i doğrulanmış özel sunucu kopyası `/root/rapot-ops/20260911-p23/security-reports/`; rapor/manifest/loglar gerçek DB veya anahtar içermez, GHA’nın 14 günlük saklama süresinden bağımsız korunur.

**Linux CI / imaj / üretim kabulü:** [CI 34636602751](https://github.com/Rapto0/Rapot/actions/runs/34636602751) ve [imaj 34637100266](https://github.com/Rapto0/Rapot/actions/runs/34637100266) tam `bacbfab814bb659f093a33733934b56f2bf5b19a` için başarılı. CI güvenlik raporu **215 dosya / 1.490 bulgu (0 HIGH, 15 MEDIUM, 1.475 LOW)** ve **128 paket / 24 etkilenen paket / 203 advisory** gösteriyor; her iki tarama tam kapsamla tamamlandı. Üretimde sabitlenen digest’ler:

| İmaj | Digest |
|---|---|
| Backend — API/bot/middleware | `sha256:18dcf104fd3e3e85d6d016c22d76a98e6dbf88ae4e0a9b60554803468d0c81b4` |
| Frontend | `sha256:369674a790d86d84ee06e16edc050e2968d5928f511a31f666d5644ecfb65340` |

**Yedek ve hazırlık:** Yeni tutarlı SQLite snapshot’ı **135.495.129 bayt SQL gzip** olarak alındı. OneDrive dışındaki özel yerel Temp’te **1.019.465.728 bayt** bağımsız SQLite kopyası yeniden oluşturuldu; integrity, arşiv/SQL hash’i, yedi tablonun şema/metadata ve tip duyarlı satır fingerprint’leri eşleşti. Bu mantıksal eşdeğerlik kontrolüdür; kaynakla fiziksel DB dosyası eşitliği iddiası değildir. PostgreSQL **59.240 bayt** dump ve 66 satırlık katalog kontrolü geçti; **bağımsız PostgreSQL restore yapılmadı**. Beş özel config yedeği alındı; tam Git dosya farkı ve değişmeyen Compose/`db_session.py`/Alembic zinciri doğrulandı. Önceki yedek/imajlar korundu.

**Üretim sonucu ve sınırı:** `deployment.json` **2026-09-11T19:14:51.075637+00:00** anında `verified`. HTTPS `/api/health` **0,036 saniye/200**; `/`, `/signals`, `/alarms`, `/chart` SSR 200; SignalFeed ready, Binance connected ve BIST running. Scheduler gözleminde **43,781 saniyede unknown → running**, `is_scanning=false`, `data_available=false` görüldü; bu başlangıç/lifecycle kabulüdür, yeni tamamlanmış tarama kabulü değildir. Yeni uygulama konteynerlerinin restart sayısı 0. Ana sayılar geçiş öncesi/sonrası aynı: **1.732.308 sinyal, 26.393 AI, 5 scan history, 4 bot_stats, 0 trade/order**. PostgreSQL konteyner kimliği ve **135/135/28/383** sayıları, runtime kimlik bilgileri ve Nginx korundu; **DRY_RUN/trading=false/live=false**, emir yok. Manuel initializer/migration veya DB restore çalıştırılmadı. Kalan disk **884.736.000 bayt**. Bu operatör yeni etkileşimli tarayıcı/WS trafik veya eşzamanlı yük kabulü yapmadı; P2-4 açık. Ayrı Windows gözlemcisinden 19:19:35 UTC’de HTTPS API health **0,204 saniye**, bot health **0,187 saniye**, ikisi de **200/healthy** doğrulandı; bunlar sunucu üzerinden yapılan 36 ms ölçümünden ayrıdır.

İlk deneme Compose `x-python.image` şablon etiketi karşılaştırmasında **pull/uygulama değişikliğinden önce** durdu. Yalnız operatörün kontrolü dar biçimde düzeltildi; uygulama kodu değişmeden ikinci deneme geçti. İlk kayıtlar `/root/rapot-ops/20260911-p23/attempt-1/` altında korundu; bu bir uygulama rollback’i değildi. Son `preparation.json`, `deployment.json`, `backup.json`, bağımsız doğrulama ve PostgreSQL dump kanıtları aynı özel OPS dizininde tutulur.

**Kabul kriterleri:**

- [x] Ana kaynak Ruff bulguları kapatıldı; tam takipli kaynak ve yeni dosyalar lint/format kontrolünden geçti.
- [x] İç worktree, bağımlılık ve üretilen klasörler için ortak araç kapsamı tanımlandı.
- [x] Altı atıl dosyanın kullanım ihtimali incelendi; frontend davranış testleri/build/standalone geçti.
- [x] İç worktree/backup branch korunarak yalnız ana repo gitlink kaydı kaldırıldı.
- [x] UTC deprecation kaynakları saklama/okuma sözleşmesi korunarak düzeltildi ve sınırları test edildi.
- [x] Güvenlik bulgusu ile araç/eksik tarama hatası ayrıldı; gerçek rapor ve offline hata senaryoları doğrulandı.
- [x] Son kaynakların bütünleşik Python koşumu **642/642, uyarısız** geçti; standalone debug bulgusu son kaynak/taramada kapandı.
- [x] Commit/push ve tam SHA Linux CI/imaj kabulü tamamlandı.
- [x] Kontrollü üretim geçişi, veri/config korunum ve dış HTTPS/sağlık kabulü tamamlandı.

**Yayın ve kullanıcı sınırı:** P2-3 uygulama yayını tamam. Son belge commit/CI, Git blob hash’leri ve aktarım kanıtı sürüm bazında `/root/rapot-ops/20260911-p23/documentation-release-record.json` içinde tutulur; uygulama imajını değiştirmez veya servis restart’ı gerektirmez. P1-G1/P2-4/P3 açık, para/hesap gerektiren testnet veya gerçek emir ve TradingView alarm teslimi kullanıcı isteğiyle ertelidir.

### P1-G1 — Python bağımlılık güvenliği

**Durum (11 Eylül 2026): Doğrulandı.** İncele → düzelt → doğrula → belgeyi güncelle, commit/push, Linux CI/imaj ve **20:56:32 UTC üretim kabulü tamamlandı**. API/bot/middleware/frontend kaynağı `ccd61544ede603eb064d871a4ec797c5057307f4`. Ücretli yükseltme yapılmadan, doğrulanmış üç eski sunucu kopyasına verilen devam onayıyla alan açıldı. P2-4 uygulaması henüz başlamadı.

**Başlangıç ve sayım:** P2-3'ün doğrulanmış pip-audit raporu 128 aktif pakette 24 etkilenen paket / 203 advisory kaydı içeriyordu. ID ve alias bağlantıları birleştirildiğinde 114 grup oluşuyor; 203 bağımsız açık veya uzaktan istismar kanıtı değildir. Eski rapor ve 24 paketin tüm alias/önkoşul envanteri korunur. Aşağıdaki “kullanım” değerlendirmeleri kaynak ve seçili bağımlılık grafiği içindir; üretimde saldırı denenmedi.

| Paket: önce → karar | Grup | Kullanım ve kararın dayanağı |
|---|---:|---|
| aiohttp 3.13.3 → 3.14.3 | 24 | Binance WS/BIST async HTTP yollarında; istemci yanıt ayrıştırıcısı ilgili. Server-only bulgular istemci bulgularıyla bir tutulmadı. [İstemci advisory](https://github.com/aio-libs/aiohttp/security/advisories/GHSA-cq5v-8q36-5273) |
| click 8.3.1 → 8.3.3 | 1 | Uvicorn/Flask/araç CLI bağımlılığı; repo pager/editor çağrısı bulunmadı. 8.3.3 pager/editor subprocess shell kullanımını kaldırıyor. [Changelog](https://click.palletsprojects.com/en/stable/changes/#version-8-3-3) |
| cryptography 46.0.3 → kaldırıldı | 7 | Seçili zorunlu parent jose extra'sıydı. HS256 PyJWT geçişiyle resolver kaldırdı; mevcut Gemini API-key/bcrypt yollarında opsiyonel sertifika/TOTP kullanımı bulunmadı. Yeni sertifika/service-account ihtiyacı ayrıca değerlendirilmeli. |
| curl-cffi 0.13.0 → 0.15.0 | 1 | Yahoo transport; eski yfinance üst sınırı düzeltmeyi engelliyordu. yfinance 1.2.1 ile birlikte yükseltildi. [Upstream düzeltme](https://github.com/ranaroussi/yfinance/releases/tag/1.2.1) |
| ecdsa 0.19.1 → kaldırıldı | 2 | Tek parent python-jose. Fixsiz Minerva ECDSA imzalama/keygen/ECDH önkoşulları Rapot'un HS256 yolunda yoktu; paket yine de yeni çözümde yok. [Maintainer açıklaması](https://github.com/tlsfuzzer/python-ecdsa/security/advisories/GHSA-wj6h-64fc-37mp) |
| Flask 3.1.2 → 3.1.3 | 1 | Bot sağlık HTTP servisi. Etkilenen session membership/cache önkoşulu kaynakta bulunmadı; patch uygulandı. [Advisory](https://github.com/pallets/flask/security/advisories/GHSA-68rp-wp8r-4726) |
| GitPython 3.1.46 → kaldırıldı | 26 | Yalnız kullanılmayan Streamlit dalı; uygulama import/giriş noktası bulunmadı. |
| idna 3.11 → 3.18 | 1 | HTTP alan adı ayrıştırma zinciri. Güvenlik minimumu 3.15, yeni dev-only httpx2 ise >=3.18 istiyor; exact 3.18 doğrulandı. [Advisory](https://github.com/kjd/idna/security/advisories/GHSA-65pc-fj4g-8rjx) |
| lxml 6.0.2 → 6.1.0 | 1 | Doğrudan import yok; pandas/Yahoo opsiyonel HTML tabloları için korundu. İlgili XML iterparse/ETCompat yolu repoda bulunmadı. [XXE düzeltmesi](https://pypi.org/project/lxml/6.1.0/) |
| Mako 1.3.10 → 1.3.12 | 1 | Alembic sabit migration şablonları; kullanıcı kontrollü Windows template URI yolu bulunmadı. [Advisory](https://github.com/advisories/GHSA-2h4p-vjrc-8xpq) |
| Pillow 12.1.0 → kaldırıldı | 19 | Streamlit dalı; GenAI/openpyxl yokluğunu destekliyor. Rapot metin analizi ve resimsiz Excel tabloları kullanıyor. |
| protobuf 5.29.5 → 5.29.6 | 1 | yfinance eager pricing_pb2 importu nedeniyle korunur. Nested Any ParseDict kullanımı repoda bulunmadı. 6.x dalının ayrı patch sınırı olduğundan constraint `<6`. [Advisory](https://github.com/advisories/GHSA-7gcm-g887-7qv7) |
| pyarrow 23.0.0 → kaldırıldı | 1 | Streamlit dalı; repo Arrow/Parquet/Feather kullanmıyor, pandas yokluğunu destekliyor. |
| pyasn1 0.6.2 → 0.6.4 | 4 | Google-auth ASN.1 zincirinde kalır; jose kaldırılması bunu kaldırmaz. Sertifika saldırı önkoşullarının mevcut API-key yolunda erişilebilirliği kanıtlanmadı. [Paket kaydı](https://pypi.org/project/pyasn1/0.6.4/) |
| pydantic-settings 2.12.0 → 2.14.2 | 1 | Ana/middleware ayarları; NestedSecretsSettingsSource veya secrets_dir kullanılmıyor. [Symlink önkoşulu](https://github.com/advisories/GHSA-4xgf-cpjx-pc3j) |
| pytest 9.0.2 → 9.0.3 | 1 | Yalnız geliştirme/CI; geçici dizin kullanan gerçek test tabanı. [Advisory](https://github.com/advisories/GHSA-6w46-j5rx-g56g) |
| python-dotenv 1.2.1 → 1.2.2 | 1 | Ortam okuma; etkilenen set_key yazımı kaynakta bulunmadı. [Advisory](https://github.com/advisories/GHSA-mf9w-mj56-hr94) |
| requests 2.32.5 → 2.33.0 | 1 | BIST/haber ve SDK HTTP istemcisi; extract_zipped_paths özel çağrısı bulunmadı. [Advisory](https://github.com/psf/requests/security/advisories/GHSA-gc5v-m9x4-r6x2) |
| soupsieve 2.8.3 → 2.8.4 | 2 | BeautifulSoup/Yahoo dalı; kullanıcı kaynaklı selector işleme bulunmadı. [Regex DoS](https://github.com/advisories/GHSA-836r-79rf-4m37), [bellek tüketimi](https://github.com/advisories/GHSA-2wc2-fm75-p42x) |
| Starlette 0.50.0 → 1.3.1 | 5 | İki ASGI uygulaması. StaticFiles/HTTPEndpoint/form ayrıştırma kullanılmıyor; auth oluşturulmuş URL yerine route Depends üzerinden. Bozuk Host ile yetki atlanmadığı ağsız sınandı. [1.3.1 düzeltmesi](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq) |
| Streamlit 1.53.0 → kaldırıldı | 2 | 215 takipli Python kaynak/import ve canonical giriş incelemesinde tüketici yok. Kullanılan dashboard Next.js. |
| Tornado 6.5.4 → kaldırıldı | 8 | Streamlit dalı; PTB webhooks extra'sı seçili değil, run_webhook kullanılmıyor. |
| urllib3 2.6.3 → 2.7.0 | 2 | requests üzerinden HTTP; özel proxy/streaming önkoşullarının erişilebilirliği kanıtlanmadı. [Advisory](https://github.com/urllib3/urllib3/security/advisories/GHSA-mf9v-mfxr-j63j) |
| Werkzeug 3.1.5 → 3.1.6 | 1 | Flask örtük /static rotası safe_join yolunu açıyor; yalnız explicit import aramak yeterli değil. Mevcut static dizini yok, üretim Linux; Windows geliştirme önkoşulu ayrı değerlendirildi. [Advisory](https://github.com/pallets/werkzeug/security/advisories/GHSA-29vq-49wr-vm6x) |

**Çözüm kapsamı:** 17 etkilenen paket yükseltildi, 7 etkilenen paket kullanılmayan bağımlılık dallarıyla kaldırıldı. Bunların yanında uyumluluk için FastAPI **0.133.0**, yfinance **1.2.1** seçildi; diğer eski pinler korundu. FastAPI'nin önceki Starlette üst sınırı nedeniyle yalnız transitif patch yeterli değildi; [0.133.0](https://github.com/fastapi/fastapi/releases/tag/0.133.0) Starlette 1.x desteği getiriyor. Resolver toplam **20 paketi** çıkardı ve **7 aktif paket** ekledi; Windows/Linux hedefinde 128 → **115** aktif paket. Yeni `rich/markdown-it-py/mdurl` curl-cffi'dan; PyJWT auth'tan; httpx2/httpcore2/truststore yalnız test istemcisinden geliyor. Streamlit dalındaki ortak protobuf/Jinja2/MarkupSafe/attrs/tenacity/blinker/click korunur; transitif paketler elle silinmedi.

**JWT davranışı:** `api/auth.py` artık extrasız **PyJWT 2.14.0** kullanır; sabit HS256 ve zorunlu `exp` korunur. Yeni anahtar üretilmedi veya mevcut secret değiştirilmedi. Eski jose 3.5 ile önceden üretilmiş sentetik token kabulü, bağımsız HMAC doğrulaması ve bozuk/yanlış imzalı token reddi test edildi. `exp == now` ve gelecekteki `iat` artık reddedilir; uygulama yalnız sub/exp üretir. Bozuk sayısal claim'in TypeError/OverflowError ile 500 oluşturması engellendi. [PyJWT sürüm notları](https://pyjwt.readthedocs.io/en/stable/changelog.html), [API](https://pyjwt.readthedocs.io/en/stable/api.html).

**Test/şema uyumu:** Starlette'in desteklenen TestClient yolu için dev-only **httpx2 2.12.0** eklendi; daha eski sürümlerde advisory bulunuyor. SDK'ların httpx 0.28.1 yolu korunur. Kök conftest iki HTTP/async transport'u da engeller; custom ASGI/Mock transport çalışır. [Starlette kaynak](https://github.com/Kludex/starlette/blob/1.3.1/starlette/testclient.py), [httpx2 düzeltmesi](https://github.com/pydantic/httpx2/security/advisories/GHSA-8xx6-hgc6-gc2m). İlk adayda 678/679 geçti; tek hata otomatik ValidationError şemasına eklenen optional ctx/input alanları, tek uyarı eski test istemcisi yolu idi. Snapshot yalnız bu iki alanla güncellendi; gerçek 422 yanıtıyla ve recursive farkla doğrulandı. Domain/endpoint/request sözleşmelerinde başka fark yok. **Son tam koşum: Python 3.12.8 / pytest 9.0.3, 710/710 uyarısız, 74,53 saniye.** 68 yeni kabul vakası: JWT 34, HTTP/şema 28, gerçek Yahoo parser/Excel/HTML 3, httpx2 izolasyon 3. Yalnız sentetik veri ve geçici DB kullanıldı; SDK transportları ağsız mock, gerçek sağlayıcı/AI/borsa çağrısı yok. Frontend kaynakları değişmedi; bu tur yerel frontend build tekrarlanmadı, Linux CI tüm frontend ve container kontrollerini çalıştıracak.

**Dosyalar:** `requirements.txt`, yeni `requirements-security.txt`, `requirements-dev.txt/lock`, Dockerfile ve CI cache girdileri; `api/auth.py`; `conftest.py`, izolasyon ve üç yeni regresyon dosyası; OpenAPI snapshot, README/AGENTS ve bu belge. Docker runtime, test paketlerini kurmaz: uygulama requirements'ı exact lock constraint'iyle çözer. Test ortamı önce Git dışında aday venv ile kuruldu; 710 testten sonra tek geliştirme ortamı `.venv` aynı lock'a eşitlendi; kurulu 115 paketin adı/sürümü exact lock ile birebir ve `uv pip check` temiz. Önceki lock Git'te ve aday başlangıç kayıtlarında korunur.

**Güvenlik kabulü:** Son adayın 115 aktif exact pini pip-audit 2.10.1 raporuyla birebir karşılaştırıldı; **115/115, 0 etkilenen paket, 0 bilinen advisory**. Ignored kanıt `runtime-data/p1g1-final-candidate-audit.json`; Windows marker kapsamı, ağ/gerçek servis testleri değil. Bu sonuç gelecekteki açıklar, OS/npm paketleri veya tüm uygulama güvenliği için garanti değildir. Tam takipli **218 Python dosyası** Ruff lint/format geçti. Bandit 218/218, **1.549 bulgu = 1.534 LOW + 15 MEDIUM, HIGH=0**; ek LOW kayıtlar yeni test kaynaklarıyla birlikte raporlanıyor, ayrı kaynak bulguları ve report-only politikası bu dependency işiyle kapanmaz; CI araç/eksik kapsam hatalarında hâlâ başarısız olur.

**İlk üretim kapasite engeli (tarihsel ölçüm):** 11 Eylül **19:44:40 UTC** salt okunur ölçüm: root dosya sisteminde **872.407.040 bayt** boş; ikinci uygun kalıcı dosya sistemi yok, Docker build cache **0**. Containerd hem compressed blob hem açılmış snapshot tutuyor; eski pip katmanı 659.689.472 bayt açılmış + 189.789.015 bayt sıkıştırılmış. Yeni lock bu katmanı baştan oluşturur; kullanılmayan paketler yeni imajı küçülttüğünde eski imajın alanı kendiliğinden geri gelmez. Bütün yedek/imaj/release korunurken, 400 MiB serbest rezerv + yeni yedek/source + yeni compressed/açılmış katmanlar + 128 MiB çalışma payı kontrolü gerekir. **2 GiB toplam boş alan** yalnız planlama tabanı; mevcut duruma göre ~1,188 GiB ek alan gerektirir ve gerçek OCI boyut kontrolünün yerine geçmez. `runtime-data/p1g1-capacity.json` ölçüm/formül kanıtı. Pull, cleanup, ücretli resize, migration veya deploy yapılmadı; kapasite kanıtı olmadan eski 600 MiB precheck eşiği kullanılamaz.

**11 Eylül yayın ilerlemesi:** `ccd61544ede603eb064d871a4ec797c5057307f4` commit/push tamam. [CI 34641121926](https://github.com/Rapto0/Rapot/actions/runs/34641121926) tüm joblarla başarılı; Linux Python 3.12.14 üzerinde 710 test/208,30 saniye, warning yok; frontend ve Docker import/sinyal-feed/boş PostgreSQL migration/startup/HTML-JS kabulü geçti. CI security artifact 10279609852, zip SHA256 `d5783d5fcc9d7bfc22a461e35257fde13aa4bd228db895e8f12a7326ba1c3003`; kaynağı ve Linux marker'ları yerelde yeniden doğrulandı: 115/115 sıfır advisory, Bandit218/218 HIGH0/MEDIUM15/LOW1534. [İmaj yayını 34641767731](https://github.com/Rapto0/Rapot/actions/runs/34641767731) başarılı. Yeni backend digest `sha256:0a92fc448e73134d82450c277219d2db82776ec6c9d4aa36c5a6ed5b7665ee39`, frontend digest `sha256:80145f4222058ef16e3dcc73a1f7dd002d07593d42db3c94dc57a73e76a5bda4`; ikisinin kaynak etiketi `ccd61544` olarak doğrulandı.

**İmaj ölçümü:** Yayımlanan OCI blob SHA256 ve açılmış tar diffID'leri doğrulandı. Yeni backend ilk 6 katmanı paylaşır; üç yeni katman için 135.577.236 bayt sıkıştırılmış içerik ve 496.926.720 bayt ihtiyatlı açılmış alan bütçesi gerekir. Frontend 13/13 katmanı önceki imajla aynıdır; yeniden katman indirme/açma maliyeti yoktur. İki imajın manifest/config payı 23.164 bayt. Önceki yedek boyutu 135.495.129 ve gerçek yeni kaynak upload+açılımı 50.144.967 bayt, 400 MiB rezerv ve 128 MiB büyüme payıyla toplam boş alan gereksinimi **1.371.815.344 bayttan fazla**; 19:44 ölçümüne göre yaklaşık **476 MiB** eksik. `runtime-data/p1g1-image-capacity-result.json` immutable imaj ölçümünü kaydeder. Bu, gerçek dosya sistemi tahsisi garantisi değildir; taze yedek/kaynak işlemleri sonrasında ve her pull öncesinde kalan imaj maliyetiyle boş alan yeniden ölçülür.

**Kullanıcı kapasite kararı:** DigitalOcean panelinde mevcut 1GB RAM/25GB disk/$6 aylık plan ve 2GB RAM/50GB disk/$12 seçenek doğrulandı. Kullanıcı **“Hayır, ücretli yükseltme yapma”** dedi. Hazırlanan seçim Cancel ile iptal edildi; ücret/plan/kapanma değişimi yok. Ücretsiz alan çözümü için üç eski yedeğin özel bilgisayar kopyaları doğrulandı; sunucu dosyası silme/otomatik temizlik yetkisi varsayılmıyor.

**Ücretsiz kapasite hazırlığı — 11 Eylül 20:21:19 UTC:** Aşağıdaki üç eski arşiv, fiziksel `C:\Users\memet\RapotBackups\20260911-p1g1-cold` klasörüne kopyalandı. Bu konum OneDrive/Temp/Codex paket cache'i dışındadır. Her gzip'in önce/sonra sunucu SHA256/stat bilgisi aynı; üç gzip CRC ve açılmış üç SQLite `integrity_check=ok` geçti. Altı yerel dosyanın SHA256'sı ikinci kez bağımsız karşılaştırıldı. İki klasör/altı dosyada yalnız kullanıcı+SYSTEM erişimi doğrulandı; gerçek veri Git'e veya rapora alınmadı. Doğrulama manifesti `runtime-data/p1g1-cold-archive-verification.json`, SHA256 `feb1bc65a6f044533c2cbb3d45262350e67384d6c182074287925acaa87217fb`; özel klasörde de `verification.json` kopyası korunur.

| Silme onayı istenen sunucu kopyası | Sıkıştırılmış boyut | Doğrulanan SHA256 |
|---|---:|---|
| `/root/rapot-ops/20260909-8f60f8e/db-backup/trading_bot.db.gz` | 229.557.912 B | `ec78967348ddc67f02bc2e0e47533f3be7dc7d483c1d103bd7bf3f939c0d87e5` |
| `/root/rapot-ops/20260910-fce5d01/trading_bot.before.db.gz` | 190.509.245 B | `02e33bc40978f86e003faf475bd5d11956927683e634158376a8cca162eece8d` |
| `/root/rapot-ops/20260910-p15/trading_bot.before.db.gz` | 186.493.190 B | `75e14668bab9660502eae172e52ec22737a22bbc526d7a4fdfbc19f53baa621a` |

Üç arşiv farklı inode/nlink1; fiziksel ayrılmış alan toplamı **606.580.736 bayt (~578,48 MiB)**. 20:20:39 UTC güncel boş alan **868.999.168 bayt**; üç kopyanın kaldırılması öngörülen alan ihtiyacını karşılayabilir, gerçek boş alan yeniden ölçülmeden pull yapılmaz. **Bu, 20:21 doğrulama anının kaydıdır; sonraki kullanıcı devam onayı ve 20:39:55 kaldırma sonucu aşağıdadır.** Güncel P2-3 SQL gzip yedeği, P1-6 r2/r3/r4 yedekleri ve tüm eski imaj/release'ler bu işlemin dışındadır. P1-6 üç yolu zaten aynı inode'a bağlı olduğundan bunlarda ek tekilleştirme alan kazandırmaz.

**Ücretsiz alan işlemi — 11 Eylül 20:39:55 UTC:** Kullanıcının doğrudan devam talimatı ve tam manifest hash'ine bağlı ayrı onay kaydıyla yalnız yukarıdaki üç sunucu kopyası kaldırıldı. Altı yerel dosyanın hash/boyut ve sekiz yolun ACL kontrolleri 20:38:48 UTC'de yeniden geçti. Sunucuda tüm üç dosyanın SHA/stat bilgisi silme öncesi tekrar doğrulandı; adım kayıtları `/root/rapot-ops/p1g1-cold-retirement-5e4659d7a3e64888ae7405e9062680a0/` içinde korunur. Ayrılmış alan 606.580.736 B; eşzamanlı sistem yazıları dahil **gözlenen gerçek boş alan artışı 606.547.968 B**. Boş alan 867.319.808 → **1.473.867.776 B**. Son kontrolde üç yol yok, P2-3/P1-6 yedekleri var; servis veya veri tabanı değişikliği yapılmadı. Önceki immutable kopya manifestindeki `server_files_retained=true` tarihsel doğrulama anını anlatır; güncel silme sonucunun yerine geçmez. Taze SQL gzip yedeği başlatıldı; bağımsız yerel restore ve her pull öncesi kalan maliyete göre disk kontrolü gerekli.

**Operator hazırlık kanıtı:** Üç sabit arşiv için ayrı kullanıcı onayı ve manifest hash'ini zorunlu kılan silme yardımcısının 12 sentetik kontrolü geçmişti; sonraki gerçek üç dosyalı silme sonucu yukarıda ayrı kayıtlıdır. Dağıtım yardımcısı yeni imaj ölçümünü hash ile bağlar: taze yedek/kaynak zaten diskteyken ilk pull öncesi **>1.186.175.248 B**, backend doğrulandıktan sonra **>553.661.268 B**, iki imaj tamamlanınca **>553.648.128 B** boş alan ister. 15 sentetik kontrol/Python3.10 AST/Ruff ve bağımsız inceleme geçti; kapasite kapıları gerçek Docker disk zirvesi kabulü değildir. Kaynak hazırlayıcıdaki eski P2-3 OPS kontrolü yükleme öncesi düzeltildi; arşiv SHA/Git ve gerçek iki arşiv farkı aynı 17 dosya, yedek/yerel doğrulama/hazırlama/dağıtım dosya sözleşmeleri uyumlu. Bu ilk hazırlık denetimini taze yedek/restore, kaynak hazırlama, pull ve uygulama geçişi izledi; son sonuç aşağıdadır. Auth kabulü eklenince dağıtım yardımcısının 20/20 ve ayrı auth yardımcısının 15/15 sentetik kontrolü geçti; auth başarısızlığı mevcut uygulama rollback akışına bağlıdır.

**Güvenlik raporlarının kalıcı yayını — 21:04:04 UTC:** Exact kod CI artifact’inin 8 raporu ve indirme kanıtı olmak üzere 9 dosya, byte-byte hash karşılaştırmasıyla `/root/rapot-ops/20260911-p1g1/security-reports/` altına aktarıldı. `security-publication.json` verified; arşiv SHA256 `71f9550876f2d11c4e2f11c1ac883a6e17c681499d2f44cee38bbdc4de73b883`, manifest SHA256 `bb9df76df1e35e519d3910a93311a2eb356c2b075e95e657bfb893afbb7250d9`. 115 exact paket/sıfır advisory ve Bandit218/15MEDIUM/1534LOW sonuçları korunuyor. Bandit’teki 4.933 kod satırı exact commit ile eşleştirildi; bu yeniden güvenlik taraması veya kapsamlı sır taraması değildir. Gerçek DB/env/anahtar dosyası arşive eklenmedi; saklama GitHub’ın 14 günlük artifact süresinden bağımsızdır.

**Taze yedek ve bağımsız restore:** 20:40:45 UTC sabit SQLite read transaction’ından 390,43 saniyede SQL gzip alındı: **135.547.494 B**, SHA256 `0d3036738f5acc171eca64a996849e709afd1312c0ab80543426d06a361a5e5c`; SQL 830.835.689 B/1.921.728 ifade, SHA256 `d7bb1fc45e8a78df8027ff8666b19c4de125ac60200d356bf371042a24a4f097`. Özel yerel kopya `C:\Users\memet\AppData\Local\Temp\rapot-p1g1-backup` altında bağımsız geri yüklendi: 1.019.871.232 B, raw SHA256 `d27927f733bf91f040803f3a16af276c8ba23777bea73a78c3de6fa119356e87`. 61,75 saniyelik restore/karşılaştırmada integrity, şema/pragma ve 7 tablonun typed içerik fingerprint’leri eşleşti; `lost_and_found` 162.156 kayıt dahil. Raw dosya hash/boyutunun üretim dosyasıyla aynı olması beklenmez. Yerel kanıt SHA256 `1ffa342e76d22d220828bcd01a1c51384933fa92d2330552fc1627606665099d` sunucu hazırlığına bağlandı. PostgreSQL custom dump 59.240 B, SHA256 `599993412c9b28dd21a2a14ab81eb27106569fad0459d374842e778e01c5fa71`; 66 satırlık katalog kontrolü geçti, bağımsız PG restore yapılmadı.

**Üretim kabulü — 20:56:32 UTC:** `/root/rapot-ops/20260911-p1g1/deployment.json` status `verified`, SHA256 `f3d9444edf4484b4f42e81508b9425823f24b4af599af42218629e21f3a15fc2`. API/bot/middleware/frontend doğru `ccd61544` digest’lerinde, PostgreSQL aynı konteyner/başlangıç kimliğinde; beşi healthy/restart0. API başlangıcında ve bot sonrası ana sayılar aynı: signals **1.733.137**, trades/orders **0/0**, scan_history **6**, ai_analyses **26.393**, bot_stats **4**. PG **135/135/28/383** korundu. Manuel initializer/migration, DB restore veya yeni kullanıcı oluşturulmadı; credentials/Nginx, DRY_RUN/trading=false/live=false ve AI kapalı durumu değişmedi.

HTTPS API health 47 ms/200; `/`, `/signals`, `/alarms`, `/chart` HTML/200; SignalFeed ready ve Binance/BIST sağlayıcıları başladı. Scheduler **47,298 saniyede unknown → running**; `data_available=false` başlangıç durumu görüldü, yeni tam tarama/yük/etkileşimli tarayıcı kabulü yapılmadı. Ayrı Windows HTTPS API ve bot kontrolleri 203 ms/200 geçti. **Auth 13/13:** sağlık; anonim/geçersiz bearer ile me/admin 401; tokensız/geçersiz tokenlı boş webhook 401; mevcut admin/user login ve me 200; admin için `logs?limit=0` validasyon 422, normal kullanıcı için 403. Parolalar/token’lar yalnız RAM’de kullanıldı, sonuçlarda saklanmadı. Üretimde yeni token ile giriş/yetki doğrulandı; eski jose token devamlılığı üretimde ayrıca denenmedi, legacy token uyumluluğu yerel/Linux test kanıtıdır.

**Kapasite sonucu ve kalan sınırlar:** Pull öncesi 1.285.820.416 B > 1.186.175.248 B; backend sonrası 718.499.840 B ve frontend sonrası 718.401.536 B, kalan maliyet/rezerv kapılarını geçti. Kabul sonrası boş alan **724.676.608 B (~691 MiB)**. Backend/frontend indirmesi sırasıyla 23,413/1,695 saniye; eski geri dönüş imajları ve kaynakları korundu. Bunlar kontrol noktası ölçümleridir, sürekli ölçülmüş disk zirvesi değildir. Kullanıcı ücretli yükseltmeyi reddetti; sonraki deploy öncesinde disk yeniden bütçelenmeli, başka yedek/imaj silme yetkisi verilmiş sayılmaz. P1-G1 kapandı; P2-4/P3, Bandit MEDIUM/LOW borcu ve ertelenen gerçek TradingView alarm/testnet/emir kabulü açık. Son belge commit/CI ve canonical blob aktarımı aynı OPS’taki `documentation-release-record.json` kaydında ayrı tutulur; uygulama imajını yeniden yayımlamaz veya restart gerektirmez.

### P2-4 — Eşzamanlı API yükünde realtime gecikmesi

**Durum — 13 Eylül: Doğrulandı.** İlk `aadde728` sürümü sağlık/auth kabulünden geçti fakat etiket listelerinde zaman aşımı verdi. SQL devamı `279aa9f`, 735 Python testi ve ayrı büyük veri ölçümünden sonra CI/imaj ve ikinci üretim kabulünü geçti. Aynı süre sınırlarıyla 24 REST ve üç WSS bağlantısı tamamlandı; üç uygulama heartbeat'i alındı. Önceki erken kapanış ve başarısız ölçümler tarihsel kanıt olarak aşağıda korunur. Ham koşum kaydı/kodu bulunamayan eski p95 değerleri kabul kanıtı değildir. Kabul sınırlı örneklem içindir; devamlı yük/SLA ve gerçek sinyal/emir teslimatı garantisi vermez.

**Tarihsel tetikleyiciler:** P1-5/P1-6'da UI yüküyle üç WS handshake yaklaşık 7,5 saniyede timeout oldu; sekmeler kapatılınca aynı kontroller geçti. P1-6 ilk yayının 20s health timeout/499 sonucu rollback gerektirdi. Senkron COUNT kullanan sağlık yolu `2cf05a8` ile tek-session/LIMIT0 şema probe'u ve thread offload'a taşındı. Sonraki 0,029–0,048s health, 30,250s heartbeat ve 11 Eylül 15s timeout → yaklaşık 45ms/200 gözlemleri farklı yük/önbellek koşullarındadır; tek başlarına kök neden veya performans kabulü değildir. Chart'ın ilk gözlemde boş, sonraki tekrarda 1.000 mum göstermesi ve scheduler'ın 43–47 saniyede hazırlanması da ayrı başlangıç gözlemleridir.

**İncele → düzelt (`98b8922`):** `api/main.py` içindeki signals, signal detail, trades ve stats servis çağrıları `asyncio.to_thread` ile worker'a taşındı. Repository stats altı ayrı sorgu yerine tek SQL çağrısı kullanır; içindeki scalar alt sorgular nedeniyle tek tablo taraması iddia edilmez. Header dört strateji/etiket sorgusu yerine iki etiket sorgusu yapar. Piyasa sağlayıcıları zaten thread/async kullanıyor; doğrudan event-loop bloklayıcısı diye sınıflandırılmadı.

**13 Eylül regresyon düzeltmesi:** `transformSignal` bilinmeyen stratejiyi COMBO'ya normalleştirdiği için dönüşüm sonrasındaki filtre LEGACY kayıtlarını kabul ediyordu. `use-signals.ts` artık ham API kaydını dönüşümden önce filtreler. Yeni test eski kodda 4/3 numaralı geçersiz kayıtları döndürerek başarısız oldu; düzeltme sonrasında yalnız 2/1 numaralı HUNTER/COMBO kayıtları kaldı. İki sorgu paralel başlar, ID ile tekilleştirme/tarih sıralaması ve hata aktarımı korunur. Liste artık etiket başına en yeni kayıtlardan oluşur; önceki strateji başına kotayı garanti etmez. Bilinmeyen stratejiler elendiğinde liste limitten kısa olabilir; bu bütün geçmişin abonelik veya teslimat garantisi değildir.

**Kalıcı doğrulama — Python 3.12.8 / Node 20.20.2:** Tam Python paketi **722 passed / 1 skipped**, uyarısız (76,64s); skip yalnız opt-in performans koşumudur. Frontend **99/99**, ESLint, incremental kapalı TypeScript, Next production build ve standalone HTTP/WS/proxy kabulü geçti. 115 paket `uv pip check` uyumlu; değişen Python dosyaları Ruff lint/format temiz. `tests/test_api_read_concurrency.py` dört REST yolu × başarı/hata/iptal olmak üzere 12 geçici SQLite vakası içerir. Gerçek SQL işlemi beklerken aynı loop'taki health ve bellek içi WS accept/broadcast ilerler; SQL döndüğünde session transaction ve pool kullanımı sıfırlanır. Caller iptali çalışan SQLite işlemini anında kesmez; worker döndüğünde oturum kapanır. `frontend/tests/special-notifications.test.mjs` gerçek normalizer ile ham strateji/etiket reddini, iki paralel sorgu/birleştirme ve başarısız sorguyu kapsar; npm test'e eklendi.

**Tekrarlanabilir ölçüm — 13 Eylül 06:20 UTC:** `tests/performance/test_api_read_benchmark.py`; Python 3.12.8/Windows, 1.750.000 sentetik sinyal +25.000 karma trade, 20 tekrar ve ısınmış önbellek. Dalga: health, iki piyasa ×150 sinyal, iki özel etiket ×50 sinyal, detail, trades50 ve stats; aynı loop'ta üç ASGI WS. Socketler REST dalgası bitene kadar açık; 5ms loop pulse ve 20ms planlanmış yayın/alım örneklenir. Queue'ya birlikte girişten HTTP bitişine/WS kabulüne ölçülür; yüzdelikler nearest-rank. Rate limiter ölçümde kapalıdır, normal sınırlara ait testler ayrıdır.

| Ölçüm (3 WS +8 REST) | p95 ms | Koşudan önce seçilen sınır |
|---|---:|---:|
| health | 9,297 | <250 |
| BIST / Kripto sinyal listesi | 16,569 /17,827 | <500 |
| BELES / COK_UCUZ listesi | 410,189 /314,611 | <500 |
| Sinyal detayı / trades / stats | 12,126 /30,743 /124,321 | <500 |
| WS handshake (60 örnek) | 7,831 | <250 |
| Sürekli WS yayın/alım (1.458 örnek) | 7,616 | <250 |
| Sürekli loop gecikmesi (1.849 örnek) | 10,438 | <250 |

Repository p95 (ayrı sıcak seri): list50 **0,538ms**, detail **0,301ms**, trades50 **18,091ms**, stats **80,338ms**. Mevcut SQL üzerinde yalnız API thread offload'unu kaldıran inline modelde (health dahil) WS handshake p95 **665,334ms**, loop **660,281ms** oldu. Bu aynı mevcut sorguların zamanlama karşılaştırmasıdır; eski Git checkout'u veya VPS kök nedeninin birebir tekrarı değildir. Yapay SQL başına20ms bekleme ile threaded WS handshake/iletim/loop p95 **5,430 /7,911 /9,745ms**; aynı <250ms sınırları geçti. Inline önce/threaded sonra sabit sıra ve sentetik veri dağılımı sınırları korunur; bunlar üretim SLA'sı değildir.

Nihai koşum **1 passed /59,17s**, bütün performans kabul alanları true; geçersiz limitler422, yedi sinyal filtresi, trade filtresi, kayıp detail404, karma stats, reconnect ve boş connection pool doğrulandı. Görevler hata halinde de cancel/drain edilir; çalışan SQL executor'u engine kapatılmadan beklenir. İlk v1 ölçüm yalnız başlangıç WS/loop davranışını kapsıyordu; tam dalga kanıtı olarak kullanılmıyor ve ayrı saklandı. Nihai ham çıktı `runtime-data/p24-benchmark-v2.log`, SHA256 `a15323b10bdf288d40cea9e77572f919764af91cb098c1b54ec90f0a575d33a9`; JSON `runtime-data/p24-benchmark-v2.json`. Test edilen dosyanın fiziksel SHA256'sı `99195e0f51c76f2d06cd0e7cd94faee61ac8c2b8956f1727ae6682aa7073af37`. Kalıcı kopya, canonical Git blob hash'leri ve exact CI/imaj sonucu `/root/rapot-ops/20260913-p24/` yayın kaydında ayrıca tutulacak.

Tekrar komutu: PowerShell'de `$env:RAPOT_RUN_API_BENCHMARK='1'`, sonra `.venv/Scripts/python.exe -X utf8 -B -m pytest tests/performance/test_api_read_benchmark.py -q -s`; bitince `Remove-Item Env:RAPOT_RUN_API_BENCHMARK`. Normal pytest bu maliyetli ölçümü atlar. Gerçek TLS/Nginx/Binance, üretim data kopyası ve etkileşimli tarayıcı bu koşumda yoktur. Üretimde kontrolsüz yük testi yapılmayacak; yeni imaj/yedekten önce kapasite kapısı geçmelidir.

**13 Eylül kapasite ön kontrolü:** 06:07:10 UTC'de beş servis healthy/restart0; disk **629.194.752 B (600,05 MiB)** boş. Sabit 400 MiB rezerv +128 MiB büyüme payından sonra **75.546.624 B** kalıyor. Son yedeğin 135.547.494 B ve önceki source upload/extract'ın 50.086.809 B boyutu vekil alınırsa yeni imajlar hariç bile >739.282.431 B gerekir; yeni exact imaj maliyeti henüz ölçülmedi. Kalıcı journal metadata toplamı 2.558.750.720 B, uygulama container logları yalnız 2.093.056 B. Ölçümler disk kaybının tamamını tek bir kaynağa bağlamaz. Ücretli resize, pull, servis değişikliği veya dosya silme yapılmadı. Kanıt Git dışındaki `runtime-data/p24-capacity-readonly.json` içindedir.

**Ücretsiz alan hazırlığı — silme yapılmadı:** 13 Eylül 06:16:20 UTC'de yalnız 1 Eylül öncesi **12 ARCHIVED system journal** dosyasının kalıcı bilgisayar kopyası doğrulandı. Gerçek header kayıtları 6–28 Ağustos; Eylül ve aktif `system.journal` hariç. Sunucuda ayrılan toplam **906.018.816 B (~864,05 MiB)**; yerel gzip tar **162.537.514 B**, SHA256 `7bcc55781fec5e9b863bae157d39310cb8c7a69c8cdb244ec429f9519555adcc`. Tam sabit dosya listesi/iki taraflı üye hash'leri `C:\Users\memet\RapotBackups\20260913-p24-journal\verified-copy-manifest.json` içinde; manifest SHA256 `046a20bfd4156239e3e7597702b55c791aa78611b044feb1b8d124250b00f400`. Gzip CRC/footer, üye boyut/SHA, yeniden okunan sunucu inode/mtime/ctime/ARCHIVED state ve özel klasörün yalnız kullanıcı/SYSTEM/Administrators ACL'i geçti. Sunucuda büyük geçici arşiv oluşturulmadı. **Bu kopyanın alındığı anda orijinaller sunucudaydı; silme yapılmamıştı.** 13 Eylül kullanıcı onayı sonrası aşağıdaki dört dosyalık işlem ayrıca doğrulandı; kalan sekiz sunucu dosyası korundu. Bu kopya yeni imajın sığacağını tek başına kanıtlamaz; exact katman bütçesi ve somut silme kararı ayrıca gereklidir.

**Commit / uzak doğrulama — ilk P2-4 sürümü:** `aadde728f7e83a636b9493b660fed33434564e9a` main'e push edildi. [CI 34742590742](https://github.com/Rapto0/Rapot/actions/runs/34742590742) Python, frontend, lint, report-only güvenlik ve Docker kabulüyle başarılı. Bunun ardından exact kaynak için [imaj yayını 34742865556](https://github.com/Rapto0/Rapot/actions/runs/34742865556) başarıyla tamamlandı; yayın/pull/üretim kabulü birbirinin yerine geçmez. Kaynak Git arşivi 23.888.014 B, SHA256 `438283331199bbe2f245e5d20041f55e44d30739fef5f985786cf9a2b06b07b8`; upload+açılmış tahmini kaynak alanı **53.399.694 B**. Salt okunur registry ölçeri hem backend/frontend için sıkışık blob hash'i, açılmış diff-ID ve ortak parent-chain'i denetler; 400+128 MiB pay değişmez. İlk geçişin taze yedek ve boş alan sonuçları aşağıdadır; ikinci geçiş için bunlar yeniden ölçülmelidir. Son imaj/kapasite sonucu ve yalnız bu belgenin sonraki commit/CI/canonical hash kanıtları aynı OPS'taki `release-record.json` içindedir; belgenin kendi hash'ine referans döngüsü oluşturulmaz. Bu yalnız belge aktarımında uygulama/config/pointer korundu; sonraki uygulama geçişi ayrı `p24-deploy` kaydındadır.

**Dosyalar / kapsam / bağımlılık:** `api/main.py`, `infrastructure/repositories/signal_trade_repository.py`, `frontend/src/lib/hooks/use-signals.ts` ve concurrency/bildirim/performans testleri. SQL devamında `models.py`, `db_session.py`, `tests/test_signal_tag_index.py` ve `tests/test_trade_stats_contract.py` eklendi. Kapsam orta; P1-5 taşımacılığı tamam. İkinci üretim geçişi, ek indeksin oluşturma alanı/süresi, taze yedek ve yeni kaynakla eşleşen yayın kanıtına bağlı.

**Kabul:**

- [x] Sorgu süreleri ve event-loop/WS etkisi izole aynı koşulda tekrarlanabilir ölçüldü.
- [x] İzole eşzamanlı yükte health/WS için sayısal sınır tanımlandı ve doğrulandı.
- [x] REST sonuçları/filtreler ve hata/iptal sonrası DB session cleanup kalıcı testlerle korundu.
- [x] İzole üç WS bağlantısı her dalga sonunda temizlendi ve yeniden bağlandı.
- [x] Exact sürümle üretim HTTPS/WSS ve kapasite/veri/servis kabulü doğrulandı.

**13 Eylül dört eski günlüğün kaldırılması — doğrulandı:** `four-file-removal-proposal.json` içindeki dört ARCHIVED sistem günlüğü için kullanıcı onayı kaydedildi. Özel bilgisayar arşivindeki 12 üye SHA256/boyut, gzip CRC ve ACL yeniden doğrulandı. Sunucudaki dört dosyanın sabit yol/inode/mtime/ctime/boyut/SHA256/header ve hiçbir süreç tarafından kullanılmadığı silmeden önce kontrol edildi. Sekiz koruma test grubu; son dosyanın hash/header/kimlik veya kullanım kontrolü başarısızsa hiçbir silme yapılmadığını sentetik olarak doğruladı. Yalnız dört dosya kaldırıldı; diğer sekiz günlük, etkin günlükler, uygulama/DB ve geri dönüş kaynakları korundu. Ayrılan alan 302.006.272 B; eşzamanlı günlük yazımları sonrası gerçek boş alan **626.130.944 → 928.104.448 B** (+301.973.504 B, yaklaşık 288 MiB). Beş container kimliği/başlama zamanı/restart, kaynak pointer ve config hash'leri aynı; HTTPS API/bot health **38,645 / 43,213 ms, 200**. Günlük temizliği uygulama kesintisi veya servis restart'ı yapmadı. Onay ve her unlink öncesi/sonrası fsync'li kayıt `/root/rapot-ops/20260913-p24/four-journals-*` altında; özel bilgisayar arşivi korunuyor. Yeni deploy için taze DB yedeği/bağımsız restore ve kapasite kapıları ayrıca tamamlanacak.


**13 Eylül taze yedek — bağımsız restore doğrulandı:** `2026-09-13T06:52:26Z` sabit, salt okunur SQLite transaction'ı; bütünlük, 7 tablonun tip bilgisi içeren veri parmak izleri ve SQL gzip **469,59 saniyede** üretildi. Arşiv **136.000.200 B**, SHA256 `b166920044a9a84ca25bb6800279a10abcf76a486bbb5f8cbe00c035db47d28d`; SQL **833.398.406 B / 1.928.441 ifade**, SHA256 `399561710e2a85a33587fe998fc17e12cd18bce4c1f4b4c6112589b1e069d37e`. Bilgisayarda `C:\Users\memet\AppData\Local\Temp\rapot-p24-backup` özel klasöründe tam restore ve karşılaştırma **71,31 saniyede** geçti; açılmış SQLite **1.023.078.400 B**, SHA256 `4ba8a43db66a25f38b09f5cab181cee13da626e55524effad84d6bd25b7b92c3`. Şema/pragma ve 7 tablonun parmak izleri aynı; signals 1.739.843, scan_history 13, ai_analyses 26.393, lost_and_found 162.156, bot_stats 4, trades/orders 0/0. Bunlar taze snapshot sayılarıdır; 11 Eylül'e göre doğal scanner eklemeleri eski sayılarla eşitlik beklenerek hata sayılmaz. PostgreSQL dump **59.240 B**, SHA256 `b0bd9a6c352f2e419b46a39723791ac7f130700d7fd3c9f6c96b943ff07e4259`; 66 satırlık katalog ve özel bilgisayar kopyası hash'i doğrulandı. PG container kimliği ve 135/135/28/383 sayıları aynı; bağımsız PG restore veya üretim DB restore yapılmadı. İki yedek/manifest ve bilgisayar kanıtları `/root/rapot-ops/20260913-p24-deploy/` hazırlığına hash ile bağlandı.


**13 Eylül ilk üretim geçişi — 07:06:20 UTC:** `aadde728` için CI 34742590742, imaj yayını 34742865556 ve manifest/katman kaynak kimlikleri doğrulandı. Backend `579fc63c…`, frontend `ade5361c…`; dört uygulama aynı kaynakta, PG aynı container ve başlangıç kimliğinde. Beşi sağlıklı, restart sayıları sıfır. Ana sayılar 1.739.843 sinyal, 0 trade, 0 order, 13 tarama, 26.393 AI kaydı ve 4 bot_stats; PG 135/135/28/383 korundu. HTTPS health 24 ms; `/`, `/signals`, `/alarms`, `/chart` HTML 200; feed/sağlayıcılar hazır. Scheduler **56,480 saniyede unknown → running** oldu; auth **13/13** geçti. DRY_RUN/trading=false/live=false ve AI kapalı; eski imajlar, env/Nginx ve geri dönüş kaynakları korunuyor. İlk pull öncesi 739.635.200 B > 692.281.947 B; backend sonrası 688.115.712 B > 638.957.773 B; frontend sonrası 609.660.928 B > 553.648.128 B. Son kabulde boş alan **675.737.600 B**. Bu dağıtımın `deployment.json` sonucu `verified`; aşağıdaki P2-4 performans kabulünü tek başına kapatmaz.

**İlk dış eşzamanlı kabul — başarısız, açık tutuldu:** Üç signals WSS bağlantısı ve sekizer REST isteğinin 0 / 15 / 29,9 saniye dalgaları için önceden seçilen üretim kontrol sınırları: REST p95 < 5 saniye, WS açılışı < 3 saniye, protokol ping/pong p95 < 1 saniye, uygulama heartbeat’i < 35 saniye. Bunlar yerel 250/500 ms hedeflerinin yerine geçmez. İlk yardımcı yalnız genel RuntimeError kaydetti. Hata ayrıntıları eklenen ikinci sınırlı koşumda ilk dalga sağlık 282 ms, WS açılışı 282 ms, protokol ping p95 141 ms ve stats 5.250 ms olarak gözlendi; BELES/COK_UCUZ listeleri 8 saniyelik toplam istek süresinde tamamlanmadı. Üç socket kapandı; kaynak, container ve config’in aynı kaldığı doğrulandı. İlk dalga yarıda kesildiğinden 24 REST isteği ve üç heartbeat kabulü sağlanmadı. Kanıtlar `runtime-data/p24-production-read-acceptance.json` ve `runtime-data/p24-production-read-acceptance-diagnostic.json`; başarısız kayıtlar korunur.

**SQL inceleme / dar düzeltme:** Üretimdeki SQLite 3.37.2 sorgu planı, etiket indeksinde aramadan sonra created_at sıralaması için geçici B-tree kullanıyordu; BELES için 41.297, COK_UCUZ için 46.162 eşleşme vardı. En son 2.000 kayıtta yalnız 23/25 etiket bulundu; sorguyu yakın geçmişle sınırlayarak eski sonuçları eksiltme yaklaşımı kullanılmadı. Özel, bağımsız restore kopyasının ayrı klonunda `idx_signals_special_tag_created(special_tag, created_at) WHERE special_tag IS NOT NULL` indeksi **114.652** satırı kapsadı. Fiziksel artış **4.980.736 B**, yerel oluşturma süresi **864,3 ms**. Etiket okumaları 135,798 / 146,128 ms’den 0,284 / 0,157 ms’ye indi; gerçek ORM sorgu planında geçici sıralama kalktı. Bunlar bilgisayar ölçümleridir; VPS süresi ve alan kullanımının zirvesi ayrıca denetlenir. `models.py` yeni DB, `db_session.py` mevcut DB için aynı indeksi tanımlar. Boş/eski DB, eksik kolon, tekrar başlatma, eski/seyrek/olmayan etiket, birleşik filtre, etiket güncellemesi ve NULL tarih için 9 test geçti. Ana veritabanı SQLite’tır; farklı motorlarda aynı kısmi indeks veya performans sonucu garanti edilmez.

`COUNT(*)` üretimde zaman damgasını kapsayan indeks üzerinden tek başına **4.173 ms** sürdü. NULL ve NULL olmayan etiketlerin iki ayrık, bütün satırları kapsayan sayımını aynı SQL ifadesinde toplamak, etiketi kapsayan daha dar indekslerle **1.520 ms** olarak gözlendi. İki ayrı ölçüm arasında scanner 4 satır ekledi; bu kontrollü A/B veya sabit veri karşılaştırması değildir. Sonuç önbelleğe alınmaz veya tahmin edilmez. Dört yeni parametrik test; boş tablo, NULL/NULL olmayan/karma etiket, boş metin/legacy etiket ve NULL ↔ etiket güncellemesi sonrasında tam sayımı, tek SQL ifadesini ve covering index planını doğrular. İlk hedefli **16/16** ve ardından tam Python **735 geçti / 1 atlandı (74,35 saniye)**. Atlanan test opt-in büyük veri ölçümüdür; aşağıdaki ayrı koşumu geçti. Frontend bu SQL devamında değişmedi; önceki `aadde728` için **99/99**, lint, type-check, build ve standalone kanıtı korunur. Bu yerel doğrulama aşamasında CI ve ikinci geçiş bekleniyordu; aşağıdaki 279aa9f yayın kaydı ikisinin de son kabulünü içerir.

**SQL devamının büyük veri ölçümü — 13 Eylül:** Aynı değişmemiş benchmark, 1.750.000 sentetik sinyal ve 25.000 trade ile **1 geçti / 20,66 saniye** sonucunu verdi; tüm kabul koşulları true. Yeni p95 değerleri: health **8,656 ms**, BELES/COK_UCUZ **15,480 / 15,263 ms**, stats **86,758 ms**, WS açılışı **5,971 ms**, WS yayın/alım **10,084 ms (402 örnek)**, loop gecikmesi **5,371 ms (662 örnek)**. Kanıt `runtime-data/p24-index-benchmark.json` içinde tutulur. Bu yeni SQL devamının yerel ölçümüdür; yukarıdaki v2 sonuçları ilk `aadde728` sürümüne aittir. Üretim eşzamanlı kabulünün yerine geçmez.

**Eşit tarihlerde sıra sınırı:** Mevcut liste sözleşmesi yalnız `created_at DESC` kullanır; aynı created_at değerindeki satırlar için sabit bir ikinci sıra tanımlamaz. Yeni indeksin ters taranması bu satırların sırasını ve LIMIT sınırında hangi eşit tarihli satırların seçileceğini değiştirebilir. Sentetik üç eşit tarihli kayıtta LIMIT 2, indeks öncesi 1/2 ve sonrası 3/2 döndü. Filtre ve en yeni tarih sözleşmesi korunur; eşit tarihlerde birebir aynı liste veya sıra iddia edilmez. Sıralamaya id eklemek ayrı sözleşme değişikliği olarak değerlendirilmelidir.

**İkinci geçişin yedeği ve kapasitesi — doğrulandı:** 07:24:47 UTC sabit SQLite snapshot'ının SQL gzip'i doğrudan özel bilgisayar klasörüne aktarıldı; sunucuda ikinci büyük arşiv oluşturulmadı. **136.013.613 B**, SHA256 `2e7eb8f3b6765be5451333a3c4e494551661cb2964184065d221ed9f0eb299d6`; bağımsız tam restore **69,66 saniyede** şema/pragma ve 7 tablo parmak izini doğruladı. Açılmış DB **1.023.168.512 B**, SHA256 `e9ad6ba5860fec775a9fccfbb909eba6db62c02633815a366f7f8c124ec9c467`. Özel kopya `C:\Users\memet\AppData\Local\Temp\rapot-p24-index-backup` altında; geçiş öncesinde boyut/hash ve klasör erişimi yeniden kontrol edildi. PG dump **59.240 B**, SHA256 `9759990729aad91195135b8550d548ece4e74dff073d91408f4d77b12c73f71e`; katalog ve bilgisayar kopyası doğrulandı, bağımsız PG restore iddia edilmez.

Kaynak arşivi **23.895.019 B** olarak RAM üzerinden aktarıldı; boyut/SHA/CRC, 405 dosyanın canonical hash'i, 128 MiB kullanılabilir bellek kapısı, 256 MiB süreç sınırı ve 60 saniye okuma süresi korundu. Sunucuda kaynak tar arşivi tutulmadı. Yeni backend katmanı için **23.897.921 B** sıkıştırılmış + **29.458.432 B** açılmış planlama alanı ölçüldü; frontend'in 13 katmanı paylaşıldı. 400 MiB rezerv + 128 MiB çalışma payı ve indeks için ayrıca **16 MiB** bütçe azaltılmadı. Kaynak hazırlandıktan sonra ilk kapı **634.781.696 > 623.804.861 B**; backend sonrası **583.245.824 > 570.438.484 B**; frontend sonrası **583.147.520 > 570.425.344 B** geçti. API indeks kabulünden sonra **579.624.960 > 553.648.128 B** kaldı. Bu anlık kontroller tüm zamanların disk zirvesi ölçümü değildir. 32 dağıtım/hazırlık ve 15 auth yardımcı testi geçti; genel temizlik, eski imaj/yedek silme veya ücretli yükseltme yapılmadı.

**İkinci üretim geçişi — 07:44:25 UTC, doğrulandı:** `279aa9fea99b520e661b43f104a2bf4791893ac3` için [CI 34745255161](https://github.com/Rapto0/Rapot/actions/runs/34745255161) beş jobla, [imaj yayını 34745419330](https://github.com/Rapto0/Rapot/actions/runs/34745419330) başarılı. Backend `sha256:9be0fdb6097f52bf97730f44c86d28c24e2c0cea1fe181e7e8fd668177fdb034`, frontend `sha256:e1e3702c591dd7f94793d93e0f1015310013a3233a0430087084db9d79327972`; dört uygulama tam kaynakla eşleşiyor. Beş servis healthy/restart0; ayrı PG aynı kimlik ve 135/135/28/383 sayılarında. Ana yazıcılar durdurulup başlatıldı; öncesi/sonrası **1.740.288 sinyal, 0 trade, 0 order, 13 scan_history, 26.393 AI ve 5 bot_stats** korundu. Şema farkı yalnız `idx_signals_special_tag_created`; üretim DB restore'u veya manuel migration yapılmadı. Başlangıç indeksi eklediğinden bu geçiş “şema değişmedi” diye tanımlanmaz. Önceki kod/imajlar korundu; olası geri dönüş uyumlu indeksi bırakır.

HTTPS health **22 ms**, `/`, `/signals`, `/alarms`, `/chart` HTML 200; feed hazır, Binance/BIST sağlayıcıları çalışıyor. Scheduler kabul gözleminde **19,898 saniyede unknown → running**, auth **13/13** geçti. Bu süre toplam kesinti veya tam tarama süresi değildir. Env/Nginx içerikleri korunuyor; DRY_RUN/trading=false/live=false ve AI kapalı. Son dağıtım kabulünde boş disk **580.993.024 B**. Kanıt `/root/rapot-ops/20260913-p24-index/deployment.json`; hazırlık ve yedek manifestleri aynı dizinde, özel DB içerikleri Git dışında tutulur.

**Son dış eşzamanlı kabul — 07:45:19 UTC, doğrulandı:** Önceki koşumla aynı üç dalga, sekiz REST yolu ve üç signals WSS bağlantısı; **24/24 REST**, üç heartbeat ve tüm süre sınırları geçti. Üretim kontrolü p95: health **313 ms**, BELES **594 ms**, COK_UCUZ **469 ms**, BIST **610 ms**, Kripto/trades/detail **500 ms**, stats **2.438 ms**, WSS açılışı **516 ms**, protokol ping/pong **63 ms (162 örnek)**. Üç uygulama heartbeat'i açılıştan **29,937–30,000 saniye** sonra alındı; biri aktif REST okumasıyla çakıştı. Socketlerin üçü de kapandı; signals kanal sayısı **1 → 1**, source/config/container kimlikleri aynı. Üç örnekli REST p95 burada maksimumla aynıdır; bu küçük örneklem uzun süreli yük/SLA veya sürekli uygulama sinyali teslimi ölçümü değildir. Gerçek alarm ya da emir üretilmedi. `runtime-data/p24-index-production-read-acceptance.json` sonucu `verified`, eşik ihlali yok; aynı isimli kanıt son belgelerle operator dizinine aktarılır. İlk başarısız kayıtlar korunur.

**Belge kapanışı:** Bu plan, `scripts/DEPLOY.md` ve `AGENTS.md` değişiklikleri ayrı belge commit'iyle yayımlanır. Tam belge SHA/CI, canonical Git blob hash'leri ve aktarım öncesi/sonrası değişmeyen çalışma kimlikleri `/root/rapot-ops/20260913-p24-index/documentation-release-record.json` içinde tutulur; `documents-final/` yalnız küçük kanıt ve belgeleri içerir. Belge yayını yeni imaj, servis restart'ı veya veri işlemi değildir. **P2-4 kapandı; sıradaki iş P3-1.**


## P3 — Daha sonra değerlendirilecek işler

### P3-1 — Backtest ve strateji eşdeğerliği

**Neden:** Python, frontend ve Pine hesaplayıcıları ayrı implementasyonlar. Backtest kodunun varlığı performans/strateji doğruluğu kanıtı değil.

**2026-09-09 kaynak bulgusu — henüz düzeltilmedi:** Pine `calcEma()` içindeki 536. satır döngüsünde `n == len`, `calcAtr()` içindeki 549. satır döngüsünde `n == len + 1` iken başlangıç indeksi son indeksi aşıyor; döngü geriye çalışıp ilk değeri fazladan güncelleyebiliyor. `getC/getH/getL` dizi dışı indekslerde gelişmekte olan mum değerine döndüğünden hesaplama sınırı etkileniyor. Bu mevcut bir ilk değer/ısınma sınırı bulgusudur, derleme hatası değildir; P1-3'te strateji değişikliği yapılmadı. Düzeltmeden önce tam sınır ve sınırın bir üstündeki geçmiş uzunluğu için EMA/ATR beklenen değerleri, kapanmış/gelişmekte olan mum ayrımıyla test edilmeli.

**2026-09-10 P2-1 incelemesindeki COMBO bulgusu — 13 Eylül ilk adımında düzeltildi:** `frontend/src/lib/indicators.ts::calculateCombo`, `rsi[i]?.value || 50` ve `wr[i]?.value || -50` ile geçerli sıfır değerini nötr değere çeviriyor. Tekrarlanabilir örnek: `i=0..39`, günlük ISO tarih, `open=high=low=close=100-i`, `volume=1`; gerçek son RSI `0`, W%R `-100`. `minBuyScore=4/minSellScore=4` ile COMBO sonucu `buyScore=3`, `signal=null`, details RSI `50`, MACD `-7`, CCI `-126,666…`. Dört alış koşulundan RSI koşulu bu yüzden kayboluyor. Yerel alarm ve grafiğin ortak hesaplayıcısını etkiler; P2-1 veri/yarış düzeltmesi bu strateji hatasını kapatmıyor. Sonlu sıfır/eksik/NaN ayrımı ve diğer hesaplayıcılarla aynı örnekte eşdeğerlik birlikte test edilmeli.

**Dosyalar:** [backtest](../backtesting_system.py), [signals.py](../signals.py), [frontend indicators](../frontend/src/lib/indicators.ts), [Pine](../middleware/pine/combo_hunter_binance.pine).

**13 Eylül ilk uygulama — COMBO yerel kabulü tamamlandı:** `calculateCombo` içindeki dört `||` varsayılanı `?? NaN` oldu; sekiz puan koşulu yalnız `Number.isFinite` değerleri sayar. Gerçek RSI `0`, Williams `%R = -0` ve CCI/MACD `0` korunur. Eksik, NaN ve sonsuz bileşenler puan üretmez; hesaplanamayan ayrıntılar sahte nötr değere çevrilmez. Varsayılan eşikler, `<26` mum sınırı, çıktı uzunluğu ve iki kota aynı anda sağlanırsa SAT önceliği değişmedi. Hesaplayıcı yeterli sonlu bileşenle sinyal üretebilir; yerel alarmın son kayıttaki bütün bileşenleri sonlu istemesi mevcut, daha sıkı sözleşmedir. Geçersiz/sıfır kullanıcı kotalarının genel doğrulanması veya tüm OHLCV doğruluğu bu değişikliğin kapsamı değildir.

Altı yeni test `frontend/tests/local-alarms.test.mjs` içinde gerçek hesaplayıcı ve alarm tüketicisini kullanır: 40 azalan mumda RSI `0` / AL4; yükselen, tepeye kapanan mumlarda W%R `0` / SAT3; özel eşiklerde ısınma NaN'ının puan üretmemesi; 26/40 düz mumda gerçek nötr sıfırlar; sonlu büyük girdilerin türettiği NaN için `unknown`; 26 mumda MACD `-Infinity` değerinin AL puanı üretmemesi. Eski kodda **105 test / 100 geçti / beklenen 5 hata**; düzeltmeden sonra **105/105** geçti. Node **20.20.2**, npm **10.9.9**; önbelleksiz ESLint, incremental kapalı TypeScript, Next production build ve standalone HTML/static/chart/proxy/WS kabulü geçti. Backend/Pine/HUNTER kodu, bağımlılıklar ve veri şeması değişmedi; bu frontend işi için aynı Python paketi yerelde tekrar çalıştırılmadı, CI ayrıca çalıştıracak. Kanıtlar `runtime-data/p31-combo-red.log`, `p31-combo-green.log`, `p31-frontend-build.log`, `p31-standalone.log`; sentetik veri/yerel mock kullanıldı, borsa/AI/Telegram testi yok.

**İlk yayın hazırlığının kapsamı — tarihsel kayıt:** Yalnız frontend imajı değişecek. `/opt/rapot/current`, mevcut Compose ve `RAPOT_RELEASE` backend sürümünde kalabilir; yeni frontend kaynak SHA/digest ve canonical dosya hash'leri ayrı bileşen manifestine bağlanır. Tam kaynak arşivi veya DB işlemi gerektirmeyen bu yolda yalnız frontend `--no-deps --no-build --pull never` ile yenilenir. Dört korunan container'ın kimlik/başlangıç/restart bilgileri, env/Nginx hash'leri ve eski frontend dönüş imajı doğrulanır. 08:05:16 UTC salt okunur ölçümde beş servis sağlıklı ve boş alan **578.912.256 B**; 400 MiB rezerv +128 MiB çalışma payı sabittir. Yeni imajın gerçek compressed/açılmış katman maliyeti ölçülmeden pull yapılmaz. Ücretli yükseltme veya diğer dosyaların silinmesi için bu kayıt yeni yetki vermez.

**13 Eylül salt okunur inceleme — henüz düzeltilmedi:** P3-1 yalnız iki gösterge sınırından ibaret değil. `backtesting_system.py` içinde Lot maliyet tabanı alış ücretini dışlıyor; aynı 100 fiyatından 1.000 bütçeli kripto alış/satışta gerçek nakit farkı −2,596624… iken rapor PnL −1,30 çıkıyor (saf sınıflarla bellek içi örnek). `run_single_symbol` end_date'i uygulamıyor; kapanıştan türetilen sinyali aynı kapanışta gerçekleştiriyor. `run_backtest` ortak nakitle her sembolün bütün tarihini sırayla işliyor; bir sembolün gelecekteki nakdi diğerinin geçmişinde kullanılabilir. `WalkForwardAnalysis.run_walk_forward` strategy parametresini hesapta kullanmadan pencere buy-and-hold getirisi üretiyor. Bunlar canlı bot emir yolu değildir; backtest doğruluk işleri olarak açık tutulur.

**13 Eylül dağıtım öncesi CI/imaj ve kapasite kararı — tarihsel kayıt:** `967f137351290735d7e6ae556b4ad237c253677c` için [CI 34746909758](https://github.com/Rapto0/Rapot/actions/runs/34746909758) beş jobla, [imaj yayını 34747132287](https://github.com/Rapto0/Rapot/actions/runs/34747132287) başarılı. Yeni frontend `sha256:9b9fd4dda8a62adb568dbce71b5eda8111c2c583d6130de6db07efa280512f3b`; Linux/amd64 ve kaynak etiketi doğrulandı. 13 katmandan ilk 11'i paylaşılıyor. İki yeni katman toplam **19.369.458 B** sıkıştırılmış, **65.929.216 B** ihtiyatlı açılmış alan ve **13.140 B** metadata gerektiriyor. 400 MiB rezerv +128 MiB çalışma payı +2 MiB sınırlı kanıt/config bütçesiyle toplam boş alan **641.057.094 B'den fazla** olmalı. Son `df` ölçümü **578.150.400 B**; en az **62.906.695 B (~60 MiB)** eksik. Bütçe azaltılmadı, backend imajı indirilmedi. Ölçüm `runtime-data/p31-image-capacity-result.json`, SHA256 `8ba2498c7165c9da7de068675cb52509b93bab81618521a42d8a100a058abbc9`.

**Dağıtım öncesi tek günlük önerisi — tarihsel kayıt:**

| Dosya | Durum / boyut | Kanıt |
|---|---|---|
| `/var/log/journal/f17d1cd4476dd2156e8df9fc69737fc6/system@9785d360ea1d4cce9ab534627a929905-0000000000644271-000658d793e9c60e.journal` | Ağustos 2026 ARCHIVED sistem günlüğü; 75.497.472 B dosya, **75.501.568 B (~72 MiB)** ayrılmış alan | SHA256 `9c2b9b4ac716cc5091d0d904f4ac1d745d27a7715b7bc1cf4c34392ba76b27cb`; inode/stat, arşiv başlığı ve hiçbir açık FD/bellek eşlemesi tarafından kullanılmadığı doğrulandı |

Özel kalıcı bilgisayar arşivi `C:\Users\memet\RapotBackups\20260913-p24-journal\archived-system-journals-before-20260901.tar.gz`; **162.537.514 B**, SHA256 `7bcc55781fec5e9b863bae157d39310cb8c7a69c8cdb244ec429f9519555adcc`. 08:11 UTC'de gzip CRC, içerideki manifest, 12 üyenin tamamının hash'i ve özel klasör erişimi yeniden doğrulandı; dosya ve yedeği eşleşiyor. Yalnız bu dosya kaldırılırsa ölçüm üzerinden boş alan **653.651.968 B**, gereken bütçenin üzerinde yaklaşık **12.594.874 B** pay beklenir; eşzamanlı yazımlar nedeniyle gerçek kazanç işlemden sonra ölçülür. Diğer yedi yedeklenmiş günlük, etkin/yeni günlükler, tüm DB/imaj/release ve özel arşiv korunur. **İkinci günlük gerekli görünmediğinden öneriye alınmadı.**

Somut öneri `runtime-data/p31-one-journal-removal-proposal.json`, SHA256 `9f88d6e7c18307c3dcd080ecedd9b4f6c38a1c3fb299b60255f2a1b0ddf64e65`; `deletion_authorized=false`, `deletion_performed=false`. Önceki kullanıcı onayı yalnız kaldırılmış dört dosyayı kapsıyordu; bu yeni tek dosya için ayrı açık onay gerekir. Hazırlanan silme aracı, yeni öneriyle eşleşen yeni onay kaydı olmadan çalışmaz. Onay alınması eski ölçümü doğrudan yürütme izni yapmaz; yedek/hash/kullanım/kapasite/servis kontrolleri işlem öncesinde yeniden geçmelidir. Günlük temizliği servis restart'ı gerektirmez; daha sonraki frontend yenilemesi kısa bir web kesintisi yaratabilir. Bu ilk öneri kaydında frontend üretim kabulü henüz yapılmamıştı.

**Hazırlık belge yayını — doğrulandı:** `5c7c47cf2779fc3da48835617fb1986fb90732a1` ve CI **34747715788** başarılı; üç canonical belge ve on küçük kanıt (**807.098 B**) `/root/rapot-ops/20260913-p31-preflight/` dizinine aktarıldı. SHA256 ve aynı kalan beş servis/config/HTTPS kabulü `release-record.json` içinde. Bu kayıt alınırken üretim `279aa9f` idi ve tek günlük onayı henüz bekleniyordu; sonraki gerçek onay/temizlik/dağıtım aşağıdaki ayrı kayıtlardır. Hazırlık kaydı geriye dönük başarı makbuzuna çevrilmez.

**13 Eylül yeni onay ve tek günlük temizliği — doğrulandı:** Kullanıcının doğrudan devam yanıtı yeni öneriye bağlandı; özel arşivin SHA256/CRC/12 üye hash'i ve ACL yeniden doğrulandı. Sunucuda sabit inode/stat/hash, ARCHIVED başlığı, açık FD/bellek eşlemesi yokluğu ve servis kimlikleri yeniden kontrol edildi. 08:52:55 UTC'de yalnız yukarıdaki dosya kaldırıldı. Ayrılmış alan **75.501.568 B**, gerçek boş alan **566.095.872 → 641.581.056 B** oldu; audit ve eşzamanlı yazımlar nedeniyle net kazanç **75.485.184 B**. Diğer yedi arşiv dosyası, özel yedek, beş container, Nginx/journald kimliği ve config hash'leri korundu; API/bot HTTPS 200, servis restart'ı yok. Sonuç `runtime-data/p31-one-journal-removal-result.json`, SHA256 `b075bdb7ebb729e7460d76c0ad80a2980c16f2866e933ffe7a06e258beadd189`; sunucuda `/root/rapot-ops/20260913-p31-preflight/one-journal-removal-result.json`. Bu temizlik sonucu frontend deploy kabulü değildir.

**13 Eylül frontend üretim geçişi — doğrulandı:** 08:59:10 UTC'de yalnız frontend `967f137` / `sha256:9b9fd4dda8a62adb568dbce71b5eda8111c2c583d6130de6db07efa280512f3b` olarak yenilendi. `/opt/rapot/current`, `RAPOT_RELEASE`, Compose ve backend `279aa9f` kaldı. İki değişmez kaynak/kapasite kanıtı aynı disk üzerindeki özel hazırlık kayıtlarından hardlink ile kullanıldı; yalnız **34.902 B** operatör yüklendi. Hazırlık sonrası **641.200.128 B** boş alan, **641.057.094 B** zorunlu eşiğini aştı; operatör pull öncesinde eşiği tekrar kontrol etti. Resolved Compose'ta yalnız frontend imajı değişti; `up -d --no-deps --no-build --pull never frontend` uygulandı. API/bot/middleware/PostgreSQL container kimliği, imajı, başlangıç zamanı ve restart sayısı aynı; ortam/Nginx hash'leri ve veri servisleri korundu. Migration, DB restore veya backend lifecycle işlemi yok. Yerel frontend/API/bot sağlık, dış API/bot sağlık, `/signals`, `/alarms` ve BTCUSDT/Kripto chart SSR olmak üzere **8/8 GET 200** geçti. Son boş alan **562.618.368 B**; frontend sağlıklı/restart0. Kanıt `runtime-data/p31-frontend-deployment.json`, SHA256 `bd90aeb083ed8fd76308243b245fe87c341b6d3b065f9caf7f571b7d8b88d85f`; sunucuda `/root/rapot-ops/20260913-p31-frontend/deployment.json`. Dış statik dosya/RSC kabulü ayrı kaydedilir; bu işlem tam etkileşimli tarayıcı/worker veya gerçek alarm/emir kabulü değildir.

**13 Eylül dış HTTPS teslim kabulü — doğrulandı:** 09:01:55 UTC'de Windows dış istemcisinden sertifika doğrulamasıyla BTCUSDT/Kripto chart HTML etiketi, ETHUSDT/Kripto RSC gezinme props'ları ve alarm sayfası **200** geçti. HTML'de bulunan 15 JS / 1 CSS içinden sınırlı örneklenen **12 JS + 1 CSS** dosyasının tamamı 200, doğru MIME ve dolu içerikle alındı; SHA256'ları kaydedildi. Toplam **16 GET / 868.343 B**, chart HTML 406 ms, gezinme 203 ms, alarm HTML 297 ms. Kanıt `runtime-data/p31-frontend-public-acceptance.json`, SHA256 `8f22e597442806cdd9fcfa758a0387c66143ff34f13c32761a99a01fa1fcf0a3`. Bu kontrol tarayıcıda worker yürütmesini/COMBO aritmetiğini yeniden çalıştırmaz; hesaplayıcı/alarm davranışı aynı kaynakta 105 yerel test ve CI ile doğrulandı. Tam tarayıcı, dinamik yüklenen tüm assetler veya gerçek dış alarm/emir testi yapılmış sayılmaz.

**Uygulama sırası:** (1) COMBO sonlu sıfır/eksik ayrımı ve alarm regresyonu; (2) sabit OHLCV fixture'leriyle Python/TS/Pine fark ölçümü ve Pine döngü sınırları; (3) alış maliyeti dahil nakit–PnL ve ayrı komisyon/kayma muhasebesi; (4) sabit veri girdisi/start–end ve kapanmış mum yürütme sözleşmesi; (5) çoklu sembolü kronolojik portföyde işleme/değerleme; (6) WalkForward'ı gerçek strateji testiyle tamamlama veya mevcut buy-and-hold analizi olarak doğru adlandırma. EMA/RSI başlangıcı, CMO yaklaşımı, standart sapma ddof, Keltner ATR ve HUNTER eşik eşitliği motorlar arasında farklıdır; otomatik eşitleme kararı verilmedi.

**13 Eylül ikinci adım — incele → düzelt → doğrula:**

- `tests/fixtures/strategy_ohlcv.json` yedi sabit 80 mumluk sentetik veri dizisi,
  20 başlangıç uzunluğu içerir. `tests/test_strategy_comparison.py` gerçek Python
  public fonksiyonlarını çağırır; `frontend/tests/strategy-export.mjs` gerçek TS
  kaynağını çalıştırır. Public çıktı/gate, NaN/sonsuz/sonlu ham değer, puan ve karar
  ayrı sayılır. 1D/ME aynı tamamlanmış diziye uygulanan puan politikasıdır;
  aylık resampling veya canlı/açık mum kabulü değildir.
- 560 Python +840 TS gözlemi; geçmişin gelecek veriden etkilenmemesi için
  2.527 Python bileşen +210 TS satır karşılaştırması geçti. Varsayılan TS ile
  Python1D arasında, ikisinde public çıktı olan 21'er gözlemde COMBO2/HUNTER3
  karar farkı var. Puan/BOP politikaları eşleştirildiğinde bu örneklerde nihai
  karar farkı0; ham gösterge ve puan farkları sürüyor. Sonuç genellenmez;
  [ayrıntılı tablo ve formül farkları](STRATEGY_COMPARISON.md) kaydedildi.
- Pine `calcEma` devamına `n > len`, `calcAtr` devamına `n > len + 1` eklendi.
  Başlangıç penceresinde aşağı sayan döngünün gelişen mumu iki kez daha
  güncellemesi engellendi. Elle hesaplanan EMA3:27,5→20; ATR3:145/27→13/3.
  Sonraki mum sonuçları30 ve32/9 aynı. Formül, eşik, HTF toplaması ve alarm
  kapıları değişmedi. Gerçek iki fonksiyon gövdesinin dar AST yorumu eski
  kaynakta10 hata/20 başarı, düzeltme sonrası30/30 verdi; mevcut22 Pine
  sözleşmesiyle52/52 geçti. Pine derleyicisi/native `ta.*` testi değildir.
- Tam Python paketi coverage açık **773 geçti /1 atlandı**, **uyarı yok**,
  97,97 sn; atlanan mevcut isteğe bağlı büyük veri performans ölçümüdür.
  Yeni ölçüm8 ve Pine30 test ekler. Frontend105/105, önbelleksiz ESLint,
  incremental kapalı TypeScript, iki yeni Python dosyasında Ruff lint/format
  geçti. CI kalite araçlarının33 testi de geçti. Node20.20.2/npm10.9.9,
  Python3.12.8; bağımlılık veya Python/TS üretim formülü değişmedi.
- CI Python job'ına seçili Node/npm ve kilit frontend kurulumu eklendi.
  `RAPOT_STRATEGY_REPORT` için parent oluşturulur; kaynak/fixture metin hash'leri
  CRLF→LF normalize edilir. CI raporu `strategy-comparison-<SHA>` artifact'inde
  14 gün saklar. Yerel raw rapor `runtime-data/p31-strategy-comparison.json`,
  SHA256 `5f9f924dc72d77dcfa12c6999cc5c5b71e9775ff051b51f1051c35b06f4201c6`.
  Tam test logu `p31-indicator-full-python.log`; Pine RED/GREEN logları
  `p31-pine-boundaries-red.log` ve `p31-pine-boundaries-green.log`.

**İkinci adım yayın kapsamı:** Uygulama girişlerinde Pine/test dosyalarını yükleyen
bir yol bulunmadı; frontend standalone çıktısı test adaptörünü içermiyor.
Bu nedenle bu adım, on allowlist canonical Git dosyası ve sıkıştırılmış sentetik
raporun yeni `/root/rapot-ops/20260913-p31-indicators/` dizinine aktarımıdır.
Tam kaynak SHA'sında başarılı CI (build/standalone/Docker dahil) ve Git blob
hash'leri yayın önkoşuludur. Raw/gzip rapor hash/boyutları, öncesi/sonrası beş
container kimliği, env/Compose/Nginx hash'leri, HTTPS sağlık ve boş disk kanıtı
`release-record.json` içinde tutulur. Toplam2MiB aktarım bütçesi ve528MiB disk
rezervi korunur; imaj yayını/pull, pointer değişikliği, migration, DB işlemi,
servis restart'ı veya dosya silme yapılmaz. Bu kaynak yayını TradingView'deki
script veya çalışan alarm kopyasını güncellemiş sayılmaz.

**Açık kalan / sonraki somut adım:** Yeni Pine kaynağının TradingView derleme ve
runtime kabulü açık; eski9–10 Eylül kullanıcı kabulü yeni kaynağa taşınmadı.
Tüm motorların canlı/açık mum ve ortak zaman dilimi kabulü tamamlanmış değil.
Sonraki yerel iş `backtesting_system.py::Lot` ve `Portfolio` için alış maliyeti
dahil nakit–PnL, komisyon ve kayma muhasebesini aynı fiyat alış/satış ve kısmi
satış örnekleriyle doğrulamaktır; sonrasında tarih sınırları ve kronoloji gelir.

**13 Eylül üçüncü adım — muhasebe yerel kabulü:**

- İki gerçek eski-kod regresyonu: %1 komisyon/%2 kayma/1.030 bütçeyle lot
  maliyeti1.000 yerine1.030 olmalı; aynı100 fiyatından alış/satışta PnL−30
  yerine nakit farkıyla aynı−60 olmalı. `p31-accounting-red.log` iki assertion
  hatasını kaydeder; yalnız import engelini açan lazyimport değişimleri bu RED'de
  vardır, eski muhasebe hesapları korunmuştu.
- `Lot` alış komisyonu ve kaymasını saklar, `invested` tüm maliyet olur.
  Mevcut `q = bütçe / (referans fiyat × (1+c+s))` modeli korunur; komisyon
  veya kayma iki kez fiyatlanmaz. Satış PnL'si net gelirden bu tabanı çıkarır.
  Kısmi-lot API eklenmedi; FIFO hâlâ tek eski lotun tamamını kapatır.
- `total_commission_paid` yalnız komisyon; `total_slippage_cost` kayma;
  `total_transaction_cost` toplam. İşlem/Excel/konsol/worker maliyet alanları
  güncellendi. Açık pozisyonun `Ortalama Fiyat` alanı referans ortalamasını
  korur, `Ortalama Maliyet` giderler dahil değeri gösterir. Satış kaydındaki
  alış giderleri açıklamadır, yeniden nakitten düşülmez.
- Bağımsız inceleme kesirli bütçe ve hashlenemeyen sembolde ek hatalar buldu.
  Genişletilmiş RED9 hata/6 başarı; 42 temel test bu ikinci RED'de seçilmedi.
  Nakit Kahan toplaması ve dokümanda tanımlı ULP/göreli sınırla izlenir;
  son temsil artığı clamp edilir. 10×100,08 ve1.000×0,1 testleri geçer;
  sıradan/sub-penny/büyük başlangıç sonrası yetersizlik ve yeni fazladan alış
  reddedilir. Çok büyük sayılarda float toleransı nominal olarak büyüyebilir;
  sınırsız parasal doğruluk iddiası yoktur.
- Sembol/fiyat/tarih, sermaye/bütçe ve maliyet oranları doğrulanır; negatif,
  NaN/sonsuz ve geçersiz birleşik oranlar muhasebeye geçmez. Satış hesaplaması
  ve tarih farkı doğrulanmadan FIFO lotu çıkarılmaz. Geçerli oran değişiminde
  eski lotun alış maliyetleri sabit kalır, yeni satış güncel oranı kullanır.
- Gerçek muhasebe modülünün importunu engelleyen matplotlib ve tqdm kilitli
  ortamda yoktu; kullanıldıkları grafik/runner fonksiyonlarına taşındı.
  Bağımlılık eklenmedi; tam CLI/grafik çalıştırılmadı. Yeni testler legacy
  modül importunun warning filtresini test dışına taşırmaz.
- **57/57 hedefli**, coverage açık tam **830 geçti /1 isteğe bağlı performans
  testi atlandı**, **uyarı yok**, 97,14sn. Elle hesaplanan FIFO/iki fiyat/çoklu
  sembol/açık taban/fee-only/slip-only/zero-cost/ham hassasiyet ve durum korunumu
  geçti. Excel sayfalarının DataFrame çıktısı, konsol ve stub provider/engine
  kullanan worker sonucu kontrol edildi; gerçek Excel/PNG veya ağ üretilmedi.
  Frontend kaynakları değişmedi; yerelde aynı frontend paketi tekrar koşulmadı,
  exact-source CI frontend/build/standalone/Docker kontrollerini de çalıştırır.

Test ve sınır ayrıntıları [BACKTEST_ACCOUNTING.md](BACKTEST_ACCOUNTING.md) içinde.
Yerel kanıtlar `runtime-data/p31-accounting-final-green.log`,
`p31-accounting-full-python.log`, `p31-accounting-review-red-expanded.txt`;
canonical kaynak hash'leri ve test sonuçları küçük
`p31-accounting-local-acceptance.json` kaydına bağlanır.

**Üçüncü adım yayın sınırı / kapasite önerisi — tarihsel hazırlık:** Çalışan servisler bu CLI modülünü
import etmez. Beş canonical kaynak/test/belge ve küçük kabul JSON'u için yeni
`/root/rapot-ops/20260913-p31-accounting/` hedefi hazırlanır; tamSHA/CI ve
hash/servis/HTTPS kabulü olmadan yayına geçilmez. Bu, tam çalıştırılabilir release
veya container içindeki CLI kopyasının güncellenmesi değildir. İmaj, pointer,
config, DB, migration ve servis lifecycle işlemi gerektirmez.

10:46:04 UTC'de boş disk550.727.680B; 528MiB rezerv + geçici payload/kayıt için
yaklaşık3,84MB eksik. Boyut son committen tekrar hesaplanır. Kalan7 eski
günlük aynı75.501.568B ayrılmış alanı kullanıyor; en eskisi seçildi:

`/var/log/journal/f17d1cd4476dd2156e8df9fc69737fc6/system@9785d360ea1d4cce9ab534627a929905-00000000006542e6-000658e4eb55aed7.journal`

Aday14 Ağustos arşivi, ARCHIVED, inode516960/dev64513/nlink1; SHA256
`4c736d72fd66ff866165aef4550026013fe0c23c88348df8851c724f3edd3708`.
131 süreç/1.223FD/11.350 maps taramasında aday ve diğer altı dosyada kullanım
yok. Özel bilgisayar arşivi
`C:\Users\memet\RapotBackups\20260913-p24-journal\archived-system-journals-before-20260901.tar.gz`
162.537.514B, SHA256 `7bcc55781fec5e9b863bae157d39310cb8c7a69c8cdb244ec429f9519555adcc`;
tam SHA/gzipCRC/12 üye hash'i/manifest ve özel ACL yeniden doğrulandı.
Öneri `runtime-data/p31-accounting-one-journal-removal-proposal.json`, SHA256
`92819e1323671aaab582eea895b334bade60525aa41afd4ec37da58afee67d8d`.
Bu taslak hazırlık kaydıdır: **yeni silme onayı yok, silme veya yayın yapılmadı**.
Önceki4+1 dosya onayı bu dosyayı kapsamaz. Tek dosya teorik olarak yeterli;
diğer altı eski günlük, yeni/etkin günlükler, veriler, imajlar ve özel yedek
korunur. Ücretli yükseltme veya rezervi düşürme önerilmez.

**Üçüncü adımın CI, temizlik ve kaynak yayın kabulü — 13 Eylül:**

- Kod `7787fc17c47ece30b09ab8aedd26366a18dd8d01` main'e push edildi.
  [CI34752893586](https://github.com/Rapto0/Rapot/actions/runs/34752893586)
  beş kontrol başarılı: Python830/skip1, frontend105, lint/type/build/standalone
  ve Docker. Python uyarısız; frontend build cache uyarısı performans bilgisidir.
  Security job report-only bulgu politikasını korur; başarı sıfır bulgu demek değildir.
- Son soru ve yeni devam yanıtı, yukarıdaki tek tam yola ve final öneri hash'ine
  bağlandı. 14 ağsız temizlik testi ve bağımsız kaynak incelemesi geçti.
  Gerçek çalıştırma öncesinde özel arşivin SHA/gzipCRC/12 üye hash'i/manifest ve
  ACL'i yeniden doğrulandı; adayın stat/hash/ARCHIVED kimliği ve açık FD/maps
  kullanımı kontrol edildi. Yalnız bu dosya 11:32:21 UTC'de kaldırıldı.
- Ayrılmış alan75.501.568B; gerçek boş alan **547.848.192 → 623.267.840B**,
  net kazanç75.419.648B. Küçük audit ve eşzamanlı yazımlar farkı açıklar.
  Diğer altı eski günlük, özel arşiv, beş container, Nginx/journald süreçleri
  ve config/current kimlikleri korundu; HTTPS API/bot200, servis restart'ı yok.
  Disk önceden528MiB altında olduğundan yalnız kurtarma audit'i için128KiB
  ve16KiB dizin payı bütçelendi; temizlik sonrası gerçek rezerv geri kazanıldı.
  Yayının528MiB sınırı değiştirilmedi.
- Uzak temizlik kaydı:
  `/root/rapot-ops/20260913-p31-accounting-cleanup/removal-result.json`, SHA256
  `cc80f664735f3ddd6993bfeebfa5f6670fea2a524b6a0cb791d1cb07706228e4`.
  Yerel ham-byte kopyası `runtime-data/p31-accounting-cleanup-remote-receipt.json`;
  araç çıktısının yerel JSON'u ayrı `p31-accounting-journal-removal-result.json`.
- 11:32:29 UTC'de beş canonical Git blob'u ve889B kabul JSON'u, toplam
  **352.918B**, yeni `/root/rapot-ops/20260913-p31-accounting/` dizinine aktarıldı.
  Dosyalar600/dizin700; altı dosyanın boyut/hash kontrolü geçti. Kaynak yayını
  26 ağsız kontrolle ve mevcut exact-source CI ile doğrulandı.
  Uzak `release-record.json`10.920B, SHA256
  `1f11263ec5d3251e40b77a53d0caf7d20ed5d142d13b68644c32b1fa62814f4c`;
  yerel ham-byte kopyası `runtime-data/p31-accounting-source-remote-receipt.json`.
- Aktarım sonrası yeniden okunan dosya hash'leri ve Windows'tan sertifika
  doğrulamalı iki HTTPS sağlık isteği geçti. Boş alan622.800.896B; tüm servis,
  config ve current kimlikleri aynı. Container içindeki CLI kopyası, uygulama
  imajları, DB veya pointer güncellenmedi; CLI veya borsa emri çalıştırılmadı.
- Bu tek belge güncellemesinin kendi commit/CI ve aktarım kabulü, döngüsel
  commit referansı oluşturmadan
  `/root/rapot-ops/20260913-p31-accounting-closure/release-record.json` içinde
  tutulur; yukarıdaki iki değişmez uzak kabul kaydının tam hash'lerine bağlanır.

**Dördüncü adımın salt okunur hazırlığı — tarihsel inceleme:**

- `BacktestEngine.end_date` yürütmede kullanılmıyor. `run_single_symbol`,
  başlangıç indeksinin veri dışında olup olmadığını kontrol etmeden bu indeksi
  log satırında okuyor. Ham tarihler yürütmeden önce sıralı/tekil doğrulanmıyor.
- Mevcut sinyal günlük kapanışı içeriyor ve aynı kapanış fiyatında işlem yapıyor.
  Sonraki gerçek açılışta yürütme seçilirse `Open` kalitesi doğrulanmalı:
  BIST sağlayıcısının `close_proxy`/`aof_proxy` değeri gerçek açılış değildir.
- En küçük önerilen kapsam: sağlayıcıdan bağımsız sabit günlük OHLCV girdisi,
  değiştirilmeyen çağıran DataFrame'i, doğrulanan tarih/OHLCV, başlangıç–bitiş
  sınırları, sabit `as_of` ve açık günlük mumun dışlanması. Örtük BIST seans
  saati varsayılmayacak. Paralel worker'ın aynı veriyi iki kez çekmesi de
  sabit girdi yoluna bağlanmalı.
- Haftalık/aylık son grup, geçmiş günlük prefix'ten hesaplanan gelişen mumdur;
  bu tek başına gelecek veri sızıntısı değildir. Tüm HTF mumlarını yalnız
  kapanmış hâlde kullanmak ayrıca strateji davranışını değiştirir. Grup indeksi
  ilk işlem günüdür; `index <= cutoff` veya koşulsuz son satırı silmek doğru
  kapanış filtresi sayılmaz. Bu politika uygulama öncesinde açıkça seçilmeli.
- Sentetik kabul: bitiş sonrası aşırı satırlar eski işlemleri değiştirmemeli;
  sınır dışı başlangıç hata vermemeli; sırasız girdi aynı sonucu üretmeli;
  mükerrer/NaT ve sahte açılış reddedilmeli; sabit girdi sağlayıcıya gitmemeli.
  Sonraki açılış seçilirse `Open=200 / Close=999` örneğinde işlem fiyatı 200
  olmalı, sonraki mum bitiş dışındaysa emir oluşmamalı. Mevcut FIFO maliyet
  korunum testleri korunmalı. Çoklu sembol ortak nakit kronolojisi ve WFA,
  bu ilk yürütme düzeltmesinden sonraki ayrı işlerdir.

**Kabul kriterleri:**

- [ ] Aynı örnek veri, zaman dilimi ve kapanmış/açık mum kurallarıyla hesaplayıcı farkları ölçüldü.
- [ ] Komisyon, kayma, veri kaynağı ve ileriye bakış etkileri kontrol edildi; sonuçlar tekrarlanabilir.
- [ ] Bilinçli strateji farkları belgeli; performans raporu canlı kazanç garantisi olarak sunulmuyor.

**13 Eylül dördüncü adım — günlük yürütme yerel kabulü:**

- Eski kaynağın iki RED testi: `end_date=2020-04-30` sonrasında işlem/equity
  üretmesi ve start veri dışındayken log satırında indeks taşması.
  `runtime-data/p31-execution-red.log` SHA256
  `547e998c5378940114b13ff6624d577f17d95d47e4f57d7293b9df74cb7d3389`.
- `BacktestEngine` strict tarih sınırları ve bir kez sabitlenen saat dilimli
  `as_of` kullanır. `run_single_symbol(..., data=frame)` sağlayıcıya gitmez;
  girdi kopyalanır/sıralanır, gün etiketi ve sütun tekilliği, sayısal OHLCV ve
  gerçek Open kalitesi ilk işlemden önce doğrulanır. Start/end işlem gününe
  dahil uygulanır; start öncesi ısınma geçmişi korunur. Bitiş ve kapanış kesmesi,
  minimum120 satır şartından önce yapılır; sınır dışı başlangıç güvenle döner.
- Piyasa takvimindeki sonraki gece yarısı konservatif gün kapanışıdır: kripto
  UTC, BIST Europe/Istanbul. Takvim günü tz eklemeden önce ilerletilir;
  2015 DST sınırı test edildi. Bugünkü açılış da henüz kapalı gün sayılmadığı
  için dışarıda kalır. BIST seans saati/tatil takvimi eklenmedi.
- Önceki kapanmış günlük prefix'te hesaplanan sinyal, sonraki mevcut mumun
  gerçek Open fiyatında yürütülür. İlk sinyal indeksi60, ilk işlem indeksi61;
  sonraki mum bitiş dışındaysa veya yoksa işlem oluşmaz. İşlem kaydına
  `Sinyal Tarihi` ve `Yürütme Modeli=next_open` eklenir. Equity kaynak satır
  indeksi10'un katında ve son uygun günde Close ile gün sonu değeri olarak
  kaydedilir. Aynı Open'da COMBO/HUNTER ve çoklu eylem sırası korunur.
- Close/AOF/synthetic/mapped/bilinmeyen Open metadata reddedilir. Yalnız
  eksik/None veya `provider` kabul edilir; eksik metadata çağıranın gerçek
  açılış sağlama sözleşmesidir. Mevcut İş Yatırım adaptörü proxy üretirse bu
  BIST veri kümesi için sonuç yerine açık hata alınır. Sessiz fiyat fallback'i
  veya canlı sağlayıcı doğrulaması yapılmadı.
- Haftalık/aylık gelişen grup, kapanmış günlük prefix'ten hesaplanmaya devam
  eder. Bu bütün HTF mumlarının kapandığı anlamına gelmez. Sabit DataFrame,
  sabit sınırlar ve aynı hesaplayıcı/maliyet sürümleri tekrarlanabilir yoludur;
  `as_of` sağlayıcı revizyonunu veya göreli indirme başlangıcını dondurmaz.
- Worker aynı veriyi iki kez çekmez. Dört elemanlı eski çağrı korunur; altı
  elemanlı çağrı end/as_of taşır. Paralel dispatch bir kapanış anını bütün
  worker'lara verir. Toplu sabit DataFrame API'si ve ortak nakit kronolojisi
  bu adımda uygulanmadı.
- **48/48 yeni test**, **878 geçti /1 isteğe bağlı performans testi atlandı**,
  **uyarı yok**, tam paket100,53sn. Gerçek yürütme + stub sinyalle FIFO oracle:
  bütçe1.030/Open100/q10; sonraki SELL Open110/net1.067; cash2.097/PnL37,
  komisyon21/kayma42. Gap senaryosu 1 Mart sinyali → 3 Mart Open500; Close999
  işleme taşınmadı. Cutoff dışı NaN, kaynak değişmezliği, UTC/İstanbul,
  Openproxy, yapı/fiyat hatalarında portföy korunumu ve tek worker fetch geçti.
  Güncel yeni testler `tests/test_backtest_execution.py`; 57 muhasebe testi
  tam pakette korunuyor. Gerçek CLI/provider/Excel/grafik/emir çalıştırılmadı.
- Ayrıntılar [BACKTEST_EXECUTION.md](BACKTEST_EXECUTION.md) içinde. Yerel
  sonuçlar `runtime-data/p31-execution-green.log` ve
  `p31-execution-full-python.log`; canonical kaynak hashleri ve sayılar
  `p31-execution-local-acceptance.json` kaydına bağlanır. Beş Git blob'u ve bu
  küçük JSON, exact-source CI sonrası yeni execution ops dizinine yayımlanır.
  Bu kaynak/kanıt aktarımı, container içindeki CLI kopyasını veya çalışan
  uygulama imajını değiştirmez. Sabit528MiB rezerv ve2MiB bütçe korunur.

**Önceki kapanış belgesinin son kabulü:** `905d1a1470b0d67ece11cfdbf0cc2b5ae64b89fe`,
[CI34754812887](https://github.com/Rapto0/Rapot/actions/runs/34754812887) beş kontrol
başarılı; 11:40:13 UTC'de263.569B belge ve9.054B kabul kaydı doğrulandı.
`/root/rapot-ops/20260913-p31-accounting-closure/release-record.json` SHA256
`ccb3876eff4382315cdc8facc3b7a54dcb3794cc88d7c68efd65801e488d62b2`.
Son boş alan622.018.560B, beş servis/config ve frontend967/backend279 aynıydı.
Üçüncü adımın kapasite veya belge yayını için yanıt/iş beklenmiyor.

**13 Eylül dördüncü adım — CI ve kaynak yayını kapanışı:**

- Kod `f937744b5184a86ee079c2c5579893f4bb638759`; [CI 34755778327](https://github.com/Rapto0/Rapot/actions/runs/34755778327) beş işte başarılı. Linux Python 878 geçti / 1 isteğe bağlı performans testi atlandı, uyarı özeti yok; frontend 105/105, lint/type/build/standalone ve Docker kabulü geçti. Git'in izlediği 225 Python dosyasında yerel Ruff lint/format ve commit hook'ları geçti.
- 12:02:42 UTC'de beş canonical Git blob'u ve yerel kabul JSON'u, toplam **371.071 B**, `/root/rapot-ops/20260913-p31-execution/` dizinine yazıldı. **10.982 B** `release-record.json` SHA256: `f52e6621d7247bc31c0364093b47f121fbd09c5c3c0a5f64347bade820fda2ca`. Altı dosyanın byte/hash, sahiplik ve izinleri yeniden okunarak doğrulandı; uzak kayıt yerel kabul ile aynı.
- Yayın öncesi/sonrası beş servis kimliği, restart=0, config hashleri ve current pointer aynı. Frontend `967f137`, backend/Compose `279aa9f`; container içindeki CLI kopyası değiştirilmedi. Kaynak yayını tek başına çalıştırılabilir yeni uygulama sürümü değildir. İmaj, migration, CLI, sağlayıcı veya borsa emri çalıştırılmadı; yeni silme yapılmadı.
- Dış Windows HTTPS kabulü 12:03:32 UTC: API 197,830 ms / 200 ve database=connected; bot sağlık 192,297 ms / 200. Yeniden ölçülen boş alan **620.085.248 B**; sabit 528 MiB rezerv korundu. Yerel tam kayıtlar `runtime-data/p31-execution-remote-receipt.json`, `p31-execution-publication-acceptance.json` ve `p31-execution-completion.json` içindedir.
- Güvenlik işinin başarı durumu report-only politikasına göredir. Bandit 225 dosyada **1.883 LOW / 17 MEDIUM / 0 HIGH**; pip-audit 115 pakette **0 bulgu**. Frontend kurulumunda npm ayrıca **11 güvenlik bildirimi (1 düşük / 2 orta / 7 yüksek / 1 kritik)** üretti. Bunlar backtest test uyarısı değildir; P1-G2 aşağıda ayrı takip edilir.
- Bu kapanış yalnız `docs/RAPOT_DEVAM_PLANI.md` değişikliğidir. Kendi tam SHA/CI, canonical belge hash'i ve son sunucu kabulü `/root/rapot-ops/20260913-p31-execution-closure/release-record.json` içinde tutulur; uygulama restart'ı gerekmez.

### P1-G2 — Frontend bağımlılık güvenliği takibi

**Bulgu:** Exact `f937744` CI'sindeki frontend ve Docker `npm ci` adımları 11 güvenlik bildirimi üretiyor. Yeşil frontend testi/build veya Python güvenlik taraması bunları kapatmaz. İlk kayıt paket/advisory etki analizi tamamlanmadan oluşturuldu; bildirim sayısı kanıtlanmış 11 üretim açığı anlamına gelmez.

**Salt okunur ilk audit:** Node 20.20.2 / npm 10.9.9 ile `npm audit --package-lock-only --ignore-scripts --json` aynı 11 etkilenmiş paket düğümünü bildirdi; çıkış 1 bulgu sonucudur. `package.json` ve `package-lock.json` hashleri değişmedi. Rapor `runtime-data/p31-execution-npm-audit.json`, 31.255 B, SHA256 `cd1fc2e7b87a0f1816cbc512f9f5138ab9cbc1f7f57e7391e455b829f867e0ba`. Tek doğrudan etkilenen paket `next@16.2.1`; npm `16.3.5` öneriyor, ancak bu sürüm henüz seçilmedi veya uyumlulukla doğrulanmadı. Diğer düğümler `@babel/core`, `@humanfs/node`, `baseline-browser-mapping`, `brace-expansion`, `browserslist`, `js-yaml`, `minimatch`, `nanoid`, `postcss`, `sharp`. Rapor 46 benzersiz advisory URL içeriyor; bir düğüm birden çok advisory içeriyor. Altı paket yalnız dev, beşi prod yolunda; postcss iki kapsamda da bulunuyor. Mevcut brace-expansion override değerleri 1.1.13 / 2.0.3 olduğu için yalnız lock yenilemesi bu kısıtı kaldırmaz. Next'in 25 doğrudan advisory kaydı arasında Windows sunucusu ve AVIF image optimization için iki kritik bildirim var; üretimin Linux olması bütün Next bulgularını elemez. Kod yollarının erişilebilirliği ve hangi sürümün tüm ilgili aralıkları kapattığı henüz tamamlanmış analiz değildir. Paket yükseltmesi veya saldırı denemesi yapılmadı.

**Yapılacak iş ve bağımlılıklar:** `frontend/package.json`, `frontend/package-lock.json`, Next sunucu rotaları ve `.github/workflows/ci.yml` üzerinden doğrudan/geçişli paketleri, dev/prod ayrımını ve erişilebilir işlevleri incele. Uyumlu sabit sürümleri seç; gerekli paket/lock değişikliğini frontend test/lint/type/build/standalone ve CI ile doğrula. Üretim etkisi varsa sabit disk rezervi, taze yedek ve imaj boyutu ölçümü sonrası deploy kabulünü tamamla. İlk inceleme küçük; kod/dağıtım kapsamı advisory bazında belirlenir. Otomatik `npm audit fix --force` veya ücretli kapasite artışı kararı verilmedi.

**Kabul:** Her advisory için etki/sürüm kararı, yeniden audit sonucu ve varsa uygulama/dağıtım kabulü kaydedilmeli. Bu iş P3-1 beşinci adımdan önce gelir; borsa emri gerektirmez.

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
| 2026-09-10 | Borsa/alarm dış kabulü ertelendi; P1-4'e geçildi | Kullanıcı hesabıyla ilgili adımları sonraya bırakıp diğer görevlere devam istedi; hazır testnet/capture araçları çalıştırılmayacak, önceki bekleyen sorular ilerlemeyi engellemiyor |
| 2026-09-10 | Tarama geçmişi terminal sonucu ve gerçekten kaydedilen sinyalleri gösterecek | Eski kayıt unknown kalır; hatalı/eksik/iptal tarama başarı sayılmaz. ContextVar sayaçları manuel/paralel çağrılardan ayrılır; SIGKILL için history garantisi verilmez |
| 2026-09-11 | Tam takipli kaynak lint/format, güvenlikte açık report-only bulgu politikası | Araç/eksik tarama hatası CI’yi başarısız yapar; yeşil job sıfır bulgu değildir. P0-G1 P2-3 ile yayımlandı; P1-G1 incelemesi P2-4’ten önce sıradaki iş. Uygulama dependency’si bu tur yükseltilmedi |
| 2026-09-11 | İç worktree korunarak yalnız ana gitlink kaldırılacak | `.claude/` ignore; detached f752ee2, dosyalar ve worktree kaydı korunur, otomatik merge/silme yok |

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
| 2026-09-09 | P1-3 | Commit/push → Linux CI → belgeyi güncelle | `ea2d0a5` main'de; CI 34375597532 başarılı. Python 403/403, frontend, lint ve Docker/izole PostgreSQL kontrolleri geçti. Pine runtime/testnet ve VPS deploy'u erişim koşulları nedeniyle açık; mevcut P2-3 uyarıları sürüyor |
| 2026-09-09 | P1-4 | Salt okunur ön inceleme | Sinyal ID'sinin AI çağrısında kaybı, eski satırı etiketleme riski ve eksik scan-history yazımı doğrulandı. Başlangıç `market_scanner.py::process_symbol`; gerçek repository dosyaları ve hedef testler kaydedildi. Uygulama başlamadı |
| 2026-09-09 | P1-2 / P1-3 | Öncelik → VPS envanteri → imaj yayını | Kullanıcı P1-4'ten önce açık dağıtım/Pine/testnet işlerini seçti. DigitalOcean root konsolu açıldı; sunucu main `62ff6cf`, yüksek CPU, eski PM2/uvicorn süreçleri ve eksik Docker/Compose doğrulandı. `8f60f8e` imaj yayını 34378537277 başarılı, anonim GHCR HEAD erişimi var. Konsol satırını temizleme ve SSH anahtarı ekleme onayı bekleniyor; yedek/servis değişikliği/deploy/emir yok |
| 2026-09-09 | P1-2 | Erişim kontrolü → kullanıcıya SSH kurulum hazırlığı | Önceki konsol satırı temizlendi; yeni SSH anahtarı hâlâ kabul edilmiyor. Otomatik onay denetimi `date` için Enter'ı reddetti. Git dışında, sözdizimi doğrulanmış ve mevcut anahtarları koruyan SSH kurulum bloğu hazırlandı; kullanıcı çalıştırması bekleniyor. Konsol boş bırakıldı; sunucu mutasyonu/deploy yok |
| 2026-09-09 | P1-2 | Konsol giriş kontrolü → onay engeli | Yapıştırma ve harf kilidi sorunları kısa, çalıştırılmamış girişlerle incelendi. Yavaş tuş girişinde ilk 190 karakter ekranda görüldü; devamı otomatik onay denetimince, önceki Enter reddinden sonra açık onaysız erişim değişikliği hazırlığı sayılarak reddedildi. Yarım komut Ctrl+U ile silindi ve boş root istemi ekrandan doğrulandı. SSH anahtarı eklenmedi, komut çalıştırılmadı, deploy yapılmadı. Hazır dosya üzerinden açık kullanıcı onayı veya manuel kurulum bekleniyor |
| 2026-09-09 | P1-2 | Açık onay → SSH → envanter/yedek | Somut root SSH kurulumu açıkça onaylandı; restrict anahtar ile uid=0 doğrulandı. Config yedekleri sonrası yalnız çakışan PM2 API ve ikinci bot durduruldu; diğer eski servisler çalışıyor. Ana/cache SQLite quick_check ve PostgreSQL dump liste kontrolü geçti; eski checkout/untracked kayıtlar korundu. Ayrı 8f60f8e kaynak arşivi hazır. Docker resmi apt kurulumu sürüyor; izole smoke/geçiş ve P1-3 dış kabulü açık, P1-4 bekliyor |
| 2026-09-09 | P1-2 | İzole smoke → üretim geçişi → HTTP kabulü | Docker 29.8.0/Compose 5.5.1; 8f60f8e backend/frontend ve PG16 digest'leriyle beş production konteyner sağlıklı. SQLite 1.721.138 sinyal ve middleware 135/135/28/383 kayıt korundu; PG14 final dump → PG16/Alembic 0006 geçti. Eski supervisor'lar devre dışı, checkout/DB/yedek/rollback korundu. HTTP/auth/WS geçti; IP sertifikası alındı, nginx TLS kurulumu/kabulü sürüyor. Emir gönderilmedi |
| 2026-09-09 | P1-3 / P3-1 | Kullanıcı derleme adımı → kaynak sınırı kaydı | CE10244 sonrası eksik editör kopyası doğrulandı; orijinal SHA ile aynı 1.089 satır/6 plotshape TXT açıldı, yeniden derleme sonucu bekleniyor. Mevcut EMA/ATR ilk değer sınırı P3-1'e kaydedildi; kod değişmedi. Pine runtime/alarm/testnet açık, P1-4 başlamadı |
| 2026-09-09 | P1-2 | HTTPS/yenileme kabulü → Doğrulandı | Güvenilir IP sertifikasıyla altı dış HTTPS rota 200, HTTP308, login/admin/anonim401 ve WSS101 geçti. Yetkisiz webhook401 sonrası MW sayıları aynı. Certbot renew dry-run+deploy-hook exit0, timer enabled/active; beş konteyner healthy/restart0. Ops HTTPS sonucu verified, veri/rollback korunuyor. P1-2 kapandı; aktif P1-3 tam Pine kopyası ve HTTPS alarm/testnet kabulü |
| 2026-09-09 | P1-3 | Kullanıcı derleme kabulü → testnet salt okunur ön kontrol | Kullanıcı BTCUSDT/standart/1D derleme sorusuna “derlendi” dedi; derleme kutusu kullanıcı bildirimi olarak kapatıldı. Futures/Heikin Ashi kontrollerini yapamadığını söyledi; bunlar açık. VPS'den mevcut testnet anahtarıyla yalnız time/account GET geçti, SPOT/canTrade=true; emir isteği 0. Grafik/alarm ve izole testnet emir kabulü bekliyor; Pine/uygulama kodu değişmedi |
| 2026-09-10 | P1-3 | Kullanıcı grafik kabulü → belgeyi güncelle | Futures/1D ve Heikin Ashi/1D için `Grafik Engelli`; standart BTCUSDT/1D/Kripto 24/7 için `TF OK` ve `Alert Acik` kullanıcı tarafından bildirildi. Kaynak/Pine değişmedi; gerçek alarm JSON'u ve ALL/FIRST/saat filtresi runtime kabulü açık |
| 2026-09-10 | P1-3 | İncele → düzelt → izole VPS simülasyon kabulü | Boş SQLite'da ilk migration'ların doğrudan constraint işlemi uygun bulunmadığından gerçek PG16 kullanıldı. İlk HTTPS denemesi JSON yanıtı alamadan durdu; r2'de nginx reload hazır olma kontrolüyle query-token `401/422`, 4 simülasyon emri, FIFO 1→2 ve restart öncesi/sonrası duplicate geçti. Üretim 135/135/28/383 aynı; test rotası/konteyner/ağ temiz, audit volume korundu |
| 2026-09-10 | P1-3 | Testnet hazırlığı → onay sınırı | En fazla 4 emir/50 sanal USDT toplam BUY kapsamındaki izole testnet aracı hazırlandı; Python 3.10 AST, Ruff ve bağımsız inceleme geçti. Yalnız varsayılan plan modu çalıştı; somut emir onayı bekleniyor. TradingView Webhook URL alanı erişimi soruldu; yalnız kayıt yapan alıcı hazırlığı sürüyor. P1-4 başlamadı |
| 2026-09-10 | P1-3 | Gerçek alarm alıcısı hazırlığı → ağsız doğrulama | Yalnız kayıt yapan alıcının kaynak incelemesi ve sabit backend imajında ağsız/sentetik ASGI kabulü geçti; auth/IP, kapsam, gövde/JSON, dedup/limit, dosya izni ve expiry kontrol edildi. Gerçek alarm veya emir yok, alıcı dışa açılmadı. Kullanıcının Webhook URL erişim yanıtı ve testnet emir onayı bekleniyor |
| 2026-09-10 | P1-3 / P1-4 | Öncelik değişikliği → incele | Kullanıcı borsayla ilgili adımları erteledi. P1-4 AI kimliği kaybı ve eksik history bağlantısı doğrulandı; legacy SQLite'da mode/errors_count eksik olabileceği de saptandı. Ertelenen işler başarılı sayılmadı |
| 2026-09-10 | P1-4 | Düzelt | Kesin ID/piyasa ile AI/tag, commit sonrası erken sayaç callback'i, ContextVar/monotonic/terminal history, status migration ve UI sonuçları eklendi. Async notify=False ve iptal cleanup korundu; root/sync kabul edilmiş her çağrı ayrı kayıt |
| 2026-09-10 | P1-4 | Doğrula → belgeyi güncelle | 68 yeni Python/3 frontend test; hedefli 92/92, tam 471/471, frontend 15/15, lint/typecheck/build ve Ruff/diff geçti. Daha geniş persistence testleri mevcut UTC kullanımından 193 warning gösterdi. Yerel gerçek DB/AI/borsa emri yok; CI ve sunucu yayını sırada |
| 2026-09-10 | P1-4 | Commit/push → CI/imaj → üretim → Doğrulandı | fce5d01 main'de; CI 34510880779 ve imaj 34510920665 başarılı. Doğrulanmış DB/config yedekleriyle şema yükseltildi; 1.726.925 sinyal/26.393 AI ve diğer tablo sayıları aynı. Beş servis healthy/restart0, HTTPS/JS/API geçti; middleware 135/135/28/383 ve DRY_RUN/false/false korundu. Ops deployment.json verified; üretim scan_history henüz boş, test verisi eklenmedi |
| 2026-09-10 | P1-5 | Salt okunur ön inceleme → sıradaki adımı kaydet | Süreçler arası callback boşluğu, ticker'a bağlı sinyal socket'i, reconnect/upsert/REST eksikleri ve async özel sinyal/tazelik farkları doğrulandı. SQLite cursor+REST başlangıç planı, transaction/restore/geç güncelleme sınırları ve testler kaydedildi; uygulama başlamadı |
| 2026-09-10 | P1-5 | Düzelt → doğrula → belgeyi güncelle | SQLite SignalFeed, bağımsız istemci/reconnect/REST, kline/trade abonelik lifecycle ve ortak scanner finalizasyonu uygulandı. 71 yeni Python ve 8 frontend test; tam 542/542, frontend 23/23, lint/typecheck/build ve Ruff geçti. Aynı batch içinde yaşlanan BIST verisi yazım öncesi reddediliyor; no-network subprocess ASGI kabulü eklendi |
| 2026-09-10 | P1-5 | Commit/push → CI/imaj → yayın hazırlığı | a513af9 main'e gönderildi. CI 34516407676 ve imaj yayını 34516429765 tamamen başarılı; ağsız subprocess sinyal kabulü, boş PostgreSQL migration/middleware startup ve frontend container HTML/JS geçti. Config/SQLite arşivi bağımsız doğrulandı, kaynak ve imaj digest'leri sabitlendi; kontrollü sunucu geçişi başlatıldı |
| 2026-09-10 | P1-5 | Üretim → dış kabul → Doğrulandı | a513af9 üretimde; beş servis healthy/restart0, DB sayıları aynı, middleware135/135/28/383 ve DRY_RUN/false/false korundu. HTTPS/feedready, BTCUSDT kline/trade ve sinyal heartbeat kabulü geçti; kanal sayaçları kapanışta0. Tarayıcı300satır/etiket gösterdi. İlk UI yükü sırasında timeout P2-4'e açık kaydedildi; test sinyali/AI/emir yok |
| 2026-09-10 | P1-6 | İncele → düzelt → doğrula | Etkisiz/secret saklayan settings kaldırıldı; eski iki key allowlist ile temizleniyor. PnL miktar/null, gerçek CLOSED count ve nullable API sözleşmesi; lifecycle/scan context, eksik sayaç ve history zaman ayrımı uygulandı. Tam Python578/578, frontend52/52, lint/typecheck/build ve yedi Python Ruff geçti; 874 mevcut UTC warning. Bağımsız incelemede saptanan manuel async tarama/DB lease/sayaç hataları da kapandı |
| 2026-09-10 | P1-6 | Belgeyi güncelle → yayın hazırlığı | Yerel kabul kaydedildi; config/SQLite yedeği ve disk rezervleriyle ayrı p16 ops dizini hazırlanıyor. Doğrulanmış kaynak CI/imaj sonrasında dağıtılacak; şu anda üretim a513af9. Snapshot üretimindeki geçici Windows log klasörü temizliği otomatik denetimce blocked by policy ile reddedildi; klasör bırakıldı, uygulama kontrolleri etkilenmedi |
| 2026-09-10 | P1-6 / P2-4 | CI/imaj geçti → kabul hatası → rollback → dar düzeltme | f61e169 CI34520120793/imaj34520142341 başarılı; ana tablo sayıları korunarak geçiş yapıldı. Son/api/health20s timeout/499 önceki a513af9 uygulamasına otomatik dönüşü tetikledi; DB restore yok. Boş sonucu kullanılan altıCOUNT sağlık yolu tek-session/LIMIT0/thread probe'a çevrildi; hata gizlenmiyor. Hedef13/13, tam588/588+874warning, Ruff geçti; yeni kaynağın CI/yedek/deploy kabulü hazırlanıyor |
| 2026-09-10 | P1-6 | Yeniden doğrula → başlangıç ve proxy engellerini ayır | 2cf05a8 CI34521979155/imaj34522034163 geçti. r2 health0,051s geçti; 65s scheduler gözlemi doldu. r3 /api/scans502 nginx localhost→::1 bağlantı reddiyle eşleşti. İkisinde a513af9'a DB restore olmadan dönüş; 180s başlangıç penceresi11 ağsız senaryoda doğrulandı, host Nginx IPv4 hedefleri düzeltildi |
| 2026-09-10 | P1-6 | Üretim → tarayıcı/WSS kabulü → Doğrulandı | r4 2cf05a8 üretimde, beş servis healthy/restart0; main kayıtları ve middleware135/135/28/383 korundu. Bot unknown→running46,766s gözlendi; health0,029–0,048s. Ayarlar/sağlık/işlemler UI ve ek UI yükü olmadan üç WSS kanalı geçti; ilk UI açıkken sonuçsuz heartbeat P2-4'e kaydedildi. Snapshot/config/ops kanıtları ve önceki sürümler korundu; DRY_RUN/false/false, emir yok |
| 2026-09-11 | P2-2 | İncele → belgeleri düzelt → doğrula → karar kaydı | 12 Markdown dosyası eşlendi; 211 tracked Python AST/12 wrapper, 98/98 hedefli test. İki DB/migration yolu, HUNTER15, güncel bağımlılıklar, eski20ALG ve tarihselP numaraları düzeltildi. 12wrapper korunur; koşullu kaldırma kanıt kapıları var. Çalışan imaj/config/source korunarak Git blob belge yayını ve tamSHA CI kanıtı `/root/rapot-ops/20260911-p22/release-record.json` kaydında tutulur. Sıradaki P2-3; dış alarm/emir kabulü erteli |
| 2026-09-11 | P2-3 | İncele → düzelt → yerel doğrula | Altı Ruff bulgusu/iki format dosyası, tam takipli kaynak/force-exclude/pre-commit, Node24 action motorları ve güvenlik report-only/operational-fail ayrımı uygulandı. 21 UTC sınır testiyle 609/609 uyarısız; ayrı 33/33 CI testleri; frontend95/95/lint/type/build/standalone ve 128 paket pip check geçti. Altı atıl frontend dosyası/1.568 satır kaldırıldı; iç worktree f752ee2/dosyalar/kayıt korunarak yalnız gitlink index’ten çıktı |
| 2026-09-11 | P2-3 | Belgeyi güncelle — yayın öncesi tarihsel kayıt | İlk güvenlik raporu korunarak standalone debug kapatıldı. Son bütünleşik Python 642/642 uyarısız; Bandit 215/215 dosya, 0 HIGH / 15 MEDIUM / 1.475 LOW. pip-audit 128/128 paket, 24 pakette 203 advisory; P1-G1 incelemesi açık. Bu aşamada commit/push/CI/imaj/deploy bekliyordu; frontend db98915 / backend 2cf05a8 ve DRY_RUN/false/false korunuyordu |
| 2026-09-11 | P2-4 | Salt okunur ek gözlem | Yayın öncesi API health 15 saniyede timeout; sonraki istek yaklaşık 45 ms/200. Nedeni doğrulanmadı, performans kabulü kapanmadı. Gerçek/testnet emir ve alarm dış kabulü erteli |
| 2026-09-11 | P2-3 / P0-G1 | Commit/push → Linux CI/imaj → üretim → Doğrulandı | bacbfab8, CI 34636602751/imaj 34637100266 başarılı; 19:14:51 UTC API/bot/middleware/frontend aynı kaynakta. Yeni SQL gzip bağımsız yerel SQLite restore ile doğrulandı; PG dump katalog kabulü, restore yok. İlk operator şablon kontrolü uygulama değişikliğinden önce durdu, dar operator düzeltmesiyle ikinci deneme geçti. Ana sayılar ve PG kimliği/135/135/28/383, eski yedek/imajlar ve DRY_RUN/false/false korundu. HTTPS health 36 ms/SSR 200, feed/sağlayıcılar hazır; scheduler 43,781 s unknown→running, tam tarama kabulü değil. P0-G1 kapandı; P1-G1 24/203 incelemesi sırada, P2-4/P3 ve dış alarm/emir kabulü açık |
| 2026-09-11 | P1-G1 | İncele → düzelt → yerel doğrula → belgeyi güncelle | 203 kayıt/114 alias grubu incelendi; 17 etkilenen paket patch, 7 etkilenen paket JWT/Streamlit dallarıyla kaldırıldı. PyJWT HS256, minimum uyumlu FastAPI/Yahoo çiftleri, güvenlik constraints, TestClient/httpx2 izolasyonu ve 68 yeni vaka. 710/710 uyarısız, canonical115exact/pip-check; Ruff218/218, pip-audit115/115 sıfır bulgu, BanditHIGH0/MEDIUM15/LOW1534. Üretim bacbfab8 ve modlar korunuyor; ~832MiB boş disk yeni katman+backup+rezerv için yetersiz, pull/resize/deploy yok. CI/imaj ve kapasite çözümü açık |
| 2026-09-11 | P1-G1 | Commit/push → CI/imaj → ücretsiz kapasite hazırlığı | ccd61544, CI34641121926/imaj34641767731 başarılı; Linux710/710 uyarısız ve115paket sıfıradvisory. OCI katman/hash/diffID maliyeti ölçüldü. Kullanıcı ücretli yükseltmeyi reddetti; panel seçimi iptal, ücret/kapanma değişimi yok. Üç eski gzip ve açılmış SQLite özel kalıcı PC klasöründe SHA/CRC/integrity/ACL ile doğrulandı; sunucu kopyalarının silme onayı bekleniyor. Güncel P2-3/P1-6 yedekleri ve tüm imaj/release korunur. Yeni üretim yedeği/pull/deploy yok; uygulama bacbfab8 ve DRY_RUN/false/false. P2-4 başlamadı |
| 2026-09-11 | P1-G1 | Kullanıcı devam onayı → ücretsiz kapasite → yedek/restore → üretim → Doğrulandı | Yalnız üç eski sunucu gzip kopyası kaldırıldı; 6 kalıcı PC dosyası korundu, gerçek boş alan +606.547.968 B. Taze SQL gzip ve 7 tablo bağımsız restore ile, PG arşivi katalog kontrolüyle doğrulandı. Exact ccd61544 imajları 20:56:32 UTC'de kabul edildi. Beş servis healthy/restart0; ana sayılar, PG kimliği ve DRY_RUN/trading=false/live=false korundu. HTTPS/SSR/feed, scheduler 47,298 s ve auth 13/13 geçti. Ücretli yükseltme, gerçek emir, migration veya üretim DB restore işlemi yok; kalan disk 724.676.608 B. Sıradaki P2-4; dış alarm/emir kabulü erteli |

| 2026-09-13 | P2-4 | Yerel doğrulama → ilk üretim geçişi → açık SQL kabulü | Ham bildirim filtresi, 12 DB-worker başarı/hata/iptal ve 4 frontend testi; ilk Python 722/skip 1, frontend 99 ve büyük veri ölçümü geçti. `aadde728` CI 34742590742 ve imaj yayını 34742865556 başarılı; ilk üretim sağlık/auth kabulü tamam. Onaylanan dört eski günlük kaldırıldı, diğer sekiz sunucu dosyası ve 12 dosyanın bilgisayar arşivi korundu; taze SQLite yedeği bağımsız restore edildi. Dış eşzamanlı kabulde etiket listeleri zaman aşımına uğradı. Kısmi indeks ve tam sayım düzeltmesiyle Python 735/skip 1 ve yeni büyük veri ölçümü geçti; CI ve ikinci üretim kabulü açık. Ücretli yükseltme veya borsa emri yok |

| 2026-09-13 | P2-4 | SQL düzeltmesi → CI/imaj → ikinci üretim → Doğrulandı | `279aa9f`; CI 34745255161 / imaj 34745419330 başarılı. Taze harici SQL gzip tam restore edildi; kaynak RAM'den aktarıldı, indeks dahil sabit disk payları korundu. Yalnız kısmi indeks eklendi; ana sayılar/PG korundu. Beş servis healthy/restart0, auth 13/13; aynı eşiklerle 24 REST / 3 WSS, üç heartbeat ve socket temizliği geçti. BELES 594 / COK 469 / stats 2438 ms; yeni borsa işlemi veya ücretli yükseltme yok. P3-1 kodu başlamadı |

| 2026-09-13 | P3-1 ilk adım | İncele → düzelt → yerel doğrula | COMBO sıfır/eksik ayrımı ve sonlu puanlama; altı gerçek hesaplayıcı/alarm regresyonu. Eski kodda beş hata; yeni kodda 105/105, lint/type/build/standalone geçti. Backend/Pine/HUNTER aynı; tüm P3 açık. CI/imaj ve frontend-only üretim kapasite kabulü bekliyor |

| 2026-09-13 | P3-1 ilk adım | Commit/push → CI/imaj → tek dosyalık kapasite önerisi | `967f137`, CI 34746909758 / imaj 34747132287 başarılı. Yalnız frontend iki yeni katmanı ölçüldü; sabit paylarla ~60 MiB eksik. Yedeği doğrulanmış tek ARCHIVED günlük ~72 MiB sağlayabilir; öneri 9f88d6e7… için yeni açık onay bekleniyor. Silme/pull/restart yapılmadı; üretim 279aa9f ve DRY_RUN/false/false |

| 2026-09-13 | P3-1 ilk adım | Yeni onay → tek günlük temizliği → frontend deploy kabulü | Tek ARCHIVED günlük kaldırıldı, özel yedek ve diğer yedi günlük korundu. Frontend967 üretimde; backend/Compose279 ve dört servis aynı. Sekiz GET/SSR200 ve dış16GET/13asset geçti; son boş alan562.618.368B; tüm P3 açık |

| 2026-09-13 | P3-1 ikinci adım | İncele → düzelt → doğrula → belgeyi güncelle | Gerçek Python/TS sentetik ölçümü; iki Pine continuation guard'ı. 773 Python/skip1 uyarısız, frontend105 ve lint/typecheck geçti; Pine eski kaynak10hata→yeni30+22geçti. Üretim frontend967/backend279 korunur; kaynak/kanıt yayını tamSHA/CI ve ayrı release-record ile bağlanır. Yeni Pine dış kabulü ile muhasebe/zaman/backtest işleri açık |

| 2026-09-13 | P3-1 ikinci adım | CI → canonical kaynak yayını → Doğrulandı | 48be08e, CI34749745272; 11 dosya488.483B +12.462B kayıt hash/gzip/HTTPS ile doğrulandı. Beş servis/config aynı; container/DB/Pine dış kopyası değiştirilmedi. Kaynak kabulü indicators/release-record.json içinde |

| 2026-09-13 | P3-1 üçüncü adım | İncele → düzelt → doğrula → kapasite önerisi | Alış maliyeti dahil FIFO PnL, ayrı komisyon/kayma, input atomikliği ve kesirli nakit sınırı; 57 hedefli/tam830-skip1 uyarısız. CLI test/provider çalışması yok. Yeni tek arşiv dosyası önerisinin yedeği doğrulandı; 528MiB altında disk nedeniyle kaynak yayını ve yeni silme onayı açık |

| 2026-09-13 | P3-1 üçüncü adım | Yeni onay → tek günlük temizliği → kaynak kabulü | Final öneri60405933 ve yeni yetki eb212130; yedek yeniden doğrulandı, yalnız tek ARCHIVED günlük kaldırıldı. Kod7787fc1/CI34752893586 başarılı, altı kaynak/kanıt dosyası aktarıldı. Beş servis/config aynı, HTTPS200, son622.800.896B boş alan. Adım4 yalnız salt okunur incelendi; kodu başlamadı, tüm P3 ve dış kabul açık |

| 2026-09-13 | P3-1 dördüncü adım | İncele → düzelt → yerel doğrula | İki eski RED; sabit günlük veri, dahil start/end, UTC as_of, konservatif kapanış ve sonraki gerçek Open yürütmesi. 48 yeni/tam878-skip1 uyarısız; FIFO/gap/cutoff/DST/input atomikliği/worker tekfetch geçti. Gelişen HTF politikası ve maliyet modeli korundu; ortak nakit kronolojisi/WFA açık. CI ve kaynak yayını ayrı execution release kaydına bağlanır |

| 2026-09-13 | P3-1 dördüncü adım | CI → kaynak yayını → kabul | f937744 / CI34755778327 başarılı; altı dosya 371.071 B ve 10.982 B receipt hash ile doğrulandı. Beş servis/config aynı, dış HTTPS 200, 620.085.248 B boş alan. Kapanış belgesi execution-closure kaydına bağlanır. npm 11 bildirimi yeni P1-G2; shared-cash/WFA ve tüm P3 açık |

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

**P3-1 dördüncü adım kapandı: f937744 / CI 34755778327 ve altı kaynak/kanıt dosyasının sunucu hash kabulü tamam. Yeni 48/tam 878-skip1 uyarısız; servisler, frontend967/backend279 ve DRY_RUN korunuyor. Bu kapanış belgesinin kendi SHA/CI/aktarım kaydı execution-closure/release-record.json içindedir. Yeni npm güvenlik bildirimi P1-G2 olarak sırada; sonraki backtest işi ortak nakit kronolojisi ve tutarlı çoklu sembol fiyatlama. Ek silme/ücretli yükseltme yok; benchmark/WFA, yeni Pine dış kabulü ve tüm P3 açık, gerçek/testnet emirleri erteli.**
