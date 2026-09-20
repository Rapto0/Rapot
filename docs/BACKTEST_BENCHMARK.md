# Benchmark karşılaştırma sözleşmesi

P3-1 son adımında `BenchmarkComparison`, gerçekleşmiş kâr yerine son portföy
değerini (NAV) kullanır. İlk işlem gününün açılışından hemen önceki nakit ile
son işlem gününün kapanış değeri karşılaştırılır. Açık pozisyonlar, alış ve
gerçekleşmiş satış maliyetleri bu NAV'ın içindedir. Açık lotların henüz
gerçekleşmemiş satış gideri düşülmez.

```python
comparison = BenchmarkComparison(
    start_date="2020-01-01",
    end_date="2020-06-30",
    as_of="2020-07-01T00:00:00Z",
)
result = comparison.compare(portfolio, "CRYPTO", data=benchmark_daily)
```

`data` günlük OHLCV DataFrame'i verilirse sağlayıcı çağrılmaz. Normal kripto
yolu BTCUSDT verisini bir kez okur. BIST için varsayılan benchmark devre dışıdır;
açıkça sağlanan veri `supplied:BIST` olarak etiketlenir, kendiliğinden BIST100
kabul edilmez. Sağlanan kripto verisi de `supplied:CRYPTO` olarak görünür.

## Aynı dönem ve değerleme

Ortak runner ile temiz tek sembol koşumu `comparison_start`, `comparison_end`
ve `comparison_initial_value` bilgilerini portföye koyar. Böylece tek sembol
equity kaydının daha seyrek olması başlangıç tarihini ileri taşımaz. Daha önce
işlem/equity kaydı veya açık pozisyon içeren tek sembol portföyüne yeni koşu
eklenirse bu kıyas için güvenilir başlangıç atanmaz.

- Portföy getirisi: `(son NAV / başlangıç nakdi − 1) × 100`.
- Brüt benchmark: `(son gün Close / ilk gün Open − 1) × 100`.
- Maliyetli benchmark: `(son Close / (ilk Open × (1 + alış maliyet oranı)) − 1) × 100`.
- `alpha`: portföy getirisi eksi maliyetli benchmark getirisi, yüzde puan.

Benchmark bütün başlangıç parasını ilk gün alıma ayırır ve sonunda açık tutar;
likidite, vergi, temettü, finansman veya tam lot kısıtı eklenmez. Maliyet oranı
varsayılan olarak portföyün komisyon+kayma oranıdır; açık `costs` seçimi bunu
değiştirebilir. Bu al-tut NAV kıyasıdır; risk ayarlı alfa veya tahmin modeli değildir.
Portföy NAV'ı mevcut equity sözleşmesindeki iki ondalıklı tutardır.

Benchmarkta tam başlangıç ve bitiş günleri bulunmalıdır. Eksik gün başka güne
kaydırılmaz; gelecek fiyat veya önceki değerle doldurulmaz. Tek günlük aralık
gerçek Open→Close hareketini ölçebilir. Ortak portföyün eskimiş kapanışla taşınan
pozisyonları varsa `stale_symbols` çıktısı bunu korur; bu fiyatın satılabilirliğini
garanti etmez.

## Veri ve hata davranışı

Veri kopyalanır ve günlük yürütmenin OHLCV, piyasa saat dilimi, gerçek Open,
`end_date` ve sabit `as_of` kontrollerinden geçer. Ayrıca benchmark `start_date`
sınırı uygulanır. Başlangıç/bitiş kapanmamışsa veya sınır dışında kalıyorsa
kıyas hesaplanamaz. [Yürütme sözleşmesi](BACKTEST_EXECUTION.md) ayrıntıları açıklar.

`status="unavailable"` durumunda `benchmark_return` ve `alpha` **None** olur;
`reason` eksik dönemi, devre dışı benchmarkı, sağlayıcının veri döndürmemesini
veya eksik uç günleri açıklar. Portföy dönemi mevcutsa kendi getirisi korunur.
Geçerli sıfır getiri `status="available"` ile döner; veri yokluğundan farklıdır.
Elle kurulmuş, dönem bilgisi olmayan portföy için başlangıç varsayılmaz.
Son equity kaydı işlem sayısını da taşır. Sonradan işlem yapılmışsa (aynı gün
ve aynı nakitle satış/yeniden alış dahil) veya nakit değişmişse eski değerleme
`stale_portfolio_valuation` ile reddedilir; önce yeniden değerleme gerekir.

Her yeni veri okuması önce eski benchmark önbelleğini kaldırır. Sağlayıcı
istisnası veya hatalı veri çağırana ulaşır; önceki başarılı veriyle kıyas
üretilmez. `calculate_benchmark_return` yalnız doğrulanmış mevcut önbellekteki
**brüt** getiriyi hesaplar; kullanıcıya sunulan maliyetli kıyas `compare` sonucudur.

Testler sentetik veriyle açık pozisyon, maliyet, aynı gün, tam tarih uçları,
BIST/UTC kapanışı, önbellek yenileme hatası, sabit veri ve sağlayıcı tek okumasını
doğrular. Gerçek piyasa performansı veya canlı kazanç kabulü değildir.
