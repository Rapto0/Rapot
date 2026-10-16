# AGENTS.md — Rapot kod tabanı rehberi

**16 Ekim ek kullanıcı talimatı:** Gönderilen 12 Ekim denetimindeki 805 benzersiz
kodun yalnız 631'i KAP pay pazarlarıyla eşleşir. Kullanıcı hem sistemin “BIST
Tümü” evreninin 631 paya indirilmesini hem mevcut SMI alarmı listesindeki 174
diğer kodun ayrı, alarmsız bir listede korunmasını açıkça onayladı. 174 kod
“sahte” veya Borsa İstanbul'la ilgisiz sayılmaz; kurum/ihraççı, hisse dışı ürün
ve pay eşleşmesi olmayan kodlar içerir. Bu tarihli sınıflama canlı veri veya
gelecekte değişmeyecek üyelik kanıtı değildir. İşlemin gerçek yayın/liste
sonucu 16 Ekim kabul kaydına yazılır; bu talimat tamamlanma kanıtı değildir.

Kaynaklarla son karşılaştırma: **16 Ekim 2026 / büyük liste canlı akış düzeltmesi**. İş sırası, kullanıcı
yetkileri, kabul kanıtları ve ertelenen işler [devam planında](docs/RAPOT_DEVAM_PLANI.md)
tutulur. Eski backlog'lardaki boş kutular tek başına eksiklik kanıtı değildir.
Teknik rehberler [docs dizininde](docs/README.md) listelenir.

**16 Ekim yayın sonrası ek düzeltme üretimde:** **`5472db486f4578a7a5d3b2454a3766d9b26cb83f`,
14:52:02 UTC / 17:52:02 TSİ** API/frontend/Compose/current yayını tamamlandı;
**14:52:50–14:53:24 UTC** bağımsız kabul geçti. `fe9e7e63` sonrasında 805 üyede
8.050 mantıksal talep kabul edildi; 173 reddedilen günlük veri 1.557 üst periyodu
gereksiz bekleme/planlama döngüsünde tutuyordu. Yeni kaynak bunu ayırır ve
hazırlık kuyruğunu tur başına 64 + 64 kontrolle sınırlar. Beş göstergenin
511/515/519 mum talepleri için ortak en yüksek istek sayısı ham önbellekten
bağımsız korunur; gerçek geçmiş revizyonu koruması değişmez. Yerel tam turda
2.114 Python/bir atlama, son kuyruk düzeltmesinin 40 ilgili testi, 310 frontend,
üretim derlemesi/standalone; aynı kaynakta beş CI işi ve temiz imaj yayını geçti.
Taze 1.342.660.608 bayt yedek bütün 15 tabloyla bağımsız restore edildi;
restore kanıtı `7d5f8754…` ile sabitlendi. Dört kural satırı (biri etkin),
tek 805 üyeli liste, 805 durum ve altı eski olay korundu; yeni olay sıfırdı.
Dört servis healthy/restart0, middleware/PG ve özel dosyalar aynı; 13 SSR,
33 statik, iki yönlendirme, 18 anonim401 ve v2/5/289 katalog kabulü geçti.
Yayın sonrası kısa başlangıç örnekleri hâlâ %100 CPU gösterdi; beş gösterge
birlikte canlı kabulü, tam liste hazırlığı ve sürekli kaynak kazanımı bu
yayın kabulünden çıkarılamaz. Manuel önizleme/son gözlem ayrı yürür.
[16 Ekim yayın ve kabul kaydı](docs/LIVE_INDICATOR_ACCEPTANCE_2026-10-16.md).

**16 Ekim süreli native tanık yayını tamamlandı:** `fe9e7e63`, **14:13:07 UTC**
API/frontend/Compose/current'e yayımlandı; **14:13:17–14:13:45 UTC** bağımsız
kabul geçti. Günlük/gün içi mumlar sürekli bağlı, uzun D/W/M mumları aynı
native gün için doğrulanan geçici chart oturumlarıyla hazırlanır. 805 × 10 TF
talebi 805 sürekli + en fazla 128 geçici fiziksel chart olarak planlanır.
Normal günlük rollover kapalı hesap durumunu korur; yeni üst periyot tanıkları
gelmeden sinyal verilmez. Gerçek revizyon/kopma geçmişi yeniden hazırlatır.
2.095 Python/bir atlama, 310 frontend, beş kaynak CI işi ve temiz imaj yayını
geçti. Taze 1.342.660.608 bayt yedek bağımsız restore edildi; 15 tablo şeması,
12 statik tablo, mevcut 805 üyeli kural/liste, 805 durum ve altı olay korundu.
Dört servis healthy/restart0; middleware/PG, özel dosyalar ve kapalı takip aynı.
13 SSR/33 statik/iki yönlendirme/18 anonim401, v2/5/289 katalog ve 422 kabulü
geçti. İlk yayın örneğinde 8.050 mantıksal talep/933 açık chart/128 geçici
oturum vardı; sertifika ve derlenmiş hesap sıfır, 805 üye henüz bekliyordu.
İki kısa CPU aralığı %100'dü; bu yayın kabulü tam liste, tam seans veya
3.000 canlı alarm kapasitesi kanıtı değildir. Sonuçlar
[16 Ekim kaydındadır](docs/LIVE_INDICATOR_ACCEPTANCE_2026-10-16.md).

**16 Ekim önceki manuel tanı ve yayınlar:** Üretimde kullanıcıya ait bir etkin izleme listesi
alarmı, 805 sembol ve 8.050 native seri talebi var. 07:55:28 UTC tanısında
native bağlantı/derlenmiş hesap/işlenen fiyat sıfır; eski 601 sonuç hazır veri
değildir. İzole gerçek sağlayıcı tanısı büyük abonelik patlamasında
`protocol_error: max sessions rate reached` gösterdi. Kaynak artık bağlantı
başına kontrol turunda 16 seri açar; ağ gönderimi alıcı kilidini tutmaz.
Geçmiş başlangıcı gerçek native tanıkları bekler, hatalı istekler 30–1.800 saniye
arasında artan gecikmeyle yinelenir. Açık mumun yalnız Close değişimi gereksiz
mum olayını çoğaltmaz; fiyat olayları, kapanış/rollover, O/H/L, metadata ve yeni
gün tanıkları korunur. 500 serilik iki izole canlı deneme geçti; bu 8.050 seri
üretim kabulü değildir. **`2ea4ea31`, 08:24:52 UTC API/frontend/Compose/current
yayını; 08:25:20–48 UTC bağımsız kabul geçti.** Taze 1.342.660.608 bayt yedek
bağımsız restore edildi; 15 şema, 12 statik tablo, mevcut kural/liste ve üç olay
korundu. 500'den 516 seriye ayrı deneme `max charts per connection reached`
verdi. 08:34:31–08:35:21 UTC altı örnekte özel hesap sıfır ve yeniden bağlantı
döngüsü sürüyordu. Yeni kaynak koruması bağlantı başına 500, dört bağlantıda
2.000 fiziksel seriyle bütün sembolleri atomik kabul eder; fazla iş görünür
kapasite durumudur. **`e290604b`, 08:54:16 UTC yalnız API/Compose/current yayını;
08:54:31–08:55:01 UTC bağımsız kabul geçti.** Frontend `2ea4ea31` kaldı;
taze 1.342.660.608 bayt yedek restore edildi, mevcut kural/liste ve veriler korundu.
13:43 UTC örneğinde 2.000 seri açık, 49 hesap derlenmiş, 605 sembol kapasite
dışındadır; 805 üyeli tam canlı kapsam henüz çalışmıyor. Kullanıcının normal
alarmı toplam gönderilmiş olay sayısını üçten altıya çıkardı; yeni test alarmı
kurulmadı. Tek 500-seri bağlantı 13:39–13:42 UTC denemesinde 130 saniye sağlıklı
kaldı; üretimdeki genel protokol hatasının nedeni bu denemede tekrarlanmadı.
Bu aşamada uzun periyotların native tanıklarını paylaşan düzen kaynakta
geliştiriliyordu; sonraki `fe9e7e63` yayını yukarıda kayıtlıdır.
Kullanıcının kuralı/listesi/bildirim ayarı değiştirilmedi; yeni
otomatik takip yok. [16 Ekim kanıtı](docs/LIVE_INDICATOR_ACCEPTANCE_2026-10-16.md).

