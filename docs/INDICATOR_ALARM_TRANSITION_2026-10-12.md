# 12–13 Ekim — eski tarama geçmişinden gösterge ve liste alarmlarına geçiş

Kullanıcı eski otomatik COMBO/HUNTER motorunun sinyal/tarama geçmişini ve bütün
site sayfalarındaki bu arşive bağlı yüzeyleri kaldırmamızı istedi. COMBO/HUNTER
hesaplayıcıları diğer göstergelerle birlikte grafik ve yeni alarm koşulu olarak
korunur. Bu istek yeni alarm, emir, AI üretimi veya Telegram test mesajı oluşturmaz.

## Güncel kaynak sözleşmesi

- Dashboard sunucu izleme listelerini, alarm durumunu ve piyasa fiyatlarını sunar.
- `/signals`, `/alarms` sayfasına yönlenir. Menü, başlık bildirimleri, grafik haber
  paneli, tarayıcı ve sağlık sayfası eski sinyal/tarama tablosunu okumaz.
- `/scanner` Borsapy taramasıdır; eski COMBO/HUNTER geçmiş tarayıcısı kaldırılır.
- `/ai` kullanıcı isteğiyle analiz ve teknik gösterge incelemesi sunar; eski
  sinyal akışını beklemez. Yeni analiz üretimi bu kabulün kapsamında değildir.
- Eski sinyal/tarama/read-model REST yolları admin kontrolünden sonra `410`
  döner ve OpenAPI'de listelenmez. Eski signal WebSocket kimlik doğrulamasından
  sonra `4410` ile kapanır; signal SSE emeklidir. SQLite sinyal polling işi yoktur.
- Fiyat/mum/işlem akışları, kullanıcı alarm motorları ve isteğe bağlı Telegram
  teslimi korunur. `/stats` yalnız ana işlem kayıtlarının metriklerini döndürür.
- Eski scanner yerel listeleri silinmez; alarm merkezinden elle içe alınabilir.
  Otomatik aktarım, kural yaratma veya etkinleştirme yapılmaz.

## Veri temizliği sözleşmesi

`scripts/retire_legacy_history.py` normal uygulama başlangıcında çalışmaz. Parametresiz
çağrı I/O yapmaz. Plan salt okunurdur; uygulama açıkça hash ile seçilmiş plan,
bağımsız restore edilmiş taze yedek ve yazıcıların durduğunu gösteren taze host
kanıtı gerektirir. Silme tek SQLite transaction'ında, küçük batch'ler ve kaynak
sınırlarıyla yapılır. Hata/iptal geri alınır. Şema migration'ı ve VACUUM yapılmaz.

Silme kapsamı: `signals.strategy` tam COMBO/HUNTER eşleşmesi, eski `scan_history`,
bu sinyallere bağlı analizler veya eski scanner kaynağında doğrulanan sekiz tam
otomatik senaryo adı ve açıkça sayılmış eski scanner sayaç/kilit anahtarlarıdır.
Kurtarma tablosunda yalnız aynı eski sinyal gövdesi/indeks ilişkisi kanıtlanan
satırlar kapsama alınır; sınıflandırılamayan kurtarma satırları korunur.

Yedi alarm tablosu, izleme listeleri, araştırma çalışma alanları, gerçek işlem/emir
verisi ve bilinmeyen sayaç anahtarları typed parmak iziyle korunur. Silinen sinyale
bağlı işlem varsa yalnız `signal_id` bağı çözülür; finansal alanlar değişmez.
Özel ayarlar ve sağlayıcı kimlikleri rapora veya Git'e alınmaz. SQLite boşalan
sayfaları tekrar kullanabilir; mantıksal temizleme dosyanın küçülmesi anlamına gelmez.

## Kabul durumu

**Tamamlandı:** `8b4e1bab` 13 Ekim **14:46:08 UTC**'de API/frontend ve
Compose/current'e yayımlandı. Ayrı üretim temizliği **15:01:12 UTC**'de commit
edildi; aynı API container'ının sağlıklı açıldığı **15:01:29 UTC**'de doğrulandı.
Bağımsız salt okunur kabul **15:11:48 UTC**'de geçti. Önceki bot kaldırma
yayını `a099dbb` ve o aşamadaki bütün veri koruma kabulü
[ayrı tarihsel kayıttadır](SERVER_ONLY_MIGRATION_2026-10-12.md).

13 Ekim devamında 1.751 Python testi/bir atlama, son yedek sözleşmesi düzeltmesinin
51 ilgili testi ve 269 kaynak dosyasının lint/format kontrolü geçti. Frontend'in
273 testi, lint ve TypeScript kontrolü geçti. Yerel Windows derlemesi PostCSS
alt süreç/IPC ve `.next` yazma hatalarıyla tamamlanamadı; normal Linux CI build ve
standalone kontrolü son kaynak CI'sinde geçti.

