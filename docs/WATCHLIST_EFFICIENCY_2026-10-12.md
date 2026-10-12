# 12 Ekim — izleme listeleri ve kaynak verimliliği

## Kullanıcı hedefi ve kapsam

Kullanıcı mevcut sunucuda RAM/CPU baskısını ve mum kuyruğunu kalıcı olarak
azaltmamızı istedi. Öncelik BIST/kripto izleme listeleri ve bu listelere birden
fazla koşul bağlamaktır. 3.000 kural kapasite hazırlığıdır; üretimde 3.000 kural
oluşturup sürekli çalıştırma zorunluluğu değildir. Eski otomatik takip/timer
yeniden açılmaz. Bu değişiklik emir göndermez ve yeni abonelik gerektirmez.

## Kaynakla doğrulanan nedenler

12 Ekim 10:06:03 UTC yönetici durum GET'i: **sıfır etkin alarm**, fakat 805
planlı mum işi, 720 bekleyen iş, 173 sağlayıcı hatası ve 71 hazır seri.
805 BIST fiyat aboneliğinin 469'u o anda tazeydi. Bu dar anlık örnek tüm BIST
paylarının kapsandığı veya fiyatların kesintisiz/gecikmesiz olduğu anlamına gelmez.
09:56 UTC üç salt okunur host örneği 213,66 / 234,75 / 217,19 MiB kullanılabilir
RAM ve iki aralıkta %40,89 / %43,53 CPU gösterdi.

Önceki planlayıcı evrendeki her adaya, alarm ihtiyacı olmadan bir 1m geçmiş işi
ekliyordu. Her yenileme 500 mumu doğruluyor, hesaplıyor ve diske yazıyordu.
Async scanner ayrıca tamamladığı batch'lerin DataFrame'lerini turun sonuna kadar
tutuyordu; üretim botunun varsayılan sync yolunda ise grup başına DataFrame
oluşturan ortak haftalık/aylık birleştirme gereksiz CPU harcıyordu.

## Yeni veri ve değerlendirme sözleşmesi

- BIST evren/fiyat aboneliği devam eder. **Mum işi yalnız etkin kuralın kullandığı
  sembol/periyot veya son 120 saniyede görüntülenen geçmiş için planlanır.** Fiyat
  karşılaştırması tek başına mum istemez; kapanış ve mum başına tetik gerçek mum ister.
- Aynı sembol/periyot bütün listeler ve kurallar arasında paylaşılır. En fazla
  128 grafik talebi tutulur; grafik talepleri dolu kuyrukta etkin alarmı dışlayamaz.
  Üyelikten çıkan ihtiyaç ve süresi dolan grafik işleri/belleği bırakılır. Alınmış
  iş nesnesinin kimliği sonuca kadar taşınır; eski iş yeni işin kilidini açamaz.
- Tam OHLCV geçmişi, hacim kalitesi, alan referansları, diğer periyotların kapanış
  dayanakları ve gerçek kapanış sınırı değişmediyse hesaplama yeniden kullanılabilir.
  Değişmeyen mum tekrar diske yazılmaz. Sağlayıcı yine sorgulanır; yeni alınma zamanı
  eski kaynak zamanını veya değişmeyen gözlemi taze fiyata dönüştürmez.
- Seri/değer sınırları aynı kalır; değer hücresi sayısı tüm serileri her yenilemede
  tekrar dolaşmak yerine ekleme/çıkarma sırasında tutulur. Kripto public HTTP
  bağlantıları sabit worker başına yeniden kullanılır; en fazla beş client,
  hatada yenileme ve worker'lar bittikten sonra kapanış uygulanır.
- Aynı koşul JSON'u etkin kurallar yüklenirken, değişmez koşul planı da hub
  yapılandırılırken paylaşılır. Sıcak değerlendirmede AST yeniden doğrulanmaz;
  her gözlemin tazelik/devamlılık/hesap denetimi korunur. Motor bütün 5.000 adayın
  durumunu önceden yüklemek yerine en fazla 128'lik gereken batch'i okur.
  250 yazı, 0,2 saniye, 5.000 değerlendirme ve 15.000 durum belleği sınırları korunur.
