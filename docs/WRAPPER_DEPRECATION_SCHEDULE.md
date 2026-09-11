# Wrapper Deprecation Schedule

**Güncelleme: 2026-09-11 — P2-2.** Güncel karar: [envanterdeki 12 compatibility wrapper](PACKAGING_REFACTOR_MAP.md#korunan-wrapper-envanteri) korunuyor. Depoda uygulama importlarının canonical olması doğrulandı; tüm çalışan sürümlerde ve harici tüketicilerde kullanımın bittiği doğrulanmadı. Bu belge güncellemesi kod kaldırmaz ve yeni bir otomatik kaldırma tarihi belirlemez.

## Eski tarihler ile güncel kararın ayrımı

`5515324` (2026-04-01) ile kaydedilen aşağıdaki tarihler tarihsel hedeftir. Takvim gününün gelmesi, gözlem/uyarı döneminin gerçekten tamamlandığını göstermez.

| Tarihsel dönem / hedef | Kapsam | Bugünkü anlamı |
| --- | --- | --- |
| 2026-04-01 → 2026-06-30 | Gözlem | Bu döneme ait eksiksiz üretim gözlem kaydı bu incelemede doğrulanmadı. |
| 2026-07-01 → 2026-09-30 | Uyarı; API wrapper'ları için 2026-09-30 hedefi | Dört `api.services.*` ve üç `api.repositories.*` wrapper içinde `planned_removal="2026-09-30"` hâlen var. Bu metadata otomatik silme/engelleme yapmaz. |
| 2026-10-01 → 2026-10-31 | Root yüzey; 2026-10-31 hedefi | `signal_repository`, `trade_repository`, `ops_repository`, `scanner_events`, **`scanner_side_effects`** içinde `planned_removal="2026-10-31"` hâlen var. |
| 2026-11-01 sonrası | Kaldırma hedefi | Aşağıdaki kabul kapıları sağlanmadan uygulamaya alınmayacak tarihsel hedef. |

Önceki listede yanlışlıkla root wrapper diye yazılan `application.scanner.signal_handlers` **gerçek implementasyondur**; kaldırma adayları arasında değildir. Onu re-export eden root dosya `scanner_side_effects.py`'dır. Canonical paketlerin `__init__.py` export'ları da bu takvimin deprecated wrapper kapsamına girmez.

## Telemetry neyi ölçer?

Kaynak: [wrapper_telemetry.py](../infrastructure/compat/wrapper_telemetry.py). Her wrapper modül gövdesinde `register_wrapper_usage(...)` çağırır.

- `usage_count`, wrapper gövdesinin çalışıp kayıt çağrısı yapmasını sayar. Python modül önbelleği nedeniyle sonraki sıradan importlar yeniden sayılmaz; `importlib.reload` sayıyı artırır. Bu, işlev çağrısı veya istek sayacı değildir.
- Veri `_wrapper_usage` sözlüğünde **yalnız o Python sürecinin belleğinde** tutulur. Süreç yeniden başlarsa kaybolur; API, bot, worker ve ayrı komut süreçleri ortak bir gözlem geçmişi paylaşmaz. Kilit thread erişimini korur, süreçler arası toplama yapmaz.
- `total_wrappers`, kayıtta görülen modül sayısıdır; depodaki 12 modülün envanter sayısı değildir. Kayıt yalnız import sırasında oluştuğundan `active_wrappers` “halen iş yapan modül” anlamına gelmez.
- Uyarı logları örneklemeli/zaman sınırlıdır; log satırı sayısı kullanım sayısı değildir. `planned_removal` yalnız metin metadata'sıdır.
- `reset_wrapper_usage_snapshot()` test yardımcısıdır. Testlerin reload/reset sonuçları üretim kullanımı veya geçmiş gözlem penceresi olarak yorumlanmaz.

Kaynakta mevcut opt-in okuma yüzeyleri:

| Süreç / kod | İstek |
| --- | --- |
| FastAPI: `api/routes/system_routes.py` → `application/services/system_service.py` | `GET /ops/read-model/overview?include_compat_telemetry=true` |
| Bot health: `health_api.py` | `GET /status?include_compat_telemetry=true` |

Yollar servis içi route'lardır; dış proxy prefix'i dağıtım konfigürasyonuna bağlıdır. İki yüzey varsayılan olarak telemetry toplamasını yanıta eklemez. `include_wrapper_details=true`, yalnız `APP_ENV` production değilse ayrıntıları açar; production'da özet kalır ve `details_disabled_in_production` nedeni yazılır. Her iki çağrı da sadece yanıt veren sürecin kaydını okur.

**Boş snapshot kaldırma kanıtı değildir.** Sürecin henüz ilgili yolu yüklememesi, yeniden başlaması veya eski tüketicinin başka süreçte/cihazda çalışması aynı sıfır sonucunu üretir. Tek `/ops` veya `/status` yanıtından “kullanım tamamen bitti” sonucu çıkarılmayacak. Bu belge turunda canlı telemetry çağrısı yapılmadı.

## Kanıta bağlı kaldırma sırası

1. **Şimdi — koru, yeni importu canonical yaz.** Uygulama ve script importları canonical yollarda; eski yollar testlerde geriye uyumluluğu doğrulamak için kullanılıyor. `api.services.*`/`api.repositories.*` ile root wrapper'lar korunur. Belge kapanışı, wrapper dosyalarının kaldırılmasıyla eş anlamlı değildir.
2. **Tüketici ve gözlem kanıtını tamamla.** Kaldırma teklifinde modül grubu, sorumlu, kaynak sürüm, desteklenen dış script/entegrasyon tüketicileri, gözlenen süreçler, başlangıç/restart zamanları, gözlem başlangıç-bitişi ve kullanılan yollar kaydedilmeli. Örneklem tüm ilgili zamanlanmış/manuel işleri kapsamalı; temsil kabiliyeti gerekçelendirilmeden rastgele gün sayısı seçilmemeli. Bu kayıtlar şu anda tamamlanmış sayılmıyor.
3. **Sürümlü uyumluluk duyurusu ve dar kaldırma değişikliği hazırla.** Tüketicilerin yeni importlara geçtiği doğrulandıktan sonra API wrapper grubu ve root wrapper grubu ayrı değerlendirilmeli. Kaldırılacak dosyalar açıkça listelenmeli; canonical implementasyonlar korunmalı. Sadece testleri susturmak için davranış testleri silinmemeli: örneğin `test_scanner_side_effects.py` canonical handler üzerinden devam etmeli, kaldırılan import için alias beklentisi bilinçli güncellenmeli.
4. **Kontrollü yayın ve geri dönüş.** Kaldırma değişikliğinde import/boundary ve ilgili davranış testleri, CI, gerçek başlangıç/yükleme yolları doğrulanmalı; import hatasında geri dönülecek önceki sürüm kaydedilmeli. Bu turda bu aşama yürütülmedi.

## Mevcut kanıt ve kalan sınır

2026-09-11, `ee49508` tabanında 211 tracked Python dosyasının AST envanteri: 12 wrapper, uygulama/script tarafında doğrudan eski yol tüketicisi yok. Test importları ve üç telemetry reload örneği [paketleme haritasında](PACKAGING_REFACTOR_MAP.md) listelidir. Depo dışı veya hesaplanan dinamik yollar bu sonucun kapsamı değildir.

Aynı haritadaki tekrar üretilebilir komutla Python 3.12.8 altında **37/37** test geçti: boundary, örnek alias kimliği, telemetry, opt-in read-model ve handler kayıt/yayın davranışı. Ağ ve gerçek DB/dotenv erişimi kök test izolasyonu tarafından engellendi. Testler telemetry mekanizmasını doğrular; üretimde gözlem döneminin tamamlandığını veya kaldırmanın dış tüketicileri bozmayacağını doğrulamaz.
