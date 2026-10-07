# 7 Ekim 2026 canlı piyasa kabulü

Kullanıcı, daha önce piyasa açılışına bıraktığı kontrolleri **“Piyasa açıkken
kalan işleri her şeyi doğrula”** talimatıyla yeniden seçti. Kontrol 17:44 TSİ'de
başladı. Kapsam, mevcut veri/alarmlar ve mevcut Telegram hedefine açıkça TEST
etiketli geçici bildirimlerdir. Emir, testnet işlemi, yeni abonelik veya hesap
kimliklerini değiştirme işlemi yapılmaz.

## Canlı gözlemler

- İlk sunucu kontrolünde beş servis healthy idi; yaklaşık üç gündür çalışan
  servisler yeniden başlatılmamıştı. Boş alan 7.409.246.208 bayttı.
- 17:46 TSİ alarm durumu: 805 KAP evren girdisi/abonelik, 521 taze ve 284
  bayat sembol. 45 güncel ve 336 önbellek geçmişi; 722 bekleyen iş ve 469
  sağlayıcı hatası. 805 abonelik, işlem gören 805 hisse veya tam kapsama kanıtı
  değildir. İşlem görmeyen sembolde son işlem zamanı da doğal olarak eskir.
- 17:50:35–17:51:38 TSİ, THYAO/GARAN/ASELS/EREGL/TUPRS için 30'ar örnek
  alındı. Hepsinde gerçek sağlayıcı zamanları ve fiyatlar ilerledi. HTTP
  yanıtları 200 olsa da her sembolde iki `error`, son üç sembolde ayrıca bir
  `waiting` yanıtı vardı. Başarılı örneklerin son işlem yaşı THYAO'da
  0,884–3,879; GARAN'da 0,878–10,724; ASELS'te 0,724–5,130; EREGL'de
  0,396–6,890; TUPRS'ta 0,803–9,130 saniyeydi. Bunlar ağ gecikmesi ölçümü
  değil, yanıt okunurken sağlayıcının son işlem zamanının yaşıdır.
- Kullanıcının giriş yaptığı TradingView ekranında standart 1 dakikalık
  THYAO grafiği ve `BISTMIXED:THYAO` kimliği görüldü. 17:55 mumunun
  O/H/L/C değerleri 286,50/286,75/286,25/286,50 idi; Rapot akışında
  17:55:21'de aynı açık mum değerleri görüldü. Aynı anda örneklenmemiş
  açık mum eşleşmesi, tüm kapalı mumların veya sıfır gecikmenin kabulü değildir.
- Rapot'un 300 THYAO akış mumunun tümünde hacim sıfır, quote hacminde
  `1e100` yer tutucusu görüldü. Bu gerçek sıfır hacim olarak kabul edilmez.
  Fiyat ve hacim erişiminin ayrı doğrulanması gerekir.

Özel ham kanıtlar Git dışındaki `runtime-data/20261007-live-acceptance/`
ve `runtime-data/live-market-20261007/` dizinlerindedir. `quote-sample.json`
SHA256: `da5a8754ebde3d7ee142dec32d72763be8438e692c0a1817eb7837c462391f95`.
Gizli anahtar/çerez/JWT/sağlayıcı hata gövdesi kanıtlara alınmaz.

## Gerçek sunucu alarmı ve Telegram

`TEST 100e0ec2b67a` çalışması, GARAN üzerinde üç tek sembollü geçici kural
oluşturdu. `cooldown=86400` ile her kuralın ilk başlangıç gözleminden sonra
yeni canlı veride yalnız bir bildirim üretmesi sınandı. Koşullar test amaçlıdır;
doğal fiyat eşiği kesişmesi veya kazanç stratejisi kabulü değildir.

| Kategori | Gerçek motor sonucu | Teslim kanıtı |
|---|---|---|
| Fiyat | Olay 1; fiyat 129,7; gözlem 17:51:21,506, olay 17:51:22 TSİ | `sent`, ilk deneme; kullanıcı Telegram'da gördüğünü doğruladı |
| İzleme listesi | Olay 2; aynı GARAN fiyat gözlemi | `sent`, ilk deneme; kullanıcı Telegram'da gördüğünü doğruladı |
| Teknik/VE | Olay 3; 1m close 129,6 ve RSI(14) 49,18840195; gözlem 17:51:35,501, olay 17:51:36,116 TSİ | `sent`, ilk deneme; Telegram sunucu kabulü |

