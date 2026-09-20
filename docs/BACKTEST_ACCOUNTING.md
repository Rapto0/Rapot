# Backtest nakit ve maliyet muhasebesi

P3-1 üçüncü adım, 13 Eylül 2026. Kapsam `backtesting_system.py` içindeki
`TradingCosts`, `Lot`, `Portfolio` ve bunların maliyet raporlarıdır. Bu sınıflar
middleware emir/pozisyon tablolarını kullanmaz; canlı hesap muhasebesi değildir.

## Maliyet modeli

Mevcut **referans tutar üzerinden toplamsal maliyet** varsayımı korunur.
Komisyon ve kayma, aynı referans işlem tutarının ayrı yüzdeleridir. Kayma
ayrıca gerçekleşme fiyatına uygulanmaz; kayma üzerinden tekrar komisyon
hesaplanmaz. Varsayılan oranlar bir aracı kurumun güncel ücret tarifesi değildir.

`B` işlem başına toplam bütçe, `P` referans fiyat, `c` komisyon oranı ve `s`
kayma oranı olmak üzere:

| İşlem | Hesap |
|---|---|
| Alış miktarı | `q = B / (P × (1 + c + s))` |
| Referans alış tutarı | `q × P` |
| Alış komisyonu / kayması | `q × P × c` / `q × P × s` |
| Nakit çıkışı ve lot maliyet tabanı | `B` |
| Satış net geliri | `q × satış_fiyatı × (1 − c − s)` |
| Gerçekleşmiş kâr/zarar | `satış net geliri − satılan lotun tüm alış maliyeti` |
| Kâr/zarar yüzdesi | `gerçekleşmiş kâr/zarar / tüm alış maliyeti × 100` |

Önceden alış giderleri nakitten çıkıyor, fakat `Lot.invested` yalnız çıplak
referans tutarı tutuyordu. Satış kârı bu nedenle alış giderleri kadar fazla
görünüyordu. Ayrıca `total_commission_paid` kaymayı da komisyon olarak sayıyordu.
Şimdi lot alış komisyonunu ve kaymasını saklar; `invested` tüm alış maliyetidir.
Nakit çıkışı bütçeye sabitlenir: kayan nokta çarpımının son bit farkı, tam bütçeli
alışı reddetmez veya bakiyeyi küçük negatif değere düşürmez. Tekrarlanan kesirli
nakit hareketleri Kahan toplamasıyla izlenir. Yalnız negatif temsil artığı,
başlangıç/nakit/bütçe ölçeğinin sekiz ULP değeri ile işlem bütçesinin `1e-12`
katından küçük olan sınır içinde sıfıra çekilir. Bu sınır çok büyük bütçelerde
nominal olarak büyüyebilir; sınırsız parasal kesinlik garantisi değildir.
Sıfırlama para birimine bağlı bir kuruş toleransı değildir; sınırın üzerindeki
nakit eksikliği reddedilir.

`total_commission_paid` yalnız komisyon, `total_slippage_cost` yalnız kayma,
`total_transaction_cost` ikisinin toplamıdır. Tutarlar içeride yuvarlanmaz;
işlem/Excel/konsol sunumunda yuvarlanır. Kayan nokta aritmetiği kullanıldığı için
korunum kontrolleri küçük sayısal toleransla yapılır; broker hassasiyet/lot
kuralları, döviz dönüşümü veya muhasebe amaçlı Decimal defteri eklenmedi.

## FIFO ve açık envanter

`sell(symbol, price, date, signal_type)` aynı dört argümanı alır ve en eski
lotun **tamamını** satar. Yeni bir kısmi lot/miktar arayüzü eklenmedi. İki lot
varken ilkini satmak, envanterin bir bölümünü kapatır; kalan lotun miktarı ve
tüm alış maliyeti aynen korunur.

Her alış/satıştan sonra temel kontrol:

`nakit + açık lotların maliyet tabanı = başlangıç nakdi + gerçekleşmiş kâr/zarar`

Tüm lotlar kapandığında gerçekleşmiş kâr/zarar, nakdin başlangıca göre farkıdır.
Bu denklem açık pozisyonların piyasa değerini hesaplamaz. Piyasa değerlemesi
ayrıca bir değerleme fiyatı ister; gelecekteki satış giderleri henüz gerçekleşmemiştir.
P3-1 beşinci adımın [ortak portföy değerlemesi](BACKTEST_PORTFOLIO.md), her açık
sembol için son bilinen kapanışı ve fiyatın gününü taşır. Eksik/geçersiz fiyatı
lot alış fiyatıyla değiştirmez; bu maliyet tabanını veya gerçekleşmiş PnL'yi
yeniden tanımlamaz.

