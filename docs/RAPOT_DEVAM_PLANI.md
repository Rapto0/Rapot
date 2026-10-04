# Rapot Devam Planı

**Güncel özet: 4 Ekim 2026.** Bu dosya, sonraki çalışmaya başlamak için okunur.
Çalışma kuralı: **incele → düzelt → doğrula → belgeyi güncelle**.
Teknik ayrıntılar [belge indeksinde](README.md), çalışma kuralları
[AGENTS.md](../AGENTS.md), önceki planın eksiksiz metni
[tarihsel arşivde](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md) bulunur.
Arşivdeki eski “bekliyor” ifadeleri güncel iş veya yeni onay talebi değildir.

## Kaldığımız nokta

- **4 Ekim — gelişmiş gün içi alarm merkezi ve 26 çizim aracı üretimde:**
  Son API düzeltmesi `3df9640`, 16:17:54 UTC'de yayımlandı; 16:19:02 UTC ayrı
  kabul geçti. Frontend `9592c69` korunur. Son CI **1.619 Python testi** geçti;
  doğal BIST dakika boşlukları ve geçmiş mum düzeltmeleri güvenli biçimde ele
  alınır. İlk kontrolde 39 geçmiş seri/1.244.264 bayt önbellek oluştu; 54
  sağlayıcı isteği henüz alınamadı, taze veri kabulü yapılmadı. Beş servis
  sağlıklı/restart0, OOM yok; 15 tablo ve diğer dört servis korundu.
  `9592c69`, 15:28:51 UTC'de yalnız API/frontend'e yayımlandı; 15:29:22 UTC ayrı
  salt okunur kabul geçti. `/alarms` ayrı ayrı 1.000 fiyat/teknik/izleme listesi
  alarmı, VE/VEYA, çoklu periyot, süresiz kurallar ve kalıcı Telegram teslim
  kuyruğu sunar. Eski günlük motor `/alarms/legacy`, yerel kurallar `/alarms/local`.
  Sunucu takip/motor servisi tarayıcıdan bağımsız; sessiz kalan WebSocket için
  90 saniyelik kalp atışı denetimi ve yeniden bağlanma var. 1m/5m grafik ve
  26 çizim aracı eklendi. Kaynakla eşleşen CI'da **1.605 Python testi** (bir
  atlama, üç mevcut uyarı), 291 frontend testi, lint/typecheck/build/standalone
  geçti. Sentetik tarayıcı CRUD/çizim, kesinti/yeniden başlatma ve karma yük
  kontrolleri tamamlandı. Eski 11 tablonun şeması korundu, dört yeni boş tablo
  doğrulandı; gerçek kural/olay/Telegram mesajı oluşturulmadı. Bot/middleware/
  PostgreSQL kimlikleri, ayarlar, hesap bilgileri ve 528 MiB rezerv korundu.
  Kabul anında takip servisi 805 sembole aboneydi fakat taze sembol sayısı
  sıfırdı; bu canlı veri kabulü değildir. Piyasa kapsamı/gecikmesi ve Telegram
  teslimi kullanıcı isteğiyle piyasa açıkken sınanacak. 3.000 kota sınırsız
  kapasite değildir: fiyat döngüsü 1 saniye, teknik geçmiş 1m için 30/diğerleri
  için 60 saniye hedefler; kuyruk bunu uzatabilir. [Sözleşme](SERVER_ALARMS.md).
- **4 Ekim — kullanım dışı sunucu kaynakları temizlendi:** Yeni açık kullanıcı
  talimatıyla 24 eski Docker imajı, dokuz eski kaynak kopyası, beş yeniden
  üretilebilir önbellek/derleme dizini ve 90 kullanım dışı PM2 günlüğü kaldırıldı.
  Günlüklerin özel bilgisayarda bağımsız doğrulanmış arşivi korundu. Aktif
  `279aa9f` kaynağı, sekiz çalışan/geri dönüş imajı, veritabanları, kimlikler ve
  yedek/kabul kayıtları yerinde. Beş servis sağlıklı/restart0; servis veya ayar
  değişmedi. 10:55:49 UTC sağlık kabulü dört sayfa/19 statik dosya/üç anonim 401
  kontrolünü geçti. 10:58:08 UTC son envanterde boş alan **7.666.819.072 bayt**,
  başarısız systemd birimi sıfır; 528 MiB rezerv korundu. Önce/sonra sağlık
  ölçümlerinde net boş alan artışı yaklaşık **6,98 GB**. İşlem tamamlandı;
  aşağıdaki tek kullanımlık operator ve eski kanıtlar yeniden çalıştırılmaz.
- **4 Ekim — BIST grafik saat düzeltmesi üretimde:** Kullanıcı Türkiye'de 10:00 olan
  açılışın grafikte farklı görünmesini bildirdi. Borsapy'nin saat dilimli verisi
  doğru; UTC eksen/imleç gösterimi `Europe/Istanbul` olarak düzeltildi. Mum/sinyal
  zamanları değiştirilmeden ana grafik, gösterge panelleri ve araştırma/replay
  grafiği aynı gösterimi kullanır. Kripto UTC ve günlük takvim tarihleri korunur.
  Panel ekle/kaldır işleminde ana grafik yeniden oluşturulmaz; mumlar ve
  yakınlaştırma korunur. 1.487 Python testi (bir atlama, üç mevcut uyarı),
  267 frontend testi, 264 Python dosyasının lint/format kontrolü, frontend
  lint/typecheck/build/standalone ve sentetik grafikte 07:00Z → 10:00 ana/RSI/
  araştırma imleç ve eksen kabulü geçti. `57aed91`, 10:08:52 UTC'de yalnız
  frontend'e yayımlandı; 10:09:03 UTC ayrı kabul dört sayfa, 19 statik dosya,
  üç anonim özel endpoint'in 401 yanıtı ve korunan dört servisi doğruladı.
  Canlı ekranda yeni saat etiketi görüldü; sürüm geçişinde bellek oturumu
  sıfırlandığından girişli canlı mum/imleç kontrolü yapılmadı. Sentetik görsel
  kabul ayrı tutulur. Tam dosya/config eşitliği doğrulanmış kaynak imajı,
  mevcut runtime katmanlarını korudu; sunucu temizliği veya plan yükseltmesi
  gerekmedi. Yayın kanıtları aşağıdaki ayrı kayıttadır.
