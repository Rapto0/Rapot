# Dönemsel buy-and-hold analizi

P3-1 altıncı adımda `backtesting_system.py` içindeki eski `WalkForwardAnalysis`
adı düzeltildi. Kod daha önce `strategy` parametresini ve eğitim verisini
hesaplamada kullanmadan Close→Close getirilerini bu stratejinin sonucu gibi
etiketliyordu. Varsayılan pencere kaydırması son dönemin yaklaşık %40'ını da
dışarıda bırakıyordu. Canonical sınıf artık **`RollingBuyAndHoldAnalysis`**.

Bu araç, ayrı dönemlerde tek varlığı alıp tutma sonuçlarını özetler. COMBO veya
HUNTER sinyali, parametre eğitimi, optimizasyon, strateji seçimi ve gerçek
walk-forward doğrulaması çalıştırmaz. Sonuçta `model=rolling_buy_and_hold`,
`strategy=buy_and_hold`, `strategy_evaluated=false`,
`optimization_performed=false` ve `history_usage=context_only_no_training`
alanları bu kapsamı taşır. Gerçek strateji yürütmesi
[günlük yürütme](BACKTEST_EXECUTION.md) ve
[ortak portföy](BACKTEST_PORTFOLIO.md) arayüzlerinin işidir.

## Veri ve tarih sınırları

```python
analysis = RollingBuyAndHoldAnalysis(
    n_splits=5,
    history_ratio=0.7,
    start_date="2020-01-01",
    end_date="2020-12-31",
    as_of="2021-01-01T00:00:00Z",
    costs=TradingCosts(),
)
result = analysis.run("BTCUSDT", "CRYPTO", data=daily_ohlcv)
```

`data` verildiğinde sağlayıcı çağrılmaz; verilmezse seçilen piyasanın sağlayıcısı
bir kez okunur. `as_of` nesne kurulurken bir kez sabitlenir ve açıkça verildiğinde
saat dilimli olmalıdır. Başlangıç/bitiş günleri dahildir. Ortak günlük doğrulayıcı
OHLCV'yi kopyalar, sıralar ve tarih/kolon tekilliği, sonlu pozitif OHLC,
negatif olmayan hacim ve High/Low tutarlılığını kontrol eder. Açılış proxy'si
ve bilinmeyen `open_quality` reddedilir; eksik/None veya `provider` kabul edilir.

Her günlük satırın piyasa takvimindeki sonraki gece yarısı `as_of` anına
ulaşmış olmalıdır: BIST için Europe/Istanbul, kripto için UTC. Güncel açık
mum muhafazakâr biçimde dışlanır. Bitiş/kapanış filtresinden sonra başlangıçtan
önceki satırlar da çıkarılır; bu analizde sinyal ısınması için başlangıç öncesi
veri tutulmaz. Eksik takvim günleri doldurulmaz.

## Pencere sözleşmesi

Kabul edilmiş aralıkta `N` satır varsa ilk `floor(N × history_ratio)` satır
yalnız başlangıç bağlamıdır. Kalan **bütün** satırlar, tarih sırasıyla
`n_splits` adet çakışmayan değerlendirme penceresine bölünür. Bölme artığı ilk
pencerelere birer satır olarak dağıtılır; boyutlar en fazla bir farklıdır.
Her pencerenin geçmiş bağlamı kendisinden önceki bütün satırları kapsar,
ancak bu bağlamdan model eğitilmez veya alım/satım kararı türetilmez.

Örneğin `N=11`, `history_ratio=0.3`, `n_splits=3` için ilk 3 satır bağlam;
sonraki pencereler 3, 3 ve 2 satırdır. Son gözlem mutlaka son pencerededir.

`n_splits` pozitif tam sayı, oran sonlu ve `0 < history_ratio < 1` olmalıdır;
boolean değerler kabul edilmez. En az bir başlangıç bağlamı satırı ve her
pencereye en az bir değerlendirme satırı gerekir. Gösterge veya strateji
hesaplanmadığından eski **120 toplam / 30 eğitim / 10 test** eşikleri bu
analize taşınmadı. Tek günlük pencere, o günün Open→Close tutma getirisidir.
Yetersiz veri veya geçersiz seçenek, boş bir başarı/0 getiri yerine hata verir.