- Dış süreçten kural düzenlemelerini yakalayan beş saniye yenileme ve her tur TEST
  izin denetimi sürer. İzin verilmeyen TEST kuralı normal kuralların sırasını sıfırlamaz.
- Ortak scanner birleştirmesi vektörel yapılır; ilk gerçek işlem günü etiketi ve
  eski hesap sonucu korunur. Async batch tamamlanınca ham seriler bırakılır.
  Eski scanner'ın tümü-NaN hacmi toplarken sıfır üretmesi bu performans yamasında
  değiştirilmemiştir; alarmın doğrulanmayan BIST hacmini `unknown` sayması korunur.

`history_requested/scheduled/pending` artık tüm fiyat evreni yerine gerçek mum
ihtiyacını sayar. Ek sayaçlar: `history_alarm_series`, `history_chart_series`,
`history_oldest_pending_seconds`, `indicator_value_count`. Coverage satırındaki
`history_1m.requested=false`, o sembol için dakika mumuna ihtiyaç olmadığını belirtir.
Bu alanlar yöneticiye özel mevcut erişim sınırlarını kullanır.

## İzleme listesi iş akışı

Grafiğin varsayılan liste paneli sunucudaki kalıcı listeleri kullanır. Liste
üyeleri BIST ve Binance USDT sembollerini birlikte taşıyabilir. Bir listeye fiyat,
teknik veya çoklu koşul içeren birden fazla `watchlist` alarmı bağlanır. Üye değişimi
bağlı kural revizyonlarını yeniler; eski bekleyen bildirimler iptal edilir.

Liste paneli fiyatları 50 üyelik sayfalarda ister; bu yalnız ekran isteği sınırıdır,
etkin sunucu alarmının üye kapsamını daraltmaz. Eski yerel listeler ayrı seçimde
korunur ve yalnız kullanıcının açık kaydetmesiyle kopyalanır. Liste kaydetmek veya
alarm taslağı açmak kendiliğinden alarm/Telegram etkinleştirmez. `serverList` kimliği
grafik ile alarm merkezinde aynı sunucu kaydını seçer. Dinamik tüm BIST alarm kapsamı
korunur. Diğer varlıklar için yeni veri adaptörü eklenmedi; rastgele kod girmek
sağlayıcının bu varlığı desteklediği anlamına gelmez.

## Yerel kabul ve sınırlar

Gerçek hub + motor + geçici SQLite, **1.000'er kategoride 3.000 kural**, karma iki
sembol, 6.000 kural-sembol durumu ve 32 yapraklı koşulla çalıştırıldı. Yalnız iki
native seri kullanıldı. Altı sıcak turda 3.920–5.000 karşılaştırma, yaklaşık
198–206 ms/tur; Python retained 11,13 MiB / peak 12,40 MiB ölçüldü. Ağ/Telegram
çağrısı yoktur. Bu sentetik masaüstü ölçümü VPS veya bütün evren için aynı saniyede
3.000 alarm kabulü değildir. 3.000 kural × 805 sembol farklı bir iş yüküdür.

Scanner ölçümünde aynı 3.000 günlük satır × iki piyasa × beş periyot, üç tekrar:
exact eşit sonuçla median 501,48 → 72,06 ms. 162 sembollü async testte tutulmuş
frame payload 16.329.600 → en fazla 5.040.000 bayt; her sonraki batch öncesinde eski
frame'lerin bırakıldığı weak-reference ile doğrulandı. Bunlar süreç RSS ölçümü değildir.