**14 Ekim canlı bağlantı yayını tamamlandı:** Kullanıcının “Piyasa şuan açık” mesajıyla
07:10:40 UTC'de manuel kontrol açıldı; otomatik takip yok. Beş özel gösterge
akışındaki gerçek `exceed limit of series in the session` hatası ayrı native
periyot chart session'larıyla düzeltilir; sembolün tek fiyat aboneliği ve bütün
periyotları aynı WS üzerinde kalır. 11 periyotlu izole canlı protokol kabulü
geçti. Dashboard BIST listesi mevcut sunucu fiyat akışını hesap/revizyon/epoch
kontrolüyle paylaşır. 1.995 Python/bir atlama, 307 frontend ve Ruff geçti.
**`e11d3d3d`, 07:49:26 UTC API/frontend/Compose/current yayını ve 07:50:01 UTC
bağımsız kabul geçti.** Beş kaynak CI işi ve temiz imaj yayını, 13 SSR/33 statik/
18 anonim401; 15 tablonun bütün satırları/şema, özel dosyalar ve middleware/PG
korundu. 1.342.660.608 bayt taze yedek bağımsız restore edildi. Gerçek THYAO
verisinde beş gösterge × beş quote = 25/25 bağımsız formül karşılaştırması
geçti; TradingView derleyicisiyle aynı an eşitliği değildir. Üretim özel alarm
canlı kabulü bu yayın kontrolüne dahil değildi. Sonuçlar
[14 Ekim kaydında](docs/LIVE_INDICATOR_ACCEPTANCE_2026-10-14.md) tutulur.
631 resmî payın tamamı abonelikte; 07:16 örneği 565 taze/66 eski/0 eksik,
tam seans veya gecikmesiz tüm evren kanıtı değildir. Mum hacmi hâlâ eksiktir.

**13 Ekim son talimat — canlı fiyat politikası:** Kullanıcı 30 saniyelik geçmiş
sorgusu yerine beş göstergenin aynı canlı fiyat anındaki bütün etkin zaman
dilimleriyle, en küçük periyot kapanışını beklemeden değerlendirilmesini istedi.
Kaynakta katalog v2, native mum/quote WebSocket, sabit kapalı Wilder/EMA
başlangıcından canlı hesap, sıralı fiyat değerlendirmesi ve sembole hedefli
alarm çağrısı uygulanır. Orijinal Pine dosyaları/geçmiş replay politikası
korunur; canlı sinyal politikası bilinçli olarak değişir. 2–6D/2–3W sınırları
TradingView native mumlarından gelir. Ayrıntılar [gösterge sözleşmesinde](docs/CUSTOM_PINE_INDICATORS.md).
**`4b739835`, 19:56:39 UTC API/frontend/Compose/current yayını ve 19:57:15 UTC
bağımsız kabul geçti.** 1.983 Python/bir atlama, 307 frontend, 290 Python
kaynağında Ruff, beş CI ve temiz imaj yayını geçti. Native rollover artımlıdır;
geçmiş yenilemesi canlı fiyat/range/koşul durumunu ezmez. Aynı ayarlar paylaşılır,
değişmeyen durum DB yazmaz. Yerel sınırlar 4 WS, 8.192 native seri/olay,
4.096 hesap, 2M seed hücresidir; fazla iş görünür kapasite durumuna geçer.
Beş gösterge × 631 sembolün tüm on TF model belleği 66,7 MiB; süreç RSS veya
üretim kapasitesi değildir. Dört servis sağlıklı/restart0, 15 tablonun bütün
satırları/şema, özel dosyalar ve middleware/PG korundu. 13 SSR/33 statik/18
anonim401, v2 / 5 / 289 katalog ve iş oluşturmayan 422 kabulü geçti. Taze
1.342.660.608 bayt yedek bağımsız restore edildi. Etkin kural yokken normal
mum işi/kuyruk 0/0; özel akış talep olmadığı için başlamadı. Kısa örnekler
279,30–298,22 MiB RAM, %19,361/%8,032 CPU'dur; tam seans/3.000 canlı yük kanıtı
değildir. Yeni alarm/Telegram/AI/emir veya otomatik takip yok. Canlı sayısal
TradingView karşılaştırması ve gecikme piyasa açık kabulüne bırakıldı.
Alttaki `b3200ed9` kabulü önceki 30 saniye/kapanış politikasına aittir.

**13 Ekim önceki gösterge yayını tamamlandı:** Kullanıcının beş Pine göstergesi (HTF RSI Score, RSI
Snapshot, RSI/SMI/RMI N OY) tüm 289 inputuyla sunucu hesaplayıcısı, grafik
önizlemesi ve kalıcı liste alarmlarına taşındı. Orijinal kaynaklar
`indicators/pine/` altında korunur. [Gösterge sözleşmesi](docs/CUSTOM_PINE_INDICATORS.md)
native periyot/seans, eksik veri, kaynak sinyali ve kapasite sınırlarını açıklar.
**`b3200ed9`, 17:45:35 UTC API/frontend/Compose/current yayını; 17:46:58 UTC
bağımsız kabul geçti.** 1.895 Python/bir atlama, 304 frontend, beş kaynak CI
işi ve temiz imaj yayını geçti. Dört servis sağlıklı; 15 tablonun bütün satırları,
şema, özel dosyalar ve middleware/PG korundu. Taze 1.342.660.608 bayt yedek
sunucu dışında bağımsız restore edildi. 13 SSR/33 statik/18 anonim401, yönetici
5/289 katalog ve iş oluşturmayan 422 önizleme doğrulandı. Etkin kural yokken
özel işçi talep edilmez; normal mum işi/kuyruk 0/0. 256 farklı etkin özel ayar
sınırı aynı kayıt transaction'ında korunur; aynı ayarlar paylaşılır. Native
geçmiş yenileme hedefi 30 saniyedir, tüm evrende saniyelik kabul değildir.
Canlı TradingView/piyasa ve yeni Telegram alarm kabulü kullanıcı tarafından
sonraki piyasa gününe bırakılmıştır; test için üretimde etkin kural kurulmaz.

