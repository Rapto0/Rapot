# Rapot Devam Planı

**Güncel özet: 21 Eylül 2026.** Bu dosya, sonraki çalışmaya başlamak için okunur.
Çalışma kuralı: **incele → düzelt → doğrula → belgeyi güncelle**.
Teknik ayrıntılar [belge indeksinde](README.md), çalışma kuralları
[AGENTS.md](../AGENTS.md), önceki planın eksiksiz metni
[tarihsel arşivde](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md) bulunur.
Arşivdeki eski “bekliyor” ifadeleri güncel iş veya yeni onay talebi değildir.

## Kaldığımız nokta

- **Arayüz iyileştirmeleri (UI-1) tamamlandı ve üretimde.** Mobil tam menü,
  masaüstü menü adları, klavye odağı, açık piyasa seçimiyle sembol arama ve
  dar ekranda grafik/izleme paneli düzeni uygulandı. Altı yeni regresyonla
  119 frontend testi ve 320–1280 px yerel tarayıcı kontrolü geçti.
  [Davranış ve kabul sınırları](FRONTEND.md#gezinme-ve-arama-iyileştirmesi--21-eylül-2026).
  Kaynak `7b90365`; beş CI job'ı, imaj yayını ve yalnız frontend rollout'u geçti.
  Canlı tarayıcıda menü, Escape ile odak dönüşü ve boş arama geri bildirimi doğrulandı.
- **P0–P3 geliştirme işleri tamamlandı.** P1-3'ün gerçek alarm/emir dış kabulü
  kullanıcı kararıyla erteli; aşağıdaki tablo bu ayrımı korur.
- **P3-1 kapandı:** altı kod adımı, sabit verili gerçek CLI ve güncel Pine
  derleme/grafik kabulü tamam. Motorların tam eşdeğerliği veya gerçek kazanç
  doğrulanmış sayılmaz.
- **P3-2 kapandı:** backup branch'teki beş commit ve 18 frontend dosyası
  incelendi; aktarım seçilmedi. Backup ref ve kayıtlı iç worktree korundu.
- **Önceki kaynak işi repo temizliği:** `abc918ededf6b491ea6cda707fb1d1005d0eaa84`,
  [CI 35640081565](https://github.com/Rapto0/Rapot/actions/runs/35640081565),
  beş job başarılı. 26 atıl/tekrarlı dosya, beş doğrudan npm bağımlılığı
  (toplam 23 paket) ve eski ortam/cache çıktıları kaldırıldı. Rehberler `docs/`
  altında; kök ve bileşen giriş README'leri uygun yerlerinde.
- **Temizlik doğrulaması:** 996 Python testi geçti, bir isteğe bağlı performans
  testi atlandı; 113 frontend testi, lint, typecheck, build ve standalone
  HTTP/WS kontrolleri geçti. npm audit: **482 paket / 0 bulgu**.
- Temizlikte yaklaşık **1,16 GB dosya içeriği** kaldırıldı; bu net disk boşluğu
  ölçümü değildir. `.tmp_pytest/pytest-of-memet` Windows erişim engeli nedeniyle
  kaldı. Aktif `.venv`, frontend bağımlılıkları, DB'ler, yedekler ve kanıtlar korundu.
- Yerel temizlik çalışan imajları değiştirmedi. **Git HEAD ile üretim sürümü
  aynı kabul edilmez;** son üretim kimlikleri aşağıdadır.

## Sıradaki işler ve ertelenen kabul

P0–P3 geliştirme listesi ve UI-1 kapalıdır. Kullanıcının seçtiği arayüz
iyileştirmelerinde sonraki aday ana sayfadaki veri güncelliği/hata bilgisidir;
UI-1 paketinde veri akışı değiştirilmedi.
Kapatılmış işleri veya eski onay bekleme kayıtlarını yeniden başlatma.

| Konu | Durum / devam koşulu |
|---|---|
| Gerçek TradingView alarmının webhook'a teslimi | Erteli; kullanıcı yeniden seçtiğinde ele alınır. Webhook URL erişimi için şu an yanıt beklenmiyor. |
| ALL/FIRST, saat filtresi, futures/standart olmayan grafik korumaları | Güncel kaynağın bu runtime matrisi erteli. BTCUSDT/standart mum kabulü bunları kapsamaz. |
| Testnet BUY → FIFO SELL → reconcile ve gerçek emir | Erteli; ayrı hesap/DB/kapsam ve somut emir yetkisi gerekir. Hazır test araçlarını kendiliğinden çalıştırma. |
| Eski pytest önbelleği | Yalnız yerel temizlik kalıntısı; Windows erişim engeli var. Uygulama geliştirmesini engellemiyor. |
| Wrapper'ların fiziksel kaldırılması | Otomatik sıradaki iş değil. Dış tüketici göçü ve süreç kullanım kanıtı olmadan 12 wrapper korunur. |

Gerçek sağlayıcı/kazanç, tam Python/TypeScript/Pine eşdeğerliği ve opsiyonel
PNG/paralel runner kabulü iddia edilmez. Ana dashboard Trade verisi ile Spot
middleware emirleri ayrı veri kümeleridir. **DRY_RUN'da geçerli webhook bile
simülasyon order/tranche yazabilir;** üretime deneme alarmı göndermek salt okunur
kontrol değildir. Dış kabul ayrı test DB'si ve execution/account scope'unda yapılır.
Reconciliation **REPORT_ONLY** kalır; eski belirsiz envanter otomatik olarak
bir hesaba atanmaz veya onarılmaz. Geçici dış test servisleri kapalıdır.

Hazır ama çalıştırılmamış `remote-p13-testnet-acceptance.py` taslağı:
BTCUSDT testnet, **25 sanal USDT × 2 BUY + 2 FIFO SELL, en fazla dört emir**;
partial/unknown/expired/eksik komisyon durumunda durur. Capture aracı da dışa
açılmadı. Bu taslak sınırlar kendi başına emir veya alıcıyı açma yetkisi değildir.

## Kapsam ve yetki kaydı

- Kullanıcı geliştirme, doğrulama, otomatik commit/push ve uygun zamanda
  doğrulanmış deploy yetkisi verdi. Aynı kapsam için yeniden onay istenmez.
  Root SSH erişim kurulumu ve alan adı olmadan IP HTTPS kurulumu 9 Eylül'de onaylandı.
- 10 Eylül kararıyla borsayı ilgilendiren dış kabul ertelendi. Bu karar
  testnet/gerçek emir yetkisi vermez; diğer geliştirme işleri devam edebilir.
- **Ücretli yükseltme yapılmayacak; mevcut $6/ay plan korunur.** Her yayın
  öncesinde **528 MiB (553.648.128 bayt)** sabit disk rezervi ile aktarım,
  imaj, yedek ve kayıt payları yeniden hesaplanır. Rezerv düşürülmez.
  Yalnız belge yayınının aktarım/kayıt bütçesi ayrıca **2 MiB** ile sınırlıdır.
- Önceki sunucu silme onayları yalnız listelenmiş tam dosya yolları ve
  öneri/onay hash'leri içindi. Diğer yedekler, günlükler, imajlar, release'ler
  veya veriler için genel silme yetkisine dönüşmez. Özel bilgisayar yedekleri korunur.
  [Özgün ifadeler, yollar ve hash'ler](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md#kapsam-ve-yetki-kaydı).
- 21 Eylül repo temizliği talimatı, gereksiz **yerel proje** dosyalarını silmeyi
  ve Markdown rehberlerini toplamayı kapsadı; sunucu verisi/yedeği silme yetkisi eklemedi.
- Planın sadeleştirilmesi `8a05b11` ile tamamlandı; eski metin arşivde bütünüyle
  korunur. Son kullanıcı seçimi arayüz iyileştirmeleridir; dış kabul ertelemesi sürer.
- Deploy yetkisi; gerçek/testnet emri, üretim verisi silme/geri yükleme,
  force-push veya sunucudaki bilinmeyen değişiklikleri ezme yetkisi değildir.
  Belgenin kendisi yeni yetki üretmez. Gerçek kullanıcı kapsam değişikliği kayda geçirilir.
- Anahtar, parola, token, `.env` içeriği ve gerçek DB'ler Git'e/rapora alınmaz.
  Yerel/sentetik test, gerçek ortam gözlemi ve dış kabul birbirinin yerine geçmez.

## Son üretim ve yayın kanıtları

Bunlar **son kaydedilmiş kabulün** değerleridir; yeni yayın için taze sunucu
kontrolü gerekir. Uygulama Docker Compose ile çalışır; eski PM2/API launcher'ları
repodan kaldırıldı. Dağıtım ve geri dönüş adımları [DEPLOY.md](DEPLOY.md) içindedir.

| Alan | Son kayıt |
|---|---|
| Sunucu / erişim | `root@138.68.71.27`, IP üzerinden HTTPS |
| Frontend kaynak | `7b903655e2685f294aed86cca2cd97de0102d2ca` |
| Frontend imaj | `sha256:dc3c65bf2fda404559260770a5cdf9cf459782c3a897a8796fa83bcec8fbca61` |
| Backend / Compose / current kaynak | `279aa9fea99b520e661b43f104a2bf4791893ac3` |
| Backend imaj | `sha256:9be0fdb6097f52bf97730f44c86d28c24e2c0cea1fe181e7e8fd668177fdb034` |
| Veri / kaynak pointer | `/var/lib/rapot/main` ve `/opt/rapot/current`; operator kaynak kopyası bunlardan ayrıdır |
| Çalışma modu | `MW_EXECUTION_MODE=DRY_RUN`, `MW_TRADING_ENABLED=false`, `MW_BINANCE_LIVE_ENABLED=false`; AI kapalı |
| Son uzak kabul | 21 Eylül 19:58:08 UTC; beş servis sağlıklı, restart0; HTTPS API/bot 200; boş alan 1.193.254.912 bayt |

Son kayıtlar:

- **UI-1 üretim kabulü:** kaynak `7b90365`,
  [CI 35645956442](https://github.com/Rapto0/Rapot/actions/runs/35645956442) ve
  [imaj yayını 35646872042](https://github.com/Rapto0/Rapot/actions/runs/35646872042)
  başarılı. `/root/rapot-ops/20260921-ui-frontend/deployment.json` durumu **verified**;
  uzak/yerel SHA256 `50d433aa5f42768426800db386e6534b6b92cdd7101d264518352aca9bc91a15`.
  Sekiz sağlık/sayfa kontrolü, iki grafik rotası ve 11 JS + 1 CSS dosyası geçti.
  Runtime SHA256 `0efe0a4886cb0b102c0c04d434705b6fdeb2ed91095ca7573c2c0e39c8342ae7`.
  Diğer dört servis, env/Nginx ve backend/Compose/current korundu; eski frontend
  `bbd9377` / `e312d7aa…` geri dönüş için duruyor. 528 MiB rezerv korundu;
  migration, sunucu temizliği veya alarm/emir testi yapılmadı.
  Yerel kanıtlar: `runtime-data/ui1-local-validation.json`,
  `runtime-data/ui1-http-acceptance.json`, `runtime-data/ui1-browser-acceptance.json`.
- **P3-1 son kod:** `07b7e53dcad9301f56a0da097b36a81541584219`,
  [CI 35502828849](https://github.com/Rapto0/Rapot/actions/runs/35502828849).
  `/root/rapot-ops/20260920-p31-final/release-record.json`;
  SHA256 `82d32c6c23cc2ea42082dccd3647e704917539e4bb7c6e912543258d6fc75f43`.
- **Pine/P3-2 belge kapanışı:** `420ea3bf0a2645760ab726a73050b7a650c8869d`,
  [CI 35636249462](https://github.com/Rapto0/Rapot/actions/runs/35636249462).
  `/root/rapot-ops/20260921-p31-p32-closure/release-record.json`;
  SHA256 `28bc324e10857d4dbd2c46a3acb94ff67525d0bcf14d69a335880c810b59f2c4`.
  Durum **verified**; “yayın bekliyor” şeklindeki eski notlar artık tarihsel.
- **Repo temizliği:** `runtime-data/20260921-repository-cleanup.json`,
  `runtime-data/20260921-cleanup-pytest.log` ve
  `runtime-data/20260921-cleanup-npm-security/` yerel kanıtları tutar;
  sunucu rollout'u yapılmadı.
- **Önceki frontend kabulü:** `/root/rapot-ops/20260920-p1g2-frontend/deployment.json`;
  belge kapanışı `/root/rapot-ops/20260920-p1g2-closure/release-record.json`.
- **Planın sadeleştirilmesi:** `8a05b11`,
  [CI 35642396338](https://github.com/Rapto0/Rapot/actions/runs/35642396338) başarılı;
  `/root/rapot-ops/20260921-continuation-plan/release-record.json` **verified**.
  SHA256 `be27d7fb235217f2ac3cc3891f6751c7253359943c1b400edf7065656ca1576d`.
  UI-1 sonrası belge kapanışı Git'te tutulur; ayrı sunucu belge aktarımı gerekmez.

Eski deployment, rollback, DB sayımı, güvenlik advisory, kapasite, yedek,
öneri/onay ve alt adım hash'leri [tam arşivde](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md)
ve ilgili `runtime-data/` / `/root/rapot-ops/` kayıtlarındadır. Bu kayıtlar yeni
sunucu durumu gibi okunmaz ve hash ile bağlı geçmiş kopyalar yeniden yazılmaz.

## Tamamlanan işlerin özeti

| İş | Sonuç / ayrıntı kaynağı |
|---|---|
| P0-1 | Python 3.12 ve kilitli ortam; sentetik ayarlar/DB/cache, ağsız test tabanı. |
| P0-2 | Ana API JWT/admin kontrolleri, limitler ve ayrı middleware yönetim kimliği. [Erişim tablosu](../README.md#security-notes). |
| P0-3 / P0-4 / P1-1 | Execution/account scope, Decimal/FIFO, kalıcı dispatch/recovery, idempotency/replay ve komisyon muhasebesi. [Middleware](MIDDLEWARE.md). |
| P1-2 | Compose, veri göçü, HTTPS/auth/WSS ve sertifika yenileme kabulü. [Dağıtım](DEPLOY.md). |
| P1-3 | Yerel/CI, grafik ve izole VPS HTTPS/simülasyon kabulü tamam; gerçek alarm/filtre/emir dış kabulü **erteli**. [Pine sözleşmesi](PINE_CONTRACT.md). |
| P1-4 | AI ilişkileri ve scan history lifecycle/sayaçları düzeltildi, üretim kabulü geçti. |
| P1-5 | Süreçler arası SignalFeed, bağımsız realtime ve scanner eşdeğerliği doğrulandı. [Mimari](ARCHITECTURE.md). |
| P1-6 | PnL/null/quantity, bot durumu ve settings kapsamı düzeltildi; üretim/UI/WSS kabulü geçti. |
| P1-7 | Kısa HUNTER serisinde ATR hatası giderildi; eşikler değiştirilmedi. |
| P2-1 | CSV, yerel alarm ve chart URL davranışları doğrulandı. [Frontend](FRONTEND.md). |
| P2-2 | Canonical paket/belge sınırları tamam; 12 wrapper korunuyor. [Harita](PACKAGING_REFACTOR_MAP.md), [kaldırma kapıları](WRAPPER_DEPRECATION_SCHEDULE.md). |
| P2-3 / P0-G1 | Ruff/CI kapsamı, UTC sözleşmesi, atıl kod temizliği ve standalone debug varsayılanı düzeltildi. |
| P1-G1 | Python advisory incelemesi, PyJWT HS256 geçişi ve kilitli bağımlılık temizliği; üretim/auth kabulü geçti. [Tarihsel ayrıntı](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md#p1-g1--python-bağımlılık-güvenliği). |
| P2-4 | DB-worker/SQL indeks düzeltmesi; 24 REST / 3 WSS eşzamanlı üretim kabulü. [Kısmi indeks ve migration sınırı](DB_MIGRATION_POLICY.md). |
| P1-G2 | Frontend bağımlılık güncellemesi ve 20 Eylül frontend-only üretim/native kabulü. Aşağıdaki özet. |
| P3-1 | Altı kod adımı, CLI ve 21 Eylül güncel Pine grafik kabulü tamam. Aşağıdaki özet. |
| P3-2 | Backup'tan aktarım seçilmedi; `backup/pre-da7d452-rollback` korundu. [Karar ve 18 dosya](BACKUP_BRANCH_REVIEW.md). |

### P3-1 — Backtest ve strateji eşdeğerliği

1. Frontend COMBO geçerli sıfırı korur; eksik/NaN/sonsuz değerler puan üretmez.
2. Gerçek Python/TypeScript ölçümü ve Pine EMA/ATR seed-sonrası sınır düzeltmesi.
3. Alış giderlerini içeren FIFO maliyeti ve gerçekleşmiş PnL muhasebesi.
4. Sabit aware `as_of`, kapanmış günlük prefix ve sonraki gerçek Open yürütmesi.
5. Ortak nakitli çoklu sembol kronolojisi, günlük NAV ve fiyat eskiliği metadata'sı.
6. Döneme uyumlu benchmark, doğru adlandırılmış rolling al-tut analizi ve
   gerçek COMBO/HUNTER ile izole CLI JSON/CSV/SVG/XLSX kabulü.

Sözleşmeler: [karşılaştırma](STRATEGY_COMPARISON.md), [muhasebe](BACKTEST_ACCOUNTING.md),
[yürütme](BACKTEST_EXECUTION.md), [portföy](BACKTEST_PORTFOLIO.md),
[benchmark](BACKTEST_BENCHMARK.md), [pencereler](BACKTEST_WINDOW_ANALYSIS.md),
[CLI](BACKTEST_CLI.md). Eski `WalkForwardAnalysis` uyumluluğu optimizasyon/eğitim değildir.

**21 Eylül Pine kabulü:** güncel 1.091 satırın SHA256'sı editörde ve yeniden
açılan özel scriptte eşleşti; BINANCE:BTCUSDT / standart mum / 1D üzerinde
`TF OK`, HMax15/CMax4 ve skor tablosu görüldü. Özel script
`Rapot P3-1 kabul 2026-09-21 59ade54a`; [tam hash ve gözlem](PINE_RUNTIME_ACCEPTANCE.md).
Bu script `strategy.entry/order/exit` emri içermez; grafik kabulü backtest
kazancı veya gerçek alarm teslimi kanıtı değildir.

### P1-G2 — Frontend bağımlılık güvenliği takibi

Next/eslint 16.3.5 ve gerekli geçişli bağımlılıklar güncellendi. 20 Eylül'de
`bbd9377` frontend-only yayını; Linux/musl native metadata, HTTPS/RSC ve
statik dosya kabulü geçti. O gün npm **505/0**; 21 Eylül yerel temizlik sonrası
lock **482/0**. Bunlar farklı kaynak/ortam kayıtlarıdır.
[Advisory ve native kabul ayrıntıları](FRONTEND_DEPENDENCY_SECURITY.md).
Native kabul metadata kontrolüdür; exploit veya görüntü decode testi değildir.

Frontend audit'i bütün prod/dev/optional/peer lock kapsamını denetler; bulgu
veya araç/rapor/kapsam hatası CI'yi başarısız yapar. Python Bandit/pip-audit
bulguları **report-only**; yeşil CI bütün güvenlik bulgularının sıfır olduğu anlamına gelmez.

## Geliştirme ortamı ve komutlar

Seçili ortam `.venv` / Python **3.12.8**, Node **20.20.2**, npm **10.9.9**.
Eski `venv` ve iki geçici araç ortamı 21 Eylül'de kaldırıldı.
`requirements-dev.lock` geliştirme/CI çözümü; `requirements.txt` ve
`requirements-security.txt` uygulama/güvenlik aralıklarıdır.

Repo kökünde PowerShell; ilk iki kurulum komutunu yalnız ortam hazırlarken çalıştır:

```powershell
uv venv --python 3.12 .venv # Yalnız .venv yoksa
uv pip sync --python .venv/Scripts/python.exe requirements-dev.lock
uv pip check --python .venv/Scripts/python.exe
.venv/Scripts/python.exe -X utf8 -B -m pytest
.venv/Scripts/python.exe -m scripts.ci_quality lint
```

Tam pytest için önce Node 20 ve frontend `npm ci` hazır olmalıdır. Gerekirse
`NODE_BINARY` tam Node 20 yürütücü yolunu seçer; karşılaştırma testi atlanmaz.
`RAPOT_STRATEGY_REPORT` mutlak JSON yolu ölçüm kanıtını isteğe bağlı üretir.
Linux/macOS'ta Python yolu `.venv/bin/python` olur.

Seçili Node/npm ile **frontend dizininde**:

```powershell
npm ci
npm test
npm run lint -- --no-cache
npm run typecheck -- --incremental false
$env:NEXT_TELEMETRY_DISABLED = '1'
npm run build
npm run test:standalone
npm run audit:dependencies
```

Windows'ta sistem Node'unu değiştirmeden alternatif:
`npm.cmd exec --yes --package=node@20.20.2 --package=npm@10.9.9 -- npm test`.
Diğer npm komutları aynı prefix ile çalıştırılabilir. `test:standalone` önceden
build ister; temizlikte `.next` kaldırıldığından gerekiyorsa yeniden derle.

Kök `conftest.py` gerçek `.env`/DB yerine geçici sentetik ortam kurar ve
HTTP/socket/curl ağını engeller. Bu izolasyon normal bot/API başlatmayı veya
keyfi native subprocess'leri kapsamaz. Uygulama modüllerini testlerin üst
seviyesinde import edip korumaları atlama. Gösterge yolları ortamda `ta` / isteğe
bağlı `pandas_ta` varlığıyla değişebilir; paket eklemek motor eşdeğerliği sağlamaz.

## Commit, push ve sunucu deploy düzeni

1. İlgili kaynakları incele, değiştir, kapsamına uygun mevcut kontrolleri yap;
   planın **güncel** durumunu güncelle ve yalnız o işe ait dosyaları commit et.
2. Push CI başlatır. Sunucu yayını için **tam commit SHA'sının başarılı CI'si**
   gerekir. Yerel Docker çalışmadığında Linux CI'deki imaj/PostgreSQL kontrolü kullanılır.
3. Sunucuda hedef, çalışan imajlar/config/DB, yerel değişiklikler ve kapasite
   yeniden okunur; gerekli yedekler bağımsız doğrulanır. Başarısız adımda yayın
   zinciri ilerlemez. Yayın sonrası veri, sağlık ve davranış kabulü ayrı kaydedilir.
4. **Yalnız belge yayını:** kaynak/bağlantı ve ilgili regression kontrolleri,
   exact CI; canonical Git blob'ları sürümlü `/root/rapot-ops/<tarih-iş>/`
   kaydına aktarılır, hash'ler karşılaştırılır. İmaj/pointer/config/DB değişmez,
   servis restart edilmez. Commit/CI ve kabul hash'leri `release-record.json`
   içinde tutulur; yalnız push, sunucu belge kabulü değildir.
5. `.github/workflows/deploy.yml` imaj yayımlar, sunucu deploy'u yapmaz.
   `scripts/deploy.ps1` doğrulanmış SHA için komutları yazdırır, SSH çalıştırmaz.
   [Dağıtım rehberi](DEPLOY.md) ve yukarıdaki yetki/rezerv sınırları uygulanır.

## Ara verdikten sonra devam etme

1. Önce bu dosyanın **Kaldığımız nokta**, **Sıradaki işler** ve **Kapsam** bölümlerini oku.
2. Git HEAD, çalışma ağacı ve gerekiyorsa gerçek runtime'ı kontrol et; son kayıtları
   güncel durum varsayma. En yeni kullanıcı talimatını mevcut yetkilerle birlikte uygula.
3. Konuyla ilgili teknik rehberi aç. Geçmiş bir kabul/karar/hash gerektiğinde
   [tarihsel arşivde](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md) ilgili iş başlığına git.
4. İş bitince burada sonuç, kapsam, doğrulama ve sıradaki adımı kısa tut.
   Yeni ayrıntılı raporu ilgili teknik belgeye/kanıt kaydına bağla; eski uzun
   ilerleme günlüğünü tekrar ana plana kopyalama. Eksik kabulü tamamlandı olarak işaretleme.
