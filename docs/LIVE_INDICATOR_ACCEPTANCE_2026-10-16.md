# 16 Ekim 2026 büyük izleme listesi canlı kabulü

Kullanıcının **“Çalışmana devam et”** talimatıyla manuel kabul sürdürüldü.
Otomatik takip/timer kurulmaz; kullanıcıya ait kural, liste ve bildirim ayarı
korunur. Bu kayıt kaynak düzeltmesini, izole sağlayıcı denemesini ve üretim
kabulünü ayrı tutar. **İlk düzeltme `2ea4ea31` ve kapasite koruması `e290604b`
sonrasında süreli native tanık düzeni `fe9e7e63` ile, ardından planlama ve ortak
geçmiş düzeltmesi `5472db4` ile yayımlandı; bağımsız yayın kabulleri geçti.
Mevcut 805 üyeli listenin tamamının hazır canlı hesabı henüz
doğrulanmadı.** Önceki denemelerin başarısız ve sınırlı sonuçları aşağıda korunur.

## Kullanıcının 631 hisse / 174 diğer kod ayrımı

Kullanıcı 12 Ekim tarihli Excel denetimini ve 631 kodluk metin dosyasını gönderdi;
hem “BIST Tümü” evreninin 631 pay olarak düzeltilmesini hem mevcut SMI listesinde
bu payların kalıp diğer 174 kodun ayrı, alarmsız listede saklanmasını açıkça
onayladı. Dosyalarda 805 benzersiz kod, 631 pay ve 174 ayrılan kod vardır. TXT
ile Excel'in pay sırası aynı; 631'lik küme, 14 Ekim'de saklanan resmî KAP pay
pazarları kümesiyle de aynı. Ayrılanların sınıfları 124 borçlanma aracı
ihraççısı, 12 alternatif kurum kodu, dört yapılandırılmış ürün, bir gayrimenkul
sertifikası, bir emtia sertifikası ihraççısı ve 32 pay kodu eşleşmesi olmayan
koddur. Bu kodların tümü “sahte” veya Borsa İstanbul'la ilgisiz değildir.

Ortak hisse evreni tarihli, özeti doğrulanan kaynak dosyasından gelir.
Şirket/ihraççı araştırması, kullanıcının açıkça eklediği diğer semboller ve
karma listeler bu hisse filtresine tabi değildir. Denetim tarihi 12 Ekim;
resmî saklanmış kaynakla ek karşılaştırma 14 Ekim'dir. Bugünkü canlı işlem,
fiyat erişimi veya gelecekte değişmeyecek üyelik iddiası yapılmaz. Kaynak
düzeltmesi ve sunucudaki liste aktarımının kabulü ayrı kaydedilir.

## Kripto yıl geçişinde bulunan gerçek native mum uyuşmazlığı