Gerçek boyutlu **özel kopya** provası 13 Ekim 14:24:13 UTC'de geçti. 2.017.235
sinyal, 184 tarama, 26.393 eski otomatik analiz, beş eski sayaç ve 161.866 kanıtlı
kurtarma kalıntısı silindi; 290 sınıflandırılamayan kurtarma satırı korundu.
İlk 491 tahmini, tekrarlanan orijinal ID'leri tek kayda indirgeyen inceleme
hesabındandı; tüm kanıtlı eski sürümler sayılınca ek 201 indeks eşleşti.
Tek transaction uygulaması 83,58 saniye; tepe working set 33.878.016 bayttı.
Integrity/FK, 15 tablo şeması ve korunan kayıt parmak izleri geçti. Bu yerel
ölçüm Docker cgroup veya üretim kapasitesi garantisi değildir.

Prova, yedek kanıtının snapshot aşamasında henüz binary hash üretmediğini ortaya
çıkardı ve silmeden önce durdu. Araç artık gerçek snapshot→transfer receipt hash
bağını doğrular; değiştirilmiş kanıtı reddeden testler eklendi. Eski yedek zamanı
yalnız açıkça LOCAL/SIMULATED provanın enjekte edilen saatinde sabitlendi;
üretimin altı saatlik yedek ve beş dakikalık yazıcı durdurma sınırları değişmedi.

İlk kaynak CI'sinde Python/lint/security/frontend işleri geçti; Docker işi
silinmiş `scripts.smoke_signal_feed` aracını çağıran eski adımda durdu.
Emekli özelliğe ait bu adım kaldırıldı. Ana DB hazırlama, ayrı PostgreSQL
migration/startup, frontend container ve mevcut piyasa/alarm testleri korunur;
son kaynak için beş CI işinin tamamı yeniden doğrulandı.

## Kaynak ve yedek kanıtları — 13 Ekim