**13 Ekim tamamlandı:** Eski COMBO/HUNTER sinyal/tarama geçmişi silindi ve
site gösterge/izleme listesi alarmları etrafında düzenlendi. `/signals` alarm
merkezine yönlenir; arşiv REST yolları kimlikli 410, signal WS 4410'dur. Eski
SQLite sinyal feed/polling ve tarama/read-model sayaçları kaldırılır; `/stats`
işlem metriklerini korur. Grafik COMBO/HUNTER hesaplayıcıları, diğer göstergeler,
manuel `/ai`, Borsapy taraması, kullanıcı listeleri ve alarmlar korunur. Ayrı
`scripts/retire_legacy_history.py` taze bağımsız yedek ve yazıcıların durdurulması
kanıtıyla tek transaction temizlik yapar; startup/migration otomatik silmez.
[Güncel kaynak ve üretim kabulü](docs/INDICATOR_ALARM_TRANSITION_2026-10-12.md):
`8b4e1bab` API/frontend/Compose/current yayını **14:46:08 UTC**, tek transaction
silme **15:01:12 UTC**, API sağlıklı yeniden açılma **15:01:29 UTC**, bağımsız
kabul **15:11:48 UTC**. 2.017.235 sinyal, 184 tarama, 26.393 otomatik analiz,
beş eski sayaç ve 161.866 kanıtlı kurtarma kalıntısı silindi; 290 tanımsız satır
korundu. 15 tablo şeması, yedi alarm tablosu, tek liste, üç olay ve özel dosyalar
korundu; middleware/PG aynı container'lardır. Dört servis healthy/restart0;
alarm motoru hatasız, sıfır etkin kuralda mum işi/kuyruk 0/0. 13 SSR/32 statik/
iki yönlendirme/17 anonim 401 ve yönetici 410/WS4410 kabulü geçti. 1.751 Python/
bir atlama, 273 frontend testi, son 51 temizlik testi, beş kaynak CI işi ve temiz
imaj yayını geçti. Taze 1.342.660.608 bayt yedek bağımsız restore ile doğrulandı.
İlk SSH sonuç taşıması takıldı; sunucudaki committed/healthy receipt'leri yeni
salt okunur bağlantıyla doğrulandı, işlem tekrarlanmadı. Ayrı kabul geçti.
Üç kısa örnek 318,52–321,49 MiB RAM ve %21,912/%2,405 CPU gösterdi;
tam seans/3.000 yük veya tam BIST kabulü değildir. Otomatik takip kapalı kalır.
Alttaki önceki bot yayınının geçmişi koruma ifadeleri o tarihsel adımı anlatır.

**Önceki 12 Ekim bot kaldırma adımı:** Otomatik COMBO/HUNTER Telegram taraması, Telegram
komutları ve bu taramaların otomatik AI/haber zinciri kaldırıldı. Site Borsapy
taraması, COMBO/HUNTER hesaplayıcıları, backtest, `/ai` ve sunucu alarmlarının
isteğe bağlı Telegram teslimi korunur. Eski bot **11:25:39 UTC'de durduruldu**;
**`a099dbb`, 12:05:39 UTC API/frontend/Compose/current yayını ve 12:15:02 UTC
bağımsız kabul geçti**, eski bot container'ı kaldırıldı. API içine gömülü bot,
Flask sağlık servisi ve `scripts.runtime bot` yolu artık yok. Dört sürekli servis
API/frontend/middleware/PostgreSQL; main-init ve middleware-migrate tek seferliktir.
`/analyze/{symbol}` yöneticiye 410 döner; site AI yolu `/market/analysis` kalır.
Tarama geçmişi salt okunur arşivdir; `scan_count` saklanan arşiv satırı sayısıdır.
Kaldırılan dosyaların saf testleri kaldırıldı, paylaşılan hesaplayıcı/veri/DB
sözleşmeleri korundu. Temiz backend imajı zorunludur; eski additive/delta imaj
korumaları atlanmaz. [Göç kaydı](docs/SERVER_ONLY_MIGRATION_2026-10-12.md).
1.709 Python/bir atlama, 309 frontend testi, beş CI işi ve temiz imaj yayını geçti.
15 tablo şeması, tek liste, üç eski olay ve diğer iki servis korundu. Taze
1.342.660.608 bayt yedek sunucu dışında bağımsız restore ile doğrulandı.
`main.env` içinden yalnız `RUN_EMBEDDED_BOT`/`BOT_LOCK_PATH` kaldırıldı; kalan
baytlar ve diğer özel dosyalar korundu. Yedi SSR/26 statik/altı anonim 401,
eski sağlık ve analiz yollarının 410 yanıtı doğrulandı. Alarm motoru hatasız,
Telegram yapılandırılmış; sıfır etkin kuralda mum işi/kuyruk 0/0. 805 abonelik,
488 taze sembol anlık örnektir; tam evren/tam seans veya 3.000 yük kanıtı değildir.
Üç kısa örnek 289,53–290,23 MiB kullanılabilir RAM, iki aralık %10,98/%22,33 CPU;
dört servis healthy/restart0, eski timer kapalı. Kabul aracındaki Windows/Linux
satır sonu ve AI yolunun GET/POST varsayımı düzeltildi; başarısız kayıtlar korundu.
Üretim imajları bu tanı sırasında değiştirilmedi. Yeni mesaj, AI üretimi veya emir yok.
Alttaki bot/beş servis kabul kayıtları gerçekleştiği tarihe ait tarihsel kanıtlardır.

12 Ekim kullanıcı RAM/CPU ve mum kuyruğuna kalıcı çözüm istedi; **3.000 etkin kural
zorunlu değil**, karma BIST/kripto listeleri ve liste başına birden çok alarm öncelikli.
Sıfır etkin alarm varken 805 planlı/720 bekleyen mum işi canlı GET ile görüldü.
Yeni kaynak mumları gerçek alarm ihtiyaçları ve son 120 saniyelik en fazla 128 grafik
talebiyle sınırlar; BIST fiyat evreni takibi sürer. Koşul/seri paylaşımı, küçük durum
batch'leri, Binance public oturum tekrar kullanımı ve ortak scanner birleştirme
iyileştirmeleri eklendi. Grafik sunucu listelerini kullanır; eski yerel listeler
yalnız elle kopyalanır. Yerel 3.000 kural ölçümü üretim kapasitesi kanıtı değildir.
**`6a84fa3c`, 10:47:19 UTC API/bot/frontend yayını ve 10:51:50 UTC bağımsız kabul
geçti.** Yerelde 1.804 Python/bir atlama, ardından son düzeltmenin 51 ilgili testi,
309 frontend testi; aynı kaynakta beş CI ve iki imaj yayın işi geçti. 15 tablo,
tek kişisel liste, üç önceki olay, diğer iki servis ve Compose/current `279aa9f`
korundu. Taze 1.342.013.440 bayt yedek sunucu dışında bağımsız restore ile doğrulandı.
Canlı GET'te alarm yokken mum işi/kuyruk 0/0 oldu; GARAN/BTCUSDT için iki grafik
talebi taze veri verdi ve süre sonunda işler/değer hücreleri tekrar sıfırlandı.
11:00 son örnekler **296,98–297,13 MiB kullanılabilir RAM, %19,83/%23,03 CPU**;
beş servis sağlıklı/restart0, eski timer kapalı. Bu yaklaşık 13 dakikalık kabul
tam seans veya tüm evrende 3.000 canlı teknik alarm kanıtı değildir. İlk bağımsız
kabul AssertionError verdi; tanılı tekrar ve değiştirilmemiş asıl araç geçti,
ilk hatanın kesin nedeni saptanmadı. [12 Ekim kaydı](docs/WATCHLIST_EFFICIENCY_2026-10-12.md)
kanıtları ve sınırları ayırır. Yeni otomatik takip/timer veya 3.000 üretim TEST
kuralı oluşturulmadı. Mevcut emir, hacim ve tazelik korumaları sürer.

