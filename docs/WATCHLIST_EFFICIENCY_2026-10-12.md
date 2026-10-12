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
komut başarılı oldu. Linux'taki tam kaynak CI ayrıca yayın kapısıdır.

Yerel test kanıtları; mum revizyonu, hesap değişimi, kuyruktan çıkarılan geç sonuç,
grafik süre sonu, dolu kapasitede alarm önceliği, volume yetkisi ve gerçek kripto
kapanış sınırını kapsar. Eksik/eski veri alarm üretmez. Üretim yayını ve ayrı kabul
tamamlandığında kaynak/imaj kimlikleri ve önce/sonra ölçümleri bu kayda eklenir.
Hazırlanmış kod kalıcı üretim kapasitesi kabulü sayılmaz.

Özel yerel kanıt dizinleri (Git dışı): `runtime-data/20261012-watchlist-efficiency/`,
`runtime-data/20261012-engine-tests/`, `runtime-data/20261012-scanner-efficiency/`.
