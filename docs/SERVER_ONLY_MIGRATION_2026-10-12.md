# 12 Ekim 2026 — Telegram botundan site yönetimine geçiş

Kullanıcı eski otomatik COMBO/HUNTER Telegram motorunu ve Telegram'a bağlı AI'ı
kaldırmayı, işlemleri site üzerinden yönetmeyi istedi. Bu karar site alarmlarının
isteğe bağlı Telegram bildirimini veya grafik indikatörlerini kaldırmaz.

## Kaynak kapsamı

- Eski zamanlayıcı, sync/async scanner, Telegram komut/alıcı/gönderici, otomatik
  haber/AI zinciri, Telegram portföy komutları ve Flask sağlık sunucusu kaldırıldı.
- API içine gömülü bot ve açılışta scanner restore kaldırıldı. Eski `/analyze`
  yönetici yolu 410 döner. Site `/ai` ve `/market/analysis` korunur.
- Borsapy tarayıcı, COMBO/HUNTER hesapları, backtest, saklanmış sinyal/analiz/işlem
  geçmişi, kalıcı sunucu alarmları ve Telegram outbox'ları korunur. Şema değişmez.
- Sağlık ve üst çubuk ana API'yi izler. API, alarm motoru ve piyasa tazeliği
  farklı durumlardır. Geçmiş tarama ekranı arşivdir; gereksiz polling kaldırıldı.
- Compose botsuzdur; API varsayılan container girişidir. Telegram ayarları yeni
  kurulumda opsiyoneldir. Dokuz eski doğrudan/geçişli Python paketi lock'tan
  çıkarıldı; kalan sürümler değiştirilmedi. Temiz imaj yayını eski paketlerin
  imaj katmanlarından da çıkarılmasını sağlar.

## Üretim aşamaları

11:25:39 UTC'de yalnız kimliği doğrulanmış eski bot durduruldu ve yeniden başlama
politikası `no` yapıldı. API/frontend/middleware/PostgreSQL kimlikleri ve
yapılandırma dosyaları değişmedi. Bu adım yeni kaynak yayını kabulü değildir.

Yeni API/frontend yayını, dört servisli Compose/current geçişi, eski sağlık
proxy'sinin kaldırılması ve bağımsız kabul henüz bekleniyor. Eski bot geri
dönüşte de çalıştırılmaz. Veritabanı, özel ayarlar, şifreli kimlikler ve tarihsel
kayıtlar silinmez; middleware DRY_RUN/trading kapalı kalır.

Bu işte otomatik takip/timer, 3.000 üretim TEST kuralı, yeni Telegram test mesajı
veya emir oluşturulmaz. Önceki canlı piyasa/hacim/tam seans sınırları devam eder.