8 Ekim kullanıcı **“Hazırım”** mesajıyla elle devamı başlattı; ilk saat kontrolü
13:13 TSİ olduğundan sabah bölümü gözlenmiş sayılmaz. Codex takibi `PAUSED` ve
eski gözlem timer'ı `disabled/inactive` kalır; ayrı otomatik takip istenmiyor.
İlk 131,6–189,7 MiB kullanılabilir RAM ve yüksek CPU/swap baskısı nedeniyle gözlem
ve 3.000 yük başlangıç sınırları sağlanmadı. Kullanılmayan request-local HTTP/TLS
kurulumunu kaldıran `f1d832bd`, **11:26:37 UTC'de yalnız API'ye yayımlandı**;
11:27:33 UTC bağımsız kabul geçti. Diğer dört servis, 15 tablo, üç gönderilmiş
test olayı ve tek kullanıcı listesi korundu. Yerelde 1.755 test/bir atlama,
kaynakla eşleşen beş CI ve iki imaj yayın işi geçti. Taze binary SQLite yedeği
sunucu dışında bağımsız restore ile doğrulandı; yalnız bu işin geçici sunucu
snapshot'ı temizlendi. Yayın sonrası üç örnek 278,21 / 236,64 / 239,64 MiB RAM,
iki aralık %79,67 / %75,82 CPU gösterdi; API yeniden başlatması sonrası kısa
örnekler sürekli kapasite kanıtı değildir. **11:39:26 UTC kontrolde 168,13 MiB
kullanılabilir RAM**, CPU başına load1m 2,3213 ölçüldü: hem 192 MiB gözlem hem
256 MiB yük başlangıç sınırı başarısız. **11:47:01–15 UTC son örnekler 146,43 /
146,27 / 159,65 MiB RAM ve %94,51 / %98,49 CPU** gösterdi; sürekli kapasite
kazancı doğrulanmadı. Yeni gözlem paketi sunucuya aktarılmadı, gözlem/yük başlatılmadı;
test kuralı veya lease oluşturulmadı. Bu tur başka gözlem/yük başlatma denemesi yapılmadı.
8 Ekim sonucu `NOT_STARTED_RESOURCE_GUARD`; ayrıntılar devam planı ve kabul belgesindedir.

7 Ekim ek doğrulamasında mevcut TradingView bağlantısı 200 THYAO/GARAN mumunu
`BISTMIXED` ve hacimsiz döndürdü; eksik hacim gerçek sıfır sayılmaz. Takvimin
çok günlük bloklarda yanlış tarih ataması düzeltildi; üç resmî saat örneği
uyuşsa da genel kaynak saat dilimi doğrulanmadı. 631 resmî KAP pay kodunun
tamamı 805 aday içinde var; bu canlı fiyat kapsamı değildir. API/frontend
`e449375`, 17:45 UTC'de yayımlandı; 17:48 UTC ayrı kabul geçti. 3.000 yük
ön kontrolü yetersiz kullanılabilir RAM'de durdu; test kuralı veya yük
zamanlayıcısı oluşturulmadı. 8 Ekim 09:30–18:15 TSİ için yalnız veri gözlemi
ayrı timer ile kuruldu; başlangıç/çalışma bellek sınırları 192/128 MiB.
**7 Ekim'deki kullanıcı talimatı:** 8 Ekim yaklaşık 10:00'da bilgisayarını açacak;
ayrı otomatik takip istemiyor. Codex takibi `PAUSED`; yalnız bu gözleme ait
timer 7 Ekim 18:38 UTC'de `disabled/inactive` doğrulandı. Yeni gözlem/çalışma
yalnız kullanıcının **“hazırım”**
mesajıyla elle devam eder. Önceki kurulum kabulü tarihsel kanıttır; 3.000
yükün bellek engeli geçerlidir.
Kurulum/sonuç durumu
[ayrı kabul belgesinde](docs/FULL_SESSION_ACCEPTANCE_2026-10-08.md) tutulur.
Yeni bellek tanıları yöneticiye özeldir; ayrılmış TEST kuralları her turda
süreli özel dosya izni gerektirir ve Telegram gönderemez. Normal kurallar
bu test iznine bağımlı değildir. Tam seans kabulünü hazırlanmış kodla karıştırma.

## Proje ve çalışma sınırları

Rapot; BIST/kripto taraması, COMBO/HUNTER sinyalleri, isteğe bağlı Gemini analizi,
Telegram bildirimleri ve Next.js dashboard içerir. TradingView webhook'larını
işleyen Binance Spot middleware'i ayrı uygulama/veritabanıdır. Dashboard'un ana
Trade kayıtları middleware emirleriyle aynı veri kümesi değildir.

İşleri **incele → düzelt → doğrula → belgeyi güncelle** sırasıyla ele al.
Commit/push/deploy kapsamı kullanıcının mevcut talimatlarından ve devam planından
okunur; bu dosya kendi başına üretim işlemi veya emir gönderme yetkisi vermez.
Kullanıcı borsa ile ilgili dış kabulü erteledi: gerçek TradingView alarm teslimi
ve testnet/gerçek emir testi açık kalır. Mevcut üretim DRY_RUN, trading/live kapalıdır.
Anahtar, parola, .env içeriği ve gerçek veritabanları rapora/Git'e alınmaz.

7 Ekim kullanıcı talimatıyla canlı fiyat/mum ve Rapot Telegram kabulü yapıldı:
GARAN fiyat, izleme listesi ve RSI/close çok koşullu teknik testleri normal
motor/kuyruk üzerinden teslim edildi; ilk iki mesaj kullanıcı tarafından da
doğrulandı. Geçici kurallar/liste kaldırıldı, üç olay korundu. Bu kabul TradingView
webhook veya emir testi değildir. Beş sembollü dar örneklem tam BIST kapsamını
kanıtlamaz. Doğrulanmayan BIST hacmi `unknown` olmalıdır; eksik hacimden sıfır
üretilip alarm tetiklenmez. [Canlı kabul kaydı](docs/LIVE_MARKET_ACCEPTANCE_2026-10-07.md)
gözlemleri, bulunan kilit/grafik/önbellek sorunlarını ve yayın durumunu ayırır.

## Mimari ve giriş noktaları

