# Kullanıcının beş Pine göstergesi

13 Ekim 2026 talebi: TradingView'de kullanılan beş göstergenin bütün ayarlarını
Rapot'ta düzenlemek, aynı hesapla grafik önizlemesi ve kalıcı izleme listesi
alarmları kurmak. Canlı piyasa ve TradingView ekran karşılaştırmasını kullanıcı
bir sonraki piyasa gününde yapacak. Bu belge kaynak sözleşmesidir; yayın kabulü
aşağıda ayrıca kaydedilir. Sonraki kullanıcı talimatı, beş göstergenin canlı
fiyat güncellemelerinde çalışmasını ve en küçük periyot kapanışını beklememesini
istedi. Aşağıdaki canlı sözleşme bu yeni davranışı anlatır; eski yayının kabulü
kendi tarih/sürümü altında korunur.

## Kaynak ve ayarlar

**22 Ekim yayın kabulü:** `0c7b266d8e3b6a7885b6f56cf7f3d245e6a79565`
yalnız frontend'e 08:36:36 UTC / 11:36:36 TSİ'de yayımlandı; ayrı salt okunur
kabul 08:37:09 UTC'de geçti. API/Compose/current `e28ef616` kaldı; API aynı
container ve 21 Ekim başlangıcıyla restart0, middleware/PG/özel dosyalar aynı.
İlgili 55 frontend testi, tip/lint; aynı kaynakta beş CI işi
`39747468405` ve temiz imaj yayını `39747553384` geçti. İmaj
`sha256:0ffb8665cc32939d08440ea5b3a24456e05ca6572a9d518c83bd6f40832ae792`.
Beş SSR, 22 statik varlık, üç anonim401 ve yeni üç çıktı metni doğrulandı.
Receipt `8ada631c22eab9e39e416ce04d5687c20ca7a1213f84a20fb1bac46264908cb0`;
ayrı kabul dosyası `817cfa823370cc7232815ad7705e3d4fd5c3f57eed51fb3d080730b98f35ee7b`.
Kanıt `runtime-data/20261022-alarm-output-frontend-v2/` içindedir; Git'e
alınmaz. İlk aracın main-init imaj varsayımı değişiklik başlamadan reddedildi;
başarısız kayıt korunup yeni v2 araçta gerçek ayrı imaj pinleri doğrulandı.
DB işlemi/yeni alarm/Telegram bildirimi veya otomatik takip yapılmadı.

22 Ekim arayüz açıklaması: alarm çıktılarının başında seçilen göstergenin adı
gösterilir. AL/SAT sinyali, sayısal oy/puan, eşik bölgesi ve hazırlık sayıları
ayrıca açıklanır. N OY göstergelerinde `onlyFirst` açık/kapalı açıklaması mevcut
ayarı izler; HTF yeni bölge girişi ve Snapshot puan hedefi ayrı anlatılır.
Çıktı anahtarları, hesaplar ve kayıtlı alarm ayarları değişmez. İlgili 55 frontend
testi geçti; bu arayüz kontrolü yeni canlı piyasa kabulü değildir.

