# Sunucuda çalışan alarmlar

## Gelişmiş gün içi alarm merkezi — 4 Ekim 2026

Yeni `/alarms` ekranı `/advanced-alarms` API'sini kullanır. Önceki günlük motor
`/alarms/legacy`, tarayıcıya bağlı eski kurallar `/alarms/local` altındadır.
Bu üç sistemin kuralları otomatik taşınmaz. Aşağıdaki **Önceki günlük motor**
bölümü yalnız eski API `/alarms` sözleşmesini açıklar.

### Kural ve bildirim sözleşmesi

- Sunucu genelinde **1.000 fiyat, 1.000 teknik ve 1.000 izleme listesi alarmı**;
  kurallar süresizdir. Açık sembol listesi, kalıcı sunucu listesi veya tüm BIST
  evreni seçilir. Kural/liste başına 2.000 sembol, 1.000 sunucu listesi sınırı
  vardır. Liste değişikliği bağlı kuralların sürümünü yeniler.
- VE/VEYA grupları en fazla 32 karşılaştırma ve dört seviye içerir. Fiyat/OHLCV,
  RSI, EMA, SMA, MACD/sinyal, ATR, Williams %R, COMBO ve HUNTER alanları sabit
  sayı veya başka alanla karşılaştırılır; yukarı/aşağı kesişme desteklenir.
  Her alan farklı periyot seçebilir: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`,
  `1d`, `1wk`, `1mo`. Bu bir Pine kaynak kodu çalıştırıcısı değildir.
- Veri geldikçe/mum içinde veya kapanmış mum seçilir. `on_enter`, koşula yeni
  girişte; `once_per_bar`, gerçek sağlayıcı mumu başına; `cooldown`, bekleme
  süresi dolunca yeni gözlemle tekrar üretir. Tüm kiplerde seçilen en az
  bildirim aralığı uygulanır. İlk geçerli gözlem başlangıç durumudur;
  yeniden başlatma, hesap değişimi ve veri kopmasından fiyat kesişmesi türetilmez.
- Eksik, eski, sonlu olmayan veya periyodu/saat dilimi tutarsız veri `unknown`
  sayılır. VEYA grubundaki eksik dal da gizlenmez. Mum içi göstergeler değişebilir.
  Python/TypeScript/Pine gösterge eşitliği varsayılmaz.
- BIST `volume` koşulu yalnız doğal sağlayıcı hacimleri doğrulanmış seride
  değerlendirilir. Eksik/geçersiz hacimden üretilen sıfır `unknown` olur;
  doğrulanmış gerçek sıfır korunur. Fiyat tabanlı koşullar bağımsız çalışır.
- Telegram seçimi varsayılan kapalıdır. Açıkça seçilen alarm mevcut sunucu
  hedefine gider; token/chat ID tarayıcıya dönmez. Olay ve teslim kuyruğu
  kalıcıdır; beş deneme, 429 bekleme süresi, teslim kira süresi ve en az gönderim
  aralığı uygulanır. En fazla 10.000 bekleyen teslim; tamamlanan geçmiş
  30 gün/100.000 olaydır. Bekleyen kayıtlar geçmiş temizliğinde silinmez.
  İsteğin kabul edilip yanıtın kaybolması tekrar teslim yaratabilir; uçtan uca
  tam bir kez teslim veya kesintideki bütün tetikleri yakalama garantisi yoktur.

### Tarayıcıdan bağımsız veri ve motor

API, `advanced-alarms.lock` ile tek motorun sahibi olur. Ayrı veri işçileri,
değerlendirme ve Telegram döngüleri tarayıcıdan bağımsız çalışır. Compose API
yeniden başladığında kayıtlı etkin kurallar yeniden yüklenir. API/sunucu kapalı
olduğunda değerlendirme yapılamaz; geri dönüşte eski fiyatlardan toplu tetik üretilmez.

BIST için kayıtlı Borsapy/TradingView hesabıyla sürekli fiyat aboneliği ve
dakikalık mum geçmişi tutulur. Yetki/oturum hatası anonim veya Yahoo verisiyle
gizlenmez. Kripto açıkça Binance kullanır. Fiyatın sağlayıcı zamanı ve alınma
zamanı ayrıdır; bağlantının açık olması gecikmesiz fiyat kanıtı değildir.
Kopma, tekrar bağlanma, güncel/bayat sembol sayıları ve bekleyen geçmiş işleri
ekranda gösterilir. `realtime_verified=false` canlı kabul tamamlanana dek korunur.
Socket açık görünse bile 90 saniye boyunca hiçbir taşıma mesajı/kalp atışı
gelmezse bağlantı yenilenir; kapalı piyasada fiyat gelmemesi tek başına kopma değildir.

Fiyat koşulları gelen fiyat gözlemlerini kullanır. Teknik koşullar gerçek
sağlayıcı OHLCV'sinden hesaplanır; fiyat kotasyonlarından uydurma mum oluşturulmaz.
Gösterge geçmişinin yenileme hedefi 1m için 30, diğer periyotlar için 60
saniyedir; kuyruk ve sağlayıcı süreleri bunu uzatabilir. Isınma süresi de
fiyat akışından farklıdır.
Alarm geçmişi en fazla iki isteğe özel TradingView sağlayıcısıyla alınır;
hesap kilidi ağ çağrısı boyunca tutulmaz. Kimlik/epoch/revizyon sonuç öncesinde
yeniden kontrol edilir. Ekran geçmişi sıcak bellekten çıkarılmışsa sınırlı disk
önbelleğini okuyabilir; bu okuma eski veriyi alarm hesabına güncel olarak sokmaz.
BIST sağlayıcısının işlem olmayan dakikaları atlayan doğal mum serisi korunur;
tam periyot katı olan boşluklara yapay mum eklenmez. Geçmiş bu haliyle saklanır
ve hesaplanır; yeni gözlemlerde aşılan boşluk alarm devamlılığını sıfırlar ve
boşluğun iki tarafındaki değerlerden kesişme üretilmez. Kripto aralık doğrulaması
kesintisiz kalır. Sağlayıcının geçmiş mum silmesi/eklemesi, zaman gerilemesi veya
önceki geçmişin karşılaştırılamaması da alarm başlangıcını sıfırlar; normal kayan
pencere ve diskten geçmişi geri okuma devamlılığı korur.
`history_cached`, eski ama önbellekte bulunan seri sayısını;
`history_ready`, şu an alarm için güncel seri sayısını; `history_failures_by_reason`
ise sağlayıcı/boşluk/geçersiz veri ayrımını gösterir.

7 Ekim canlı seansta fiyat, izleme listesi ve çok koşullu teknik kuralın normal
motor/kuyruk üzerinden Telegram teslimi doğrulandı; ilk iki mesajı kullanıcı da
doğruladı. [Kabul kaydı](LIVE_MARKET_ACCEPTANCE_2026-10-07.md) dar örneklem ile
tam evren/gecikme garantisi arasındaki sınırı ve üretim sürümünü belirtir.
BIST'te bir mumun kapandığını sonraki gerçek sağlayıcı mumu doğrular; yarım gün
ve tatil kapanışı tahmin edilmez. Son seans mumu bir sonraki gerçek muma kadar
bekleyebilir. Kriptoda yerel UTC aralık sınırı kullanılır.

Değerlendirme ve ekran yenileme hedefi bir saniyedir. Tur en fazla 5.000
kural-sembol karşılaştırması, 0,2 saniye hesaplama bütçesi ve 250 kalıcı değişimle
sınırlıdır; sıra sonraki turda devam eder. Bunlar katı uçtan uca süre garantisi
değildir: DB/sağlayıcı gecikmeleri ve büyük liste çarpımları süreyi uzatabilir.
Ekrandaki hazır/kontrol sayısı **son turdur**, tüm evrenin aynı saniyede tarandığı
anlamına gelmez. 3.000 kural kotası sınırsız donanım kapasitesi değildir.

Sıcak ham geçmiş 128 seri × 500 mum, hesaplanmış son gözlemler 4.096 seri/120.000 değer hücresi ve
durum belleği 15.000 kural-sembol kaydıyla sınırlıdır. Dakikalık gerçek sağlayıcı
geçmişi ayrı, sınırlı SQLite önbelleğindedir; sınırsız tarih arşivi değildir.
Ana alarm yazıları 592 MiB boş alan eşiğinde durur; 528 MiB işletim rezervi
korunur. Kapasite nedeniyle bekleyen işler başarı olarak gösterilmez.

`ADVANCED_ALARMS_ENABLED`, `ADVANCED_ALARM_MARKET_ENABLED` ve
`ADVANCED_ALARM_ALL_BIST_ENABLED` varsayılan açıktır. Test ortamı bunları kapatır
ve sahte sağlayıcı kullanır. Kullanıcının ertelediği canlı kabul, üretimde
normal veri servisinin çalışmasını kapatmaz.

### Kalıcılık, erişim ve grafik

7 Ekim'de eklenen yöneticiye özel `/advanced-alarms/heartbeat` ve `/coverage`
tanı yolları yalnız belleği okur; sağlayıcı/DB sorgusu veya geçmiş işi başlatmaz.
Motorun son turu yanında toplam ve son 60 saniyede kontrol edilmiş farklı kural
sürümlerini kategori bazında gösterir. Süreç kimliği ve sayaç zamanı, yeniden
başlatılmış/eski ölçümleri ayırt eder. KAP şirket kodları doğrulanmış pay evreni
olarak etiketlenmez. Sınırlı canlı yük için ayrılmış test kuralları her turda
90 saniyelik kalp atışı ve sabit son tarih içeren özel izin dosyasını gerektirir;
normal kurallar bu dosyalara bağımlı değildir. Test sahibi Telegram gönderemez.
[Tam seans ölçümü ve kabul sınırları](FULL_SESSION_ACCEPTANCE_2026-10-08.md).

`advanced_alarm_rules`, `advanced_alarm_states`, `advanced_alarm_events` ve
`advanced_alarm_watchlists` tabloları ana DB'ye uyumlu olarak eklenir. Eski
sinyal/trade/alarmlar değiştirilmez. API yönetici ve kayıt sahibi denetimi,
özel önbelleksiz yanıt, sürümle çakışma kontrolü ve girdi sınırları uygular.
Duraklatma/düzenleme/silme, henüz teslim işçisi almamış bildirimleri iptal eder.

Grafikte 1m/5m seçenekleri ve 26 çizim aracı vardır: çizgi/ışın, şekil, kanal,
Fibonacci, ölçüm, pozisyon planlama ve not araçları. Çizimler zaman/fiyat
koordinatlarıyla **tarayıcıda**, sembol/periyot başına en fazla 80 adet saklanır;
sunucu alarmı oluşturmaz. Seçme/sürükleme, mıknatıs, stil, kilit/gizleme,
nesne listesi, geri al/yinele desteklenir. Cihazlar arasında çizim eşitlemesi
bu sözleşmenin parçası değildir.

Sentetik testler erişim, girdi, fiyat kesişmesi, veri boşluğu, yeniden başlatma,
kuyruk/429, kota, disk koruması ve çizimleri kapsar. Gerçek piyasa kapsamı,
gecikme, bölünme uyumu ve Telegram teslimi piyasa açıkken kabul edilir.
Yayın ve kanıtların güncel durumu [devam planındadır](RAPOT_DEVAM_PLANI.md).

## Önceki günlük motor

`/alarms/legacy`, yönetici oturumuyla kalıcı alarm kuralları oluşturur, düzenler,
duraklatır ve siler. Kural sunucuya kaydedildikten sonra tarayıcı, bilgisayar
veya oturum kapansa da API'nin alarm motoru değerlendirmeye devam eder.
TradingView alarmı veya webhook'u gerekmez. Varsayılan BIST veri kaynağı için
sunucuda Borsapy/TradingView hesabı gerekir; kripto Binance genel verisini kullanır.
Bu sistem bildirim üretir;
Spot middleware emir hattına bağlanmaz.

## Kurallar ve grafik bağlantısı

- İlk gösterge kümesi RSI(14), Williams %R(14), COMBO ve HUNTER'dır.
  COMBO/HUNTER sunucudaki Python hesaplayıcılarını kullanır. Grafik TypeScript
  hesaplayıcısıyla veya TradingView Pine ile birebir eşdeğerlik varsayılmaz.
- Kripto periyotları `1h`, `4h`, `1d`; BIST periyodu `1d`'dir.
  Desteklenmeyen bir periyot sessizce günlük veriye çevrilmez.
  BIST saatlik/4 saatlik alarmları, güvenilir yarım gün/seans takvimi
  doğrulanmadan kullanıma açılmaz.
- RSI/W%R dip koşulu `değer <= eşik`, tepe koşulu `değer >= eşik`tir.
  COMBO/HUNTER ilgili dip/tepe skorunun eşiğe ulaşmasını değerlendirir.
- `on_enter`, önceki kapanmış mumda sağlanmayan koşulun son kapanmış mumda
  sağlanmasıdır. `once_per_bar`, koşul sürdükçe her yeni kapanmış mumda
  bir olay üretir. Kapanmamış mumlardan alarm üretilmez.
- Oluşturma, düzenleme veya yeniden etkinleştirmeden önce kapanmış mumlar
  geçmiş bildirim yağmuruna dönüştürülmez. Kesintideki bütün mumları geriye
  dönük tarayan bir teslim garantisi yoktur; son kapanmış mum çifti kullanılır.
- Her kural en fazla 20 sembol içerir; toplam 50 kural ve 100 kural-sembol
  kaydı sınırı uygulanır. İzleme listesinden seçilen semboller kaydedilen
  kuralın içeriğidir; sonraki tarayıcı listesi değişiklikleri otomatik aktarılmaz.
- Eski tarayıcı kuralları `/alarms/local` altında kalır. Bunlar otomatik
  taşınmaz, etkinleştirilmez veya Telegram aboneliğine dönüştürülmez.

Pine editörü/çalıştırıcısı eklenmemiştir. Yeni özel göstergelerin kabulü,
kaynak/formül incelemesi ve sabit verili doğrulama gerektirir.

## Çalışma ve veri sınırları

API lifespan'i `api/runtime/server_alarms.py` üzerinden tek alarm döngüsü
başlatır. Aynı SQLite dizinindeki `server-alarms.lock` süreç kilidi ikinci
motorun aynı anda çalışmasını engeller; scanner kilidi ayrıdır. Compose'un
mevcut tek API worker düzeni korunur, yeni bir ücretli servis gerekmez.
`SERVER_ALARMS_ENABLED=false` motoru durdurur. API kapalıysa alarmlar çalışmaz.

Her tur tamamlandıktan sonra yaklaşık 60 saniye beklenir. Sağlayıcı beklemeleri
tur başına 45 saniyeyle, bildirim işi toplam 30 saniye ve 20 denemeyle sınırlanır.
SQLite işlemleri ve kilit beklemeleri bu sürelerin dışındadır. Hesaplama
kalıcı sıra imleciyle sonraki turda devam eder; böylece
yavaş bir sağlayıcı listenin sonundaki kuralları sürekli geride bırakmaz.
Çok sayıda sembol veya bildirim yeniden denemeleri süreyi uzatabilir; bir
dakikada kesin kontrol/teslim taahhüdü yoktur. Motor durumu, son tur, kural
hataları ve olay geçmişi arayüzde görünür. Eksik/bayat veri veya tamamlanmamış
sembol kontrolü başarılı tam kontrol sayılmaz.

Kripto Binance'in genel mum verisini, BIST varsayılan olarak kimlikli
Borsapy/TradingView günlük mumlarını kullanır. `BORSAPY_USE_FOR_BIST=false`
eski BIST Yahoo yolunu açıkça seçer; kimlik/sağlayıcı hatasında sessiz kaynak
değişimi yapılmaz. Borsapy BIST verisi eski fiyat önbelleğiyle karıştırılmaz;
alarmın ek kısa önbelleği bu yolda atlanarak gateway kimlik kontrolü korunur.
Hesaplama için başka periyoda geri düşülmez. Runtime yanıtı BIST kaynağını
ve desteklenen `1d` periyodunu ayrıca bildirir.
BIST günlük mumun kapanışı muhafazakâr biçimde İstanbul'da sonraki gece
yarısı kabul edilir; bu seans kapanışında anında bildirim sözleşmesi değildir.
BIST tatil/seans ve sağlayıcı gecikmesi sınırları, TradingView ile aynı veri
ve aynı zamanda sinyal garantisi vermez.

## Kalıcılık, erişim ve bildirim

Ana SQLite'daki alarm kuralı, sembol durumu ve olay tabloları `init_db()` /
SQLAlchemy metadata yoluyla eklenir. Mevcut sinyal/trade satırları değiştirilmez.
Olaylar kural sürümü, sembol ve mum kimliğiyle tekilleştirilir. Yeniden başlatma
sonrası işlenen mum bilgisi korunur. Ağ erişimi sırasında yazma işlemi açık
tutulmaz; kural değiştirme/duraklatma/silme yarışları kayıt öncesi denetlenir.

`GET/POST /alarms`, `PUT/DELETE /alarms/{id}` ve `GET /alarms/events` yönetici
JWT'si ister ve kayıt sahibini denetler; yanıtlar `private, no-store` taşır.
Tarayıcıya bot token'ı veya chat ID
dönmez. Yönetici olmayan kullanıcıların ortak Telegram hedefine bildirim
göndermesi desteklenmez.

Telegram seçimi varsayılan kapalıdır. Açılırsa mevcut sunucu Telegram hedefine
bildirim gönderilir. Sunucudaki token/hedef kurulumu bu ekrandan değiştirilmez.
Olay ve teslim durumu kalıcıdır; geçici hatalar sınırlı sayıda yeniden denenir.
Telegram isteğinin alınıp yanıtının kaybolduğu durumda tekrar teslim mümkün
olduğundan uçtan uca tam bir kez teslim garantisi yoktur. Olay kimliği mesajda
izlenebilir. Düzenleme, duraklatma ve silme, henüz gönderime alınmamış bekleyen
bildirimleri iptal eder. Gönderime alınmış bir mesaj tamamlanabilir;
doğrulanmış teslim gönderildi
olarak kaydedilir. Üç teslim denemesi, kalıcı bekleme ve gönderimler arasında
asgari aralık uygulanır. Yapılandırma kaldırılırsa bekleyen kayıtlar korunur.

Tamamlanan olay geçmişi en fazla 30 gün ve 20.000 kayıt ile sınırlıdır;
bekleyen bildirimler bu temizliğe dahil değildir. 1.000 bekleyen bildirim
sınırına ulaşılırsa yeni olay teslim hatasıyla kaydedilir; eski kuyruk ezilmez.
Geçmişsiz, silinmiş kurallar için de süre/sayı sınırı vardır. Temizlik yalnız
bu yeni alarm tablolarını kapsar; sinyal/trade/önbellek verilerine dokunmaz.
Sıra imleci `bot_stats` içindeki `server_alarm_cursor` anahtarında tutulur.

## Doğrulama ve yayın

Yerel testler sentetik veri/geçici DB ve sahte HTTP kullanır. Yetki, sahiplik,
girdi sınırları, kapanmış mumlar, veri hataları, kalıcı tekilleştirme, yeniden
başlatma, bildirim hataları ve motor kapanışı ayrı doğrulanır. Yerel testler
gerçek Telegram teslimi veya gerçek sağlayıcı kabulü değildir.

Alarm motorunun yayını API ve frontend değişikliği gerektirir; sonraki ortak
Borsapy veri geçişi scanner nedeniyle botun da yenilenmesini gerektirir.
Bu site geneli Borsapy geçişi `ab18dc4` ile tamamlandı. Ana DB için doğrulanmış yedek,
tam kaynak SHA'sının CI/imajı ve 528 MiB disk rezervi kontrol edilir. İlk açılış
boş alarm tablolarıyla gelir; kullanıcının yerine canlı alarm oluşturulmaz.
Geri dönüş eski API/frontend imajlarını kullanır ve uyumlu ek tabloları korur;
otomatik veri geri yükleme veya tablo silme yapılmaz. Güncel yayın/kabul durumu
[devam planında](RAPOT_DEVAM_PLANI.md) tutulur.

2 Ekim 2026'da `d4d2b65` API/frontend kaynağı üretime alındı. Canlı yönetici
okumalarında motorun çalıştığı ve son turun hatasız olduğu; BTCUSDT/1h ve
THYAO/1d verilerinden kapalı mum hesaplanabildiği doğrulandı. Üç alarm tablosu
boş olarak eklendi; mevcut şema korundu. Yerel sentetik CRUD/bildirim testleri
ve canlı salt okunur kabul, gerçek kullanıcı alarmı veya Telegram teslimi
olarak yorumlanmaz. İlk kuralı kullanıcı yönetici oturumuyla oluşturur.
