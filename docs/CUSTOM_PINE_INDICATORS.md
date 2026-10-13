# Kullanıcının beş Pine göstergesi

13 Ekim 2026 talebi: TradingView'de kullanılan beş göstergenin bütün ayarlarını
Rapot'ta düzenlemek, aynı hesapla grafik önizlemesi ve kalıcı izleme listesi
alarmları kurmak. Canlı piyasa ve TradingView ekran karşılaştırmasını kullanıcı
bir sonraki piyasa gününde yapacak. Bu belge kaynak sözleşmesidir; yayın kabulü
aşağıda ayrıca kaydedilir.

## Kaynak ve ayarlar

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

## 13 Ekim 2026 yayını ve bağımsız kabul

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
