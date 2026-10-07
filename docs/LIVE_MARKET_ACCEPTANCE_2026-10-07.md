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

## Henüz başarılı sayılmayan kontroller

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
