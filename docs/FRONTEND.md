# Rapot Dashboard 📈

Rapot'un BIST/Kripto sinyallerini, ana veritabanındaki işlemleri ve bot durumunu
gösteren Next.js dashboard'u. Grafikler Lightweight Charts kullanır; TradingView
Pine/alarm akışı ve ayrı Spot middleware bu arayüzden yönetilmez.

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
`admin` veya `user` hesabını kullanın; parolalar backend ortamından yönetilir.
AI analizi ve strateji inceleme giriş, loglar ve manuel tarama admin yetkisi ister.

Token yalnız sekme belleğinde tutulur; sayfa yenileme, süre dolumu veya çıkış oturumu
sonlandırır. Oturum değişince sorgu önbelleği ve önceki kullanıcıya ait bileşen durumu
temizlenir. Token yalnız yapılandırılmış ana API adresine eklenir; health API'ye
ve başka servislere gönderilmez. `MW_ADMIN_AUTH_TOKEN` frontend'e verilmez.

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

- **Framework:** Next.js 16.3.5 (App Router)
- **Dil:** TypeScript
- **Stil:** Tailwind CSS v4
- **UI:** Shadcn/UI
- **Grafikler:** TradingView Lightweight Charts & Recharts
- **State:** Zustand & React Query

## 📱 Sayfalar

| Sayfa | Açıklama |
|-------|----------|
| **Dashboard** | Piyasa özetleri, BIST/Kripto sembol araması ve ekranlara hızlı erişim |
| **Piyasa Tarayıcı** | `/scanner` - BIST ve Kripto tarama durumu |
| **Aktif Sinyaller** | `/signals` - Filtre/arama, HUNTER/COMBO sinyalleri ve görünür satırların CSV çıktısı |
| **Grafik** | `/chart` - URL'den sembol/piyasa seçimi, izleme listeleri ve yerel alarm kuralı oluşturma |
| **Yerel Alarmlar** | `/alarms` - Bu sayfa açıkken kuralların kontrolü, kapatma ve silme |
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
- **Yerel alarm:** Kurallar bu tarayıcıda saklanır. `/alarms` açıkken ilk kontrol,
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
testi, lint, typecheck, build ve standalone HTTP/WS kontrolü geçti. Gerçek mum,
alarm/emir veya tam erişilebilirlik kabulü değildir. Üretim durumu devam planındadır.

## 🎨 Tema

Proje **Dark Mode** odaklı tasarlanmıştır. Renk paleti TradingView dark temasıyla uyumludur:
- **Arka Plan:** `#08080c`
- **Kartlar:** `#0c0c12`
- **Yükseliş (Long):** `#22c55e`
- **Düşüş (Short):** `#ef4444`