Normal motor → kalıcı olay → teslim kuyruğu → Telegram yolu kullanıldı;
Telegram'a doğrudan test mesajı gönderilip alarm çalıştı sayılmadı. Çalışma
59,455 saniye/41 API isteği sürdü. Gönderimden sonra yalnız bu çalışmanın
üç kuralı duraklatıldı ve kaldırıldı, geçici liste kaldırıldı. Olay geçmişi
korundu. Diğer kullanıcı kurallarına veya emir sistemine dokunulmadı.

## Bulunan sorunlar ve düzeltme kapsamı

1. Arka plan mum geçmişi, ağ isteği boyunca ortak hesap kilidini tutuyordu.
   805 sembollü yük altında grafik, takvim ve araştırma istekleri 429 alıyordu.
   Alarm geçmişi, kimliği kısa kilit altında sabitleyen, isteğe özel sağlayıcı
   ve en fazla iki iş ile ayrılır. Sonuç kabul edilmeden hesap revizyonu,
   token ve epoch tekrar denetlenir. Anonim veriye geçilmez.
2. Sıcak bellekten çıkarılan geçmiş, diskte mevcutken boş görünüyordu.
   Geçmiş okuması sınırlı disk önbelleğine ulaşır; bu okuma eski veriyi canlı
   alarm verisi yapmaz. `stale`/`cached_unverified` ayrımı korunur.
3. Tarihçe yenileme hatası, akıştan geçerli mumlar gelmesine rağmen grafiği
   tam ekran kapatıyordu. Mevcut seçimin mumları varsa hata küçük bir
   yenileme uyarısı olarak kalır; mum yoksa engelleyici hata korunur.
4. Borsapy eksik hacmi sıfırla doldurabiliyor. BIST hacim koşulları için
   doğal sağlayıcı alanının doğrulanması gerekir; doğrulanmayan hacim
   `unknown` olur. Fiyat ve fiyat tabanlı göstergeler bundan bağımsızdır.
5. Teknik tarama, önce Türkiye genelindeki 200 sonucu alıp sonra istenen
   sembolleri seçiyordu; bu sıra eşleşmeleri kaçırabiliyordu. Dar adaptör,
   sembol filtresini sorguya baştan ekler; sonuç sayısı ve sembol kimliklerini
   doğrular. Native koşul ayrıştırıcısı korunur. Seçilen periyodun gösterge
   değerleri alınır; günlük değerler başka periyot etiketiyle sunulmaz.
   Sağlayıcı/şema hatası başarılı boş sonuç olarak dönmez.
6. Şirket işlemlerinin herkese açık İş Yatırım sorgusu da hesap kilidini
   tutuyordu. Yalnız `company.actions`, mevcut kilitsiz public callback yoluna
   alındı; HTTP yönetici kontrolü ve iki araştırma sınırı korundu.

İlk kaynak `6976127` için CI, frontend audit'te iki yeni yüksek bulgu nedeniyle
durdu. Sharp 0.35.5 ve source-map-js 1.2.2 yamaları lock'a alındı; Next/React
değişmedi. Temiz kurulumda 469 paket/0 bulgu ve 297 frontend testi,
lint/typecheck/build/standalone geçti. Native Sharp değiştiği için yeni frontend
tam runtime imajıyla yayımlanmalıdır; eski native tabanı koruyan kaynak imajı
bu yamayı taşımaz. [Güvenlik kanıtı](FRONTEND_DEPENDENCY_SECURITY.md).

Yayın öncesi güncel 15 tabloluk SQLite yedeği sunucu dışında bağımsız geri
yüklenerek şema, satır sayıları ve içerik parmak izleri karşılaştırıldı.
1.152.856.064 baytlık doğrulanan DB, 152.453.201 baytlık gzip arşivden üretildi;
arşiv SHA256 `bde3ca0d71991596f38de7b174385ca8a53e9e3478fb76424aa07659b3f88609`.
Üretime geri yükleme yapılmadı; özel yedek Git dışındadır.

