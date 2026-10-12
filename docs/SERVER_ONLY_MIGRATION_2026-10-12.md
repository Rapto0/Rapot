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

**12:05:39 UTC'de `a099dbb9353bc7965cb03755fe6f166df16c4f6a` yayımlandı.**
API/frontend temiz imajlara, Compose ve `current` aynı kaynak sürümüne geçti.
Eski bot container'ı kaldırıldı. Dört sürekli servis sağlıklı/restart0;
middleware ve PostgreSQL container kimlikleri değişmedi. Eski `/health-api/status`
proxy'si 410 döner; site ana API sağlığını kullanır. Bağımsız kabul aşağıda tutulur.

`main.env` içinden yalnız `RUN_EMBEDDED_BOT` ve `BOT_LOCK_PATH` satırları kaldırıldı;
diğer bütün baytlar korundu. Önceki dosya sunucuda özel 0600 izinli yedektedir.
`release.env`, `middleware.env` ve şifreli Borsapy kimlik dosyası aynı hash/izinlerle
korundu. Veritabanı migration/restore yapılmadı. Middleware DRY_RUN, trading/live
kapalı kaldı. Eski bot geri dönüşte de başlatılmaz; korunan eski imajlar ve kaynak
kopyaları geri dönüş/çalışan middleware içindir, toplu temizlik yapılmadı.

## Doğrulama ve yedek

- Temiz 125 paketli yerel ortamda **1.709 Python testi geçti, bir test atlandı**;
  üç mevcut deprecation uyarısı kaldı. 274 Python dosyasının Ruff lint/format
  kontrolü ve `uv pip check` geçti.
- **309 frontend testi**, lint, typecheck, Next build ve standalone HTTP/statik/WS
  kontrolü geçti. npm audit 469 paket/sıfır bulgu; bu tüm güvenlik araçlarının
  sıfır bulgu verdiği iddiası değildir.