Yerel tam Python paketi **1.804 geçti / bir atlandı**. Sonrasında tur ortasında boşalan
evrenin CPU döngüsüne girmesini engelleyen üyelik snapshot düzeltmesi eklendi;
ardından 51 ilgili test geçti. Frontend **309 test**, lint, typecheck ve standart
Turbopack üretim build'i geçti. İlk Windows build denemeleri sandbox/geçici dizin
ve eski build çıktısıyla başarısızdı; temiz çıktı ve sade geçici dizinle standart
komut başarılı oldu. Aynı kaynak için Linux CI'nin beş işi ve gerekli iki imaj
yayın işi de geçti; npm bağımlılık denetimi 469 paket / sıfır bulgudur.

Yerel test kanıtları; mum revizyonu, hesap değişimi, kuyruktan çıkarılan geç sonuç,
grafik süre sonu, dolu kapasitede alarm önceliği, volume yetkisi ve gerçek kripto
kapanış sınırını kapsar. Eksik/eski veri alarm üretmez. Bu testler tam piyasa
kapsamı veya bütün seans boyunca kapasite kabulü değildir.

## Üretim yayını ve bağımsız kabul

**12 Ekim 10:47:19 UTC**'de API, bot ve frontend kaynak
`6a84fa3c9829dec710f44ddd991d3188555b5c81` ile yayımlandı.

| Hedef | İmaj digest'i |
|---|---|
| API ve bot | `sha256:b1aca6dc44924c6e0a4b1bf583e52b1c310c14b564c1c6417fd0b206f208d695` |
| Frontend | `sha256:f50217de1bb4b0c323b7c9f7223dbcb0044d0de7a220d41185d0354acc460725` |

