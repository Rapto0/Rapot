# 12 Ekim — eski tarama geçmişinden gösterge ve liste alarmlarına geçiş

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

Kaynak, yerel test ve yayın/üretim temizliği kanıtları bu bölümde ayrı kaydedilir.
Üretimde silme henüz yapılmadı; hazırlanmış araç tamamlanmış silme kanıtı değildir.
Önceki bot kaldırma yayını `a099dbb` ve önceki veri koruma kabulü
[ayrı tarihsel kayıttadır](SERVER_ONLY_MIGRATION_2026-10-12.md).

13 Ekim devamında 1.751 Python testi/bir atlama, son yedek sözleşmesi düzeltmesinin
51 ilgili testi ve 269 kaynak dosyasının lint/format kontrolü geçti. Frontend'in
273 testi, lint ve TypeScript kontrolü geçti. Yerel Windows derlemesi PostCSS
alt süreç/IPC ve `.next` yazma hatalarıyla tamamlanamadı; normal Linux CI build ve
standalone kontrolü yayın şartıdır.

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
