# 21 Ekim 2026 — 631 pay canlı kapsamı ve kalıcı toparlanma

Kullanıcının piyasa açıkken verdiği talimatla elle başlatılmış çalışmadır.
Otomatik takip, timer, emir veya AI işi kurulmaz. 631 üyeli kişisel liste,
bağlı SMI N OY kuralının koşulu/bildirim tercihi ve ayrı 174 üyeli alarmsız
liste korunur. 3.000 üretim test alarmı bu çalışmanın gereği değildir.

## Başlangıçta doğrulanan arıza

Üretim kaynağı `c801e275a2848c03c2a0f1b2f29c19329955f52f`.
**07:24:10–07:25:01 UTC** altı örnekte 6.310 mantıksal native talep,
631 sürekli chart ve dört bağlı WS olmasına rağmen bütün 631 kural üyesi
hazırlıksız/eskiydi. Derlenmiş hesap ve ham native satır sayısı sıfırdı.
4.417 uzun seri doğrudan reddedilmiş, 1.262 sertifika kalmıştı; bekleyen
ve yeniden denenen lease sayısı sıfırdı. Son geçmiş hazırlığı
`2026-10-16T23:59:33.800795Z` olarak görünüyordu. Fiyat callback'lerinin
artması, hazır gösterge veya çalışan sinyal kabulü değildir.

**07:29:35–07:30:25 UTC** ayrı, salt okunur altı örnek bütün 631 kayıt için
zaman damgası ve kaynak ölçümü aldı. Katı **kaynak ve alım yaşı ≤30 saniye**
ölçümünde her örnekte 380–408 pay tazeydi; en az bir örnekte 500 pay tazeydi,
131 pay hiçbir örnekte bu eşiğe girmedi. 463 payın kaynak zamanı ilerledi.
Normal fiyat servisinin farklı tazelik eşiğiyle verdiği daha yüksek `fresh`
sayısı, özel gösterge motorunun 30 saniye şartı olarak sunulmaz.
UMPAS ve bazı İş Bankası pay kodlarında çok eski son işlem zamanları
vardı. Bu gözlem tek başına işlem sırası kapalı, hatalı kod veya veri
sağlayıcı sorunu ayrımı yapamaz; eski fiyat taze sayılmaz.

Bu kısa aralıkta API CPU tek çekirdek ölçeğinde **%35,680–45,525**;
host CPU steal dahil **%46,748–60,197**, steal **%1,113–6,305**.
Kullanılabilir host RAM **254,078–274,023 MiB**, kullanılan swap
**410,598→416,875 MiB**; swap-in/out artışı 127/1.657 sayfa.
Canlı kuyruk/taşma ve normal mum kuyruğu sıfırdı. Bu sırada gösterge
hazırlığı sıfır olduğundan bu ölçüm çalışır 631 hesap kapasitesi değildir.

**07:31:42–07:32:07 UTC** izole THYAO denemesi aynı kayıtlı hesapla yeni
oturum açarak 10 native periyodun hepsinden mum, beş fiyat olayı aldı;
sağlayıcı hatası sıfırdı. Bu, kalmış 4.417 reddin o anda bütün periyotların
erişilemez olduğunu kanıtlamadığını gösterir. Önceki reddin ham nedeni
saklanmadığı için kesin tarihsel neden belirlenemedi.

## Kaynakta bulunan nedenler ve düzeltmeler

- Reddedilen native talepler kalıcı bir kümeye konuyor; yeniden deneme
  ve yeni günlük tanık bu kümeyi açmıyordu. Uygulama katmanındaki ikinci
  ret kümesi de başarılı yeni native ACK sonrası temizlenmiyordu.
- TradingView token'ı uzun yaşayan bağlantıda süreli yenilenmiyordu.
  Yeni Gateway ile bütün THYAO periyotlarının gelmesi oturum eskimesini
  olası neden yapar; eski ret nedeni kaydı olmadığından kesinlik değildir.
- Tekrar gelen geçersiz/eski fiyat her seferinde history seed ve ham
  önbelleği siliyordu. İlk geçersiz dönem devamlılığı keser; aynı bekleme
  döneminin sonraki paketleri yeni hazırlığı tekrar iptal etmemelidir.
- SMI başlangıcı bütün replay dizilerini üretip yalnız son EMA durumunu
  kullanıyordu. Aynı native doğrulamayla tek geçişli son durum hesabı
  eklenir; replay yolu değişmez. Nihai yerel 631×10×519 sentetik hazırlık
  medyanı **10,489→6,717 saniye** (yaklaşık %36 azalma), geçici ek tahsis
  tepesi **158.236→7.068 bayt**. Bu ölçüm üretim CPU/RSS kanıtı değildir.
- Her geçmiş periyodu ayrı WS/TLS bağlantısı kuruyordu. Özel geçmiş
  işçisine ait sınırlandırılmış bağlantı paylaşımı ayrıca doğrulanır;
  canlı chart tanıkları ve geçmiş oturumları birbirine karıştırılmaz.