| Katman | Kaynak ve görev |
|---|---|
| Alarm motorları | `api/runtime/server_alarms.py`, `api/runtime/advanced_alarms.py`; API yaşam döngüsü |
| Hesaplama | `signals.py`, `config.py`, `strategy_inspector.py`, `data_loader.py` |
| Sinyal/tarama arşivi uyumluluğu | `application/scanner/signal_handlers.py`, `application/scanner/scan_history.py`; `domain/events/signal_domain_event.py`; otomatik bot girişi yok |
| Ana API | `api/main.py`, `api/routes/`, `api/auth.py`; port 8000 |
| Servis/repository | `application/services/` → `infrastructure/repositories/`; tarihsel sinyal kalıcılığı `infrastructure/persistence/` |
| Ana veri | `models.py`, `db_session.py`, `database.py`; SQLite ve ayrı fiyat önbelleği |
| Realtime | `api/runtime/realtime_bootstrap.py` provider yaşam döngüsü; `api/realtime.py` kimlikli piyasa WS/SSE; eski SQLite signal feed kaldırıldı |
| Sağlık | Ana API `/health`; özel alarm durumu `/advanced-alarms/status` |
| Middleware | `middleware/api/main.py` → `middleware/services/trading_service.py`; port 8001; ayrı PostgreSQL/Alembic |
| Frontend | `frontend/src/app/`, `frontend/src/components/`, `frontend/src/lib/api/client.ts`, `frontend/src/lib/hooks/`; port 3000 |
| Container girişleri | `scripts/runtime.py`: init-main-db, api, migrate-middleware, middleware |

Ana dashboard `/`; diğer sayfalar `/signals`, `/trades`, `/scanner`, `/health`,
`/settings`, `/chart`, `/research`, `/alarms`, `/ai`, `/calendar`, `/tradingview`, `/login`.
Ayarlar sayfası sunucu/tarayıcı ayarlarının kapsamını açıklar; tarayıcı tercihleri
ilgili ekranlardan düzenlenir. `/alarms` yöneticiye ait kalıcı sunucu kurallarını
yönetir; `/advanced-alarms` API'si 1.000'er fiyat/teknik/izleme listesi alarmı,
çok koşullu ve süresiz kurallar sunar. Ayrı süreç kilidiyle API motoru ve
kalıcı veri takibi tarayıcıdan bağımsız çalışır. Saniyelik tur hedefi, bütün
kural-sembol çarpımını aynı saniyede değerlendirme garantisi değildir; son tur,
veri tazeliği ve kapasite beklemeleri gösterilir. Dört `advanced_alarm_*` tablosu
ve ayrı sınırlı dakika önbelleği kullanılır. Önceki günlük motor `/alarms/legacy`
altındadır; `/alarms` eski API yolu korunur. Eski yerel kurallar
`/alarms/local` sayfası açıkken değerlendirilir ve otomatik taşınmaz.
[Sunucu alarm sözleşmesi](docs/SERVER_ALARMS.md) periyot, hesaplayıcı ve teslim
sınırlarını açıklar; keyfi Pine çalıştırma desteği değildir.
Grafik 26 çizim aracı ve 1m/5m periyot sunar. Çizimler sembol/periyot başına
tarayıcıda saklanır; sunucu alarmı veya emir oluşturmaz.
7 Ekim 15:58 UTC'de API/frontend `c74c1ad` üretime alındı; 15:59 UTC ayrı kabul
geçti. 16:31 UTC'de yalnız API `a835ece` oldu: yavaş herkese açık şirket işlemi
sorgusu hesap kilidini tutmaz; yönetici ve iki araştırma sınırı korunur.
Ardından 17:45 UTC'de API/frontend `e449375` oldu: hacim kalitesi, takvim tarih
parser'ı, özel bellek tanıları ve TEST lease koruması eklendi. Bot `876f3f3`,
middleware/Compose/current `279aa9f` korundu. Beş servis sağlıklı, 15 tablo ve
üç gönderilmiş test olayı korundu. Tam kaynak CI'nin beş işi ve 299 frontend
testi geçti; Sharp 0.35.5/rsvg 2.63.2/vips 8.18.7 native metadata'sı doğrulandı.
Doğal seyrek BIST
mumları doldurulmadan saklanır; yeni boşluk, geçmiş mum revizyonu ve kayıp
karşılaştırma girdisi alarm devamlılığını sıfırlar. Eski önbellek güncel veri
sayılmaz. 4 Ekim'deki 1.619 Python/291 frontend ve 15 tablo/servis/HTTPS kabulünü
7 Ekim dar canlı örneklem ve üç Rapot alarm kategorisinin Telegram kabulü izledi;
tam piyasa kapsamı/gecikmesi ve doğrulanmış hacim hâlâ açık.

`/research` borsapy 0.11.0 katalog/form/tablo/grafik, sanal portföy, replay ve
hesap bağlantılarını yöneticiye sunar. Kişisel dashboard HTTP verileri yöneticiye
özeldir ve `private, no-store` döner; WS ilk mesajla, SSE Bearer başlığıyla
kimlik doğrular. TradingView/EVDS/X kimlikleri sunucuda şifrelenir;
`research_workspaces` yalnız kullanıcı girdilerini tutar. `/chart`, dashboard
ve izleme listelerinde BIST kaynağı Borsapy/TradingView'dur. Günlük veri yükleyici ve
BIST alarmları için `BORSAPY_USE_FOR_BIST` varsayılan true'dur; false eski
sağlayıcıları açıkça seçer. Kimlik/sağlayıcı hatası sessiz kaynak değişimi yapmaz.
Ortak fiyat akışı en fazla 200 etkin sembol, istek başına 50 sembol taşır;
geçmiş metrik işi tek worker, 100 bekleyen iş ve 200 bellek kaydıyla sınırlıdır.
Kripto grafik/alarm ve Binance sembol kimliği korunur; BtcTurk ayrı araştırmadır.
Ekonomik takvim Borsapy/Doviz.com kullanır; TradingView/Finnhub anahtarı istemez.
Canlı piyasa kabulü ertelidir; bağlantı açık olması gecikmesiz fiyat kanıtı değildir.
[Entegrasyon sözleşmesi](docs/BORSAPY_INTEGRATION.md) kapsam ve sınırları açıklar.
4 Ekim 06:21 UTC'de `4b15335` API/frontend üretime alındı; 51 işlem/9 grup, özel GET'ler,
HTTPS/statik dosyalar ve ek araştırma tablosu doğrulandı. TradingView/EVDS/X
bağlantıları bu kabulde henüz tanımlı değildi. Bot/middleware/Compose/current
`279aa9f` korundu; o aşamada gerçek hesap ve piyasa kabulü erteliydi. İmaj/kanıt
kimlikleri ve tamamlanmış iki-imaj temizlik onayı devam planındadır.
Ardından 08:02:14 UTC'de `ab18dc4` API/bot/frontend'e yayımlandı; 08:02:47 UTC
ayrı salt okunur kabul erişim sınırlarını, WS kimliğini, SSR/statik dosyaları ve
11 tablonun değişmeyen şemasını doğruladı. API/bot `BORSAPY_USE_FOR_BIST=true`
ile aynı kaynak imajını kullanır; middleware/Compose/current `279aa9f` korundu.
Bu kabulde TradingView/EVDS/X bağlantıları tanımsızdı; boş alan 804.610.048 bayttı.
09:06 UTC'de `876f3f3` API/bot/frontend'e alındı: TradingView yerel dil
yönlendirmesinde oturumun kaybolmasını sınırlı bir adaptör düzeltir; başarısız
kaydetme/doğrulama sonrası arayüz kayıt durumunu yeniler. 09:08 UTC bağımsız
kabul ve mevcut yönetici ekranından doğrulama, TradingView oturumunun başarılı
olduğunu gösterdi. 1.421 Python ve 256 frontend testi geçti. Beş servis sağlıklı,
11 tablo şeması ve şifreli kimlik kaydı korundu; temizlik/migration yapılmadı.
Bu kabulde boş alan 696.680.448 bayt, sabit rezerv 528 MiB'dir. EVDS/X tanımsız;
canlı fiyat/mum, şirket işlemleri ve alarm/emir kabulü hâlâ ertelidir.

