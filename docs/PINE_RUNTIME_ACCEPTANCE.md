# Pine derleme ve grafik kabulü — P3-1

**21 Eylül 2026, 17:57:58 UTC:** Güncel Pine kaynağı TradingView'da derlendi
ve **BINANCE:BTCUSDT / standart Candles / 1D** grafiğinde çalıştı.
Bu kabul, P3-1'in son açık derleme/grafik kriterini kapatır.

## Kaynak kimliği ve aktarım

| Alan | Doğrulanan değer |
|---|---|
| Kaynak commit | `07b7e53dcad9301f56a0da097b36a81541584219` |
| Dosya | [combo_hunter_binance.pine](../middleware/pine/combo_hunter_binance.pine) |
| Satır | 1.091, son LF dahil |
| LF normalize UTF-8 SHA256 | `59ade54a6677a731deedeb4fd5e229b2c97099d27e2e90c502f3967a45cc672f` |
| Ayrı özel script | `Rapot P3-1 kabul 2026-09-21 59ade54a` |
| Ayrı grafik yerleşimi | `Rapot P3-1 Kabul 2026-09-21` |

Kaynak, sabit commitin GitHub dosya görünümünden okundu. Görünümün dışarıda
bıraktığı son satır sonu geri eklendi ve tam dosya hash'i yerel kaynakla
eşleştirildi. Editöre yapıştırıldıktan sonra tüm metin geri kopyalanarak
aynı hash tekrar doğrulandı. Kaydedilen özel script yeni oturumda yeniden
açıldı; geri kopyalanan kaynağın hash'i üçüncü kez eşleşti. Kod değiştirilmedi.

Yeni script ve kabul yerleşimi ayrı kaydedildi; önceki kullanıcı scripti veya
yerleşiminin üzerine yazılmadı. Topluluğa script yayımlanmadı; alarm oluşturma
veya mevcut alarmı güncelleme işlemi yapılmadı.

## Gerçek tarayıcı gözlemi

- `Add to chart` sonrasında `C+H Binance MW` grafiğe eklendi.
- Manuel preset ve varsayılan HTF `2W / 3W / M / 2M` ile altı sinyal satırlı
  skor tablosu oluştu. Durum satırında `TF OK`, `HMax:15` ve `CMax:4` görüldü.
- TradingView strateji raporu **1 Ekim 2017–21 Eylül 2026** aralığını gösterdi.
  Rapordaki “This report requires trade data” bildirimi beklenir: bu script
  `strategy.entry/order/exit/close` çağrısı içermez; grafik ve `alert()` üretir.
  Bildirim derleme hatası veya kâr/zarar ölçümü olarak yorumlanmadı.
- Yeniden bağlandıktan sonra fiyat güncellemeleri görüldü. Kabul sırasında
  görünür derleme/runtime hatası yoktu; derleyicide sıfır uyarı iddia edilmez.
- Kabul yerleşimi kaydedildi ve `All changes saved` durumu ayrıca görüldü.

İlk oturumda başka bir Chrome oturumu nedeniyle TradingView bağlantıyı kesti;
o denemenin yalnız grafiğe ekleme/kaydetme sonucu çalışma kabulü sayılmadı.
Kullanıcı diğer grafikleri kapattığını bildirdikten sonra yeni bağlantı ve
ayrı yerleşimde yukarıdaki kabul tamamlandı.

Küçük makine kaydı Git dışında
`runtime-data/p31-pine-runtime-acceptance-20260921.json` içindedir; raw SHA256
`c6dd1729d32600f58aeef89375c7beb613f642df940b999b098bfe16f35c8122`.
Bu dosya gözlem tutanağıdır; TradingView tarafından imzalanmış derleyici raporu
değildir. Tarayıcıdaki kaynak/ekran gözlemlerini ve sınırlarını kaydeder.

## Kabulün sınırı

Bu çalışma bütün Pine ayar kombinasyonlarını, altı tarihsel etiket türünün
her birini veya Python/TypeScript/Pine sayısal eşdeğerliğini doğrulamaz.
[Strateji karşılaştırması](STRATEGY_COMPARISON.md) formül/varsayılan farklarını
ve dar kaynak testlerini ayrı tutar. Gerçek kazanç sonucu çıkarılmaz.

Gerçek TradingView alarm teslimi, ALL/FIRST/saat filtresi matrisi, futures ve
standart olmayan grafik korumalarının runtime kabulü ile testnet/gerçek emir
testleri önceki kullanıcı kararıyla ertelidir. Tablodaki `Alert Acik` metni
yerel script koşuludur; sunucuda çalışan alarm veya webhook teslimi kanıtı
değildir. Borsa emri gönderilmedi.

Bu yalnız belge ve kabul kaydı yayınıdır. Altı canonical belge ile küçük
kabul JSON'u başarılı exact commit CI sonrasında
`/root/rapot-ops/20260921-p31-p32-closure/` altına aktarılır. Tam commit, CI,
hashler, taze kapasite/HTTPS ve değişmeyen üretim kimliği `release-record.json`
içinde tutulur. İmaj, servis, config, DB veya kaynak pointer değişmez.
