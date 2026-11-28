# Rapot Devam Planı

## Kaldığımız nokta

**28 Kasım 2026.** Aşama 1–3 ile Takipçi’nin Aşama 4.1 iyileştirmesi
üretimde. Aşama 5 ve 6’nın ekran geliştirmeleri yayımlandı. Takipçi, Grafik
ve dört mevcut BIST alarmının **tam açık seans kabulü** açık. Aşama 4.2’nin
kalıcı kapanış özeti kodda ve yerel testlerde hazır. Gerçek BIST pilotu kaynak
izni ve örnek veri bekliyor. Aşama 7’de veri kaynağı, VPS ve protokol kararları
ölçümden sonra verilecek.

**Bir sonraki iş** ilk uygun açık BIST seansında mevcut dört alarmın hazırlığını,
ekranların ilk kullanılabilir verisini ve sunucu kaynaklarını birlikte ölçmek.
Gün sonu ve gün içi kaynak araştırması bu ölçümle paralel ilerler.
[İş sırası](#sıradaki-işler-ve-ertelenen-kabul) · [Son yayın](#son-üretim-ve-yayın-kanıtları)

| Son gözlem | 28 Kasım sonucu |
|---|---|
| Ekran yanıtı | 13 sayfada üçer dış HTTPS örneğinin sayfa bazlı medyanları 0,282–0,365 sn. Ölçüm HTTP başlıklarına kadar. |
| Takipçi | Hafta sonu ilk gözlemde 400 hücre hazırlanıyordu. Sonraki gözlemde 394/400 hücre sayısaldı, 384’ü son kayıttı. İlk kullanılabilir tablo süresi ve canlı kapsama açık. |
| Grafik | THYAO’da ilk 160 mum çizildi. 1.000 mumluk geçmiş bu kısa gözlemde tamamlanmadı. 27 Kasım’da ayrı oturumda 1.000 mum görüldü. |
| Alarm Merkezi | Hafta sonu dört kuralın her birinde 631 sembol kontrol edildi, 0/631 hazırdı. İki kural ilk canlı fiyatı, iki kural güncel RSI verisini bekliyordu. |
| VPS | 1 vCPU, 957 MiB RAM. 11:46 TSİ’de 30 saniyelik kapalı seans örneğinde CPU %8,31–64,77, kullanılabilir RAM 245,7–249,1 MiB, swap kullanımı 415,7 MiB ve 65 sayfa giriş/923 sayfa çıkış görüldü. Yayın kabulünde 3,12 GiB boş disk vardı. |

## Sıradaki işler ve ertelenen kabul

| Sıra | Durum | İş | Kabul ve sonraki karar |
|---|---|---|---|
| 1 | **Sıradaki · ilk uygun açık BIST seansı** | Mevcut akışta ekran, alarm ve VPS gecikmesini ölç (Aşama 4.1, 5, 6 ve 7). | Aynı zaman çizelgesinde veri yaşı, ekran süreleri, dört kuralın kapsamı ve kaynak baskısı. Sonuç yetersiz veya gün olağandışıysa normal seansta tekrarla. |
| 2 | **Paralel · başlayabilir** | Gün sonu ve geçmiş/gecikmeli gün içi BIST seçeneklerinin yazılı kullanım kapsamını, örnek dosyasını ve fiyatını araştır (Aşama 4.2 ve 7). | Uygun ürün ve izin, periyot kapsamı, örnek veri ve maliyet belirli. Ücretli paket veya yeni sağlayıcı için kullanıcı kararı. |
| 3 | **Bekliyor · izinli örnek veri** | Küçük örnekten 25 sembole çıkan kalıcı son kapanış pilotunu doğrula (Aşama 4.2). | Gerçek RSI karşılaştırması, hazır tablo p95 ≤ 3 sn, kesinti ve yedekten dönüş kontrolü, dört alarm regresyonu. Sonuç uygunsa önce kullanıcı listesi değerlendirilecek. |
| 4 | **Bekliyor · ölçüm ve karşılaştırma sonucu** | BIST canlı veri kaynağı ve VPS kapasitesine karar ver (Aşama 7). | Mevcut akış ve uygun adayın kapsama, gecikme, güvenilirlik ve maliyet farkı. Kaynak değişikliği veya yükseltme için kullanıcı kararı. |

### 1. Açık seans ölçümü

- Açılış, gün ortası ve kapanış boyunca aynı sürüm ve mevcut kurallarla ölç.
  İlk kayıt için tarih, TSİ aralığı, API/frontend SHA, piyasa durumu ve ölçüm
  kapsamı yazılır. Gözlem eldeki akış, sağlık sayaçları ve normal ekran
  açılışlarıyla yürür. Mevcut sağlayıcı bütçesi ve alarm önceliği korunur.
- **Takipçi** için ilk HTTP yanıtı, ilk fiyat, ilk sayısal RSI, ilk kullanılabilir
  tablo ve sayısal/güncel kapsamı ayrı kaydet. Varsayılan 25 × 16 tablo, ikinci
  sayfa, filtreli liste, BIST/kripto ve iki sekmeyi dene. İlk ziyaret ile
  hazır kaydı olan tekrar ziyareti ayır. Hazır kayıtta hedef **p95 ≤ 2 sn**.
  `rapot.rsi.*` ölçümü kapsam açılışından başlar ve ilk fiyat ile ilk sayısal
  değeri işaretler. Gezinme başlangıcını ve o andaki doluluk oranını ayrıca kaydet.
- **Ana Sayfa ve Grafik** için ilk kaynak zamanlı fiyatı, ilk mum çizimini ve
  seçilen sembolde 1.000 mumluk geçmişin sonucunu ayrı ölç. BIST’te THYAO,
  kriptoda BTCUSDT ile başla. İlk açılış, tekrar ziyaret ve sembol değişimini
  ayrı kaydet. Zaman aşımını ve eldeki mumların korunup korunmadığını yaz.
- **Dört mevcut alarm ve Sistem Sağlığı** için kural başına toplam, kontrol
  edilen ve hazır sembolleri kaydet. Bekleme gerekçelerini ayır. Mümkün olan
  doğal olaylarda kaynak → sunucu, sunucu → değerlendirme/olay kaydı,
  olay → Telegram API kabulü ve olay → Alarm Merkezi gecikmesini ayrı ölç.
  Doğal tetik yoksa teslim süresini ölçülemedi olarak kaydet. Telegram
  API kabulü ile cihazda görülen teslim farklı ölçümlerdir.
- Aynı pencerede **CPU p95, kullanılabilir RAM, swap I/O, disk büyümesi, kuyruk
  ve taşma, sağlayıcı ret ve yeniden bağlantı** ölçülür. Sonuçta örnek sayısı,
  süre aralığı, medyan/p95 ve zaman aşımı/eksik örnekler birlikte yazılır.
  Tek gözlemle tam seans kapasitesi kararı verilmez.
- Bir sonraki çalışma sonunda şu kayıt doldurulur. **Tarih ve seans · sürümler ·
  senaryo ve örnek sayısı · medyan/p95 ve kapsam · bekleme nedeni · kanıt
  bağlantısı · karar ve sonraki adım.** Bu kayıt tamamlandığında yukarıdaki
  sıra tablosu güncellenir. [Takipçi ölçüm kodu](../frontend/src/components/scanner/rsi-tracker.tsx) ·
  [BIST işlem saatleri](https://www.borsaistanbul.com/en/trading-hours) ·
  [Sunucu alarm sözleşmesi](SERVER_ALARMS.md)

### 2. BIST kaynak araştırması

**Önce iki kapsamı karşılaştır.** Gün sonu verisi günlük ve uygun uzun
periyotların son değerini açılışta gösterebilir. 15 ve 30 dakikalık RSI için
geçmiş veya gecikmeli gün içi mum gerekir. Canlı 631 sembol alarmı, ancak
ölçüm gerekçe sağlarsa, eşanlı akış ve uyumlu geçmişle ayrıca karşılaştırılır.
Mevcut Borsapy/TradingView akışı ölçümde referans olarak kullanılır.
Oturum doğrulaması, veri saklama veya ekran dışı kullanım iznini doğrulamaz.
[BIST veri yayını](https://www.borsaistanbul.com/veriler/veri-yayini) ·
[DataStore](https://www.borsaistanbul.com/veriler/gecmise-donuk-veri-satisi) ·
[TradingView koşulları](https://www.tradingview.com/policies/)

DataStore ve BIST’in yetkili dağıtıcıları üzerinden, **özel Rapot sunucusunda**
dosya/API erişimi, geçmiş derinliği, kapsanan pay ve periyotlar, kaynak
zamanları, seans ve kurumsal işlem düzeltmeleri, saklama/yedekleme ve türetilmiş
RSI gösterme hakkı doğrulanır. Otomatik alarm değerlendirme hakkı, canlı veri
kapsamında ayrı sorulur. Örnek dosya ile tek seferlik ve aylık ücret kalemleri
ayrıca istenir. Matriks ve ForInvest ilk inceleme adaylarıdır. İzin ve örnek
paket doğrulanınca pilot kapsamı belli olur.
[Yetkili dağıtıcılar](https://www.borsaistanbul.com/veriler/veri-yayini/veri-dagitici-kuruluslar) ·
[BIST lisanslama](https://www.borsaistanbul.com/sss/veri-dagitim-ve-endeks-lisanslama) ·
[Matriks veri servisleri](https://www.matriksdata.com/website/urunlerimiz/kurumsal-hizmet-ve-servisler/veri-ve-icerik-saglayici-servisler)

### 3. Kalıcı son kapanış pilotu

- **Mevcut durum.** Aşama 4.2 kaynakta `14c4f00` ile hazır ve üretim API’sinde
  yayımlanmadı. Sentetik 400 seri yeniden başlatma ve bağımsız geri yükleme
  testini geçti, özet 128 KiB altında kaldı. Kullanıcı bu kapsamda veri
  paketi olmadığını doğruladı.
- **Kurulum.** İzinli örnekle önce likit, seyrek işlem gören ve geçmişi kısa
  semboller denenecek. Ardından en fazla 25 sembol × 16 periyot. Arka plan
  işçisi 30 saniyede bir geçerli dosyayı kontrol eder. Kapanış ve Wilder
  RSI(14) özetini ayrı SQLite dosyasında tutar, API başlangıcında ilk
  okumadan önce yükler. Sağlayıcı kapanış saati ve sunucu alım saati ayrı
  saklanır. Son kapanış ekran içindir. Canlı filtre ve alarm doğrulanmış
  taze veriyi kullanır.
- **Kabul.** Aynı kaynak ve düzeltme yöntemiyle gerçek RSI değerlerini,
  eksik mumları ve kurumsal işlem revizyonunu doğrula. Tarayıcı 150 sn’den
  uzun kapalı kaldığında, yeni oturumda ve izole API yeniden başlatmasında
  hazır kapsam ilk kullanılabilir tablo **p95 ≤ 3 sn**. Her senaryoda sayısal
  kapsam ve veri olmayan hücrelerin gerekçesi kayıtlı. Kaynak kesintisi ve
  bağımsız SQLite geri yüklemesi geçer. Mevcut dört alarmın tanımı, canlı
  veri koşulu ve bildirim tercihi korunur.
- **Uygulama bağlantıları.** `RSI_TRACKER_HISTORY_SOURCE` ve
  `RSI_TRACKER_HISTORY_SYMBOLS` onaylı kaynağı ve pilot üyelerini seçer.
  `rsi-tracker-input.jsonl` atomik teslim edilir. Girdi sınırı 400 seri,
  seri başına 240 mum ve toplam 6 MiB. `rsi-tracker-closed.sqlite3` ayrı
  yedeklenir. Geri dönüşte kaynak ayarı boş bırakılır.
  [Girdi ve saklama sözleşmesi](../infrastructure/persistence/rsi_tracker_history.py) ·
  [API yaşam döngüsü](../api/runtime/tracker_history.py) ·
  [Pilot testleri](../tests/test_rsi_tracker_history.py)

### 4. Canlı kaynak ve VPS kararı

Taze verinin Rapot’a ulaşma süresi veya sağlayıcı kapsamı yetersizse izinli
eşanlı kaynak küçük bir örnekte paralel karşılaştırılır. Rapot içindeki
gecikme CPU baskısıyla birlikte artıyorsa 2 vCPU’lu, swap baskısıyla birlikte
artıyorsa en az 2 GiB RAM’li planlar maliyetle karşılaştırılır. Ayrı veri
işçisi de ölçüm gerekçe gösterirse değerlendirilir. Ekran gecikmesi
baskınsa önce mevcut yenileme ve çizim yolu iyileştirilir. Alarm Merkezi’nin
kimlikten itibaren sorgusuna alternatif SSE, ancak ölçüm ekran gecikmesini
gösterirse değerlendirilir. 631 × 16 seri talebi mevcut bağlantı kapasitesini
aşar. Listeyi büyütme kararı ölçülen kapsama ve sağlayıcı sınırlarına bağlıdır.
[DigitalOcean boyut değiştirme rehberi](https://docs.digitalocean.com/products/droplets/how-to/resize/) ·
[21 Ekim kapasite kanıtı](LIVE_MARKET_CAPACITY_2026-10-21.md)

### İkincil ve ertelenen işler

- Resmî 2027 BIST takvimi teyit edilince tatil ve yarım gün kuralları güncellenir.
  Araştırma/Takvim’de kullanılan sağlayıcıların gerçek yanıt süreleri ve hata
  durumları ayrıca denenir. Gerçek ücretli AI çağrısı ilgili kullanım ve bütçe
  kapsamında ele alınır. [BIST tatil takvimi](https://borsaistanbul.com/resmi-tatil-gunleri) ·
  [Borsapy entegrasyonu](BORSAPY_INTEGRATION.md)
- Ekim’deki 3.000 canlı kural denemesi kaynak ön kontrolünde başlayamadı.
  İlk öncelik mevcut dört kuralın tam seans kabulüdür. Mum hacmi ve bazı
  takvim olaylarının kaynak saat dilimi sınırlamaları ilgili kayıtlarda durur.
  Doğrulanmamış hacim eksik gösterilir.
  [Tam seans ve yük kaydı](FULL_SESSION_ACCEPTANCE_2026-10-08.md) ·
  [Dar canlı piyasa kabulü](LIVE_MARKET_ACCEPTANCE_2026-10-07.md)
- Gerçek TradingView webhook teslimi, Pine çalışma zamanı matrisi ve
  Binance testnet/gerçek emir kabulü ertelidir. Dış kabul, kullanıcı yeniden
  seçtiğinde ayrı test kapsamı ve DB ile ele alınır. Middleware DRY_RUN ve
  reconciliation REPORT_ONLY kullanır. DRY_RUN’da geçerli webhook simülasyon
  kaydı yazabilir. [Pine sözleşmesi](PINE_CONTRACT.md) · [Middleware](MIDDLEWARE.md)

## Kapsam ve yetki kaydı

- Çalışma sırası **incele → düzelt → doğrula → planı güncelle**. Mevcut
  geliştirme, doğrulama, commit/push ve uygun zamanda doğrulanmış yayın
  yetkisi geçerlidir. Otomatik takip önceki kullanıcı talimatıyla kapalıdır.
  Bir sonraki seans ölçümü elle yürütülür.
- Ücretli veri paketi, plan yükseltmesi, yeni dış kabul veya bildirim/emir
  testi ayrı kullanıcı kararıdır. Önceki bakım ve temizlik onayları kayıttaki
  adaylara özeldir. Çalışan servisler, mevcut kurallar/listeler, veritabanları,
  özel dosyalar, yedek ve geri dönüş imajları korunur.
- Üretim yayını öncesi exact SHA CI, taze kapasite ve bağımsız yedek kontrolü.
  Mevcut **528 MiB** sabit disk rezervi ayrıca hesaplanır. Anahtar, token,
  `.env` ve gerçek DB’ler Git dışında kalır. Kaynak testi, üretim yayını ve
  canlı kabul ayrı kaydedilir. [Çalışma rehberi](../AGENTS.md) · [Dağıtım](DEPLOY.md)

## Son üretim ve yayın kanıtları

**28 Kasım birleşik yayın.** Frontend `d99c6774a1b4b533ed36aa46a7fd1dfd52386efb`
11:58:31 TSİ’de yayımlandı. 11:58:37 TSİ’de bağımsız kabulde 13 sayfa,
41 statik dosya, sekiz anonim 401, iki 307 ve özel 404 geçti. API
`fbdbaa4a7261f83aa4394547ca6f88bc1d6d95fb`, Compose/current `21e39512`,
middleware ve PostgreSQL aynı kaldı. Dört servis sağlıklı, dört etkin
kural, 418 olay ve 15 tablo korundu. 1.134.592 bayt yedek bağımsız olarak
geri yüklendi. 356 frontend ve 70 hedefli Python testi, beş CI işi,
üretim derlemesi, standalone proxy ve 470 paketlik sıfır bulgulu npm
denetimi geçti. Yayın ve kabul kanıtı
`c76169275252c583bebf37f5c89cc23e79fd2d6704a2e3e7a87ffda59739972c`.
[Kaynak CI](https://github.com/Rapto0/Rapot/actions/runs/46127384353) ·
[Temiz imaj](https://github.com/Rapto0/Rapot/actions/runs/46127402664)

| Yayın aralığı | Korunan kısa kayıt |
|---|---|
| 27–28 Kasım · Aşama 5 ve 6 | Ortak BIST fiyatı, sekme başına paylaşılan Binance Spot bağlantısı ve Grafik’te artımlı çizim yayımlandı. Alarm Merkezi 5 sn arayla artımlı okuyor. Bir boş kontrolde 50 bayt, ilk okumada 48.211 bayt ölçüldü. Sağlık ve alarmlarda kaynak, seans, veri yaşı ve hazırlık ayrı görünüyor. Diğer ekranların boş/hata/oturum akışları birleşik yayında doğrulandı. |
| 26 Kasım · Aşama 4.1 | Mevcut süreçte son geçerli fiyat/RSI korunuyor. 150 sn’lik kapsam talebi dışında geçerli kayıt okunabiliyor. İki seans dışı açılışta 150 değer 0,84 ve 0,77 sn’de görüldü. Bunlar tekil örnekler. [CI](https://github.com/Rapto0/Rapot/actions/runs/45887838562) |
| 25 Kasım · Aşama 1–3 | Ekran erişimi, hata durumları, yönetici çerez oturumu, CSRF, kısa ömürlü WS bileti ve grafik modülleri yayımlandı. Kullanıcının tarihli onayıyla 48 kullanılmayan Ekim imajı kaldırıldı. |
| 14–19 Kasım · Takipçi | 16 periyot ve 25 görünür satır, sıralama/filtre ve 120 sn ekran yenilemesi üretime girdi. Dar canlı pilotta THYAO/BTCUSDT 16/16 periyotta doğrulandı. Tüm evren, sayısal TradingView eşitliği ve tam seans açık. |
| 21–23 Ekim · Hesap ve kapasite | Hesap koruması, kontrollü erişim ve ortak veri bütçesi yayımlandı. 631 hesap hazırlığı ve dar canlı önizleme belgeli. Tam seans kapasitesi açık. [Kapasite kaydı](LIVE_MARKET_CAPACITY_2026-10-21.md) · [Hesap koruması](ACCOUNT_PROTECTION_2026-10-23.md) |
| 12–16 Ekim · Geçiş ve liste ayrımı | Eski otomatik bot ve COMBO/HUNTER tarama arşivi emekli edildi. Beş özel gösterge ve liste alarmı yayımlandı. 631 paylık liste ile 174 kodluk alarmsız liste ayrı saklandı. [Geçiş](INDICATOR_ALARM_TRANSITION_2026-10-12.md) · [Liste ve canlı kabul](LIVE_INDICATOR_ACCEPTANCE_2026-10-16.md) |

**DigitalOcean e-postaları.** Bülten ve NGINX, OpenJDK, PHP uyarılarının
28 Kasım kontrolü kapandı. Rapot ana sisteminde ve dört çalışan container’da
PHP/Java komutu bulunmadı. Çalışan NGINX’in Ubuntu paketi
`1.18.0-6ubuntu14.24`, ilgili iki açığı düzelten `.23` paketinden sonra gelir.
[NGINX güvenlik duyurusu](https://ubuntu.com/security/notices/USN-9159-1)

**Ayrıntılı geçmiş.** 28 Kasım’a kadarki yayınlar, ara ve başarısız ölçümler,
imaj kimlikleri, hash’ler ve tarihli onaylar önceki planın sabit Git
sürümünde. Eski gözlem ve onaylar ait oldukları tarih için geçerlidir.
[Tam planın 28 Kasım kopyası](https://github.com/Rapto0/Rapot/blob/6af842532c778676bc2061be2cd165af377fee90/docs/RAPOT_DEVAM_PLANI.md) ·
[6–21 Eylül arşivi](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md) ·
[Belge dizini](README.md)

### 14 Kasım — Yayın ve kabul

İlk Takipçi ön yüzü `0e7489ce5dd073648bd093fb65859745020745af` 21:32:59
TSİ’de yayımlandı. Ayrı kabulde giriş ve sayfa doğrulandı. RSI veri
servisi sonraki yayınla eklendi.
[CI](https://github.com/Rapto0/Rapot/actions/runs/43625586813) ·
[İmaj](https://github.com/Rapto0/Rapot/actions/runs/43625856142)

### P3-1 — Backtest ve strateji eşdeğerliği

Altı geliştirme adımı, sabit verili CLI ve 21 Eylül BTCUSDT Pine grafik
kabulü tamamlandı. Yürütme, FIFO, portföy, benchmark ve formül sınırları
ilgili sözleşmelerde tutulur. [Strateji karşılaştırması](STRATEGY_COMPARISON.md) ·
[Muhasebe](BACKTEST_ACCOUNTING.md) · [CLI](BACKTEST_CLI.md) ·
[Pine grafik kabulü](PINE_RUNTIME_ACCEPTANCE.md)

### P1-G2 — Frontend bağımlılık güvenliği takibi

Frontend audit’i tam kilit kapsamını denetler. En son yayın kaydı
470 paket ve 0 bulgu. 18 Kasım’daki tek advisory’ye bağlı süreli istisna
tarihsel güvenlik kaydında durur. Python Bandit/pip-audit CI’da
`report-only` olarak raporlanır. [Güvenlik ve yayın ayrıntıları](FRONTEND_DEPENDENCY_SECURITY.md)

## Geliştirme ortamı ve komutlar

Depodaki `.python-version` ve `.nvmrc` ile Python 3.12 / Node 20.20.2,
kilitli Python paketleri ve npm 10.9.9 kullanılır. Tam pytest, Node ve
frontend `npm ci` sonrasında çalıştırılır. Gerekirse `NODE_BINARY` ile
Node yürütücüsünün tam yolu seçilir.

```powershell
uv venv --python 3.12 .venv # Yalnız .venv yoksa
uv pip sync --python .venv/Scripts/python.exe requirements-dev.lock
uv pip check --python .venv/Scripts/python.exe
.venv/Scripts/python.exe -X utf8 -B -m pytest
.venv/Scripts/python.exe -m scripts.ci_quality lint
```

Frontend dizininde `npm ci`, `npm test`, `npm run lint -- --no-cache`,
`npm run typecheck -- --incremental false`, `npm run build`,
`npm run test:standalone` ve `npm run audit:dependencies`.
Windows’ta mevcut Node’u değiştirmeden
`npm.cmd exec --yes --package=node@20.20.2 --package=npm@10.9.9 -- npm test`.
[Frontend rehberi](FRONTEND.md) · [CI ve dağıtım](DEPLOY.md)
