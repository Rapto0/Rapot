# 16 Ekim 2026 büyük izleme listesi canlı kabulü

Kullanıcının **“Çalışmana devam et”** talimatıyla manuel kabul sürdürüldü.
Otomatik takip/timer kurulmaz; kullanıcıya ait kural, liste ve bildirim ayarı
korunur. Bu kayıt kaynak düzeltmesini, izole sağlayıcı denemesini ve üretim
kabulünü ayrı tutar. **İlk düzeltme `2ea4ea31` ile yayımlandı; tam 805 üyeli
canlı kabul başarısızdır. İkinci kapasite koruması kaynak aşamasındadır.**

## İlk yayın ve bulunan ikinci sınır

`2ea4ea31e68c07f6aec44f359546833d8d4665f8` API/frontend/Compose/current
yayını **08:24:52 UTC**, bağımsız kabul **08:25:20–08:25:48 UTC** tamamlandı.
15 tablo şeması, 12 statik tablo, kullanıcının etkin kuralı/revizyonu ve 805
üyeli listesi, üç eski olay korundu; yeni olay oluşmadı. Dört servis healthy/
restart0; middleware/PG ve özel dosyalar değişmedi. 13 SSR, 33 statik dosya,
iki yönlendirme, 18 anonim401, v2/5/289 katalog ve 422 doğrulandı. Tam kaynak
beş CI işi ve temiz imaj yayını geçti. Taze **1.342.660.608 bayt** yedek,
sunucu dışında bağımsız restore ve bütün tablo karşılaştırmasıyla doğrulandı.
İlk snapshot denemesi aktif yazıcılar nedeniyle ilerleyemedi; salt okunur
sabit transaction düzeltmesiyle ikinci deneme yaklaşık 13 saniyede tamamlandı.
İlk başarısızlık kanıtı saklandı. Kullanıcı kuralı durdurulmadı.

Yayın kabulünde CPU **%96,806/%98,597**, kullanılabilir RAM **293,55–303,28
MiB** idi; 372 native ret ve 679 bekleyen/eski sonuç vardı. Bu web/veri
koruma kabulü, canlı alarm kapasite kabulü değildir.

Tek sınırlı izole sağlayıcı tanısı **08:30:05 UTC** tamamlandı. İlk 500 seri
tamamlandı ve hata vermedi. Sonraki 16 seri eklenince `critical_error:
session_start_error — max charts per connection reached` geldi. Kesin 512
sınırı varsayılmıyor; güvenli yerel sınır **bağlantı başına doğrulanmış 500**
seçildi. RAM 278,6 → 196,9 MiB, süre 51,1 saniye; tanı bağlantısı kapatıldı.
Üretim dört bağlantıyla 8.050 fiziksel seri taşımaya devam edemez.

Salt okunur altı örnek **08:34:31–08:35:21 UTC** boyunca kullanıcı kuralı ve
liste hash'lerini değişmez doğruladı. Native abonelik sayısı 32→512→320→0
gibi tekrar başladı; derlenmiş hesap/sonuç sıfır, canlı işlenen sayaç 2.944'te
donuktu. Ana fiyat taze sayısı da sıfırdı. RAM 276,855–291,785 MiB, CPU yaklaşık
%38–51. Önceki gözlem aracının değişken sağlık alanlarını kural tanımına katması
yanlış `rule_changed_guard` üretmişti; açık statik alan listesiyle düzeltildi,
19 çevrimdışı kontrol geçti. Önceki kanıt silinmedi.

İkinci kaynak koruması her sembolün bütün TF'lerini tek bağlantıda atomik
planlar, bağlantı başına 500 fiziksel seriyi aşmaz ve çalışan sembolü başka
sokete taşımaz. Dört soket/10 TF örneğinde 200 sembol kabul edilir; diğer
605 sembol görünür kapasite durumuna geçer. Kullanıcının 805 üyeli tanımı
değişmez. Bu koruma tam kapsam çözümü değildir; uzun periyot native tanıklarını
paylaşan düzen ayrıca geliştirilecektir. 107 ilgili servis ve 26 akış testi
geçti; ikinci kaynak yayını ayrıca kaydedilecektir.

## Gerçek kullanıcı alarmında bulunan sorun

07:55:28 UTC / 10:55:28 TSİ salt okunur tanı API'yi sağlıklı/restart0 ve
kullanılabilir RAM'i **319,03 MiB** gösterdi. Kullanıcıya ait **bir etkin
izleme listesi alarmı**, 805 sembol ve 8.050 native seri talebi vardı.
Native bağlantı, derlenmiş hesap ve işlenen canlı fiyat sayıları **0/0/0**;
805 sembol bekliyor/eski durumundaydı. Bellekteki 601 eski sonuç hazır canlı
gösterge değildir. Normal mum işi/kuyruk 0/0 kalırken bu ayrı özel gösterge
akışı çalışamıyordu. Önceki üç gönderilmiş olay korundu.

İzole gerçek sağlayıcı denemesinde aynı sokette 100 seri açıldı. 250 seriye
birden büyütme yaklaşık 0,30 saniyede **`protocol_error: max sessions rate
reached`** üretti. Bu bir oturum açma hızı hatasıdır; toplam seri sayısının
250 ile sınırlı olduğunu kanıtlamaz. Eski akış aynı alıcı kilidini binlerce
abonelik mesajını gönderirken tutuyordu. Bağlantının tekrar kapanması bütün
canlı başlangıçları sıfırlıyor; geçmiş işçisi de hazır olmayan sembollere
gereksiz başlangıç sorguları yapabiliyordu.

## Kaynak düzeltmesi

