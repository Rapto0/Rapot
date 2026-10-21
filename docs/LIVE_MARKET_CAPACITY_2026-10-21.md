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
Üretim yayını ve gerçek kaynak ölçümü ayrıca kaydedilecek.

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
