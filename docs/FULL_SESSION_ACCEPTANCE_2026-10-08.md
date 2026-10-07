# BIST tam seans, 3.000 alarm ve veri kalitesi kabulü

**Hazırlık: 7 Ekim 2026. Durum: canlı tam seans kabulü henüz tamamlanmadı.**
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

Hedef gözlem 8 Ekim 09:30–18:15 TSİ; 3.000 kural yükü 10:00–18:00 sürekli
işlem bölümünü kapsayacak şekilde hazırlanır. Sunucu kurulumu ve başlatma
kanıtı ayrıca yazılmadan bu plan çalışıyor veya tamamlandı sayılmaz.

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
284 izlenen Python kaynağının lint/format kontrolü temiz. Tam kaynak CI sonucu
yayımdan önce ayrıca doğrulanacak; bu yerel kontroller canlı piyasa kabulü değildir.

Kaynak düzeltmeleri ve ölçüm araçları hazırlanıyor. Tam kaynak CI, yayın,
sunucu zamanlayıcı kurulumu, çalışma kimliği ve gün sonu kanıtları bu bölüme
sonradan, gerçekleşen sonuçlarla eklenecek. **Tam BIST, 3.000 canlı yük ve tam
seans kesintisizlik şu aşamada kabul edilmiş değildir.**
