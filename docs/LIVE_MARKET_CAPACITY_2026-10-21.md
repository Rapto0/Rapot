# 21 Ekim 2026 — 631 pay canlı kapsamı ve kalıcı toparlanma

Kullanıcının piyasa açıkken verdiği talimatla elle başlatılmış çalışmadır.
Otomatik takip, timer, emir veya AI işi kurulmaz. 631 üyeli kişisel liste,
bağlı SMI N OY kuralının koşulu/bildirim tercihi ve ayrı 174 üyeli alarmsız
liste korunur. 3.000 üretim test alarmı bu çalışmanın gereği değildir.

## Sonuç — son üretim kaynağı e28ef616

- Retlerin yeniden denenmesi, süreli oturum yenilemesi, ortak/sınırlı geçmiş
  bağlantısı, yinelenen önizleme hesabı ve her fiyatta ayar doğrulama maliyeti
  düzeltildi; dört aşamalı kaynak yayını bağımsız kabul edildi.
- Etkin 631 üyeli SMI kuralının bütün geçmiş hesapları hazır; 6.310 mantıksal
  periyot, 631 sürekli günlük abonelik ve 5.679 üst periyot tanığı mevcut.
  Yayın sonrası ilk bütün-liste hazırlığı yaklaşık 26 dakika sürdü.
- THYAO/BTCUSDT beşli önizleme, süre dolduktan sonra yeniden açılış ve normal
  karma liste alarmı geçti. Son iki testte motor girdisi→olay kaydı
  10,572/23,730 ms; bildirimsiz test nesneleri temizlendi. Bu borsa→Telegram
  gecikmesi değildir. Mevcut teslim sayacı son pencerede 13 başarılı, sıfır
  bekleyen/hata gösterdi; altı bildirimsiz test olayı ayrı kaldı.
- Son kaynağın 11 kesikli penceresi/66 örneğinde **584/631 farklı üyede taze
  normal fiyat**, **573/631 üyede hazır seçili gösterge çıktısı** görüldü.
  Hazır çıktı görülmeyen 58 üyenin son nedenleri 33 eski fiyat ve 25 yeni
  fiyat beklemesidir. Aynı anda 631 taze fiyat kabulü yapılmadı.
- Geçmiş hazırlığı bitmiş üç kısa pencerenin ağırlıklı API CPU'su **%43,883**;
  API belleği 235,570–244,996 MiB, kullanılabilir sunucu RAM'i
  199,723–224,098 MiB. Normal mum işi/kuyruğu ve taşma sıfır; canlı işleme
  kuyruğunda kısa beklemeler var. Oturum yenilemesi 631 hesabı korudu.
  Swap hareketi sürdüğünden bellek baskısının tamamen bittiği iddia edilmez.
- 2.346 Python/bir atlama, 310 frontend testi, beş CI işi ve temiz imaj
  yayını geçti. Son kayıt yalnız belge güncellemesidir; çalışan kaynak
  `e28ef616a3155b09b62fa699513d948dc8d5d528` korunur.

Tam seans kesintisizlik, aynı anda 3.000 canlı kural, TradingView Pine
derleyicisiyle sayısal eşitlik, tüm BIST üyelerinde sürekli taze fiyat ve
kalıcı kaynak kazanımı henüz kanıtlanmadı. THYAO/GARAN günlük mumlarında
hacim yok; takvimde üç etkinlik grubu sınırlı kontrol edildi, genel kaynak
saat dilimi açık. Kullanıcı listeleri/koşulları değişmedi; otomatik takip
kurulmadı. Aşağıdaki kayıtlar her kaynak sürümünü ve başarısız denemeyi
ayrı tutar.

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

08:50:44 UTC'de ilk kaynağın otomatik token yenileme sayısı 1, yenileme
hatası/ret 0, derlenmiş hesap 426, o anda seçili çıktıları hazır üye 217 idi.
08:58 yayın ön kontrolünde kullanıcının değişmeyen SMI kuralına ait üç yeni
olayın her biri `sent`/bir deneme durumundaydı; toplam olay 6→9 oldu.
Bu kullanıcı alarmının normal ilerlemesidir; test kuralı oluşturulmadı.

## İkinci kaynak yayını

`85feb159968e6a6094e14660b9e278749bc6294c` API/frontend/Compose/current
**08:59:54 UTC / 11:59:54 TSİ**'de yayımlandı; **09:00:35–09:01:09 UTC**
bağımsız kabul geçti. Son sabit kaynakta 2.324 Python/bir atlama, 313 Python
dosyasında Ruff; 310 frontend testi ve aynı kaynakta beş CI işi/temiz imaj
yayını başarılıdır. İlk tam turdaki pacing regresyonu giderilerek tam tur
yeniden çalıştırıldı; başarısız kayıt silinmedi.

