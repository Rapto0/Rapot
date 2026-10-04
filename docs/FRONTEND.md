# Rapot Dashboard 📈

Rapot'un BIST/Kripto sinyallerini, ana veritabanındaki işlemleri ve bot durumunu
gösteren Next.js dashboard'u. Grafikler Lightweight Charts kullanır; TradingView
Pine/webhook akışı ve ayrı Spot middleware bu arayüzden yönetilmez.
Rapot'un kendi kalıcı sunucu alarmları `/alarms` ekranından yönetilir.

Güncel iş sırası, doğrulama ve yayın kayıtları [Rapot Devam Planı](RAPOT_DEVAM_PLANI.md)
içindedir. P2-1 ekran davranışları, P2-4 eşzamanlı yük ve P3-1 COMBO sıfır-değer
düzeltmesi kabul edildi. Python/TypeScript/Pine farkları
[karşılaştırma belgesinde](STRATEGY_COMPARISON.md), güncel Pine derleme/grafik
kabulü [ayrı kayıtta](PINE_RUNTIME_ACCEPTANCE.md) açıklanır.

## 🚀 Başlangıç

Node 20.20.2 ve npm 10.9.9 kullanılır. Kurulum ve doğrulama adımları
[devam planında](RAPOT_DEVAM_PLANI.md#geliştirme-ortamı-ve-komutlar) kayıtlıdır.
Repo kökündeki `frontend/` dizininde geliştirme sunucusunu başlatmak için:

```bash
npm ci
npm run dev
```

Tarayıcınızda [http://localhost:3000](http://localhost:3000) adresine gidin.

Dashboard'un gerçek verisi için ana API ve bot health servisi ayrıca çalışmalıdır.
Varsayılan tarayıcı yolları `/api` ve `/health-api`; Next proxy hedefleri sırasıyla
`http://localhost:8000` ve `http://localhost:5000`'dir. Bunlar
[`next.config.ts`](../frontend/next.config.ts) içindeki `API_PROXY_TARGET` ve
`HEALTH_PROXY_TARGET` ile yapılandırılır. Public istemci adresleri
`NEXT_PUBLIC_API_URL` ve `NEXT_PUBLIC_HEALTH_API_URL` ile değiştirilebilir;
standalone dağıtımda build sırasında kullanılan hedefleri de kontrol edin.
Sunucu sırları `NEXT_PUBLIC_*` değişkenlerine konmaz.

## Oturum ve doğrulama

Üst çubuktaki **Giriş yap** bağlantısı `/login` ekranını açar. Ana API'de tanımlı
`admin` hesabını kullanın; parolalar backend ortamından yönetilir. Kişisel
dashboard verileri, analizler, takvim ve işlemler admin yetkisi ister; `user`
rolü bu özel verilere erişmez. HTTP yanıtları `private, no-store` taşır.

Token yalnız sekme belleğinde tutulur; sayfa yenileme, süre dolumu veya çıkış oturumu
sonlandırır. Oturum değişince sorgu önbelleği ve önceki kullanıcıya ait bileşen durumu
temizlenir. Token yapılandırılmış ana API adresine ve aynı origin'deki
yapılandırılmış health API'nin yalnız `/status` yoluna eklenir; harici health
adresine veya başka sağlık yollarına otomatik gönderilmez. `MW_ADMIN_AUTH_TOKEN`
frontend'e verilmez. Başlıksız bot `/status` yanıtı yalnız DB/yerel lifecycle
sağlığıdır; kişisel sayaç/hata ayrıntıları admin ister. İki yanıt da
`private, no-store` ve `Vary: Authorization` kullanır.
Backend WebSocket bağlantısı yalnız admin oturumunda açılır. İlk mesaj
`{type: "auth", token}` olur; `authenticated` yanıtı gelmeden abonelik başlamaz.
Token URL'ye konmaz. 4401/4403 bağlantıyı yeniden denemeyi durdurur ve özel
realtime durumu temizler. API'nin SSE yolu Bearer başlığı ister; frontend şu an
SSE tüketmez. Oturum değişimi bütün özel realtime/sorgu sonuçlarını temizler.

```bash
npm test
npm run lint
npm run typecheck -- --incremental false
npm run build
```

`npm test`, [package.json](../frontend/package.json) içindeki Node test dosyalarını çalıştırır.
Gerçek TypeScript modülleri ve seçili React callback/render davranışları bellekte
derlenir; HTTP, WebSocket, saat ve tarayıcı depolaması test çiftleriyle denetlenir.
Oturum/API, scan-history, realtime yeniden bağlantı, eski ayar temizliği,
health/PnL, chart URL, CSV, yerel alarm lifecycle/sekme eşgüdümü ve header saatini
kapsar. Backend, dış ağ veya gerçek kullanıcı hesabı gerekmez. Güncel test sayısı
ve geçmiş sonuçlar devam planında tutulur.

Yerel proxy hedefleriyle alınmış bir build sonrasında:

```bash
npm run test:standalone
```

Bu smoke testi `.next/standalone` altında statik dosyaları hazırlar, geçici Next
sunucusu ve sahte API/health dinleyicileri açar; HTTP, statik varlık, chart SSR/RSC
ve WebSocket upgrade yollarını denetler. Varsayılan 8000/5000 portları test için
boş olmalıdır. Gerçek API/bot veya üretim hedefi kullanmaz; gerçek piyasa verisi
ve sunucu kabulünün yerine geçmez.

Kilitli bağımlılık güvenliğini ayrıca doğrulayın:

```bash
npm run audit:dependencies
```

Bu komut public npm registry'ye bağlanır; prod/dev/optional/peer paketlerini
kilit dosyasına bağlı kapsamla tarar. Her bulgu ve araç/ağ/rapor hatası başarısız
sonuç üretir. Raporlar repo kökünde `security-reports/npm/` altında tutulur;
`NPM_AUDIT_REPORT_DIR` farklı çıktı klasörü seçer. Guard'ın ağsız negatif/pozitif
testleri `npm test` içindedir. Advisory kararları ve npm 10'un iki optional
platform paketi için ürettiği `npm ls` uyarısı
[bağımlılık incelemesinde](FRONTEND_DEPENDENCY_SECURITY.md) açıklanır.

## 🛠️ Teknolojiler

- **Framework:** Next.js 16.3.8 (App Router)
- **Dil:** TypeScript
- **Stil:** Tailwind CSS v4
- **UI:** Shadcn/UI
- **Grafikler:** TradingView Lightweight Charts & Recharts
- **State:** Zustand & React Query

## 📱 Sayfalar

| Sayfa | Açıklama |
|-------|----------|
| **Dashboard** | Piyasa özetleri, BIST/Kripto sembol araması ve ekranlara hızlı erişim |
| **Piyasa Tarayıcı** | `/scanner` - BIST/Kripto COMBO-HUNTER geçmişi, Borsapy temel/teknik tarama |
| **Aktif Sinyaller** | `/signals` - Filtre/arama, HUNTER/COMBO sinyalleri ve görünür satırların CSV çıktısı |
| **Grafik** | `/chart` - BIST Borsapy/TradingView, Kripto Binance, izleme listeleri ve sunucu alarmı taslağı |
| **Araştırma** | `/research` - Borsapy katalog, sanal portföy, replay ve sunucu hesap bağlantıları |
| **Ekonomik Takvim** | `/calendar` - Borsapy/Doviz.com olayları, ülke/önem/tarih filtreleri ve kaynak uyarıları |
| **Sunucu Alarmları** | `/alarms` - Yöneticiye ait kalıcı kural oluşturma/düzenleme, duraklatma ve teslim geçmişi |
| **Eski Yerel Alarmlar** | `/alarms/local` - Bu sayfa açıkken eski tarayıcı kurallarının kontrolü |
| **İşlem Geçmişi** | `/trades` - Ana DB işlemleri; hesaplanabilir PnL, eksik veride bilinmeyen değer |
| **Bot Sağlığı** | `/health` - Bot yaşam döngüsü, tarama sonucu, admin logları ve sistem metrikleri |
| **Ayarlar** | `/settings` - Sunucuda yönetilen ayarların açıklaması ve tarayıcı tercihlerinin kapsamı |

## Ekran davranışları ve sınırlar

- **CSV:** `/signals` üzerindeki Dışa aktar, filtre/arama sonrası görünen satırları
  aynı sırayla indirir; veri kümesi en fazla yüklenen 300 sinyaldir. Tüm arşivi
  çekmez. UTF-8 BOM, Türkçe başlıklar, noktalı virgül ayırıcı, CSV kaçışları ve
  formül başlangıcı taşıyan metin hücreleri için koruma kullanılır. Boş, yüklenen,
  yenilenen veya hatalı veri dışa aktarılmaz.
- **Grafik URL:** `/chart?symbol=BTCUSDT&market=Kripto` ve
  `/chart?symbol=THYAO&market=BIST` doğrudan açılabilir. Tekrarlı parametrede ilk
  değer kullanılır; piyasa `Kripto` değilse BIST, geçersiz/boş sembolde seçilen
  piyasanın varsayılanı BTCUSDT veya THYAO uygulanır. Sembol doğrulaması biçimseldir;
  sağlayıcıda gerçekten listelenmesi ayrıca veri yanıtına bağlıdır.
- **Sunucu alarmı:** `/alarms` yönetici oturumu ister. Kurallar ana DB'ye kaydedilir;
  API motoru tarayıcı ve oturumdan bağımsız çalışır. Grafik üzerinden sembol/listeden
  kural taslağı açılabilir. Telegram varsayılan kapalıdır. Durum, son kontrol,
  hata ve teslim geçmişi görünür; başarısız yenileme mevcut kayıtları silmez.
  BIST yalnız günlük (`1d`), Binance Spot USDT ise `1h`/`4h`/`1d` destekler;
  BIST içeren karma listelerde de saatlik seçim reddedilir. BIST günlük mumları,
  Türkiye saatinde ertesi gün 00.00 geçince kapanmış kabul edilir. Her kontrol
  turundan sonra yaklaşık 60 saniye beklenir; tüm semboller aynı turda
  tamamlanamayabilir. Form, desteklenmeyen periyodu sessizce değiştirmez.
  [Hesaplama, periyot ve teslim sınırları](SERVER_ALARMS.md) geçerlidir.
- **Piyasa kaynağı:** BIST grafik, dashboard ve izleme listesi Borsapy/TradingView
  kullanır; kimlik veya sağlayıcı hatasında eski kaynağa sessiz dönüş yoktur.
  Kaynak, alınma zamanı, sağlayıcı zamanı ve bayat/bekleniyor/hata durumu ayrı
  gösterilir. Bağlantı açık olması gecikmesiz veri kanıtı değildir. İzleme
  listesindeki ilk 50 BIST sembolü takip edilir; sunucu ortak havuzu en fazla
  200 etkin sembolle sınırlıdır. Günlük geçmiş hazırlanırken 7/30 günlük
  performans/mini grafik beklenebilir; bilinmeyen değişim sıfır yapılmaz.
  Binance sembolleri BtcTurk verisiyle değiştirilmez.
- **Takvim:** Borsapy/Doviz.com genel kaynağı TradingView/Finnhub kimliği istemez;
  Rapot admin oturumu gerekir. En fazla üç ülke ve 31 günlük aralık seçilir;
  aralık İstanbul gününe göre son 7 gün ile gelecek 30 gün içinde olmalıdır.
  Kaynak saat dilimi doğrulanmadığı için tarih/saat İstanbul'a çevrilmez.
  Boş sonuç, eksik saat ve eski önbellek uyarıları görünür; sağlayıcının bir
  saatlik önbelleği nedeniyle yeniden sorgulama yeni veri garantisi değildir.
- **Yerel alarm:** Eski kurallar bu tarayıcıda saklanır. `/alarms/local` açıkken ilk kontrol,
  ardından yaklaşık 60 saniyelik kontrol vardır; devam eden tura yenisi eklenmez.
  Sayfa kapanınca durur; arka plan zamanlayıcıları tarayıcı tarafından geciktirilebilir.
  Veri hatası, eksik gösterge ve kısmi kontrol başarılı bir “tetik yok” sonucu
  olarak gösterilmez. Bu akış Telegram bildirimi veya sunucuda 7/24 alarm hizmeti değildir.
- **Sekme eşgüdümü:** Grafik ve alarm sayfası diğer sekmeden gelen kural değişimini
  okur. Kullanıcı işlemi güncel kayıtlara uygulanır; eski React listesi topluca
  kaydedilmez. Bozuk/erişilemeyen depolamada değişiklik başarısız görünür.
  localStorage işlem kilidi sağlamadığından gerçekten eşzamanlı iki yazımda son
  yazan davranışı devam eder.
- **Ayarlar:** API anahtarı girme veya bot stratejisi/tarama/Telegram ayarı
  değiştirme formu yoktur. Bot yapılandırması sunucuda yönetilir. Başlangıçta
  eski `rapot.settings.v1` ve `rapot-settings` kayıtlarından gizli alanlar
  allowlist ile temizlenir; tutulan sayısal/bool değerler etkisiz geçmiş kaydıdır.
  Gerçek izleme listesi/sütun/filtre tercihleri kendi ekranlarından düzenlenir.
- **Veri ayrımı:** `/trades` ve dashboard ana API kayıtlarını gösterir; ayrı
  middleware envanteri, borsa bakiyesi veya gerçek emir durumunun dashboard'a
  bağlandığı varsayılmamalıdır. Frontend COMBO/HUNTER hesaplamalarıyla Python/Pine
  hesaplamalarının birebir eşitliği ayrıca doğrulanmış değildir.

Bu site geneli özel veri ve Borsapy kaynak değişikliklerinin API/frontend/bot
yayını henüz tamamlanmadı. Sentetik yerel tarayıcı kabulü gerçek hesap, piyasa
gecikmesi veya bildirim teslimi kabulünün yerine geçmez; güncel durum devam planındadır.

## Gezinme ve arama iyileştirmesi — 21 Eylül 2026

- Mobil alt menü dört ana ekran ve **Diğer** düğmesini içerir. Alarmlar,
  İşlemler, Bot Sağlığı, AI Analizi, Takvim ve Ayarlar bu menüden açılır.
  Native dialog odağı içeride tutar; Escape, kapatma düğmesi, dış alan,
  sayfa seçimi ve masaüstü genişliğine geçişte kapanır. Alt boşluk cihazın
  güvenli alanını hesaba katar. Masaüstü menü adları geniş ekranda görünür;
  kısa ekranlarda menü kaydırılabilir. Aktif bağlantı `aria-current` taşır.
- **İçeriğe geç** bağlantısı ve belirgin klavye odağı eklendi. Ana arama
  açık BIST/Kripto seçimi kullanır; varsayılan BIST'tir. `BTCIM` gibi BIST
  sembolleri artık `BTC` metni nedeniyle Kripto'ya yönlenmez. Enter ve düğme
  aynı formu gönderir. Boş/geçersiz sembol açıklanır ve girişe odaklanılır;
  geçerli biçim sağlayıcıda listelenme garantisi değildir.
- Arama kontrolleri 44 px, sembol giriş yazısı 16 px'tir. Ana ekran başlığı
  kısaltıldı, piyasa kartları mobilde iki sütun oldu. Grafik araçları dar
  alanda sarılır; 1024 px altında izleme paneli grafiğin altına geçer.
  Grafik yüksekliği üst/alt gezinme alanıyla eşleşir; hesaplama değişmedi.

Yerel tarayıcı kontrolünde 320, 390, 768 ve 1280 px genişlikler; boş arama,
BIST/BTCIM Enter gönderimi, Kripto/ETHUSDT düğme gönderimi, sağlık ekranına
menüden erişim, Escape/resize kapanışı ve yatay taşma kontrol edildi. 44 px
kontrol yüksekliği ve odaklanan girişin 16 px yazısı DOM üzerinden ölçüldü.
API/health hedefleri kullanılmayan yerel portlardı; grafik kabulü yerleşim ve
yönlendirme kapsamındadır. Bu, gerçek mum/veri doğruluğu veya dış alarm/emir
kabulü değildir. Mevcut Binance fiyat akışı salt okunur kaldı.

Altı yeni arama regresyonuyla frontend **119 test** geçer. Güncel CI ve
üretim sürümü [devam planından](RAPOT_DEVAM_PLANI.md) izlenir.

`7b90365` kaynağı 21 Eylül'de yalnız frontend yenilenerek üretime alındı.
CI, sekiz sağlık/sayfa isteği, iki grafik rotası ve 11 JS + 1 CSS kontrolü geçti.
Canlı HTTPS tarayıcıda yeni ana ekran, alt menüdeki altı ek rota, Escape ile
kapanma/odağın dönüşü ve boş aramanın açıklamalı hatası görüldü. Bu kontrol tam
erişilebilirlik denetimi veya bütün ekranların etkileşimli kabulü değildir.

## Piyasa verisi durumları — UI-2

Ana sayfa her grupta alınabilen fiyat sayısını, yükleme/eksik veri/boş yanıt/hata
durumunu ve **Yenile** düğmesini gösterir. İlk isteğin hatası boş fiyatlarla,
sonraki isteğin hatası son alınan fiyatlarla ve açık uyarıyla görünür. Başarılı
ama kısmi/boş yanıtta eksik semboller eski yanıttan taşınmaz. Sonlu sıfır korunur;
null, metin, NaN veya sonsuz fiyat gösterilmez. Eksik fiyatın yüzdesi de gösterilmez.

- BIST/ABD/emtia/döviz özeti React Query ile 10 saniyede bir denetlenir;
  görünür sekmeye dönüşte de yenilenir. Tek sorgu paylaşılır; sürmekte olan
  isteğe elle yenileme ikinci istek eklemez. İstek 60 saniyede iptal edilir;
  sayfadan çıkışın iptal sinyali HTTP'ye ulaşır. 30 saniyedir başarılı yanıt
  alınmadığında gecikme görünür. Arka plan sekmesi ve tarayıcı zamanlayıcıları
  bu süreleri geciktirebilir; bunlar teslim garantisi değildir.
- **Son başarılı yanıt**, tarayıcının yanıtı aldığı zamandır. API son mevcut
  günlük veriyi kullanır; borsa zamanı/cache yaşı veya her sembolün hata nedenini
  vermez. Boş HTTP 200 yanıt fiyat bulunduğunu göstermez. Gösterim, piyasa verisinin
  gerçek zamanlı veya işlem yapılabilir olduğunu doğrulamaz.
- Kripto kartları bağlantıyı ve her sembolün son geçerli mesaj alımını ayrı izler.
  Fiyat değişmese de alım zamanı ilerler. 30 saniyelik sessizlik uyarı üretir;
  ilk geçerli mesaj hiç gelmezse de bekleme açıklamaya dönüşür. Kopma, normal
  uzak kapanış ve tarayıcı çevrimdışı/çevrimiçi geçişi görünür. Bağlantı açılışı
  20 saniyede bırakılır; tekrarlar 1–10 saniye aralıkla denenir. Eski socket/timer
  olayları temizlenir. Grafik/izleme listesinin eski `useBinanceTicker` fiyat
  haritası ve `paused`/biriktirme seçenekleri korunur.

Yerel kabul sentetik HTTP ile ilk hata, eksik/boş yanıt, eski fiyatla hata ve
elle yenilemeyle toparlanmayı; 320/768/1280 px taşma kontrolünü ve 44 px yenileme
düğmesini kapsar. Kripto bağlantısını yenileme salt okunur akışla gözlendi;
kopma/zaman aşımı/bozuk paket senaryoları ağsız test edildi. Toplam 155 frontend
testi, lint, typecheck, build ve standalone HTTP/WS kontrolü geçti. `13e5fbb`
kaynağı yalnız frontend yenilenerek üretime alındı. Exact CI ve sekiz sağlık/sayfa
kontrolü, iki grafik rotası ve 11 JS + 1 CSS geçti. Canlı tarayıcıda BIST/Kripto
fiyatlarının görünmesi, durumlar, alım süreleri ve BIST **Yenile** düğmesi doğrulandı. Gerçek mum,
alarm/emir veya tam erişilebilirlik kabulü değildir. Yayın kanıtları devam planındadır.

## Sinyaller ve Tarayıcı — UI-3

2 Ekim 2026: iki ekranda etiketli, en az 44 px filtre kontrolleri; etkin
seçimlerin tekli/tümü temizliği ve yükleme/hata/boş sonuç ayrımı eklendi.
Sayılar yüklenen kayıt kapsamını açıklar. İlk bağlantı bekleme durumu boş
başarılı yanıt sayılmaz. Yenileme hatasında eldeki satırlar uyarıyla kalır;
başarılı boş yanıtta eski satırlar kaldırılır.

- **Sinyaller:** piyasa/strateji/yön/özel etiket API filtreleri ve yerel sembol
  araması korunur. Tüm piyasalarda 150 BIST + 150 Kripto, tek piyasada en fazla
  300 kayıt alınır; arama tüm geçmişi taramaz. CSV yine yalnız görünen satırları
  indirir; hata/yükleme/yenilemede kapalıdır. Satır seçimi klavyeden sembol
  düğmesiyle yapılır; sonuç tablosu klavyeyle yatay kaydırılabilir.
- **Tarayıcı:** her piyasanın en son 700 sinyalinden sembol özeti üretir.
  Strateji/yön/periyot sembolün son sinyaline göre süzülür. Ayrı filtreler AND,
  seçili periyotlar kendi aralarında OR'dur. Gizlenen sütunun sayısal filtresi
  etkin kalır ve özetinde görünür; kayıtlarda artık olmayan seçili periyot da
  kaldırılabilir. Temizleme izleme listelerini, görünümü ve sıralamayı korur.
  Bir piyasanın yenileme hatası diğer mevcut satırları gizlemez.
- **Tercihler:** Tarayıcı filtre/görünüm/listeleri mevcut v2 anahtarlarında
  hatırlar; arama metni saklanmaz. Bozuk JSON veya engellenen depolama ekranı
  düşürmez. Anahtarlar bağımsız okunur; okuma hatasında otomatik yazma durur,
  ham kayıt ezilmez. Yazma hatasında kalıcılık uyarısı görünür. Bu üç anahtarın
  yazımı atomik değildir ve sekmeler arası eşzamanlılık garantisi eklenmedi.
- **Ortak işlem penceresi:** native dialog, başlık/açıklama bağlantısı, ilk
  odak, Tab/Shift+Tab sınırı, Escape ve kapanınca tetikleyiciye dönüş sağlar.
  Bekleyen işlemde yeniden gönderme/iptal engellenir. Tarayıcı ve Alarmlar
  mevcut props sözleşmesini kullanmaya devam eder.

İlk UI-3 CI'sinde mevcut lock için güvenlik bulguları yayın kapısını durdurdu.
Next/eslint-config-next 16.3.8 ve dar brace-expansion 1.1.21/2.1.7 yamaları
aynı yayına dahil edildi; [advisory ve lock incelemesi](FRONTEND_DEPENDENCY_SECURITY.md)
ayrıntıları içerir. Audit kapısı gevşetilmedi.

API istekleri, sorgu sıklıkları, fiyat/gösterge hesapları ve strateji eşikleri
değişmedi. Tarayıcı metrik yardımcısının bazı parça hatalarını boş/kısmi haritaya
dönüştüren mevcut davranışı sürer; uyarı tüm sağlayıcı hatalarını tespit etme
garantisi değildir. Bu çalışma tam erişilebilirlik veya gerçek veri/emir kabulü
değildir. 37 yeni regresyonla 192 frontend testi, lint/typecheck, build/standalone
geçti. Yerel 320/768/1280 px tarayıcı kontrolü; filtre birleştirme/temizleme,
başarılı boş yanıt, eldeki satırlarla yenileme hatası, 44 px/16 px kontroller ve
dialog Tab/Shift+Tab/Enter/Escape odağını kapsar. Fixture yalnız loopback sentetik
GET yanıtlarıdır. Yayın sonucu [devam planında](RAPOT_DEVAM_PLANI.md).

**Üretim kabulü, 2 Ekim:** `db534fb` kaynağı exact beş CI işi ve imaj yayını
sonrasında yalnız frontend yenilenerek **09:52:39 UTC**'de üretime alındı;
imaj digest'i `sha256:feaa0325…`, backend/Compose/current `279aa9f` korundu.
Dış HTTP kabulünde ana sayfa, Sinyaller, Tarayıcı ve iki grafik URL'si ile
**20 JS + 1 CSS** geçti. Canlı tarayıcıda 320/768/1280 px taşma kontrolü,
filtre/arama boş sonucu, tekli/tümü temizleme ve odak dönüşü; işlem penceresinde
Tab/Shift+Tab, Escape ve Enter doğrulandı. Kontroller 44 px, metin girişi 16 px
ölçüldü. Kabul anında Sinyaller 300 kayıt, Tarayıcı 1.400 sinyalden 325 sembol
gösterdi; BIST filtresi 102 sembol, sayısal filtre boş sonuç verdi ve temizleme
325 sembole döndürdü. Bu sayılar sabit ürün toplamı değil, kabul anı gözlemidir.

Tarayıcıda **ek metriklerin beklediği uyarısı kabul boyunca görünür kaldı**;
etkileşim kabulü bu uyarının veya tüm sağlayıcı/metrik yolunun düzeldiğini
göstermez. Üretim kanıtları Git dışında `runtime-data/ui3-http-acceptance.json`
ve `runtime-data/ui3-browser-acceptance.json` dosyalarındadır. Next/Node sürüm
metadata'sı [güvenlik belgesinde](FRONTEND_DEPENDENCY_SECURITY.md) ayrıca kayıtlıdır;
fiyat doğruluğu, gerçek alarm/emir ve tam erişilebilirlik kabulü kapsam dışıdır.

## 🎨 Tema

Proje **Dark Mode** odaklı tasarlanmıştır. Renk paleti TradingView dark temasıyla uyumludur:
- **Arka Plan:** `#08080c`
- **Kartlar:** `#0c0c12`
- **Yükseliş (Long):** `#22c55e`
- **Düşüş (Short):** `#ef4444`
