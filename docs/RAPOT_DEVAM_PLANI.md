# Rapot Devam Planı

**Güncel özet: 4 Ekim 2026.** Bu dosya, sonraki çalışmaya başlamak için okunur.
Çalışma kuralı: **incele → düzelt → doğrula → belgeyi güncelle**.
Teknik ayrıntılar [belge indeksinde](README.md), çalışma kuralları
[AGENTS.md](../AGENTS.md), önceki planın eksiksiz metni
[tarihsel arşivde](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md) bulunur.
Arşivdeki eski “bekliyor” ifadeleri güncel iş veya yeni onay talebi değildir.

## Kaldığımız nokta

- **Borsapy entegrasyonu:** Kullanıcı, mevcut TradingView Premium + BIST veri
  paketiyle README'deki 22 özellik ailesini kendi sitesinde istedi. borsapy
  0.11.0 sabitlendi; yönetici `/research` ekranına 51 işlem, bağlantı yönetimi,
  kayıtlı sorgu/portföy, grafik/replay ve akış/Pine gösterge kimliği yüzeyleri
  eklendi. `/chart` özel TradingView kaynağını seçebilir. Scanner ve günlük BIST
  alarm adaptörü hazır; `BORSAPY_USE_FOR_BIST` varsayılan false kalır. Genel Pine
  kaynak çalıştırıcısı veya gün içi BIST alarm takvimi eklenmedi. Kimlikler
  sunucuda şifrelenir; özel fiyatlar genel grafik/önbellek yoluna taşınmaz.
  [Kapsam ve kabul](BORSAPY_INTEGRATION.md). Canlı hesap/piyasa testi kullanıcının
  isteğiyle piyasa açılışına ertelidir. Python CI'da **1.204 test geçti**, bir
  performans testi atlandı; üç eski bağımlılık uyarısı kaldı. 227 frontend
  testi, lint/typecheck, build/standalone ve sentetik tarayıcı kabulü geçti.
  Tarayıcıda 51 işlem, kayıt, replay, akış başlat/durdur, özel grafik kaynağı,
  bağlantı sekmesi ve 320 px görünüm kontrol edildi. Bu kayıt henüz üretim
  yayını değildir. İlk `39d4243` kaynağının Python/lint işleri ve Linux borsapy
  runtime kabulü geçti; frontend CI yeni `braces` bildirimiyle durdu. Next lint
  bağımlılığının dar uyarlamasıyla tam audit 469/469 paket, sıfır bulgu verdi;
  bütün Next kuralları ve gerçek tüketici davranışı sınandı.
  [Güvenlik düzeltmesi](FRONTEND_DEPENDENCY_SECURITY.md). İlk kaynak üretime alınmaz.
  Son uygulama kaynağı **`4b15335`** için beş CI işi ve iki imaj yayın işi geçti.
  Özel yerel yedek ayrı veritabanında doğrulandı. Sunucuya geçiş, aşağıdaki
  **iki eski frontend imajına özel temizlik onayını** bekler; silme/pull/restart
  yapılmadı. Mevcut üretim sürümü korunuyor.
- **Sunucu alarmları tamamlandı ve üretimde:** Kullanıcı, TradingView benzeri alarm
  yönetiminin bütünüyle kendi sitesinden yapılmasını seçti. `/alarms` artık
  yöneticiye ait kalıcı kuralları ve teslim geçmişini yönetir; API kapalı mumları
  tarayıcıdan bağımsız değerlendirir. RSI(14), Williams %R(14), COMBO ve HUNTER;
  kriptoda 1h/4h/1d, BIST'te günlük periyot desteklenir. Genel Pine çalıştırıcısı
  eklenmedi. Eski kurallar `/alarms/local` altında korunur ve otomatik etkinleşmez.
  [Sözleşme ve sınırlar](SERVER_ALARMS.md). Tam yerel paket 1.093 Python
  testiyle geçti (bir performans testi atlandı); son BIST periyot kısıtıyla
  99 alarm + OpenAPI testi ayrıca geçti. 206 frontend testi, Python lint/format,
  frontend lint/typecheck, build/standalone ve sentetik tarayıcı kabulü geçti.
  Üç Binance/websockets bağımlılık uyarısı kaldı. `d4d2b65` kaynağının beş CI
  işi ve iki imaj yayın işi geçti; yalnız API/frontend güncellendi. Canlı
  yönetici GET'leri, çalışan alarm döngüsü, Binance/BIST kapalı mum hesaplaması,
  HTTPS sayfalar/statik dosyalar ve erişim sınırı doğrulandı. Mevcut yedi
  tablonun şeması korundu, üç yeni alarm tablosu boş olarak eklendi.
  Canlı kullanıcı alarmı veya Telegram test bildirimi oluşturulmadı.
