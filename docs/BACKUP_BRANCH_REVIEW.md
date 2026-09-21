# Backup branch değerlendirmesi — P3-2

**Karar tarihi: 21 Eylül 2026.** `backup/pre-da7d452-rollback` içindeki beş
eski commit incelendi; bu değerlendirmede hiçbir kod veya belge aktarımı
seçilmedi. Güncel main tasarımı, API sözleşmeleri ve güvenlik sınırları
korunacak. Backup branch tarihsel referans olarak korunacak; merge,
cherry-pick veya branch silme yapılmayacak.

Bu karar, eski değişikliklerin tamamının main'de birebir bulunduğu anlamına
gelmez. Bir kısmının karşılığı mevcut, bir kısmının yerine yeni uygulama
geçmiş, kalanlar ise bu incelemede uygulanması seçilmeyen tasarım/temizlik
alternatifleridir. Yalnız backup'ta bulunmaları kayıp veya geri getirilmesi
gereken iş olduklarını göstermez.

## Sabit inceleme kaynakları

| Kaynak | Tam Git kimliği |
|---|---|
| İncelenen main ve yerel `origin/main` | `07b7e53dcad9301f56a0da097b36a81541584219` |
| `refs/heads/backup/pre-da7d452-rollback` | `d71c196062ea072d4a2e9d82d1f1e3887b28ab17` |
| Ortak ata | `0aecc74f534e5f05e5a9fd76280f68e4bd69f31b` |

Yerel ref envanterinde backup'ın ayrı remote-tracking ref'i yoktu. Bu
inceleme fetch yapmadı; uzak sunucudaki bütün ref'lerin envanteri olduğu
iddia edilmez. Ortak atadan sonraki ayrım **main tarafında 128, backup
tarafında 5 commit**. Backup'ın ortak ataya göre toplam farkı 22 dosyada
1.129 ekleme / 330 silme; son frontend commitinin kapsamı 18 dosyada
880 ekleme / 329 silmedir.

Salt okunur kanıt komutları:

```text
git merge-base main backup/pre-da7d452-rollback
git rev-list --left-right --count main...backup/pre-da7d452-rollback
git log --reverse --format="%H %s" main..backup/pre-da7d452-rollback
git diff --stat main...backup/pre-da7d452-rollback
git show <commit> -- <dosya>
git diff d71c196062ea072d4a2e9d82d1f1e3887b28ab17 07b7e53dcad9301f56a0da097b36a81541584219 -- <dosya>
```

Kaynak incelemesinin başlangıcında ve sonunda çalışma ağacı temizdi;
HEAD ve backup ref değişmedi. Bu belge ve devam planı güncellemesi, o
salt okunur incelemenin ardından yapılan belge çalışmasıdır.

## Beş commitin kararı

