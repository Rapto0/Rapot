# Sabit veriyle CLI ve rapor kabulü

P3-1'in CLI yolu gerçek `BacktestEngine`, COMBO/HUNTER hesaplayıcıları, ortak
nakit yürütmesi, benchmark karşılaştırması ve bağımsız al/tut pencere özetini
birlikte çalıştırır. Sabit sentetik OHLCV kullanır; piyasa geçmişi veya kazanç
kanıtı değildir. [Portföy](BACKTEST_PORTFOLIO.md), [yürütme](BACKTEST_EXECUTION.md)
ve [muhasebe](BACKTEST_ACCOUNTING.md) sözleşmeleri geçerlidir.

Repo kökünde, yeni veya boş bir çıktı klasörüyle:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.backtest_fixture `
  --output-dir runtime-data/backtest-fixture-acceptance `
  --as-of 2020-06-16T00:00:00Z --excel
```

Bu wrapper uygulamayı import etmeden önce boş geçici çalışma dizini ve sentetik
ayarlar kurar. Çağıranın `.env` dosyası okunmaz; uygulama ayarları, günlük ve
önbellek yolları geçici alana yönelir. Sağlayıcılar, Python socket/DNS, SQLite,
native Curl ve alt süreç çağrıları engellenir. Gerçek veri tabanı açılmaz;
hesaplayıcılar stub ile değiştirilmez. Wrapper modülünü import etmek bu işleri
başlatmaz. Bu işlem bir güvenlik sandbox'ı değil, fixture kabulünün IO sınırıdır.

`daily-waves-v1`, 1 Ocak 2018'den başlayan 900 günlük dört deterministik OHLCV
serisi üretir: iki sentetik BIST ve iki sentetik CRYPTO sembolü. İşlem aralığı
20 Mayıs–15 Haziran 2020'dir; önceki satırlar gerçek göstergeleri ısıtır.
Varsayılan `as_of` yukarıdaki sabit UTC anıdır. Formül ve girdi hash'leri,
Python/pandas/NumPy sürümleri ve çalıştırma kapsamı JSON'a girer. Aynı kod,
bağımlılıklar ve cutoff ile JSON/CSV/SVG tekrar üretilebilir. XLSX ZIP dosyasının
oluşturulma zamanı değişebilir; kabul sayısal hücreleri denetler.

## Üretilen dosyalar

- `report.json`: piyasa başına NAV, başlangıca göre toplam getiri, gerçekleşmiş
  PnL, açık maliyet tabanı, gerçekleşmemiş PnL, masraflar ve işlenen/atlanan
  semboller; ayrıca benchmark ve açıkça etiketlenmiş al/tut pencere sonuçları.
- `bist_*` ve `crypto_*` adlarıyla altı CSV: işlemler, günlük equity ve açık
  pozisyonlar. Boş sonuçlarda da başlık satırı bulunur. Equity CSV'sinde fiyat
  tarihleri ve eski fiyatlı semboller JSON hücreleriyle korunur. JSON raporu
  bu dosyaların byte sayısını ve SHA-256 değerini taşır.
- `equity.svg`: iki piyasanın gerçek günlük NAV serileri ve başlangıç sermayesi;
  standart kütüphaneyle yazılan, tarayıcıda açılabilir SVG. Matplotlib gerektirmez.
- `--excel` seçildiyse `report.xlsx`: gerçek openpyxl çalışma kitabı; özet,
  işlemler, açık pozisyonlar, gerçekleşmiş sembol performansı ve equity sayfaları.

Çıktı klasörü doluysa işlem mevcut raporları ezmeden hata verir. Başarılı kabul
hem sıfır çıkış kodunu hem üretilen dosyaların doğrulanmasını gerektirir; kısmi
çıktı tek başına kabul değildir. Yeni testler gerçek subprocess koşumunu iki kez
yapar; JSON/CSV/SVG eşitliğini, CSV hash'lerini, XLSX hücrelerini ve SVG serilerini
kontrol eder. Aynı cutoff'ta her piyasada gerçek sinyallerin açık lot üretmesi de
denetlenir; boş veya yalnız stub sonuç tam CLI kabulü sayılmaz.

## Getiri adları ve sınırlar

`NAV Getiri % = (son kapanış NAV / başlangıç sermayesi − 1) × 100`.
Gerçekleşmiş PnL kapatılmış FIFO lotlarının sonucudur; açık pozisyonların değer
değişimini içermez. Sembol performansındaki `Getiri %` yalnız kapalı lotların
gerçekleşmiş PnL/maliyet oranıdır ve aynı sayfada bu temel açıkça yazılır.
Açık pozisyon varken geçerli equity kaydı yoksa NAV/toplam getiri `null`/`N/A`
kalır; lot alış fiyatından değer uydurulmaz. NAV mevcut equity kaydının iki
ondalık sunum değerini kullanır; bu bir Decimal muhasebe defteri değildir.

Benchmark aynı tarih aralığında maliyetli al/tut NAV karşılaştırmasıdır. Pencere
özeti gerçek COMBO/HUNTER optimizasyonu değildir: ayrı al/tut deneylerinin giriş
Open/çıkış Close sonuçlarını hesaplar ve `strategy_evaluated=false` döndürür.
Bu rapor gerçek strateji WFA yapılmış gibi sunulmaz.

Eski `backtesting_system.py` girişinin varsayılanı gerçek sağlayıcılardır.
Doğrudan `--fixture` sabit veriyi seçer, ancak eski modül import zinciri ayarları
`main` öncesinde yüklediğinden izole kabul için yukarıdaki wrapper kullanılır.
Openpyxl yoksa `--excel` anlaşılır hata verir; JSON/CSV/SVG için zorunlu değildir.
Eski `plot_results` PNG yolu matplotlib gerektirir ve ayrı isteğe bağlı yoldur;
SVG kabulü matplotlib'in kurulduğu veya PNG renderer'ın çalıştırıldığı anlamına
gelmez. Yeni zorunlu bağımlılık eklenmedi. Borsa emri, TradingView teslimi,
gerçek sağlayıcı verisi ve Pine runtime kabulü bu fixture koşumunun dışındadır.
