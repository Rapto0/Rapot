# Kullanıcının beş Pine göstergesi

13 Ekim 2026 talebi: TradingView'de kullanılan beş göstergenin bütün ayarlarını
Rapot'ta düzenlemek, aynı hesapla grafik önizlemesi ve kalıcı izleme listesi
alarmları kurmak. Canlı piyasa ve TradingView ekran karşılaştırmasını kullanıcı
bir sonraki piyasa gününde yapacak. Bu belge kaynak sözleşmesidir; yayın kabulü
aşağıda ayrıca kaydedilir.

## Kaynak ve ayarlar

Orijinal ekler `indicators/pine/` altında baytları ve lisans açıklamalarıyla
korunur. `.gitattributes` bu dosyaların satır sonlarını dönüştürmez.

| Gösterge | Ayar | Ana çıktı | Kaynağın sinyal zamanı |
|---|---:|---|---|
| HTF RSI Score | 24 | Ağırlıklı RSI skoru, AL/SAT bölgesi | Eşik bölgesine yeni giriş; gelişen mum değişebilir |
| MTF RSI DİP + TEPE Snapshot | 73 | Ayrı DİP/TEPE puanı ve seri | Yalnız 1D; koşul sağlanan her kapanış |
| RSI N OY | 54 | AL/SAT oyları ve uzlaşma | En küçük etkin periyot kapanışı |
| SMI N OY | 74 | AL/SAT oyları ve uzlaşma | En küçük etkin periyot kapanışı |
| RMI N OY | 64 | AL/SAT oyları ve uzlaşma | En küçük etkin periyot kapanışı |

Toplam **289 input**; ad, tür, varsayılan, alt/üst sınır ve adım kaynaklardan
ayrı testlerle karşılaştırılır. Görsel `showTable` ayarı hesaplamayı değiştirmez.
N OY `onlyFirst` ayarı önceki mumun uzlaşmasına bakar; önceki HTTP isteğine bakmaz.
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
SMI ayrıca üst periyot başlangıcından itibaren yüksek/düşük aralığının tam
gözlenmesini ister. Sınırı kesen veya eksik ana mum hazır sayılmaz.

BIST'te çok günlük/haftalık bir periyot ana periyot seçilmişse son açık mumun
kapanış sınırı henüz bilinmeyebilir. Gelişen önizleme bu durumu açıkça gösterir.
Kapanış alarmı bilinen, onaylanmış önceki native mumu kullanır; yeni sınırın
sonraki native mumla doğrulandığı durumda değerlendirme gecikebilir. Bu sınır
1D ana periyotta çok günlük HTF satırları kullanmakla aynı durum değildir.

Pine biçiminde dakika, saniye, gün, hafta ve ay ayarları doğrulanır; gerçek
erişim TradingView hesabı ve sağlayıcıya bağlıdır. Eksik veya reddedilen aralık
başka periyoda çevrilmez. Kaynağın geçerli input sınırları korunur; bir seri
için en fazla 10.000 geçmiş mum istenir. En az gereken uzunluk/momentum bu
sınırı aşarsa açıklı hata verilir. Ek başlangıç geçmişi sınır içinde istenir.
SMI'nın gelişen yüksek/düşük aralığı için ana periyot geçmişi en geniş etkin
satıra göre artırılır. Aylık satırlardaki 31 günlük üst sınır yalnız istek
bütçesidir; mum kapanışı üretmez. 10.000 mum yine de aralığın başlangıcını
kapsamıyorsa eksik SMI aralığı hazır sayılmaz.
Sonlu geçmişten başlatılan özyinelemeli ortalamaların TradingView'nin tüm
geçmişiyle sayısal eşitliği henüz ölçülmemiştir.

## Kullanım ve alarmlar

Grafikte **Özel sunucu göstergeleri** panelini aç, göstergeyi ve ayarlarını seç,
önizlemeyi başlat. Ana periyot göstergenin sözleşmesine uymalıdır. Satır tablosu,
skor/oy çıktıları, kaynak ve hazır olma durumu aynı sunucu hesaplamasından gelir.
Görseldeki ayarlar alarm taslağına aktarılabilir; aktarım alarmı etkinleştirmez.

