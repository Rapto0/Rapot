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

Yerel özel kanıt yolları (kimlik bilgisi veya veritabanı Git'e alınmaz):

- `runtime-data/20261016-native-preview-acceptance/20261021-initial-observation.json`
- `runtime-data/20261021-live-acceptance/first-live-coverage.json`
- `runtime-data/20261021-native-refusal/thyao-native-refusal.json`
- `runtime-data/20261021-performance/seed-baseline.json`
- `runtime-data/20261021-performance/seed-optimized-final.json`
- `runtime-data/20261021-performance/reusable-history-live.json`
- `runtime-data/20261021-live-capacity-deploy/topology.json`

## Kabul durumu

Bu kayıt başlangıç bulgularıdır; yeni kaynağın yayını, bütün paylarda
gösterge hazırlığı, normal motor alarmı ve yayın sonrası kaynak ölçümü
tamamlandıkça ayrı kanıtla eklenir. Başlangıçta **0/631 hazır özel hesap**
varken tam canlı kapsam veya kalıcı CPU/RAM çözümü kabul edilmez.