Son uygulama kaynağı `8b4e1bab46a2fd149cdb80ad85ada340692961ad`:
[CI 38414547462](https://github.com/Rapto0/Rapot/actions/runs/38414547462)
beş işin tamamında başarılı;
[imaj yayını 38414577648](https://github.com/Rapto0/Rapot/actions/runs/38414577648)
başarılıdır. Temiz backend imajındaki 111 dağıtım ve 274 kaynak/girdi dosyası
exact CI manifestiyle doğrulandı. Güvenlik işi report-only backend bulgularını
sıfır bulgu olarak yorumlamaz.

- Backend: `ghcr.io/rapto0/rapot/backend@sha256:d888e5286f37ca780b31a3c3d64b7012fc20fb0b61c12ecf699a0a10c519860f`
- Frontend: `ghcr.io/rapto0/rapot/frontend@sha256:2b482449ce7e06340e831511cc4475a48dd754a2f4dee45f913880cbdf609945`
- Taze binary yedek: 13 Ekim **14:19:03 UTC**, **1.342.660.608 bayt**;
  SHA-256 `0d1e5b118071a2c19c5e676354c5b4372d058f680e7448a6bd5ffb10b5ec681d`.
  Sunucu dışındaki özel dizinde bağımsız SQL dump/restore, integrity/FK ve
  15 tablo typed parmak izi doğrulandı. Geçici sunucu snapshot'ı kaldırıldı;
  bağımsız yedek ve restore kopyası korunur.
- Yedek kanıtı SHA-256 `ea29cd9fd902151d407e516304c4752e5c0938984b626a2393ebbd6c8a730a99`.
- Üretim planı SHA-256 `7c3d883c3f6de66e8afc7eeed51c566311b1bd6b390d05b0d3472d1c583f165a`.
  Başlangıç fingerprint'i yedekle, beklenen sonuç gerçek boyutlu özel kopya
  provasıyla birebir eşleşti. Plan salt okunur aşamada hazırlandı.

Yerel özel kanıt dizini `runtime-data/20261012-indicator-alarms/`, sunucu
kanıt dizini `/root/rapot-ops/20261012-indicator-alarms/` altındadır. Ham yedek,
kimlik bilgileri ve özel veritabanı satırları Git'e eklenmez.

## Üretim sonucu

| Kayıt | Silinen | Kalan |
|---|---:|---:|
| Eski COMBO/HUNTER sinyalleri | 2.017.235 | 0 |
| Tarama geçmişi | 184 | 0 |
| Eski otomatik AI analizleri | 26.393 | 0 |
| Eski scanner sayaç/kilit kayıtları | 5 | 0 |
| Kanıtlı kurtarma kalıntıları | 161.866 | 290 sınıflandırılamayan satır |

15 tablo şeması, yedi alarm tablosunun içeriği, tek kullanıcı listesi, üç önceki
alarm olayı, araştırma alanları ve finansal kayıtlar başlangıçla aynı parmak
izindedir. Finansal satır silme veya FK çözme gerekmedi (`trades=0`). Özel ortam
dosyaları ve şifreli sağlayıcı kimlikleri değişmedi. Middleware/PostgreSQL aynı
container kimliklerinde kaldı; DRY_RUN ve trading/live kapalı ayarları korundu.
Yayın yalnız API/frontend'i değiştirdi; temizlik için yalnız API durdurulup aynı
container yeniden açıldı. Dört servis healthy, restart sayıları sıfır, OOM yok.
Eski bot ve 5000 dinleyicisi yok; eski gözlem timer'ı disabled/inactive kaldı.

İşlem tek transaction, 128 MiB bellek ve 0,5 CPU sınırında tamamlandı. Eski
kayıtların boşaldığı ve korunan verilerin değişmediği bağımsız kabul sırasında
iki kez tam parmak iziyle doğrulandı. VACUUM, şema migration'ı, üretime restore
ve imaj/özel dosya temizliği yapılmadı. DB dosyası 1.342.660.608 bayt kaldı;
boşalan SQLite sayfaları yeniden kullanılabilir. Disk küçülmesi iddiası yoktur.

İlk SSH taşıması işlem bitmesine rağmen sonuç döndürmedi. Sunucudaki commit
receipt'i ve sağlıklı yeniden açılma kaydı yeni, salt okunur SSH bağlantısıyla
alındı; özgün plan/spec/yayın hash bağları doğrulandı. Yalnız kimliği doğrulanan
takılmış yerel SSH süreci kapatıldı; ilk taşıma `cleanup_transport_not_confirmed`
ile sonlandı. Silme veya servis başlatma tekrarlanmadı. Sunucudaki başarı kaydı,
yerel taşıma başarısızlığı ve bağımsız kabul ayrı kanıtlardır; ağ takılmasının
kök nedeni belirlenmedi.

Kabul 13 SSR sayfasını, 32 JS/CSS dosyasını, iki `307` yönlendirmesini ve 17
anonim `401/private, no-store` kontrolünü kapsadı. Yönetici JWT'siyle 20 HTTP
kontrolü (19 GET ve yalnız emekli analiz yoluna yan etkisiz bir POST), sekiz
emekli geçmiş GET'inin `410` yanıtı ve kimlikli signal WS `4410` kapanışı geçti.
`/stats` yalnız işlem metrikleri döndürüyor. Manuel AI ve gösterge inceleme yolu
OpenAPI'de var; AI üretimi, yeni alarm, Telegram mesajı veya emir yapılmadı.

Alarm motoru çalışıyor, son döngü hatasız ve Telegram yapılandırılmıştır. Sıfır
etkin kuralda mum işi/kuyruk **0/0** ve gösterge değer hücresi sıfırdır. 805
abonelik/146 taze sembol yalnız kabul anının örneğidir. Üç kısa örnekte yaklaşık
318,52–321,49 MiB kullanılabilir RAM, iki aralıkta %21,912/%2,405 CPU görüldü;
son boş alan **5.315.047.424 bayt**. Bunlar tam seans veya 3.000 canlı alarm
yükü kabulü değildir. Tam BIST tazelik/hacim/bölünme ve dış emir kabulü açık kalır.

Tarayıcıda ana sayfa, Borsapy tarayıcı ve manuel AI'nin oturumsuz görünümü
kontrol edildi. Açık yönetici tarayıcı oturumu bulunmadığından bu, yönetici
formları üzerinde etkileşimli kabul olarak sunulmaz; kimlikli API kontrolleri
ve frontend bileşen testleri ayrı olarak geçti.

Başlıca kanıt hash'leri:

- Yayın receipt'i: `2353fbe389b53f2783b83a43ad601628689f8e06f643f6189bcc51366a43fd69`
- Temizlik receipt'i: `f8d014feacb45e096e47e8573641e59dd2e1f7a40845e8ea08f011a8482c31a7`
- Yazıcı durdurma kanıtı: `903b14493f06331c605e0527f6b146beaaa07cd561a243e677bae6db99af39c5`
- Host sonuç kaydı: `7eab2725aa56cd8bb65424570a90e46f2eef609b661d172c8e0bca6c33ae5bdf`
- Bağımsız `acceptance.json`: `31d4f20f0ff16338cb4ae6d1c30c0cf1f56b99e5b3e76b188f2df9b12a778cbf`
