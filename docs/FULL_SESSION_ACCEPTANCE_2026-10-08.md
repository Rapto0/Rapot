# BIST tam seans, 3.000 alarm ve veri kalitesi kabulü

**Güncelleme: 8 Ekim 2026. Durum: API düzeltmesi yayımlandı; son kaynak kontrolü gözlem/yük başlangıcını engelledi. Tam seans ve 3.000 yük kabulü tamamlanmadı.**
Kullanıcı tam BIST kapsamını, eşzamanlı 3.000 canlı alarmı, gün boyunca devamlılığı,
hacim erişimini ve ekonomik takvim saat dilimini doğrulamamızı istedi.
[Önceki kısa canlı kabul](LIVE_MARKET_ACCEPTANCE_2026-10-07.md) bundan ayrıdır.

## 8 Ekim elle devam ve kaynak düzeltmesi

Kullanıcının “Hazırım” mesajıyla çalışma elle devam etti. İlk saat kontrolü
10:13 UTC / 13:13 TSİ; sabah bölümü gözlenmiş sayılmaz. Codex takibi `PAUSED`,
eski gözlem timer'ı `disabled/inactive`, servis `inactive/MainPID0` olarak
korundu. Ayrı otomatik takip veya yük zamanlayıcısı başlatılmadı.

İlk üç host örneğinde kullanılabilir RAM 131,6 / 140,4 / 189,7 MiB; 192 MiB
gözlem ve 256 MiB yük başlangıç sınırları sağlanmadı. Tek çekirdekte yaklaşık
%100 kullanım ve swap sayfalama görüldü; API/bot etkin tüketicilerdi. Beş
servis sağlıklı, restart0/OOMfalse. 10:39 UTC'deki ek sınırlı tanı denemesi
145,5 MiB nedeniyle container çocuğunu ve HTTP isteklerini başlatmadan durdu.
Kaynak guard'ları düşürülmedi; 3.000 test kuralı oluşturulmadı.

Kod incelemesi, 805 sembol için request-local dakika geçmişi sağlayıcısının
her seferinde kullanılmayan bir HTTP istemcisi/TLS context oluşturduğunu
gösterdi. Native geçmiş yalnız WebSocket kullanır. Dar düzeltme bu HTTP
kurulumunu kaldırır, HTTP hesap yollarını kapalı tutar ve eksik hacim
işaretlemesini toplu uygular. WebSocket TLS, token/hesap epoch kontrolü,
500 mum sınırı, fiyat/hacim kalitesi ve sembol kapsamı değişmez.

Windows'ta ağsız sentetik ölçümde kurucu medyanı 191,1 → 0,0085 ms, 500
eksik hacim satırının işlenmesi 11,74 → 0,603 ms oldu. Bu VPS CPU veya
3.000 alarm kapasite kabulü değildir. 52 ilgili test, gerçek native
`get_history` için sahte WebSocket replay'i dahil geçti. **Bu paragrafın
yazımında düzeltme henüz üretime alınmadı; yayın ve sonrası ölçüm ayrıdır.**

