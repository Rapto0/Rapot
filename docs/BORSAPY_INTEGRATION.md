# Borsapy araştırma ve kişisel veri altyapısı

4 Ekim 2026. Kullanıcı, mevcut TradingView Premium ve BIST gerçek zamanlı veri
paketiyle kişisel Rapot sitesinde borsapy README'sindeki özellik ailelerini
istedi. Sonraki kapsam grafik, dashboard, izleme listesi, scanner ve ekonomik
takvimin ortak kişisel veri altyapısını da içerir. Canlı piyasa kabulü
piyasa açıkken yapılmak üzere ertelendi. Sonraki bağlantı yardım talimatı,
kayıtlı TradingView oturumunun doğrulanmasını ayrıca yetkilendirdi; bu hesap
kabulü `876f3f3` yayını sonrasında tamamlandı. 7 Ekim canlı piyasa kabulü yeniden
seçildi; beş sembollü fiyat örneklemi, THYAO açık mum karşılaştırması ve üç Rapot
alarm kategorisinin Telegram teslimi yapıldı. Tam kapsam/hacim kabulü açık;
[güncel kanıt ve yayın durumu](LIVE_MARKET_ACCEPTANCE_2026-10-07.md).

Kaynak: borsapy 0.11.0,
[`a9e41ae398fc2d25b35f864a5c7028d5f98862c3`](https://github.com/saidsurucu/borsapy/tree/a9e41ae398fc2d25b35f864a5c7028d5f98862c3).
`borsapy[twitter]==0.11.0` ve geliştirme/CI bağımlılıkları kilitlidir. Kurulan
paketin stream, ticker, technical, TradingView provider ve fund dosyaları,
satır sonları normalleştirilince incelenen Git kaynağıyla aynıdır.

## Ekran ve kapsam

`/research` yalnız yönetici oturumuyla kullanılır. Katalogdaki işlem; etiketli
form, kaynak, alım zamanı, uyarı, tablo, CSV ve uygun işlemlerde mum grafiği üretir.
Yalnız açıkça tanımlı işlemler ve sınırlı girdiler kabul edilir; Python konsolu
veya sağlayıcının bütün metotlarına serbest erişim değildir.

| README'deki özellik ailesi | Web karşılığı |
|---|---|
| TradingViewStream | Hesap bağlantısı, fiyat/mum akışı, uzak Pine gösterge kimliği |
| Backtest Engine | Sabit stratejili deneysel borsapy backtest |
| Replay Mode | Mum grafiğinde oynat/duraklat/adım/hız |
| Search | Piyasa türüne göre sembol arama |
| TA Signals | TradingView teknik alış/satış/nötr özeti |
| Heikin Ashi | Standart mumlardan sentetik grafik |
| ETF Holders | Hissede ETF sahipliği tablosu |
| Portfolio | Çoklu varlıklarla sanal portföy ve risk analizi |
| FX | Döviz/emtia, geçmiş ve banka kurları |
| Crypto | BtcTurk çiftleri ve verileri; Binance emir sistemi ayrıdır |
| Fund | TEFAS bilgi/geçmiş/dağılım/tarama/karşılaştırma/stopaj |
| Inflation | Enflasyon serileri ve hesaplayıcı |
| EVDS | Katalog, arama ve anahtarlı zaman serileri |
| VIOP | Vadeli/opsiyon verileri, kontrat arama ve yetkiye bağlı akış |
| Bond | Devlet tahvili faizleri ve risksiz oran |
| TCMB | Politika/gecelik/LON faizleri ve geçmiş |
| Eurobond | Devlet eurobondları |
| EconomicCalendar | Ülke/önem filtreli ekonomik takvim |
| Screener | Temel tarama, ölçütler ve teknik koşullar |
| Teknik Analiz | OHLCV üzerinde borsapy yerel göstergeleri |
| Twitter/X | Ayrı X oturumu tanımlandıktan sonra sınırlı arama |
| KAP | Bildirimler ve şirket takvimi |

Şirket finansalları ve temettü/sermaye işlemleri de sunulur. Her aile için web
yüzeyi bulunması, bütün sağlayıcıların canlı kabul edildiği anlamına gelmez.

İlk araştırma yayınının çevrimdışı kabulü: CI'da 1.204 Python testi (bir performans testi atlandı);
227 frontend testi, lint/typecheck, build ve standalone proxy kontrolü geçti.
Sentetik tarayıcı oturumunda katalog/formlar, kaydetme, replay, akış kontrolleri,
özel grafik kaynağı, bağlantı sekmesi ve 320 px görünüm sınandı. Sağlayıcı,
TradingView oturumu, gerçek fiyat gecikmesi veya bildirim teslimi sınanmadı.
Linux runtime yayın işi, 98 mevcut paketin sürüm/dosya hash'lerini koruyup 22
ek paketi, native importları ve ağsız uygulama kontrolünü doğruladı.

4 Ekim 06:21 UTC'de `4b15335` kaynağı yalnız API/frontend için üretime alındı.
Salt okunur üretim kabulünde yönetici kataloğu 51 işlem/9 grup, kurulu borsapy
0.11.0, özel endpointlerin erişim/cache sınırları, üç HTTPS sayfası ve 17 statik
dosya doğrulandı. Eski 10 tablonun şeması korundu; araştırma tablosu ve indeksi
eklendi. TradingView/EVDS/X bağlantıları henüz yapılandırılmamış; gerçek hesap,
fiyat/mum akışı ve piyasa kabulü erteli. Ayrıntılı kaynak/imaj, yedek, temizlik ve
kapasite kanıtları [devam planındadır](RAPOT_DEVAM_PLANI.md#son-üretim-ve-yayın-kanıtları).

Aşağıdaki site geneli özel veri ve varsayılan kaynak değişiklikleri `ab18dc4`
ile 4 Ekim 08:02:14 UTC'de API/bot/frontend'e yayımlandı.
[CI 37187054987](https://github.com/Rapto0/Rapot/actions/runs/37187054987)
ve [imaj yayını 37187060992](https://github.com/Rapto0/Rapot/actions/runs/37187060992)
geçti: 1.385 Python testi, bir isteğe bağlı atlama/üç uyarı ve 250 frontend testi.
Kaynak imajı önceki `b9695f5f…` runtime'ının 120 paket dosya envanterini ve tüm
katman önekini korur; API/bot aynı imajı `BORSAPY_USE_FOR_BIST=true` ile kullanır.
08:02:47 UTC ayrı salt okunur kabulde 45 anonim özel GET'in 401/no-store sınırı,
Flask erişim ayrımı, WS kimlik doğrulaması, beş SSR sayfası, 22 JS/CSS dosyası ve
11 değişmeyen tablo şeması doğrulandı. Middleware, PostgreSQL, özel ayarlar,
Nginx ve Compose/current kaynağı korundu. Bu kabulde TradingView/EVDS/X bağlantıları
tanımsızdı; hesap kabulü daha sonra aşağıdaki düzeltmeyle tamamlandı. Normal başlangıç
trafiği ölçülmedi. Yedek, kapasite ve imaj kimliklerinin kanıtları devam planında tutulur.

4 Ekim 09:06:07 UTC'de `876f3f37b9d56624d17c46ab924684de559c5530`
bağlantı düzeltmesi API/bot/frontend'e yayımlandı.
[CI 37190406726](https://github.com/Rapto0/Rapot/actions/runs/37190406726)
beş iş, [imaj yayını 37190433460](https://github.com/Rapto0/Rapot/actions/runs/37190433460)
iki iş başarılı; API delta işi atlandı. Yerelde 1.421 Python testi (bir atlama/üç uyarı),
262 Python dosyasında lint/format ve 256 frontend testi/lint/typecheck/build/standalone
geçti. 09:08:31 UTC ayrı salt okunur kabul beş sağlıklı servisi, API/bot içinde
30 canonical dosya/120 paketi, 51 işlem/9 grubu, 45 yerel ve 45 dış anonim
401/no-store yanıtını, beş HTTPS sayfasını, 22 statik dosyayı ve değişmeyen
11 tablo şemasını doğruladı. Son boş alan 696.680.448 bayt; 528 MiB rezerv korundu.
Yeni temizlik, migration veya yedek alma işlemi yapılmadı. Exact imajlar ve kabul
hash'leri [devam planındadır](RAPOT_DEVAM_PLANI.md#son-üretim-ve-yayın-kanıtları).

Python güvenlik işi report-only sözleşmesini korur: 134 pakette 5 etkilenen
paket / 16 ham bulgu (12 benzersiz bildirim) raporlandı. 22 ek paketin tamamı
kapsamdadır ve bunlarda bulgu yoktur. Etkilenen eski pinler `anyio 4.12.1`,
`PyJWT 2.14.0`, `soupsieve 2.8.4`, `urllib3 2.7.0` ve yalnız geliştirmedeki
`virtualenv 21.7.8`'dir. Bunlar önceki sıfır bulgulu kabulden sonra yayımlanan
bildirimlerdir; önceden kabul edilmiş risk olarak sınıflanmaz.
Önerilen düzeltme alt sınırları sırasıyla 4.14.2, 2.15.0, 2.9.0, 2.8.0 ve
21.7.13'tür. Runtime pinlerinin yenilenmesi, mevcut 98 paketi koruyan ek imaj
yolundan ayrı test edilmiş taban imaj çalışması gerektirir. Sabit ASCII sağlayıcı
hedefleri, doğrulanan HS256 ve dış CSS seçicisi sunulmaması bazı önkoşulları
sınırlar; özellikle dış HTTP istemcisinin tam erişilemezliği kanıtlanmadı.
[AnyIO](https://github.com/advisories/GHSA-82r6-8w77-94w6),
[PyJWT](https://github.com/advisories/GHSA-42vr-xj54-vc7v) ve
[urllib3](https://github.com/advisories/GHSA-vxq7-64xx-v4gw) bildirimleri.

`/chart` BIST kaynağı olarak Borsapy/TradingView kullanır. Özel
`/borsapy/candles/{symbol}` ve `/borsapy/stream` kullanılır. Göstergeler mevcut
TypeScript hesaplayıcısıyla çalışır; grafik eski sağlayıcıya otomatik dönmez.
Kripto grafiği Binance kaynağını korur. Koşulsuz “Canlı” etiketi kullanılmaz.
Araştırmadaki borsapy göstergeleriyle mevcut
COMBO/HUNTER motorlarının eşdeğerliği iddia edilmez.

## TradingView oturum yönlendirmesi

4 Ekim bağlantı incelemesinde kullanıcının kaydettiği oturumun geçerli olduğu
doğrulandı. Sunucudan `www.tradingview.com/` isteği 302 ile
`tr.tradingview.com/` adresine yönlendiriliyordu. borsapy 0.11.0 çerezleri
elle `Cookie` başlığında gönderir; httpx otomatik yönlendirmede bu başlığı
kaldırıp çerez deposundan yeniden kurar. Session yöntemi depoyu doldurmadığı
için ikinci istek oturumsuz kalır. Aynı yönlendirmeyi izin verilen hedefe
çerezleri koruyarak izleyen sınırlı tanı çağrısı 200 ve kullanılabilir token
buldu; çerez/token/HTML veya profil bilgisi rapora alınmadı. Bu gözlem
gerçek zamanlı fiyat, BIST paket yetkisi veya piyasa kabulü değildir.

`infrastructure.providers.tradingview_session_auth`, hesap kilidi altında
yalnız doğrulama süresince sağlayıcının HTTP istemcisine geçici bir adaptör
uygular. borsapy'nin HTML ayrıştırıcısı ve oturum deposu korunur; paket dosyası
değiştirilmez. En çok dört GET, yalnız HTTPS `www.tradingview.com`,
`tr.tradingview.com` ve `tradingview.com` kök adresleri kabul edilir. Port,
kullanıcı bilgisi, sorgu, fragment veya başka yol/hedef taşıyan yönlendirme,
ikinci isteğe sır gönderilmeden reddedilir. Yanıt en çok 8 MiB'dir; her istek
ve parçada 30 saniyelik zaman bütçesi denetlenir, HTTP faz timeout'u en çok
10 saniyedir. Bu kontroller çalışan ağ çağrısı için sert bir toplam süre
garantisi değildir. Başarı ve hatada özgün istemci ile önceki çerez deposu
geri yüklenir; geçici yanıttaki çerezler sonraki işlemlere bırakılmaz.

Bağlantı ekranında kaydetme, doğrulama başarısız olsa bile sunucuda tamamlanabilir.
Başarılı ve başarısız işlemlerden sonra ortak bağlantı durumu yenilenir;
“Kayıtlı · doğrulanmadı” ile “Yapılandırılmadı” ayrılır. Durum alınamıyorsa eski
başarı kartı gösterilmez. Oturum kapanmış, değişmiş veya süresi dolmuşsa eski
işlemin sonucu yeni oturuma taşınmaz. Depolama hatasında açık onayla kaydı
kaldırma yolu korunur.

Düzeltme üretime alındıktan sonra mevcut şifreli kayıtla gerçek site üzerindeki
**Oturumu doğrula** eylemi **Oturum doğrulandı** sonucunu verdi. Kullanıcının
kayıtlı bilgileri geçerliydi; TradingView bilgileri yeniden kaydedilmedi.
Sır içermeyen UI/API kanıtı `runtime-data/borsapy-auth-fix-deploy/account-ui-acceptance.json`,
ekran kanıtı `runtime-data/borsapy-auth-connected.jpg` içinde, Git dışında tutulur.
Bu hesap kabulü gecikmesiz BIST veri yetkisi, fiyat/mum veya bölünme doğrulaması
değildir; `realtime_verified=false` korunur.

## Kalıcılık ve erişim

- Araştırma ve sanal portföy girdileri ana SQLite `research_workspaces`
  tablosunda kullanıcıya bağlı saklanır. Kullanıcı başına en fazla 100 kayıt;
  sonuçlar ve kimlikler bu tabloda tutulmaz. `init_db()` tabloyu ekler.
- TradingView session/session_sign, isteğe bağlı EVDS ve X anahtarları yalnız
  yönetici POST'uyla alınır; yanıtta, tarayıcı depolamasında veya Git'te tutulmaz.
- Kimlikler, mevcut en az 32 karakter JWT anahtarından HKDF türetilmiş anahtar
  ve Fernet ile şifrelenir. Varsayılan ana DB yanında `.borsapy/credentials.enc`;
  `BORSAPY_CREDENTIALS_PATH` ile değişebilir. Linux dizin/dosya izinleri 0700/0600.
  JWT değişirse bağlantı yeniden tanımlanır. Dosya kalıcı özel volume'da olmalı.
- API'de kimlik değişince ayrı bot süreci sonraki sağlayıcı çağrısında dosya
  revizyonunu yeniden okur; aktif akışlar da en geç kiralama kontrolünde yenilenir.
  Süresi dolan TradingView oturumu, bağımsız TEFAS/EVDS gibi sorguları engellemez;
  okunamayan şifreli dosyada bütün kimlikli yollar durur.
- `.borsapy/` Git ve Docker build context'inden çıkarılır. Gizli yedekler genel
  rapora veya Git'e alınmaz. Windows'ta ciphertext JWT anahtarından ayrı tutulur.
- Kişisel dashboard HTTP yolları, `/borsapy/*`, piyasa verisi, sinyaller,
  kayıtlı analizler ve takvim dahil yönetici ister; yanıtlar ve hatalar
  `private, no-store` taşır. Ana API kök/health, auth ve belge yolları global
  sınırın dışındadır; `/auth/me` kendi JWT doğrulamasını korur. Sağlayıcı
  oturumu ile Rapot JWT oturumu ayrıdır.
- Ayrı Flask bot proxy'si de bu sınırı korur: sinyal, istatistik ve isteğe bağlı
  Prometheus yolları admin ister. Başlıksız `/status` yalnız DB/yerel lifecycle
  döndürür; ayrıntılı sayaç/hata bilgisi admin ister. Başlığı geçersiz bir istek
  anonim yanıta düşmez. Cevaplar `private, no-store` ve `Vary: Authorization` taşır.
- Backend WS ilk beş saniyede `{type: "auth", token}` mesajı, SSE Bearer başlığı
  ister. WS `authenticated` yanıtından önce abonelik/veri akışı başlamaz.
  URL'de token kabul edilmez. JWT süresi ve erişim veri tesliminde yeniden
  denetlenir; 4401/4403 sonrası istemci yeniden bağlanmayı durdurup özel veriyi temizler.

## Dashboard, izleme listesi ve takvim

`borsapy_market_data.py` dashboard/izleme listesi için ortak özel read-model'dir.
`/borsapy/market/*` ve ana piyasa endpointlerinin varsayılan `source=borsapy`
yolu bunu kullanır. Eski piyasa endpointlerinde `source=legacy` açık seçimi
korunur; ikisi de yöneticiye özeldir. Kimlikli fiyatlar eski SQLite `price_cache`
ile karıştırılmaz. Kaynak, sağlayıcı zamanı, alınma zamanı ve
bekleniyor/bayat/hata/kimlik gerekli durumları ayrı taşınır; eksik değişim sıfır
gibi gösterilmez. `realtime_verified=false` canlı kabul sınırını korur.

Dashboard fiyatları tek ortak TradingView quote bağlantısında en fazla 200 etkin
sembol, istek başına 50 sembolle sınırlıdır. Kullanılmayan abonelikler varsayılan
120 saniyelik kiralama süresinden sonra bırakılır. Günlük geçmişten 7/30 günlük metrik ve mini grafik hazırlayan
tek worker, 100 bekleyen iş ve en fazla 200 bellek kaydı kullanır. Başarılı
geçmişin TTL'i 300 saniye, hatalı sonucun yeniden deneme süresi 60 saniyedir.
Geçmiş hazırlanırken fiyat yanıtı bekleniyor metadata'sıyla dönebilir; eksik
geçmişten getiri uydurulmaz. BIST geçmiş önbelleği kimlik revizyonuna bağlıdır.

Binance sembolleri, kripto grafik/alarmları ve mevcut Binance fiyat akışı korunur.
BtcTurk araştırması bunların yerine geçirilmez. Global endeks/döviz/emtia
eşlemeleri açık sembol/borsa listesi kullanır; tanımsız araç desteklenmiyor
olarak döner. Spot yerine vadeli kontratla sessiz ikame yapılmaz.

`/scanner`, mevcut COMBO/HUNTER sinyal geçmişinin yanında Borsapy temel/teknik
tarama yüzeylerini sunar. Bu araştırma taramaları mevcut bot stratejilerini
ve ikinci kaynak teyidini değiştirmez.

`/calendar` Borsapy/Doviz.com `EconomicCalendar` kaynağını kullanır; Finnhub
veya TradingView kimliği istemez, Rapot yönetici oturumu ister. İstanbul gününe
göre son 7 gün/gelecek 30 gün içinde en fazla 31 gün ve üç ülke seçilebilir.
Tek sağlayıcı işi ve 16 girişli bellek önbelleği vardır. Kaynak bir saatlik
önbellek uyguladığından alım zamanı yeni upstream güncelleme kanıtı değildir.
Yenileme başarısızken sınırlı eski yanıt açık `stale` uyarısıyla gösterilebilir.
Kaynak saat dilimi doğrulanmadığından olayın tarih/saat metni UTC veya İstanbul
zamanına çevrilmez; boş sonuç olay olmadığına dair kesin kanıt değildir.

## Akış ve hesaplayıcı

Upstream'in çoklu chart eşlemesindeki sabit seri kimliği nedeniyle her
sembol/periyot/gösterge ayrı bağlantı kullanır. `BORSAPY_MAX_STREAMS` varsayılan 3,
en fazla 5; `BORSAPY_STREAM_IDLE_SECONDS` varsayılan 120. Kullanılmayan grafik
aboneliği kapanır; bu kiralar sunucu alarm döngüsünü durdurmaz. Mum tamponu sınırlı.
Sekmeler ayrı abone kimliği kullanır; bir sekmeyi kapatmak diğer sekmenin ortak
akışını kapatmaz. VİOP veri hakkı ayrıca doğrulanır; BIST paketi bunu kanıtlamaz.

Kimlikli sağlayıcı callback'leri ortak hesap kilidi altında sıralanır. Yeni işin
kilit beklemesi bir saniyeyle sınırlıdır; mevcut fiyat/grafik tamponu, hesap
revizyonu ve epoch değişmemişse güvenli okuma yolundan dönebilir. Bu bekleme
sınırı başlamış ağ çağrısını iptal etmez ve sağlayıcı yanıt süresi garantisi değildir.

7 Ekim düzeltmesinde arka plan alarm geçmişi bu uzun kilitten ayrılır: en fazla
iki isteğe özel sağlayıcı, kısa kilit altında yakalanan kimliği kullanır; sonuç
öncesi revizyon/epoch/token tekrar kontrol edilir. Doğal hacim alanı ayrıca
doğrulanır; borsapy'nin eksik hacmi sıfıra çevirmesi BIST hacim alarmına veri
sağlamaz. Grafik yenileme hatasında mevcut seçimin geçerli akış mumları varsa
grafik görünür kalır ve hata ayrı uyarı olarak gösterilir.

Kimlikli istek token yokken anonim veriye düşmez. Oturumun süresiz geçerli olması
veya bütün mesajların eksiksiz teslimi garanti edilmez. Sağlayıcının işlem zamanı
ve yerel alınma zamanı ayrıdır. `realtime_verified` canlı kabulden önce false;
açık bağlantı tek başına anlık veri kanıtı değildir.

Pine alanı TradingView üzerinde erişilebilen gösterge kimliğidir; serbest Pine
veya Python kaynak metni çalıştırmaz. Deneysel borsapy backtest aynı mum kapanışı
sözleşmesine sahiptir. Rapot'un önceki kapalı mum → sonraki gerçek Open motoru
değişmez. Araştırma işlemleri borsaya emir veya kullanıcı adına alarm göndermez.

## Scanner ve sunucu alarmları

Gelişmiş `/advanced-alarms` motoru, tarayıcının kısa süreli akış kiralarından
bağımsız BIST abonelikleri ve gerçek dakika geçmişi tutar. Kayıtlı kimliği
gateway üzerinden kullanır; kopma/kimlik değişiminde önceki gözlemleri geçersiz
kılar. Son fiyat kotasyonlarıyla OHLCV uydurulmaz. Süresiz, çok koşullu kurallar,
saniyelik tur hedefi, veri ısınması/kapsamı ve sınırlı disk/bellek politikası
[alarm sözleşmesinde](SERVER_ALARMS.md) açıklanır. Günlük scanner/önceki alarm
motoru aşağıdaki sözleşmeyi korur.

`BORSAPY_USE_FOR_BIST` varsayılan true'dur: `get_bist_data`, sync/async scanner ve
günlük BIST alarm sağlayıcısı kimlikli gateway'i kullanır. False eski sağlayıcı
yolunu açıkça seçer. Kimlik veya sağlayıcı hatasında başka kaynağa sessiz fallback
olmaz. Günlük İstanbul işlem tarihi mevcut
hesaplamaya uyarlanır; `open_quality=provider`, `adjustment=splits` taşınır.
Scanner'ın alım tazeliği metadata'sı korunur; alım zamanı işlem zamanı değildir.
`adjustment=splits` temettü dahil toplam getiri veya tüm sermaye işlemlerinin
canlı doğrulaması değildir. Borsapy verisi eski fiyat önbelleğine yazılmaz.
Alarmın ek 30 saniyelik önbelleği Borsapy BIST yolunda atlanır; kimlik değişimi
gateway'de yeniden kontrol edilir.

BIST sembol evreni varsayılan modda KAP kaynaklı `bp.companies()` ile tembel
yüklenir; importta sağlayıcı çağrısı yoktur. En fazla 2.000 girdi doğrulanır,
yerel TTL bir saat, upstream KAP önbelleği 24 saattir. Tek worker ve paylaşılan
işle bekleme 25 saniyeyle sınırlıdır; hata/eski veri sessiz statik listeye düşmez.
`/borsapy/market/status` kaynak politikasını ve sembol durumunu açıklar.

Mevcut özel sinyal/AI/bildirim koşullarında gereken bağımsız Yahoo teyidi
korunur. Borsapy'yi ikinci kez okumak bağımsız teyit sayılmaz; aynı sağlayıcı
eşleşmesi reddedilir. Sinyal metadata'sı birincil kaynak ve teyit politikasını
taşır; politika alanı tek başına başarılı teyit sonucu değildir. Strateji
eşikleri ve COMBO/HUNTER hesaplama sözleşmesi değiştirilmez.

API bootstrap varsayılan modda eski BIST fiyat servisini başlatmaz; Borsapy
akışları ihtiyaç olduğunda açılır. Hesap henüz tanımlı değilse bu durum kişisel
veri hatasıdır; çalışan API/DB sinyal feed'i ve Binance sağlık durumu bununla
başarısız sayılmaz. Bot da bu kaynak değişikliği için yenilenmelidir.

BIST sunucu alarmlarının günlük kısıtı korunur. Gün içi grafik bulunması BIST
seans/tatil/yarım gün ve mum kapanış takviminin doğrulandığı anlamına gelmez.
Mevcut alarm kalıcılığı, sahiplik, Telegram sınırları ve DRY_RUN/emir ayarları korunur.

## Ertelenen canlı kabul

TradingView oturumunun Rapot sunucusundan doğrulanması tamamlandı. Aşağıdaki
piyasa ve diğer sağlayıcı kontrolleri bundan ayrıdır:

1. İşlem gören hisselerde fiyat, sağlayıcı işlem zamanı, 1m/5m/günlük mumların
   TradingView ekranıyla karşılaştırılması.
2. Çoklu bağlantı ayrımı, bağlantı kaybı/yenileme ve oturum sona ermesi.
3. Tarihsel kapsam, bölünme/bedelli/temettü düzeltmeleri ve geçmiş revizyonları.
4. EVDS/X bağlantıları; ekonomik takvim saat dilimi ve KAP bildirim kapsamı.
   Bilanço beklenen son tarihi kesin yayın anı değildir.

Üretim öncesinde yeni bağımlılıkların disk bütçesi ölçülür; mevcut $6/ay plan ve
528 MiB rezerv korunur. Yerel doğrulama ve yayın sonuçları devam planında tutulur.
