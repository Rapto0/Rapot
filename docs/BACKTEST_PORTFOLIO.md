# Ortak nakitli çoklu sembol backtest sözleşmesi

P3-1 beşinci adım, `backtesting_system.py::BacktestEngine.run_backtest` için
sembolleri ortak nakitle tarih sırasına koyar ve açık pozisyonları birlikte
değerler. Ayrı CLI modülü kapsamındadır; scanner, dashboard, Pine ve middleware
emir yolu değişmez. [Günlük yürütme](BACKTEST_EXECUTION.md) ile
[maliyet/FIFO muhasebesi](BACKTEST_ACCOUNTING.md) korunur. Sonuç gerçek borsa
dolumu, strateji getirisi veya yatırım önerisi kabulü değildir.

## Girdi ve hazırlık

```python
portfolio = engine.run_backtest(
    ["AAA", "BBB"],
    "BIST",
    initial_cash=100000.0,
    trade_amount=1000.0,
    data_by_symbol={"AAA": daily_aaa, "BBB": daily_bbb},
    costs=trading_costs,
)
```

`daily_aaa` ve `daily_bbb`, çağıranın sağladığı günlük OHLCV DataFrame'leridir.
`data_by_symbol` ve `costs` yalnız anahtar sözcükle verilen isteğe bağlı
argümanlardır. Sabit veri eşlemesinin anahtarları istenen sembollerle tam
eşleşmelidir; eksik/fazla anahtar sağlayıcıya dönüş yapmaz. Bu yol hiçbir
sembol için sağlayıcı çağırmaz. Sabit eşleme verilmezse her sembolün sağlayıcısı
bir kez okunur; aynı engine'in sabit `as_of` sınırı hepsine uygulanır.

Semboller, maliyetler ve bütün girdiler ilk işlemden önce doğrulanır; günlük
veriler kopyalanır. Hatalı girdi `ValueError` ile durur. Bir sembolde hata
oluştuğunda önceki sembollerin kısmi işlemleri başarı sonucu gibi döndürülmez.
Sağlayıcının `None` döndürmesi, 120'den az uygun satır veya aralıkta işlem günü
kalmaması ayrı atlama durumlarıdır. Sabit eşlemede `None` geçerli DataFrame
sayılmaz. Sağlayıcıdan veya `check_signals` çağrısından dışarı çıkan istisnalar
runner tarafından yutulmaz; hesaplayıcının mevcut periyot bazlı hata politikası
değişmez.
`portfolio.backtest_metadata` içindeki
`processed_symbols` ve `skipped_symbols`, işlenen ve atlanan sembolleri açıklar.
İşlenmiş bir sembolün hiç sinyal/işlem üretmemesi tek başına atlama değildir.

120 satır koşulu, `end_date`/`as_of` ile kabul edilen tüm örnekleme uygulanır.
İlk olası işlem yine indeks 61'dir. Dolayısıyla daha sonraki kabul edilen
satırlar bir sembolün bu eşiği geçmesini sağlayabilir; bu yeterlilik kuralı
tarihsel her günde bilinen sembol evrenini modellemez. Önceki kapanış prefix'i
dışında sinyal verisi kullanılmaması, tek başına tamamen nedensel evren seçimi
veya survivorship bias yokluğu garantisi değildir.

## Ortak tarih ve nakit sırası

1. Her uygun sembol için kendi işlem günleri belirlenir. Bu günlerin birleşimi
   artan tarih sırasıyla işlenir; takvimde olmayan mumlar oluşturulmaz.
2. Aynı gün işlem satırı olan semboller ham sembol metni sırasıyla ele alınır;
   harf dönüşümü veya yerel alfabe sıralaması uygulanmaz. Liste sırasını
   değiştirmek nakit tahsisini değiştirmez. Bu kural piyasa önceliği veya
   eşzamanlı emir eşleştirmesi değildir.
3. Bir sembolün önceki kapanmış prefix'i COMBO, ardından HUNTER için kullanılır.
   Her stratejide ÇOK UCUZ, BELEŞ, PAHALI sırası korunur. Bütün sembollerin
   satışlarını alışlardan önce yapan ayrı bir sıralama yoktur.
