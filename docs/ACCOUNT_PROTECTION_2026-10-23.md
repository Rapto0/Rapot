# 23 Ekim TradingView hesap koruması ve alarm düzeltmesi

Kullanıcı grafikte şüpheli etkinlik nedeniyle hesap engeli gördü; yaklaşık yarım
saat sonra açıldığını bildirdi. Dört alarmın tetiklenmesini, CPU %95–98 durumunu
ve DigitalOcean PHP güvenlik e-postasını incelememizi istedi.

## Hesap koruması

[TradingView'in aynı mesaj için açıklaması](https://www.tradingview.com/support/solutions/43000674726-why-is-my-account-banned-due-to-suspicious-activity/)
otomatik veri toplamayı neden olarak belirtir; tekrarlar kalıcı engele varabilir.
Bu hesabın iç güvenlik kaydına erişim yoktur: kesin tetikleyici istek veya IP
kanıtlanmadı. Premium/BIST paketi, bu otomatik erişimin engel riski taşımadığını
göstermez. Çerez değişimi, IP değiştirme veya daha düşük sorgu hızıyla risksiz
olacağı sözü verilmez.

Yeni `BORSAPY_TRADINGVIEW_ENABLED=false` varsayılanı gateway başlangıcında
sabitlenir. TradingView kimlik doğrulama/yenileme, fiyat, mum, tarama ve özel
gösterge akışları kapalıdır. Bağlantı düzenleme/doğrulama veya otomatik retry bu
sınırı kaldıramaz. Bağlantı bilgileri ve kullanıcı kuralları silinmez. Bu kaynağa
bağlı BIST ve özel Pine kripto alarmları **çalışıyor sayılmaz**, açık koruma
mesajıyla veri bekler. Doğrudan Binance kullanan standart kripto ve bağımsız
takvim/araştırma yolları korunur. Eski önbellek taze alarm verisi olarak okunmaz.

Normal BIST mum işleri bu durumda planlanmaz; özel geçmiş ve native akış
hazırlığı da durur. Üretimde yalnız API kontrollü durdurularak otomatik erişim
kesildi; frontend/middleware/PostgreSQL korundu. Eski API imajı otomatik olarak
yeniden başlatılacak rollback hedefi değildir. Yayın kabulü aşağıdadır.

## Dört alarm ve kaynak sorunu

23 Ekim 12:55:45–12:56:58 UTC salt okunur gözleminde dört etkin kural aynı
631 üyeli listeyi izliyor, intrabar/once_per_bar/Telegram açık:

| Kural | Koşul | Bakım öncesi bulgu |
|---|---|---|
| SMI N OY | AL veya SAT, 8 oy | 21 tarihsel başarılı teslim; sonuncusu 22 Ekim 10:00:17 TSİ AAGYO |
| RSI SCORE 27 | HTF RSI Score AL veya SAT, 27/70 | Bugün olay yok; özel hesap hazırlığı bekliyor |
| Haftalık RSI | RSI(14) ≤25 | Bugün olay yok; kısmi hazırlık |
| Günlük RSI | RSI(14) ≤10 | Bugün olay yok; eski veri |

Toplam 24 sent (21 SMI +3 önceki test), 6 not_requested, hata sıfır.
“Hiçbir alarm tetiklenmedi” tarihsel olarak doğru değildir; bugünkü yeni üç
kuralın tetiklenmemiş olması tek başına eşik hatası değildir. Eşikler veya
AL/SAT seçimi değiştirilmedi.

Özel hesap 2/1.262, 630 üyede seed_wait; native geçmiş sayacı 655.871 tamamlanan
istek/655.907 chart. Normal mum işi 1.262, bekleyen 1.204, en eski bekleme yaklaşık
1.146 saniye. Bunlar tek anlık gözlemdir; CPU %95–98 kullanıcının gözlemidir.
API belleği 284,7 MiB, kullanılabilir RAM 256,1 MiB ölçüldü.

Yerel tekrar üretimde, gerçek bir geçmiş sıfırlamasından sonra ham önbellekten
çıkan üye 180 saniyeyi aşan FIFO beklemesi nedeniyle tekrar “revizyon” sayılıyordu.
Bu, native tanık ve hesap hazırlığını yeniden başlatabiliyordu. Düzeltme aynı
üye/yayın belirteci/hesap epoch'unda zaten yapılmış sıfırlamayı hatırlar. Bütün
geçmiş yine karşılaştırılır; gerçek OHLC değişimi, kopma, yeni dönem ve hesap
değişimi korumaları sürer. Gecikmeli yeniden hazırlama testi önce hatayı üretti,
sonra geçti; gerçek revizyon ve tanık bekleme testleri de geçti.

Kanıtlar (özel runtime-data, Git'e alınmaz): `oct23-initial-coverage.json`
SHA256 `6ba5187e4ac69184a3410941b0996024c5ab5db72a7e47d0fb6d9b26e846ee7a`;
`oct23-rules-events.json` SHA256
`6e062b69dfc8a0f38be5f1827d03e531ca66b4816d645eb74f9b398785b79f0c`.
İkisi de `runtime-data/20261021-live-acceptance/` altındadır.

## PHP e-postası

DigitalOcean'dan 21 Ekim 20:46:12 UTC tarihli ilgili e-posta okundu;
DKIM/SPF/DMARC başarılıdır. Metin bütün müşterilere gönderilen genel uyarıdır.
[DigitalOcean duyurusu](https://www.digitalocean.com/blog/critical-php-rce-vulnerabilities-patch-now)
Droplet üzerindeki kullanıcı iş yüklerinin kontrolünü ister.
[PHP duyurusu](https://www.php.net/archive/2026.php#2026-10-21-5) iki CVE için
düzeltmeleri açıklar. 23 Ekim 12:55:35–12:56:02 UTC denetiminde Ubuntu host ve
çalışan dört container içinde PHP paketi/binary/süreç bulunmadı; nginx yalnız
üç localhost upstream'e proxy yapar, PHP/FastCGI yapılandırması yoktur. Bu
sunucuda bu iki CVE için PHP güncellemesi gerekmiyor. Başka DigitalOcean
varlıkları veya kapalı eski imajlar bu denetim kapsamında değildir.

## Yayın kontrolünde bulunan Next.js açıkları

İlk kaynak `45be03c` için CI'nin zorunlu npm denetimi mevcut Next.js 16.3.8
sürümünde iki kritik ve bir yüksek önem dereceli bildirim buldu. Bu kaynak
üretime alınmadı. Next.js ve eşleşen ESLint yapılandırması **16.4.2** sürümüne
yükseltildi; React 19.2.3 ve Sharp 0.35.5 korundu. Tam kilitli bağımlılık
denetimi 469 paket düğümünde sıfır bulgu verdi.

- [Görüntü optimizasyonu RCE](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw): duyurudaki glibc koşulu mevcut Alpine/musl imajıyla eşleşmez; Sharp 0.35.5 düzeltmesi de zaten vardır.
- [Cache Components RCE](https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr): mevcut uygulamada Cache Components veya `use cache` kullanımı bulunmadı.
- [Server Actions DoS](https://github.com/vercel/next.js/security/advisories/GHSA-p3m5-59mp-jv5r): mevcut kaynakta Server Action bulunmadı.

Bunlar istismar veya bildirilen CPU artışının nedeni olduğuna dair kanıt
değildir. Yine de savunmasız sürüm tutulmaz; temiz frontend imajı da yayına
dahil edilir. Kaynak ve üretim kabulü ayrıca kaydedilir.

## Kaynak doğrulaması

Son uygulama kaynağı `bf852c75ac54ef2412a126bf40a464951b640417`:
2.373 Python testi geçti, bir test atlandı; 311 frontend testi geçti.
Arayüz lint/tip/üretim derlemesi ve standalone HTML/statik/API/sağlık/WS
kontrolleri geçti. İlk yerel standalone denemesi başlangıç zaman aşımında
kaldı; aynı kaynak ve çıktı ile tekrar geçti, kesin neden saptanmadı.
Başarısız kayıt silinmedi. Alarm merkezindeki koruma uyarısı kapalı ayrıntı
bölümünün dışında görünür; bu kaynağa bağlı alarmların değerlendirilmediğini
açıkça belirtir. Bu UI kontrolü alarm koşullarını değiştirmez.

Son kaynak [CI 39961029474](https://github.com/Rapto0/Rapot/actions/runs/39961029474)
ve [temiz imaj yayını 39961049736](https://github.com/Rapto0/Rapot/actions/runs/39961049736)
ile izlenir. İlk `45be03c` kaynağının npm bulgusu nedeniyle durduğu
[CI 39958604964](https://github.com/Rapto0/Rapot/actions/runs/39958604964) korunur;
o kaynak üretime alınmadı.

## Üretim yayını ve bağımsız kabul

**23 Ekim 13:36:52 UTC / 16:36:52 TSİ** tarihinde son kaynak API/frontend,
Compose ve current seçimine yayımlandı. **13:39:38–13:40:02 UTC** ayrı kabul
geçti. Beş CI işi ve temiz imaj yayını başarılıdır. Çalışan imajlar:

- API `sha256:f5198c5daaebdf8f77b3acc084189f38c5801be473655bcddd321c7a4fb3b185`
- Frontend `sha256:c7f22ca8e505753e4e524e6105f2389fecbd4cc9366432fa0869110e770352f1`

Dört servis healthy/restart0; middleware/PostgreSQL container kimlikleri ve
özel dosyalar korundu. 15 tablonun şeması/statik verileri, 11 kuralın tanımları
(dördü etkin), tek kullanıcı listesi, 30 eski olay ve 2.524 durum korundu.
Yeni olay yoktur. Veri geri yükleme veya migration uygulanmadı. Taze
1.342.660.608 bayt yedek sunucu dışında 15 tabloyla bağımsız restore edildi.
Yedek kanıtı `e749a8c6e0841074f0a7d0899fe953a8ec9ab467aaa72c5285b489aae4ef97ba`.

İki kabul örneğinde normal ve özel kaynak `provider_paused`: fiyat aboneliği,
planlı geçmiş işi, native WS/seri ve oturum yenileme sıfırdır. 1.262 istenen
geçmiş işi yalnız kullanıcı gereksinimi sayısı olarak tutulur; çalıştırılmaz.
323 API kaynak dosyası ve beş gösterge kataloğu doğrulandı. Web kontrolleri
üç 200 ve bir anonim 401 döndürdü. Çalışan frontend Next16.4.2/Node20.20.2,
Sharp0.35.5/vips8.18.7/rsvg2.63.2 sürümlerini doğruladı.

Yaklaşık **24 saniyelik TradingView kapalı** pencerede API CPU **%29,480**,
API belleği **164,535 →164,574 MiB**, kullanılabilir sunucu RAM'i
**311,809 →297,078 MiB** oldu. Bu ölçüm canlı piyasa yükünde kalıcı CPU/RAM
iyileşmesini, bütün BIST fiyatlarını veya 3.000 alarm kapasitesini doğrulamaz.
Kaynak döngüsü düzeltmesi sentetik regresyonlarla doğrulandı; hesap korumasını
kaldıracak bir canlı TradingView denemesi yapılmadı.

İlk ayrı kabul, Sharp0.35.5'in dışa açmadığı `sharp/package.json` yolunu okuyan
araç varsayımında durdu. Servis arızası değildi. CI ile aynı `s.versions.sharp`
okumasına geçilerek ikinci kabul başarılı oldu; ilk başarısız kanıt korunur,
üretim tekrar yayımlanmadı.

Özel kanıt dizini: `runtime-data/20261023-provider-security-final/`.

| Kanıt | SHA256 |
|---|---|
| `deployment-receipt.json` | `42cda5a25513da7c67fab2f196158512426a07ffa1e48929682f11bfcf24aefd` |
| `acceptance-v2.json` | `ac4ace89d827bb7bbf9c459c4d9a77634f81a59b508d8494d0c83c7ee37bb40f` |
| İlk `acceptance.json` | `aaec153bbfcab20c72e852910438b00fac56fafd5e304bf4c79e3323e1c56b30` |

Yeni sağlayıcı sorgusu, test alarmı, Telegram mesajı, AI üretimi, emir veya
otomatik takip başlatılmadı. Dört BIST alarmının yeniden canlı çalışması için
izin verilen bir veri bağlantısı gerekir. Alternatif olarak TradingView'in
kendi alarm motorundan [resmî webhook](https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/)
teslimi ayrı bir entegrasyon olabilir; mevcut emir middleware'ine otomatik
olarak yönlendirme yapılmadı.

## Anlık alarmları hesap riski olmadan yeniden açma talebi

Kullanıcı dört alarmın durmasını istemedi; borsapy ile anlık BIST verisinin
TradingView hesabını riske atmadan yeniden kullanılmasını istedi. Kurulu
borsapy0.11.0 kaynakları ve güncel upstream README salt okunur incelendi.
`Ticker.info/fast_info` fiyatı, `Ticker.history` hisse mumları ve
`TradingViewStream` akışı TradingView'e bağlıdır. Bu yollar için hazır bir
TradingView dışı BIST canlı veri sağlayıcısı bulunmadı.
[Upstream açıklaması](https://github.com/saidsurucu/borsapy#ger%C3%A7ek-zamanl%C4%B1-veri-ak%C4%B1%C5%9F%C4%B1-tradingview-streaming)
anonim erişimi yaklaşık 15 dakika gecikmeli, gerçek zamanlı yolu hesap/veri
paketine bağlı tanımlar.

İç `IsYatirimProvider.get_realtime_quote()` yöntemi v0.5.1'den beri deprecated,
HTTP sorgusu ve 60 saniye önbelleklidir. Eksik kaynak zamanını yerel saatle
doldurduğundan taze fiyat tanığı olarak kullanılamaz. Diğer eski tarihçe yolu
endeks/günlük tek fiyat verisidir; dört alarmın gerçek hisse OHLC/native dönem
gereksinimlerini karşılamaz. [İş Yatırım'ın açıklaması](https://www.isyatirim.com.tr/tr-tr/analiz/Sayfalar/default.aspx)
BIST verisini en az 15 dakika gecikmeli belirtir. Gecikmeli veriyle anlık alarm
çalışıyormuş gibi gösterilmez; oturum veya IP değiştirme çözüm kabul edilmedi.

Mevcut ücretli hesabı kullanarak resmî alarm/webhook yolu alternatif olabilir;
hesaplama TradingView'de çalışır, site bildirim alır. Bu, bütün hesapların
sunucuda kalması şartını karşılamaz. Güncel [plan tablosunda](https://www.tradingview.com/pricing/)
Premium iki izleme listesi alarmı sunar: dört koşulun birlikte bir Pine
göstergesine taşınması, bağımsız günlük/haftalık tekrar sıklıkları ve hesap
eşitliği ayrıca doğrulanmadan dört hazır alarmın doğrudan taşınacağı söylenmez.
Sunucuda hesaplamayı koruyan yol ayrı, izinli bir BIST fiyat/mum API'sidir;
mevcut Osmanlı ekran/veri hakkı tek başına API erişimi kanıtı değildir.

Bu araştırmada üretim yapılandırması değişmedi, yeni piyasa sorgusu veya
alarm/Telegram gönderimi yapılmadı. Dört kuralın etkin tanımları korunuyor;
TradingView kaynağı kapalı olduğu için canlı değerlendirme yeniden açılmadı.

## Kontrollü yeniden açma talimatı ve kaynak değişikliği

Kullanıcı daha sonra borsapy ile, hesabını **fazla riske atmadan** anlık BIST
verisinin ve mevcut dört alarmın sürmesini açıkça istedi. Bu talimat kontrollü
yeniden açmayı kapsar; sıfır hesap riski garantisi değildir. TradingView'in
otomatik veri toplama hakkındaki açıklaması geçerliliğini korur. İstek hızını
düşürmek, erişimin sağlayıcı tarafından onaylandığı anlamına gelmez.

Yeni kaynak varsayılan kapalı ayarı korur; üretimde yalnız API için açık bir
ayar gerekir. Ortak istek bütçesi geçmiş, bağlantı ve yeni abonelik açılışlarını
sınırlar; gelen fiyatların hesaplanmasına bekleme süresi eklemez. Açık hesap
kısıtlaması veya sağlayıcının belirli erişim/hız retleri bütün TradingView
taşımalarını kapatan bir korumayı tetikler. Ayrı kalıcı işaret süreç yeniden
başlatıldığında da korunur; çerez düzenleme veya oturum doğrulama bu işareti
kaldırmaz. Yerel iş kuyruğu doluluğu ya da genel ağ zaman aşımı hesap yasağı
olarak sınıflandırılmaz. IP/hesap değiştirme veya engel aşma uygulanmaz.

Mevcut özel göstergelerin native 1D/1W geçmişi, aynı üyelerin intrabar standart
RSI koşullarına da başlangıç sağlar. Standart RSI kendi `ta` EWM başlangıcını
ve son 500 mumunu korur; Pine RSI değeriyle değiştirilmez. Her yeni fiyat aynı
native gözlem üzerinde değerlendirilir. Normal günlük/haftalık RSI için
yinelenen geçmiş işleri kalkar; başka gösterge, kapanış kuralı veya açık grafik
gereksinimi varsa ilgili geçmiş işi korunur. Desteklenmeyen/karma üyeler normal
yolda kalır. Native dönem sınırı, gerçek geçmiş revizyonu, kopma, oturum ve
tazelik kontrolleri devam eder; hazır olmayan girdi alarm üretmez.

Bu bölüm kaynak davranışını açıklar. Yeni kaynağın üretim yayını ve canlı kabulü
aşağıda ayrı kaydedilmedikçe, önceki `bf852c75` kapalı üretim durumu geçerlidir.

Ortak bütçe saniyede dört **iş kabulü**, en fazla dört birikmiş kabul hakkı ve
oturum doğrulamaları arasında en az 300 saniyedir. `requests_admitted` sayacı
bağlantı, abonelik, chart ve geçmiş/araştırma çağrılarının başlangıcını sayar;
ham WebSocket mesajı veya sağlayıcının iç işlem sayısı değildir. Bir chart
başlangıcı birkaç protokol mesajı gönderir. Heartbeat yanıtları ve gelen fiyat
mesajları bu bütçeyle bekletilmez. 631 fiyat aboneliği ilk açılışta hesap kilidi
tutulmadan kademeli eklenir; diğer işler de aynı bütçeyi paylaşır. Bu nedenle
ilk hazırlık, kesintisiz hazır durumdaki fiyat değerlendirmesinden daha uzundur.

Kalıcı işaret, şifreli kimlik dosyasıyla aynı dizindeki
`tradingview-protection.json` dosyasıdır; yalnız sabit neden, sürüm ve UTC tarih
tutar. Atomik yazma başarısız olursa çalışan süreç yine kapanır ve
`policy_storage_error` bildirir; dosya hiç yazılamadıysa yeniden başlatmada
kalıcılık garanti edilmez. Bozuk mevcut dosya güvenli biçimde kapalı kalır.
Genel `auth_error`, HTTP 401/403/429 ve açık hesap/hız retleri durdurur;
tek sembolün `permission_denied` yanıtı bütün hesabın yasaklandığı sayılmaz.
33 yeni çevrimdışı test; kalıcı işareti, yeniden açılmama davranışını, ortak
bütçeyi, hassas veri taşımayan hata sınıflamasını, tüm gateway taşıma türlerinin
kapanmasını ve native fiyat/geçmiş callback'lerini doğruladı. Önceki 198 ilgili
test de geçti. Bunlar gerçek sağlayıcı izni veya canlı seans kapasitesi kanıtı
değildir; bu doğrulamalarda dış sağlayıcıya bağlanılmadı.

Bağımsız incelemenin bulduğu kapatma/abonelik yarışına ek koruma uygulanır:
bütçede bekleyen yeni bağlantı, kapatılmış havuza kaydedilemez; geç açılan
soket kimlik veya abonelik mesajı göndermeden kapanır. Önbellek okuması
sırasında durdurma oluşursa sonuç yayınlanmaz. Açık `unauthorized_user_token`
sonucu kalıcı kimlik reddi sayılır; boş token genel doğrulama hatası kalır.
Sekiz ek çevrimdışı senaryoyla politika testleri 41'e çıktı; bu düzeltmenin
140 ilgili testi geçti. Canlı sağlayıcı denemesi yapılmadı.

## Kontrollü sürümün üretim yayını ve ilk kabulü

Son uygulama kaynağı **`21e39512e13c2665acb24551248f56d1d4065319`**,
**23 Ekim 15:20:46 UTC / 18:20:46 TSİ** tarihinde yalnız API'ye yayımlandı.
Compose/current bu kaynağa geçti; frontend `bf852c75` imajı ve container'ı,
middleware/PostgreSQL container'ları korundu. Yeni API imajı
`sha256:e776c5a1d25fb61defc0c8ef7e49739b4b329a6204316ba895f99819043e9afb`.
`BORSAPY_TRADINGVIEW_ENABLED=true` yalnız API Compose override'ına eklendi;
özel ortam ve şifreli kimlik dosyaları değişmedi. Sağlayıcı koruma dosyası
silinmedi veya sıfırlanmadı. Gereken geri dönüş hedefi kapalı `bf852c75` API'si
ve önceki override'dır; eski korumasız sürüm otomatik açılmaz.

Yerel son tam tur **2.460 Python testi başarılı/bir atlama**; aynı kaynakta
Linux CI de **2.460 başarılı/bir atlama** verdi. 323 izlenen Python kaynağında
Ruff geçti. Frontend CI 311 testi, tip/lint/derleme/standalone ve bağımlılık
kontrolünü geçti; bu tur frontend yeniden yayımlanmadı. Beş kaynak işi
[CI39974969161](https://github.com/Rapto0/Rapot/actions/runs/39974969161), temiz
imaj [publication39975043324](https://github.com/Rapto0/Rapot/actions/runs/39975043324)
başarılı. Önceki tam yerel turdaki bir hata, eski test sağlayıcı fabrikasının
yeni keyword argümanlarını kabul etmemesiydi; fixture düzeltildikten sonra tam
tur yeniden geçti. Başarısız kayıt saklandı; ara kaynak üretime alınmadı.

Taze **1.342.660.608 bayt** SQLite yedeği sunucu dışında bağımsız restore edilip
15 tabloyla doğrulandı. Restore kanıtı
`2fcb6d1dbfab7e3dfc670880a450e4b7eb8f063b29b364813df62df32c48b1f4`.
15 tablo şeması/statik veriler, 11 kuralın tanımları, tek631 üyeli liste,
30 eski olay ve2.524 durum korundu. Veri geri yükleme/migration yapılmadı.
Dört etkin kuralın koşulları ve Telegram tercihleri aynı kaldı:

| Kural | Mevcut koşul |
|---|---|
| SMI Oy | SMI N OY `any_signal=1`; AL/SAT için8 oy |
| RSI SCORE27 | HTF RSI Score `any_signal=1`;27/70 eşikleri |
| RSI1HAFTALIK25 | Haftalık standart RSI14≤25 |
| RSI GÜNLÜK10 | Günlük standart RSI14≤10 |

Hepsi631 üyeli aynı izleme listesinde, intrabar ve `once_per_bar` politikasında
kaldı. İşlem emri yolu açılmadı. Geçmişte kaçırılmış olabilecek sinyallerden
geriye dönük Telegram bildirimi üretilmedi.

**15:21:55–15:22:21 UTC** ayrı kabulde dört servis healthy/restart0,328 çalışan
API kaynak dosyası ve v2/beş gösterge kataloğu doğrulandı. Üç web okuması200,
anonim özel API401 döndürdü. Bağlantı `authenticated`, koruma `blocked=false`
idi. Dört native bağlantıda fiziksel abonelik136→191 ilerledi;6.310 mantıksal
native talep kabul edildi. Ortak kabul sayacı284→385 artışı4/saniye bütçesine
uydu. Normal yinelenen geçmiş işi/kuyruğu0/0, standart RSI talebi1.262 idi.
İlk hazırlıkta derlenmiş hesap/RSIseed henüz0'dı; bu durum hazır alarm hesabı
olarak raporlanmaz. Normal fiyat abonelik sayacı,631 üyenin kademeli eklenmesi
tamamlanmadan atomik olarak yayımlanmadığından bu erken örneklerde0 görünür.

Yaklaşık25 saniyede API CPU **%38,046**, API belleği **176,586–179,547 MiB**,
kullanılabilir sunucu RAM'i **298,817–298,906 MiB** oldu. Bunlar soğuk başlangıç
ve seans dışı ölçümlerdir; gün boyu yük,631 taze fiyat, dört alarmın canlı
tetiklenmesi veya kalıcı kaynak kazanımı kabulü değildir. `live_rejected`
sayacı eski/geçersiz/sırası geriye giden ya da yayın sırasında kaynak değişen
fiyatları içerir; sağlayıcı hesap yasağı sayacı değildir.

Yeni test alarmı, Telegram testi, AI üretimi, emir veya otomatik takip yoktur.
Mevcut alarm motorunun kullanıcıca yetkilendirilmiş normal veri akışı açıktır;
bu kabul aracı yalnız yerel durum okur ve ayrı sağlayıcı denemesi başlatmaz.

Özel kanıt dizini: `runtime-data/20261023-controlled-resume-api/`.
Yayın receipt SHA256:
`4eb6fa845025297d20bd0928d0bbf533a50f96536424c0511d5f1fcb20a75313`.
Ayrı kabul SHA256:
`abf9ea2721ea85653fb5bcca37d0f8859c307a1a5018eb80633f58871aa904bc`.

## Yayın sonrası son pasif hazırlık gözlemi

**15:27:17–15:27:40 UTC / 18:27:17–18:27:40 TSİ** iki kısa yerel durum okumasında
fiyat aboneliği ve izlenen semboller **631/631** oldu. Oturum doğrulanmış,
koruma engelsiz kaldı. Native kalıcı günlük abonelik631; mantıksal talep6.310,
fiziksel chart sayısı681→684'tü. Derlenmiş özel hesaplar **22→30**, standart
RSI başlangıçları **22→30**, native üst periyot tanıkları **186→238** ilerledi.
Tek paylaşılan geçmiş bağlantısında tamamlanmış istek110→150, tamamlanmış
on-chart grup11→15 oldu; başarısız istek/grup, native ret ve bekleyen yeniden
deneme0. Oturum yenileme hatası yok; bu kısa süre normal1800 saniyelik token
yenilemesini sınamaz. Bütçe sayacı1.569→1.663 artışı ortak4/saniye sınırına uydu.

Normal mum işi/kuyruğu **0/0**, canlı kuyruk/taşma **0/0**, yeniden bağlantı
denemesi/kopma **0/0** kaldı. API CPU **%37,828**, API belleği
**194,836–195,480 MiB**, kullanılabilir RAM **296,703–307,871 MiB** ölçüldü.
Bu iki kısa ölçüm %95–98 sürekli yükün kalıcı olarak çözüldüğü iddiası değildir.

Seans dışında bütün631 kaynak fiyatı eskilik sınırını aşıyordu. Canlı işlenen
fiyat/sinyal0; özel kuralların1.262 üye-hesap sonucu hâlâ hazır/eski durumunu
bekliyordu. Başlangıçlar ilerliyor ancak tam liste hazırlığı bitmiş sayılmaz.
Normal servis çalışır durumda bırakıldı; yeni takip/timer veya sağlayıcıya
ayrı test sorgusu açılmadı. Son pasif kanıt `passive-final.json` SHA256:
`9c740a1ae213c8272a86e47989a1889229cd601cd96036300452ab63a8509732`.
