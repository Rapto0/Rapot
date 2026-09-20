# Günlük backtest yürütme sözleşmesi

P3-1 dördüncü adım, `backtesting_system.py::BacktestEngine` için tarih aralığını,
sabit günlük girdiyi ve sinyalden işleme geçişi tanımlar. Bu ayrı CLI modülüdür;
scanner, dashboard hesaplayıcıları, Pine veya middleware emir yolu değişmez.
[Maliyet muhasebesi](BACKTEST_ACCOUNTING.md) aynı referans fiyat ve FIFO modelini
korur. Bu belge gerçek borsa dolumu veya strateji getirisi kabulü değildir.

## Zaman ve fiyat

1. Girdi günlük OHLCV'dir. `DatetimeIndex` değerleri piyasanın gün etiketidir:
   BIST için Europe/Istanbul, CRYPTO için UTC. Saat dilimsiz indeks bu takvimde
   yorumlanır; saat dilimli indeks önce bu takvime çevrilir. Sonuç gece yarısı
   olmalı; gün içi veri günlük veri gibi kabul edilmez.
2. `as_of` engine oluşturulurken bir kez sabitlenir. Verilmezse o andaki UTC
   zamanı alınır. Açıkça verilirse saat dilimli timestamp gerekir; örneğin
   `2020-06-09T00:00:00Z`. Saat dilimsiz bir timestamp sessizce yorumlanmaz.
3. Bir gün, **sonraki takvim gününün yerel gece yarısı** `as_of` anına ulaştığında
   veya bu andan önceyse kabul edilir. Takvim günü ekleme, saat dilimi eklenmeden
   yapılır; geçmiş yaz saati günleri 24 saat varsayılmaz. BIST seans bitiş saati
   veya tatil takvimi uydurulmaz. Bu bilinçli olarak muhafazakâr bir kuraldır:
   bugünkü açılış gerçekleşmiş olsa bile bugünün satırı henüz kullanılmaz.
4. `start_date` ve `end_date`, **işlem gününe** uygulanan dahil sınırlardır.
   `YYYY-MM-DD`, `date` veya saat dilimsiz/gece yarısındaki `datetime` kabul
   edilir. Saat dilimi/gün içi saat ve ters tarih aralığı reddedilir. `None`
   ilgili sınırı kaldırır; `as_of` kapanış sınırı her durumda korunur.
5. Sinyal yalnız önceki kapanmış günün sonuna kadar olan prefix'ten hesaplanır.
   İşlem, **sonraki mevcut satırın gerçek Open fiyatıyla** gerçekleşir. Takvimde
   bulunmayan günler için mum üretilmez. Son satırın sinyali için sonraki satır
   yoktur; dolayısıyla bu sinyal ayrıca işleme dönüşmez.
6. Başlangıçtan önceki satırlar göstergelerin ısınması için korunur. Eski
   120 uygun satır şartı ve ilk sinyalin 0–60 indekslerini içermesi korunur;
   ilk mümkün işlem indeksi61'dir. Sınırlar nedeniyle 120'den az uygun satır
   veya hiç işlem günü kalırsa `None` döner ve portföy değişmez.

Örnek: 1 Haziran kapanışındaki sinyal, sonraki mevcut gün 2 Haziran ise onun
Open fiyatıyla işlenir. 2 Haziran `Open=200`, `Close=999` olduğunda referans
işlem fiyatı200 olur; komisyon/kayma mevcut maliyet modeliyle ayrıca uygulanır.
`end_date=1 Haziran` ise 2 Haziran işlemi oluşmaz. Tarih alanları gün etiketidir;
borsadan alınmış gerçek dolum saatleri olarak sunulmaz.

Kabul edilen işlem kaydında `Tarih` işlem günü, `Sinyal Tarihi` önceki gözlenen
gün, `Yürütme Modeli` ise `next_open` olur. COMBO ardından HUNTER ve her biri
içindeki ÇOK UCUZ / BELEŞ / PAHALI sırası korunur; aynı açılışta birden fazla
eylem mümkündür. Maliyet/FIFO sınırları değişmez. Tek sembol arayüzünde equity,
kaynak satır indeksi 10'un katı olduğunda ve son uygun günde Close ile gün sonu
değeri olarak kaydedilir; gerçekleşmiş işlem adedi sayılmaz. Ortak portföy
runner'ının her ortak işlem gününde tek kayıt üreten değerlemesi
[ayrı sözleşmede](BACKTEST_PORTFOLIO.md) tanımlanır.

## Girdi ve hata davranışı

`run_single_symbol(..., data=frame)` yolu sağlayıcıya gitmez. Girdi kopyalanır,
tarihler sıralanır ve ilk portföy değişikliğinden önce doğrulanır:

- Tekil `Open`, `High`, `Low`, `Close`, `Volume` sütunları ve `DatetimeIndex`
  gerekir. Mükerrer sütun/tarih, NaT ve gün içi tarih reddedilir.
