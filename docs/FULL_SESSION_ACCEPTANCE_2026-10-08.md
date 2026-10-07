# BIST tam seans, 3.000 alarm ve veri kalitesi kabulü

**Güncelleme: 7 Ekim 2026. Durum: düzeltmeler üretimde; canlı tam seans kabulü tamamlanmadı.**
Kullanıcı tam BIST kapsamını, eşzamanlı 3.000 canlı alarmı, gün boyunca devamlılığı,
hacim erişimini ve ekonomik takvim saat dilimini doğrulamamızı istedi.
[Önceki kısa canlı kabul](LIVE_MARKET_ACCEPTANCE_2026-10-07.md) bundan ayrıdır.

## Doğrulanmış hacim sonucu

7 Ekim 16:44 UTC'de mevcut şifreli hesapla, ayrı bir API container sürecinde
THYAO/GARAN için 1m ve günlük olmak üzere dört sınırlı sorgu yapıldı. Her sorgu
50 mum döndürdü; 200 mumun tamamında OHLC sonluydu, doğal hacim alanı yoktu.
İstek `BIST` olsa da sağlayıcı sembolü `BISTMIXED:THYAO` /
`BISTMIXED:GARAN`, görünür alanlar `ohlc` olarak çözüldü. Parser'ın ürettiği
200 sıfır, gerçek sıfır hacim değildir. Bu sorgular hesap/kimlik, kural veya
üretim dosyası değiştirmedi. Kullanıcının faturalama planı incelenmedi.

TradingView'in [BIST MIXED açıklaması](https://www.tradingview.com/support/solutions/43000609137-what-is-the-bist-mixed-data-subscription/)
bu akışta hacim olmadığını belirtir. Yeni abonelik satın alınmadı ve gecikmeli
veriye sessiz geçiş yapılmadı. Mevcut bağlantının hacim erişimi **yok** olarak
doğrulandı; başka paket/oturumdaki yetki için aynı doğal alan kontrolü gerekir.

Eksik/sentinel hacim API'de `null` olur; gerçek doğal sıfır korunur. Akış,
grafik geçmişi ve araştırma sonuçları hacim kalite bilgisini taşır. OHLC ve
fiyat göstergeleri kullanılabilir; doğrulanmayan hacimle OBV/VWAP sonucu
üretilmez. Hacme bağlı alarm zaten `unknown` kalır. Bir canlı mumun doğrulanmış
hacmi, eski geçmişin hacmini kendiliğinden doğrulamaz. Metadata taşımayan
geçmiş serisi de doğrulanmış sayılmaz.

Özel kanıt `runtime-data/20261007-volume-acceptance/volume-probe.json`, SHA256:
`75187e734b5e825e117a02555845c56c367939bd0072313106ba0e18577addfa`.
İncelenen probe SHA256:
`0b94ece734ee8ce2a8357b04a247cfb7765f9f3710cbbacfe4b1ca36bcb23941`.

## Takvim tarihleri ve saat dilimi

Borsapy 0.11 parser'ı haftalık/aylık HTML bloğunun ilk gün başlığını sonraki
tablolara da uyguluyordu. Böylece 2 Ekim ABD istihdam ve 14 Ekim TÜFE gibi
olaylar 1 Ekim'e taşınabiliyordu. Yerel adaptör her gün başlığı ve tablosunu
ayrı ayrıştırır; tarih/saat/ülke/olay kimliğiyle tekrarları kaldırır. Hem
`/calendar` hem araştırma takvimi aynı adaptörü kullanır. Upstream global
provider değiştirilmez; ayrı, sınırlı önbellek kullanılır. Tarih verilmemişse
bugün İstanbul takvimine göre seçilir.