- CI: [39571978451](https://github.com/Rapto0/Rapot/actions/runs/39571978451).
- Temiz imaj: [39572015353](https://github.com/Rapto0/Rapot/actions/runs/39572015353).
- API: `ghcr.io/rapto0/rapot/backend@sha256:114efb8b7fa9d8da879ab8fab830af58c68ae9a58d79c8fc56dc17037f322f8c`.
- Frontend: `ghcr.io/rapto0/rapot/frontend@sha256:0923364641b905e7740d2138b96e1dde18d0dc23f34d628f2426172bffbcd484`.
- Yayın receipt: `f833ce933c03e3f7b7d66efa66e905a5dc2afbf375da62e608c7480873994d5d`.
- Bağımsız kabul: `fb16e8d81b79c130fdc3db860603a1fdb66bfb431ad5b78d2066e17c029b3556`.
- Taze 1.342.660.608 bayt yedek SHA: `4bc3c761a23199603eac4f377c5e45f2044d4ebf9eecee9381c67b99290ef892`.
- 15 tablo bağımsız restore kanıtı: `92a0cd23674f31260ed90a3b86031b266728b09d5e7d996757a84e542f3437b2`.

İki liste/kural ayarları, dokuz olay, özel dosyalar, 15 tablo şeması/statik
veri ve middleware/PG korundu; dört servis sağlıklı/restart0. 13 SSR/33
statik/iki yönlendirme/18 anonim 401, 318 kaynak/bağımlılık dosyası ve 111
dağıtım kabulü geçti. İmaj gereksinimi 11.402.091 bayttı; eski imaj silinmedi.
İlk hazırlık örneğinde dokuz hesap, 1.464 üst periyot tanığı, kuyruk 213 vardı;
bu başlangıç örneği tam liste kapasitesi değildir. Yayın sonrası piyasa
hazırlığı, beşli önizleme/normal alarm ve kaynak ölçümleri aşağıda ayrılır.

## İkinci kaynakta beşli canlı kabul

**09:07:08–09:08:55 UTC** THYAO/BTCUSDT × beş varsayılan gösterge önizlemesi
geçti (160 POST). Her gösterge için en az iki farklı hazır fiyat gözlemi ve
her gözlemde etkin TF satırlarının aynı kaynak/alınma zamanına bağlı olması
doğrulandı. Etkin TF sayıları 10/10/2/2/2; farklı hazır gözlem sayıları
THYAO'da 11/8/7/5/3, BTCUSDT'de 10/2/4/14/13 idi. Bu TradingView/Pine
derleyicisiyle sayısal eşitlik testi değildir. İki başarısız önceki deneme
yerel kanıtta kalır; yeni kabul onların sonucunu değiştirmez.

**09:09:32–09:09:40 UTC** iki üyeli geçici karma listede beş göstergenin
`active_count > 0` koşulları VE ile birleştirilerek normal intrabar motorunda
iki olay üretildi. THYAO ve BTCUSDT olaylarının teslim durumu `not_requested`,
teslim denemesi 0; Telegram/emir çağrısı yok. Bu seçilen basit beşli koşulun
kalıcı olay yolunu doğrular; kullanıcının AL/SAT semantiği testi değildir.
Olay API'sindeki gözlem→kayıt süreleri 17,116 ve 11,420 ms'dir; kaynak fiyat
zamanı olayda tutulmadığından bunlar uçtan uca borsa gecikmesi sayılmaz.
Geçici kural/liste normal API ile kaldırıldı; iki kanıt olayı korundu.
Kullanıcının iki listesi ve etkin kural tanımları değişmedi. Toplam olay
bu anda dokuz gönderilmiş + iki bildirimsiz test olayıdır.

09:07:51–09:08:43 UTC'deki paralel hazırlık/önizleme örneklerinde derlenmiş
ayar sayısı 178→201, seçili SMI çıktıları hazır üye 82→112, henüz başlangıç
bekleyen üye 456→439 idi. Bütün native tanıklar hazır, ret 0; kuyruk 4–30,
taşma 0. API CPU %70,047–77,097, kullanılabilir RAM 247,590–268,113 MiB;
swap +5,391 MiB. Bu devam eden hazırlık ve önizleme yüküdür, kararlı kapasite
sonucu değildir. Kalıcı kaynak iddiası için test yükü bittikten sonraki
ölçümler ayrıca gerekir.

09:17:06–09:17:56 UTC'de önizleme talepleri sıfırdı. Derlenmiş hesaplar
382→402; seçili SMI çıktıları o anda hazır üyeler 178–202, son örnekte 188
idi. Son örneğin 443 bekleyen üyesi 229 başlangıç bekleyen, 154 eski fiyat,
59 canlı fiyat bekleyen ve bir çıktı/native tanık belirsizliğinden oluşuyordu.
Bütün 5.679 üst periyot tanığı hazır, ret ve retry beklemesi sıfırdı.
CPU %62,345–71,113, kullanılabilir RAM 231,336–256,902 MiB; kuyruk 3–11,
taşma 0. İlk hazırlık devam ettiği için bu da kararlı çalışma ölçümü değildir.

09:22:36–09:23:15 UTC'de üç sembol tek yeni bağlantıda, ayrı ve süreli bir
işlemde gözlendi. THYAO için 11 ham fiyat paketi ve 09:23:14'e ilerleyen
kaynak zamanı vardı. ALVES/BARMA için birer ham paket, sıfır fiyat değişimi
ve yeni bağlantıda da **06:55:31 UTC** kaynak zamanı geldi; kaydedilmiş üretim
gözlemiyle aynıydı. Bu dar bulgu bu iki sembolde eski zamanın yalnız Rapot
önbelleğinden kaynaklandığını desteklemez; işlem durması/likidite/lisans gibi
kesin bir neden ispatlamaz ve diğer eski sembollere genellenmez. Üç native
chart sağlıklı kapandı, yaratılan thread sayısı kapanışta sıfırdı. Kimlik ve
üretim dosyaları/abonelikleri değişmedi. Kaynak zamanı yerine alınma zamanı
yazılmadı; eski veri alarm için güncel kabul edilmedi.

Bu ayrı tanı sırasında kullanılabilir RAM 254,781→182,375 MiB oldu. Aynı
sırada başlatılan salt okunur gözlem 192 MiB başlangıç sınırında, sıfır örnekle
durdu; başarısız kanıt korunur. Tanı tamamlanmadan ek yük başlatılmadı.

09:25:22–09:25:36 UTC hacim tanısı aynı mevcut hesaptan THYAO/GARAN için
50'şer native günlük mum aldı. **100/100 ham dizide yalnız zaman+OHLC vardı;
hacim alanı yoktu.** Metadata `BISTMIXED` / `visible_plots_set=ohlc` döndü.
Eksik hacim sıfır sayılmadı; bu iki günlük örnekte hacim `unavailable` kaldı.
Bu sonuç bütün periyotların/üyelerin hacmi veya hesabın borsa veri yetkisi
hakkında genel hüküm değildir. Bir bağlantı/tam iki chart açılıp kapandı,
iki tamamlanmış istek ve sıfır hata; receiver/koruma thread'i kapanışta yoktu.
Minimum kullanılabilir RAM 204,215 MiB; üretim dosyası, kural veya kimlik
değişikliği yapılmadı. Önce dokuz yerel tanı testi geçti; sayısal sıfır ile
eksik hacim ve `has_no_volume`/OHLC-only metadata çelişkileri ayrı korunur.

TradingView'in [BIST MIXED açıklaması](https://www.tradingview.com/support/solutions/43000609137-what-is-the-bist-mixed-data-subscription/)
bu paketin gerçek zamanlı fiyat verdiğini fakat hacim içermediğini açıklar.
Bugünkü iki örneğin `BISTMIXED` cevabı bu açıklamayla tutarlıdır. Bu, kullanıcının
satın aldığı paketin adını veya oturumun neden bu veri yoluna yönlendiğini
kanıtlamaz; Premium planı ile borsa veri yetkisi birbirinin yerine varsayılmaz.

## Sürekli alarm hesabının CPU düzeltmesi

İlk hazırlıktan bağımsız yerel profilde 631 hazır SMI hesabı × 10 TF ve
5.048 fiyat güncellemesi kullanıldı. Her normal alarm okumasında aynı ayarlar
beş kez doğrulanıp JSON/hash üretiliyordu. Hazırlanmış koşul artık doğrulanmış,
değiştirilemez operand/config kimliklerini taşır; fiyat, hesap oturumu veya
hazırlık durumu önbelleğe alınmaz. Kullanıcı girdileri kopyalanır; kuralın
yerinde değişmesi eski planı kullanamaz. Epoch, ret, boşluk, eksik başlangıç,
tazelik ve aynı gözlemden çoklu gösterge değerlendirme kontrolleri korunur.

Aynı yerel normal alarm yolunda CPU/olay **783→241–300 µs** (%62–69 azalma),
yeniden config doğrulaması/hash çağrısı sıfır oldu. Provider/ağ, gerçek SQL
ve süreçler arası çekişme bu modele dahil değildir; üretim CPU/RSS veya
3.000 canlı kural kapasitesi sonucu değildir. Dört farklı fiyat gözleminde
beş gösterge callback'ten önce aynı gözlem kimliğiyle yayımlandı. Yeni 11
regresyon ve bağımsız kod incelemesi geçti. Yerel tam tur **2.335 başarılı,
bir atlama** ile 250,54 saniyede tamamlandı; 314 Python kaynağında Ruff geçti.
İlk lint kontrolünde yalnız yeni test dosyasının iki biçim satırı düzeltildi.
Üretim yayını üçüncü kaynak bölümünde, gerçek kaynak ölçümleri onun altında
ayrıca kaydedilir.

09:31:05–09:31:57 UTC'de ikinci üretim kaynağında **631/631 hesap derlenmiş**,
6.310 mantıksal TF kabul edilmiş, 631 sürekli günlük abonelik ve 5.679 üst
periyot tanığı hazırdı. Başlangıç/ret/retry/kapasite beklemesi sıfırdı. Son
anlık seçili çıktı kontrolü 310 hazır + 270 eski fiyat + 51 canlı fiyat
bekleyen üyeydi; 50 saniyelik pencerede 441 farklı üye en az bir kez hazır
görüldü. Bu, tüm fiyatların aynı anda taze olduğu veya gün boyu kesintisizlik
iddiası değildir. Normal mum kuyruğu sıfır; canlı kuyruk son örnekte 13,
taşma sıfır. Kısa başlangıç-sonrası CPU %45,855–55,692; kullanılabilir RAM
245,457–267,934 MiB, API cgroup belleği 264,348–281,297 MiB'dir. Bu CPU
düzeltmesinin üretim ölçümü değildir; düzeltme henüz yalnız yereldedir.

09:41:23–09:42:15 UTC'deki ikinci kısa başlangıç-sonrası pencerede 631
derlenmiş hesap ve 5.679 üst periyot tanığı korundu; başlangıç/ret/retry
beklemesi sıfırdı. Son anda 295 hazır, 293 eski fiyat, 43 canlı fiyat
bekleyen üye; pencere boyunca 442 farklı hazır üye görüldü. CPU
%39,775–53,713, kullanılabilir RAM 264,797–288,648 MiB, API cgroup belleği
228,672–233,387 MiB; kuyruk12/taşma0. Hâlâ ikinci kaynaktır; yerel CPU
düzeltmesinin üretim sonucu veya aynı piyasa yükünde karşılaştırması değildir.

İkinci kaynağın dokuz tamamlanmış penceresi çevrimdışı birleştirildi:
09:07:52–09:42:14 UTC arasındaki 54 örnekte **578/631 farklı üyenin seçili
SMI çıktısı en az bir kez hazır**, 587 üyenin normal fiyatı en az bir kez
30 saniye içinde taze, 588 üyenin normal/özel kaynak zamanı ilerlemişti.
Hiç hazır görülmeyen 53 üyenin son nedenleri 43 canlı fiyat bekleyen ve
10 eski fiyat idi. Pencerelerin toplam süresi yalnız 449,654 saniyedir;
aralardaki yaklaşık 27 dakika gözlenmiş sayılmaz. Dokuz üyenin daha erken
normal fiyatı taze olup özel çıktısı hiçbir örnekte hazır görülmemiştir;
bu, hazırlık sırası ile sonraki fiyat seyrekliğini ayırmadığından tek başına
hesaplama hatası kanıtı değildir. Son iki başlangıç-sonrası pencerede
taze normal fiyatı olup özel çıktısı bekleyen üye sıfırdı. Kaynak/üyelik/
tanım korumaları ve bağımsız aritmetik için sekiz yerel kontrol geçti.
Birleşik kanıt SHA:
`a15a1a4c9df99ac4e247ddb69cce5b3af2590b6b0b3ab2b7daa7378bc2a338db`.
Bu sonuç üçüncü kaynakla birleştirilmez ve gün boyu kesintisizlik değildir.

## 21 Ekim ekonomik takvim örnekleri

09:39:30–09:39:34 UTC tek yetkili `/calendar` GET'i, bugünün GB/US sorgusunda
30 satır/HTTP200 getirdi. API cache miss; bu sıradan yol ülke başına en fazla
bir upstream sorgusu başlatabilir. Dokuz yerel tanı testi geçti; API kimliği,
restart0 ve bütün alarm ayarları korundu. Minimum RAM 333,148 MiB idi.

| Etkinlik grubu | Resmî yayın planı | API kaynak saati | Kabul sınırı |
|---|---|---|---|
| İngiltere tüketici enflasyonu, altı satır | 21 Ekim 07:00 | 09:00 | Europe/London yerel saati yorumu altında eşleşme |
| İngiltere kamu net borçlanması, bir satır | 21 Ekim 07:00 | 09:00 | Aynı yerel saat varsayımı altında eşleşme |
| EIA haftalık petrol raporu, dokuz satır | Çarşamba 10:30 Eastern | 17:30 | Bugünkü IANA dönüşümüyle plan eşleşmesi |

[ONS enflasyon](https://www.ons.gov.uk/releases/consumerpriceinflationukseptember2026)
ve [kamu maliyesi](https://www.ons.gov.uk/releases/publicsectorfinancesukseptember2026)
sayfaları tarih/07:00'ı doğrular; incelenen sayfalarda açık yerel saat/ofset
bulunmadığı için Londra yorumu varsayım olarak kalır. [EIA resmî planı](https://www.eia.gov/petroleum/supply/weekly/schedule.php)
Eastern saatini açıkça belirtir; 21 Ekim istisna listesinde değildir.
America/New_York UTC−04 → İstanbul UTC+03 dönüşümü 17:30 verir. Gözlemde
EIA açıklaması henüz gelecektedir; gerçek yayın anı/gecikmesi doğrulanmadı.

Bu üç grup 16 satırdır, 16 bağımsız yayın değildir. Diğer 14 satır, tüm
ülkeler veya DST geçişleri doğrulanmış sayılmaz. `source_timezone=null` ve
kaynak saatini aynen gösterme politikası korunur. Genel saat dilimi kabulü
açık kalır. Receipt SHA:
`e2002de5b9667a49b0f5e7e01b25d58824652b266b1fc13e3518ce7f9220ee2f`;
yerel resmî karşılaştırma SHA:
`097905e6a3a1024a9aa992e10494e422658045a2ff28cf4cfdc01563cf479d38`.

## Üçüncü kaynak yayını — hazırlanan operand kimlikleri

`a5c14b75413e7f246bb579f28cf6dd4b61dd7a93`, **09:46:19 UTC / 12:46:19 TSİ**
API/frontend/Compose/current yayını tamamlandı. **09:46:35–09:47:07 UTC**
ayrı kabul geçti. Yerel 2.335 Python/bir atlama, 314 Python kaynağında Ruff,
aynı kaynakta frontend test/build dahil beş CI işi ve temiz imaj yayını geçti.
56 yerel yayın aracı kontrolü ve iki bağımsız incelemede engelleyici bulgu yok.

- CI: [39578264786](https://github.com/Rapto0/Rapot/actions/runs/39578264786).
- Temiz imaj: [39578294699](https://github.com/Rapto0/Rapot/actions/runs/39578294699).
- API: `ghcr.io/rapto0/rapot/backend@sha256:432d0e101970e6c557ba7b6cb9ade36698a1172f09ae589af4c59409fa51f9f2`.
- Frontend: `ghcr.io/rapto0/rapot/frontend@sha256:94537e3f6186d9b2044facf677b3fd6cbc2ac2c291e9d1f9d3882f73db43e050`.
- Yayın receipt: `18f981ce3c94022ec9f288d104bee4189cbff7a43378108493971bb90dc78e4c`.
- Ayrı kabul dosyası SHA: `08e1a04d876055e59bb5d60d8eb4e80594a03541d5d7553b59368e2be0f9bc00`.
- Yeni 1.342.660.608 bayt yedek SHA: `4a619b6e457ea6e894ba2b67f2d1457075945f58e8ba0f6d4cda35d9fc4d6f68`.
- 15 tablo bağımsız restore kanıtı: `21b57c366544eacaf12c62fcf4ac5b4f0b6b55c85ea80057e6439e93d9810457`.

Yalnız bu yayının geçici sunucu snapshot'ı doğrulamadan sonra kaldırıldı;
sunucu dışındaki snapshot/restore/kanıt korundu. 562 dosyalık kaynak arşivi
SHA `a2872a6e73ef4dec7c79861acf8060ba4f38ae95796f3a52fbcc17cffd77e63c`;
319 kaynak/bağımlılık dosyası ve 111 dağıtım temiz imajla doğrulandı. İmaj
gereksinimi 11.433.328 bayt, korumalı toplam boş alan gereksinimi
3.386.717.552 bayt; yayın sonunda 3.999.240.192 bayt boştu. İmaj silinmedi.
Kullanıcı listeleri/etkin kural, yedekteki dokuz gönderilmiş ve iki bildirimsiz
olay, özel dosyalar, middleware/PG ve 15 tablo şeması korundu. Yedek ile
yayın ön kontrolü arasında mevcut kullanıcı kuralından bir doğal olay daha
oluştu (ID12); yayın öncesinde toplam 12 olay vardı ve hepsi korundu. Dört servis
healthy/restart0; 13 SSR/33 statik/iki yönlendirme/18 anonim401 kabulü geçti.
Yayın sonrası canlı alarm ve kaynak ölçümleri bu kurulum kabulünden ayrıdır.

## Üçüncü kaynakta canlı kabul

**09:47:41–09:50:07 UTC** THYAO/BTCUSDT × beş varsayılan gösterge önizlemesi
geçti; 220 POST, etkin TF sayıları 10/10/2/2/2. Farklı hazır fiyat gözlemleri
THYAO'da 11/4/3/2/11, BTCUSDT'de 10/8/9/7/6 idi. Her gösterge içinde bütün
etkin periyotlar aynı fiyat gözlemini kullandı. Kullanıcı tanımları korundu;
bu yine Pine derleyicisiyle sayısal eşitlik değildir.

**09:54:07–09:56:08 UTC** ilk bildirimsiz normal alarm denemesi 120 saniye
içinde olay üretmedi (`InterruptedError`, süre sınırı). Geçici kural ve liste
normal API ile tamamen kaldırıldı; kullanıcı tanımları değişmedi. Başarılı
önizleme bitişi ile kuralın açılması arasında 240,407 saniye vardı. Kaynakta
önizleme talepleri 120 saniye sonra bırakıldığından test başladığında on
geçici ayarın tamamının süresi dolmuştu; sürekli etkin kullanıcı kuralının
ayarları bu varsayılan test ayarlarıyla aynı değildir. Kaynak, süresi dolan
işlerin hazırlığını bırakıp yeni alarmda yeniden kuyruğa alır. Son önizleme
koşulları ve alarm girdileri aynıydı. Deneme kaydı periyot bazında bekleme
durumunu içermediğinden bu zamanlama sıfır olayın tek kesin nedeni diye
sunulmaz; başarısız kanıt korunur. Yeniden önizleme ve hemen ardından normal
alarm kabulü ayrı bir niyetle yürütülür.

09:56:45–09:57:35 UTC ilk hazırlık penceresinde derlenmiş hesap 260→284,
önizleme talebi0; seçili çıktı hazır üye116→143, pencere boyunca189 farklı
üye idi. CPU %51,761–62,787, kullanılabilir RAM247,074–253,395 MiB,
API cgroup225,852–231,637 MiB; canlı kuyruk0–7/taşma0. Bu tamamlanmamış
başlangıç ölçümüdür; kararlı kapasite veya kalıcı kazanım değildir.

09:57:47–10:00:47 UTC ikinci önizleme denemesi 272 POST sonunda süre
sınırında kaldı. İki sembolde HTF RSI Score/RSI Snapshot hazırlık beklerken
ikişer TF kullanan diğer üç gösterge hazır sonuçlar verdi. Başarısız kayıt
korundu; normal alarm açılmadı. Daha sonra **10:13:25–10:14:17 UTC**
631/631 hesap derlenmiş, 5.679 tanık hazır, ret/retry0 ve geçmiş işi0 oldu.
Son anda 348 hazır +246 eski fiyat +37 canlı fiyat bekleyen üye vardı;
pencerede468 farklı üye hazır görüldü. Taze normal fiyatı olup özel çıktısı
bekleyen üye son örnekte0. CPU %31,441–44,853; API cgroup230,266–231,582 MiB,
kullanılabilir RAM206,570–220,691 MiB. Canlı kuyruk14/taşma0; bu kısa pencere
tam seans veya aynı piyasa yükünde CPU karşılaştırması değildir.

**10:14:55–10:16:37 UTC** başlangıç bittikten sonraki üçüncü önizleme geçti:
140 POST; THYAO farklı hazır gözlemler10/10/10/11/10, BTCUSDT2/2/3/3/2.
**10:16:57–10:17:05 UTC** hemen ardından normal karma liste alarmı iki olay
üretti. BTCUSDT ID15 ve THYAO ID16, `not_requested`/0 deneme; motor girdisi
alınma zamanı→olay kaydı29,969/8,667 ms. Bu borsa→bildirim gecikmesi değildir.
Geçici kural/liste silindi; bütün kullanıcı tanımları korundu. Önceki
başarısız denemenin kaydı değiştirilmedi. Kabul SHA:
`9a994ab0bd7a145b09a7eb669d2edb3f7d3c88cca1cecdd82d5148c17dfc6b2c`.

10:17:26–10:18:18 UTC'de oturum yenileme1/hata0,641 derlenmiş hesap
(631 kullanıcı +10 geçici önizleme),5690 tanık/ret0 ve geçmiş işi0 görüldü.
CPU %35,331–42,961; kullanılabilir RAM200,000–214,016 MiB, API
cgroup242,469–244,000 MiB, kuyruk7/taşma0. Önizleme talepleri hâlâ10 olduğu
için bu pencere yalnız kalıcı kullanıcı işi yükü değildir. Son örnekte330
üye hazır; bir üyede çıktı/native tanık belirsizliği vardı. Oturum yenilemesi
hesapları korudu; tüm fiyatlar aynı anda taze veya her üye kesintisiz hazır
iddiası yapılmaz.

10:28:37–10:29:28 UTC son üçüncü-kaynak penceresinde631 hesap/5679 tanık,
geçmiş işi0, önizleme0 ve taşma0 korundu. CPU %31,351–38,904, API
cgroup205,379–227,082 MiB, kullanılabilir RAM288,699–317,945 MiB idi.
Bu pencere geçici SQLite yedeğinin tam hedefli temizliğiyle çakıştı;
host CPU tepe değeri%98,075 ve swap+8,832 MiB görüldü. Bu yüzden host RAM
artışı veya bu pencere tek başına kalıcı kaynak kazanımı sayılmaz.

Üçüncü kaynağın dokuz penceresi/44 örneği ayrı birleştirildi:
09:49:35–10:29:27 UTC aralığında toplam350,168 saniyelik gözlem;
**582/631 farklı üyede seçili çıktı hazır**,583 üyede normal fiyat≤30 saniye
tazeydi. Hiç hazır görülmeyen49 üyenin son nedenleri30 canlı fiyat bekleyen,
19 eski fiyat; yalnız OZATD daha önce normal taze fiyat örneğine sahipti.
Normal kaynak zamanı627, özel native fiyat zamanı588 üyede ilerledi; bu iki
ayrı akış birbirinin canlı kabulü değildir. Yedi pencere başlangıç/önizleme
işi içerir; iki pencere631 hesap ve geçmiş işi0 koşulunu sağlar. İkinci
kaynağın örnekleri veya sonraki yayın bu toplama dahil edilmedi. Kanıt SHA:
`ef98401c700a05afcbd7848e0d980c7540bb3118631ddfd5a9bbf15004b4e0bc`.
Kesintili örnekler arasındaki süreler ve gün boyu kesintisizlik doğrulanmadı.

## Önizlemeyi yeniden açma maliyetinin düzeltmesi

İki zaman aşımı ayrı incelendi. Gerçek `process` ve batch provider yoluyla
yerel tekrar üretimde, önizleme süresi dolup ham önbellek başka sembollere
yer açınca eski on tarih özeti tek tek devamlılığı sıfırlıyordu. İlk TF'nin
geçersizleştirmesi aynı grubun kalan TF'lerini iptal ediyordu. Değişmemiş
on TF **11 hazırlık turu/100 chart isteği** sonrasında toparlandı; 0/8/24/32
saniye aralıklı tekrarların tümü sonunda düzeldi. Sonsuz döngü doğrulanmadı.
Üretimde THYAO'nun son kalan hazırlığı da daha sonra tamamlandı; bütün
üretim gecikmesinin yalnız bu neden olduğu ileri sürülmez.

Düzeltme native talebi önce sınırlı alt gruplarla alıp tamamını canonical
olarak doğrular; sonra tek yayın/hesap/nesil kontrolü altında tek geçmiş
revizyon kararı ve birlikte önbellek kaydı yapar. Gerçek revizyonda elde
kalan diğer gerekli TF'ler de yeniden alınır. Revizyon turu hesap yayımlamaz;
sonraki tur yeni native tanıklarla hazırlanır. 180 saniyelik tarih özeti
koruması, kapalı mum hash'leri ve gerçek revizyon kontrolü korunur.
Aynı yerel örnek **iki tur/10 isteğe** indi. Eksik ikinci grup, bozuk mum,
eşzamanlı kopma, hesap değişimi, durdurma ve kaldırılmış önizleme hiçbir
kısmi geçmiş/hesap yayımlamaz. Yeni11 regresyon ve150 farklı ilgili test,
Ruff ve bağımsız inceleme geçti. Son tam tur2.346 başarılı/bir atlama,
üç bağımlılık uyarısıyla215,35 saniyede tamamlandı;315 Python kaynağında
Ruff geçti. Üretim yayını ve canlı yeniden açılış kabulü ayrıca kaydedilir.

## Dördüncü kaynak yayını — birlikte geçmiş doğrulaması

`e28ef616a3155b09b62fa699513d948dc8d5d528`, **10:37:39 UTC / 13:37:39 TSİ**
API/frontend/Compose/current yayını tamamlandı. **10:37:49–10:38:19 UTC**
ayrı kabul geçti. Aynı kaynakta2.346 Python/bir atlama,315 kaynakta Ruff,
310 frontend testini içeren beş CI işi ve temiz imaj yayını başarılıdır.
56 yerel yayın kontrolü ve iki ayrı inceleme geçti;320 kaynak/bağımlılık
dosyası,111 dağıtım ve temiz imaj eşdeğerliği doğrulandı.

- CI: [39584723388](https://github.com/Rapto0/Rapot/actions/runs/39584723388).
- Temiz imaj: [39584742410](https://github.com/Rapto0/Rapot/actions/runs/39584742410).
- API: `ghcr.io/rapto0/rapot/backend@sha256:f6cdc77037788d459716789b4ff4cfeeb5f950db63824ddc9c54fc1ec0fb8c0a`.
- Frontend: `ghcr.io/rapto0/rapot/frontend@sha256:ad7abb180c366d560dfaa8340ac6f2eccadde713cfcf4791bdd07aa02490c920`.
- Yayın receipt: `710f644e2bf8ae51e7248e9934edecf4b214a4172ed08c7caae1b2e8f99a8b8e`.
- Ayrı kabul SHA: `1ba8b654824b1f544257836916dc6d80391427953cb98f8adf6ee3bbf3d72475`.
- Taze1.342.660.608 bayt yedek SHA: `af35910419dae3bc96b184ead9b9480453a7fa47648648bfe1008352aaf01d1f`.
- Bağımsız15 tablo restore kanıtı: `b3e148139b04262ded40bcaf3994c80e123105acdb223456d025e73579fff9e2`.
- 563 dosyalık kaynak arşivi SHA: `619374f6f875a9378cca46a68be57da3ae2164cbb863d16ac0e178bceb0b678d`.

10:23:51–10:24:07 UTC taze snapshot alındı, sunucu dışında bütün tablo/şema
ve aktif alarm durumuyla bağımsız restore edildi. Yalnız tam bu yayının
sunucu snapshot'ı doğrulamadan sonra temizlendi; sunucu dışı kopyalar korundu.
Yedekte 16 olay vardı: 12 gönderilmiş olay ve dört bildirimsiz test.
Gönderilmiş olaylar arasında önceki kabul testleri de bulunduğundan tümü
doğal kullanıcı sinyali olarak sınıflandırılmaz.
Son iki normal olay13/14, önceki kaynağın değişmeyen kullanıcı kuralına
aittir ve `sent`/bir deneme olarak korunur. Yayın/kabulde yeni olay0;
628 durum satırı, iki liste, etkin kural, bütün15 şema/12 statik tablo,
özel dosyalar ve middleware/PG korundu. Dört servis healthy/restart0,
13 SSR/33 statik/iki yönlendirme/18 anonim401 kabulü geçti.
İmaj ek gereksinimi11.468.876 bayt, korumalı toplam boş alan
gereksinimi3.386.753.100 bayt; yayın sonunda3.970.867.200 bayt boştu.
İmaj silinmedi. Bu kurulum kabulü canlı yeniden açılış/tam liste/kaynak
kabulünün yerine geçmez; sonraki ölçümler ayrı tutulur.

## Dördüncü kaynak canlı kabulü

İlk soğuk önizleme **10:38:34–10:41:34 UTC** aralığında 273 POST ile
180 saniye sınırına ulaştı. On sembol/gösterge birleşiminin tümünde en az
bir hazır canlı gözlem vardı; THYAO HTF RSI Score yalnız bir gözlemle
iki farklı gözlem ölçütünü sağlayamadı. Diğer dokuz birleşim geçti.
Başarısız kayıt korunur. **10:42:07–10:42:20 UTC** ayrı devam denemesi
13,042 saniye/20 POST ile on birleşimin tümünde iki farklı hazır gözlem
üretti. Etkin periyot sayıları 10/10/2/2/2 idi; her göstergenin etkin
periyotları kendi aynı fiyat gözlemiyle doğrulandı. Bu TradingView Pine
derleyicisiyle sayısal eşitlik kabulü değildir.

10:39:47–10:40:38 UTC ilk ölçüm başlangıç/önizleme yükü içeriyordu:
son örnekte 58 derlenmiş hesap, 5.690 tanık, on önizleme talebi ve
578 başlangıç bekleyen üye vardı. CPU %57,494–82,555, kullanılabilir RAM
243,250–271,996 MiB, API cgroup 207,395–210,141 MiB idi. Önizleme
bittikten sonra 120 saniyelik talep süresinin dolması ve ham önbelleğin
diğer semboller için kullanılması beklendi; yeniden açılış ayrı sınanır.

**10:47:13–10:48:04 UTC** salt okunur pencerede önizleme talebi sıfır,
5.679 üst periyot tanığı hazır, ret/retry beklemesi sıfırdı. Son derlenmiş
hesap 259, başlangıç bekleyen üye 372 idi. CPU %52,567–65,418,
kullanılabilir RAM 262,805–275,746 MiB, API cgroup 215,305–219,277 MiB;
taşma sıfır. Bu hâlâ ilk hazırlık ölçümüdür.

**10:48:19–10:51:06 UTC** süresi dolmuş önizlemeyi yeniden açma kabulü
250 POST ile geçti. THYAO farklı hazır gözlemleri 3/5/8/2/2, BTCUSDT
10/4/2/18/16 idi; on birleşimin hepsi en az iki farklı canlı gözlem verdi.
Başlangıç hazırlığıyla aynı zamandaki bu sonuç, yerel iki tur/10 istek
ölçümünün üretimde birebir süresi veya bütün listede anlık açılma garantisi
değildir. Kabul SHA:
`0ebf488b1d3cef206c8e543a7dcc407826eabfae0df69cb40adc31f8bd6f05c6`.

**10:51:20–10:51:26 UTC** hemen ardından normal motor üzerinden karma
izleme listesi alarmı geçti. Beş göstergenin `active_count > 0` koşulları
AND ile bağlıydı; intrabar, bildirim kapalı, iki üyeyle sınırlıydı.
THYAO ID17 ve BTCUSDT ID18 olayları `not_requested`/sıfır teslim denemesi
olarak kaydedildi. Motor girdisi alınma zamanından olay kaydına süre
sırasıyla **10,572 / 23,730 ms**; borsa→sunucu veya Telegram gecikmesi
değildir. Bu hazır hesap/çok koşullu motor yolunu doğrular; kullanıcının
AL/SAT koşulunun her hissede gerçekleşmesi testi değildir. Geçici kural
ve liste silindi; kullanıcı nesneleri değişmedi. Olay kanıtları korundu.
Kabul SHA:
`156436c845ecda7884bcb198b31694d32ef5e6e08cfa8fa2a4cccf1c53b5282e`.

**11:03:50 UTC** örneğinde son kaynakta **631/631 hesap derlenmiş** oldu;
11:04:01 örneği bunu korudu. 5.679 üst periyot tanığı hazır, başlangıç,
native ret, yeniden deneme ve kapasite beklemesi sıfırdı. Bu, yayından
yaklaşık **26 dakika sonra** ilk bütün-liste hazırlığıdır; yeniden başlatma
sonrası bütün göstergelerin hemen hazır olduğu iddia edilmez. Son örnekte
290 seçili çıktı hazır, 301 eski fiyat ve 40 yeni canlı fiyat bekleyen
üye vardı. Aynı anda 631 taze fiyat veya 631 gerçekleşmiş alarm değildir.

Son hazırlık bölümünde geçmiş bağlantısı ikinci kez açıldı ve başarısız
talep sayacı 40 oldu. Bu sayaç, başarısız gruptaki bütün TF taleplerini
sayar; 40 ayrı sağlayıcı hatası anlamına gelmez. Tek bir TF hatası da grubu
başarısız sayabilir. Timeout, bağlantı ve bozuk/ret yanıt ayrımı bu kayıtla
yapılamaz. Sonraki örneklerde sayaç 40'ta sabit, tamamlanan talep 6.591,
etkin geçmiş isteği ve retry sıfırdı; 631 üyenin geçmiş hazırlığı müdahalesiz tamamlandı.
Oluşturulan/silinen chart sayaçlarındaki fark, hata sonrası kapanan socket
nedeniyle tarihsel kalabilir; açık oturum sayısı olarak yorumlanmadı.

11:04:58–11:05:49 UTC geçmiş hazırlığı tamamlanmış, önizlemesiz pencerede 631 hesap,
5.679 tanık, önizleme sıfır ve geçmiş isteği sıfır korundu. CPU
%37,010–52,328; API cgroup 235,570–235,641 MiB, kullanılabilir sunucu RAM'i
199,723–216,254 MiB idi. Swap-out artışı sıfır; canlı kuyruk son örnekte
5, taşma sıfırdı. Son anda 303 çıktı hazır, 297 eski fiyat, 31 yeni fiyat
bekleyen vardı; normal fiyatı taze olduğu halde özel çıktısı bekleyen üye
sıfırdı. Bunlar kısa örneklerdir, tam seans veya kalıcı kapasite garantisi
değildir.

**11:07:13–11:08:05 UTC** ikinci pencerede erişim yenileme sayacı sıfırdan
bire geçti; ilk yenilenmiş örnek 11:07:34 UTC, hata/retry sıfırdı.
631 hesap ve 5.679 tanık, tamamlanan 6.591 geçmiş talebi ve sıfır etkin
geçmiş isteği korundu; yenileme bütün geçmişi yeniden yükletmedi.
CPU %37,070–48,889; API cgroup 236,219–244,910 MiB, kullanılabilir RAM
209,711–224,098 MiB idi. Swap kullanımı +5,465 MiB, swap-in/out artışı
242/1.791 sayfa; bu yüzden host üzerinde hiç bellek baskısı olmadığı
iddia edilmez. Son anda 279 çıktı hazır, 324 eski fiyat, 28 yeni fiyat
bekleyen; canlı kuyruk 4, taşma sıfırdı. Taze normal fiyatı olup özel
çıktısı bekleyen iki üye, ayrı akışların aynı anda okunmadığı da dikkate
alınarak açıkça korunur.

**11:08:34–11:09:26 UTC** son pencerede 631 hesap/5.679 tanık, önizleme ve
etkin geçmiş isteği sıfır, oturum yenileme bir/hata sıfır korundu.
CPU %34,913–56,526; API cgroup 242,262–244,996 MiB, kullanılabilir RAM
200,363–216,922 MiB idi. Swap +2,344 MiB, swap-in/out 202/669 sayfa.
Normal mum işi/kuyruğu 0/0, son canlı kuyruk 1 ve taşma sıfırdı.
Son anda 285 seçili çıktı hazır, 321 eski fiyat ve 25 yeni fiyat bekleyen
üye vardı. Üç üyede normal akışın fiyatı tazeyken özel çıktı bekliyordu.
Telegram teslim kuyruğu/hatası sıfır; `sent` sayacı 12'den 13'e çıktı,
bildirimsiz test olayı sayısı altıda kaldı. Son artış burada yalnız teslim
sayacıyla gözlenmiştir; bu pencere tek tek olay içeriğini sorgulamaz.
Kullanıcının tek etkin kuralı, iki listesi ve bütün tanım hashleri korundu.

## Son kaynağın birleşik kapsamı

Yalnız `e28ef616` kaynaklı, aynı kullanıcı tanımları ve aynı 631 üyelik
hash'iyle tamamlanmış **11 pencere/66 örnek** çevrimdışı birleştirildi.
10:39:48–11:09:24 UTC arasındaki pencerelerin kendi süreleri toplamı
**546,818 saniye**; aradaki gözlenmeyen süreler kabul kapsamına eklenmedi.
573 üyede en az bir seçili çıktı hazır, 584 üyede normal fiyatın hem kaynak
hem alınma yaşı ≤30 saniyeydi. Hazır çıktı görülmeyen 58 üyenin son durumları
33 eski fiyat ve 25 canlı fiyat bekleme; 11'inde daha önce normal taze fiyat
görülmüş olması özel native akışın aynı anda hazır olduğunu kanıtlamaz.
Normal kaynak zamanı 627, özel native kaynak zamanı 613 üyede ilerledi;
iki akış birbirinin yerine kullanılmadı.

Sekiz pencere başlangıç/önizleme/geçmiş işi içerir. Yalnız üç pencerede bütün
631 hesap derlenmiş, önizleme ve geçmiş işi sıfırdır. Bu üç pencerede
64,80198 CPU-saniye / 147,66879 ölçüm-saniye = **%43,8833 API CPU**;
4.000 işlenen canlı gözlem başına toplam 16,200495 ms API CPU düşer.
Bu oran HTTP, normal alarm ve diğer API işlerini de içerir; tek gösterge
hesabının maliyeti veya aynı trafikte neden-sonuç karşılaştırması değildir.
Kesikli örnekler uzun süreli bellek/CPU kararlılığı veya eksiksiz tick
yakalama garantisi vermez.

Son örnekte normal fiyatı taze/özel çıktısı bekleyen CIMSA, TKNKA ve YIGIT
için iki akışın kaynak zamanı aynıydı ve 30 saniye sınırına yakındı.
Ardışık API okumaları bu sınırı aşabileceğinden tek örnek yeni bir motor
arızası veya tam eşitlik kanıtı sayılmadı. Üç üye rapordan çıkarılmadı.
Birleşik kanıt SHA:
`45caf109d3d018e83aec24371fd63c6db2ea72f55512bfff93350d4b06e28346`.