| Commit | Eski değişiklik | Güncel karşılık ve karar |
|---|---|---|
| `da7d452faba9046750b0e404cdc5bcbf6c6d6b60` | `chore: add Codex repo guide and local skill setup`; ilk AGENTS rehberi | Güncel [AGENTS.md](../AGENTS.md) mimariyi, canonical yolları, çalışma sırasını, test ortamını ve yetki sınırlarını daha ayrıntılı tanımlar. Eski rehberin deploy yardımcısına ilişkin git add ve commit yönlendirmesi güncel davranışa uymaz: [deploy.ps1](../scripts/deploy.ps1) test çalıştırmaz, dosyaları stage etmez ve commit oluşturmaz. Temiz çalışma ağacını ve verilen tam SHA'nın HEAD ile eşleşmesini kontrol eder; `-Push` verilirse bu commit'i seçilen uzak branch'e gönderir ve uzak SHA'yı doğrular. SSH bağlantısı kurmaz ve sunucuda deploy yapmaz; sunucu komutlarını yalnız yazdırır. Eski rehber aktarılmayacak. |
| `17710c1b977d806aca2d71c73b80a3aa0571cc2c` | `fix: use valid frontend smoke check route`; `/dashboard` yerine `/` | Geçerli `/` smoke kontrolü [deploy.ps1](../scripts/deploy.ps1) tarafından yazdırılan sunucu komutlarında ve [dağıtım rehberinde](DEPLOY.md) zaten var; komut `curl --fail` ile HTTP başarısızlığını reddeder. Gerçek ana sayfa [app/page.tsx](../frontend/src/app/page.tsx); eski `/dashboard` rotası yok. Ek aktarım gerekmiyor. |
| `d50574e4acd5c54fcabbd098ed5dd0c6d92fd64a` | `docs: tighten live trade guardrails in agents guide` | Güncel AGENTS ana Trade kayıtlarını ayrı middleware emirlerinden ayırır; üretim için DRY_RUN ve trading/live kapalı sınırlarını belgeler. [Portfolio panel](../frontend/src/components/dashboard/portfolio-panel.tsx) işlem gönderiminin bağlı olmadığını açıklar; AL/SAT ve pozisyon kapatma devre dışıdır. Eski paper/Gerçek seçici ve TODO tespitleri tarihsel kaldı. Eski belgenin aynen aktarımı seçilmedi; bütün eski önerilerin birebir uygulandığı iddia edilmez. |
| `d1a00239e9a508f9b2b15582b2a25fb1f0d315df` | `docs: add Codex skill usage guide`; 175 satır `docs/CODEX_SKILL_USAGE.md` | Bu commit skill uygulaması eklemez, yalnız kullanım rehberi ekler. Eski `$build-rapot-platform`, `$rapot-terminal-ui`, `$rapot-trade-safety`, `$doc`, `$spreadsheet` adları ve zorunlu öncelikler inceleme oturumunun güncel skill kataloğuyla örtüşmüyor. Main'de bulunmaması uygulama eksikliği değildir; tarihsel rehber geri getirilmeyecek. |
| `d71c196062ea072d4a2e9d82d1f1e3887b28ab17` | `feat: refine frontend terminal and fix lint`; aşağıdaki 18 frontend dosyası | KPI, işlem ve sinyal bölümlerini ana sayfaya taşıyan terminal tasarımı, grafik düzeni ve lint/lifecycle değişiklikleri. Güncel UI ve API ile farkları incelendi; aktarılması gereken somut bir eksiklik saptanmadı. Eski ana sayfanın güncel nullable sağlık sözleşmesiyle doğrudan uyumsuzluğu da var. Tasarım veya kod aktarımı seçilmedi. |

## Son committeki 18 frontend dosyası

Tablodaki yollar `frontend/src/` altındadır; değerlendirme yukarıda sabitlenen
`07b7e53` kaynağının durumunu anlatır. Sonraki 21 Eylül repo temizliğinde
kaldırılan `MiniSparkline`, `connection-status`, `use-chart-data` ve
`use-websocket` dosyalarının bağlantıları bu sabit Git commit'ine gider.
P2-3'te daha önce silinen bileşenler kod biçiminde gösterilir; kalan yerel
bağlantılar çalışan kaynaklara gider. Sonraki temizlik, bu tarihsel aktarım
yapmama kararını veya inceleme anındaki kaynak bulgularını değiştirmez.