Üç resmî saat örneği kaynakla uyuştu: TÜİK 5 Ekim TÜFE 10:00 TSİ; BLS
2 Ekim istihdam 08:30 Eastern → 15:30 TSİ; EIA 7 Ekim petrol verisi
10:30 Eastern → 17:30 TSİ. Kaynaklar:
[TÜİK](https://tuik.gov.tr/Kurumsal/Veri_Takvimi),
[BLS](https://www.bls.gov/schedule/2026/home.htm),
[EIA](https://www.eia.gov/petroleum/supply/weekly/schedule.php).

Doviz.com yanıtında açık IANA saat dilimi/ofset bulunmadı. Bu üç örnek tüm
ülkeler ve yaz/kış saati geçişleri için garanti değildir. API `timezone: null`
ve doğrulanmamış saat uyarısını korur; saatsiz olaylara saat uydurmaz, kaynak
saatine ofset eklemez. ABD'nin kasım geçişi henüz gerçek kaynak olayıyla
doğrulanmadı. [NIST geçiş açıklaması](https://www.nist.gov/pml/time-and-frequency-division/popular-links/daylight-saving-time-dst).
Özel saat kanıtı `runtime-data/20261007-live-acceptance/calendar-timezone/source-time-evidence.json`,
SHA256 `2af787927b35c938f4d85344dc2e9852b0d828040027f4ec8e7a187e4238690f`.

## Tam seans ölçümünün sözleşmesi

Hedef gözlem 8 Ekim 09:30–18:15 TSİ; rapor 10:00–18:00 sürekli işlem bölümünü
ayrıca değerlendirir. **3.000 kural yükü kaynak ön kontrolünde durdu; yük
zamanlayıcısı kurulmadı ve test kuralları oluşturulmadı.** Yalnız veri gözlemi
için ayrı zamanlayıcı kuruldu. 8 Ekim seansı henüz başlamadı.

7 Ekim 17:21 UTC karşılaştırmasında [KAP resmî pazar listesi](https://www.kap.org.tr/tr/Pazarlar)
Yıldız 149, Ana 394, Alt 49, Yakın İzleme 20, PÖİP 19 olmak üzere **631**
benzersiz pay kodu içeriyor. Tamamı mevcut 805 adayda var; resmî listeden
eksik kod yok. Kalan 174 adayın 130'u başka resmî pazar gruplarında, 44'ünün
üyeliği bu karşılaştırmada çözülemedi. Bunlara geçersiz hisse denmedi.
Bu, fiyat akışının 631 kodun tamamına geldiğini veya ertesi gün üyeliğin
değişmeyeceğini kanıtlamaz. Ölçüm bu 631'i ayrıca raporlayacak.
Özel `universe-crosswalk.json` SHA256
`a58002db2577132e01ea50555bebee6f5d658eec5578a30443c36754d704e45e`;
sıralı kanonik 631 kod JSON SHA256
`e49d93571a6de780664f5a11baeebfb8bc69bb042034616db9de5dd795db4c9e`.

- KAP `bp.companies()` kodları aday evrendir; alternatif kodlar ve şirket/pay
  ayrımı çözülmeden sayısı işlem gören pay sayısı olarak sunulmaz. Resmî pay
  evreni, sağlayıcı eşlemesi, abone olunan ve gerçekten veri gelen kodlar ayrı
  tutulur. Eksik kodlar sessizce kapsamdan çıkarılmaz.
- Özel `/advanced-alarms/coverage` yalnız bellekten aday/abonelik, fiyat kaynak
  ve alınma zamanı, sıra/devamlılık kimliği, 1m geçmiş ve istek durumunu verir.
  Fiyatlar, kimlikler ve kural içerikleri dahil değildir; sağlayıcı sorgusu,
  geçmiş işi veya DB okuması başlatmaz. Örnekleme hedefi 30 saniyedir.
- Özel `/advanced-alarms/heartbeat` saniyelik motor turu ve süreç kimliği,
  başarısızlık, kontrol/hazır sayıları, süreleri ve seçili testin kategori
  sayaçlarını verir. Fiyat/teknik/izleme listesinde gerçekten değerlendirilen
  farklı kural sürümleri sayılır. Sadece 3.000 kayıt bulunması yeterli değildir.
- Son işlem zamanının yaşı tek başına ağ gecikmesi değildir; seyrek işlem,
  durdurma ve tavan/taban olasılıklarıyla beraber değerlendirilir. 30 saniyelik
  görüntüler aradaki her sağlayıcı mesajının eksiksizliğini kanıtlamaz.
- Sayaçlar süreçte tutulur, en son 3.000 kural sürümüyle sınırlıdır. Yeniden
  başlatma/süreç kimliği değişimi ve gözlem araları raporda kesinti olarak
  korunur; süreler birbirine eklenip kesintisiz kabul uydurulmaz.

## 3.000 kural yükünün sınırları

Test gerçek kalıcı repository ve çalışan motoru kullanır: 1.000 fiyat,
1.000 teknik, 1.000 tek sembollü izleme listesi kuralı; 15 likit sembole
dağıtılan 3.000 kural/sembol çifti. Teknik koşullar 1m RSI/close ve 5m EMA
girdilerini kullanır. Bu, 3.000 ayrı hisse veya tüm olası karmaşık koşulların
aynı saniyede çalışması değildir. Tam evren veri kapsamı ayrı ölçülür.

Kurallar ayrılmış `__acceptance__:<run-id>` sahibine aittir; giriş hesabı veya
JWT oluşturmaz. Telegram kapalıdır, emir kodu çağrılmaz. Normal global kategori
kotaları geçerlidir; mevcut kullanıcı kuralları değiştirilmez veya kota aşılmaz.
Kurallar başlangıçta kapalıdır; 09:50/09:52/09:55 için 10/100/3.000 yük rampası
planlanır. Her artış kaynak ve servis kontrollerine bağlıdır.

Motor her turda özel dosya iznini denetler: tam kural kimliği/sürümü/içerik
hash'i, sabit bitiş, en fazla 90 saniyelik kontrolcü kalp atışı. Dosya yok,
bozuk, süresi geçmiş veya Telegram açık ise test kuralını değerlendirmez.
Önbellekteki kurallar da bu denetimden geçer. Normal kullanıcı kuralları izin
dosyası okumaz. Teslim repository'si ayrılmış test sahibinin gönderimini ayrıca
iptal eder. Bağımsız temizleyici yalnız manifestteki test kayıtlarını kaldırır.

Başlangıç öncesi bağımsız doğrulanmış güncel SQLite yedeği, tam kaynak/imaj
kimlikleri, 15 tablo ve kullanıcı kayıt parmak izleri gereklidir. 528 MiB sabit
rezerv, bellek/CPU ve servis sağlık sınırları korunur. Yeniden başlatma veya
yükseltme bu testi başarmış göstermek için kullanılmaz. Ölçüm/temizlik
başarısızlığı ve bilinmeyen aralıklar sonuçta açıkça kalır.

## Yayın ve çalışma sonucu

Yerelde 299 frontend testi, lint/typecheck/build/standalone ve tam bağımlılık
audit'i (469 paket, sıfır bulgu) geçti. Python tam koşusunda 1.751 test geçti;
eski teslim bütçesi testindeki Windows saat çözünürlüğü kaynaklı 20 ms yarışı
sabit test saatiyle giderildi. Ardından ilgili 23 alarm/OpenAPI testi geçti.
284 izlenen Python kaynağının lint/format kontrolü temiz. Tam kaynak
`e4493751ec4bc7838ef9e6eefecce3aeab1a5b82` için
[CI'nin beş işi](https://github.com/Rapto0/Rapot/actions/runs/37659323929) ve
[iki imaj yayın işi](https://github.com/Rapto0/Rapot/actions/runs/37659357095)
geçti. Bu kontroller canlı piyasa kabulü değildir.

7 Ekim **17:45:10 UTC** yayın makbuzu API ve frontend'i bu kaynağa bağlar;
**17:48:15 UTC** bağımsız kabul geçti. İmajlar:

- API: `sha256:2bfa6ac02fd03305656041d051808e56449605624c7886f21482ec297f06fa8d`.
- Frontend: `sha256:589be0f933de1d4353b187081abb1dfd4d6e6f78abbae76aabe09533365bf08d`.

Beş servis sağlıklı/restart0; bot, middleware ve PostgreSQL kimlikleri korundu.
15 tablo şeması aynı; üç gönderilmiş olay ve tek kullanıcı listesi güncel
yedek parmak izleriyle eşleşti. Altı özel GET, iki tanı yolu için anonim 401,
beş HTTPS sayfası ve 13 statik dosya örneği geçti. Canlı tanılar 805 kapsam
satırı verdi; piyasa kapalı olduğundan sıfır taze kayıt canlı kabul değildir.
Boş alan **7.177.162.752 bayt**, sabit rezerv 528 MiB. Migration/temizlik,
Telegram gönderimi veya emir testi yapılmadı.

Özel kanıt dizini `runtime-data/20261007-full-session-deploy/`:
`acceptance.json` SHA256
`5a53150d7c78005cd17ab5a01c2b44ddef0ca30c7362c2b098ac9c37eb2d990f`,
yayın makbuzu SHA256
`b60ff218cf94533c44807447bd23c1e769fc6b4d56ecf9a09af0807544012a95`.
Yedek ayrı bilgisayarda açılıp 15 tablo doğrulandı; doğrulama SHA256
`dcf06f4f83ed5b3772ebdd564ca41e4f11f4c56abddeb810f95a5cecd35c1f47`.
Tamamlanmış yayın operatorü ve kanıt dosyaları yeniden çalıştırılmaz.

### 3.000 yük ön kontrolü: kaynak yetersizliği

Eski test paketi yalnız `/root/rapot-ops/20261007-full-session-acceptance`
dizinine aktarıldı. `prepare` kullanılabilir bellek 197.005.312 bayt olduğunda
256 MiB yük korumasında durdu. 17:56:38 UTC bağımsız kontrolünde altı test
unit'i yoktu; baseline/manifest/seed/collector spec'i ve izin dosyası yoktu;
ayrılmış test sahibine ait kural/liste sayıları sıfırdı. Bu paket yeniden
çalıştırılmaz; eski collector hash'i yereldeki son düzeltmeden farklıdır.
Çalışma kimliği `4330f1623e334fb2955ef85ca853ba47`, ilk kurulum manifesti SHA256
`44898838f22af96d03f6ebb1675a1142c07da0b087fe246c26d4d62cf5110214`.

17:58:10–24 UTC'de üç ayrı kaynak örneğinde toplam fiziksel bellek 957,3 MiB,
kullanılabilir bellek 210,6–216,7 MiB, kullanılan swap 699,4 MiB idi. Botun
401,1 MiB swap'ta olması, uyandığında gereken belleği görünür RSS'nin
göstermediğini ortaya koyuyor. Beş servis sağlıklı/restart0/OOM0 olsa da
3.000 canlı alarm için güvenli baş boşluğu kanıtlanmadı. Kullanılabilir
bellek zaten geri kazanılabilir önbelleği içerir; önbellek tekrar eklenmez.

Yük koruması düşürülmedi; servis durdurulmadı, plan yükseltilmedi. Sonraki
kapasite adımı tam Linux imajıyla çevrimdışı 3.000 kural + geçmiş seriler +
gözlem süreçlerinin birlikte tepe bellek/CPU ölçümüdür; ardından ölçülen
gereksiz süreç/import/önbellek maliyetleri azaltılabilir. Swap eklemek veya
kotanın 3.000 olması canlı kapasite kabulü değildir.
Özel `memory-evidence.json` SHA256
`22f177e8425e6df1f73b8ec6d0377b4d6c2da4f3ec750680cd7d3d29e9abc814`;
`memory-assessment.json` SHA256
`1702878d8ad87f29a9184121fb1b824483cf87968633a43dd4bc305fa7144eaf`.

### Ayrı, salt okunur seans gözlemi

Yeni gözlem paketi `runtime-data/20261008-market-observation/` altında,
sunucuda `/root/rapot-ops/20261008-market-observation` dizinine kuruldu.
Yük kontrolcüsü, seed, kural, watchlist ve izin dosyası oluşturmaz;
`load_test_status=NOT_STARTED_RESOURCE_GUARD` raporda zorunlu kalır.
1 saniyelik motor kalp atışı, 30 saniyelik kapsam ve kaynak örnekleri
yalnız bellekten okunur; yeni sağlayıcı sorgusu başlatılmaz.

18:06 UTC'deki gerçek Linux imajı kontrolünde tek tanı çocuğunun tepe belleği
55,9 MiB; iki GET 200, kapsam 805 satırdı. Token yalnız süreç belleğindeydi.
Bu ölçüm ana gözlem sürecini ve sonraki bot taramalarını içermez. Gözlem için
Başlamadan önce 192 MiB kullanılabilir bellek gerekir: 128 MiB devam sınırına
ölçülen çocuk için 64 MiB eklenir. 30 saniyelik kaynak kontrolünde 128 MiB'nin
altına inildiğinde gözlem durur; 3.000 yükün 256 MiB önkoşulu değişmez.
Host gözlem grubunun 96 MiB sınırı container içindeki tanı çocuğunu kapsamaz.
Toplam kanıt bütçesi 32 MiB ve sabit disk rezervi 528 MiB'dir. Örnekler hash
zinciriyle saklanır; kaynak sınırı, kayıt boşluğu veya süreç değişimi gizlenmez.
Özel `collector-memory-evidence.json` SHA256
`4b6930699469791c292f37d98613877c9537a486850728d0291c1f37395b9b4a`.

**7 Ekim 18:24:40 UTC'de kuruldu; 18:24:51 UTC kurulum kabulü ve 18:26:04 UTC
ayrı salt okunur kabul geçti.** Tek `rapot-market-observation-20261008.timer`
enabled/active/waiting; sonraki başlangıç **8 Ekim 06:30 UTC / 09:30 TSİ**.
Servis henüz inactive; bitiş 18:15 TSİ, `Restart=no`, azami çalışma 9 saat.
Test kuralı/lease oluşturulmadı, uygulama servisleri yeniden başlatılmadı.
İki sağlık GET'i 200; son boş alan **7.167.053.824 bayt**.

15 collector/rapor koruma testi, gerçek motor/hub sözleşme testi, 10 kurulum
testi, Ruff ve host Python 3.10 sözdizimi kontrolü geçti. Kurulum öncesi ayrı
iki GET gerçek strict collector şemasını doğruladı; çocuğun bu seferki tepe
belleği 59.113.472 bayttı. Gözlem hem piyasa öncesi/sonrası örnekleri korur hem
10:00–18:00 için ayrı sembol durumları, tazelik aralıkları ve boşluklar çıkarır.

- Çalışma kimliği: `917a800aca2a4f078f3e8d346b6ee1be`.
- Kurulum manifesti: `240483f99d19456bcb9758b2ed4e04016fef211f69f35db38f139e1e4908acf8`.
- Collector: `bf6d4f78e11aec3cc7dc34fc615149264bf3f1441d3567e53050b59c85f027a2`.
- Rapor: `01b695a34c0e76bd1fd4e0d23fc5e08780074e37f5b869c3b7819b4dfca55bf3`.
- Sunucu kurulum kabul makbuzu: `6076a02d25cd0f3d215317394a669b881a4ff103ef2021d17cf1328ea7458541`.
- Ayrı yerel kabul dosyası `independent-install-acceptance.json`:
  `2b658b3e2d14a6ddf551da840036cb8512b84acd0c2760ac6527616f600c4182`.

Codex takibi 8 Ekim 10:20 ve 18:20 TSİ için bu sohbete bağlandı; tarih sınırını
geçen yeni test açamaz ve rapor sonrasında kapanır. Yerel takip Codex/bilgisayarın
açık olmasına bağlıdır; sunucu gözlemi bundan bağımsızdır. Sabah yalnız gözlemin
başlaması ve kaynak sınırları doğrulanır. Seans bitince mühürlenmiş kanıtlar
özel yerel dizine alınır, hash zinciri doğrulanır ve raporlanır; yalnız bu
gözleme ait timer durdurulup devre dışı bırakılır. Kanıtlar korunur. Tamamlanmış
kurulum araçları tekrar çalıştırılmaz; yetersiz bellekle duran yük testi açılmaz.

**Tam BIST, 3.000 canlı yük ve tam seans kesintisizlik kabul edilmiş değildir.**
