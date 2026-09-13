# COMBO/HUNTER hesaplayıcı farkları

13 Eylül 2026, P3-1 ikinci adım. Bu belge hesaplayıcı davranışını karşılaştırır;
strateji getirisi, canlı emir doğruluğu veya üç motorun eşdeğerliği iddiası değildir.

## Ölçümün kapsamı

`tests/fixtures/strategy_ohlcv.json` yedi ayrı 80 mumluk sentetik OHLCV dizisi
tutar: aralıksız düz fiyat, fiyatı düz fakat aralığı olan mumlar, yükseliş,
düşüş, dönüşümlü hareket, yön değişimi ve boşluk/sıçrama. Veriler değişmez JSON
değerleridir; sağlayıcı, kullanıcı veritabanı veya ağ kullanılmaz. Her dizinin
0, 1, 2, 7, 8, 12, 13, 14, 15, 19, 20, 21, 25, 26, 27, 28, 29, 30, 40 ve 80
mumluk başlangıç parçaları ayrı değerlendirilir.

Python testi gerçek `signals.py` fonksiyonlarını, Node adaptörü gerçek
`frontend/src/lib/indicators.ts` kaynağını çalıştırır. Python'un public ayrıntıları
yuvarlanmış olduğundan ham `v_*` değerleri yalnız hedef fonksiyonun dönüşünde
geçici profiling callback'iyle alınır. Gösterge formülleri ölçüm aracında yeniden
yazılmaz. Rapor; public çıktının bulunmasını, hesaplanmama/NaN/sonsuz/sonlu
durumlarını, ham değerleri, puanları ve AL/SAT kararlarını ayrı karşılaştırır.

`1D` ve `ME`, aynı tamamlanmış mum dizisine uygulanan **puan politikası**
etiketleridir. Zaman koordinatları UTC günlük olsa da ME ölçümü aylık yeniden
örnekleme değildir. İki etiket de aynı girdi dizisini kullanır. Açık mum,
sağlayıcı düzeltmesi ve gerçek çoklu zaman dilimi toplaması bu ölçüme dahil değil.

| Sözleşme | Python | TypeScript |
|---|---|---|
| Public veri yeterliliği | 1D en az 30; ME en az 8; ayrıca aktif gösterge gerekli | COMBO en az 26, HUNTER en az 30; sonra tüm geçmiş satırları döner |
| COMBO varsayılan puan | 1D 4/3, ME 3/3 | 2/2 |
| HUNTER varsayılan puan | 1D 7/10, ME 5/10 | 3/4 |
| HUNTER BOP eşiği | −0,7 / +0,7 | −0,5 / +0,5 |
| HUNTER eşik eşitliği | MACD hariç `<=` / `>=` | `<` / `>` |
| Karar gösterimi | BUY ve SELL ayrı boolean | Tek sinyal; iki kota sağlanırsa SAT öncelikli |

Rapor hem TypeScript'in kendi varsayılanlarını hem yalnız toplam puan ve BOP
eşikleri Python'a ayarlanmış profilleri içerir. Bu eşleştirme RSI, EMA, ATR,
standart sapma, eşik eşitliği veya public çıktı sözleşmesini değiştirmez.

## Sentetik ölçüm sonucu

Her grup 7 dizi × 20 başlangıç parçası = 140 gözlem içerir. Puan ve karar farkı
yalnız **iki motorun da public çıktı verdiği** gözlemlerde sayılır. `native`,
TypeScript varsayılanlarını Python 1D politikasıyla karşılaştırır.

| TS profili / strateji | İkisinde public çıktı | Public var/yok farkı | Puan farkı | AL/SAT karar farkı |
|---|---:|---:|---:|---:|
| native / COMBO | 21 | 28 | 6 | 2 |
| native / HUNTER | 21 | 0 | 8 | 3 |
| 1D / COMBO | 21 | 28 | 6 | 0 |
| 1D / HUNTER | 21 | 0 | 14 | 0 |
| ME / COMBO | 49 | 42 | 16 | 0 |
| ME / HUNTER | 21 | 91 | 14 | 0 |