10:08:52 UTC'de yalnız frontend `57aed918` / `sha256:399ab9fa…` imajına geçti.
BIST ana grafik, gösterge panelleri ve araştırma/replay eksenleri ile crosshair
`Europe/Istanbul`, ana kripto grafiği UTC gösterir; kaynak zaman damgalarına ofset eklenmez.
API/bot `876f3f3` / `sha256:a6d0e72e…`, middleware/Compose/current `279aa9f` korundu.
1.487 Python ve 267 frontend testi, exact-source CI'nin beş işi ve iki yayın işi geçti;
üretimde dört SSR sayfası, 19 statik dosya ve üç anonim isteğin 401 yanıtı doğrulandı.
Bu kabulde boş alan 686.026.752 bayt, sabit rezerv 528 MiB'dir. Bu gösterim kabulü gerçek
piyasa verisinin saat/tazelik kabulü değildir; ayrıntılar ve ertelenen işler
[devam planındadır](docs/RAPOT_DEVAM_PLANI.md).

Ardından kullanıcı talebiyle 24 kullanılmayan imaj, dokuz eski kaynak kopyası,
beş yeniden üretilebilir önbellek/build dizini ve 90 kullanılmayan PM2 günlük
dosyası kaldırıldı. Günlüklerin tamamı, sunucu dışında özel bir yedekte bağımsız
olarak doğrulandı. Aktif `279aa9f` kaynağı/current, sekiz aktif veya geri dönüş
imajı, DB'ler, özel ortam/kimlik dosyaları, yedekler ve kabul kanıtları korundu.
Servisler yeniden başlatılmadı; beşi de sağlıklı ve restart sayısı sıfırdı.
10:55:49 UTC kabulünde dört SSR sayfası, 19 statik dosya ve üç anonim 401 kontrolü
geçti; boş alan 7.666.995.200 bayttı. 10:58:08 UTC son envanterinde boş alan
7.666.819.072 bayt, başarısız systemd birimi sıfırdı. Sabit 528 MiB rezerv
değişmedi; kapsam ve kanıtlar [devam planındadır](docs/RAPOT_DEVAM_PLANI.md).

Canonical import ve compatibility listesi [paketleme haritasındadır](docs/PACKAGING_REFACTOR_MAP.md).
`application.scanner.signal_handlers` gerçek uygulamadır; `scanner_side_effects`
eski yola uyumluluk sağlar. Wrapper silmek için kullanım ve tüketici göçü kanıtı
gerekir; [takvim](docs/WRAPPER_DEPRECATION_SCHEDULE.md) otomatik silme emri değildir.

## Geliştirme ortamı ve bağımlılıklar

- Python **3.12** (`.python-version`, `pyproject.toml`); yerelde doğrulanan 3.12.8.
- Node **20.20.2**, npm **10.9.9** (`.nvmrc`, `frontend/package.json`).
- Frontend: Next.js **16.3.8**, React **19.2.3**, TypeScript **5.9.3**, Tailwind
  **4.1.18**, Lightweight Charts **5.1.0**, Zustand **5.0.10**, React Query **5.90.19**.
- Backend: FastAPI/Uvicorn, SQLAlchemy/Pydantic, pandas/NumPy/ta, python-binance,
  isyatirimhisse/yfinance, google-genai, Alembic/psycopg. Telegram alarm teslimi HTTP kullanır.
  `requirements.txt` sürüm aralıklarını ve `requirements-security.txt` güvenlik
  kısıtlarını kullanır; kesin geliştirme/CI çözümü
  `requirements-dev.lock`, araç tanımları `requirements-dev.txt` içindedir.
- `ai_analyst.py` öncelikle `google.genai` kullanır. Eski `google.generativeai`
  fallback kodu kalmıştır; eski SDK güncel zorunlu bağımlılık değildir.
- Lock ortamı `ta` kullanır; `signals.py` isteğe bağlı `pandas_ta` importunu ve
  yokluğunda DataFrame `.ta` uyumluluk katmanını içerir. Ortama paket eklemek
  hesaplama yolunu değiştirebilir; Python/TypeScript/Pine eşdeğerliği varsayılmaz.