[Kaynak CI](https://github.com/Rapto0/Rapot/actions/runs/38235227458) ve
[imaj yayını](https://github.com/Rapto0/Rapot/actions/runs/38235262219) aynı SHA'ya
bağlıdır. Middleware/PostgreSQL, Compose/current `279aa9f`, özel yapılandırma ve
şifreli kimlikler korundu. Migration, emir, test Telegram gönderimi, TEST kuralı
veya yeni takip/timer oluşturulmadı.

Taze **1.342.013.440 bayt** SQLite snapshot sunucu dışında SHA, integrity ve
bağımsız SQL dump/restore ile doğrulandı; 15 tablonun tipli parmak izi eşleşti.
Aktarım iki kez durdu; ilk neden yalnız AssertionError olarak kayıtlıdır,
ikinci duruşun nedeni 128 MiB bellek sınırıdır. Sınır düşürülmedi. Devam aracı
önce mevcut parçanın uzak snapshot ile SHA eşleşmesini, sonra tüm dosyayı kontrol
etti. Doğrulanan yerel yedek korundu; yalnız bu işe ait geçici sunucu snapshot'ı
ve receipt kaldırıldı, hata tanısı saklandı.

İlk bağımsız kabul AssertionError nedeniyle tamamlanamadı; ayrıntılı güvenli tanılı
tekrar bütün kontrolleri geçti. **Değiştirilmemiş asıl kabul aracı 10:51:50 UTC'de
başarılı oldu.** İlk hatanın kesin nedeni saptanmadı; kontrol gevşetilmedi.
API ve botta 26 seçilmiş kaynak dosyası ve 120 dağıtım, 15 tablo şeması, tek
kişisel liste ve üç önceki olayın taze yedekle tipli parmak izi doğrulandı.
Beş HTTPS sayfası, 13 statik örnek, 11 anonim özel yolun 401/no-store sınırı
ve iki ek tanı erişim sınırı geçti. Frontend native Sharp 0.35.5 / vips 8.18.7 /
rsvg 2.63.2 doğrulandı. Etkileşimli tarayıcı yüzeyi mevcut değildi; bu kabul
gerçek kullanıcı tıklama/görsel karşılaştırma testi olarak sunulmaz.

## Canlı kaynak ve mum yaşam döngüsü

10:48:21 UTC: **805 BIST adayına fiyat aboneliği sürerken sıfır alarm için
istenen/planlanan/bekleyen mum işi 0/0/0** oldu. 484 aday o anda tazeydi;
bu 805 adayın tamamının gecikmesiz olduğu anlamına gelmez.

10:49:03 UTC yalnız GARAN/BIST ve BTCUSDT/Kripto 1m grafik GET'i iki geçici
iş açtı. İlk GARAN yanıtı `cached_unverified`, BTCUSDT `waiting` idi. 10:49:19
ikinci okumada her ikisi `ok`, iki seri hazır ve kuyruk sıfırdı; son kaynak
mumları sırasıyla 10:48 ve 10:49 UTC. Hacim alanının bulunması BIST hacim
yetkisi kanıtı değildir; doğrulanmamış hacmin alarm koruması değişmedi.

Son history isteğinin ardından başka history isteği yapılmadı. **10:52:00 UTC**
durum okumasında 120 saniyelik talepler sona ermiş, planlı/bekleyen işler,
grafik serileri ve hesaplanan değer hücreleri tekrar sıfır olmuştu. Disk
önbelleğinin yaklaşık 13 MiB kalması beklenen kalıcılıktır; sıcak alarm verisi
olarak yeniden yüklenmez. Alarm kuralları/kişisel liste değiştirilmedi.

| Salt okunur örnek zamanı (UTC) | Kullanılabilir RAM, üç örnek (MiB) | CPU, iki aralık |
|---|---|---|
| Yayın öncesi 09:56 | 213,66 / 234,75 / 217,19 | %40,89 / %43,53 |
| Aktarım durduktan sonra 10:38–10:39 | 160,85 / 161,78 / 161,43 | %77,75 / %80,93 |
| Yayın sonrası 10:48 | 350,77 / 330,44 / 330,98 | %24,72 / %8,53 |
| Talepler sona erdikten sonra 10:53 | 331,62 / 329,34 / 297,00 | %20,14 / %24,97 |
| Son örnek 11:00 | 296,98 / 297,13 / 297,13 | %19,83 / %23,03 |

API cgroup belleği ilk örneklerde 236,61–240,46 MiB iken 10:53'te 113,58 MiB
oldu; RSS veya Python heap ile aynı ölçü değildir. Yeniden başlatma, tarama
evresi ve host yükü de sonuçları etkiler. Bu kısa örnekler tam seans boyunca
aynı kaynak düzeyini veya 3.000 × bütün evren yükünü kanıtlamaz.

**11:00:16 UTC** son servis kontrolünde kabul edilen beş container aynı kimlikte,
sağlıklı, restart0 ve OOM kaydı yoktu. Eski gözlem timer'ı `disabled/inactive`,
servis `inactive/MainPID0`; disk boşluğu **6.934.380.544 bayt**, 528 MiB sabit
rezerv korunuyor. Yeni otomatik takip kurulmadı.

Temel sonuç: gereksiz evren çapındaki mum kuyruğu kaldırıldı; gerçek BIST/kripto
mum talebi ve talepten sonra kaynak bırakma canlıda doğrulandı. 3.000 kural
hazırlığı yerel motor testidir; tüm piyasanın gecikmesizliği, tüm gün süreklilik
ve bütün evren üzerinde 3.000 eşzamanlı teknik alarm kabulü açık kalır.

Kanıt SHA'ları:

- Yayın: `6d335fb911f1e436b1fe36570932c86f153d840cee982bd4f8b88f95547335ac`.
- Bağımsız kabul: `fdfc04392a9cb30f6adc11636c7d047b25fcf55d0bc53477fcdff9f94f8ef392`.
- Yedek doğrulama: `cc7fef48198e15afde697a25c110040c9f3346b0d81521174377de4c28252300`.

Özel yerel kanıt dizinleri (Git dışı): `runtime-data/20261012-watchlist-efficiency/`,
`runtime-data/20261012-engine-tests/`, `runtime-data/20261012-scanner-efficiency/`,
`runtime-data/20261012-watchlist-deploy/`. Gerçek DB/yedek ve özel kimlikler Git'e alınmaz.