4. İşlemler o sembolün ilgili günündeki gerçek Open üzerinden mevcut sabit
   bütçe ve FIFO kurallarıyla yürütülür. Yetersiz nakitli alış gerçekleşmez;
   sonraki günün satışı geçmişteki alışa nakit sağlayamaz. Aynı gün önceki
   sembolün işlemleri sonraki sembole kalan nakdi etkileyebilir.

Örneğin AAA'nın 10 Haziran satışı, BBB'nin 5 Haziran alışını finanse edemez.
İki sembol aynı gün alış isterken nakit yalnız birine yetiyorsa, ham metin
sırasındaki ilk sembolün işlemleri önce değerlendirilir. Bu sonuç liste
sırasından bağımsızdır; eşit sermaye paylaştırma modeli değildir.

## Gün sonu değerleme

Her ortak işlem gününde bütün açılış işlemleri tamamlanır, ardından o güne
ait mevcut Close fiyatları güncellenir. Ortak portföye **bir** equity kaydı
eklenir:

`portföy değeri = nakit + Σ(açık miktar × son bilinen Close)`

Bir sembolün o gün mumu yoksa, o tarihten önceki son gözlenen kapanışı taşınır.
Verisi diğer sembollerden önce biten açık pozisyon da son kapanışıyla
taşınmaya devam eder; otomatik satış, sıfır değer, maliyet fiyatı veya gelecekteki
bir kapanışla geriye doldurma yapılmaz. Taşıma için azami eskilik süresi yoktur.
Bu, askıya alınmış/delist olmuş varlığın o fiyattan satılabileceğini göstermez.

Equity satırının `Fiyat Tarihleri` alanı açık pozisyonların kullanılan kapanış
günlerini, `Eski Fiyatlı Semboller` alanı o equity gününden eski kapanışla
değerlenen sembolleri gösterir. Böylece güncel olmayan fiyat sessizce güncel
fiyat gibi sunulmaz. Tarihler piyasa gün etiketleridir; gerçek işlem saati
değildir.

`Portfolio.get_portfolio_value` bütün açık pozisyonlar için sonlu ve pozitif
fiyat ister. Eksik, sıfır, negatif veya sonlu olmayan fiyat kabul edilmez;
son lotun alış fiyatına örtülü dönüş yoktur. Yalnız nakit olan portföy açık
pozisyon fiyatı gerektirmez. Açık pozisyon değeri henüz gerçekleşmemiş satış
komisyonu/kaymasını düşmez; gerçekleşmiş PnL ve açık maliyet tabanı ayrı kalır.

## Tek sembol, paralel runner ve kapsam

`run_single_symbol` önceki kapanış → sonraki Open sözleşmesini ve kaynak
indeksi 10'un katlarında/son uygun günde equity kaydetme sıklığını korur.
Kendisine verilen portföyde başka sembole ait açık pozisyon varsa ilk işlemden
önce reddeder; eksik fiyatla ortak portföy kaydı üretmez.
`run_backtest(["AAA"], ...)` ise ortak runner olduğu için her uygun işlem
gününde equity kaydeder. İşlem sırası/maliyet kuralları aynıdır; iki arayüzün
equity kayıt sayısının aynı olması beklenmez.

`run_parallel_backtest` bağımsız sembol deneyleridir: her worker kendi
sermayesini ve portföyünü oluşturur. Worker kârlarını toplamak, burada
tanımlanan ortak nakitli portföyün sonucu değildir. Bu adım paralel runner'ı
ortak sermaye motoruna dönüştürmez.

Bir koşum tek piyasa ve tek para birimi varsayar; BIST/CRYPTO arasında ortak
nakit veya döviz dönüşümü eklenmedi. Gerçekleşmiş PnL ayrı bir ölçüt olarak
korunur; son adım [benchmark](BACKTEST_BENCHMARK.md), [pencere analizi](BACKTEST_WINDOW_ANALYSIS.md)
ve [tam CLI](BACKTEST_CLI.md) kabulünü ekler. Maliyet modeli,
tek en eski lotu tam satma FIFO davranışı, günlük kapanış sınırı ve gelişen HTF
politikası önceki sözleşmelerdeki gibidir.
