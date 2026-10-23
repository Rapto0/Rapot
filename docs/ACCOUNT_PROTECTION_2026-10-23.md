# 23 Ekim TradingView hesap koruması ve alarm düzeltmesi

Kullanıcı grafikte şüpheli etkinlik nedeniyle hesap engeli gördü; yaklaşık yarım
saat sonra açıldığını bildirdi. Dört alarmın tetiklenmesini, CPU %95–98 durumunu
ve DigitalOcean PHP güvenlik e-postasını incelememizi istedi.

## Hesap koruması

[TradingView'in aynı mesaj için açıklaması](https://www.tradingview.com/support/solutions/43000674726-why-is-my-account-banned-due-to-suspicious-activity/)
otomatik veri toplamayı neden olarak belirtir; tekrarlar kalıcı engele varabilir.
Bu hesabın iç güvenlik kaydına erişim yoktur: kesin tetikleyici istek veya IP
kanıtlanmadı. Premium/BIST paketi, bu otomatik erişimin engel riski taşımadığını
göstermez. Çerez değişimi, IP değiştirme veya daha düşük sorgu hızıyla risksiz
olacağı sözü verilmez.

Yeni `BORSAPY_TRADINGVIEW_ENABLED=false` varsayılanı gateway başlangıcında
sabitlenir. TradingView kimlik doğrulama/yenileme, fiyat, mum, tarama ve özel
gösterge akışları kapalıdır. Bağlantı düzenleme/doğrulama veya otomatik retry bu
sınırı kaldıramaz. Bağlantı bilgileri ve kullanıcı kuralları silinmez. Bu kaynağa
bağlı BIST ve özel Pine kripto alarmları **çalışıyor sayılmaz**, açık koruma
mesajıyla veri bekler. Doğrudan Binance kullanan standart kripto ve bağımsız
takvim/araştırma yolları korunur. Eski önbellek taze alarm verisi olarak okunmaz.

Normal BIST mum işleri bu durumda planlanmaz; özel geçmiş ve native akış
hazırlığı da durur. Üretimde yalnız API kontrollü durdurularak otomatik erişim
kesildi; frontend/middleware/PostgreSQL korundu. Eski API imajı otomatik olarak
yeniden başlatılacak rollback hedefi değildir. Yeni yayın kabulü aşağıya eklenir.

## Dört alarm ve kaynak sorunu

23 Ekim 12:55:45–12:56:58 UTC salt okunur gözleminde dört etkin kural aynı
631 üyeli listeyi izliyor, intrabar/once_per_bar/Telegram açık:

| Kural | Koşul | Bakım öncesi bulgu |
|---|---|---|
| SMI N OY | AL veya SAT, 8 oy | 21 tarihsel başarılı teslim; sonuncusu 22 Ekim 10:00:17 TSİ AAGYO |
| RSI SCORE 27 | HTF RSI Score AL veya SAT, 27/70 | Bugün olay yok; özel hesap hazırlığı bekliyor |
| Haftalık RSI | RSI(14) ≤25 | Bugün olay yok; kısmi hazırlık |
| Günlük RSI | RSI(14) ≤10 | Bugün olay yok; eski veri |

Toplam 24 sent (21 SMI +3 önceki test), 6 not_requested, hata sıfır.
“Hiçbir alarm tetiklenmedi” tarihsel olarak doğru değildir; bugünkü yeni üç
kuralın tetiklenmemiş olması tek başına eşik hatası değildir. Eşikler veya
AL/SAT seçimi değiştirilmedi.

Özel hesap 2/1.262, 630 üyede seed_wait; native geçmiş sayacı 655.871 tamamlanan
istek/655.907 chart. Normal mum işi 1.262, bekleyen 1.204, en eski bekleme yaklaşık
1.146 saniye. Bunlar tek anlık gözlemdir; CPU %95–98 kullanıcının gözlemidir.
API belleği 284,7 MiB, kullanılabilir RAM 256,1 MiB ölçüldü.

Yerel tekrar üretimde, gerçek bir geçmiş sıfırlamasından sonra ham önbellekten
çıkan üye 180 saniyeyi aşan FIFO beklemesi nedeniyle tekrar “revizyon” sayılıyordu.
Bu, native tanık ve hesap hazırlığını yeniden başlatabiliyordu. Düzeltme aynı
üye/yayın belirteci/hesap epoch'unda zaten yapılmış sıfırlamayı hatırlar. Bütün
geçmiş yine karşılaştırılır; gerçek OHLC değişimi, kopma, yeni dönem ve hesap
değişimi korumaları sürer. Gecikmeli yeniden hazırlama testi önce hatayı üretti,
sonra geçti; gerçek revizyon ve tanık bekleme testleri de geçti.

Kanıtlar (özel runtime-data, Git'e alınmaz): `oct23-initial-coverage.json`
SHA256 `6ba5187e4ac69184a3410941b0996024c5ab5db72a7e47d0fb6d9b26e846ee7a`;
`oct23-rules-events.json` SHA256
`6e062b69dfc8a0f38be5f1827d03e531ca66b4816d645eb74f9b398785b79f0c`.
İkisi de `runtime-data/20261021-live-acceptance/` altındadır.

## PHP e-postası

DigitalOcean'dan 21 Ekim 20:46:12 UTC tarihli ilgili e-posta okundu;
DKIM/SPF/DMARC başarılıdır. Metin bütün müşterilere gönderilen genel uyarıdır.
[DigitalOcean duyurusu](https://www.digitalocean.com/blog/critical-php-rce-vulnerabilities-patch-now)
Droplet üzerindeki kullanıcı iş yüklerinin kontrolünü ister.
[PHP duyurusu](https://www.php.net/archive/2026.php#2026-10-21-5) iki CVE için
düzeltmeleri açıklar. 23 Ekim 12:55:35–12:56:02 UTC denetiminde Ubuntu host ve
çalışan dört container içinde PHP paketi/binary/süreç bulunmadı; nginx yalnız
üç localhost upstream'e proxy yapar, PHP/FastCGI yapılandırması yoktur. Bu
sunucuda bu iki CVE için PHP güncellemesi gerekmiyor. Başka DigitalOcean
varlıkları veya kapalı eski imajlar bu denetim kapsamında değildir.

## Yayın kontrolünde bulunan Next.js açıkları

İlk kaynak `45be03c` için CI'nin zorunlu npm denetimi mevcut Next.js 16.3.8
sürümünde iki kritik ve bir yüksek önem dereceli bildirim buldu. Bu kaynak
üretime alınmadı. Next.js ve eşleşen ESLint yapılandırması **16.4.2** sürümüne
yükseltilir; React 19.2.3 ve Sharp 0.35.5 korunur. Tam kilitli bağımlılık
denetimi 469 paket düğümünde sıfır bulgu verdi.

- [Görüntü optimizasyonu RCE](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw): duyurudaki glibc koşulu mevcut Alpine/musl imajıyla eşleşmez; Sharp 0.35.5 düzeltmesi de zaten vardır.
- [Cache Components RCE](https://github.com/vercel/next.js/security/advisories/GHSA-673q-mjm6-r5xr): mevcut uygulamada Cache Components veya `use cache` kullanımı bulunmadı.
- [Server Actions DoS](https://github.com/vercel/next.js/security/advisories/GHSA-p3m5-59mp-jv5r): mevcut kaynakta Server Action bulunmadı.

Bunlar istismar veya bildirilen CPU artışının nedeni olduğuna dair kanıt
değildir. Yine de savunmasız sürüm tutulmaz; temiz frontend imajı da yayına
dahil edilir. Kaynak ve üretim kabulü ayrıca kaydedilir.
