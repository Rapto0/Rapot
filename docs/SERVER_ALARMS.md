# Sunucuda çalışan alarmlar

`/alarms`, yönetici oturumuyla kalıcı alarm kuralları oluşturur, düzenler,
duraklatır ve siler. Kural sunucuya kaydedildikten sonra tarayıcı, bilgisayar
veya oturum kapansa da API'nin alarm motoru değerlendirmeye devam eder.
TradingView hesabı veya webhook'u gerekmez. Bu sistem bildirim üretir;
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

Kripto Binance'in genel mum verisini, BIST Yahoo'nun ilgili periyot verisini
kullanır. Hesaplama için fiyat önbelleğindeki başka periyoda geri düşülmez.
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
JWT'si ister ve kayıt sahibini denetler. Tarayıcıya bot token'ı veya chat ID
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

Yayın API ve frontend değişikliği gerektirir. Ana DB için doğrulanmış yedek,
tam kaynak SHA'sının CI/imajı ve 528 MiB disk rezervi kontrol edilir. İlk açılış
boş alarm tablolarıyla gelir; kullanıcının yerine canlı alarm oluşturulmaz.
Geri dönüş eski API/frontend imajlarını kullanır ve uyumlu ek tabloları korur;
otomatik veri geri yükleme veya tablo silme yapılmaz. Güncel yayın/kabul durumu
[devam planında](RAPOT_DEVAM_PLANI.md) tutulur.