| Dosya | Backup'taki değişiklik | Güncel main karşılığı / değerlendirme |
|---|---|---|
| [app/page.tsx](../frontend/src/app/page.tsx) | Bot/tarama KPI'ları, işlem günlüğü, sinyal akışı, dört ana piyasa satırı ve yoğun terminal yerleşimi | Main kategori bazlı kripto/BIST/ABD/emtia-döviz takibini, sembol aramasını ve ilgili ekranlara geçişi kullanıyor. Backup yerleşimi tercih edilmedi. Eski sağlık alanlarının doğrudan kullanımı aşağıda açıklanan uyumsuzluğu taşır. |
| [components/charts/MiniSparkline.tsx](https://github.com/Rapto0/Rapot/blob/07b7e53dcad9301f56a0da097b36a81541584219/frontend/src/components/charts/MiniSparkline.tsx) | `LineData<UTCTimestamp>` tipi, renk hesabı ve effect bağımlılığı düzeni | Main renk hesabını effect içinde yapar; typed setData değişikliği birebir mevcut değildir. Repo içindeki kaynak/test aramasında bu bileşeni kullanan bir çağrı bulunmadı. Sırf backup farkı nedeniyle tipi veya bileşeni değiştirme kararı alınmadı. |
| [components/charts/advanced-chart.tsx](../frontend/src/components/charts/advanced-chart.tsx) | Grafik komut şeridi, header/araç düzeni, yüzey stilleri ve küçük tip/lint düzenleri | Güncel grafik P2-1'in URL'den sembol/piyasa alma, veri yükleme ve yerel alarm akışlarını içerir. Backup'ın komut şeridi ve görünümü bir tasarım alternatifi olarak bırakıldı. Eski dosya güncel grafik davranışının yerine geçirilmez. |
| `components/dashboard/ai-analysis-widget.tsx` | Kullanılmayan import/helper temizliği ve JSX tırnakları | Bileşen P2-3'te kullanım incelemesinden sonra kaldırıldı. Güncel [AI ekranı](../frontend/src/app/ai/page.tsx) ve [AI terminali](../frontend/src/components/ai/ai-terminal.tsx) korunur; eski bileşen geri getirilmez. |
| [components/dashboard/bot-dashboard.tsx](../frontend/src/components/dashboard/bot-dashboard.tsx) | Kullanılmayan importların kaldırılması | Temizlik main'de mevcut; devamında doğrulanmış sağlık state'leri, normalizer ve metrik gösterimi eklendi. Güncel uygulama korunur. |
| `components/dashboard/global-ticker.tsx` | Fiyat parlamasını requestAnimationFrame ile başlatma, timer temizliği, kullanılmayan prop/import temizliği | P2-3'te kaldırılan eski bileşen. Ana sayfa canlı fiyatları güncel ticker/index kaynaklarından okuyor; eski widget geri getirilmez. |
| `components/dashboard/signal-terminal.tsx` | Filtre tipleri, sayfa sıfırlama ve güvenli sayfa indeksi | P2-3'te kaldırılan eski bileşen. Kullanıcı akışı güncel [sinyal sayfasında](../frontend/src/app/signals/page.tsx) bulunur; eski pagination uygulamasının birebir taşındığı iddia edilmez ve bileşen yeniden eklenmez. |
| [components/layout/header.tsx](../frontend/src/components/layout/header.tsx) | Bot Hazır/Durdu/Tarama Aktif durumları ve uptime | Güncel header API bağlantısının loading/unknown/error ayrımını, özel sinyal bildirimlerini ve oturum kontrollerini kullanır. Backup'ın ikili bot durumu yorumu güncel nullable sözleşmeye uygun değildir. |
| [components/layout/mobile-nav.tsx](../frontend/src/components/layout/mobile-nav.tsx) | Aktif rota etiketini listeden üretme ve bot durum noktası | Main yedi menü öğesiyle alarm girişini ve oturum kontrollerini içerir. Eski altı öğeli görünüm ve durum noktası seçilmedi. |
| [components/layout/sidebar-context.tsx](../frontend/src/components/layout/sidebar-context.tsx) | localStorage başlangıcını sıfır gecikmeli timer'a taşıma | Main doğrudan effect okumasını korur. Güncel ESLint politikası bu örüntüyü yasaklamıyor; timer eklemeyi gerektiren ayrı bir davranış hatası bu incelemede gösterilmedi. |
| [components/ui/connection-status.tsx](https://github.com/Rapto0/Rapot/blob/07b7e53dcad9301f56a0da097b36a81541584219/frontend/src/components/ui/connection-status.tsx) | Kullanılmayan `Icon` değişkeninin kaldırılması | Main bu değişkeni ve kullanılmayan ikon/import yapılarını zaten kaldırmış durumda. |
| [lib/api/client.ts](../frontend/src/lib/api/client.ts) | `safeParseTechnicalData` dönüşünü `Record<string, unknown>` yapma | Client artık compatibility export yüzeyidir. Tipli parse işlevi [normalizers.ts](../frontend/src/lib/api/normalizers.ts) içinde mevcut; eski monolitik client geri getirilmez. |
| [lib/hooks/use-analyses.ts](../frontend/src/lib/hooks/use-analyses.ts) | `technicalData` için `Record<string, unknown>` | Aynı tip main'de mevcut. |
| [lib/hooks/use-chart-data.ts](https://github.com/Rapto0/Rapot/blob/07b7e53dcad9301f56a0da097b36a81541584219/frontend/src/lib/hooks/use-chart-data.ts) | Rastgele demo mum üretimini helper/lazy state ve requestAnimationFrame ile düzenleme | Bu helper gerçek sağlayıcı verisi değildir. Repo içindeki kaynak/test aramasında tüketici bulunmadı; aktif grafik `fetchCandles` kullanır. Demo lifecycle değişikliği seçilmedi. |
| [lib/hooks/use-dashboard.ts](../frontend/src/lib/hooks/use-dashboard.ts) | Kullanılmayan `mockKPIStats` importunu kaldırma | Main'de mock importu yok; ops overview read-model ve API fallback dönüşümü kullanılıyor. |
| [lib/hooks/use-health.ts](../frontend/src/lib/hooks/use-health.ts) | Kullanılmayan API tip importlarını kaldırma | Temizlik mevcut; sağlık yorumu ayrıca [health-status.ts](../frontend/src/lib/health-status.ts) içine taşınmış, stale/loading/unknown durumları ve nullable sayaçlar tanımlanmış. |
| [lib/hooks/use-realtime.ts](../frontend/src/lib/hooks/use-realtime.ts) | Sayı animasyonunun yön state'ini requestAnimationFrame ile güncelleme | Realtime altyapısı ayrı [use-realtime-connection.ts](../frontend/src/lib/realtime/use-realtime-connection.ts) ve store/type modüllerine ayrılmış durumda. Animasyon yardımcı değişikliği ayrı bir ihtiyaç olarak seçilmedi. |
| [lib/hooks/use-websocket.ts](https://github.com/Rapto0/Rapot/blob/07b7e53dcad9301f56a0da097b36a81541584219/frontend/src/lib/hooks/use-websocket.ts) | Genel WebSocket hook'una reconnect timer/ref temizliği ekleme | Repo içindeki kaynak/test aramasında genel `useWebSocket` çağrısı bulunmadı; aynı dosyanın bağlantı sağlık helper'ı ayrı kullanılır. Aktif realtime transport başka modüldedir. Bu eski hook'u silme veya timer yamasını aktarma kararı alınmadı. |

Üç eski dashboard bileşeninin kaldırılma kaydı
`bacbfab814bb659f093a33733934b56f2bf5b19a` commitidir. Bu inceleme kaldırmayı
geri almıyor. Repo içi tüketici bulunmaması, dış tüketici bulunmadığının kanıtı
olarak kullanılmaz; kalan compatibility dosyaları da silinmez.

## Güncel sağlık sözleşmesiyle somut fark

Backup ana sayfası `botHealth.errorCount.toLocaleString(...)` ve
`botHealth.scanCount.toLocaleString(...)` çağrılarını koşulsuz yapar. Güncel
`deriveBotHealth`, veri yüklenirken, eskimişken veya hata durumunda bu
alanları `null` döndürebilir. Bu eski sayfanın güncel hook ile doğrudan
birleştirilmesi TypeScript/null sözleşmesini ihlal eder; kontrolsüz çalışma
yolunda render hatası riski vardır.

Backup ayrıca API hatası yokken `isRunning` falsy olduğunda “Durdu”,
`isScanning` falsy olduğunda “Beklemede” gösterir. Main'in `unknown`/`loading`
durumlarında bu alanlar `null` olabilir; eski ayrım bilinmeyen durumu durmuş
veya bekleyen bot gibi sunar. Güncel sözleşme ve
[sağlık regresyon testleri](../frontend/tests/health-status.test.mjs)
bu ayrımı açıkça korur. Bu nedenle tasarım daha sonra ayrıca seçilse bile
güncel veri durumlarına uyarlanması gerekir; eski hook'u geri almak çözüm
olarak seçilmemiştir.

## Doğrulama kapsamı ve kapanış

Bu çalışma Git ref/commit envanteri, commit patch'leri, güncel kaynak ve
repo içi kullanım aramasıyla yapılan tasarım değerlendirmesidir. İki bağımsız
incelemede ilk dört belge/deploy commit'i ile son frontend commit'i ayrı
okundu. Ağ, uygulama, sağlayıcı, tarayıcı veya üretim işlemi çalıştırılmadı.

**Aktarım seçilmediği için yeni bir UI/API entegrasyonu yoktur; seçilen
değişikliğin runtime UI uyum testi bu karar için uygulanamaz.** Yeni
frontend test/build veya görsel kabul sonucu üretilmiş gibi gösterilmez.
Somut null uyumsuzluğu kaynak karşılaştırmasıyla belirlenmiştir; backup
tasarımı çalıştırılarak alınmış bir ekran/hata kanıtı değildir.

P3-2'nin kabulü bu değerlendirme ve aktarım yapmama kararının
[devam planına](RAPOT_DEVAM_PLANI.md) işlenmesidir. Güncel Pine'ın TradingView
derleme/grafik kabulü ve ertelenen gerçek alarm/emir kontrolleri bu karardan
bağımsızdır. Bu belge bunları tamamlanmış saymaz.