- Kabul edilen prefix'te gerçek sayısal sütunlar gerekir. Boolean, complex,
  sayısal metin/object, NaN/sonsuz, sıfır/negatif OHLC fiyatı ve negatif hacim
  reddedilir. High/Low, Open ve Close'u kapsamalıdır. Sıfır hacim kabul edilir.
- `open_quality` eksik/None ise veya `provider` ise kabul edilir. `close_proxy`,
  `aof_proxy`, `synthetic_fallback`, `mapped` ve bilinmeyen değerler reddedilir.
  Alanın olmaması veya None olması, çağıranın sağladığı Open'ın gerçek açılış
  olduğu sözleşmesidir;
  verinin gerçek kaynağını otomatik olarak kanıtlamaz.
- BIST'in mevcut İş Yatırım adaptörü gerçek açılış bulamazsa Close veya AOF
  proxy'sini işaretler. Bu veri yeni yürütmede açık bir `ValueError` ile
  durur; fallback fiyatla backtest üretmez. Sağlayıcının gerçek açılış alanı
  bulunmadan o veri kümesi için next-open sonucu alınamaz.
- Piyasa yalnız `BIST` veya `CRYPTO` olabilir ve `Portfolio.market_type` ile
  eşleşmelidir. Hatalı piyasa/sembol ve constructor tarihleri sağlayıcı
  çağrısından önce reddedilir. Geçersiz girdi `ValueError` üretir; sağlayıcıdan
  `None` veya yetersiz uygun geçmiş alınması ise `None` sonucu verir.

İndeks/sütun yapısı tüm girdide doğrulanır. Fiyat/hacim doğrulaması, bitiş ve
kapanış sınırlarına göre kesilmiş geçmişte uygulanır; başlangıç öncesi ısınma
satırları buna dahildir. Kesme, 120 satır yeterlilik kontrolünden önce yapılır.
Geçerli veriye sabit `end_date`/`as_of` dışından satır eklemek eski işlemleri
etkilememelidir. Sınır **içindeki** geçmiş değişirse veya 119 satır120'ye
çıkarsa aynı sonuç garantisi yoktur.

```python
engine = BacktestEngine(
    start_date="2020-03-15",
    end_date="2020-06-08",
    as_of="2020-06-09T00:00:00Z",
)
portfolio = Portfolio(100000.0, "BIST", 1000.0)
engine.run_single_symbol("AAA", "BIST", portfolio, data=daily_ohlcv)
```

`daily_ohlcv` bu örnekte çağıranın sağladığı, yukarıdaki sözleşmeye uyan sabit
DataFrame'dir. Tekrarlanabilirlik aynı veri, parametre, maliyet ve hesaplayıcı
sürümleri için geçerlidir. `as_of` tek başına sağlayıcıdaki geçmiş revizyonları,
düzeltmeleri veya göreli “8 years ago” indirme başlangıcını dondurmaz.

## Çoklu periyot ve runner sınırları

Haftalık/aylık hesaplama, **kapanmış günlük prefix'ten gelişen HTF snapshot**
üretmeye devam eder. Son HTF grubunun henüz tamamlanmamış olması tek başına
gelecek veri sızıntısı değildir. Bütün periyotlarda yalnız tamamlanmış mum
kullanma politikası uygulanmadı; bu ayrıca strateji davranışını değiştirir.
Resampler indeksi ilk işlem günüdür, grubun kapanış zamanı değildir.

Paralel worker artık aynı sembolü iki kez indirmez; tek sağlayıcı okuması
engine içindedir. Eski dört elemanlı worker tuple'ı korunur; altı elemanlı
yol `end_date` ve `as_of` taşır. `run_parallel_backtest` bunları keyword-only
alır ve tüm worker'lara aynı sabit kapanış anını verir. Bu runner'a sabit
DataFrame koleksiyonu API'si eklenmedi. Her worker kendi sermaye/portföyünü
kullanır; sonuçlarının toplamı ortak nakitli bir portföy değildir.

P3-1 beşinci adımda `run_backtest(..., data_by_symbol=...)`, sabit günlük
eşlemeyi ortak nakitle tarih sırasına koyar ve açık pozisyonları son bilinen
kapanışlarıyla birlikte değerler. Tam eşleme, deterministik aynı gün sırası,
günlük equity ve eski fiyatların görünürlüğü
[ortak portföy sözleşmesindedir](BACKTEST_PORTFOLIO.md). Tek sembol arayüzü başka
sembollerin açık pozisyonlarını içeren portföyü ilk işlemden önce reddeder.

Son adımın [benchmark](BACKTEST_BENCHMARK.md), doğru adlandırılmış
[al-tut pencere analizi](BACKTEST_WINDOW_ANALYSIS.md) ve [tam fixture CLI](BACKTEST_CLI.md)
kabulü bu yürütme sözleşmesini kullanır. SVG grafik için matplotlib gerekmez;
bağımsız paralel runner'ın tqdm bağımlılığı ayrıdır. Günlük yürütme birim testleri
stub sinyaller kullanır; CLI kabulü gerçek COMBO/HUNTER hesaplayıcılarını sentetik
veride çalıştırır. Üretim verisine veya borsa emrine erişmez.