Elle hesaplanan örnek: başlangıç 4.000, her alış bütçesi 1.030, komisyon %1,
kayma %2. Önce 100 fiyatından 10 birim, sonra 200 fiyatından 5 birim alınır.

| Adım | Nakit | Açık maliyet tabanı | Birikmiş gerçekleşmiş kâr/zarar |
|---|---:|---:|---:|
| İki alış sonrası | 1.940 | 2.060 | 0 |
| İlk lot 110'dan satılır | 3.007 | 1.030 | 37 |
| İkinci lot 180'den satılır | 3.880 | 0 | −120 |

Toplam komisyon 40, kayma 80'dir. Tek lotu değişmeyen 100 fiyatından alıp
satmak ise 1.030 çıkış /970 giriş /−60 gerçekleşmiş kâr/zarar üretir; eski
rapor −30 gösteriyordu. Bu örnekler sentetiktir, getiri tahmini değildir.

## Rapor sözleşmesi ve hatalı girdiler

- İşlem satırlarında `Fiyat` ve `Tutar` referans fiyat/tutar olarak kalır.
  `Kayma Maliyeti`, `Toplam İşlem Maliyeti`, `Nakit Akışı` ve `Maliyet Tabanı`
  maliyet ayrımını gösterir. Satıştaki `Alış Komisyonu` ve `Alış Kayma Maliyeti`
  önceki giderlerin açıklamasıdır; yeniden tahsil edilmez.
- Açık pozisyonda `Ortalama Fiyat` referans ortalaması; yeni `Ortalama Maliyet`
  tüm giderleri içeren birim maliyettir. `Toplam Yatırım` kalan toplam maliyettir.
- Excel genel özeti ve konsol ayrı komisyon/kayma/toplam gider gösterir.
  Worker çıktısındaki `commission_paid` yalnız komisyon anlamına gelir;
  `slippage_cost` ve `transaction_cost` ayrı alanlardır.
- Oranlar sonlu ve negatif olmayan, toplamı birden küçük değerler olmalıdır.
  Yapılandırma hatası `ValueError` verir; değiştirilebilir oranlar her işlemde
  yeniden kontrol edilir. Başlangıç nakdi/bütçe sonlu ve pozitif, piyasa BIST
  veya CRYPTO olmalıdır.
- Geçersiz fiyat/tarih, yetersiz nakit ve hesaplanamayan işlem tutarı kabul
  edilmez. Satış hesapları ve tarih farkı doğrulanmadan FIFO kuyruğundan lot
  çıkarılmaz. Satış zamanı alıştan önce olamaz; uyumsuz saat dilimleri reddedilir.

## Doğrulama ve kalan işler

`tests/test_backtest_accounting.py` gerçek sınıfları izole pytest ortamında
sentetik verilerle sınar. Rapor tüketicilerinin sayısal çıktıları da kontrol
edilir; normal CLI, piyasa sağlayıcıları ve broker çağrılmaz.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_backtest_accounting.py -q
```

Muhasebe sınıflarını import etmek artık matplotlib/tqdm gerektirmez. Bu
paketler kilitli ortamda bulunmadığından yalnız grafik veya ilerleme çubuğunu
kullanan fonksiyonlarda yüklenir; tam CLI/grafik çalıştırma kabulü yapılmış
sayılmaz. Bu adım bağımlılık eklemez veya mevcut warning politikasını yenilemez.

Tarih/kapanış sınırları ve önceki kapanış sinyalinin sonraki Open'da yürütülmesi
[dördüncü adımda](BACKTEST_EXECUTION.md), ortak nakit kronolojisi ve açık
pozisyon değerlemesi [beşinci adımda](BACKTEST_PORTFOLIO.md) tanımlanmıştır.
Benchmark hâlâ gerçekleşmiş PnL getirisi kullanır; WalkForward mevcut haliyle
gerçek strateji optimizasyonu değildir. Bu muhasebe ve yürütme adımları onları
geçerli karşılaştırma veya canlı kazanç kanıtı haline getirmez.

Kaynak yayını yalnız sürümlü CLI kaynağı/test/belge/kanıt kopyasıdır. Çalışan
API/bot/middleware bu modülü tüketmez; mevcut container içindeki dosya veya
`/opt/rapot/current` değiştirilmez. Kopya tek başına tam çalıştırılabilir release
değildir. CI ve yayın kanıtı [devam planındaki P3-1 kaydıyla](RAPOT_DEVAM_PLANI.md#p3-1--backtest-ve-strateji-eşdeğerliği)
bağlanır.