- Bağlantı başına kontrol turunda en fazla **16 yeni native seri** açılır.
  Kalan işler sonraki turda devam eder ve bekleyen sayı durum çıktısındadır.
  Dört WS ve 8.192 yerel seri sınırı değişmez; bunlar sağlayıcı garantisi değildir.
  Alarm ekranı planlanan/istenen seriyi, açılan/bekleyen aboneliği ve canlı
  hesap başlangıcı hazır sayısını ayrı gösterir.
- Ağ gönderimleri alıcı kilidini tutmaz. Her sembolün native periyotları ve
  tek fiyat aboneliği aynı sıralı sokette kalır. `protocol_error` açıkça
  yakalanır; yalnız sabit hata kategorileri gösterilir, ham oturum bilgileri
  veya özel sağlayıcı payload'ı günlüklere yazılmaz.
- Çalışan mum içi hesapların geçmiş başlangıcı, sembolün taşıma kabulünü ve
  gereken bütün native mum tanıklarını bekler. Reddedilen/henüz açılmamış
  semboller hazır işleri engellemez. Geçmiş başarısızlığı 30 saniyeden
  başlayıp en fazla 1.800 saniyeye çıkan beklemeyle yinelenir; kopma kuyruğu
  bu beklemeyi atlamaz. Hazırlık kontrolü sembol indeksini kullanır; her işte
  bütün bağlantı üyelerini dolaşmaz. Kapanış/geçmiş replay sözleşmesi korunur.
- Açık native mumda yalnız `Close` değişince gereksiz mum callback'i
  üretilmez; gelen satır yine saklanır ve bütün fiyat olayları korunur.
  İlk veri, önceki mum düzeltmesi, O/H/L, metadata ve rollover olayları
  geçer. Günlük native mum değişince üst periyodun ilk gerçek yeni paketi
  yeniden tanık olur; önbellekteki satırdan sahte gün tanığı oluşturulmaz.

## İzole canlı protokol kanıtı

Üretim dosyaları değişmeden ayrı sınırlı tanı sürecinde, 50 sembol × 10 native
periyot = **500 seri** kademeli açıldı. İlk deneme yaklaşık 40 saniyede 500
`series_completed`, 197 fiyat ve 2.443 mum olayıyla sağlıklı bitti; sağlayıcı
ve callback hatası sıfırdı. Bu adayda gereksiz mum olaylarını azaltma henüz yoktu.

Mum olayı azaltmasını içeren sonraki adayın ayrı denemesi yaklaşık 40 saniyede
yine 500 seriyi tamamladı: **194 fiyat / 590 mum olayı**, 2.050 `du` paketi,
sıfır sağlayıcı/callback hatası ve sağlıklı kapanış. İkinci örneğin başlangıç
RAM'i 308,20 MiB'dı. Örnekler farklı piyasa anlarına ait olduğundan doğrudan
CPU veya aynı yükte yüzde performans kazancı iddiası yapılmaz. İkinci adayın
akış kaynağı SHA-256:
`4bbd0c88e5467139dec563e6957d81406db1cf00ee918bb81a9fd5b81af17bde`.

Yerel regresyonlar yavaş ağ gönderiminde alıcı thread'inin ilerlemesini, kademeli
kabul/iptali, güvenli hata kategorilerini, fiyatların korunmasını, son
kapanışın rollover'a taşınmasını, metadata ve yeni gün tanıklarını sınar.
Yerelde tam pakette **2.014 Python testi / bir atlama**, **307 frontend testi**
geçti. Son hazırlık indeksi, önizleme adaleti ve hata tanısı değişikliklerinin
ardından **97 ilgili Python testi**, arayüz metni sonrası **25 alarm ekranı
testi**, 290 Python kaynağında Ruff, frontend lint ve typecheck geçti. Son
kaynak CI'si ve yayın kabulü ayrıca kaydedilecektir.

805 sembol × 10 TF hazırlık kontrolünün yerel ortalaması **171 ms → 4,57 ms**
oldu; bu üretim CPU ölçümü değildir. Önizlemeler başlangıç kuyruğunun arkasında
süreleri dolmadan, her dört geçmiş işinden birini alır; seçilmiş iş kuyrukta
yinelenmez. Kalan üç iş alarm hazırlığına ayrılır.

## Açık kalan kabul ve korunan sınırlar

Yeni sürümün yedekli yayını, kullanıcının mevcut 805 üyeli alarmında 8.050
native seri kabulü, hazır hesap sayısı, uçtan uca gecikme ve kaynak tüketimi
henüz doğrulanmadı. 500 serilik protokol denemesi 3.000 canlı alarmı veya tam
seans kesintisizliğini kanıtlamaz. Yeni test alarmı/bildirim bu tanıda
oluşturulmadı; kullanıcının mevcut etkin Telegram tercihi değiştirilmedi.

[14 Ekim](LIVE_INDICATOR_ACCEPTANCE_2026-10-14.md) gerçek verisi üzerinde
beş gösterge × beş fiyat için 25/25 bağımsız formül eşleşmesi vardır; bu
TradingView derleyicisinden alınmış aynı an çıktısı değildir. Native mum
hacmi eksik/unknown kalır. Takvimde saat dilimi resmî kaynakta açık yalnız
iki olay ailesi eşleşti; tüm kaynak ve yaz/kış saati geçişleri doğrulanmadı.
Gerçek/testnet emir ve TradingView webhook kabulü bu çalışmanın kapsamında değildir.

Özel kanıtlar `runtime-data/20261016-live-market/` altında tutulur. Temel
kayıtlar `runtime-diagnostic-20261016.json`, `subscription-protocol-live.json`,
`subscription-paced-500-live.json` ve `subscription-paced-final-500-live.json`;
kimlik bilgileri ve veritabanları Git'e alınmaz.