- İlk geçmiş hazırlığı sonuç kaydı oluşmadan iptal edilirse iş FIFO'ya
  geri konmuyordu. Yerel gerçek planlayıcı denemesinde diğer iki üyenin
  tekrar hazırlıkları 60 tur boyunca bu üyeyi bekletti. İptal edilen,
  hâlâ talep edilen iş artık kuyruğun sonuna tek kez döner. Kaldırılmış
  liste üyesi, durmuş servis veya süresi bitmiş önizleme yeniden iş üretmez.

**07:47:45–07:48:02 UTC** yeni geçmiş adaptörünün `78608580…` adayı yalnız
izole işlem belleğinde çalıştırıldı. THYAO'nun 10 periyodunda dokuz 519 ve bir 399
mum alındı; aynı bir WS, 10 oluşturulan/kapatılan chart, sıfır hata.
OHLC, native sınırlar, hesap revizyonu ve seans metadata'sı doğrulandı.
Toplam 17,541 saniye ilk hesap doğrulamasını da içerir; periyot istekleri
yaklaşık 0,5–1,2 saniyedir. Temizlikte alıcı thread ve bağlantı kapalıydı.
Üretim dosyası/kuralı değiştirilmedi. Daha sonra bağımsız incelemede
bulunan gecikmiş handshake iptal yarışı ayrıca düzeltildi; bu deneme tek
başına bütün liste veya son adayın tüm hata senaryoları kabulü değildir.
Son adaptör `efae5004…` hashindedir; gecikmiş handshake için iki deterministik
test ve toplam 23 adaptör testi geçti. Bağımsız inceleme bu düzeltmeyi doğruladı.

## Korunan kullanıcı verisi ve kanıtlar

Başlangıç kontrolünde kural revizyon 2, asıl liste revizyon 3/631 üye,
ayrı liste revizyon 1/174 üye ve altı eski gönderilmiş olay aynıydı.
07:33:25 UTC envanterinde dört servis sağlıklı, 15 tablo, iki liste,
dört kural satırı (biri etkin), 628 durum satırı ve altı olay vardı.
Eski sinyal/tarama/otomatik AI sayaçları boş kaldı; emir sıfırdı.
Durum satırı sayısı normal motorun çalışma durumudur, veri tazeliği değildir.

21 Ekim taze 1.342.660.608 bayt snapshot sunucu dışında tam SQL dump/restore
ile 15 tablonun tüm satır/şema parmak izleri üzerinden doğrulandı. Kanıt
SHA256 `6612e3d0c48f4e53ced8d4046e61cd9c2bac4173e01133547db3cf5fc558a19b`;
Snapshot SHA256 `488f90a6a05d84270d156eceacbe163ef34589760c8e459dd5db07162d64f50d`.
Yalnız bu yedeğin sunucudaki geçici kopyası, doğrulamadan sonra kaldırıldı.
Yerel 310 frontend testi, lint/types, üretim build ve standalone smoke geçti.
İlk `294a3b5` adayında 2.290 Python testi/bir atlama ve 309 Python dosyasında
Ruff geçti. Bu adayın imajı yayımlandı ancak sunucuya alınmadı; son FIFO
düzeltmesi için yeni kaynak doğrulanır. Yerel venv'de pip bulunmadığından
ayrı `pip check` çalışmadı; tam kaynak CI bağımlılık kontrolü ayrıca gereklidir.