Eşleştirilmiş puan politikalarında bu örneklerde nihai karar aynı kaldı;
ham değerler ve puanlar hâlâ farklı. Bu sonuç genel karar eşitliğini kanıtlamaz.
Gelecek mum eklendiğinde aynı geçmiş gözlemin değişmemesi, **2.527 Python ham
bileşen** ve **210 TypeScript public satır** karşılaştırmasında doğrulandı.
Bu kontrol sağlayıcı geçmiş düzeltmesi veya Pine realtime yürütmesi değildir.

Ölçüm ortamı Python 3.12.8, Node 20.20.2, TypeScript 5.9.3, NumPy 1.26.4,
pandas 2.3.3, ta 0.11.0'dır. Ham rapor 560 Python ve 840 TypeScript gözlemi
tutar; kaynak/fixture hash'leri CRLF→LF normalizasyonuyla Windows ve Linux'ta
aynı canonical metne bağlanır. JSON rapor dosyasının kendi SHA256'sı ayrıca
yayın kaydında tutulur.

## Kaynaklardan doğrulanan farklar

Python sütunu kilitli ortamı (`ta`, `pandas_ta` yok) anlatır. İsteğe bağlı
`pandas_ta` kurulursa mevcut fallback yolu değişebileceğinden bu kabul aktarılamaz.

| Gösterge | Python | TypeScript |
|---|---|---|
| RSI 14/7/2 | İlk gözlemlerden EWM; düz seride 100 | İlk N fiyat değişiminin SMA başlangıcı, sonra Wilder; düz seride 50 |
| MACD | İlk kapanıştan başlayan EWM; yavaş periyot dolmadan NaN | EMA için SMA başlangıcı; ilk satırlarda da değer |
| CMO | Fallback `2 * RSI - 100`; düz seride 100 | Son 14 değişimin yükseliş/düşüş toplamları; düz seride 0 |
| BOP | Sıfır aralık/eksik sonuç 0 | Sıfır aralık 0; normal sonlu girdilerde aynı oran |
| Williams %R | Sıfır aralıkta NaN | Sıfır aralıkta −50 |
| CCI | Sıfır ortalama mutlak sapmada NaN | Aynı durumda 0 |
| Ultimate | Sıfır true range toplamında NaN | Aynı durumda 0 |
| Bollinger %B | Örneklem sapması (`ddof=1`), paydada epsilon; düz seride 0 | Popülasyon sapması (`ddof=0`); düz seride 50 |
| ROC | Pozitif önceki kapanışta aynı oran; işlem sırası küçük yuvarlama farkı yaratabilir | Aynı sınır; önceki kapanış 0 ayrıca sonlu olmayan sonuç üretebilir |
| DeMarker | İlk değer 14. mum; düz seride 0, paydada epsilon | İlk değer 15. mum; düz seride 50 |
| PSY | İlk değer 12. mum | İlk değer 13. mum; sonraki aynı pencerelerde aynı yükseliş sayımı |
| Z-Score | `ddof=1`, paydada epsilon | `ddof=0`; iki yol da düz seride 0 |
| Keltner %B | İlk kapanıştan EMA merkezi; ATR Wilder `1/20`; düz seride 0 | SMA başlangıçlı EMA merkezi; ATR EMA `2/21`; düz seride 50 |

COMBO frontend'inde sıfır/eksik ayrımı ve `Number.isFinite` puanlama ilk P3-1
adımında düzeltildi. Python ve TypeScript HUNTER'ın NaN kontrolü sonsuzluğu
reddetmekle aynı değildir; tüm motorların geçersiz OHLCV/sonsuzluk sözleşmesi
bu sentetik sonlu veri ölçümüyle kapatılmaz. Alarm tüketicisi ayrıca son kaydın
bütün bileşenlerinin sonlu olmasını ister; hesaplayıcıda sinyal bulunması tek
başına yerel alarm kabulü değildir.

## Pine EMA/ATR başlangıç sınırı