- **4 Ekim — TradingView bağlantı düzeltmesi üretimde ve hesap doğrulandı:** Kullanıcının
  kaydettiği oturum geçerli; borsapy/httpx otomatik `www` → `tr` yönlendirmesinde
  elle gönderilen çerez başlığının kaybolduğu doğrulandı. Sınırlı, sır içermeyen
  sunucu tanısı hedefe oturumla ulaşıldığında kullanılabilir token bulunduğunu
  gösterdi. Güvenli yönlendirme adaptörü ve hata sonrası durumu yenileyen
  frontend düzeltmesi `876f3f3` ile 09:06:07 UTC'de API/bot/frontend'e yayımlandı.
  09:08:31 UTC ayrı üretim kabulü geçti; gerçek bağlantı ekranındaki
  **Oturumu doğrula** işlemi **Oturum doğrulandı** sonucunu verdi. Kayıtlı bilgiler
  yeniden girilmedi. Yerelde 1.421 Python testi (bir atlama/üç uyarı), 262 Python
  dosyasında lint/format ve 256 frontend testi/lint/typecheck/build/standalone geçti;
  kaynakla eşleşen CI'ın beş işi ve imaj yayınının iki işi başarılı.
  [Neden ve bağlantı sözleşmesi](BORSAPY_INTEGRATION.md#tradingview-oturum-yönlendirmesi).
  Hesap bağlantısı kabulü tamamdır; `realtime_verified=false` korunur. Canlı fiyat/mum,
  bölünme, alarm teslimi ve emir kabulü hâlâ ertelidir.
- **4 Ekim — Borsapy ortak piyasa altyapısı:** Kullanıcı Borsapy verisini grafik,
  tarayıcı ve ekonomik takvimde istedi. Yeni kaynakta BIST varsayılanı Borsapy;
  grafik/izleme listesi/piyasa kartları ortak, sınırlı TradingView fiyat havuzunu
  kullanır. Borsapy temel/teknik tarama ekranı ve Borsapy/Doviz.com takvimi bağlandı.
  Binance USDT enstrümanları Binance kaynağını korur; Yahoo yalnız gerektiğinde
  bağımsız sinyal teyidi veya açıkça seçilen eski yol içindir. Kişisel HTTP verisi,
  WebSocket ve SSE artık yönetici oturumu gerektirir; oturum bitince teslim kesilir.
  Yeni kaynak **`ab18dc4` ile üretimde**: API/frontend/bot birlikte güncellendi;
  middleware, PostgreSQL ve emir ayarları korundu. Exact-source CI'da
  **1.385 Python testi / 1 isteğe bağlı atlama / 3 bağımlılık uyarısı**, **250 frontend testi**, lint,
  typecheck, build ve standalone geçti. Tarayıcıdaki sahte veri kabulü grafik, BIST
  izleme listesi, iki tarama görünümü, takvim filtreleri ve çıkışta veri temizliğini
  doğruladı. Canlı salt okunur kabulde özel HTTP/WS ve bot sağlık erişimi,
  beş HTTPS sayfası, 22 statik dosya ve değişmeyen 11 tablo şeması doğrulandı.
  Anonim bot sağlık yanıtı yalnız hizmet durumunu verir; ayrıntılar aynı yönetici
  oturumunu ister. Bu ilk ortak altyapı kabulünde TradingView/EVDS/X bağlantıları
  yapılandırılmamıştı; hesap kabulü sonraki `876f3f3` yayınıyla tamamlandı.
- **Borsapy araştırma merkezinin ilk yayını üretimde:** Kullanıcı, mevcut TradingView
  Premium + BIST veri paketiyle README'deki 22 özellik ailesini kendi sitesinde istedi. borsapy
  0.11.0 sabitlendi; yönetici `/research` ekranına 51 işlem, bağlantı yönetimi,
  kayıtlı sorgu/portföy, grafik/replay ve akış/Pine gösterge kimliği yüzeyleri
  eklendi. `/chart` özel TradingView kaynağını seçebilir. Scanner ve günlük BIST
  alarm adaptörü hazırdı; o yayında `BORSAPY_USE_FOR_BIST` varsayılan false idi. Genel Pine
  kaynak çalıştırıcısı veya gün içi BIST alarm takvimi eklenmedi. Kimlikler
  sunucuda şifrelenir; özel fiyatlar genel grafik/önbellek yoluna taşınmaz.
  [Kapsam ve kabul](BORSAPY_INTEGRATION.md). O yayında canlı hesap/piyasa testi
  kullanıcının isteğiyle ertelenmişti. Python CI'da **1.204 test geçti**, bir
  performans testi atlandı; üç eski bağımlılık uyarısı kaldı. 227 frontend
  testi, lint/typecheck, build/standalone ve sentetik tarayıcı kabulü geçti.
  Tarayıcıda 51 işlem, kayıt, replay, akış başlat/durdur, özel grafik kaynağı,
  bağlantı sekmesi ve 320 px görünüm kontrol edildi. İlk `39d4243` kaynağının
  Python/lint işleri ve Linux borsapy runtime kabulü geçti; frontend CI yeni
  `braces` bildirimiyle durdu. Next lint
  bağımlılığının dar uyarlamasıyla tam audit 469/469 paket, sıfır bulgu verdi;
  bütün Next kuralları ve gerçek tüketici davranışı sınandı.
  [Güvenlik düzeltmesi](FRONTEND_DEPENDENCY_SECURITY.md). İlk kaynak üretime alınmaz.
  İlk araştırma yayınının kaynağı **`4b15335`** için beş CI işi ve iki imaj yayın işi geçti.
  Kullanıcının özel onayıyla iki eski frontend imajı kaldırıldı; güncel yedek
  ayrı veritabanında doğrulandı ve yalnız API/frontend güncellendi. Canlı yönetici
  GET'lerinde 51 işlem/9 grup, borsapy 0.11.0, HTTPS/statik dosyalar ve erişim
  sınırı geçti. Mevcut 10 tablonun şeması korundu; araştırma tablosu eklendi.
  Bu kabulde TradingView/EVDS/X bağlantıları tanımlı değildi; veri kabulü ertelendi.
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
alarmları üretimdedir; son kullanıcı seçimi 4 Ekim gelişmiş gün içi alarm ve
kalıcı veri takibidir. Kullanıcı canlı piyasa testlerini daha sonra yapmayı seçti.
Yerel doğrulama, imaj/disk bütçesi ve yayın kaydı birbirinden ayrı tutulur.
Kapatılmış işleri veya eski onay bekleme kayıtlarını yeniden başlatma.

| Konu | Durum / devam koşulu |
|---|---|
| Gelişmiş gün içi alarmlar ve çizimler | Frontend `9592c69`, API `3df9640` üretimde; 4 Ekim 16:19 UTC son şema/motor/HTTPS kabulü geçti. Fiyat/teknik/liste kotası 1.000'er, 26 çizim aracı. Doğal seyrek mumlar saklanıyor; canlı saniyelik kapsam, tüm dakika geçmişi ve Telegram teslimi piyasa açıkken ayrıca kabul edilecek. |
| Kullanım dışı sunucu kaynaklarının temizliği | Tamamlandı: 4 Ekim 10:58 UTC son envanter. 24 imaj, dokuz eski kaynak dizini, beş önbellek/derleme dizini ve yedeklenmiş 90 PM2 günlüğü kaldırıldı; beş servis sağlıklı/restart0, boş alan yaklaşık 7,67 GB. Yeni silme adayı otomatik varsayılmaz. |
| BIST grafik saat gösterimi | Tamamlandı: `57aed91` yalnız frontend, 4 Ekim 10:08 UTC. Ana grafik/gösterge/araştırma eksen ve imleci Türkiye saatinde; sentetik 07:00Z → 10:00 kabulü geçti. Canlı piyasa doğruluğu aşağıdaki ayrı kabuldür. |
| TradingView hesap bağlantısı | Tamamlandı: `876f3f3` API/bot/frontend, 4 Ekim 09:06 UTC; mevcut kayıtlı oturumla sitedeki doğrulama başarılı. Canlı piyasa verisi bu kabulün dışındadır. |
| Borsapy canlı kabulü | Gerçek fiyat/mum zamanı, tarihsel kapsam ve şirket işlemleri piyasa açıkken karşılaştırılacak. `realtime_verified=false` korunur. EVDS/X ayrı kimlik ve kabul ister. |
| Borsapy ortak piyasa altyapısı yayını | Tamamlandı: `ab18dc4` API/bot/frontend, 4 Ekim 08:02 UTC. İki runtime'da BIST kaynak seçimi açık; yeni temizlik veya plan yükseltmesi yapılmadı. Güncel 11 tablo yedeği ve bağımsız restore, kapasite, runtime/HTTP/WS/şema kabulü geçti. Son boş alan 804.610.048 bayt; 528 MiB rezerv korundu. |
| Borsapy araştırma merkezi ilk yayını | Tamamlandı: `4b15335` API/frontend, 4 Ekim 06:21 UTC. Özel onaylı iki imaj kaldırıldı; güncel yedek, kapasite, runtime/şema/HTTPS kabulü geçti. Son boş alan 839.430.144 bayt; sabit 528 MiB rezerv ve mevcut sunucu planı korundu. Bu tarihsel yayının kabulü kapalı; yeni ortak piyasa geçişi üstte ayrı izlenir. |
| Eski Python pinlerinin yeni güvenlik bildirimleri | 134 paketlik report-only taramada 5 paket/16 ham bulgu; 22 borsapy ek paketinde bulgu yok. anyio/PyJWT/soupsieve/urllib3 runtime ve virtualenv geliştirme pinleri için ayrı taban imaj güncellemesi gerekir. [İnceleme ve düzeltme sınırları](BORSAPY_INTEGRATION.md). Yeşil güvenlik işi sıfır bulgu değildir. |
| Canlı veri yükleme gecikmesi | UI-3'te görülen bekleme tarihsel gözlemdir. Yeni ortak altyapı sınırlı fiyat havuzu, kuyruk, önbellek ve bekleme/eskilik durumlarını ekledi; gerçek sağlayıcı gecikmesi ve piyasa performansı henüz ölçülmedi. |
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
- Aynı gün devam talimatı, Borsapy'nin grafikler, tarayıcılar ve ekonomik takvim
  dahil ortak veri altyapısına taşınmasını kapsar. Bu geçiş API/frontend yanında
  scanner botunun da yeni kaynağı çalıştırmasını gerektirir. Genel doğrulanmış
  yayın yetkisi sürer; önceki iki imaja özel silme yetkisi genişlemez.
- Bağlantı yardımında kullanıcı hesabını bağlamayı ve başarısız bağlantıyı
  düzeltmeyi açıkça istedi; kayıtlı oturumla yalnız kimlik doğrulama tanısı ve
  doğrulaması bu kapsamdadır. Oturum sırları sohbete/Git'e/kanıta yazılmaz.
  Bu istek canlı piyasa veya testnet/gerçek emir kabulünü açmaz.
- 4 Ekim grafik düzeltmesinden sonra kullanıcı **"Gereksiz eski kaynakları sil.
  Sunucumda hata istemiyorum."** dedi. Bu yeni talimat, kullanım dışı ve yeniden
  üretilebilir sunucu kaynaklarının kontrollü temizliğini kapsar; önceki iki-imaj
  onayından bağımsızdır. Çalışan sürümler, uyumlu geri dönüş imajları, aktif
  `279aa9f` Compose kaynağı, veritabanları, kimlikler ve yedek/kabul kayıtları
  korunur. Eski PM2 günlükleri ancak bağımsız doğrulanmış özel bilgisayar
  arşivinden ve taze kullanım kontrolünden sonra kaldırılır. Toplu prune,
  volume/veritabanı silme veya servisleri yeniden başlatma bu işlemde seçilmedi.
- 4 Ekim devamında kullanıcı, iki eski frontend imajını (`e312d7aa…` ve
  `a24bbefa…`) kaldırıp yayını tamamlama sorusuna **"yayını tamamlamama onay
  veriyorum"** yanıtını verdi. Yetki, aşağıdaki tam digest'ler ve teklif hash'i
  ile sınırlıdır; başka imaj/dosya/volume/DB silme yetkisi eklemez.
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
  korunur. O aşamadaki kullanıcı seçimi sunucu alarm yönetimiydi. Bu seçim gerçek
  işlem emri veya kullanıcının yerine canlı alarm oluşturma yetkisi değildir;
  TradingView/testnet dış kabul ertelemesi sürer.
- Deploy yetkisi; gerçek/testnet emri, üretim verisi silme/geri yükleme,
  force-push veya sunucudaki bilinmeyen değişiklikleri ezme yetkisi değildir.
  Belgenin kendisi yeni yetki üretmez. Gerçek kullanıcı kapsam değişikliği kayda geçirilir.
- Anahtar, parola, token, `.env` içeriği ve gerçek DB'ler Git'e/rapora alınmaz.
  Yerel/sentetik test, gerçek ortam gözlemi ve dış kabul birbirinin yerine geçmez.

## Son üretim ve yayın kanıtları

### 4 Ekim — gelişmiş gün içi alarmlar ve çizim araçları

- **Yayın sonrası dar API düzeltmesi tamamlandı:** Salt okunur durum gözleminde geçmiş
  önbelleği henüz oluşmamıştı. Kaynak incelemesinde, yerel doğrulamanın BIST'teki
  gerçek seyrek mumları (işlemsiz dakika/kapanış aralığı) tümüyle reddedebildiği
  bulundu. Sağlayıcının zaman/fiyat dizisi korunarak tam periyot katı boşluklar
  kabul edilir; boşluk sonrası alarm devamlılığı sıfırlanır, boşluk üzerinden
  kesişme türetilmez. Kripto, gelecek mum ve kapanış korumaları korunur. Yeni
  cached/failure sayaçları eski geçmişi sağlayıcı hatasından ayırır. Sağlayıcının
  geçmiş satır silme/eklemesi, zaman gerilemesi ve eski karşılaştırma girdisinin
  kaybı da devamlılığı sıfırlar. Normal kayan pencere/diskten geri okuma korunur.
  `800cf71` adayı sunucuya alınmadı; son kaynak
  **`3df9640737ddb4b3f3a2cd006a2188b79d603a72`** kullanıldı.
  [CI 37215360836](https://github.com/Rapto0/Rapot/actions/runs/37215360836)
  beş iş/1.619 Python testi/1 atlama/3 eski uyarı ve 291 frontend testiyle geçti;
  [yayın 37215374643](https://github.com/Rapto0/Rapot/actions/runs/37215374643)
  iki işi başarıyla tamamladı, iki isteğe bağlı iş atlandı. Hedefli 102 test
  ve bağımsız kod incelemesi, sentetik mum/önbellek/kesişme sınırlarını doğruladı.
  Yeni API imajı
  `sha256:c6a1afda9f2267e1feeb12cfe649cb75c3341ccadbe656765774b009ce14fe17`.
  Runtime 120 paket/285 kaynak dosyasıyla eşleşir; dokuz şema/startup/repository
  kaynağı ve frontend değişmedi. API-only ek imaj bütçesi 10.134.488 bayt.
  Yeni migration, veri geri yüklemesi, temizlik veya plan değişikliği yapılmadı.
  `/root/rapot-ops/20261004-advanced-alarms-hotfix/deployment.json`,
  16:17:54 UTC **verified_health_ssr_auth_boundary**; SHA256
  `d3d4a92ae2e5024f4dc716eb7d310c9be1703c671523e1e43c3408f3ec685727`.
  Bağımsız 16:19:02 UTC kabul SHA256
  `33b1c9f51c43449d1106f7db99d1fb8ce0ff150df8dcf87d37bf2a36b13d3a1b`:
  15 tablo şeması değişmedi; motor, dört yönetici GET, 18 kaynak/120 paket,
  üç sağlık/beş HTTPS sayfa/13 statik dosya/11 anonim 401 sınırı geçti.
  805 abonelik, 39 önbellek serisi/1.244.264 bayt, 54 sağlayıcı hatası,
  sıfır gap/invalid_data hatası ve sıfır taze seri görüldü. Bunlar normal arka
  plan servisinin durum sayaçlarıdır; tüm geçmişin veya gecikmesiz verinin kabulü
  değildir. Kural/liste/olay sayısı sıfır, Telegram teslim testi yapılmadı.
  16:19:14 UTC beş servis sağlıklı/restart0, OOM yok, boş disk **7.626.874.880
  bayt**; 528 MiB rezerv korundu. Frontend/bot/middleware/PostgreSQL kimlikleri,
  private env/hesap dosyası ve current/Compose aynı kaldı. Tek kullanımlık
  helper önceki doğrulanmış operator hash'ine bağlıdır; eski OPS kanıtları
  silinmez veya bu tamamlanan operator yeniden çalıştırılmaz.
- Kaynak `9592c69adb355f907b6c84642bed5259fbbe6ba1`;
  [CI 37212519520](https://github.com/Rapto0/Rapot/actions/runs/37212519520) beş işi,
  [yayın 37212533457](https://github.com/Rapto0/Rapot/actions/runs/37212533457) üç işi
  başarıyla bitirdi; API delta işi beklenen şekilde atlandı. Son kaynakta
  1.605 Python testi/1 atlama/3 eski uyarı, 291 frontend testi ve bütün zorunlu
  derleme/lint/tip/standalone kontrolleri geçti. Güvenlik işi report-only Python
  bulgularını sıfırladığı anlamına gelmez.
- API imajı `sha256:d08c27c439a477c4134e34dbba5335dcc03a44251fd4a525809c56e10bc7a994`,
  frontend `sha256:43c1755eaf03d66e2d9b222cfc08bc269d78d51b2e23228972ca016bbf5e7376`.
  API, `384674f` Borsapy tabanını; frontend `18a15ab` tabanını kullanır.
  Bağımsız kanıt 120 kurulu paketi, değişmeyen runtime dosyalarını ve 285 kaynak
  dosyasını Git/GHCR/artifact hash'leriyle eşleştirdi. Frontend dosya sistemi ve
  runtime config eşitliği de doğrulandı. İlave imaj bütçesi 21.146.649 bayt;
  temizlik veya sunucu planı değişikliği yapılmadı.
- Yayın öncesi sunucu dışındaki özel yedek, ayrı SQLite'a geri yüklenerek
  bütün eski 11 tablonun şema/veri parmak izleri, integrity ve FK kontrollerinden
  geçti. Arşiv SHA256 `45da730980a1caf1fe1f55f7afab8fe11ce2b1d618996dff461116a93b990cff`;
  bağımsız kabul `5c90fcdb9627c6946a933026290d867f6866e0df1485b75d9f21a21493b5f3ad`.
  Üretim geri yüklemesi yapılmadı. Sentetik iki kez init kabulü eski veriyi
  korudu; canlı kabul eski veri satırlarını yeniden taramadı veya eşitlik iddia etmedi.
- Tek kullanımlık `/root/rapot-ops/20261004-advanced-alarms/deployment.json`,
  15:28:51 UTC **verified_health_ssr_auth_boundary**;
  SHA256 `d30776a84d84ecf9e80bb394d4f4489c80bcffcb7f083de41114b350b5a1d949`.
  Ayrı 15:29:22 UTC kabul SHA256
  `2e53375cde13e7f2adb589aa4ca76bc3e9d4f6bbd7541ee209d605df38b300cd`.
  Eski 11 tablo şeması yedekle aynı; yeni dört tablo kanonik DDL/index/FK/kolon
  tanımlarıyla aynı ve boş. Dört yönetici GET, çalışan motor, 18 runtime kaynak
  dosyası, üç sağlık yanıtı, beş HTTPS sayfası, 13 JS/CSS örneği ve 11 anonim
  401/özel no-store sınırı doğrulandı. Kabul yalnız bellek/DB/sağlık okudu;
  sağlayıcı sorgusu, test alarmı, Telegram mesajı veya emir üretmedi.
- Normal arka plan servisi açıktır. Kabul anında 805 evren/takip/abonelik,
  0 taze sembol, 0 hazır geçmiş/805 istek/778 bekleyen iş görüldü; piyasa
  doğruluğu veya gecikmesiz kapsam kanıtı değildir. `realtime_verified=false`
  ve `one_second_coverage_guaranteed=false` korunur. Telegram yapılandırılmıştır,
  teslim testi kullanıcı isteğiyle ertelidir.
- 15:29:32 UTC kaynak gözleminde beş servis sağlıklı/restart0, OOM yok;
  boş disk 7.644.327.936 bayt, sabit 528 MiB rezerv korundu. API yaklaşık
  238,5 MiB kullanıyordu; tek anlık kaynak ölçümü sürdürülebilir piyasa yükü
  kabulü değildir. Bot `876f3f3`, middleware/PostgreSQL/current/Compose `279aa9f`,
  özel env/Nginx ve şifreli hesap dosyası korundu. Yeni kural/liste/olay sayısı sıfır.
- Sentetik tarayıcı kabulü alarm oluşturma/duraklatma/çok koşul/liste ve çizim,
  taşıma/geri al/stil/kilit/yenileme/periyot ayrımını doğruladı. Karma yük deneyi
  1.000 fiyat + 1.000 teknik + 1.000 liste kuralını 600 sembolle (1,8 milyon
  olası eşleşme) değerlendirdi: 10 turda 1.520 hazır değerlendirme, ilerleyen
  sıra, sınırlı iş/durum belleği; tracemalloc tepe 37,3 MB. Sağlayıcı/Telegram
  çağrısı yok. Bu yerel sentetik ölçüm bütün kapsamın saniyede işlendiğini veya
  tek CPU'lu üretimin kapasitesini kanıtlamaz.

### 4 Ekim — TradingView bağlantı düzeltmesi ve hesap kabulü tamamlandı

- Kaynak `876f3f37b9d56624d17c46ab924684de559c5530`;
  [CI 37190406726](https://github.com/Rapto0/Rapot/actions/runs/37190406726)
  beş başarılı iş, [imaj yayını 37190433460](https://github.com/Rapto0/Rapot/actions/runs/37190433460)
  iki başarılı iş; istenmeyen API delta işi skipped. Yerel tam paket 1.421 Python
  testiyle geçti; bir isteğe bağlı test atlandı, üç bağımlılık uyarısı kaldı.
  262 Python dosyasının lint/format kontrolü ve 256 frontend testi,
  lint/typecheck/build/standalone geçti.
- API ve bot ortak imajı:
  `ghcr.io/rapto0/rapot/backend@sha256:a6d0e72e9430d99d01e31409b347000d175cf1d116b0b83d6298079a2fd869d5`.
  Frontend:
  `ghcr.io/rapto0/rapot/frontend@sha256:18a15abed812a356df102980c8a520b8f03707d1ef2d8e84a739d1c879903787`.
  Source-only backend doğrudan önceki kabul edilmiş `384674f3…` / `ab18dc4`
  imajına dayanır; 120 paket dosya envanteri ve tam taban katman öneki korunur.
- 09:06:07 UTC / 12:06:07 TSİ dağıtım tamamlandı. Dağıtım kaydı SHA256:
  `a0692c0726493dbc4864f42dd71173d59190579f285c7aada3650609d46857ce`.
  Yeni temizlik, migration veya yedek alma işlemi yapılmadı; önceki bağımsız
  doğrulanmış yedek korundu. Son boş alan **696.680.448 bayt**, sabit rezerv 528 MiB.
- 09:08:31 UTC ayrı salt okunur kabul: beş servis healthy/restart0; API/bot içinde
  30 canonical dosya ve 120 paket, katalogda 51 işlem/9 grup doğrulandı.
  45 yerel ve 45 dış anonim özel GET 401/no-store verdi. Beş HTTPS sayfası ve
  22 statik dosya geçti; 11 tablonun şeması değişmedi. Kanıt
  `runtime-data/borsapy-auth-fix-deploy/acceptance.json`, SHA256:
  `21ea67843d1191a2d9c60f696f16255c814ac6c29a81b68fc202340f2da0d85a`.
- Ayrı etkileşimli hesap kabulünde kullanıcının mevcut şifreli kaydıyla sitedeki
  **Oturumu doğrula** eylemi **Oturum doğrulandı** sonucunu gösterdi. Kayıtlı
  oturum bilgileri geçerliydi; sorun yönlendirmede çerez başlığının kaybıydı.
  Sır içermeyen UI/API kanıtı ignored
  `runtime-data/borsapy-auth-fix-deploy/account-ui-acceptance.json`, ekran kanıtı
  `runtime-data/borsapy-auth-connected.jpg` dosyasında. Operatör hazırlık kaydı
  `deployed_and_acceptance_verified`; `reexecution_allowed=false` ile kapatıldı.
  Bu, gerçek zamanlı fiyat/mum veya BIST paket yetkisi ölçümü değildir;
  `realtime_verified=false` kalır. Fiyat/mum, bölünme, alarm teslimi ve emir
  kabulü ertelidir. Önceki `ab18dc4` kaydındaki tanımsız bağlantı durumu tarihsel
  gözlemdir; güncel hesap bağlantısı kabulünü geri almaz.

### 4 Ekim — site geneli Borsapy üretim kabulü tamamlandı

- Kaynak `ab18dc48881964f6211dc9d9a63ebe33cec9c785`;
  [CI 37187054987](https://github.com/Rapto0/Rapot/actions/runs/37187054987)
  beş başarılı iş, [imaj yayını 37187060992](https://github.com/Rapto0/Rapot/actions/runs/37187060992)
  iki başarılı iş; istenmeyen eski API delta işi skipped. Python 1.385 passed,
  bir isteğe bağlı performans testi skipped, üç eski websockets uyarısı;
  250 frontend testi, lint/typecheck, build/standalone başarılı.
  İlk `769b2e9` CI'ı üç önbellek testinin makine çalışma süresi varsayımıyla
  durdu ve o kaynak üretime alınmadı. Yalnız test saatinin deterministik
  yapılmasıyla yeni exact-source CI geçti; uygulama davranışı değiştirilmedi.
- API ve bot ortak imajı:
  `ghcr.io/rapto0/rapot/backend@sha256:384674f3a7230ae4a6b182ac26e6114808627555988cb3305e7ed906b7d59def`.
  Frontend:
  `ghcr.io/rapto0/rapot/frontend@sha256:bbb7bb3821811618641127ead98d08130804c88aec8bd11591692ba90ca3e7ba`.
  Source-only backend, kabul edilmiş `b9695f5f…` Borsapy imajının tam 14 katman
  önekini korur. 98+22 paket doğrulamasına ek olarak 120 paketin bütün dosya
  envanterleri eşleşti; 266 canonical kaynak hash'i ve ağsız uygulama kontrolleri
  geçti. Artifact `11297208981`, ZIP SHA256
  `2d017d8c1071efa1ca960410b319718efce4fad440c6d7d3746d98d7bc2167ff`.
  Yerelde iki doğrulayıcı yeniden çalıştırıldı ve sonuç registry digestine bağlandı.
- 07:48:21 UTC salt okunur sabit snapshot ayrı özel bilgisayar dizinine alındı:
  **150.096.490 bayt** gzip, SHA256
  `c6367372e991bfbed1491aabf9ac23a5f46cb5b81c85869b213bde9c84fef0d3`.
  Ayrı yerel restore **1.129.897.984 bayt**; 11 tablonun integrity, şema ve
  tipli satır fingerprint'leri eşleşti. Üretime geri yükleme yapılmadı.
- İki benzersiz imajın ölçülen ek bütçesi **117.284.294 bayt**; API/bot aynı
  backend katmanlarını paylaşır. Sabit 528 MiB rezerv, 64 MiB WAL/log ve 2 MiB
  kanıt payıyla gerekli alan **740.138.438 bayt**, ölçülen boş alan 826.183.680
  bayttı. Yeni temizlik, imaj/veri/önbellek/yedek silme veya ücretli plan
  değişikliği yapılmadı; bütün önceki geri dönüş imajları korundu.
- 08:02:14 UTC / 11:02:14 TSİ rollout kabulü: API → bot → frontend sırayla
  healthy/restart0; bot `running/local_lifecycle`. Override'da yalnız üç imaj
  ve API/bot için `BORSAPY_USE_FOR_BIST=true` değişti. Diğer ortam değerleri,
  başlangıç komutları, credential mount'ları, özel env dosyaları, Nginx,
  middleware/PostgreSQL kimliği/başlangıcı/restart sayısı, Compose/current
  `279aa9f` korundu. DRY_RUN ve trading/live kapalı kaldı. Initializer/migration
  çalıştırılmadı; rollback gerekmedi. Uzak kayıt
  `/root/rapot-ops/20261004-borsapy-market/deployment.json`, SHA256
  `67521db3573dba30addae369759bdda6ee9a113e5049cbbf1a2f4ca922dd6048`.
- 08:02:47 UTC ayrı salt okunur kabul: API/bot içinde 28 canonical dosya,
  120 kurulu paket, borsapy 0.11.0 ve BIST kaynak seçimi doğrulandı. Üç güvenli
  yönetici GET'i 51 işlem/9 grup, bağlantı ve kaynak politikasını gösterdi.
  45 özel yol hem yerel hem HTTPS anonim GET'te 401/no-store verdi. Dört yerel
  WS ve dış signals WS kimliksiz 4401; yerel/dış signals WS ilk-frame tokenıyla
  authenticated ack verdi. Token URL'ye konmadı, piyasa akışına abone olunmadı.
  Flask'ın dört özel yolu yerel/proxy üzerinden 401; anonim `/status` yalnız
  sağlık/lifecycle alanlarını döndürdü. Beş HTTPS sayfası ve 22 JS/CSS geçti.
  11 tablonun tüm şema nesneleri değişmedi; şema kabulünde tablo satırları okunmadı.
- Son kabulde beş servis healthy/restart0, boş alan **804.610.048 bayt** idi.
  TradingView/EVDS/X hâlâ yapılandırılmamış. Gerçek hesap/fiyat/mum/bölünme,
  alarm teslimi veya emir testi yapılmadı. Normal servis başlangıcının sağlayıcı
  trafiği ayrıca ölçülmedi; kabul kontrolleri sağlayıcı sorgusu başlatmadı.
- Kanıtlar ignored `runtime-data/borsapy-market-deploy/` içinde; bu tek
  kullanımlık operatör tekrar çalıştırılmaz. SHA256:
  `github-evidence.json`: `b7feeef5263acf69f4cd801530e888105caeb43a3812b5edfb0728f2a9a49ce6`;
  `capacity.json`: `a3c107e721cbff55f9372ff1eb6089e37b1f574a72b3b11c1aed80a9d3dd15bc`;
  `backup-verified.json`: `f8bf66905fc9ece022de256adead24c6b1d1217c9b79f1a3a764e79526fdcbe4`;
  `acceptance.json`: `4b37721869427102aac20526b9418ae748458b9073d23fd641c0311f720a8129`.

### 4 Ekim — ilk Borsapy araştırma yayını kabulü

- Uygulama kaynağı `4b15335f00f30e65a21899e73af47c508f395706`.
  [CI 37159767810](https://github.com/Rapto0/Rapot/actions/runs/37159767810)
  beş başarılı iş; [imaj yayını 37159767909](https://github.com/Rapto0/Rapot/actions/runs/37159767909)
  iki başarılı iş ve istenmemiş source-only API delta işi skipped.
- API: `ghcr.io/rapto0/rapot/backend@sha256:b9695f5f78ccb6f16112578c54fb9fb2de7ce6a3dc4c0836c3da7deacf7adf14`.
  Frontend: `ghcr.io/rapto0/rapot/frontend@sha256:f569c7e24e9d7a9efb8918406e0fcc05137146c96fe3715a2d0f308b4c06428e`.
  Linux kabulü 98 mevcut paketin sürüm/dosya hash'ini korudu, tam 22 paket
  ekledi; 255 kaynak dosyası, native import, şifreleme, SQLite ve 8 araştırma/
  yerel gösterge kontrolü ağsız geçti. Bu, gerçek sağlayıcı kabulü değildir.
- İlk gece yedeği ve kapasite ölçümü tarihsel kaldı; rollout öncesinde yenilendi.
  4 Ekim 06:09:59 UTC snapshot'ı 149.978.197 bayt gzip; SHA256
  `ae1f2a1962c37a5d7a33ed790592a5ad2baaae5ff60ca05d03ae6c42dd2d1ebd`.
  Bağımsız özel yerel restore 1.129.062.400 bayt; 10 tablonun şeması, integrity
  ve tipli satır fingerprint'leri eşleşti. Yedek OneDrive/repo dışında tutulur;
  üretim DB'si geri yüklenmedi. Önceki yedek de korundu.
- Kullanıcının bu turdaki özel onayıyla 06:12:06 UTC'de **yalnız** şu iki
  kullanılmayan frontend imajı `docker image rm --no-prune` ile kaldırıldı:
  `sha256:e312d7aa5e682a7835e4dc7ba3e1b4263f04a64f872f47037814ec4b0ba1f4d0`
  (`bbd9377`, 13 Eylül build) ve
  `sha256:a24bbefa443cf30f77af55161c19520f6febf1c977ef55a044fd030189bd0b41`
  (`13e5fbb`, 21 Eylül build). Çalışan/durmuş container referansları yeniden
  kontrol edildi. Net boş alan kazanımı **196.517.888 bayt**; önceki API/frontend,
  ortak backend, PostgreSQL ve eski frontend geri dönüş imajı `feaa0325…` korundu.
  Genel prune/force, volume/DB/dosya silme yapılmadı. Teklif hash'i
  `e853b8419a957243910928212b4c1752015b6b8b75791f749ae7d8c881990722`.
  Bu tamamlanmış onay başka bir temizliğe yetki vermez.
- Temizlik sonrası 06:13:17 UTC ölçümü: boş alan 1.216.286.720, iki imajın ek
  maliyeti 460.329.392, toplam gerekli alan 1.083.183.536 bayt. Bu tutar sabit
  528 MiB rezerv + 64 MiB WAL/log + 2 MiB kanıt payını içerir. Registry katman
  hash'leri ve containerd katman varlığı doğrulandı; pull sırasında bütçe korundu.
- 06:21:23 UTC / 09:21:23 TSİ: yalnız API/frontend exact digest ile güncellendi.
  `/root/rapot-ops/20261004-borsapy/deployment.json` durumu
  `verified_health_ssr_auth_boundary`, SHA256
  `8e86b9d53699392eb228185177f33122d385deeb6523ff9a20c036b65978f948`.
  Bot/middleware/PostgreSQL container kimliği, başlangıcı ve restart sayısı;
  özel ortamlar, Nginx, Compose kaynağı ve `current` korundu. Override'da yalnız
  iki imaj alanı değişti. BIST scanner geçişi açılmadı; DRY_RUN korundu.
- 06:21:54 UTC ayrı salt okunur kabul: üç yönetici GET'inde 51 işlem, 9 grup,
  kurulu borsapy 0.11.0 ve `private, no-store`; üç anonim GET'te 401 doğrulandı.
  `/research`, `/login?next=%2Fresearch`, `/chart` HTTPS SSR ve 17 JS/CSS geçti.
  Mevcut 10 tablonun 41 şema nesnesi hash'i korundu; `research_workspaces`
  yedi kolon, PK ve owner indeksiyle doğrulandı. Şema kabulünde tablo satırları
  okunmadı. TradingView/EVDS/X yapılandırılmamış; kayıtlı araştırma sayısı sıfır.
  Bu kabul etkileşimli canlı tarayıcı, sağlayıcı, hesap, alarm veya emir testi değildir.
- Son 06:22:23 UTC gözlemi: beş servis healthy/restart0; boş alan
  **839.430.144 bayt**, sabit rezerv üstünde. Sunucu planı değiştirilmedi.
- Kanıtlar ignored `runtime-data/borsapy-deploy/` içindedir; gizli yedekler
  Git'e alınmaz. Güncel SHA256'lar:
  `capacity.json`: `5e852c27e515066488bffb8e6a74db5668d370630867e6735aa840b8d8fe0d5d`;
  `backup-verified.json`: `6dabe7481c31be372abcebce955394c1607624753442a8167898cb2af72e69be`;
  `acceptance.json`: `f773747918f9d4f98520550069cb54364948b800da14716c995aa7b943cddda0`;
  `final-observation.json`: `3a99ec553bf8139fc17244ca0d1b6a2179256e6efbb11406b4999d63d994f7f1`.
  `cleanup-run.json` tamamlanmış iki-imaj işlemini kaydeder; operator betikleri
  önceki kanıtlarla tekrar çalıştırılmaz. Yeni yayın ayrı taze kabul gerektirir.

### BIST grafik saati — 4 Ekim üretim kabulü

- Kaynak `57aed91895144cd1b915fa2e929d9712f8bf77cc`;
  [CI 37193523498](https://github.com/Rapto0/Rapot/actions/runs/37193523498)
  beş iş ve [imaj yayını 37193536102](https://github.com/Rapto0/Rapot/actions/runs/37193536102)
  iki seçili iş başarılı. Yerelde 1.487 Python testi (bir atlama/üç mevcut
  bağımlılık uyarısı), 267 frontend testi, lint/typecheck/build/standalone geçti.
- Frontend `sha256:399ab9fa72a2944127169578344c9fbfd2334ebf5bbe074e2d645dfb51931745`.
  Kanıt artifact'i `11299104786`; ZIP SHA256
  `6d7fa3347d5a13509f7995af95d27a39255a9644b127d27a79c3a7dc8ed8d05e`.
  Normal adayla tam rootfs/config eşitliği, eski imajın 13 katmanının tam
  öneki ve iki imajda ağsız üç sayfa/18 statik dosya kabulü doğrulandı.
  Docker API'nin 11 boş/false/null varsayılan alanı yalnız kanıtlanan
  biçimde tamamlandı; diğer alanlar korunarak exact CI config hash'i elde edildi.
- Ölçülen ek imaj bütçesi 10.550.266 bayt; 528 MiB sabit rezerv, 64 MiB
  çalışma payı ve 2 MiB kanıt payı korundu. Temizlik/yükseltme yapılmadı.
  Eski `18a15abe…` frontend geri dönüş imajı duruyor.
- 10:08:52 UTC makbuzu `/root/rapot-ops/20261004-chart-timezone/deployment.json`
  **verified_frontend_only**; SHA256
  `6960f3c9e42671d5359cb548c605fc726f7c017899e11219c9dc3ee696b8fad7`.
  10:09:03 UTC ayrı kabul **verified**; SHA256
  `e0c819da7e594e980e20e32a19aa5cc6358aafef6d3389e13ca79405169b5275`.
  Dört SSR sayfası/19 statik dosya, üç anonim özel endpoint'te 401 ve
  `private, no-store` geçti; son boş alan **686.026.752 bayt**.
- API/bot `876f3f3`, middleware/PostgreSQL/current `279aa9f`, env/Nginx ve
  şifreli TradingView kimlik dosyasının bayt/izinleri korundu. DB, migration,
  sağlayıcı doğrulaması, alarm veya emir işlemi yapılmadı.
- `runtime-data/chart-timezone-ui-acceptance.json` sabit sentetik 07:00Z
  mumunun ana/RSI/araştırma imlecinde 10:00 gösterimini ve panel ekle/kaldırda
  mumların korunmasını kaydeder. `chart-timezone-live.jpg` üretimdeki saat
  etiketini gösterir; sürüm geçişi Rapot bellek oturumunu sıfırladığı için
  üretimde girişli mum/imleç kabulü değildir. Kayıtlı TradingView bağlantısı
  silinmedi. Canlı piyasa ve şirket işlemleri kabulü erteli kalır.

### Kullanım dışı sunucu kaynakları — 4 Ekim temizlik kabulü

- Yeni kullanıcı talimatı kapsamında üç ayrı, tek kullanımlık işlem tamamlandı.
  Hiçbir servis yeniden oluşturulmadı veya yeniden başlatılmadı; uygulama sürümü,
  Compose/current, env/Nginx ve şifreli TradingView kimlik dosyasının bayt/izinleri
  korundu. Veritabanı, volume, sağlayıcı veya emir işlemi yapılmadı.
- **24 Docker imajı:** Bütün konteyner referansları ve korunan imaj katmanları
  denetlendi; kaldırılan her digest'in registry metadata/katman erişimi ve yerel
  Git kaynağı doğrulandı. `docker image rm --no-prune` ile yalnız kesin adaylar
  kaldırıldı. 32 imajdan sekizi kaldı: dört çalışan imaj ile `18a15abe…`,
  `384674f3…`, onunla eşleşen `bbb7bb38…` frontend ve `b9695f5f…` tabanı.
  İlk 25 adaylı taslak yerine eşleşen frontend'i de koruyan 24 adaylı plan
  uygulandı. 10:42:56 UTC makbuzu:
  `/root/rapot-ops/20261004-resource-cleanup-images/image-cleanup.json`, SHA256
  `8b8887c371e837b61375ac0ac1b31dd3d450533b4aefdd88f8b58204f3e1e114`.
- **14 dizin:** `/root/.npm/_cacache`, `/root/.npm/_npx`, `/root/.cache/pip`,
  `/root/Rapot/frontend/node_modules`, `/root/Rapot/frontend/.next` ile
  `/opt/rapot/releases/` altındaki `2cf05a8`, `8f60f8e`, `a513af9`, `aadde72`,
  `bacbfab`, `ccd6154`, `db98915`, `f61e169`, `fce5d01` eski kaynakları kaldırıldı.
  Dokuz kaynağın tam dosya listesi/Git içeriği ve `RELEASE_SHA` eşleşti; metinlerde
  yalnız CRLF/LF normalizasyonuna izin verildi. Süreç, açık dosya, mmap, mount,
  konteyner ve servis/cron kullanım kontrolü geçti. Aktif `279aa9f` kaynağı ve
  benzersiz eski veri/ayar barındıran `/root/Rapot` kökü korundu. 10:44:32 UTC
  makbuzu `/root/rapot-ops/20261004-filesystem-cleanup/filesystem-cleanup.json`, SHA256
  `a05e389c9df3001aed75b6a86976884af4f4806f2e8bff89b5c6739ef334e4bd`.
- **90 PM2 günlüğü:** `/root/.pm2/logs/` içindeki toplam 2.388.935.299 baytlık
  kullanım dışı dosyalar, doğrudan bilgisayara sıkıştırılarak yedeklendi. Arşiv
  139.575.947 bayt; tam 90 üye, boyut/izin/sahiplik/hash ve gzip CRC bağımsız
  doğrulandı. Kaynakların yedek öncesi/sonrası eşitliği ve taze kullanım kontrolü
  ardından yalnız bu dosyalar kaldırıldı. Özel Windows arşivi:
  `C:/Users/memet/RapotBackups/20261004-resource-cleanup/pm2-logs-103221Z/pm2-logs.tar.gz`,
  SHA256 `f0f354029e02c198d67d2b623c1cfdc4dd0fd4b55cd1adccf0fb6991c75cb854`.
  ACL yalnız mevcut kullanıcı/SYSTEM; içerik Git'e veya sohbete alınmadı.
  10:45:37 UTC makbuzu `/root/rapot-ops/20261004-pm2-logs-cleanup/receipt.json`, SHA256
  `a59dc29d9089d22edbbb07fed6c7077285e8d09e3323cffc55e081afd2e3989c`.
- **Bağımsız son kabul:** 10:30:24 UTC önceki sağlık ölçümünde 683.552.768 bayt,
  10:55:49 UTC son sağlık ölçümünde 7.666.995.200 bayt boş alan vardı: net artış
  **6.983.442.432 bayt**. Beş servis kimliği/imajı/başlangıcı/runtime hash'i aynı,
  hepsi sağlıklı/restart0; dört SSR sayfası, 19 JS/CSS ve üç anonim özel endpoint'in
  401/`private, no-store` kontrolleri geçti. `health-after.json` SHA256
  `bbb0d29d775fea441ba3c4d78e9ee4b2c8bd772c609c38f7424de66c46f63206`.
  10:58:08 UTC son envanter sekiz imajı, 14 dizin/90 günlüğün yokluğunu,
  aktif kaynak pointer'ını ve sıfır başarısız systemd birimini doğruladı;
  boş alan **7.666.819.072 bayt**. `final-inventory.json` SHA256
  `5e44c23681829949769bc43095a0bcbd6eca2ecbf2328cdc6d62b219ee913d44`.
- Makbuzların hash'i doğrulanmış yerel kopyaları ve denetimler
  `runtime-data/server-cleanup-20261004/` içindedir; Git'e alınmaz. Sistem/auth
  günlükleri, veriler, mevcut yedekler ve kabul kayıtları korunur. Uygulama kodu
  değişmediği için tam uygulama testleri yeniden çalıştırılmadı; canlı piyasa,
  alarm teslimi ve emir kabulü erteli kalır.

### Mevcut üretim

Bunlar **son kaydedilmiş kabulün** değerleridir; yeni yayın için taze sunucu
kontrolü gerekir. Uygulama Docker Compose ile çalışır; eski PM2/API launcher'ları
repodan kaldırıldı. Dağıtım ve geri dönüş adımları [DEPLOY.md](DEPLOY.md) içindedir.

| Alan | Son kayıt |
|---|---|
| Sunucu / erişim | `root@138.68.71.27`, IP üzerinden HTTPS |
| API kaynak | `3df9640737ddb4b3f3a2cd006a2188b79d603a72` |
| Frontend kaynak | `9592c69adb355f907b6c84642bed5259fbbe6ba1` |
| Bot kaynak | `876f3f37b9d56624d17c46ab924684de559c5530` |
| API imaj | `sha256:c6a1afda9f2267e1feeb12cfe649cb75c3341ccadbe656765774b009ce14fe17` |
| Frontend imaj | `sha256:43c1755eaf03d66e2d9b222cfc08bc269d78d51b2e23228972ca016bbf5e7376` |
| Bot imaj | `sha256:a6d0e72e9430d99d01e31409b347000d175cf1d116b0b83d6298079a2fd869d5` |
| API / bot doğrudan Borsapy tabanı | `sha256:384674f3a7230ae4a6b182ac26e6114808627555988cb3305e7ed906b7d59def` (`ab18dc4`) |
| Middleware / Compose / current kaynak | `279aa9fea99b520e661b43f104a2bf4791893ac3` |
| Middleware / ortak eski backend tabanı imajı | `sha256:9be0fdb6097f52bf97730f44c86d28c24e2c0cea1fe181e7e8fd668177fdb034` |
| Veri / kaynak pointer | `/var/lib/rapot/main` ve `/opt/rapot/current`; operator kaynak kopyası bunlardan ayrıdır |
| Çalışma modu | `MW_EXECUTION_MODE=DRY_RUN`, `MW_TRADING_ENABLED=false`, `MW_BINANCE_LIVE_ENABLED=false`; AI kapalı; API/bot `BORSAPY_USE_FOR_BIST=true` |
| Son uzak kabul | 4 Ekim 16:19:02 UTC API düzeltmesi: 15 tablo şeması, motor ve özel GET, beş sayfa/13 statik/11 anonim 401 geçti. 16:19:14 UTC beş servis sağlıklı/restart0, OOM yok; boş alan 7.626.874.880 bayt. Frontend/bot/middleware/PostgreSQL kimlikleri korundu. |
| TradingView bağlantısı | Mevcut kayıtlı oturum siteden doğrulandı; canlı fiyat/mum/bölünme kabulü erteli, `realtime_verified=false` |

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