21 Ekim'de hazır çıktısı görülmeyen 58 kodun 14 Ekim kayıtlı KAP pazar listesiyle
karşılaştırmasında 20 YİP, 19 PÖİP, 8 Ana, 9 Alt ve 2 Yıldız payı bulunur.
[Borsa İstanbul işlem yöntemi](https://www.borsaistanbul.com/piyasalar/pay-piyasasi/piyasa-isleyisi)
YİP/PÖİP için tek fiyatı doğrular. Bu 39 payda seyrek fiyat oluşumuyla uyumludur;
58 payın tamamının bekleme nedenini veya güncel üyeliğini kanıtlamaz.
Diğer 19 kod: ARTMS, DERIM, OZATD, OZYSR, RALYH, SEGYO, TMPOL, UFUK, DGGYO,
EUKYO, HUBVC, ISATR, ISBTR, ISKUR, SKYLP, TRHOL, VKFYO, KAYSE, NUHCM.
Eski fiyatı taze sayma kuralı eklenmez; yeni geçerli fiyat normal akışta
değerlendirilir. Kullanıcı hacimsiz paketini doğruladığından hacim bu işin
kapsamı dışındadır.

Standart RSI için [7 Ekim canlı alarm kabulü](LIVE_MARKET_ACCEPTANCE_2026-10-07.md)
korunur. Williams %R dahil dokuz standart teknik alanın hesap testleri
`tests/test_advanced_alarm_market_data.py`, negatif Williams eşik karşılaştırması
`tests/test_advanced_alarm_conditions.py` içinde önceki başarılı 21 Ekim turuna
dahildir; tekrar çalıştırılmadı. Williams'a özel canlı Telegram kabulü iddia
edilmez. Standart alanların [30/60 saniye OHLCV yenileme hedefi](SERVER_ALARMS.md)
beş özel göstergenin her canlı fiyat politikasıyla karıştırılmamalıdır.

Orijinal ekler `indicators/pine/` altında baytları ve lisans açıklamalarıyla
korunur. `.gitattributes` bu dosyaların satır sonlarını dönüştürmez.
Whitespace/EOF commit kancaları da yalnız bu özgün Pine dizinini dönüştürmez.

| Gösterge | Ayar | Ana çıktı | Kaynağın sinyal zamanı |
|---|---:|---|---|
| HTF RSI Score | 24 | Ağırlıklı RSI skoru, AL/SAT bölgesi | Eşik bölgesine yeni giriş; gelişen mum değişebilir |
| MTF RSI DİP + TEPE Snapshot | 73 | Ayrı DİP/TEPE puanı ve seri | Yalnız 1D; koşul sağlanan her kapanış |
| RSI N OY | 54 | AL/SAT oyları ve uzlaşma | En küçük etkin periyot kapanışı |
| SMI N OY | 74 | AL/SAT oyları ve uzlaşma | En küçük etkin periyot kapanışı |
| RMI N OY | 64 | AL/SAT oyları ve uzlaşma | En küçük etkin periyot kapanışı |

Toplam **289 input**; ad, tür, varsayılan, alt/üst sınır ve adım kaynaklardan
ayrı testlerle karşılaştırılır. Görsel `showTable` ayarı hesaplamayı değiştirmez.
Tablodaki sinyal zamanı özgün Pine kaynaklarının davranışıdır. **Canlı sunucu
politikası v2** bu kapanış kapılarını kaldırır. N OY `onlyFirst` canlı akışta
önceki geçerli fiyat gözleminin uzlaşmasına bakar; HTTP önizleme isteğine bakmaz.
HTF RSI Score da canlı eşik bölgesine girişte sinyal üretir. İlk hazır gözlem
başlangıç durumunu kurar; bağlantı boşluğunun arkasından sahte giriş üretilmez.
İki yönde gereken oy sayısı bağımsızdır; eksik satır için gerekli N düşürülmez.
Aynı periyodu kullanan iki satır ayrı oy/puan sayılır, veri isteğini paylaşır.
Snapshot'ın yedinci satırı **7D**, diğer göstergelerin ilgili satırı **1W**'dir.
Eşit süreli bu iki periyot aynı mum dizisi kabul edilmez.

Bu beş kaynak Python'a ayrı hesaplayıcılar olarak taşınır. Sunucuda keyfi Pine
metni çalıştıran bir yorumlayıcı yoktur. Genel RSI/SMI/RMI adı taşıyan başka bir
paketin varsayılan formülü bu kaynakların yerine kullanılmaz. Wilder RMA'nın
SMA başlangıcı, Snapshot'ın ilk sıfır değişimi, SMI'nın iki EMA adımı ve RMI'nın
kendi periyodundaki momentum referansı korunur.

## Veri ve zaman sözleşmesi

Özel göstergelerin BIST ve Binance USDT mumları Borsapy üzerinden **TradingView
native periyotlarından** alınır. Kripto için bu kaynak ayrıca belirtilir;
mevcut normal kripto grafiği/alarmlarının Binance kaynağı değiştirilmez.
Borsapy'nin tanımadığı periyodu sessizce 1D'ye çeviren varsayılanı bu adaptörde
kullanılmaz. İstek ayrı sınıf haritasıyla yapılır; kütüphanenin global ayarı
değiştirilmez. Sağlayıcının tamamladığı seri alınmadan sonuç yayınlanmaz.

TradingView kaynaklarının [diğer periyotlardan veri](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/)
ve [çalışma modeli](https://www.tradingview.com/pine-script-docs/language/execution-model/)
sözleşmeleri gereği gelişen HTF değeri ile geçmişte kapanmış HTF değeri farklı
olabilir. Gelecekteki HTF kapanışı geçmiş bir ana muma uygulanmaz. Ana mum ve
üst periyotların açılışları sağlayıcıdan gelir; çok günlük BIST mumları takvim
günlerini toplayarak oluşturulmaz.

BIST günlük kapanışı sağlayıcının seans/saat dilimi bilgisi ve tarihli
düzeltmelerinden belirlenir. Tanınmayan seans biçimi için saat tahmin edilmez.
Sonraki native mumun varlığı geçmiş mumun kapanmışlığına tanıktır. Son açık
HTF'nin gelecekteki kapanışı bilinmese bile önceki kapanmış durumdan gözlem
anına kadar gelişen RSI/RMI hesaplanabilir; sahte bir kapanış saati atanmaz.
Canlı SMI, sağlayıcının ilgili native mumunun yüksek/düşük aralığını ve bundan
sonra gözlenen fiyat uçlarını kullanır. Güncel native günlük mumun yüksek/düşük
değerleri, aynı gün için doğrulanmış üst periyodun mevcut aralığını yalnız
genişletebilir; geçmiş HTF aralığı günlük veriden yeniden oluşturulmaz.
Geçmiş önizlemesinin özgün politika hesabında sınırı kesen veya eksik ana mum
hazır sayılmaz.

BIST'te çok günlük/haftalık son açık mumun gelecekteki kapanış sınırı bilinmese
bile canlı akış aynı native mum başlangıcını doğruluyorsa güncel fiyatla hesap
yapılır. 2–6D veya 2–3W mumları takvim günü aritmetiğiyle üretilmez. Kullanıcı
özellikle kapanış tetiklemesini seçerse onaylanmış kapanış tanığı gerekir;
bu seçenek varsayılan canlı fiyat politikası değildir.

Pine biçiminde dakika, saniye, gün, hafta ve ay ayarları doğrulanır; gerçek
erişim TradingView hesabı ve sağlayıcıya bağlıdır. Eksik veya reddedilen aralık
başka periyoda çevrilmez. Kaynağın geçerli input sınırları korunur; bir seri
için en fazla 10.000 geçmiş mum istenir. En az gereken uzunluk/momentum bu
sınırı aşarsa açıklı hata verilir. Ek başlangıç geçmişi sınır içinde istenir.
Geçmiş önizlemesinde SMI aralığı için kullanılan ana periyot geçmişi bütçesi
canlı sinyalin bekleme süresi değildir. Native canlı mum aralığı ayrıca gelir.
Geçmişteki aylık satırların 31 günlük üst sınırı yalnız istek bütçesidir;
mum kapanışı üretmez.
Sonlu geçmişten başlatılan özyinelemeli ortalamaların TradingView'nin tüm
geçmişiyle sayısal eşitliği henüz ölçülmemiştir.

## Kullanım ve alarmlar

21 Ekim toparlanma sözleşmesi: native bağlantının hesap token'ı süreli
yenilenir; sağlıklı yenileme mevcut hesap başlangıçlarını silmez. Geçici
sağlayıcı retleri artan beklemeyle yeniden denenir; eski istek kuşağının
gecikmiş cevabı yeni talebi doğrulayamaz. Bilinmeyen sembol sürekli sorgu
döngüsüne alınmaz. Desteklenmeyen uzun periyot yeni native gün veya yeni
token sonrasında tekrar sınanabilir. Ret kalksa bile yeni geçerli native
tanık ve gereken geçmiş olmadan gösterge hazır sayılmaz.

Tek geçmiş işçisi aynı özel WebSocket'i kullanır; tek sembolün eksik
periyotları en fazla 10 chart, toplam 12.000 mum ve 12 MiB gruplarla alınır.
Chart açma aralığı en az 0,1 saniyedir. Grup tamamlanınca chart'lar kapatılır;
tek periyodun hatası veya hesap değişimi kısmi gösterge başlangıcı yayımlamaz.
Süresi dolan önizleme yeniden açıldığında gereken bütün native periyotlar
önce doğrulanır, ardından tek geçmiş revizyon kararıyla birlikte önbelleğe
alınır. Bir periyodun geçmişi değişmişse elde kalan diğer gerekli periyotlar
da yeniden alınır; eski ve yeni geçmiş birleştirilmez. Revizyon turu sinyal
başlangıcı yayımlamaz; sonraki tur güncel native tanıkları bekler. Böylece
aynı eski tarih özetinin periyot başına bütün hazırlığı yeniden başlatması
önlenirken gerçek geçmiş düzeltmesi ve kopma kontrolleri korunur.
İlk geçersiz fiyat devamlılığı keser; aynı geçersiz dönemin tekrarları
yeniden hazırlanan başlangıcı sürekli silmez. Geçerli fiyat gelmeden alarm
üretilemez. `/advanced-alarms/coverage` yöneticiye her yapılandırılmış sembolün
seçili çıktılarının hazırlığını ve bekleme nedenini verir; bu GET yeni veri
işi başlatmaz. Hazır çıktı, alarm koşulunun gerçekleştiği veya bildirimin
teslim edildiği anlamına gelmez. Canlı kabul ve kaynak ölçümleri
[21 Ekim kaydında](LIVE_MARKET_CAPACITY_2026-10-21.md) ayrı tutulur.

Grafikte **Özel sunucu göstergeleri** panelini aç, göstergeyi ve ayarlarını seç,
önizlemeyi başlat. Ana periyot göstergenin sözleşmesine uymalıdır. Satır tablosu,
skor/oy çıktıları, kaynak ve hazır olma durumu aynı sunucu hesaplamasından gelir.
Görseldeki ayarlar alarm taslağına aktarılabilir; aktarım alarmı etkinleştirmez.
Önizleme geçmişi 128 noktanın zaman, çıktı ve sinyallerini korur; periyot
satırlarının ayrıntıları yalnız son noktada saklanır. Güncel `latest.rows`
tablosu tam kalır. 32.768 hücrelik bütçe artırılmaz; geçmişte yinelenen satır
ayrıntıları yüzünden etkin göstergelerin tekrar replay edilmesi önlenir.

Alarm Merkezi'nde teknik veya izleme listesi alarmında bir özel gösterge
seçilebilir. AL/SAT sinyali boolean sayısal çıktıdır: **1'e eşit** koşulu kaynak
sinyalini kullanır. Skor/oy çıktıları sayısal eşiklerle, başka göstergelerle ve
VE/VEYA gruplarıyla birleştirilebilir. Her özel operand kendi inputlarını
kalıcı koşul JSON'unda saklar. Aynı alarm içindeki özel göstergelerin ana
periyodu alarmın ana periyoduyla aynı olmalıdır; HTF satırları ayrı ayarlanır.

N OY için ana periyot en küçük etkin satırla **aynı native kimlikte** olmalıdır.
Bu yalnız ana mum kimliği kuralıdır, kapanışı bekleme kuralı değildir. Snapshot
1D kimliğiyle çalışır. **Beş başlangıç düğmesi de mum içi / koşula girişte**
tetikleme seçer. 10:02'de gelen geçerli fiyat, bütün etkin satırların 10:02'deki
gelişen RSI/SMI/RMI değerine uygulanır. Her satır kendi son kapanmış native
durumundan başlar; önceki mumun gösterge değeri sinyal değeri olarak kullanılmaz.
Kapanmış geçmiş hesaplamanın matematiksel başlangıcı olarak yine gereklidir.
Kullanıcı tekrar politikasını, kapanış seçeneğini ve isteğe bağlı Telegram
teslimini ayrıca düzenler. Önceden kaydedilmiş kapanış kuralları değiştirilmez.

Beş özel göstergenin birlikte kullanıldığı koşullar ortak canlı gözlem kimliği
ister. Özel göstergeye eklenen fiyat operandı da aynı quote fiyatıdır. Normal
RSI/EMA/COMBO gibi diğer teknik alanlarla karma koşullar önceki son-taze-mum
sözleşmesini korur; bu alanların kaynak zamanları ayrıca taşınır ve form bu
ayrımı açıklar. Bu çalışma normal teknik alanların tümünü yeni canlı hesaplayıcıya
dönüştürdüğü iddiasında bulunmaz.

Wilder/EMA durumu her fiyatı yeni bir mum gibi biriktirmez. Açık mum her
gözlemde aynı kapanmış başlangıçtan yeniden hesaplanır; Snapshot seri puanı
fiyat güncellemesi sayısıyla artmaz. Canlı `onlyFirst` ilk geçerli koşul girişini
izler. Bu kullanıcı tarafından istenen canlı politika, özgün Pine dosyalarının
geçmiş kapanış sinyallerini değiştirmez; eski geçmiş çizgisi canlı tick arşivi
olarak sunulmaz.

Mevcut motorun ilk hazır gözlemde başlangıç durumunu kurma, revizyon/kopuklukta
devamlılığı sıfırlama, eski veriden alarm üretmeme, kalıcı olay kuyruğu ve
tekrar teslim korumaları sürer. Önizleme yalnız geçici veri talebidir. Tarayıcı
kapansa da kaydedilmiş etkin sunucu alarmı izlenir; grafiği açık tutmak gerekmez.
Bu çalışma otomatik etkin test alarmı veya Telegram mesajı oluşturmaz.

## Kaynak sınırları ve kabul

Native geçmiş başlangıcı, canlı bağlantı yönetimi ve sıralı fiyat değerlendirmesi
ayrı, sabit sayıda işçide çalışır. Aynı hesap/gösterge/ayar/sembol sonuçları ve
aynı native veri isteği paylaşılır. Geçmiş yalnız başlangıç, gerekli yenileme
ve uzlaştırma işinde hazırlanır; her fiyat güncellemesinde bütün geçmiş tekrar
hesaplanmaz. Canlı hesaplayıcı en fazla on satırlık kapalı durum özeti tutar.
Önizleme/alarm okuması bellek sonucunu kullanır.

Alarm planı hazırlanırken özel operandın doğrulanmış ayar kimliği ve alan
anahtarı değiştirilemez bir kopyada tutulur. Her fiyat güncellemesinde aynı
ayarlar tekrar doğrulanıp hashlenmez. Bu yalnız hesap kimliğinin paylaşımıdır;
fiyat gözlemi, hesap/epoch, veri tazeliği ve native hazırlık her okumada
kontrol edilir. Kural girdisi değişirse eski hazırlık yeniden kullanılamaz.

Bir sembolün bütün ayarları aynı fiyat ve kaynak zamanıyla yayımlandıktan sonra
ilgili alarmlar eşzamanlı çağrıyla değerlendirilir; bu işlem bitmeden sonraki
fiyat gözlemi onun yerini alamaz. Kısa eşik aşımı/geri dönüş böyle korunur.
Her native periyot ayrı TradingView chart session kullanır; aynı sembolün
bütün periyotları ve tek fiyat aboneliği aynı sıralı WebSocket üzerinde kalır.
16 Ekim `fe9e7e63` düzeninde günlük ve gün içi periyotlar sürekli bağlıdır;
1D dışındaki D/W/M periyotları iki native mumla doğrulanan süreli aboneliklerdir.
Native günlük mum önce uygulamanın seans/saat doğrulamasından geçer. Uzun periyot
paketi de aynı doğrulamayı geçip tüketici tarafından onaylanınca aboneliği
kapatılır; gerçek mum başlangıcı, önceki mum ve kapalı hesap durumu korunur.
Her fiyat güncellemesi bütün etkin satırlara aynı fiyatı uygular.

Her bağlantıda en fazla 32 geçici abonelik için yer ayrılır. 805 sembol ×
10 uzun/günlük TF örneği 805 sürekli günlük ve en fazla 128 geçici chart ile
planlanır; 8.050 mantıksal TF talebi sürekli 8.050 açık chart değildir.
Sertifika bağlantı, hesap, sembol ve native gün nesline bağlıdır. Günlük mumun
değişmesi/düzeltilmesi, geçmiş revizyonu, bağlantı kaybı veya kaldırılıp yeniden
eklenen sembol eski sertifikayı geçersiz kılar. Yeni gerçek native paketler
gelmeden eski mum kimliğiyle sinyal verilmez. Uzun periyotların bağımsız tarihsel
düzeltmeleri, günlük mumda görünmüyorsa bir sonraki uzlaştırmaya kadar fark
edilemeyebilir; bu yol her eski mumun anlık revizyonunu izleme garantisi değildir.
14 Ekim canlı denemesinde aynı chart session'a ikinci fiyat serisinin
eklenmesi sağlayıcı tarafından reddedildi; bu protokol sınırı yerel testlere
de eklendi. Önizlemedeki `observation_price`, kaynak zamanı ve hesap çıktısıyla
aynı fiyat gözlemidir; ayrı grafik fiyatı kullanılarak aynı an varsayılmaz.
16 Ekim kaynak düzeltmesinde büyük listelerin ilk aboneliği bağlantı başına
kontrol turunda 16 yeni seriyle kademeli açılır. Bu sağlayıcının oturum açma
hızı hatasına karşı uygulama sınırıdır; toplam desteklenen seri garantisi
değildir. Bekleyen kayıtlar görünür; aynı talep sonraki turlarda devam eder.
Ağ gönderimi alıcı kilidini tutmaz. Mum içi geçmiş başlangıcı ilgili sembolün
gereken native tanıklarını bekler; başarısız geçmiş işi 30–1.800 saniye artan
gecikmeyle yinelenir. Bağlantı kopması bu beklemeyi atlatmaz.

16 Ekim ek kaynak düzeltmesi, planlamayı abonelik değişikliği, native onay/ret
ve gerçek yeniden deneme süresine bağlar. Günlük verisi reddedilen sembolün
üst periyotları işlenebilir bekleme kuyruğunda sayılmaz; kullanılamayan veri
olarak görünür. Sembol listeden silinmez. Hazırlık işçisi her turda en fazla
64 ertelenmiş işi döndürür; eksik başlangıç/yenileme için ayrı 64 işlik arama
ve önizleme adaleti korunur.

Aynı sembol/periyodu kullanan etkin ayarların en büyük geçmiş ihtiyacı
paylaşılır. İstenen en yüksek mum sayısı sınırlı devamlılık özetinde saklanır;
ham önbellek boşalsa da sonraki küçük ayar geçmiş penceresini daraltmaz.
Yeni, daha uzun geçmiş ilk kez gerekirse hesap bir kez yeniden hazırlanabilir.
Eski kapalı mum hash'i, eksik satır ve bağlantı/revizyon korumaları gevşetilmez.
Bu ek düzeltmeler **`5472db4`, 16 Ekim 14:52:02 UTC**'de
API/frontend/Compose/current'e yayımlandı; **14:52:50–14:53:24 UTC** bağımsız
yayın kabulü geçti. Yerelde 2.114 Python/bir atlama ve son fallback düzeltmesi
için 40 ilgili test; 310 frontend/derleme/standalone ve aynı kaynakta beş CI
işi geçti. Taze yedek bütün 15 tabloyla bağımsız restore edildi; mevcut dört
kural satırı (biri etkin), tek 805 üyeli liste, 805 durum ve altı olay korundu.
Bu yayın kabulü beş göstergenin birlikte hazır canlı önizlemesini veya sürekli
CPU kazancını kanıtlamaz; sonraki manuel kabul [16 Ekim kaydında](LIVE_INDICATOR_ACCEPTANCE_2026-10-16.md)
ayrı tutulur.

Akış bütün fiyat olaylarını korur. Native açık mumun yalnız Close değişimi,
gösterge fiyatını ayrıca taşıyan quote bulunduğu için yeni mum işi üretmez;
son Close dahili satırda saklanır ve sonraki rollover'a aktarılır. İlk veri,
geçmiş mum düzeltmesi, O/H/L ve metadata değişimleri işlenir. BIST günlük
native kimliği değişince üst periyodun ilk gerçek yeni paketi tanık olarak
yeniden işlenir; takvim günü hesabından veya önbellekten tanık üretilmez.
Süreli native tanık düzeninin ilk yayını **16 Ekim 14:13:07 UTC**'de
`fe9e7e63` ile API/frontend/Compose/current'e yapıldı;
14:13:17–45 UTC bağımsız yayın kabulü geçti. [16 Ekim kaydı](LIVE_INDICATOR_ACCEPTANCE_2026-10-16.md)
imaj/CI/yedek ve koruma kanıtlarını tutar. İlk durumdaki sıfır derlenmiş hesap,
805 bekleyen üye ve %100 CPU örnekleri nedeniyle yayın kabulü tam liste veya
sürekli kapasite kabulü olarak sunulmaz.
Sembol-kural ilişkisi bitset ile indekslenir; her tick bütün evreni taramaz.
Değişmeyen gözlem durumları SQLite yazısı üretmez. Olaylar hemen kalıcılaştırılır;
olay üretmeyen durum değişimleri sınırlı gruplarla birleştirilir. Telegram
teslim işçisi yeni olayda uyandırılır.
En fazla 256 farklı etkin özel hesap ayarı paylaşılır; aynı ayarla çok sayıda
alarm bu sayıyı artırmaz. Sınırı aşan kayıt açık hata alır. Önceden veya ayrı
bir yoldan oluşturulmuş fazla ayarlar da çalışıyormuş gibi gösterilmez;
engellenen yapılandırmalar durum ekranında ayrıca sayılır.

**30 saniyelik geçmiş sorgusu canlı alarm tetikleme yolu değildir.** Native
mumlar ve fiyat güncellemeleri kalıcı WebSocket üzerinden gelir. Önizlemenin
bir saniyelik bellek sorgusu alarmın çalışma zamanını belirlemez; tarayıcı
kapalıyken de sunucu çalışır. Sağlayıcı gecikmesi, ağ ve gerçek yük altında
işleme süresi yine vardır; borsadaki her işlemin sıfır gecikmeyle gelmesi
garanti edilmez.

Kalan 30 saniyelik sınırlar, eski fiyatı reddetme ve başarısız geçmiş isteğini
yeniden deneme içindir; canlı fiyatlar arasında bekleme koymaz. Sağlıklı canlı
hesap, periyodik geçmiş HTTP hatasında korunur; geçmiş hatası ayrı tanılanır.
Kesintisiz native akışta altı saatlik uzlaştırma yalnız özetin yaşından dolayı
başlangıcı sıfırlamaz. Gerçek geçmiş düzeltmesi ve bağlantı boşluğu yine
karşılaştırma durumunu geçersiz kılar.

Bağlantı sayısı, native seri, derlenmiş satırlar ve sıralı olay kuyruğu yerel
üst sınırlarla korunur. 16 Ekim'de 500'den 516 chart session'a büyüme gerçek
sağlayıcı kapasite hatası verdi. Sonraki kaynak koruması dört bağlantının her
birinde en fazla 500 fiziksel seri kabul eder. Süreli tanık düzeninde sürekli
günlük/gün içi maliyet ile geçici abonelik rezervi bu sınıra birlikte sığmalıdır;
sembolün gereken verisi tek bağlantıda güvenle izlenemiyorsa hazır sayılmaz.
8.192 yerel istek bütçesi 8.192 fiziksel abonelik kabulü değildir. Kararlı
yerleşim çalışan sembolleri liste değiştiğinde başka bağlantıya taşımaz.
Bunlar TradingView hesabının kabul edeceği abonelik
kapasitesi iddiası değildir. Eksik/reddedilen TF, eski fiyat, bağlantı kopması,
geçmiş revizyonu ve kuyruk taşması görünür `unknown`/devamlılık sıfırlaması
üretir; aşırı yük sessizce güncel veri gibi gösterilmez. Kaynak zamanı, işleme
gecikmesi, bekleyen olay ve kapasite sayaçları durum ekranında izlenir.
Aktif alarm ve önizleme talebi yokken özel veri işi başlatılmaz. Tam BIST,
3.000 karma canlı kural ve tam seans kapasitesi ayrı canlı kabul gerektirir.

Canlı yolun yerel üst sınırları: 256 farklı etkin ayar, 4.096 sembol/ayar
hesabı, 40.960 derlenmiş satır, 2.000.000 başlangıç durumu hücresi, dört native
bağlantı, 8.192 mantıksal native seri ve 8.192 sıralı olay. Native geçmiş LRU'su en fazla
64 seri / 60.000 mum, kısa alarm sonuçları 262.144 hücre tutar. Bunlar ayrı
bütçelerdir; uzun momentum/pencere ayarları daha erken kapasite sınırına
ulaşabilir. Kabul sırası kararlıdır; fazla işlerin derlenip sonra sürekli
önbellekten atıldığı bir yeniden hazırlama döngüsü kurulmaz.

Normal, ardışık native mum geçişinde kapanan mum Wilder/EMA durumuna **bir kez**
işlenir. RMI için gerekli momentum kuyruğu, SMI için gerekli yüksek/düşük
penceresi sınırlı tutulur. Düzeltme, atlanan native kimlik veya bağlantı
boşluğunda geçmiş yeniden hazırlanır. BIST günlük başlangıcı değiştiğinde
kapanış saati bilinmeyen HTF kimliği yeni native paketle doğrulanır.
SMI'da fiyat akışının göstermediği fakat native mumun bildirdiği uç değerler
zaman tanığıyla birleştirilir; daha eski fiyat gözlemine gelecekteki yüksek/
düşük değer uygulanmaz. Zaman uyumu henüz doğrulanamıyorsa sonuç hazır sayılmaz.

Yerel yapısal test beş varsayılan ayar × 631 sembolün 3.155 hesap ve paylaşılan
6.941 native seri talebine dönüştüğünü doğrular; gerçek abonelik açmaz. Bütün
on satır açıkken hesaplayıcıların model belleği yaklaşık **66,7 MiB**, varsayılan
etkin satırlarda **53,4 MiB** ölçüldü. Bu konservatif nesne erişim hesabı ortak
değişmez değerleri tekrar sayar; process RSS, allocator, geçmiş, kuyruk, API,
veritabanı ve Telegram dahil değildir. Üretim RAM veya tam evren kabulü sayılmaz.

Yerel kabul; elle hesaplanmış OHLC fixture'ları, her inputun Pine kaynağıyla
karşılaştırılması, zaman sınırları, eksik veri, ayar kalıcılığı, API erişim
sınırları, kuyruk/cache sınırları ve frontend etkileşimlerini kapsar.
TradingView derleyicisinde beş scripti yeniden çalıştırma, anlık aynı mum/aynı
ayar karşılaştırması ve gerçek Telegram alarmı sonraki canlı kabul kapsamıdır.

## 13 Ekim 2026 canlı fiyat yayını ve bağımsız kabul

**Tamamlandı:** `4b739835d3cd12485b50422028a3cb1134dd8ac7` kaynağı
**19:56:39 UTC / 22:56:39 TSİ**'de API/frontend/Compose/current'e yayımlandı.
Bağımsız kabul **19:56:55–19:57:15 UTC**'de geçti. Önceki `b3200ed9` kaynağı
ve imajları geri dönüş için korunur. Middleware/PostgreSQL aynı container ve
runtime kimliklerinde kaldı; DRY_RUN ve trading/live kapalı durumu değişmedi.

| Kanıt | Kimlik |
|---|---|
| API imajı | `ghcr.io/rapto0/rapot/backend@sha256:23c65e711ead2528bd0c7a089dd60846b527027d14408b865b1a292eb463b771` |
| Arayüz imajı | `ghcr.io/rapto0/rapot/frontend@sha256:f4ce5d8494379e2db425f555972739bb78138e15f70453345cd7bf1bbe5ee059` |
| Beş CI işi | [38457171430](https://github.com/Rapto0/Rapot/actions/runs/38457171430), tamamı başarılı |
| Temiz imaj yayını | [38457206678](https://github.com/Rapto0/Rapot/actions/runs/38457206678), başarılı; additive/delta yolları kapalı |
| Yayın receipt SHA-256 | `2fa7e53322fb0739cb6864b85db921e8a885151cd6fc4e6f6a273f2d16ec8f0f` |
| Bağımsız kabul SHA-256 | `1b007a4619cfc4f67d16b15ba48e5e8fc59f0a860c164769ad92122af2147fae` |
| Taze SQLite yedeği | 1.342.660.608 bayt; `250e34a04a2ed08affefad1133cd5fd7b545350a85b2b512a46cd890b9aff167` |
| Bağımsız restore kanıtı SHA-256 | `6939856aa19481bb9fbe4efab781ce02a1dbb1e5c768aa17504399cb53714633` |

Yerelde **1.983 Python başarılı / bir atlama**, **307 frontend testi**, tüm
290 Python kaynağında Ruff, frontend lint/typecheck, webpack production ve
standalone HTTP/WS kabulü geçti. Aynı kaynağın Linux CI'sinde standart
Turbopack ve Docker kabulü geçti. 111 Linux runtime paketi ve 295 kaynak/
bağımlılık dosyasının imaj hash'leri kaynakla eşleşti. Üç mevcut Binance/
websockets deprecation uyarısı yeni hesaplama hatası değildir. İlk commit
kancası OpenAPI dosyasının son satırını düzeltti; kanonik sözleşme değişmedi.

Saf testler aynı anda tüm TF'lerin güncel fiyatını, Wilder ilk geçerli seed'ini,
uzun RMI momentumunu, tick rollback'ini, SMI yüksek/düşük zaman sırasını ve
normal native geçişte tek commit'i doğrular. Kapalı piyasa başlangıcında son
onaylı mum canlı değer diye sunulmaz; yeni native çift geldiğinde ilerler.
Geçmiş/fiyat/rollover yarışları, eski seed kurulumu, kopukluk sonrası ilk gözlem,
kuyruk taşması, HTTP hatası ve kaynak sınırları ayrı regresyonlarla kapsanır.

Yerel geçici SQLite ölçümünde aynı özel koşulu paylaşan 3.000 kural için tek
snapshot okundu; değişmeyen beş tur 15,7–16,9 ms ve sıfır DB yazısıyla tamamlandı.
Aynı anda üretilen 3.000 olayın kalıcı yazımı 128'lik gruplarla yaklaşık 1,22
saniyeydi. Bu ölçüm API kategori kotası, Telegram teslimi veya gerçek sunucu
kapasitesi testi değildir. Beş gösterge × 631 sembolün varsayılan ve tüm on TF
açık ayarları yerel kabul bütçesine sığdı. Bellek ölçümünün saf kaynak SHA-256'sı
`38461bdbf7cac6798f9970c521f28ef4314408a0c78ab00b305a1b67bf1bf75c`'dir.

Taze yedek sunucu dışında bağımsız restore ile doğrulandı. İlk binary aktarımın
süre sınırı kaydı korundu; aynı dosya doğrulanmış önekten sürdürülerek tamamlandı.
Yalnız bu işin geçici sunucu snapshot'ı doğrulama sonrası kaldırıldı. Yayın
araçlarının yedi offline kontrolü, kabulün 10 DB ve 41 API negatif senaryosu
bağımsız geçti; üretimde DB restore/migration/silme yapılmadı.

Üretim kabulü 13 SSR sayfası, 33 statik dosya, iki yönlendirme ve 18 anonim
401 yanıtını doğruladı. Yönetici kataloğu v2 / 5 gösterge / 289 input ve iş
oluşturmayan 422 önizleme doğrulandı. 15 tablonun tüm satırları/şeması, özel
dosyalar, tek izleme listesi, üç eski olay ve üç silinmiş kural korundu.
Dört servis healthy/restart0; alarm motoru hatasız ve Telegram yapılandırılmış.
Sıfır etkin alarmda normal mum işi/kuyruk 0/0; özel işçiler talep olmadığı için
başlatılmadı. 805 normal abonelik ve seans dışında sıfır taze sembol, canlı
fiyat/kapsam kabulü değildir.

19:57:05–15 UTC kısa örnekleri **279,30–298,22 MiB kullanılabilir RAM**,
**%19,361 / %8,032 CPU** ve **5.057.884.160 bayt boş alan** gösterdi. Sabit
528 MiB rezerv korundu. Bu kısa, etkin alarmsız örnek tam seans veya 3.000
canlı teknik alarm yükünü kanıtlamaz. Yeni etkin kural, Telegram mesajı, AI,
emir veya otomatik takip oluşturulmadı; eski gözlem timer'ı disabled/inactive.
Canlı TradingView sayısal karşılaştırması, gerçek gecikme ve kapsam sonraki
piyasa açık kabulünde ölçülmelidir.

Yerel kanıtlar `runtime-data/20261013-live-indicators/` altında, özel taze
yedek `C:/Users/memet/RapotBackups/20261013-live-indicators-binary-aa0ed6063230482b/`
altında saklanır; Git'e alınmaz.

## 14 Ekim 2026 bağlantı düzeltmesi yayını

`e11d3d3d` API/frontend/Compose/current yayını **07:49:26 UTC**, bağımsız
uygulama kabulü **07:50:01 UTC**'de tamamlandı. 1.995 Python/bir atlama,
307 frontend, beş CI işi ve temiz imaj yayını geçti. 15 tablonun bütün
satırları/şema, özel dosyalar ve middleware/PG korundu. Gerçek THYAO native
geçmişi ve beş quote üzerinde beş göstergenin bağımsız tam geçmiş hesabı
**25/25** eşleşti. Bu TradingView derleyicisiyle aynı an karşılaştırması
değildir. Yayın kabulünde etkin kural sıfırdı; sonradan oluşan büyük liste
yükü ayrıca test edilir. İmajlar, yedek, uygulama kabulü, hacim ve takvim
sınırları [14 Ekim kaydındadır](LIVE_INDICATOR_ACCEPTANCE_2026-10-14.md).

## 13 Ekim 2026 önceki gösterge yayını ve bağımsız kabul

**Tamamlandı:** `b3200ed9ced081807f0471b4c82f33d9653ba7bc` kaynağı
**17:45:35 UTC / 20:45:35 TSİ**'de API/frontend/Compose/current'e yayımlandı.
Bağımsız kabul **17:46:39–17:46:58 UTC**'de geçti. Önceki kaynak `8b4e1bab`
geri dönüş için korunur. Middleware/PostgreSQL aynı container ve runtime
kimliklerindedir; DRY_RUN ve trading/live kapalı durumu korunur.

| Kanıt | Kimlik |
|---|---|
| API imajı | `ghcr.io/rapto0/rapot/backend@sha256:53c4b58f15159a3bb55a7ffdb136c547011d4bd10fb369702f6fb845ae0fd3fb` |
| Arayüz imajı | `ghcr.io/rapto0/rapot/frontend@sha256:740560459028be8dbbf7206d01e85e79948bf6ac4273ad604f09e9d416ab1bd5` |
| Beş CI işi | [38439878283](https://github.com/Rapto0/Rapot/actions/runs/38439878283), tamamı başarılı |
| Temiz imaj yayını | [38439913974](https://github.com/Rapto0/Rapot/actions/runs/38439913974), başarılı; additive/delta yolları kullanılmadı |
| Yayın receipt SHA-256 | `7e093b4113fe573a335b7671bc75835440e85845007bde82dd7717e93d22fe04` |
| Bağımsız kabul SHA-256 | `a5d78c878a6cadc06e07e04a23d4b6cf41f86c30d54d335960c21a729084924f` |
| Taze SQLite yedeği | 1.342.660.608 bayt; `250e34a04a2ed08affefad1133cd5fd7b545350a85b2b512a46cd890b9aff167` |
| Bağımsız restore kanıtı SHA-256 | `b5746bcea531a3d5ff0f19429dee17d7c090a0e810b7b9f93a7855937a172ad8` |

Yerelde son tam Python paketi **1.895 başarılı / bir atlama**, frontend
**304 başarılı**, tüm 281 Python kaynağında Ruff, frontend lint/typecheck,
125 kurulu paketin bağımlılık tutarlılığı geçti. Sentetik gerçek motor testi
karma BIST/kripto listesinde iki kuraldan dört kalıcı olay üretti; yeniden
gözlem, motor yükleme ve hesap değişiminde eski sinyal tekrarlanmadı.
Eksik zorunlu HTF olay üretmedi. Kapasite kontrolü aynı SQLite yazma
transaction'ındadır; aynı ayarın paylaşımı, güncellemede eski ayarın çıkarılması,
duraklatma ve başarısız kaydın veriyi değiştirmemesi doğrulandı.

Windows'ta standart Turbopack derlemesi subprocess IPC hatası verdi; başarısız
log korundu. Yerel webpack production ve taze standalone kabulü geçti;
**aynı kaynağın Linux CI'sinde standart Turbopack ve container kabulü de geçti**.
Bir ara Python turunda eski kapsam testinin `123` fiyatını rastgele kimlik
alt dizisiyle karıştırması ve tur sürerken değişen OpenAPI snapshot'ı iki hata
verdi. Kapsam testi alan sözleşmesini denetleyecek biçimde düzeltildi; ayrıca
normal geçmiş yolunun özel periyotları 500 yerine 422 ile reddetmesi korundu.
Son sabit kaynak tam paketi ve Linux CI temizdir. İlk hata kayıtları silinmedi.
Commit kancasının özgün Pine EOF'larını değiştirmesi geri alındı; beş ekin
bayt hashleri yeniden eşleşti ve dar kanca istisnası eklendi.

Üretim kabulü 13 SSR sayfası, 33 statik dosya, iki yönlendirme ve 18 anonim
401'i doğruladı. Yönetici kataloğu beş gösterge/289 input döndürdü; geçersiz
önizleme 422 aldı ve özel işçiyi veya veri talebini başlatmadı. Sekiz emekli
GET yolu 410, eski sinyal WS 4410 kalır. 111 runtime dağıtımı ve 286 Python/
bağımlılık kaynak dosyası imajda hashleriyle doğrulandı.

Taze yedek sunucu dışında bağımsız restore edildi. 15 tablonun **bütün satırları
ve şeması** typed fingerprint ile yayın öncesi/sonrası aynıydı: tek kişisel
liste, üç önceki olay, üç soft-delete kural, sıfır eski sinyal/tarama ve 290
tanımsız kurtarma satırı korundu. Özel ortam/şifreli kimlik dosyaları değişmedi;
migration, restore veya ikinci geçmiş temizliği yapılmadı. Yalnız doğrulanan
bu işe ait geçici sunucu yedek dosyası exact hash kontrolüyle kaldırıldı;
sunucu dışındaki özgün yedek, restore ve kanıt korunur.

Dört servis healthy/restart0; alarm motoru hatasız, etkin kural sıfır,
normal mum işleri/kuyruk/seri/değer sıfır, özel işçi henüz talep edilmemiştir.
Üç kısa RAM örneği **317,270 / 319,602 / 320,855 MiB** kullanılabilir bellek;
iki CPU aralığı **%9,438 / %13,972**; son boş alan **5.196.759.040 bayt**.
Sabit 528 MiB disk rezervi korundu. 805 abonelik ve piyasa kapalıyken sıfır
taze fiyat bu anın örneğidir; tam seans veya tüm evren kabulü değildir.

Yerel çalışma kanıtları `runtime-data/20261013-custom-indicators/` altında
Git dışında korunur. Bu kabul için sağlayıcı sorgusu, AI üretimi, Telegram
mesajı, etkin test alarmı, emir veya yeni otomatik takip oluşturulmadı.
**Açık kalan dış kabul:** aynı sembol/periyot/ayarlarla TradingView sayısal
karşılaştırması, BIST/kripto canlı sinyal zamanı, gerçek Telegram teslimi ve
istenen liste boyutunda tazelik/kuyruk davranışı. Kullanıcı bunları sonraki
piyasa gününde elle test edecek; bu yayın onları tamamlanmış saymaz.
