# 14 Ekim 2026 canlı gösterge kabulü

Kullanıcının “Piyasa şuan açık” mesajıyla manuel çalışma **07:10:40 UTC /
10:10:40 TSİ**'de başladı. Önceki otomatik takip yasağı korunur. Bu çalışma
gerçek/testnet emir veya TradingView webhook testi içermez.

## İlk üretim gözlemi

Üretim API/frontend/current kaynağı `4b739835`; dört servis sağlıklı, yeniden
başlatma sıfır. Etkin alarm sıfır; bir kullanıcı listesi ve üç eski teslim
olayı korunuyor. Normal mum işi/kuyruk **0/0**. Üç kısa örnekte kullanılabilir
RAM **270,72–285,23 MiB**, CPU **%22,25–22,50**. Bu bir tam seans yük kabulü değildir.

07:16:28 UTC bellek kapsamında 805 adayın 566'sı taze, 66'sı eski, 173'ü
fiyatsızdı. Bugünkü resmî [KAP pazarları](https://www.kap.org.tr/tr/Pazarlar)
ile eşleştirilen 631 pay kodunun tamamı abonelikte: **565 taze / 66 eski /
0 fiyatsız**. Fazladan 174 şirket kodu gerçek işlem gören pay evreniyle aynı
anlama gelmez. Tek örnek, seyrek işlem ile veri kesintisini ayıramaz.

## Canlı testte bulunan ve düzeltilen kaynak sorunları

1. Beş THYAO önizlemesinde native akış hazır olamadı. İzole gerçek sağlayıcı
   tanısında 1D/2D için 515'er mum, OHLC ve native zaman doğrulaması geçti.
   Canlı soket ikinci seride `exceed limit of series in the session` aldı.
   Her native periyot ayrı chart session'a taşındı; sembolün bütün periyotları
   ve tek quote aboneliği aynı sokette kalır. Dört bağlantı sınırı korunur.
   Session kapasite hatası artık oturum kimliği hatası sayılmaz.
2. Liste ekranı hesap kilidi meşgulken tüm fiyatları boş gösterebiliyordu.
   Sunucuda zaten açık BIST fiyat bağlantısı aynı hesap/revizyon/epoch ve
   bağlantı sağlığı denetimleriyle paylaşılır. Yeni abonelik açılmaz; eski,
   eksik veya reddedilen veri hazır sayılmaz. Sorun önce başarısız, düzeltme
   sonrasında geçen 50 sembollü regresyonla yeniden üretildi.

Düzeltilmiş stream kaynağı üretim dosyalarına yazılmadan ayrı tanı sürecinde
gerçek veriye bağlandı: **11 native periyot**, 30 saniyelik gözlemde **15 fiyat /
226 mum olayı**, sıfır sağlayıcı/callback hatası ve sonunda sağlıklı bağlantı.
Bu izole protokol kabulüdür; çalışan uygulamadaki gösterge/alarm kabulü ayrıca
yapılır. Akış kaynağı SHA-256:
`9d2414ae7b64f813f5994071ffe100ed3f0035a964b9aae6d8913871fbe2f321`.

## Kanıtların sınırı

Yerelde **1.995 Python testi / bir atlama**, **307 frontend testi**, 290 Python
kaynağında Ruff, frontend lint ve TypeScript kontrolü geçti. Kaynak regresyonları
sağlayıcının tek seri sınırını ve hesap kilidi tutulurken 50 sembollü listenin
mevcut fiyat aboneliğini paylaşmasını ayrıca doğrular.

Yerel webpack build ve standalone HTTP/WS smoke kabulü de geçti. Gerçek THYAO
akışından 11 TF (10 × 519, aylık 399 mum) ve beş farklı quote kaydedildi.
Bağımsız tam geçmiş Wilder/EMA hesabıyla **beş gösterge × beş quote = 25/25**
karşılaştırma geçti. Bu hesap/protokol kabulüdür; TradingView derleyicisinden
alınmış beş gösterge çıktısı veya üretim preview karşılaştırması değildir.
1.342.660.608 bayt taze yedek hash ile aktarıldı ve sunucu dışında bağımsız
restore/fingerprint karşılaştırması 15 tablo için geçti. İlk aktarım süre
sınırında durdu; doğrulanan prefix üzerinden devam edildi.

İlk TradingView grafik ekranı oturum açmış ve piyasa açık görünüyordu. Sonraki
kontrolde başka etkin oturum nedeniyle bağlantı kesilmesi uyarısı çıktı.
Bu ekranla henüz beş özel göstergenin aynı anda sayısal eşitliği doğrulanmadı.
Bağımsız TradingView bağlayıcısının günlük THYAO mumları da hacmi `null`
döndürdü; tarayıcıdaki toplam hacim alanı, mum hacmi erişiminin kanıtı değildir.

## Tamamlanan yayın ve bağımsız uygulama kabulü

`e11d3d3dadddabf92aba9421b540868984b0ac01`, **07:49:26 UTC / 10:49:26 TSİ**'de
API/frontend/Compose/current'e yayımlandı; bağımsız kabul **07:50:01 UTC**'de
tamamlandı. [Beş CI işi](https://github.com/Rapto0/Rapot/actions/runs/38529725630)
ve [temiz imaj yayını](https://github.com/Rapto0/Rapot/actions/runs/38529762879)
geçti; additive/delta imaj kullanılmadı.

| Kanıt | Değer |
|---|---|
| API imajı | `sha256:4624f9f40afcbe6b4314d6081f1c87cb3e1418f6276d0c830bf16eaa96a41749` |
| Frontend imajı | `sha256:5306c5440faebeaebab319bc2fba25096d47ddcc31072ffa07f0fe955cfb3e08` |
| Yayın makbuzu SHA-256 | `d380034810004e08a9133618d7ca9f3a4dfd1981b0c436f0f66955e4df9dcc01` |
| Bağımsız kabul SHA-256 | `cef5cf45127f30cece29b09d820c4d3a18a7525ca1784a66d85e92e3f2946aaf` |
| Yedek / bağımsız restore | 1.342.660.608 bayt; doğrulama `b540a08fcd9af4f06b1bb9dfc2704c83fbd16982f7207e4e500aebd2c3bd45d8` |

Dört servis sağlıklı/restart0; middleware ve PostgreSQL container kimlikleri
korundu. 15 tablonun bütün satırları ve şeması, tek kullanıcı listesi, üç eski
olay ve özel ortam/şifreli kimlik dosyaları aynı kaldı. Migration, üretime
restore veya yeni geçmiş temizliği yapılmadı. 13 SSR sayfası, 33 statik dosya,
iki yönlendirme, 18 anonim 401, katalog v2 / beş gösterge / 289 input ve iş
oluşturmayan 422 önizleme kabulü geçti. DRY_RUN/trading/live kapalı kaldı.

Yayın kabulü sırasında etkin kural sıfırdı. Normal mum işi/kuyruk **0/0**,
805 fiyat aboneliği ve 550 taze sembol görüldü. Kısa örneklerde kullanılabilir
RAM **292,102–322,527 MiB**, CPU **%33,868 / %13,972**; son boş alan
**4.886.237.184 bayt**. Bu kontroller özel göstergelerde etkin bir kullanıcı
alarmının canlı başarısını kanıtlamaz. Kabul aracı yeni sağlayıcı isteği,
etkin kural, Telegram, AI veya emir üretmedi; otomatik takip kurulmadı.

## Takvim örneklerinin sınırlı doğrulaması

07:38 UTC tarihli tek takvim GET'i 22 olay döndürdü. Tarihi ve saat dilimi
resmî kaynakta açık iki olay ailesi karşılaştırıldı: ABD TÜFE için
[BLS takvimi](https://www.bls.gov/schedule/2026/10_sched_list.htm) 08:30 New York
= 15:30 İstanbul; Huw Pill için [BoE takvimi](https://www.bankofengland.co.uk/events/upcoming-events)
07:00 BST = 09:00 İstanbul. Uygulamanın kaynak saatleri bu iki örnekle eşleşti.
TÜFE'nin altı metriği altı bağımsız saat dilimi testi sayılmaz.

Doviz.com yanıtında olay saat dilimi metadata'sı yoktur; API `source_timezone`
alanı `null`, saatler değişmeden `source_time` olarak gösterilir. Bu iki
eşleşme bütün olayların saat dilimini, yaz/kış saati geçişlerini veya açıklama
anındaki veri gecikmesini doğrulamaz. Fed Bej Kitap ve gilt ihalesinin saatleri
yalnız kaynak dilimi varsayılırsa uyumluydu; ek kesin kabul sayılmadı. Kaynak
önbelleği bir saattir; yeni HTTP alınma zamanı yeni veri anlamına gelmez.

Özel yerel kanıtlar `runtime-data/20261014-live-market/` altında tutulur;
oturum sırları, gerçek veritabanı veya hesap kimlikleri Git'e eklenmez.
Yayın kanıtları `runtime-data/20261014-live-fix-deploy/` içindedir. **Tam BIST
saniyelik kapsamı, 3.000 canlı kural, TradingView derleyicisiyle aynı an
eşitliği ve tam seans kesintisizliği bu kabulde doğrulanmadı.** Kullanıcının
sonradan oluşturduğu büyük listedeki gerçek sorun ve sonraki kaynak düzeltmesi
[16 Ekim kaydında](LIVE_INDICATOR_ACCEPTANCE_2026-10-16.md) ayrıca izlenir.