`5472db4` üzerinde izole, sınırlı ve salt okunur BTCUSDT tanısı
**15:12:38–15:13:04 UTC**'de on periyodu sorguladı. Sağlayıcı bütün serileri
tamamladı, protokol hatası yoktu; günlük ve aylık doğrulama geçti. 2–7D ile
2–3W olmak üzere sekiz periyot, mevcut sabit süre kontrolünde yıl sınırındaki
kısalmış native mumlar nedeniyle reddedildi. Örneğin 30 Aralık 2022 tarihli
3D mumdan sonra 1 Ocak 2023 gerçek native mumu geliyor; sabit üç gün eklemek
2 Ocak üretir. Bu nedenle reddi genel sağlayıcı gecikmesi saymak yanlıştı.
[TradingView'in resmî hizalama açıklaması](https://www.tradingview.com/charting-library-docs/latest/ui_elements/Resolution/#bar-alignment)
günlük periyotların 1 Ocak'ta, haftalıkların yılın ilk tam haftasında yeniden
başladığını ve yıl sonunda kısalabildiğini belirtir. Tanı kanıtı
`btc-native-history-5472-first.json`; fiyat, ham paket veya kimlik içermez.
Kaynak/container ve hesap revizyonu korundu. Bu tanı, canlı beşli alarm kabulü
değildir; BIST periyotları ayrıca kendi native tanıklarıyla korunur.

## Sonraki kaynak düzeltmesi: önizleme yenilemesi ve gereken periyotlar

`5472db4` üzerindeki 180 saniyelik BTCUSDT kabulü de **14:58:27–15:01:27 UTC**
arasında `NOT_READY_WITHIN_BOUND` ile bitti: 207 önizleme isteğinde beş
göstergenin her biri için kabul edilmiş hazır gözlem sıfırdı. Kaynak ve kullanıcı
tanımları korundu; API healthy/restart0 kaldı. Son durumda sertifika kuyruğu
sıfır olsa da geçmiş hesap başlangıcı bekliyordu. Bir Snapshot isteği geçmiş
alınamadığına dair genel hata döndürdü; bunun kesin sağlayıcı nedeni bu kanıttan
çıkarılamaz. Yeni alarm/Telegram oluşturulmadı.

Kaynak incelemesi iki somut hatayı ayırdı. Önizlemelerin değişmeyen üyeliği,
her okumanın yenilediği LRU sırasıyla karşılaştırılıyordu; bu nedenle aynı
beşli sorgu bütün planı yeniden kurup geçmiş imlecini sıfırlıyordu. İmza artık
sırasız üyeliği kullanır; gerçek yeni üyeler ve süre dolumu planı yeniler.
Ayrıca bir işin gereken periyotları, aynı semboldeki başka işlerin bütün
periyotlarının hazır olmasına bağlıydı. Hazırlık artık yalnız gereken alt
kümeyi ve zorunlu günlük tanığı denetler. Gerçek günlük revizyon, bağlantı,
ret, kabul edilmiş abonelik ve sertifika korumaları sürer. 176 ilgili test,
ardından tam **2.121 Python testi / bir atlama** ve bağımsız kaynak incelemesi
geçti; bu paragraf tek başına yayın kabulü değildir.

`5472db4` için **14:57:44–54 UTC** ayrı salt okunur CPU ölçümü hostta
%72,12, API cgroup'unda %64,32 gösterdi. Ardından önizleme çalışırken alınan
**14:58:46–14:59:36 UTC** altı örnekte beş CPU aralığı %100, RAM
224,395–245,207 MiB, son işlenen fiyatın kaynak zamanı farkı 0,645–1,635 saniye
idi. Kuyruk 0–34, taşma sıfır; sertifikalar 5.698 ve işlenebilir periyot
kuyruğu sıfır kaldı. Derlenmiş hesaplar 31→36 arttı; bu bütün listenin hazır
olduğu veya kalıcı CPU kazanımı anlamına gelmez. Kanıtlar
`steady-btc-first-btcusdt.json`, `steady-observation-second.json` ve
`cpu-attribution-steady-first.json` dosyalarındadır.

## Planlama ve ortak geçmiş düzeltmesinin üretim yayını

**`5472db486f4578a7a5d3b2454a3766d9b26cb83f`, 14:52:02 UTC / 17:52:02 TSİ**
API/frontend/Compose/current yayını tamamlandı. Bağımsız kabul
**14:52:50–14:53:24 UTC / 17:52:50–17:53:24 TSİ** arasında geçti.
Önceki `fe9e7e63` API/frontend/current kaynağı bu yayının başlangıcıdır;
middleware ve PostgreSQL aynı container/runtime kimliklerinde kaldı.
Üretime restore/migration veya silme uygulanmadı.

| Kanıt | Kimlik |
|---|---|
| API imajı | `ghcr.io/rapto0/rapot/backend@sha256:73375f30d1a930623c1be630d6f0d5e255787694a5efbf0c1bd1c6d54a807799` |
| Frontend imajı | `ghcr.io/rapto0/rapot/frontend@sha256:b6ac6ba2beda189d542c6d5d40626444a1b26d96fa6463dd3b242a17a740e77e` |
| Beş kaynak CI işi | [38917373981](https://github.com/Rapto0/Rapot/actions/runs/38917373981), tamamı başarılı |
| Temiz imaj yayını | [38917448230](https://github.com/Rapto0/Rapot/actions/runs/38917448230), başarılı; additive/delta yolları çalıştırılmadı |
| Yerel yayın receipt dosyası SHA-256 | `55644d540985a50b4ae4aa5189e7a91d68a2bff1385255d4052f3cb1975d55ab` |
| Bağımsız kabul dosyası SHA-256 | `a4713a29b13c1e1e9020617cd3148f5a537888a481fc4ee971c603e5f6cc13d1` |
| Taze SQLite yedeği | 1.342.660.608 bayt; `0a7a9c655fee1d379f73fc88c0e6101818715f3c8c016dc13684045255f3077f` |
| Bağımsız restore kanıtı SHA-256 | `7d5f8754d01be5f5a7ec36a584161d9e59799915776551580d4212d3c30c5125` |

`fe9e7e63` çalışırken **14:25:47–14:26:04 UTC**'de alınan taze snapshot,
sunucu dışında tam SQL restore ve bütün **15 tablo** için tipli satır/şema
parmak izleriyle doğrulandı. Snapshot ve restore'un etkin alarm izdüşümleri
de eşleşti. Yayın ve bağımsız kabul; **dört kural satırını (biri etkin),
tek 805 üyeli listeyi, 805 durum satırını, altı eski olayı, 12 statik tabloyu,
290 tanımsız kurtarma satırını ve özel dosyaları** korudu. Bu kabul aralığında
yeni olay sıfırdı. Kullanıcı kuralı, revizyonu ve bildirim tercihi değiştirilmedi;
doğal durum/teslim ilerlemesine izin veren koruma kullanıldı. Yeni TEST alarmı,
Telegram/AI üretimi veya emir bu yayın kabulünde istenmedi. Eski gözlem timer'ı
disabled/inactive kaldı; yeni otomatik takip kurulmadı.

Dört servis healthy/restart0; 13 SSR sayfası, 33 statik dosya, iki yönlendirme
ve 18 anonim401 kontrolü geçti. Katalog v2 / beş gösterge / 289 input, canlı
fiyat politikası ve geçersiz önizlemenin 422 yanıtı doğrulandı. Etkin işçiler
ve eşzamanlı manuel önizleme varken genel sayaçların sabitliği iddia edilmedi.
İmaj/arşivdeki seçilmiş **303 kaynak dosyası** tam ham SHA-256 ile eşleşti.
Yerel tam test turunda **2.114 Python/bir atlama**, ardından son fallback
düzeltmesinin **40 ilgili testi** geçti; 310 frontend, üretim derlemesi ve
standalone kabulü başarılıydı. Aynı commit'in beş CI işi ve temiz imaj yayını
geçti. Yayın araçlarının 46 çevrimdışı kontrolü de başarılıydı. Yerel tam
turdan sonraki regresyonu sayıya ekleyerek yeni bir tam test sonucu üretilmedi.

Bu kaynak, günlük verisi reddedilen sembolün üst periyotlarını kullanılabilir
bekleme kuyruğundan ayırır; abonelik planını gerçek değişiklik veya süre dolumu
olmadan baştan dolaşmaz. Geçmiş işçisi bir turda 64 ertelenmiş + 64 eksik/yenileme
işini inceler; fallback'ten seçilen işi kuyruktan da tüketir. Aynı sembol/periyot
için en büyük geçmiş talebi ham önbellekten bağımsız saklanır; ilk genişlemede
yeniden hazırlık ve gerçek OHLC/zaman/revizyon korumaları sürer.

Bağımsız kabulün başlangıç örneğinde **8.051 mantıksal TF talebi/kabulü** vardı:
kullanıcı kuralının 8.050 TF'sine manuel önizleme bir periyot eklemişti. Dört
native bağlantı, 805 sürekli chart, son örnekte 933 açık fiziksel chart,
124 geçici oturum, **1.680 uzun periyot sertifikası ve üç derlenmiş hesap**
görüldü. 173 günlük ret nedeniyle **1.557 uzun periyot kullanılamıyor** olarak
ayrıldı; işlenebilir bekleyen uzun periyot sayısı 4.009'du. Kullanıcı kuralının
803 üyesi bekleyen/eskiydi; işçi kuyruk örnekleri 445–469, genel çalışma ve
geçmiş hata bayrakları false idi. Ana fiyat akışında 805 abonelik/544 taze
sembol, normal mum işi/kuyruk 0/0 vardı. Bu sayaçlar bütün listenin hazır
hesapları veya her fiyatın gecikmesiz işlenmesi değildir.

**14:53:14–24 UTC** üç kısa örnekte kullanılabilir RAM **280,22 / 285,73 /
275,43 MiB**, iki CPU aralığı **%100 / %100**, son boş alan **4.400.545.792
bayt** idi. Yayın kabulü sürekli CPU kazanımını doğrulamaz. İlk THYAO
beşli önizlemesinin başarısız sonucu ve kısa canlı gözlem aşağıdadır;
diğer canlı/CPU/alarm doğrulamaları bu bölümde tamamlanmış sayılmaz. Kanıtlar
`runtime-data/20261016-native-steady-deploy/deployment-receipt.json`,
`acceptance.json`, `github-evidence.json` ve `backup-verified.json` altındadır.

## `5472db4` sonrasındaki ilk canlı gözlem ve önizlemeler

**14:53:24–14:54:14 UTC / 17:53:24–17:54:14 TSİ** arasındaki altı salt
okunur örnekte mevcut tek etkin kuralın tanımı/revizyonu ve 805 üyeli liste
korundu. Kullanıcı kuralının 8.050 TF talebine önizlemenin ek periyoduyla
toplam 8.051 mantıksal talep kabul edilmişti; dört bağlantı açık kaldı.

| Ölçüm | Altı örnekteki sonuç |
|---|---|
| Kullanılabilir RAM | 240,680–277,367 MiB |
| CPU | Ölçülebilen beş aralığın tamamı %100 |
| Uzun periyot sertifikası | 2.015 → 3.173 |
| İşlenebilir bekleyen uzun periyot | 3.674 → 2.516 |
| Günlük ret nedeniyle engellenen uzun periyot / doğrudan uzun periyot reddi | 1.557 / 0; bütün örneklerde sabit |
| Açık fiziksel chart | 917–933 |
| Derlenmiş hesap | 5 → 9; 50 → 90 hesap satırı |
| Bekleyen/eski kural üyesi | 800–802 / 805 |
| İşçi kuyruğu | 213–400 |
| İşlenen fiyat olayı | 4.495 → 7.195 |
| Son işlenen kaynak zamanından hesaplanan gecikme | 3,1468–6,0342 saniye |

Son satır saniye çözünürlüklü kaynak zamanı ile işleme zamanı farkıdır;
Telegram'a uçtan uca teslim gecikmesi veya bütün sembollerin gecikme dağılımı
değildir. Kuyruk taşması sıfır, native hata kodları boş, geçmiş/hesap/bağlantı
işçilerinin üçü de canlıydı; genel çalışma ve geçmiş hata bayrakları false idi.
`live_rejected=240` bütün örneklerde sabit kaldı; bu sayaç sıfır değildi.
Normal mum işi/kuyruk 0/0, Telegram gönderilmiş/bekleyen/başarısız sayıları
6/0/0 olarak kaldı. Sertifikaların ilerlemesi, listenin hazır canlı hesaplara
ulaştığını göstermedi; **en az 800 üye bekleyen/eskiydi ve
CPU kazancı bu örnekte doğrulanmadı.**

THYAO için beş gösterge önizlemesi **14:53:03–14:56:04 UTC /
17:53:03–17:56:04 TSİ** arasında 180 saniyelik gözlem sınırıyla çalıştı.
**160 önizleme isteği ve 32 aşama sonunda `NOT_READY_WITHIN_BOUND`** döndü;
beş göstergenin her biri için kabul edilen farklı hazır gözlem sayısı **0**
idi. Kaydedilen yanıtların beşi `waiting`, 154'ü `unknown` durumundaydı;
`unknown` açıklaması native periyotların güncel günlük mumla doğrulanmasının
beklendiğini belirtiyordu. Durum yanıtı olan 31 aşamada bağlantı ve üç işçi
canlıydı, yeni kuyruk taşması yoktu. Son aşama kısmiydi; eksik durum yanıtı
ayrı bağlantı/işçi arızası sayılmadı. Son kontrolde kaynak `5472db4`, API
healthy/restart0 ve kullanıcı tanımı korunmuştu. Yalnız süreli önizlemeler
açıldı; alarm/liste/Telegram/emir değişikliği yapılmadı. Bu sonuç beşli canlı
kabulün **geçmediğini** gösterir; bekleyen doğrulamanın nedeni ayrıca incelenir.

BTCUSDT için eski kabul aracının **14:54:40–14:54:50 UTC** aralığındaki kısa
çağrısı yalnız hazırlık talebi açtı; iki aşamalı kayıt `TimeoutError` ile
`incomplete` bitti. Bu yaklaşık on saniyelik çağrı kripto kabulü değildir;
son koruma kontrollerinin tamamlandığı da iddia edilmez. Alarm/liste/Telegram/
emir mutasyonu istenmedi. Daha uzun BTC kabulü ve yeni CPU ayrıştırması ayrı
çalışmalardır; sonuçları bu kayda henüz eklenmemiştir.

Kanıtlar `runtime-data/20261016-native-steady-acceptance/` altındaki
`steady-observation-first.json` (SHA-256 `233ad027c42b374c1ff34e5a35cf8aae56ba6601d33c68886a595affa778c246`)
ve `steady-thyao-first-thyao.json` (`455f7e488f8f5ce4e9bc02ad83950b7df81770681b0dff00de77c5fa88f91a93`)
ile `runtime-data/20261016-native-lease-acceptance/steady-crypto-warm-btcusdt.json`
(`bbd2d208babf9af49cf2b2327bf36c5275ff46292a5b16bd5c4d9f0a70717908`)
dosyalarıdır. Tam seans, tam 805 üye veya 3.000 canlı alarm kabulü yapılmış
sayılmaz; otomatik takip kurulmadı.

## Süreli native tanık düzeninin üretim yayını

**`fe9e7e632f6a3aee280c3f3c5b68c2b01a3620cc`, 14:13:07 UTC / 17:13:07 TSİ**
API/frontend/Compose/current yayını tamamlandı. Bağımsız kabul
**14:13:17–14:13:45 UTC** arasında geçti. Önceki API/current `e290604b` ve
frontend `2ea4ea31` bu yayının doğrulanmış başlangıçlarıdır; middleware ve
PostgreSQL aynı container/runtime kimliğinde kaldı. Main-init çalıştırılmadı;
üretim veritabanına restore/migration veya silme uygulanmadı.

| Kanıt | Kimlik |
|---|---|
| API imajı | `ghcr.io/rapto0/rapot/backend@sha256:414e5dd937f6d152c0ef5a7fe761ea264a80a708a9396f7916777373eb66d2fc` |
| Frontend imajı | `ghcr.io/rapto0/rapot/frontend@sha256:1a2215479f346ac7abd2f9e44bfe670a6fa5f392fe718033dfd90936d227aa29` |
| Beş kaynak CI işi | [38912184633](https://github.com/Rapto0/Rapot/actions/runs/38912184633), tamamı başarılı |
| Temiz imaj yayını | [38912466333](https://github.com/Rapto0/Rapot/actions/runs/38912466333), başarılı; additive/delta yolları çalıştırılmadı |
| Yayın receipt SHA-256 | `9fb3f7e46faf4ce4ce5b1994a2b71f2794ad7783074b760c1c701edfb1c3db1e` |
| Bağımsız kabul SHA-256 | `bbd0316c6f37c669c93a98b8a04fcdabdc26ca30320fbe592ba2c3c287067fcd` |
| Taze SQLite yedeği | 1.342.660.608 bayt; `090d6d0fac6e5ee59c27a27b5137c8b225fef083fd2812433985ec395980094e` |
| Bağımsız restore kanıtı SHA-256 | `1333dceb5be9d2efe10020673abb6b92ee6a39ffa6113c523783e5adbe5f3f57` |

13:53:27 UTC'de tamamlanan taze `e290604b` kaynaklı SQLite snapshot'ı,
sunucu dışında tam bağımsız restore ve bütün tablo parmak izleriyle doğrulandı.
Etkin yazıcı sürerken sabit salt okunur transaction kullanıldı. Snapshot ve
restore'un etkin alarm durum izdüşümleri de eşleşti. Yayın ve ayrı kabulde
**15 tablo şeması, 12 statik tablo, kullanıcının etkin kural tanımı/revizyonu,
805 üyeli listesi, 805 durum satırı ve altı eski olay** korundu; bu kısa kabul
aralığında yeni olay sıfırdı. Tanımsız 290 kurtarma satırı ve özel dosyalar
korundu. Araçlar doğal alarm/teslim ilerlemesine izin verir, kullanıcı kuralını
durdurmaz veya değiştirmez. Ayrı test alarmı/Telegram/AI/emir üretilmedi;
eski gözlem timer'ı disabled/inactive kaldı.

Dört servis healthy/restart0; 13 SSR sayfası, 33 statik dosya, iki yönlendirme
ve 18 anonim401 yanıtı geçti. Yönetici katalog v2 / beş gösterge / 289 input,
canlı fiyat politikası ve geçersiz önizlemenin 422 cevabı doğrulandı. Etkin
işçiler eşzamanlı çalıştığından genel sayaçların sabit kaldığı veya 422 sırasında
başka doğal iş oluşmadığı iddia edilmez. İmaj ve kaynak arşivinin seçilmiş
**301 dosyası** tam ham SHA-256 ile eşleşti. Yerel 2.095 Python/bir atlama,
310 frontend, üretim derlemesi ve standalone kabulü; aynı commit'in beş CI
işi ve temiz imaj yayını geçti. Yayın araçlarının 46 çevrimdışı kontrolü de
başarılıydı; eski yedek/review/receipt yeni kanıt yerine kullanılmadı.

Yayın sonrası ilk durum henüz hazırlık aşamasıdır: **8.050 mantıksal TF kabulü,
805 sürekli günlük chart, 128 geçici oturum, toplam 933 açık fiziksel chart**
ve dört bağlantı vardı. Uzun periyot sertifikası/derlenmiş hesap **0/0**, 805
üye bekleyen/eski, native ret 84; işçi kuyruk örnekleri 1.652–1.656 idi.
149 bellek sonucu hazır hesap kanıtı değildir; sağlayıcı çalışma hata bayrağı
mevcuttu. Ana fiyat akışı 805 abonelikte 524 taze sembol gösterdi; normal mum
işi/kuyruk 0/0'dı. Bunlar özel gösterge evreninin tamamının canlı hazır olduğunu
göstermez.

14:13:35–45 UTC üç kısa örnekte kullanılabilir RAM **300,33 / 274,38 / 279,22
MiB**, iki CPU aralığı **%100 / %100**, son boş alan **4.520.148.992 bayt** idi.
Bu yayın ve veri koruma kabulüdür; sürekli CPU/RAM kazancı, tam liste hazırlığı,
uçtan uca gecikme, tam seans veya 3.000 eşzamanlı canlı alarm kabulü değildir.
Sonraki manuel canlı gözlemler aşağıda ayrı kaydedilmiştir. Yayın kanıtları
`runtime-data/20261016-native-lease-deploy/deployment-receipt.json`,
`acceptance.json`, `github-evidence.json` ve `backup-verified.json` altındadır.

## `fe9e7e63` sonrasında mevcut listedeki canlı gözlemler

İki ayrı altı örnekli salt okunur gözlem **14:13:35–14:14:26 UTC /
17:13:35–17:14:26 TSİ** ve **14:16:09–14:16:59 UTC /
17:16:09–17:16:59 TSİ** aralıklarında tamamlandı. Aradaki süre sürekli
gözlenmiş sayılmaz. İki araç da mevcut tek etkin `smi_votes` izleme listesi
kuralını, revizyonunu, 805 üyeli listesini ve Telegram tercihini aynı hash'lerle
doğruladı. Kural `intrabar` / `once_per_bar` olarak kaldı. Teslim sayacı bütün
örneklerde **altı önceki gönderim**, sıfır bekleyen/başarısızdı; yeni TEST
alarmı veya Telegram mesajı oluşturulmadı. Üç özel gösterge işçisi canlıydı;
normal mum işi/kuyruk 0/0 kaldı.

| Gözlem | İlk altı örnek | İkinci altı örnek |
|---|---|---|
| Kullanıcı kapsamı | 805 üye / 8.050 mantıksal TF kabul edildi | Aynı 805 üye; önizlemeyle toplam 8.051 TF |
| Açık fiziksel chart | 933 → 869 | 869 → 805 |
| Uzun periyot sertifikası | 0 → 1.352 | 4.468 → 5.689 |
| Derlenmiş hesap | 0 → 3 | 12 → 18 |
| Bekleyen/eski kullanıcı hesabı | 805 → 804 | 798 → 796; ara örneklerde 799 |
| Canlı kuyruk | 1.636 → 0; en yüksek 1.636 | 6 → 0; en yüksek 96 |
| Son işlenen fiyatın kaynak yaşı | 24,77 → 2,09 sn; en yüksek 27,10 sn | 1,49 → 0,78 sn |
| Kullanılabilir RAM | 286,49–301,31 MiB | 252,98–264,83 MiB |
| Sunucu CPU aralıkları | Beş aralığın tamamı %100 | Beş aralığın tamamı %100 |

Dört native bağlantı örnekler boyunca açık, kuyruk taşması sıfırdı; yeni
protokol hata kodu kaydedilmedi. Canlı işlenen sayaç 267 → 2.986 ve ikinci
aralıkta 6.686 → 8.505 ilerledi. İlk hazırlıkta eski/geçersiz kabul edilen
fiyat sayacı 189 → 437 oldu; ikinci gözlemde artmadı. Bunlar bütün fiyatların
işlendiği veya sıfır gecikme kanıtı değildir. Derlenmiş hesap sayısı taze
sinyal veya hazır kullanıcı üyesi sayısı değildir.

İkinci gözlemdeki **8.051 TF ve 5.689 sertifika**, THYAO RSI Snapshot
önizlemesinin ek `7D` talebini içerir; kullanıcı kuralı 8.050 TF olarak kaldı.
Son örnekte 805 sürekli günlük chart ve sıfır geçici chart vardı. **173
günlük native aboneliği reddedildiği halde bunlara bağlı 1.557 uzun TF
`pending` sayılıyordu**; uzun periyot ret sayacı sıfır görünüyordu. Bu 1.557
iş, açılmayı bekleyen sağlıklı periyot değildir. Yayındaki kaynak bu yanlış
bekleyen sayısını yeniden planlama gerekçesi sayarak değişmeyen talebi tekrar
dolaşıyordu. Bu gözlemden sonra geliştirilen kaynak bu işleri günlük veri reddi
nedeniyle kullanılamayan grupta gösterir; sonraki `5472db4` yayını üstte ayrı
kayıtlıdır. Bu eski örneğin sayaçları yeni kaynak sonucu olarak sunulmaz.

### Resmî pay listesi, fiyat önbelleği ve alarm durum satırları

**14:17:08 UTC / 17:17:08 TSİ** kontrolü bir salt okunur SQLite transaction'ı
ve mevcut önbellek GET'leriyle tamamlandı; yeni sağlayıcı isteği veya abonelik
oluşturmadı. Resmî karşılaştırma, **14 Ekim 07:19:45 UTC'de kaydedilmiş KAP
pazar manifestindeki 631 paydır**; 16 Ekim üyeliği yeniden sorgulanmadı.
Bu 631 kodun tamamı kullanıcının 805 üyeli listesinde vardı.

| Kapsam | Önbelleğin `fresh` sınıfı | `stale` | Eksik fiyat | Kaynak ve alım yaşı en fazla 30 sn |
|---|---:|---:|---:|---:|
| Kayıtlı resmî 631 pay | 519 | 112 | 0 | 332 |
| Kullanıcının 805 üyesi | 520 | 112 | 173 | 332 |
| Resmî listede olmayan 174 üye | 1 | 0 | 173 | 0 |

`fresh`, standart fiyat önbelleğinin kendi tazelik sınıfıdır; özel gösterge
akışının 30 saniyelik koşuluyla aynı anlamda kullanılmaz. Tablodaki son sütun
kaynak ve alım zamanlarından ayrıca hesaplanmıştır. Seyrek işlem ile veri
teslim sorunu tek örnekten ayrıştırılamaz; 173 eksik fiyat da tek başına
geçersiz sembol kanıtı değildir. Kişi/sembol bazında güncel özel gösterge
hazırlığı ve native ret eşlemesi bu API alanlarından çıkarılamadı.

DB'de 805 durum satırı bulundu: 13 `ready`, 792 `unknown` kontrol noktası;
resmî pay alt kümesinde 13/618 idi. **Bunlar son anlamlı durum değişiminde
yazılan kayıtlardır; o andaki hazır alarm sayısı değildir.** `updated_at`
son fiyatı veya son değerlendirmeyi göstermez; DB kimlikleri mevcut özel
akış nesliyle eşlenemedi. Aynı anda genel sayaçta 19 derlenmiş hesap ve 793
bekleyen/eski kullanıcı hesabı vardı; periyot sertifikası yine hesap hazırlığı
yerine geçmez. İlk kapsam okuması Docker'ın nanosaniyeli `StartedAt` değerini
Python 3.10'da ayrıştıramayıp `container_timestamp_guard` ile, DB okumasına
başlamadan durdu. İlk kanıt korundu; parser gerçek Python 3.10.19 ve 3.12.8'de
on kontrolle doğrulandıktan sonra yeni dosyaya yazılan ikinci okuma geçti.

### CPU yükünün ayrıştırılması

**14:21:27–14:21:37 UTC / 17:21:27–17:21:37 TSİ**, 10,003 saniyelik iki
salt okunur procfs/cgroup örneği tek mantıksal CPU'da sunucu meşguliyetini
**%96,01**, hypervisor `steal` payını **%0,40**, API container yürütmesini
**%90,32** gösterdi. API cgroup'u 9,036 CPU saniyesi kullandı; bunun 8,654
saniyesi user, 0,381 saniyesi system idi. CPU throttling artışı sıfırdı.
Dolayısıyla bu kısa aralıktaki yüksek yük yalnız hypervisor beklemesine
bağlanamaz; API gerçek CPU tüketiyordu. Bu ölçüm önceki %100 aralıklarının
yeniden hesaplanması değildir ve tek başına hangi Python fonksiyonunun
maliyeti olduğunu belirlemez.

API cgroup belleği **232,79 → 232,87 MiB**, swap kullanımı **11,55 MiB**,
Python RSS son örneği **216,16 MiB** idi; kullanılabilir sunucu RAM'i
**236,42 → 236,73 MiB** ölçüldü. OOM/oom-kill sayaçları sıfırdı. Süreç ve
thread RSS değerleri ortak sayfaları içerebildiğinden toplanmadı. Tanı
uygulamaya bağlanmadı, profil enstrümantasyonu, kill veya restart yapmadı.

### Beş gösterge önizlemesinin kısmi ve başarısız sonuçları

| Sembol/deneme | UTC aralığı; TSİ için +3 saat | Sonuç |
|---|---|---|
| THYAO ilk | 14:14:53–14:15:53 | Hiçbir gösterge kabul koşullarında hazır olmadı; `TimeoutError` / `incomplete` |
| THYAO ikinci | 14:17:33–14:18:33 | RSI Snapshot ve RSI Votes hazır gözlemleri; sonra HTF RSI Score da hazır; SMI/RMI hazır olmadı; `TimeoutError` / `incomplete` |
| THYAO üçüncü | 14:19:03–14:20:03 | İlk üç turda HTF RSI Score, RSI Snapshot ve RSI Votes hazır; ardından geçmiş sıfırlamasıyla tümü `unknown`; `TimeoutError` / `incomplete` |
| BTCUSDT ilk | 14:21:08–14:22:08 | 79 önizleme isteğinde beş göstergenin hiçbiri hazır olmadı; `NOT_READY_WITHIN_BOUND` |

**Hiçbir tur beş göstergenin birlikte kabulünü geçmedi.** Üçüncü THYAO
denemesinde 14:19:16 UTC'de açık “Native geçmiş düzeltildi” nedeni görüldü;
devamlılık son eki 0 → 2, daha sonra 4 oldu. Yeni canlı fiyatın gelmesi
hesap başlangıcının hazır olduğu anlamına gelmedi. Üç THYAO denemesinin
süre sınırında kesilen son aşamaları ve tamamlanmamış kapanış kontrolleri
korundu. BTCUSDT denemesi sonrasında kaynak, healthy/restart0 ve kullanıcı
tanımı yeniden doğrulandı. Son kısmi/boş aşamalarda alınamayan durum cevabından
üretilen `false` kabul bayrakları gerçek bağlantı kopması veya işçi ölümü
kanıtı sayılmadı. Yalnız süreli önizleme talepleri açıldı; alarm, liste,
Telegram veya emir değişikliği yapılmadı.

Kaynak incelemesi, paylaşılan geçmişin **511/515/519 mumluk farklı taleplerinde**
eski kapalı satırlar aynı kalsa bile daha eski başlangıç eklenmesini revizyon
sayan bir koşul buldu. Ham önbellek silindikten sonra daha kısa talebe dönüş
de üç satırlık kayan pencere sınırını aşabiliyor. Bu davranış canlı sıfırlama
bulgusuyla uyumludur; kayıt tek başına bütün sağlayıcı satırlarının değişmezliğini
kanıtlamaz. Sonraki `5472db4` düzeltmesi gerekli en yüksek geçmiş talebini korur; mevcut
sayı/zaman/OHLC hash'i ve pencere devamlılığı korumalarını gevşetmez. İlk kez
daha uzun geçmiş gerekirse bir defa yeniden hazırlama olabilir; sonraki
küçük talepler ham önbellek silindiğinde bile pencereyi tekrar daraltmaz.
Aynı sembolün etkin ayarları başlangıçta ortak en büyük talebi kullanır.

Bu gözlem sırasında **değişiklik/zaman aşımı geldiğinde abonelik planlama,
64 işle sınırlı hazırlık kuyruğu taraması ve geçmiş talebi üst sınırını
koruma düzeltmeleri henüz adaydı; daha sonra `5472db4` ile yayımlandı.** Gerçek geçmiş
düzeltmesi, kopma, eski fiyat ve eksik native tanıkta `unknown` davranışı
korunur. Bu bölümde ölçülen `fe9e7e63` için tam 805 üye hazırlığı, beş gösterge canlı
kabulü ve kalıcı CPU iyileşmesi tamamlandı denemez.

Bu bölümün özel kanıtları `runtime-data/20261016-native-lease-acceptance/`
altındaki `native-lease-observation-first.json`, `native-lease-observation-second.json`,
`lease-preview-first-thyao.json`, `lease-preview-second-thyao.json`,
`lease-preview-third-thyao.json`, `lease-preview-first-crypto-btcusdt.json` ile
`runtime-data/20261016-live-market/` altındaki
`existing-watchlist-coverage-fe9e-first.json`, `existing-watchlist-coverage-fe9e-second.json`
ve `cpu-attribution-fe9e-first.json` dosyalarıdır. Başarısız kanıtlar silinmedi;
bu okumalar otomatik takip veya tam seans kaydı değildir.

## İlk yayın ve bulunan ikinci sınır

`2ea4ea31e68c07f6aec44f359546833d8d4665f8` API/frontend/Compose/current
yayını **08:24:52 UTC**, bağımsız kabul **08:25:20–08:25:48 UTC** tamamlandı.
15 tablo şeması, 12 statik tablo, kullanıcının etkin kuralı/revizyonu ve 805
üyeli listesi, üç eski olay korundu; yeni olay oluşmadı. Dört servis healthy/
restart0; middleware/PG ve özel dosyalar değişmedi. 13 SSR, 33 statik dosya,
iki yönlendirme, 18 anonim401, v2/5/289 katalog ve 422 doğrulandı. Tam kaynak
beş CI işi ve temiz imaj yayını geçti. Taze **1.342.660.608 bayt** yedek,
sunucu dışında bağımsız restore ve bütün tablo karşılaştırmasıyla doğrulandı.
İlk snapshot denemesi aktif yazıcılar nedeniyle ilerleyemedi; salt okunur
sabit transaction düzeltmesiyle ikinci deneme yaklaşık 13 saniyede tamamlandı.
İlk başarısızlık kanıtı saklandı. Kullanıcı kuralı durdurulmadı.

Yayın kabulünde CPU **%96,806/%98,597**, kullanılabilir RAM **293,55–303,28
MiB** idi; 372 native ret ve 679 bekleyen/eski sonuç vardı. Bu web/veri
koruma kabulü, canlı alarm kapasite kabulü değildir.

Tek sınırlı izole sağlayıcı tanısı **08:30:05 UTC** tamamlandı. İlk 500 seri
tamamlandı ve hata vermedi. Sonraki 16 seri eklenince `critical_error:
session_start_error — max charts per connection reached` geldi. Kesin 512
sınırı varsayılmıyor; güvenli yerel sınır **bağlantı başına doğrulanmış 500**
seçildi. RAM 278,6 → 196,9 MiB, süre 51,1 saniye; tanı bağlantısı kapatıldı.
Üretim dört bağlantıyla 8.050 fiziksel seri taşımaya devam edemez.

Salt okunur altı örnek **08:34:31–08:35:21 UTC** boyunca kullanıcı kuralı ve
liste hash'lerini değişmez doğruladı. Native abonelik sayısı 32→512→320→0
gibi tekrar başladı; derlenmiş hesap/sonuç sıfır, canlı işlenen sayaç 2.944'te
donuktu. Ana fiyat taze sayısı da sıfırdı. RAM 276,855–291,785 MiB, CPU yaklaşık
%38–51. Önceki gözlem aracının değişken sağlık alanlarını kural tanımına katması
yanlış `rule_changed_guard` üretmişti; açık statik alan listesiyle düzeltildi,
19 çevrimdışı kontrol geçti. Önceki kanıt silinmedi.

İkinci kaynak koruması her sembolün bütün TF'lerini tek bağlantıda atomik
planlar, bağlantı başına 500 fiziksel seriyi aşmaz ve çalışan sembolü başka
sokete taşımaz. Dört soket/10 TF örneğinde 200 sembol kabul edilir; diğer
605 sembol görünür kapasite durumuna geçer. Kullanıcının 805 üyeli tanımı
değişmez. Bu koruma tam kapsam çözümü değildir; uzun periyot native tanıklarını
paylaşan düzen ayrıca geliştirilecektir. 107 ilgili servis ve 26 akış testi
geçti. **`e290604b895c416285adae0c95152b25963d3613` yalnız API/Compose/current
yayını 08:54:16 UTC'de, bağımsız kabul 08:54:31–08:55:01 UTC'de geçti.**
Frontend `2ea4ea31`, middleware ve PostgreSQL korundu. Beş kaynak CI işi ve
temiz imaj yayını geçti; backend digest'i
`sha256:2905ec95017df78c4e32044b5258c090f38e91d89ef1b51fbaf43b029167b4b1`.
Taze 1.342.660.608 bayt SQLite yedeği sunucu dışında bağımsız restore edildi;
SHA-256 `ee225fba6e89111ad770dd8c364f5735123a69ea6350eab64da301131d4de3e5`.
15 tablo şeması, 12 statik tablo, kullanıcının kuralı/listesi ve olaylar korundu.
Dört servis healthy/restart0; 13 SSR, 33 statik, iki yönlendirme ve 18 anonim401
kabulü geçti. Ayrı kabul kaydı
`runtime-data/20261016-native-capacity-guard-deploy/acceptance.json`.

08:55:17–08:56:07 UTC altı kısa örneğin ilk beşinde 2.000 seri açık ve
4 bağlantı sağlıklıydı; sonuncusunda genel `provider_protocol_error` ile
yeniden bağlantı görüldü. Tek 500-seri bağlantının daha uzun izole denemesi
13:39:28–13:42:24 UTC'de yapıldı: 43,698 saniyede bütün seriler açıldı,
ardından 130,199 saniye sağlıklı kaldı; 815 fiyat, 632 mum, 11.285 `du` paketi
ve 16 alınmış/yanıtlanmış heartbeat görüldü. Sağlayıcı/callback hatası sıfırdı.
Bu sonuç üretimdeki genel protokol hatasının nedenini açıklamaz. Başlangıç
RAM'i 312,83 MiB, en düşük örnek 183,70 MiB'dı; süreç sınırlar içinde kapandı.

13:43:40 UTC ayrı salt okunur örnekte 805 üye tanımı korundu, 2.000 seri
açıktı; 49 derlenmiş hesap ve 162 önbellek sonucu vardı. Son geçmiş tamamlanması
11:05:20 UTC'deydi; bu zaman farkı ayrıca inceleniyor. Taze fiyat sayısı
506/805, normal mum işi/kuyruk 0/0, mevcut alarmın gönderilmiş olay sayısı
altı (önceki üçe ek üç normal olay), başarısız/bekleyen teslim sıfırdı.
Beş saatlik sınırlı günlük taramasında traceback görülmedi. Ara verilen
08:56–13:38 aralığı kesintisiz gözlenmiş sayılmaz; 805 üyeli tam canlı kabul yoktur.

## Süreli native tanık düzeninin izole kabulü

13:48:12–13:51:17 UTC'de aday kaynak yalnız ayrı tanı sürecinin belleğine
yüklendi; üretim dosyası/servisi değişmedi. Aynı sokette 50 resmî BIST sembolü
× 10 TF için önce 50 güncel native günlük mum doğrulandı. Sonra 450 uzun
periyot iki gerçek native mum ve aynı günlük nesille uygulama doğrulamasından
geçirildi. 450 geçici chart `remove_series`/`chart_delete_session` ile kapandı;
54,57 saniyede yalnız 50 sürekli günlük chart kaldı.

Bundan sonra **130,045 saniye** boyunca 50 üyenin 450 uzun periyot sertifikası
geçerli kaldı; 772 fiyat olayı (754 taze işlenen), 17 yanıtlanmış heartbeat,
sıfır protokol/callback/doğrulama/ret ve sıfır kuyruk taşması görüldü. Son
örnekte taze fiyatlı üye 32/50'ydi (ara örneklerde 25–38); sessiz semboller
gecikmesiz güncel kabul edilmez. Başlangıç RAM'i 288,77 MiB, en düşük örnek
194,79 MiB, son örnek 201,30 MiB'dı. Bütün tanı bağlantıları kapatıldı.

Akış kaynağı SHA-256 `353ed92421fb88651e36f7364d78276e7eb14dfb3a668f66a4c61c7e1585402e`,
tanık defteri SHA-256 `b373f14921a4b2603ea8cf7d357c8524f7c9122701cde726bfc1d5c06db9c409`.
Kanıt `runtime-data/20261016-live-market/lease-protocol-50x10-live.json`.
Bu kabul gerçek abonelik açma/kapatma ve native tanık yolunu doğrular;
805 üyeli uygulama, tam geçmiş hazırlığı, sayısal TradingView veya tam seans
kabulü değildir. Gün geçişinde kapalı hesap durumunu koruyan sonraki kaynak
düzeltmesi ayrı sentetik regresyonlarla doğrulanır; bu denemede gerçek gün
geçişi gözlenmedi.

Bu düzende güncel ama `ready=false` bir fiyat kaydının eksik hesap başlangıcını
altı saat gizleyebilmesi de düzeltildi. Hazırlık işçisi, gerçek native tanık
ve retry sınırlarını geçtikten sonra eksik derlenmiş durumu yeniden hazırlar.
Hazır sayaçları hesaplanmamış fiyatları hazır saymaz; üç işçinin gerçek thread
canlılığı ayrı raporlanır. Normal günlük rollover kapalı Wilder/EMA durumunu
ve geçmiş önbelleğini korur, karşılaştırma devamlılığını keser ve yeni native
HTF paketlerinden sonra artımlı ilerler. Gerçek revizyon yine geçmişi yeniler.
Mum içi başlangıç yalnız kompakt hesap durumunu kurar; 500 satırlık tam geçmiş
replay'i önizleme veya kapanış kuralı istendiğinde hazırlanır.

Son kaynakta **2.095 Python testi / bir atlama**, **310 frontend testi**,
frontend üretim derlemesi ve standalone HTTP/WS kabulü geçti. Gerçek pool
regresyonu normal gün geçişinde ek geçmiş sorgusu olmadan toparlanmayı,
geçersiz tanıkta sinyal verilmemesini ve ilk hazır gözlemde sahte eşik girişi
oluşmamasını doğrular. Bunlar üretimde tam evren kabulünün yerine geçmez.

## Gerçek kullanıcı alarmında bulunan sorun

07:55:28 UTC / 10:55:28 TSİ salt okunur tanı API'yi sağlıklı/restart0 ve
kullanılabilir RAM'i **319,03 MiB** gösterdi. Kullanıcıya ait **bir etkin
izleme listesi alarmı**, 805 sembol ve 8.050 native seri talebi vardı.
Native bağlantı, derlenmiş hesap ve işlenen canlı fiyat sayıları **0/0/0**;
805 sembol bekliyor/eski durumundaydı. Bellekteki 601 eski sonuç hazır canlı
gösterge değildir. Normal mum işi/kuyruk 0/0 kalırken bu ayrı özel gösterge
akışı çalışamıyordu. Önceki üç gönderilmiş olay korundu.

İzole gerçek sağlayıcı denemesinde aynı sokette 100 seri açıldı. 250 seriye
birden büyütme yaklaşık 0,30 saniyede **`protocol_error: max sessions rate
reached`** üretti. Bu bir oturum açma hızı hatasıdır; toplam seri sayısının
250 ile sınırlı olduğunu kanıtlamaz. Eski akış aynı alıcı kilidini binlerce
abonelik mesajını gönderirken tutuyordu. Bağlantının tekrar kapanması bütün
canlı başlangıçları sıfırlıyor; geçmiş işçisi de hazır olmayan sembollere
gereksiz başlangıç sorguları yapabiliyordu.

## İlk düzeltmenin kaynak davranışı (`2ea4ea31`)

- Bağlantı başına kontrol turunda en fazla **16 yeni native seri** açılır.
  Kalan işler sonraki turda devam eder ve bekleyen sayı durum çıktısındadır.
  Dört WS ve 8.192 yerel seri sınırı değişmez; bunlar sağlayıcı garantisi değildir.
  Alarm ekranı planlanan/istenen seriyi, açılan/bekleyen aboneliği ve canlı
  hesap başlangıcı hazır sayısını ayrı gösterir.
- Ağ gönderimleri alıcı kilidini tutmaz. Her sembolün native periyotları ve
  tek fiyat aboneliği aynı sıralı sokette kalır. `protocol_error` açıkça
  yakalanır; yalnız sabit hata kategorileri gösterilir, ham oturum bilgileri
  veya özel sağlayıcı payload'ı günlüklere yazılmaz.
- Çalışan mum içi hesapların geçmiş başlangıcı, sembolün taşıma kabulünü ve
  gereken bütün native mum tanıklarını bekler. Reddedilen/henüz açılmamış
  semboller hazır işleri engellemez. Geçmiş başarısızlığı 30 saniyeden
  başlayıp en fazla 1.800 saniyeye çıkan beklemeyle yinelenir; kopma kuyruğu
  bu beklemeyi atlamaz. Hazırlık kontrolü sembol indeksini kullanır; her işte
  bütün bağlantı üyelerini dolaşmaz. Kapanış/geçmiş replay sözleşmesi korunur.
- Açık native mumda yalnız `Close` değişince gereksiz mum callback'i
  üretilmez; gelen satır yine saklanır ve bütün fiyat olayları korunur.
  İlk veri, önceki mum düzeltmesi, O/H/L, metadata ve rollover olayları
  geçer. Günlük native mum değişince üst periyodun ilk gerçek yeni paketi
  yeniden tanık olur; önbellekteki satırdan sahte gün tanığı oluşturulmaz.

## İzole canlı protokol kanıtı

Üretim dosyaları değişmeden ayrı sınırlı tanı sürecinde, 50 sembol × 10 native
periyot = **500 seri** kademeli açıldı. İlk deneme yaklaşık 40 saniyede 500
`series_completed`, 197 fiyat ve 2.443 mum olayıyla sağlıklı bitti; sağlayıcı
ve callback hatası sıfırdı. Bu adayda gereksiz mum olaylarını azaltma henüz yoktu.

Mum olayı azaltmasını içeren sonraki adayın ayrı denemesi yaklaşık 40 saniyede
yine 500 seriyi tamamladı: **194 fiyat / 590 mum olayı**, 2.050 `du` paketi,
sıfır sağlayıcı/callback hatası ve sağlıklı kapanış. İkinci örneğin başlangıç
RAM'i 308,20 MiB'dı. Örnekler farklı piyasa anlarına ait olduğundan doğrudan
CPU veya aynı yükte yüzde performans kazancı iddiası yapılmaz. İkinci adayın
akış kaynağı SHA-256:
`4bbd0c88e5467139dec563e6957d81406db1cf00ee918bb81a9fd5b81af17bde`.

Yerel regresyonlar yavaş ağ gönderiminde alıcı thread'inin ilerlemesini, kademeli
kabul/iptali, güvenli hata kategorilerini, fiyatların korunmasını, son
kapanışın rollover'a taşınmasını, metadata ve yeni gün tanıklarını sınar.
Yerelde tam pakette **2.014 Python testi / bir atlama**, **307 frontend testi**
geçti. Son hazırlık indeksi, önizleme adaleti ve hata tanısı değişikliklerinin
ardından **97 ilgili Python testi**, arayüz metni sonrası **25 alarm ekranı
testi**, 290 Python kaynağında Ruff, frontend lint ve typecheck geçti. Son
kaynak CI'si ve yayın kabulü yukarıdaki ilk yayın kaydında ayrıca tutulur.

805 sembol × 10 TF hazırlık kontrolünün yerel ortalaması **171 ms → 4,57 ms**
oldu; bu üretim CPU ölçümü değildir. Önizlemeler başlangıç kuyruğunun arkasında
süreleri dolmadan, her dört geçmiş işinden birini alır; seçilmiş iş kuyrukta
yinelenmez. Kalan üç iş alarm hazırlığına ayrılır.

## Açık kalan kabul ve korunan sınırlar

Süreli native tanık düzeninin yedekli `fe9e7e63` yayını, 8.050 mantıksal TF'nin
yerel planlamaya kabulü ve sonraki `5472db4` planlama/geçmiş düzeltmesinin yayını
doğrulandı. Kullanıcının mevcut 805 üyeli alarmında bütün
hazır hesaplar, uçtan uca gecikme ve sürekli kaynak tüketimi henüz doğrulanmadı.
Önceki yayınlar yukarıda ayrı kayıtlıdır. 500 serilik protokol denemesi 3.000 canlı alarmı veya tam
seans kesintisizliğini kanıtlamaz. Yeni test alarmı/bildirim bu tanıda
oluşturulmadı; kullanıcının mevcut etkin Telegram tercihi değiştirilmedi.

[14 Ekim](LIVE_INDICATOR_ACCEPTANCE_2026-10-14.md) gerçek verisi üzerinde
beş gösterge × beş fiyat için 25/25 bağımsız formül eşleşmesi vardır; bu
TradingView derleyicisinden alınmış aynı an çıktısı değildir. Native mum
hacmi eksik/unknown kalır. Takvimde saat dilimi resmî kaynakta açık yalnız
iki olay ailesi eşleşti; tüm kaynak ve yaz/kış saati geçişleri doğrulanmadı.
Gerçek/testnet emir ve TradingView webhook kabulü bu çalışmanın kapsamında değildir.

Özel kanıtlar `runtime-data/20261016-live-market/` altında tutulur. Temel
kayıtlar `runtime-diagnostic-20261016.json`, `subscription-protocol-live.json`,
`subscription-paced-500-live.json` ve `subscription-paced-final-500-live.json`;
kimlik bilgileri ve veritabanları Git'e alınmaz.