- **UI-3: Sinyaller ve Tarayıcı tamamlandı ve üretimde.** Etiketli filtreler,
  tekli/tümü temizleme, yüklenen kayıt kapsamı, ayrı boş/hata/bekleme durumları
  ve klavye erişimi eklendi. Tarayıcı yenileme hatasında mevcut satırları korur;
  bozuk/engellenen tarayıcı depolaması açıklanır. 37 yeni regresyonla **192
  frontend testi**, lint/typecheck, build/standalone ve 320/768/1280 px yerel
  tarayıcı kabulü geçti. Kaynak `db534fb`; beş CI işi, imaj yayını ve yalnız
  frontend rollout'u başarılı. Canlı iki ekranda filtre/temizleme, dar ekran
  ve Tarayıcı dialog klavye kabulü geçti. Ek fiyat bilgileri beklerken mevcut
  satırların uyarıyla görünmesi doğrulandı; tüm sağlayıcı yanıtlarının
  tamamlandığı iddia edilmez.
  [Davranış ve sınırlar](FRONTEND.md#sinyaller-ve-tarayıcı--ui-3).
  İlk kaynak `bc9bdc0` / CI `36989001597` mevcut npm lock bulgularıyla durdu;
  Next/eslint 16.3.8 ve brace-expansion 1.1.21/2.1.7 yamaları uygulandı;
  yeni tam audit **482 paket / 0 bulgu**. Test/lint/typecheck ve build yamalı
  ortamda da geçti. Başarısız kaynak üretime alınmadı; audit kapısı korunuyor.
- **Arayüz UI-2 tamamlandı ve üretimde.** Ana sayfada yükleme,
  eksik/boş yanıt, hata, son başarılı yanıt ve kripto akışı durumu görünür;
  elle yenileme var. 36 yeni regresyonla 155 frontend testi, lint/typecheck,
  build/standalone ve 320/768/1280 px yerel tarayıcı kabulü geçti.
  [Davranış ve sınırlar](FRONTEND.md#piyasa-verisi-durumları--ui-2).
  Kaynak `13e5fbb`; exact CI, imaj yayını ve yalnız frontend rollout'u başarılı.
  Canlı tarayıcıda fiyatların görünmesi, durum/alım süresi ve elle yenileme doğrulandı.
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

P0–P3 geliştirme listesi ve arayüz UI-1/UI-2/UI-3 kapalıdır. 2 Ekim sunucu
alarmları üretimdedir; son kullanıcı seçimi 4 Ekim borsapy araştırma ve veri
entegrasyonudur. Kullanıcı canlı piyasa testlerini daha sonra yapmayı seçti.
Yerel doğrulama, imaj/disk bütçesi ve yayın kaydı birbirinden ayrı tutulur.
Kapatılmış işleri veya eski onay bekleme kayıtlarını yeniden başlatma.

| Konu | Durum / devam koşulu |
|---|---|
| Borsapy canlı kabulü | TradingView oturumu, gerçek fiyat/mum zamanı, tarihsel kapsam ve şirket işlemleri piyasa açıkken karşılaştırılacak. EVDS/X ayrı kimlik ve kabul ister. |
| Borsapy üretim yayını | Son `4b15335` kaynağının CI ve yayın kanıtları hazır. 528 MiB rezerv, 64 MiB WAL/log ve 2 MiB kanıt payıyla 1.083.183.536 bayt gerekir; 985.182.208 bayt boş, 98.001.329 bayt eksik. Aşağıdaki iki eski frontend imajının kaldırılması için özel onay beklenir. Exact imaj maliyeti ve rezerv kontrolü temizlikten sonra yenilenir; sunucu planı yükseltilmez. |
| Eski Python pinlerinin yeni güvenlik bildirimleri | 134 paketlik report-only taramada 5 paket/16 ham bulgu; 22 borsapy ek paketinde bulgu yok. anyio/PyJWT/soupsieve/urllib3 runtime ve virtualenv geliştirme pinleri için ayrı taban imaj güncellemesi gerekir. [İnceleme ve düzeltme sınırları](BORSAPY_INTEGRATION.md). Yeşil güvenlik işi sıfır bulgu değildir. |
| Canlı veri yükleme gecikmesi | UI-3 kabulünde Tarayıcı ek fiyat/metrikleri bekledi; Sinyaller tekrar açılışta bekledikten sonra 300 kaydı yükledi. Arayüz durumları doğru gösterildi; gecikmenin nedeni ve sağlayıcı performansı bu pakette çözülmedi. |
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
- 4 Ekim: borsapy README özelliklerinin siteye eklenmesi istendi. Mevcut
  TradingView Premium ve BIST paketi kullanılacak, yeni abonelik alınmayacak.
  Gerçek hesap/sağlayıcı testleri piyasa açılışına erteli; çevrimdışı yazılım
  doğrulamaları gerçek veri kabulü sayılmaz.
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
  korunur. Son kullanıcı seçimi sunucu alarm yönetimidir. Bu seçim gerçek
  işlem emri veya kullanıcının yerine canlı alarm oluşturma yetkisi değildir;
  TradingView/testnet dış kabul ertelemesi sürer.
- Deploy yetkisi; gerçek/testnet emri, üretim verisi silme/geri yükleme,
  force-push veya sunucudaki bilinmeyen değişiklikleri ezme yetkisi değildir.
  Belgenin kendisi yeni yetki üretmez. Gerçek kullanıcı kapsam değişikliği kayda geçirilir.
- Anahtar, parola, token, `.env` içeriği ve gerçek DB'ler Git'e/rapora alınmaz.
  Yerel/sentetik test, gerçek ortam gözlemi ve dış kabul birbirinin yerine geçmez.

## Son üretim ve yayın kanıtları

### 4 Ekim — borsapy yayına hazır, sunucu değişikliği bekliyor

- Uygulama kaynağı `4b15335f00f30e65a21899e73af47c508f395706`.
  [CI 37159767810](https://github.com/Rapto0/Rapot/actions/runs/37159767810)
  beş başarılı iş; [imaj yayını 37159767909](https://github.com/Rapto0/Rapot/actions/runs/37159767909)
  iki başarılı iş ve istenmemiş source-only API delta işi skipped.
- API: `ghcr.io/rapto0/rapot/backend@sha256:b9695f5f78ccb6f16112578c54fb9fb2de7ce6a3dc4c0836c3da7deacf7adf14`.
  Frontend: `ghcr.io/rapto0/rapot/frontend@sha256:f569c7e24e9d7a9efb8918406e0fcc05137146c96fe3715a2d0f308b4c06428e`.
  Linux kabulü 98 mevcut paketin sürüm/dosya hash'ini korudu, tam 22 paket
  ekledi; 255 kaynak dosyası, native import, şifreleme, SQLite ve 8 araştırma/
  yerel gösterge kontrolü ağsız geçti. Bu, gerçek sağlayıcı kabulü değildir.
- Offhost yedek 149.948.452 bayt; SHA256
  `4703b369249a1f6da32fc6697ac294d9e491d15bb4418e57b8e32a02fbdbfbf3`.
  Bağımsız özel yerel restore 1.128.845.312 bayt; 10 tablonun şeması, integrity
  ve tipli satır fingerprint'leri eşleşti. Üretim DB'si geri yüklenmedi.
- 3 Ekim 23:01:54 UTC / 4 Ekim 02:01:54 TSİ ölçümü: boş alan 985.182.208,
  iki imajın ek maliyeti 460.329.392, toplam gerekli alan 1.083.183.536 bayt.
  Katmanların sıkıştırılmış ve açılmış hash'leri doğrulandı; ölçüm sırasında
  sunucuya imaj indirilmedi. Beş mevcut servis sağlıklı; DRY_RUN korunuyor.
- İncelenen temizlik **yalnız** şu iki kullanılmayan frontend imajıdır:
  `sha256:e312d7aa5e682a7835e4dc7ba3e1b4263f04a64f872f47037814ec4b0ba1f4d0`
  (`bbd9377`, 13 Eylül build) ve
  `sha256:a24bbefa443cf30f77af55161c19520f6febf1c977ef55a044fd030189bd0b41`
  (`13e5fbb`, 21 Eylül build). İkisinin de çalışan/durmuş container referansı
  sıfırdır. Mevcut API/frontend, ortak backend, PostgreSQL ve önceki frontend
  geri dönüş imajı `feaa0325…` korunur. Tahmini benzersiz kazanım 196.446.914
  bayttır; ortak katmanlar çift sayılmadı. Gerçek disk kazanımı garanti değildir.
- **Bu kayıt silme yetkisi değildir.** Teklif hash'i
  `e853b8419a957243910928212b4c1752015b6b8b75791f749ae7d8c881990722`.
  Onaydan sonra referanslar/container'lar tekrar doğrulanır; yalnız iki tam
  registry digest referansı `docker image rm --no-prune` ile kaldırılabilir.
  Genel prune, force, volume/DB/dosya silme kapsam dışıdır. Yeni boş alan yeterli
  değilse pull yapılmaz. Ardından yalnız API/frontend, mevcut geri dönüş
  imajlarıyla güncellenir; bot ve BIST scanner anahtarı mevcut durumda kalır.
- Tekrarlama kanıtları ignored `runtime-data/borsapy-deploy/` içindedir:
  `capacity.json` SHA256 `62421b30317d8b0422ff638da86b05c49cb42e6c63cfd74585bb7440be0413f8`,
  `backup-verified.json` SHA256 `34b1e8499f59af928731fa0fe29b9be9aed4f81997f6c4210f80fb874e81346b`.
  `cleanup.py` yalnız onaylı iki imaja sınırlıdır; `deploy_operator.py` yeni
  source/digest/CI/kanıt pinlerini taşır. Varsayılanları işlem yapmaz. Canlı
  guard'lar yeniden çalıştırılmalı; yedek kabulü rollout sırasında iki saatten
  eskiyse yenilenmelidir. Hiçbir gerçek hesap, piyasa, alarm veya emir testi yapılmadı.

### Mevcut üretim

Bunlar **son kaydedilmiş kabulün** değerleridir; yeni yayın için taze sunucu
kontrolü gerekir. Uygulama Docker Compose ile çalışır; eski PM2/API launcher'ları
repodan kaldırıldı. Dağıtım ve geri dönüş adımları [DEPLOY.md](DEPLOY.md) içindedir.

| Alan | Son kayıt |
|---|---|
| Sunucu / erişim | `root@138.68.71.27`, IP üzerinden HTTPS |
| API / frontend kaynak | `d4d2b6588744dc82779ef240ef292241933a20ff` |
| API imaj | `sha256:fb6bff3d29d6e8f8d088a0c23857e1eee8790742288616373249d2f8cc21026e` |
| Frontend imaj | `sha256:d0403873d7fd836709f515efa5e4f3629cb6f4fee65d03c1a41f1d6b8c7e0a8f` |
| Bot / middleware / Compose / current kaynak | `279aa9fea99b520e661b43f104a2bf4791893ac3` |
| Bot / middleware ve API bağımlılık tabanı imajı | `sha256:9be0fdb6097f52bf97730f44c86d28c24e2c0cea1fe181e7e8fd668177fdb034` |
| Veri / kaynak pointer | `/var/lib/rapot/main` ve `/opt/rapot/current`; operator kaynak kopyası bunlardan ayrıdır |
| Çalışma modu | `MW_EXECUTION_MODE=DRY_RUN`, `MW_TRADING_ENABLED=false`, `MW_BINANCE_LIVE_ENABLED=false`; AI kapalı |
| Son uzak kabul | 2 Ekim 12:55:25 UTC; beş servis sağlıklı/restart0, HTTPS API/bot 200; boş alan 1.056.694.272 bayt |

Son kayıtlar:

- **Sunucu alarmları üretim kabulü:** [CI 37004866806](https://github.com/Rapto0/Rapot/actions/runs/37004866806)
  ve [imaj yayını 37005938969](https://github.com/Rapto0/Rapot/actions/runs/37005938969)
  başarılı. `/root/rapot-ops/20261002-server-alarms/deployment.json` durumu
  **verified_health_ssr_auth_boundary**; SHA256
  `a00e71a25f9a99af713626225c6e276ecf27183f908b52a94f20da6e2aac5424`.
  Bağımsız canlı kabul 12:54:18 UTC: yönetici GET'lerinde motor `running=true`,
  son tur hatasız, Telegram yapılandırılmış; kural/olay sayısı sıfır. Dört HTTPS
  sayfası, **17 JS/CSS** ve iki anonim alarm endpoint'inde 401 doğrulandı.
  BTCUSDT/1h ve THYAO/1d genel fiyat verisinden son kapalı mum hesaplandı;
  hesaplama kontrolü gerçek bir alarm veya Telegram teslimi değildir.
  Tarayıcıda canlı alarm sayfası, API bağlı durumu, eski kurallar açıklaması
  ve `/login?next=%2Falarms` yönlendirmesi görüldü; canlı oturum açıp CRUD
  yapılmadı. Etkileşimli CRUD kabulü yalnız yerel sentetik ortamda yapıldı.
  Canlı kabul JSON SHA256
  `213c6afada409a7289b16aa7905b6e0f3978a2d3f59c8f73492a3875f142c4bd`.
  Son runtime JSON SHA256
  `acf1a881a7848366f48acc343d6c1d47c22f7e6bc3ffbcf30bce996129ab8bcd`.
  Yalnız API/frontend değişti; bot/middleware/PostgreSQL kimlikleri ve başlama
  zamanları, env/Nginx, Compose/current ve eski geri dönüş imajları korundu.
  API, değişmeyen Python bağımlılık tabanı üzerine doğrulanmış kaynak katmanı
  kullanır; normal yeniden oluşturulmuş backend imajı sunucuya çekilmedi.
  Ölçülen artımlı imaj bütçesi **114.486.874 bayt**; sabit 528 MiB rezerv,
  2 MiB kanıt ve 64 MiB runtime/WAL/günlük payıyla gereken boş alan
  **737.341.018 bayt** idi. Yayın için veri/önbellek/imaj/yedek silinmedi.
  Ana DB salt okunur sabit snapshot'tan özel bilgisayar dizinine aktarıldı;
  **149.049.104 bayt** SQL gzip, bağımsız restore ile **1.122.439.168 bayt**
  DB'ye açıldı. Integrity, şema, pragma ve yedi tablonun tipli satır hash'leri
  eşleşti. Arşiv SHA256
  `ee07b3afdf6267b082e375aa76406fe000aaae3c9611d75470f29d581faa1eff`;
  doğrulama JSON SHA256
  `cf51d4432053365fa8c6b34c39d2c0a05a77542b4decc56afd691a6cbb54522e`.
  Gerçek DB/arşiv yalnız OneDrive dışındaki özel yedek dizininde tutulur;
  sunucuda DB arşivi veya üretim restore'u oluşturulmadı. Geri dönüş eski
  API/frontend imajlarını kullanır, ek alarm tablolarını silmez.

- **UI-3 üretim kabulü:** [CI 36990139903](https://github.com/Rapto0/Rapot/actions/runs/36990139903)
  ve [imaj yayını 36991379299](https://github.com/Rapto0/Rapot/actions/runs/36991379299)
  başarılı. `/root/rapot-ops/20261002-ui3-frontend/deployment.json` **verified**;
  SHA256 `2d5e28febb7cb6843135cf89a2b1820929138b97202aaec20388bd58d55c3fb4`.
  Uzak/yerel makbuz birebir; son runtime SHA256
  `273eb2b589056d48a79471b972720dc0f823f7ecd9ab5ef2ced28241948c9b67`.
  Yalnız frontend değişti; backend/Compose/current `279aa9f`, diğer dört servis,
  env/Nginx ve eski `13e5fbb` / `a24bbefa…` geri dönüş imajı korundu. Sabit
  528 MiB rezerv ve 2 MiB kanıt bütçesi sağlandı; silme veya DB işlemi yok.
  Beş dış HTTPS sayfası (iki grafik rotası dahil), iki sağlık GET'i ve
  **20 JS + 1 CSS** geçti. Exact konteynerde Next **16.3.8**, Node **20.20.2**,
  Linux/x64 metadata'sı doğrulandı; bu native decode/exploit testi değildir.
  Canlı tarayıcıda Sinyaller 300 kayıt, Tarayıcı 325 sembol yükledi; filtre
  birleşimi, tekli/tümü temizleme, sayısal dialog Tab/Shift+Tab/Enter/Escape
  ve 320/768/1280 px taşma kontrolü geçti. Tarayıcı ek fiyat bilgilerini
  beklerken satırlar uyarıyla görünür kaldı; bu tam sağlayıcı kabulü değildir.
  Hata ve başarılı boş API yanıtı senaryoları ayrıca yerel sentetik kabulde
  sınandı. Yerel kanıtlar: `runtime-data/ui3-final-local-validation.json`,
  `ui3-local-browser-acceptance.json`, `ui3-http-acceptance.json`,
  `ui3-browser-acceptance.json`, `ui3-browser-overview-followup.json`,
  `ui3-20261002-native-version-acceptance.json`, `ui3-20261002-runtime-final.json`.
- **UI-2 üretim kabulü:** [CI 35650332366](https://github.com/Rapto0/Rapot/actions/runs/35650332366)
  ve [imaj yayını 35651233045](https://github.com/Rapto0/Rapot/actions/runs/35651233045)
  başarılı. `/root/rapot-ops/20260921-ui2-frontend/deployment.json` **verified**;
  SHA256 `c3b9e7d833af7a2383707c75f59b09807d9b21bd4671dc5552cc847dec6f7b00`.
  Uzak/yerel makbuz bağımsız doğrulandı; yeni runtime SHA256
  `a2b118e0de10a04ec5820800ef41abf9771ddc7290ec5f96b2be8baacadd22d5`.
  Sekiz sağlık/sayfa kontrolü, iki grafik rotası ve 11 JS + 1 CSS geçti.
  Canlı BIST/Kripto durumları ve BIST yenilemesi tarayıcıda doğrulandı.
  Backend/current ve diğer servisler korundu; `7b90365` / `dc3c65bf…` geri dönüş
  imajı duruyor. 528 MiB rezerv korundu; bağımlılık, DB/migration veya emir değişikliği yok.
  Yerel kanıtlar: `runtime-data/ui2-local-acceptance.json`,
  `runtime-data/ui2-http-acceptance.json`, `runtime-data/ui2-browser-acceptance.json`.
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
  UI paketlerinin belge kapanışı Git'te tutulur; ayrı sunucu belge aktarımı gerekmez.

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
