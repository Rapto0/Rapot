# Binance Spot middleware Pine alarm sözleşmesi

`combo_hunter_binance.pine`, altı COMBO/HUNTER sinyalini
`POST /webhooks/tradingview` payload'una çevirir. Miktar ve risk kontrolleri
middleware'dedir; Pine miktar, API key, secret veya broker token göndermez.

## İzin verilen grafik

Alarm için bütün koşullar sağlanmalıdır:

- Borsa `BINANCE`, enstrüman türü `crypto` olmalıdır.
- `syminfo.ticker`, basecurrency + currency birleşimine eşit olmalıdır.
- Sembol en fazla 24 ASCII harf/rakamdan oluşmalıdır.
- `chart.is_standard` doğru olmalıdır; Heikin Ashi/Renko gibi sentetik OHLC
  üreten grafikler kabul edilmez.

Örnek: standart `BINANCE:BTCUSDT` grafiği uygundur. `BINANCE:BTCUSDT.P`, vadeli
kontratlar, `BINANCEUS`, başka borsalar ve sentetik grafiklerde alarm kapalıdır.
`.P` veya başka türev işaretleri silinerek Spot sembolüne dönüştürülmez.
Tabloda uygun olmayan grafik için uyarı gösterilir; analiz hesapları devam eder.
Bu koruma piyasanın Binance'te halen işleme açık olduğunu kanıtlamaz; middleware
ayrıca `exchangeInfo` ve hesap/risk kontrollerini uygular.