Kurulum ve Windows Node alternatifi: [ortam komutları](docs/RAPOT_DEVAM_PLANI.md#geliştirme-ortamı-ve-komutlar).
Repo kökünde seçili .venv ile:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest
uv pip check --python .venv/Scripts/python.exe
# Yalnız ilgili Python dosyalarında lint/format kontrolü:
.venv/Scripts/python.exe -m ruff check <dosyalar>
.venv/Scripts/python.exe -m ruff format --check <dosyalar>
```

`pytest.ini` varsayılan olarak `tests/` ve `middleware/tests/` toplar. Kök
`conftest.py` ortam ayarlarını sentetik değerlerle değiştirir, geçici DB/cache
kullanır, HTTP/socket/curl ağını engeller. Bu izolasyon normal API başlatma
komutlarını veya keyfi native subprocess'leri kapsamaz.

Tam pytest paketindeki `tests/test_strategy_comparison.py` ayrıca Node 20 ve
`frontend` içinde `npm ci` ile kurulmuş TypeScript'i gerektirir. Node PATH'te
değilse `NODE_BINARY` tam yürütücü yolunu seçer. Adaptör yalnız sabit sentetik
fixture ve gerçek gösterge kaynağını okur; ağ/uygulama servisi başlatmaz.
İsteğe bağlı `RAPOT_STRATEGY_REPORT` mutlak JSON yolu ölçüm kanıtını üretir;
CI iki runtime'ı kurar ve raporu artifact olarak saklar.

Seçili Node/npm ile frontend klasöründe:

```powershell
npm ci
npm test
npm run lint -- --no-cache
npm run typecheck -- --incremental false
$env:NEXT_TELEMETRY_DISABLED = '1'
npm run build
npm run test:standalone
```

`test:standalone` önceden build edilmiş çıktıyı yerel HTTP/WS mock'larıyla sınar.
`python -m scripts.ci_quality lint`, Git'in izlediği tüm Python kaynaklarında
Ruff lint/format uygular; middleware ve testler dahildir. Ruff/pre-commit sınırları
iç worktree, ortam/bağımlılık ve üretilmiş klasörleri dışarıda tutar.
Bandit ve pip-audit bulguları açıkça report-only raporlanır; araç hatası, geçersiz
rapor veya eksik kapsam CI'yi başarısız yapar. Yeşil CI sıfır güvenlik bulgusu değildir.
Frontend'de `npm run audit:dependencies` bütün kilitli prod/dev/optional/peer
paketlerini public npm registry üzerinden tarar; her bulgu veya araç/rapor/kapsam
hatası CI'yi başarısız yapar. Ham JSON, lock hash'i ve kapsam manifesti saklanır.
`npm test` bu kontrolün ağsız testlerini içerir. npm 10'un Sharp WASM ortak optional
çocukları için iki `npm ls` extraneous uyarısı lock uyuşmazlığı değildir;
[advisory incelemesi](docs/FRONTEND_DEPENDENCY_SECURITY.md) kapsamı açıklar.
Pip içermeyen uv ortamında bağımlılık kontrolü yukarıdaki `uv pip check` ile yapılır.

P1-G2'nin 20 Eylül üretim kabulünde frontend `bbd9377` / `sha256:e312d7aa…`
imajına geçti; backend/Compose/current `279aa9f` korundu. Sekiz sağlık/SSR GET,
dış HTTPS/RSC ve 12 JS + 1 CSS örneği geçti. Exact imajdaki Linux/musl native
metadata Next16.3.5, Sharp0.35.4, libheif1.23.2 ve libvips8.18.6'yı doğruladı;
bu exploit, görüntü decode veya etkileşimli tarayıcı testi değildir. Taze npm
audit 505/0; sabit 528 MiB disk rezervi korundu. Onaylı üç eski günlük yolundan
ikisi işlem öncesinde yoktu, yalnız kalan bir yedekli dosya kaldırıldı. Ayrıntılı
yetki/kabul ve tamamlanan P3-1 backtest işleri devam planındadır.

## Strateji terminolojisi

- AL/SAT = BUY/SELL; BIST/Kripto piyasa adlarıdır.
- Backend tarama periyotları `1D`, `W-FRI`, `2W-FRI`, `3W-FRI`, `ME`;
  chart/API'deki `1d`, `1wk`, `1h`, `4h` biçimleri aynı arayüz değildir.
- COMBO dört göstergeyi puanlar: MACD, RSI, Williams %R, CCI. `Score=+X/-Y`
  alış/satış puanıdır. Günlük/haftalık AL4–SAT3, diğer tanımlı periyotlar
  AL3–SAT3 kullanır; bilinmeyen periyot fallback'i AL4–SAT4'tür.
- HUNTER **15 göstergenin** dip/tepe koşullarını sayar: RSI, hızlı RSI, CMO,
  BOP, MACD, Williams %R, CCI, Ultimate Oscillator, Bollinger %B, ROC,
  DeMarker, PSY, Z-Score, Keltner %B, RSI(2).
  Günlük/haftalık/iki haftalık dip eşiği 7; üç haftalık/aylık 5; tepe eşiği 10.
  `DipScore=7/7`, **7 gösterge puanı / gerekli 7 puan** demektir; gün sayısı değildir.
  `ActiveIndicators=X/15` kullanılabilir gösterge sayısını ayrıca verir.
  NaN göstergeler puanlanmaz; eşik düşürülmez. RSI puanlardan biridir,
  ayrı zorunlu onay değildir.
- `config.py` eşik tanımları içerse de `signals.py` yalnız MIN_PERIODS'i
  ithal eder; eşikler hesaplayıcı fonksiyonlarda sabittir. Yalnız config
  değiştirerek strateji değiştiği varsayılmaz.
- HUNTER kısa ATR serisi P1-7'de düzeltildi. P3-1'in ilk adımında frontend
  `calculateCombo` geçerli sıfırı korur; eksik, NaN ve sonsuz göstergeler puan
  üretmez. Eşikler, 26 mum koşulu ve AL sonrası SAT önceliği değişmedi. Altı yeni
  regresyonla 105 frontend testi, CI ve imaj yayını geçti. İlk geçişte frontend
  `967f137`, backend/Compose/current `279aa9f` idi. 20 Eylül P1-G2 bağımlılık
  güncellemesiyle üretim frontend'i `bbd9377` oldu; backend/Compose/current
  `279aa9f` kaldı. Yalnız frontend yenilendi.
  Tek günlük temizliği ve uygulama kabulü devam planında ayrı kayıtlardır.
  Hesaplayıcı yeterli sonlu göstergeyle puan üretebilir; yerel alarm son kaydın tüm
  göstergeleri sonlu değilse `unknown` döndürür. P3-1 ikinci adımında özel Pine
  EMA/ATR devam döngüleri yalnız seed sonrasında çalışacak biçimde sınırlandı;
  kaynak alt kümesi sayısal testi TradingView derleyicisi değildir. Güncel 1.091
  satırlık Pine, 21 Eylül'de hash'i doğrulanmış ayrı özel script ile TradingView
  BINANCE:BTCUSDT / standart mum / 1D grafiğinde derlenip çalıştırıldı; skor
  tablosu ve TF OK görüldü. [Kabul kaydı](docs/PINE_RUNTIME_ACCEPTANCE.md)
  gerçek alarm/filtre/testnet kapsamının hâlâ erteli olduğunu açıklar.
  Gerçek Python/TS ölçümünün kapsamı ve
  varsayılan/formül farkları [karşılaştırma belgesinde](docs/STRATEGY_COMPARISON.md).
  Motorları topluca eşitleme kararı verilmedi; yerel backtest kabulü aşağıdadır.

`backtesting_system.py` ayrı CLI'dir; çalışan servis girişleri onu import etmez.
P3-1 üçüncü adımında `Lot.invested` tüm alış giderlerini içerir; komisyon ve kayma
ayrı izlenir. Eski referans tutar üzerinden toplamsal model ve tek en eski lotu
tam satma FIFO sözleşmesi korunur. Nakit + açık maliyet tabanı = başlangıç +
gerçekleşmiş PnL bağıntısı sentetik testlerle doğrulanır. Float/Kahan ve dar
temsil toleransı Decimal defteri değildir;
[muhasebe belgesi](docs/BACKTEST_ACCOUNTING.md) sınırları açıklar.
SVG grafik standart kütüphane ile üretilir; Excel isteğe bağlı openpyxl kullanır.
tqdm yalnız bağımsız paralel runner için gerekir. Muhasebe testleri tek başına
tam CLI kabulü değildir; gerçek fixture CLI kabulü ayrı kaydedilir.

P3-1 dördüncü adımında `BacktestEngine(..., as_of=...)` kapanış anını bir kez
sabitler; açıkça verilen an saat dilimli olmalıdır. `run_single_symbol(...,
data=frame)` sabit günlük OHLCV'yi kopyalayıp doğrular ve sağlayıcıya gitmez.
Start/end dahil işlem günü sınırlarıdır; önceki geçmiş ısınmada korunur.
Önceki kapanmış günlük prefix'in sinyali sonraki mevcut mumun gerçek Open
fiyatında yürütülür. Hem sinyal hem işlem satırı, piyasa takviminde sonraki
gece yarısına ulaşmış olmalıdır; bugünkü Open muhafazakâr biçimde dışlanır.
BIST Close/AOF proxy açılışı ve bilinmeyen `open_quality` reddedilir; yalnız
eksik/None veya `provider` metadata kabul edilir. 120 uygun satır ve ilk sinyal
indeksi60 korunur; en erken işlem indeksi61'dir. Günlük prefix'ten gelişen HTF
politikası değişmez. Paralel worker bir kez veri okur ve ortak `as_of` alır.
[Yürütme sözleşmesi](docs/BACKTEST_EXECUTION.md) kapsamı açıklar.

P3-1 beşinci adımında `run_backtest(..., data_by_symbol=..., costs=...)` tek
piyasanın ortak nakdini artan gün, aynı günde ham sembol metni sırasıyla işler.
COMBO/HUNTER ve sembol içi eylem sırası korunur. Sabit eşleme istenen sembollerle
tam eşleşir, sağlayıcıya dönmez; tüm uygun girdiler ilk işlemden önce doğrulanır.
Her ortak işlem gününün sonunda tek equity kaydı, tüm açık pozisyonları o ana
kadar gözlenen son Close ile fiyatlar. Eksik günlerde fiyat tarihi/eskilik
metadata'sı taşınır; alış fiyatı veya gelecek fiyat fallback'i yoktur. Tek sembol
yolu eski equity sıklığını korur ve başka sembolde açık lot varsa reddeder.
Paralel runner bağımsız sermayeli deneylerdir. Minimum 120 uygun satır kuralı
tarihsel sembol evreni modeli değildir; eskimiş fiyat taşımanın süre sınırı yoktur.
[Ortak portföy sözleşmesi](docs/BACKTEST_PORTFOLIO.md) kapsamı ve sınırları açıklar.

P3-1 son adımında benchmark son NAV/başlangıç nakdini, aynı işlem günlerinin
Open→Close al-tut NAV'ıyla karşılaştırır. Alış maliyeti dahildir; açık pozisyona
varsayımsal satış gideri eklenmez. Tam tarih uçları veya dönem verisi yoksa
benchmark/alpha `None` ve açıklı durum döner; sıfır getiri gibi gösterilmez.
[Benchmark sözleşmesi](docs/BACKTEST_BENCHMARK.md) ayrıntıları açıklar.
`RollingBuyAndHoldAnalysis` tüm değerlendirme dönemini çakışmayan pencerelerle
kapsar; strateji eğitimi/optimizasyonu yapmaz. Eski `WalkForwardAnalysis` yolu
uyumluluk için korunur, kullanılmayan strategy parametresini açıkça bildirir.
[Pencere analizi](docs/BACKTEST_WINDOW_ANALYSIS.md) bağımsız, maliyetli al-tut
deneyleridir. `python -m scripts.backtest_fixture --output-dir <yeni-dizin> --excel`
boş geçici ayar ortamında gerçek COMBO/HUNTER ve JSON/CSV/SVG/XLSX çıktısını sınar;
ağ/sağlayıcı/SQLite/subprocess girişimleri engellenir. [CLI rehberi](docs/BACKTEST_CLI.md)
tekrarlama komutunu ve gerçek piyasa/dış kabul sınırlarını açıklar.

P3-2'de `backup/pre-da7d452-rollback` içindeki beş commit ve 18 frontend dosyası
değerlendirildi; eski kod/belge aktarımı seçilmedi. Güncel tasarım, nullable
sağlık sözleşmesi ve backup ref korunur. [Karar kaydı](docs/BACKUP_BRANCH_REVIEW.md)
parçaların güncel karşılığını açıklar; branch otomatik merge/silme adayı değildir.

## Veri, erişim ve dağıtım

Ana SQLite: `db_session.init_db()` → create_all + uyumlu kolon/index ekleme;
`migrate_db.py` eski veri taşıma aracıdır. Middleware: ayrı modeller ve
`middleware/infra/alembic/` revision zinciri; üretimde migration önce, startup
revision kontrolü sonra gelir. [Migration politikası](docs/DB_MIGRATION_POLICY.md)
iki yolun ayrıntısını ve eski taşıma aracının sınırlarını açıklar.

P2-4, ana SQLite'a yalnız etiketi NULL olmayan kayıtları kapsayan
`idx_signals_special_tag_created(special_tag, created_at)` kısmi indeksini ekler.
Yeni DB'de metadata, mevcut DB'de `init_db()` bu indeksi oluşturur; başlangıç
sırasında disk/WAL alanı bütçelenmelidir. Kod geri dönüşü uyumlu indeksi korur;
üretim verisini geri yüklemez veya indeksi otomatik kaldırmaz. Eşit `created_at`
değerlerinde liste sırası ve LIMIT sınırındaki seçim deterministik değildir.

Ana DB'nin saat dilimsiz UTC sözleşmesi `infrastructure.time.utc_now_naive`
ile korunur: aware UTC saatinden yalnız tzinfo kaldırılır. Yerel saat kullanılmaz;
değişiklik eski satırları dönüştürmez veya API tarih biçimlerini topluca değiştirmez.

Ana API PyJWT ile yalnız HS256 ve zorunlu `exp` kullanır; frontend token'ı yalnız
sekme belleğinde tutar. TestClient için dev-only httpx2, SDK'lar için httpx
korunur; kök test izolasyonu ikisinin de HTTP transport'unu engeller. Ana API'de
kök/health, auth ve API belge yolları dışındaki HTTP yolları admin ister;
dashboard okuması da bu sınırdadır. `/auth/me` kendi JWT kontrolünü korur.
WS beş saniye içinde `{type: "auth", token}` bekler; `authenticated` yanıtından
sonra abonelik başlar. Token URL'ye konmaz; süre dolumu ve çıkış özel veriyi temizler.
Eski Flask sağlık yüzeyi kaldırıldı. Frontend ana API'nin `/health` yanıtını
okur; sağlıklı API, çalışan alarm motoru ve taze piyasa verisini ayrı gösterir.
Özel alarm durumuna erişim yönetici oturumu gerektirir.
Middleware webhook token'ı ve X-Admin-Token yönetim kimliği ana JWT'den ayrıdır.
[README erişim tablosu](README.md#security-notes) ve [middleware rehberi](docs/MIDDLEWARE.md)
güncel sözleşmeyi gösterir. Gizli anahtarlar NEXT_PUBLIC değişkenlerine konmaz.

Üretim yolu Docker Compose 2.24+ ve HTTPS Nginx'tir. API/frontend sürekli
servislerdir; main-init bir defalık iştir. Middleware profili PostgreSQL,
middleware-migrate ve middleware'i ekler. Site alarm motorları ayrı paylaşılan
dosya kilitleriyle tek süreçte çalışır. Kullanılmayan eski PM2/API
launcher dosyaları 21 Eylül repo temizliğinde kaldırıldı; Compose yolu kullanılır.
Host upstream'leri açıkça 127.0.0.1 kullanır; portlar loopback'e bağlıdır.

`.github/workflows/deploy.yml` imaj yayımlar; sunucu deploy'u yapmaz.
`scripts/deploy.ps1` doğrulanmış SHA'yı kontrol edip komutları yazdırır; SSH
çalıştırmaz. [Dağıtım rehberi](docs/DEPLOY.md) ve devam planındaki son kabul
kaydı izlenir. Yalnız belge değişikliği servis restart'ı veya migration gerektirmez.

## Kod stili

Python: Ruff, 100 karakter, çift tırnak, standart/third-party/local import sırası,
fonksiyon imzalarında type hints. TypeScript: functional component + hooks,
Zustand client state, React Query server state, Tailwind utility sınıfları.
Lightweight Charts v5 marker'ları `createSeriesMarkers(series, markers)` ile
oluşturulur; temizlemede `detach()` kullanılır, eski `series.setMarkers` kullanılmaz.
