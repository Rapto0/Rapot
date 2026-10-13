# Wrapper Deprecation Schedule

**Aktif kaynak güncellemesi: 2026-10-12.** [Envanterdeki 10 compatibility wrapper](PACKAGING_REFACTOR_MAP.md#korunan-wrapper-envanteri) korunuyor. Aynı gün ilk bot kaldırma değişikliği 12 wrapper'ı korumuştu; sonraki sinyal/tarama geçmişi temizliğinde tüketicileri kaldırılan `api.services.system_service` ve `api.repositories.system_repository` da kaldırıldı. Bu, genel takvimin otomatik uygulanması değildir. Diğer dış tüketicilerin kullanımının bittiği doğrulanmadı. Kaynak değişikliği üretim kabulü değildir; yayın ve veri temizliği [devam planında](RAPOT_DEVAM_PLANI.md) izlenir.

## Eski tarihler ile güncel kararın ayrımı

`5515324` (2026-04-01) ile kaydedilen aşağıdaki tarihler tarihsel hedeftir. Takvim gününün gelmesi, gözlem/uyarı döneminin gerçekten tamamlandığını göstermez.

| Tarihsel dönem / hedef | Kapsam | Bugünkü anlamı |
| --- | --- | --- |
| 2026-04-01 → 2026-06-30 | Gözlem | Bu döneme ait eksiksiz üretim gözlem kaydı bu incelemede doğrulanmadı. |
| 2026-07-01 → 2026-09-30 | Uyarı; API wrapper'ları için 2026-09-30 hedefi | Tarihsel grupta dört servis/üç repository vardı; bugün kalan üç `api.services.*` ve iki `api.repositories.*` wrapper içinde `planned_removal="2026-09-30"` hâlen var. Bu metadata otomatik silme/engelleme yapmaz. |
| 2026-10-01 → 2026-10-31 | Root yüzey; 2026-10-31 hedefi | `signal_repository`, `trade_repository`, `ops_repository`, `scanner_events`, **`scanner_side_effects`** içinde `planned_removal="2026-10-31"` hâlen var. |
| 2026-11-01 sonrası | Kaldırma hedefi | Aşağıdaki kabul kapıları sağlanmadan uygulamaya alınmayacak tarihsel hedef. |

Önceki listede yanlışlıkla root wrapper diye yazılan `application.scanner.signal_handlers` **gerçek implementasyondur**; kaldırma adayları arasında değildir. Onu re-export eden root dosya `scanner_side_effects.py`'dır. Canonical paketlerin `__init__.py` export'ları da bu takvimin deprecated wrapper kapsamına girmez.

## Telemetry neyi ölçer?

Kaynak: [wrapper_telemetry.py](../infrastructure/compat/wrapper_telemetry.py). Her wrapper modül gövdesinde `register_wrapper_usage(...)` çağırır.

- `usage_count`, wrapper gövdesinin çalışıp kayıt çağrısı yapmasını sayar. Python modül önbelleği nedeniyle sonraki sıradan importlar yeniden sayılmaz; `importlib.reload` sayıyı artırır. Bu, işlev çağrısı veya istek sayacı değildir.
- Veri `_wrapper_usage` sözlüğünde **yalnız o Python sürecinin belleğinde** tutulur. Süreç yeniden başlarsa kaybolur; API, worker ve ayrı komut süreçleri ortak bir gözlem geçmişi paylaşmaz. Kilit thread erişimini korur, süreçler arası toplama yapmaz.
- `total_wrappers`, kayıtta görülen modül sayısıdır; depodaki 10 modülün envanter sayısı değildir. Kayıt yalnız import sırasında oluştuğundan `active_wrappers` “halen iş yapan modül” anlamına gelmez.
- Uyarı logları örneklemeli/zaman sınırlıdır; log satırı sayısı kullanım sayısı değildir. `planned_removal` yalnız metin metadata'sıdır.
- `reset_wrapper_usage_snapshot()` test yardımcısıdır. Testlerin reload/reset sonuçları üretim kullanımı veya geçmiş gözlem penceresi olarak yorumlanmaz.

Eski HTTP telemetry yüzeyleri kaldırılmıştır: Flask `/status` ilk bot kaldırma
çalışmasında, `/ops/read-model/overview` ise sonraki geçmiş yüzeyi temizliğinde
kapatıldı. Son adres admin için `410` döner ve OpenAPI'de görünmez. Kalan
`infrastructure.compat` kütüphanesi süreç içi import telemetry'sini ve testlerini
korur; HTTP'den sinyal/tarama geçmişi veya wrapper ayrıntısı sunmaz.

**Boş snapshot kaldırma kanıtı değildir.** Bir sürecin ilgili yolu henüz
yüklememesi veya yeniden başlaması aynı sıfır sonucunu üretir. Önceki `/ops`
yanıtları tarihsel kanıttır; bunlardan tüm dış tüketicilerin bittiği sonucu
çıkarılmaz. Bu belge güncellemesinde canlı telemetry çağrısı yapılmadı.

## Kanıta bağlı kaldırma sırası

1. **Şimdi — koru, yeni importu canonical yaz.** Uygulama ve script importları canonical yollarda; eski yollar testlerde geriye uyumluluğu doğrulamak için kullanılıyor. Kalan üç API servis, iki API repository ve beş root wrapper korunur. Kaldırılan iki system wrapper'ının alias testleri korunan analysis wrapper'larına geçirildi; canonical persistence davranış testleri korunur. Belge kapanışı, wrapper dosyalarının kaldırılmasıyla eş anlamlı değildir.
2. **Tüketici ve gözlem kanıtını tamamla.** Kaldırma teklifinde modül grubu, sorumlu, kaynak sürüm, desteklenen dış script/entegrasyon tüketicileri, gözlenen süreçler, başlangıç/restart zamanları, gözlem başlangıç-bitişi ve kullanılan yollar kaydedilmeli. Örneklem tüm ilgili zamanlanmış/manuel işleri kapsamalı; temsil kabiliyeti gerekçelendirilmeden rastgele gün sayısı seçilmemeli. Bu kayıtlar şu anda tamamlanmış sayılmıyor.
3. **Sürümlü uyumluluk duyurusu ve dar kaldırma değişikliği hazırla.** Tüketicilerin yeni importlara geçtiği doğrulandıktan sonra API wrapper grubu ve root wrapper grubu ayrı değerlendirilmeli. Kaldırılacak dosyalar açıkça listelenmeli; canonical implementasyonlar korunmalı. Sadece testleri susturmak için davranış testleri silinmemeli: örneğin `test_scanner_side_effects.py` canonical handler üzerinden devam etmeli, kaldırılan import için alias beklentisi bilinçli güncellenmeli.
4. **Kontrollü yayın ve geri dönüş.** Kaldırma değişikliğinde import/boundary ve ilgili davranış testleri, CI, gerçek başlangıç/yükleme yolları doğrulanmalı; import hatasında geri dönülecek önceki sürüm kaydedilmeli. Yeni kaynak değişikliğinin yayın/kabul durumu devam planından okunur; bu belge tek başına üretim işlemi kanıtı değildir.

## Mevcut kanıt ve kalan sınır

2026-09-11, `ee49508` tabanında 211 tracked Python dosyasının AST envanteri: 12 wrapper, uygulama/script tarafında doğrudan eski yol tüketicisi yok. Test importları ve üç telemetry reload örneği [paketleme haritasında](PACKAGING_REFACTOR_MAP.md) listelidir. Depo dışı veya hesaplanan dinamik yollar bu sonucun kapsamı değildir.

Aynı haritada korunan **11 Eylül tarihsel koşumunda** Python 3.12.8 altında **37/37** test geçti: boundary, örnek alias kimliği, telemetry, opt-in read-model ve handler kayıt/yayın davranışı. O komut kaldırılan Flask ve system read-model testlerini içerir; güncel koşum notu haritada ayrıca verilir. Ağ ve gerçek DB/dotenv erişimi kök test izolasyonu tarafından engellendi. Testler telemetry mekanizmasını doğrular; üretimde gözlem döneminin tamamlandığını veya kaldırmanın dış tüketicileri bozmayacağını doğrulamaz.