- Aynı kaynak için [CI 38244865553](https://github.com/Rapto0/Rapot/actions/runs/38244865553)
  beş işi geçti. [Yayın 38244888595](https://github.com/Rapto0/Rapot/actions/runs/38244888595)
  normal backend/frontend imajlarını üretti; üç eski türev imaj yolu atlandı.
  Linux imajında 111 kurulu runtime dağıtımı ve 279 kaynak dosyası doğrulandı;
  kaldırılan 10 dosya, dokuz paket ve üç modül bulunmuyor. Frontend native kanıtı
  Node20.20.2/Next16.3.8/Sharp0.35.5/vips8.18.7/rsvg2.63.2 gösteriyor.
- 11:33:10 UTC taze SQLite binary yedeği **1.342.660.608 bayt**; sunucu dışında
  bağımsız logical restore, integrity ve 15 tablo parmak izi kontrolü geçti.
  Yalnız bu işe ait geçici sunucu snapshot'ı kaldırıldı. Özel yedek Git'te değildir.
- İmaj indirme/açma bütçesi 1.566.988.854 bayt; rezerv/çalışma/kanıt paylarıyla
  gereken boş alan 2.189.842.998 bayttı. Yayın öncesi 6.924.644.352 bayt vardı;
  yayın sonunda 5.495.250.944 bayt kaldı. Sabit 528 MiB rezerv korundu.

## Kanıt kimlikleri

| Kanıt | Değer |
|---|---|
| API imaj referansı | `ghcr.io/rapto0/rapot/backend@sha256:9893c31713ba18eb878f8e899d5f33e11922cda5d6e022bc767ed388f75cd0dc` |
| Frontend imaj referansı | `ghcr.io/rapto0/rapot/frontend@sha256:c52866cae8b0e990c9196ac9ee984e852b5afabb4ec6980d40376ac8afc6c32a` |
| Yeni current | `/opt/rapot/releases/a099dbb9353bc7965cb03755fe6f166df16c4f6a` |
| Uzak yayın kaydı | `/root/rapot-ops/20261012-server-only/receipt.json`, `verified_four_service_release` |
| Yayın kaydı SHA256 | `6190a82a04b6f8f501c2cf5b3256d12c819a2df8e7718388cfe356c7cdf95d9e` |
| Binary yedek SHA256 | `0d1e5b118071a2c19c5e676354c5b4372d058f680e7448a6bd5ffb10b5ec681d` |
| Offhost yedek doğrulaması SHA256 | `646bad268cdb32e8e71bcc5b2b70b8260b9b08c792ff4cf8de41c802ab47b245` |
| CI/yayın/temiz runtime kanıtı SHA256 | `4bebafd672f426b7a6696acd785ac6e0c7e203a0186836c65c25dbae694f3181` |
| Linux kaynak manifest SHA256 | `9a7c998d6ad3bf871932785a8465e4f45e966f5192fa6ba1a081202bfb2fcb39` |
| 15 tablo şeması SHA256 | `c28ae9e08b49f21eeec1b4ceeb9a1853ac6232fbf33f1243055de7a510aec06b` |
| Bağımsız kabul dosyası | Yerel, Git dışı `runtime-data/20261012-server-only/acceptance-final.json` |
| Bağımsız kabul SHA256 | `d05f2dea8eeb2e83916ac522138c831f2b6797be0eaaccbef04bdb6d0dbeb443` |
| Son kabul aracı SHA256 | `2bd30cf7a261c5d1dae1620f741f0deea923efaef274e7d694384c42172c47dc` |

Yayın öncesi/sonrası dört küçük alarm tablosu bayt parmak izleri eşleşti:
üç önceden silinmiş kural kaydı, sıfır durum, üç önceki olay ve bir kişisel liste.
Kullanıcı kayıtları kanıt çıktısına yazılmadı. Tam DB doğrulaması sunucu dışında
yapıldı; üretimde büyük tablo taraması veya bütün geçmişin tekrar okunması yoktur.

## Bağımsız kabul

**12:14:44–12:15:02 UTC bağımsız salt okunur kabul geçti:**
`verified_four_service_acceptance`. Dört container sağlıklı/restart0/OOMfalse;
middleware/PG kimlikleri aynı. Eski bot ve 5000 portu dinleyicisi yok.
Yedi HTTPS SSR sayfası, 26 JS/CSS dosyası ve altı anonim 401/private,no-store
yanıtı geçti. Ana API sağlıklı, DB bağlı, realtime çalışıyor. Yönetici kimliği,
özel alarm durumu, emekli `POST /analyze/GARAN` için 410 ve site AI'ın mevcut
`GET /market/analysis` OpenAPI sözleşmesi doğrulandı; AI üretimi çağrılmadı.

İmajın 279 kaynak dosyası kanonik CI manifestine göre ham SHA256 ile eşleşti;
111 runtime dağıtımı ve kaldırılan dosya/paket/modüllerin yokluğu üretimde de
doğrulandı. Ayrı release arşivi ham hash'leri korundu; 268 dosyadaki Windows
satır sonu farkı yalnız arşiv/Git eşdeğerliği için doğrulandı, imaj baytlarına
normalizasyon uygulanmadı. Kabul çocuğunun tepe RSS'i 31.502.336 bayt;
uygulama/sağlayıcı modülleri import edilmedi.

Alarm motorunda son hata yok, Telegram yapılandırılmış. Etkin kullanım üç
kategoride sıfır; planlı/bekleyen mum işi, mum seri ve gösterge hücreleri sıfır.
805 sembollük evrende 805 abonelik ve **488 taze sembol** görüldü; abonelik sayısı
bütün evrende gecikmesiz fiyat kabulü değildir. Kontrol yeni sağlayıcı sorgusu
istemedi; çalışan servislerin arka plan sağlayıcı faaliyetini ölçmedi.

Üç kısa host örneği **289,53 / 289,62 / 290,23 MiB kullanılabilir RAM**,
iki beş saniyelik aralık **%10,98 / %22,33 CPU** gösterdi. Son boş alan
5.486.444.544 bayt. Bu kısa örnekler tam seans/3.000 canlı alarm kapasitesini
kanıtlamaz. Eski gözlem timer'ı disabled/inactive, servisi inactive kaldı.
15 tablo şeması, dört küçük alarm tablosu, özel dosyalar ve yeni config hash'leri
kabulün başında/sonunda eşleşti; ek servis restart'ı veya rollback gerekmedi.

İlk sarmalayıcı, helper'ın `future` importundan önce SPEC
atadığı için yerelde SyntaxError verdi; kaynak ayrı derlenerek düzeltildi.
Sonraki kaynak kontrolü, Windows `git archive` CRLF baytlarını Linux imajındaki
LF baytlarıyla karşılaştırdığı için durdu. Tanılı tekrar `source_files` aşamasını
gösterdi; 279 dosyanın tamamının yalnız CRLF→LF dönüşümüyle Git blob/CI kaynak
hash'lerine eşit olduğu doğrulandı. Kanonik tekrar, kontrol aracının site AI için
yanlış POST varsayımında durdu; gerçek GET sözleşmesiyle düzeltildi. Test fixture'ı
artık doğrulanmış OpenAPI snapshot'ını okur. Son aracın 17 çevrimdışı testi geçti.
Başarısız kayıtlar korunur; uygulama imajına veya servislere bu tanılar nedeniyle
değişiklik yapılmadı.

Bu işte otomatik takip/timer, 3.000 üretim TEST kuralı, yeni Telegram test mesajı,
ücretli AI üretimi veya emir oluşturulmadı. Önceki canlı piyasa/hacim/tam seans
sınırları devam eder. Telegram'ın yapılandırılmış olması yeni teslim testi,
AI yolunun bulunması gerçek model üretim kabulü değildir.