Yerel özel kanıt yolları (kimlik bilgisi veya veritabanı Git'e alınmaz):

- `runtime-data/20261016-native-preview-acceptance/20261021-initial-observation.json`
- `runtime-data/20261021-live-acceptance/first-live-coverage.json`
- `runtime-data/20261021-native-refusal/thyao-native-refusal.json`
- `runtime-data/20261021-performance/seed-baseline.json`
- `runtime-data/20261021-performance/seed-optimized-final.json`
- `runtime-data/20261021-performance/reusable-history-live.json`
- `runtime-data/20261021-live-capacity-deploy/topology.json`

## Kabul durumu

`1d36efec58566742a226a7796238b1f82a5cda91` API/frontend/Compose/current
**08:18:27 UTC / 11:18:27 TSİ**'de yayımlandı. **08:18:47–08:19:17 UTC**
bağımsız yayın kabulü geçti. 2.298 Python testi/bir atlama, 310 frontend,
310 Python dosyasında Ruff; aynı kaynakta beş CI işi ve temiz imaj yayını geçti.

- CI: [39566987014](https://github.com/Rapto0/Rapot/actions/runs/39566987014).
- Temiz imaj yayını: [39566991883](https://github.com/Rapto0/Rapot/actions/runs/39566991883).
- API: `ghcr.io/rapto0/rapot/backend@sha256:803514908db1b2066ebfa20a79eaeaa1455b7f1a0dc1b94d0b95cf6281d63dbc`.
- Frontend: `ghcr.io/rapto0/rapot/frontend@sha256:9e3375e22e46fded2b93177502ee2cad54a6e206b70bef472896070dae265e1b`.
- Yayın receipt: `2fad34c67b23dc063cc6ae6158c409dec495d8cd1d20ac61c7cd1b9064604f06`.
- Bağımsız kabul: `7ec7e2fce583311e58f53bc8b3cac666a702a141867efffbe18821bb72a39c95`.

Dört servis sağlıklı; middleware/PG, özel dosyalar, 15 tablo şeması/statik
veri ve mevcut kullanıcı tanımları korundu. 13 SSR/33 statik dosya/iki
yönlendirme/18 anonim 401; 315 kaynak ve bağımlılık dosyası kabulü geçti.
Yayın için ek imaj gereksinimi 11.339.908 bayttı; imaj temizliği yapılmadı.
Son kabulde boş alan 4.035.911.680 bayt, kullanılabilir RAM 314.028.032 bayttı.

Bütün paylarda gösterge hazırlığı, normal motor alarmı ve yayın sonrası
sürekli kaynak ölçümü ayrıca yürür. Bu yayın kabulü, başlangıçta sıfır olan
631 özel hesabın artık tamamının hazır olduğunu veya kalıcı kapasiteyi kanıtlamaz.

## İlk yayın sonrası canlı kontrol ve ikinci düzeltme

08:19:36–08:20:25 UTC başlangıç örneklerinde bütün 6.310 talep kabul edildi,
ret sıfırdı; derlenmiş hesap 5'ten 11'e çıktı. Geçmiş bağlantısı bir WS üzerinde
56'dan 116 tamamlanmış isteğe ilerledi. CPU %67,531–84,357, kullanılabilir
RAM 263,92–298,10 MiB, son canlı kuyruk 76/taşma 0 idi; bunlar başlangıç yüküdür.

08:29:42–08:30:33 UTC örneklerinde seçili SMI çıktıları hazır pay sayısı
60/62/72/75/73/62, kaynak ve alınma zamanı 30 saniye içindeki fiyat sayısı
331/341/364/365/368/346 oldu. Son örnekte 129 toplam derlenmiş ayar,
5.690 üst periyot tanığı, sıfır native ret/bekleyen tanık, canlı kuyruk 5,
taşma 0; normal mum kuyruğu 0 vardı. Derlenmiş ayarlar önizlemeleri de içerir.
İki liste ve etkin kural tanımları aynı, teslimler altı eski olaydı.

İki ayrı 180 saniyelik THYAO/BTCUSDT beşli önizleme denemesi tamamının
hazırlığını doğrulayamadı; başarısız kayıtlar korundu, test alarmı açılmadı.
Gerçek varsayılan ayarlarda eski önizleme geçmişi tek sembolde 67.584,
iki sembolde 135.168 hücre isterken bütçe 32.768 idi. Göstergeler birbirinin
geçmişini çıkarıyor ve tekrar replay işi oluşturuyordu. Geçmiş noktaların
çıktıları korunarak yalnız yinelenen TF satırları inceltildi; son noktanın
satırları tam kalır. On gerçek ayarlı regresyonda üç yeni fiyat turu boyunca
yeni geçmiş isteği/replay sıfır, aynı başlangıç hesapları ve bütün çıktılar
korundu. Eski davranış aynı testte önbellek kaybıyla başarısızdır.

İkinci kaynak değişikliği geçmiş taleplerini tek sembolde sınırlı gruplar.
Kontrollü 0,6 saniyelik yanıt modeliyle 10×519 mum medyanı 6,362→1,921 saniye;
10/10 veri hashleri aynı, geçici tepe tahsis 0,54–0,85→1,32–1,46 MiB'dir.
Bu yerel ölçüm üretim CPU/RSS değildir. **08:35:57–08:36:11 UTC** yalnız
izole işlem belleğindeki gerçek THYAO denemesi 10 periyodu **2,074 saniyede**
aldı; bir WS, 10 açılan/kapatılan chart, hata sıfır, bütün native/OHLC/seans
kontrolleri geçti. Dokuz periyot 519, aylık seri 399 mum döndürdü. İşlem sonunda
alıcı ve kaynak koruma thread'leri kapandı. Bu deneme üretim dosyalarını veya
alarmları değiştirmedi; 631 pay ve kalıcı kapasite kabulü değildir.

Bu canlı deneme `9e6fb4da…` adaptörüne aittir. Son bağımsız incelemede yavaş
chart gönderiminin sonraki 0,1 saniyelik aralığı tükettiği görüldü; aralık
başarılı gönderim sonrasından başlatılarak sıkılaştırıldı. Yeni regresyon
ilk tam turda tek hata verdi (2.323 başarılı/bir atlama); başarısız log korunur.
Son `85b8bd93…` adaptöründe 36 transport testi ve iki bağımsız önizleme testi
geçti. Son kaynağın tam turu ve yayını ayrıca kaydedilir.

08:39:13–08:40:05 UTC'de ilk yayın hâlâ çalışırken derlenmiş hesaplar
259→272, o anda seçili çıktıları hazır üyeler 127–138 aralığındaydı.
CPU %52,272–64,966, kullanılabilir RAM 259,598–286,238 MiB; son kuyruk 6,
taşma 0 ve ret 0. Bu aşamada ikinci kaynak henüz üretimde değildi.