Alarm Merkezi'nde teknik veya izleme listesi alarmında bir özel gösterge
seçilebilir. AL/SAT sinyali boolean sayısal çıktıdır: **1'e eşit** koşulu kaynak
sinyalini kullanır. Skor/oy çıktıları sayısal eşiklerle, başka göstergelerle ve
VE/VEYA gruplarıyla birleştirilebilir. Her özel operand kendi inputlarını
kalıcı koşul JSON'unda saklar. Aynı alarm içindeki özel göstergelerin ana
periyodu alarmın ana periyoduyla aynı olmalıdır; HTF satırları ayrı ayarlanır.

N OY için ana periyot en küçük etkin satırla **aynı native kimlikte** olmalıdır.
Varsayılanları 1D olduğundan sinyal varsayılan olarak günlük kapanıştadır;
gün içinde fiyat hareketi tek başına kapanış sinyali üretmez. Snapshot 1D ile
sınırlıdır. Başlangıç düğmeleri bu göstergelerde kapanış ve mum başına bir kez
seçer; HTF RSI Score için mum içi değerlendirme seçer. Kullanıcı tekrar
politikasını ve isteğe bağlı Telegram teslimini ayrıca düzenler.
Snapshot/N OY sinyal çıktısı mum içi tetikle seçilirse kayıt açıklı hatayla
reddedilir; mum içi inceleme için skor, oy veya bölge çıktısı kullanılabilir.

Mevcut motorun ilk hazır gözlemde başlangıç durumunu kurma, revizyon/kopuklukta
devamlılığı sıfırlama, eski veriden alarm üretmeme, kalıcı olay kuyruğu ve
tekrar teslim korumaları sürer. Önizleme yalnız geçici veri talebidir. Tarayıcı
kapansa da kaydedilmiş etkin sunucu alarmı izlenir; grafiği açık tutmak gerekmez.
Bu çalışma otomatik etkin test alarmı veya Telegram mesajı oluşturmaz.

## Kaynak sınırları ve kabul

Özel hesaplama ve sağlayıcı erişimi ayrı, tek bir işçide çalışır. API istekleri
ve alarm turu bellek sonucunu okur; hesaplama ağ beklerken ana alarm kilidini
tutmaz. Aynı hesap/gösterge/ayar/sembol sonuçları ve aynı native veri isteği
paylaşılır. Alarm sonuçları kısa tutulur; ayrıntılı önizleme sınırlı ayrı önbellek
kullanır. Talep, bekleyen iş, tazelik ve kapasite durumu raporlanır.
En fazla 256 farklı etkin özel hesap ayarı paylaşılır; aynı ayarla çok sayıda
alarm bu sayıyı artırmaz. Sınırı aşan kayıt açık hata alır. Önceden veya ayrı
bir yoldan oluşturulmuş fazla ayarlar da çalışıyormuş gibi gösterilmez;
engellenen yapılandırmalar durum ekranında ayrıca sayılır.

Önizlemenin 5 saniyede sorgulanması, yeni piyasa verisinin 5 saniyede geldiği
veya tüm liste üyelerinin aynı anda kontrol edildiği anlamına gelmez. Native
geçmiş yenileme hedefi 30 saniyedir; sağlayıcı ve kuyruk gecikmesi buna eklenir.
Bu ekleme tam BIST evreni veya 3.000 karma gösterge alarmı için kapasite kabulü
değildir. Aktif alarm ve önizleme talebi yokken özel veri işi başlatılmaz.

Yerel kabul; elle hesaplanmış OHLC fixture'ları, her inputun Pine kaynağıyla
karşılaştırılması, zaman sınırları, eksik veri, ayar kalıcılığı, API erişim
sınırları, kuyruk/cache sınırları ve frontend etkileşimlerini kapsar.
TradingView derleyicisinde beş scripti yeniden çalıştırma, anlık aynı mum/aynı
ayar karşılaştırması ve gerçek Telegram alarmı sonraki canlı kabul kapsamıdır.

**Yayın kaydı:** uygulama ve doğrulama sürüyor; kaynak/imaj ve bağımsız üretim
kabul kimlikleri bu iş tamamlandığında eklenecek.