8 Ekim KAP kontrolü yine 631 kod içerdi; eklenen/çıkan/pazar değiştiren kod
yok. Yeni iki saat örneği uyuştu: EIA 8 Ekim doğal gaz 10:30 Eastern →
17:30 TSİ; BLS 14 Ekim TÜFE 08:30 Eastern → 15:30 TSİ.
[EIA](https://ir.eia.gov/ngs/schedule.html),
[BLS](https://www.bls.gov/schedule/2026/10_sched.htm).
11:23:35 UTC'de mevcut yönetici ekranında 8 Ekim EIA 17:30, 14 Ekim TÜFE
15:30 ve 15/22 Ekim EIA 17:30 satırları görüldü. Bu ekim örnekleri genel
kaynak saat dilimini veya kasım yaz/kış saati geçişini doğrulamaz.

Özel kanıtlar `runtime-data/20261008-live-verification/` altında:

- `host-resources.json`: `06f3035560f068defdbf6ff30cda918ec1443ac645834df7123bd97c2e259f63`.
- `stdlib-diagnostic-once.json`: `b519cabf75a0a708821498ffa9b5805e568663bec8b19b33723d853844daea54`.
- `history-cost-probe-after.json`: `16a98483a959bc48e372fb7892d510a39d300b8c643421833310307b83c34871`.
- `kap-equity-recheck.json`: `fb096f53598fa3f41c38a2d9548eb8783fe3d79e24247263be9e66ab4dea39ab`.
- `public-source-verification.json`: `b24271f6825690eff0f93254a6f4ca9a8743bf2500ef9c96191ab17ae277f181`.
- `ui-calendar-confirmation.json`: `a0b956f13fc37333bdef0f1d6fd9ee2e68d84396a5327d86fc63bc0e87fb413e`.

### 8 Ekim 11:26 UTC API yayını ve bağımsız kabul

Yukarıdaki yayın öncesi ölçüm tarihsel olarak korunur. Kaynak
`f1d832bd553b4f54f2bb5a31ab49414fe179a6c1`, **11:26:37 UTC / 14:26:37 TSİ**
makbuzuyla yalnız API'ye yayımlandı. Yeni API imajı
`sha256:0ef59ac11a653bdaa5a5efc1eec3106a5e24c2e4c5a7bf36244787d05f3673ad`,
container kimliği `5cf37465e854…`. Frontend `e449375`, bot `876f3f3`,
middleware/PostgreSQL ve Compose/current `279aa9f` korundu.

Yerel tam testte **1.755 geçti, bir atlandı**. Aynı kaynak için
[CI'nin beş işi](https://github.com/Rapto0/Rapot/actions/runs/37765051092) ve
[iki imaj yayın işi](https://github.com/Rapto0/Rapot/actions/runs/37765095469)
başarılı. **11:27:33 UTC** bağımsız kabul; beş servisin sağlıklı/restart0
durumunu, değişmeyen 15 tabloyu, üç gönderilmiş test olayını ve tek kullanıcı
listesini doğruladı. 23 seçilmiş kaynak dosyasının hash'i, 120 kurulu dağıtım,
yedi yetkili salt okunur GET, 11 anonim 401/no-store, beş HTTPS sayfası ve
13 statik dosya örneği kontrol edildi. Bu, tüm runtime dosyalarının tek tek
incelendiği veya canlı piyasa kabulünün tamamlandığı iddiası değildir.
Kimlik/ortam baytları ve diğer dört servis değişmedi; migration yapılmadı.

Taze **1.317.625.856 bayt** binary SQLite snapshot, salt okunur kaynak üzerinden
SQLite online backup API'siyle alındı. Tam integrity, 15 tablonun tür bilgili
parmak izi ve ayrı logical restore karşılaştırması özel yerel dizinde,
repo dışında tamamlandı; üretim restore'u yapılmadı. Kaynak sunucuda pahalı
satır taraması yerine yerel doğrulama kullanıldı. Yalnız bu çalışmanın tam
kimliği/hash'i doğrulanmış geçici sunucu snapshot'ı ayrı temizleme makbuzuyla
kaldırıldı; özel yerel doğrulanmış yedek korundu.

11:28:29–43 UTC kaynak örneklerinde kullanılabilir bellek **278,21 / 236,64 /
239,64 MiB**; ardışık iki aralıkta host CPU **%79,67 / %75,82**, load1m
**4,00 / 3,62 / 3,33** idi. API yeniden başlatması ve önbelleğin tekrar ısınması
sonrasındaki kısa ölçüm, kalıcı CPU kazancını veya 3.000 yük baş boşluğunu tek
başına kanıtlamaz. Üç örnekten ikisi 256 MiB yük sınırının altında; **3.000 test
yükü çalıştırılmadı ve yeni elle gözlem henüz başlatılmadı**. Eski timer/Codex
takibi kapalıdır; sonraki elle adımlar kendi güncel kaynak kontrollerine bağlıdır.

Kabulde alarm motoru çalışıyordu, etkin kural sıfırdı. 805 adayın 461'inde
taze fiyat, 40 hazır/48 önbellekli geçmiş seri ve 782 bekleyen geçmiş işi
görüldü; bunlar yeni süreçte erken anlık örnektir. `history_ready` tazelik
kontrolünü geçen seri, `history_pending` vadesi gelmiş veya çalışan iş sayısıdır;
iki küme örtüşebilir. Sıfır kuralda da 805 adayın 1m geçmişi iki worker ile
yenilenir; başarılı iş yeniden 30 saniye sonra uygun olur. Her iş en fazla
500 doğal mum ister. CPU düzeltmesi bu ağ/yenileme düzenini değiştirmez;
805 abonelik bütün sembollerin sağlayıcıca kabul edildiği veya gecikmesiz
olduğu anlamına gelmez. Tam 631 pay kapsamı ve gün boyu süreklilik açık kalır.
İki worker'ın 805 seriyi 30 saniyede yenileyebilmesi için toplam iş başına
ortalama yaklaşık 75 ms gerekir; 180 saniyelik tazelik penceresi için bile
yaklaşık 447 ms gerekir. Bunlar gerekli hız hesabıdır, ölçülmüş sağlayıcı
kapasitesi değildir. Her seferinde yeni WebSocket ve 500 mum alınması,
sağlayıcı beklemeleri/hataları ve eski kaynak mumları hâlâ kuyruğu uzatabilir.

11:30:58 UTC / 14:30:58 TSİ mevcut alarm ekranında motor çalışıyor, etkin
kural sıfır; 805 adaydan **480 taze**, **101 hazır geçmiş seri / 775 bekleyen
iş** görüldü. Bu ayrı bir anlık ekran gözlemidir. Gösterilen kaynak/alıntı
yaşları bütün önbelleğin maksimumudur; tek eski kaydın yaşı bütün piyasaya
ait gecikme gibi yorumlanmaz. Resmî 631 payın ayrı tazelik dağılımı veya
kesintisiz veri kapsamı bu ekran örneğiyle doğrulanmadı.
11:50:34 UTC / 14:50:34 TSİ son ekran örneği **451/805 taze aday, 87 hazır
seri / 762 bekleyen iş**, son motor turu 14:50:33 gösterdi; bu da sürekli
gözlem değil, ayrı bir anlık kayıttır.

**11:39:26.970 UTC** kaynak kapısı kimliği doğrulanmış çalışan API için
**176.300.032 bayt / 168,13 MiB** kullanılabilir bellek, CPU başına load1m
**2,3213**, **7.117.983.744 bayt** boş disk alanı ölçtü. Disk rezervi korunsa
da 192 MiB gözlem ve 256 MiB yük bellek sınırları başarısız; 3.000 yükün
CPU başına load1m < 1,5 koşulu da sağlanmadı. Sonuç
**`NOT_STARTED_RESOURCE_GUARD`**. Yeni paket sunucuya aktarılmadı, gözlem veya
yük başlatılmadı; test kuralı/lease oluşturulmadı. Ayrı otomatik takip açılmadı.
Bu son örnekte container bazlı bellek dökümü yok; önceki ölçüme göre tüm
bellek düşüşü yalnız API'ye veya önbelleğe yüklenemez. Ek bellek tanısı bir
başlangıç/çalışma kabulü değildir.

**11:47:01–15 UTC son kaynak ölçümü:** kullanılabilir RAM **146,43 / 146,27 /
159,65 MiB**, iki aralıkta CPU **%94,51 / %98,49**, load1m **3,81 / 3,99 /
3,91**. Üç örnekte cgroup `memory.current` API için 203,45–214,22 MiB,
bot için 205,84–215,45 MiB aralığında; bunlar swap'taki belleği kapsamaz.
Yayın hemen sonrasındaki 236–278 MiB baş boşluğu kalıcı olmadı. Dar kurucu
düzeltmesinin yerel test kazancı doğrulansa da **sunucuda sürdürülebilir CPU
ve yük kapasitesi iyileşmesi doğrulanmadı**. Hem gözlem hem 3.000 yük başlangıç
kapısı hâlâ başarısızdır; bu tur yeni gözlem paketi aktarımı,
gözlem başlatılması veya yük çalıştırılması yapılmadı. Yük testinin çalışması
başarısız olmuş gibi gösterilmez: test çalıştırılmadı, başlangıç kabulü geçmedi.

Yeni 15 dakikalık, göreli başlangıçlı 3.000 yük planının tam çalıştırıcısı
tamamlanmadı; salt okunur ön kontrol bunun yerine geçmez. Yerel gözlem taslağının
RSS kontrolü, container'ın ağ namespace'ini kullanacak biçimde düzeltilmeden ve
yeni inceleme manifesti hazırlanmadan yayımlanmaz. Bu taslaklar üretimde çalışmaz.

**11:52:08 UTC bağımsız son kontrol:** beş servisin kimliği, runtime hash'i,
sağlığı/restart0/OOMfalse durumu; özel yapılandırma, şifreli kimlik dosyaları ve
current işaretçisi korundu. Eski timer disabled/inactive, eski servis
inactive/MainPID0; yeni gözlem servisi, altı yük birimi, yeni uzak gözlem dizini
ve lease dizini yok. İki küçük alarm tablosunda salt okunur sayım ayrılmış
TEST sahibi için sıfır kural/liste, genel etkin kural için sıfır gösterdi.
Kullanılabilir RAM 188.592.128 bayt (179,86 MiB), boş alan 7.117.021.184 bayt.
Bu son kontrol de 192 MiB gözlem başlangıç sınırını karşılamadı.

Özel kanıtlar `runtime-data/20261008-history-efficiency-deploy/` altında:

- `acceptance.json`: `27dc00877d2e14a622e10871c998702de13e331651270044623aafc72d16cdf1`.
- Yayın makbuzu: `a137925d8e283021d8e26835b4929750d4c4f8b61f80eae332759dfb166918ec`.
- `backup-verified.json`: `be6ab569a1cfd8d325f8b44c210bc7ed659f1bab24171c101af28eb03c676a16`.
- `backup-cleanup.json`: `d8eb26e6219ad9cdb93fd9f83650b414fb3aee51b80e078688237ac745f971c5`.
- `resources-after-deploy.json`: `c7150f74b1cd046fe9f2f69d3f38b14b37ca57e790c34a1a034d1e9d38c14be1`.
- `resources-warm.json`: `9909946c90ef6bf271da46de28cfcc97414689ec315a0bd57d7f19f9efbbe403`.

Son kaynak engeli `runtime-data/20261008-manual-observation/` altında:

- `transport-resources.json`: `d68558fa1317d6c1c8b7a7d6fe857b0c3ca5158f34c39f544d10b871258fd418`.
- `resource-blocker.json`: `9a91a6d07bf76ba3207bfe4b44d4eea3703442fca03ab13eb6c8cb82fa8d53bf`.

Anlık ekran kanıtı `runtime-data/20261008-live-verification/ui-after-deploy.json`:
`5d4007bb05de363b4275f019061fd83796859f3cbfafa4d5511349af9d72c9ee`.
Son ekran kanıtı aynı dizindeki `ui-final-alarm-sample.json`:
`bc9d8c07b9d80a06d59c40f7b7ac658edba12a9f784f90a183dec4af6069f9fd`.
Bağımsız son durum aynı dizindeki `final-state.json`:
`ca5384813a0601954308a87db51af1b7d96b1cd0edaf166bc9bb0aa4d8119cf6`.

Tamamlanmış yayın/yedek/temizleme araçları yeniden çalıştırılmaz. Bu kayıt
Telegram mesajı, emir veya yeni test kuralı oluşturulmuş sayılmaz.

## Doğrulanmış hacim sonucu

8 Ekim 14:51:16 TSİ grafik ekranında THYAO günlük 1.000 mum için kullanılabilir
hacim gelmediği uyarısı görüldü. Aynı ekrandaki beş hissede kaynak zamanları
14:51:09–14 arasında günceldi; bu dar ekran örneği tüm piyasa veya her işlem
kabulü değildir. Yeni ham sağlayıcı hacim sorgusu yapılmadı. Özel ekran kanıtı
`runtime-data/20261008-live-verification/ui-final-chart-sample.json`, SHA256:
`fde5f51f9d238eeab0baba4dbbb7c95be28ce018cbdc50706364aa366822bada`.

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

7 Ekim'de hazırlanan hedef gözlem 8 Ekim 09:30–18:15 TSİ idi. Aynı akşam
kullanıcı talimatıyla otomatik başlangıç iptal edildi. 8 Ekim “Hazırım”
mesajıyla elle inceleme başladı; son kaynak engeli yukarıda ayrıca kaydedildi.
Rapor 10:00–18:00 sürekli işlem bölümünü
ayrıca değerlendirir. **3.000 kural yükü kaynak ön kontrolünde durdu; yük
zamanlayıcısı kurulmadı ve test kuralları oluşturulmadı.** Yalnız veri gözlemi
için ayrı zamanlayıcı kurulmuştu. **7 Ekim'deki kurulum kabulü sırasında**
8 Ekim seansı henüz başlamamıştı; bu tarihsel kurulum seans gözlemi değildir.

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
ayrı salt okunur kabul geçti.** Bu tarihsel kabul anında tek
`rapot-market-observation-20261008.timer` enabled/active/waiting durumundaydı;
sonraki başlangıç **8 Ekim 06:30 UTC / 09:30 TSİ** olarak kayıtlıydı.
Servis o anda inactive idi; bitiş 18:15 TSİ, `Restart=no`, azami çalışma 9 saat.
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

**Son kullanıcı talimatı — otomatik başlangıç iptal:** Kullanıcı 8 Ekim yaklaşık
10:00'da bilgisayarını açacağını, ayrı otomatik takip istemediğini ve yalnız
kendisi **“hazırım”** dediğinde çalışmanın başlamasını istediğini belirtti.
Önceden 10:20/18:20 için bağlanan Codex takibi `PAUSED` olarak doğrulandı.
**7 Ekim 18:38:08 UTC'de** yalnız `rapot-market-observation-20261008.timer`
`disabled/inactive`, sonraki başlangıç boş; gözlem servisi `inactive/MainPID0`
doğrulandı. Beş ana servisin kimlik/sağlık/restart bilgileri aynı ve sağlıklı.
Veritabanı/kural değişmedi; kanıtlar korundu. Özel `user-requested-pause.json`
SHA256: `4f276af636f5042c8b6cbe69c5825b686bd3b560290750dcf63b426a100d388d`.
Önceki başarılı kurulum ve kabul hash'leri tarihsel
kanıt olarak korunur; otomatik çalışma için güncel talimat sayılmaz.

Elle devam kullanıcının “hazırım” mesajını bekler. O sırada gerçek saat ve kaynak
durumu yeniden değerlendirilir; kaçırılan seans bölümü ölçülmüş sayılmaz.
Tamamlanmış kurulum araçları tekrar çalıştırılmaz; 3.000 yükün 256 MiB bellek
engeli geçerlidir ve yük testi kendiliğinden açılmaz. Mevcut uygulama servisleri
ve kişisel kayıtlar bu takip iptalinin kapsamı dışındadır.

**Tam BIST, 3.000 canlı yük ve tam seans kesintisizlik kabul edilmiş değildir.**