## Fiyatlama, masraf ve özet

Her pencere **bağımsız 1 birim başlangıç sermayesiyle**, ilk satırın gerçek
Open fiyatından alıp son satırın Close fiyatından tamamen satar. Önceki
pencerenin nakdi, pozisyonu veya getirisi sonrakine taşınmaz. Sonuçlarda
`entry_open`, `exit_close`, `gross_return`, `net_return`, `final_value`,
`commission_paid` ve `slippage_cost` ayrı bulunur.

Tek yön komisyon `c`, kayma `s`, toplam `r=c+s`, açılış `O` ve son kapanış `C`
için mevcut [maliyet sözleşmesi](BACKTEST_ACCOUNTING.md) kullanılır:

```text
alış referans tutarı = 1 / (1 + r)
satış referans tutarı = (C / O) / (1 + r)
son değer = (C / O) × (1 - r) / (1 + r)
brüt getiri (%) = (C / O - 1) × 100
net getiri (%) = (son değer - 1) × 100
```

Komisyon ve kayma her iki yönde ilgili referans tutardan hesaplanır;
kayma ayrıca fiyatın içinde ikinci kez uygulanmaz. Masraflar sıfırsa brüt/net
aynıdır. Bu, bağımsız pencere sonunda satışı varsayan modeldir; ortak portföyün
açık pozisyonları için kullanılan satış masrafı düşülmemiş NAV ile aynı ölçü
değildir. Sayısal taşma hata verir.

`avg_return`, `std_return`, `min_return`, `max_return` net yüzde getirilerin
aritmetik istatistikleridir; standart sapma popülasyon tanımını kullanır.
Getiriler hesapta yuvarlanmaz. Sonuç toplam, bileşik veya yıllıklandırılmış
strateji getirisi olarak sunulmaz. `aggregation` alanı bu bağımsız pencere
tanımını açıklar. `test_return`, uyumluluk için `net_return` ile aynıdır.

## Eski adla uyumluluk ve hatalar

`WalkForwardAnalysis(n_splits=..., train_ratio=..., ...)` ve
`run_walk_forward(symbol, market_type, strategy="combo", data=...)` çalışmaya
devam eder. Eski sınıf ve yöntem `FutureWarning` üretir. `train_ratio` yalnız
`history_ratio` için eski bir yazımdır; eğitim iddiası taşımaz. Eski
`train_start`/`train_end` çıktı alanları bağlam sınırlarının alias'larıdır.

`strategy` parametresi kabul edilir ancak kullanılmaz. Sonuçtaki `strategy`
daima `buy_and_hold`; kullanıcının eski argümanı `ignored_strategy` alanında,
uyarı ise `warning` ve `legacy_api` alanlarında bulunur. Önceden yanlış
strateji etiketi taşıyan sonuçlarla birebir sayısal uyum iddia edilmez:
kapsama, Open girişi ve iki yönlü masraflar bilinçli düzeltmelerdir.

Her yeni `run` önce `results` durumunu boşaltır; doğrulama/sağlayıcı hatası
eski başarılı sonucu bırakmaz. Sağlayıcı `None` dönerse veya veri yetersizse
`ValueError`; sağlayıcı istisnası varsa özgün istisna çağırana iletilir.
Hatalar 0 getiriyle örtülmez ve yarım pencere sonucu yayımlanmaz.

## Sentetik kabul

`tests/test_backtest_window_analysis.py` içindeki **40 test**; eski iki RED
kusurunu, tam/çakışmasız kapsama, bağımsız aritmetik özet, Open fiyatı,
kesirlerle hesaplanan masraf oracle'ı, tek günlük pencere, geçersiz seçenekler,
BIST/kripto kapanış sınırları, başlangıç/bitiş filtresi, değişmez/sırasız
girdi, gelecek fiyat etkisi, tek sağlayıcı okuması, hata sonrası durum temizliği,
legacy uyarıları ve taşmayı kapsar. Koşum ağsızdır; gerçek sağlayıcı veya
borsa emri çalıştırılmış kabul edilmez.
