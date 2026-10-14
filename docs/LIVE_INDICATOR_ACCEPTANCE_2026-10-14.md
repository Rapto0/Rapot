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

Özel yerel kanıtlar `runtime-data/20261014-live-market/` altında tutulur;
oturum sırları, gerçek veritabanı veya hesap kimlikleri Git'e eklenmez.
Yayın ve uygulama içindeki canlı kabul sonuçları tamamlandıkça bu kayıt
güncellenir. **Tam BIST saniyelik kapsamı, 3.000 canlı kural ve tam seans
kesintisizliği bu aşamada doğrulanmış değildir.**