## Araştırma kontrollerinin ilk sonuçları ve sınırları

İlk dar araştırma kontrolünde günlük teknik tarama 200/boş sonuç verdi;
bu gösterge doğruluğu kanıtı değildir. Bugünün TR ekonomik takvimi ve
EREGL/TUPRS şirket işlemleri 429 verdi. Kanıt SHA256:
`b5297480b7c469ef05c56e076d8f9e6987d4c2ca38839a2f20add213e6436254`.

EREGL'in 27 Kasım 2024 tarihli %100 bedelsiz işlemi için resmî referans
[KAP 1360496](https://www.kap.org.tr/tr/Bildirim/1360496)'dır. Bu kaynak
oran/tarihi destekler; Rapot geçmiş fiyat düzeltmesinin karşılaştırmalı
kabulü değildir. `adjustment=splits`, temettü dahil toplam getiri anlamına gelmez.

18:22 TSİ'de ayrı süreçte, henüz yayımlanmamış aday adaptörle salt okunur
sağlayıcı kontrolleri yapıldı. EREGL şirket işlemleri 27.11.2024 için %100
bedelsiz döndürdü; 500 günlük bölünmeye göre düzeltilmiş seride 26 Kasım
kapanışı 25,05 ve 27 Kasım kapanışı 24,70 idi. Beklenen ikiye bölünme kaynaklı
grafik kopukluğu bu örnekte yoktur; tüm şirket işlemlerinin doğruluğu veya
temettü toplam getirisi kabul edilmez. TUPRS'ta 2023 %600 bedelsiz kaydı geldi.
Türkiye takviminde 7 Ekim 17:00 kaynak saatiyle Hazine Nakit Bakiyesi olayı
geldi; sağlayıcı saat dilimi bilinmediğinden Türkiye saati olarak kabul edilmedi.
Dar teknik alan sorgusunda GARAN 129,9 < SMA50 130,184 ve THYAO 286,25 <
SMA50 298,875 bulundu; bu iki sembolde `close > SMA50` boş sonucu tutarlıydı.
Bu ayrı süreç sonuçları, henüz çalışan eski API'nin 429 sorununun giderildiğini
kanıtlamaz; yayın sonrası HTTP kabulü ayrıca gereklidir.

Tüm sembollerde kesintisiz/saniyelik kapsama, uzun süreli yük, tüm zaman
dilimleri, hacim erişimi, tarihsel şirket işlemi düzeltmeleri ve takvim saat
dilimi tek bir seans sonu örnekleminden doğrulanmış sayılmaz.
`realtime_verified=false` ve `one_second_coverage_guaranteed=false` korunur.
TradingView webhook/gerçek veya testnet emir kabulü bu bildirim testinden
ayrı kapsamdır ve işlem yetkisi gerektirir.

## Yayın ve kapanış sonrası bağımsız kabul

Kaynak **`c74c1ad12f5464502bd7da7b72d7d6dfde69244a`**; 1.693 Python testi
(bir atlama/üç mevcut bağımlılık uyarısı), 280 Python dosyasında Ruff, 297 frontend
testi, lint/typecheck/build/standalone ve 469 paket/0 bulgu audit geçti.
[CI 37646334599](https://github.com/Rapto0/Rapot/actions/runs/37646334599)
beş iş; [yayın 37646403634](https://github.com/Rapto0/Rapot/actions/runs/37646403634)
iki başarılı iş/iki beklenen atlama içerir. API 120 runtime paketini koruyan
kaynak imajı; frontend native güvenlik yamaları nedeniyle tam imajdır.

| Bileşen | Yeni değişmez imaj |
|---|---|
| API | `ghcr.io/rapto0/rapot/backend@sha256:94ff294ba51be2bf7648b34bf382040eb8fffda4a680f7f9e95c20c9c66a6dcb` |
| Frontend | `ghcr.io/rapto0/rapot/frontend@sha256:e7b8e6b9cdb49b138523d57f16a14eabaef3013287be0d2ebed6e444a59c7c54` |

Ek imaj bütçesi 119.115.601 bayt; 528 MiB rezerv, 64 MiB WAL/günlük ve
2 MiB kanıt payıyla gerekli alan 741.969.745 bayt; mevcut alan 7.396.454.400
bayttı. Temizlik, migration veya plan yükseltmesi yapılmadı.

**15:58:41 UTC yayın / 15:59:24 UTC bağımsız kabul geçti.** Beş servis healthy/
restart0; API/frontend değişti, diğer üç container korundu. Beş HTTPS sayfası,
20 keşfedilen statik dosyanın 13'lük örneklemi ve 11 anonim 401/no-store kontrolü
geçti. 15 tablo şeması değişmedi. Olaylar 1/2/3 ve kullanıcı listesi içerik
parmak izleriyle taze yedekle eşleşti. Test kuralları API'de görünmez; olaylarla
ilişkili yumuşak silinmiş satırlar korunur. Yeni Telegram mesajı/emir gönderilmedi.

Motor çalışıyor; kapanış sonrası 805 sembolün eskimiş olması taze veri gibi
gösterilmedi (`history_ready=0`). Native ELF64 Linux/x64 modülü ile Node 20.20.2,
Next 16.3.8, Sharp 0.35.5/rsvg 2.63.2/vips 8.18.7 doğrulandı. Boş alan
**7.295.827.968 bayt**; kimlik/ayarlar ve DRY_RUN/live kapalı sözleşmesi korundu.
Açık yönetici grafiğinde 1.000 mum, Türkiye saati etiketi ve hata örtüsünün
kalktığı görüldü. Bu ekran yeni sürümün açık piyasa kapsam/gecikme kabulü değildir.

19:04 TSİ üretim sağlayıcı kontrolünde takvim **200/0,283s**, teknik tarama
**200/0,472s** döndü. Takvim kaynak saat dilimi hâlâ bilinmiyor; iki aynı başlıklı
olay 17:00 ve 17:40 olarak geldi, kaynak saatleri sessizce birleştirilmedi.
EREGL şirket işlemleri 45s istemci süresinde tamamlanmadı; arkasındaki TUPRS
sorgusu 429 verdi. Bu şirket işlemleri API kabulü başarısızdır; ayrı aday
sürecin önceki başarılı sonuçları bu sonucu geçersiz kılmaz. Yavaş herkese açık
şirket sorgusunun ortak hesap kilidini tutması için ek dar düzeltme gerekir.

İkinci aday düzeltmede yalnız `company.actions`, mevcut `run_public` yoluna
alındı. Borsapy 0.11.0'ın gerçek `Ticker` zinciri incelendi: temettü ve sermaye
işlemleri herkese açık İş Yatırım sağlayıcısına gider; birleşik tablo bu verilerden
yerelde üretilir. Yönetici HTTP erişimi ve iki eşzamanlı araştırma sınırı korunur.
Bloke şirket sorgusu sırasında yeni fiyat aboneliğinin açılabildiği, diğer
araştırmaların hesap yolunda kaldığı ve hata/slot temizliği 49 testle doğrulandı.
Bu değişiklik İş Yatırım yanıt süresini hızlandırma iddiası taşımaz; yayın ve
HTTP kabulü aşağıdaki ikinci yayın kaydında ayrıca tamamlandı.

Hacim kalite bilgisi alarm hesaplayıcısında korunur; mevcut grafik/araştırma
yanıtı bu kalite alanını arayüze taşımaz. Grafikte görülen sıfır hacimler
doğrulanmış sıfır işlem hacmi olarak yorumlanamaz.

Özel kanıtlar `runtime-data/20261007-live-fix-deploy/` altında: yayın SHA256
`194082959e6868a4e0cbbe73cf0be59fa5a9c8bae1857fb7e26ed07ca31043c0`, bağımsız kabul
`e23f8b90a05cec6cf18086cbfe45e762cfc75bdf1592ccdd60869064f9696d6e`, sağlayıcı kontrolü
`210e237858d177cd9181304665ab390a20ea25e54f1b1fe9dc773dde6f92ccdd`.

## Şirket sorgusunun ayrılması: son API yayını

Kaynak **`a835eceaa0f8a2795e140137a2f237d246ca7008`**, yalnız API imajı
**`ghcr.io/rapto0/rapot/backend@sha256:c17fc9595d132e1e853148a37b73d38f4dec957fd38bf8542a68a44e5b564e7e`**.
Yerelde **1.697 Python testi** geçti (bir atlama/üç mevcut bağımlılık uyarısı).
[CI 37651616416](https://github.com/Rapto0/Rapot/actions/runs/37651616416)
beş iş; [yayın 37651671995](https://github.com/Rapto0/Rapot/actions/runs/37651671995)
iki başarılı iş/iki beklenen atlama ile tamamlandı. Frontend kodu değişmedi;
aynı 297 test ve audit/lint/typecheck/build/standalone kontrolleri CI'de geçti.
120 runtime paketi ve 287 kaynak dosyası yayın artifact'iyle doğrulandı.

Ek imaj bütçesi **10.252.411 bayt**; sabit 528 MiB rezerv + 64 MiB runtime/WAL
+ 2 MiB kanıt payı ile toplam **633.106.555 bayt**, ölçülen boş alan
**7.294.513.152 bayt**. Aynı gün alınan altı saatten genç, bağımsız restore'u
doğrulanmış 15 tabloluk yedek ve değişmeyen şema kapısı korundu.

**16:31:11 UTC yayın / 16:31:50 UTC bağımsız kabul geçti.** Yalnız API container'ı
değişti; frontend `c74c1ad`, bot `876f3f3`, middleware/PostgreSQL ve
Compose/current `279aa9f` korundu. Beş servis healthy/restart0; 15 tablo şeması,
üç `sent` olay ve tek kullanıcı listesi korundu. HTTPS sayfaları, statik örneklem,
11 anonim 401/no-store ve dört yönetici GET kontrolü geçti. Alarm motoru çalışıyor;
boş alan **7.286.444.032 bayt**. Migration, temizlik, yeni Telegram mesajı veya
emir gönderilmedi. Grafikte 1.000 mum ve Türkiye saati etiketi görüldü.

**16:32:18–16:32:34 UTC üretim eşzamanlı sorgu kontrolü:**

| İstek | HTTP ve süre | Sonuç |
|---|---|---|
| EREGL şirket işlemleri | 200 / 15,4769 saniye | 20 temettü, 6 sermaye işlemi, 26 birleşik kayıt; kesilmedi |
| THYAO/GARAN fiyat okuması | 200 / 0,0102 saniye | İki sonlu fiyat; kapanış sonrası ikisi de açıkça `stale` |
| TR takvimi | 200 / 0,1642 saniye | İki olay; kaynak saat dilimi hâlâ bilinmiyor |
| THYAO/GARAN teknik tarama | 200 / 0,5118 saniye | Önceki sayısal karşılaştırmayla tutarlı boş sonuç |

Üç kısa istek, şirket isteği hâlâ beklerken başladı ve tamamlandı; bütün HTTP
yanıtları `private, no-store`. API kimliği öncesi/sonrası aynıydı. Bu gözlem ve
gerçek Ticker zinciriyle yapılan kilit regresyon testi birlikte, dar ayrımın
çalıştığını destekler. İstemci isteklerinin örtüşmesi, her sağlayıcı çağrısının
aynı anda çalıştığını veya kapanış sonrası fiyatın canlı olduğunu kanıtlamaz.
Şirket işlemleri kaynağının 15 saniyeyi aşan yanıt süresi devam eder.

Özel kanıtlar `runtime-data/20261007-public-research-fix/` altında: yayın SHA256
`822154dfbe8028411d94b64cfe8e37c987d25b6200eb4cec315892d6bab60b23`, bağımsız kabul
`30c2e7162c1e3ca33df6fcfd5a8f2d9ec8b80dfd00889bc63ca04d3721226b54`, sağlayıcı ölçümü
`15b721eaf0da2c1b6f7b49163941aec8b182d9f6b3ba7ba34ae5410f9d76680a`.

Tam seans/tüm BIST kapsamı, 3.000 kuralın canlı yükü, saniyelik kayıpsız akış,
hacim erişimi, tüm kurumsal işlem düzeltmeleri ve takvim saat dilimi açık kalır.
Son düzeltmeler seans kapandıktan sonra yayımlandı; önceki canlı örneklem yeni
sürümün açık piyasa kabulü olarak sunulmaz.