TradingView, borsa/sembol bilgilerini `syminfo` üzerinden verir; standart ve
sentetik grafik ayrımı `chart.is_standard` ile yapılır.
[Resmi grafik bilgisi belgesi](https://www.tradingview.com/pine-script-docs/concepts/chart-information/)

## Payload v1 ve olay zamanı

```json
{
  "schemaVersion": 1,
  "source": "Combo+Hunter",
  "symbol": "BTCUSDT",
  "ticker": "BTCUSDT",
  "signalCode": "H_BLS",
  "signalText": "Hunter Beles",
  "side": "BUY",
  "price": 50000.00,
  "timeframe": "1D",
  "barTime": 1788919200000,
  "barIndex": 12345,
  "isRealtime": true
}
```

Bu JSON yalnız sözleşme örneğidir; canlı alarm kaydı değildir.

- `barTime = timenow`: milisaniye cinsinden alarmın üretildiği çalışma anıdır.
  **Barın açılış zamanı değildir.** V1 ayrı bir bar açılış zamanı göndermez.
  Middleware freshness/future-skew kontrolü bu olay zamanını kullanır.
- `barIndex`, grafiğin mevcut veri kümesindeki sıradır; kalıcı olay kimliği değildir.
- `timeframe`, Pine'ın `timeframe.period` değeridir: örneğin `1D` veya bir saat
  için `60`. Kod bu değeri `1H` gibi başka bir gösterime çevirmez.
- `price`, alarm anındaki `close` değeridir; `format.mintick` ile yazılır.
- `symbol` ve `ticker`, `syminfo.ticker` değerinin büyük harfli halidir.

| Kod | Metin | Yön |
| --- | --- | --- |
| H_UCZ | Hunter Ucuz | BUY |
| H_BLS | Hunter Beles | BUY |
| C_UCZ | Combo Ucuz | BUY |
| C_BLS | Combo Beles | BUY |
| H_PAH | Hunter Pahali | SELL |
| C_PAH | Combo Pahali | SELL |

V1 idempotency, doğrulanmış payload'un tamamından türetilir ve yürütme kapsamına
göre uygulanır. Aynı HTTP payload'unun tekrar gönderimi aynı emri döndürür.
Aynı barda farklı sinyal kodu veya yeni `timenow` ile yeniden üretilen alarm ayrı
olaydır; kasıtlı tekrarlı BUY biriktirme davranışı korunur. Fiyatın ondalık
yazımı, sinyal metni veya eşdeğer timeframe gösterimi değiştirilirse mevcut hash
değişebilir; v1 semantik eşdeğerlik normalizasyonu yapmaz.

## Preset, saat ve alarm sırası

| Ayar | Manuel varsayılanı | Kripto 24/7 |
| --- | --- | --- |
| Kaynak grafik | Yalnız 1D | Yalnız 1D koşulu korunur |
| Saat filtresi | Açık; 17:45–17:57 | Kapalı |
| Çoklu sinyal | ALL | ALL girişi korunur |
| Realtime / intrabar | Açık / açık | Aynı girişler kullanılır |

`BIST Algo` saat filtresini zorunlu açar; bu preset Binance Spot grafik
korumasını kaldırmaz. Saat filtresi **borsanın `syminfo.timezone` saat dilimini**
kullanır. Başlangıç/bitiş dakikaları dahildir; gece yarısını aşan aralık da
desteklenir. `Kripto 24/7`, günlük grafik zorunluluğunu kendiliğinden kaldırmaz.

- `confirmClose=true`, sinyalin bar kapanışında doğrulanmasını ister.
- `watchlistIntrabar=false`, alarm dispatch'ini kapanış iterasyonuyla sınırlar.
- ALL: aynı barda her farklı sinyal kodu en fazla bir kez gönderilir.
- FIRST: aynı barda ilk oluşan sinyal gönderilir. Aynı iterasyonda birden fazla
  koşul doğruysa öncelik tablodaki sıradır: H_UCZ → H_BLS → C_UCZ → C_BLS →
  H_PAH → C_PAH. Sonraki sinyaller o bar için gönderilmez.

`varip` gönderim bayrakları `barstate.isnew` ile sıfırlanır. Bu, tek çalışan
alarmın bar içindeki belleğidir; yeniden oluşturulan alarmın önceki durumunu
korumaz. TradingView'in bu değişkenlere ilişkin açıklaması:
[Bar states](https://www.tradingview.com/pine-script-docs/concepts/bar-states/).

## Alarm kurulumu ve doğrulama sınırı

Derleme ve dış kabul testi yapılacağı zaman alarm koşulu `Any alert() function
call` seçilir; JSON'u script üretir. Hedef, yapılandırılmış middleware'in
`/webhooks/tradingview?token=<MW_WEBHOOK_AUTH_TOKEN>` adresidir. Yönetim anahtarı
bu URL'ye veya Pine'a konulmaz.

TradingView çalışan alarm için script/girdilerin kopyasını tutar; kod/girdi
değişikliğini kullanması için alarm yeniden oluşturulmalıdır. `alert()` olayları
realtime çalışır; `realtimeOnly=false` geçmiş HTTP alarmları oluşturulduğunun
kanıtı değildir. [Resmi alarm belgesi](https://www.tradingview.com/pine-script-docs/concepts/alerts/)

Yerel kaynak sözleşmesi kontrolü:

```powershell
.venv\Scripts\python.exe -X utf8 -B -m pytest middleware/tests/test_pine_contract.py -q
```

Testler gerçek Pine kaynağındaki grafik koşulunu sahte metadata ile ve diğer
dispatch/payload sözleşmelerini kaynak incelemesiyle kontrol eder. Pine derleyici,
TradingView sunucusu veya tick yürütücüsü değildir. 9 Eylül 2026'da kullanıcı,
tam kaynağın `BINANCE:BTCUSDT` / standart mum / 1D grafiğinde derlendiğini bildirdi;
bu kayıt araçla alınmış derleyici çıktısı değildir. Grafik korumalarının runtime
kontrolü, gerçek alarm JSON'u ve ayrıca izin verilmiş ayrılmış testnet hesabı/DB
üzerinde BUY → FIFO SELL → reconcile kabulü **henüz doğrulanmadı**.
Ayrıntılı kanıt ve kalan adımlar [devam planında](../../docs/RAPOT_DEVAM_PLANI.md).
`strategy()` başlığı ve `realtimeOnly=false`, çalışan backtest kanıtı değildir; scriptte
`strategy.entry/order/exit` emri yoktur.

## Miktar ve FIFO

BUY bütçesi `MW_BINANCE_BUY_QUOTE_AMOUNT_USDT * multiplier(signalCode)` ile
belirlenir; varsayılan 10 USDT'dir. Riskten geçen ve gerçekleşen ayrı BUY'lar
yeni tranche açar; SELL en eski açık tranche'ı kullanır. Binance fiyat/miktar ve
minimum tutar filtreleri middleware'de uygulanır. Testnet başarısı gerçek
hesap doğrulaması veya otomatik LIVE geçişi anlamına gelmez.