`middleware/pine/combo_hunter_binance.pine` içindeki özel `HtfBar` hesaplayıcısı
kapalı mum dizisine gelişmekte olan mumu ekler. `total()` bu toplamdır;
`getC/H/L` dizi sınırının üzerindeki indekslerde gelişen mum değerini döndürür.
Bu yol, aynı dosyadaki `ta.*` kullanan native hesaplayıcıyla aynı değildir.
`confirmClose` ve `watchlistIntrabar` mevcut grafik mumunun kapanışını kapılar;
üst zaman dilimindeki gelişen mumun otomatik çıkarılması anlamına gelmez.

Pine `for` döngüsünde başlangıç bitişten büyükse sayaç aşağı ilerler.
Bu nedenle EMA'da `n == len`, ATR'de `n == len + 1` iken devam döngüsü
boş kalmıyor, iki güncelleme daha yapıyordu. Devam koşulları sırasıyla
`n > len` ve `n > len + 1` olarak sınırlandı. Başlangıç formülleri, eşikler,
HTF toplaması ve alarm sözleşmesi aynı kaldı.
[Resmi Pine döngü açıklaması](https://www.tradingview.com/pine-script-docs/language/loops/#for-loops)

| Elle hesaplanan sınır | Eski sonuç | Düzeltilmiş sonuç |
|---|---|---|
| EMA(3), kapanışlar 10,20,30 | 27,5 | 20 |
| Aynı seriye 40 eklenmesi | 30 | 30 |
| ATR(3), ilk üç TR 2,2,9 | 145/27 ≈ 5,37037 | 13/3 ≈ 4,33333 |
| Aynı seriye TR=2 eklenmesi | 32/9 ≈ 3,55556 | 32/9 ≈ 3,55556 |

Regresyon testi yalnız gerçek iki Pine fonksiyon gövdesinin izin verilen dar
sözdizimini yorumlar. Genel Pine derleyicisi, `ta.*` yürütücüsü veya TradingView
kabulü değildir. Mevcut kullanıcı derleme/grafik kabulü 9–10 Eylül kaynağına
aittir; değişmiş kaynağın TradingView derlemesi ve yürütmesi ayrıca açık kalır.
Pine'ın RSI/CCI tepe eşikleri, gösterge ağırlıkları, native/custom hesaplama ve
çoklu HTF koşulları nedeniyle son Pine alarmını Python/TS puanıyla eşdeğer
saymak mümkün değildir. Sayısal Python/TS raporunda Pine çalıştırılmış gösterilmez.

## Tekrarlama

Önce seçili Python 3.12 kilit ortamı ile Node 20 / npm 10 frontend bağımlılıkları
kurulmuş olmalıdır. Node yürütücüsü PATH'te değilse `NODE_BINARY` tam yoluyla
seçilir. Eksik/yanlış Node sürümü karşılaştırmanın sessizce atlanmasına yol açmaz.

```powershell
$env:RAPOT_STRATEGY_REPORT = Join-Path (Get-Location) 'runtime-data/strategy-comparison.json'
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_strategy_comparison.py middleware/tests/test_pine_indicator_boundaries.py middleware/tests/test_pine_contract.py -q
```

Rapor yalnız ortam değişkeniyle açık bir yol verildiğinde yazılır; normal testler
rapor dosyası oluşturmaz. CI kilitli iki ortamı kurar ve aynı raporu commit SHA'sı
taşıyan `strategy-comparison-*` artifact'i olarak 14 gün saklar. Kaynak/fixture
hash'leri ve runtime sürümleri raporda bulunur. Ham sayılar sentetik örneklere
aittir; fark oranı gerçek piyasa genelindeki hata veya başarı oranı değildir.

Ölçüm sonucu ve doğrulama sayıları [devam planındaki P3-1 kaydına](RAPOT_DEVAM_PLANI.md#p3-1--backtest-ve-strateji-eşdeğerliği)
eklenir. Motor formüllerini topluca eşitleme kararı verilmedi; sonraki uygulama
alış maliyeti dahil backtest nakit–PnL muhasebesidir.
