# Packaging Refactor Map

**Aktif kaynak güncellemesi: 2026-10-12 — eski sinyal/tarama yüzeylerinin kaldırılması.** Bu harita mevcut implementasyon ve import yönlerini gösterir; kaynak değişikliği üretim yayını veya veri temizleme kabulü sayılmaz. 12 Ekim'deki ilk bot kaldırma değişikliği 12 wrapper'ı korumuştu. Sonraki geçmiş yüzeyi temizliğinde tüketicileri kaldırılan iki system wrapper'ı da kaldırıldı; **10 wrapper korunuyor**. Aşağıdaki P2-2 ölçüm/test kayıtları `ee49508` tabanındaki **11 Eylül tarihsel kanıtlardır**. Üretim/kabul durumu [devam planında](RAPOT_DEVAM_PLANI.md) izlenir.

Eski belgedeki `P2-4` adı, `5515324` (2026-04-01) paketleme çalışmasının tarihsel iş numarasıdır. Güncel [devam planında](RAPOT_DEVAM_PLANI.md) belge/wrapper kapanışı **P2-2**, API yükü ve gecikme çalışması **P2-4** olarak izlenir.

## Gerçek implementasyon ve import yönleri

| Bileşen | Canonical implementasyon | Mevcut uygulama tüketicileri / sınır |
| --- | --- | --- |
| Sinyal olayı | `domain/events/signal_domain_event.py` | Canonical handler, `scanner_events` uyumluluk yüzeyi ve izole testler kullanır; eski sync/async scanner tüketicileri kaldırılmıştır. |
| Sinyali kaydetme ve yayına iletme | `application/scanner/signal_handlers.py` | `scanner_side_effects` re-export'u ve kayıt/yayın davranış testleri korunur. Kayıt, payload ve publish fonksiyonları çağırandan alınır; artık otomatik scanner girişi yoktur. |
| Ana kayıt yardımcıları | `infrastructure/persistence/{signal,trade,ops}_repository.py` | API startup, alarm durum anahtarları, `scripts/backfill_special_tags.py`, compatibility yüzeyleri ve testler canonical alt modülleri kullanır. Bu yardımcılar API startup sırasında geçmiş veri silmez. |
| Tarama geçmişi | `application/scanner/scan_history.py` → `infrastructure/persistence/ops_repository.py` | Context/persistence yardımcıları ve testleri korunur; eski scheduler bunları artık çağırmaz. Eski `/scans` kapalıdır; iç okuyucu tarihsel şema/persistence testlerini destekler. |
| API servisleri | `application/services/{analysis,signal_trade,market_data}_service.py` | API canonical servisleri kullanır; signal_trade servisi artık yalnız trade listesi/özetini sunar. System read-model servisi kaldırıldı. |
| API okuma repository'leri | `infrastructure/repositories/{analysis,signal_trade,system}_repository.py` | Analysis/trade servisleri ORM'ye bu katmandan erişir. İç signal/scan okuyucuları bakım ve şema testleri için korunur; birleşik ops/scanner projeksiyonu kaldırıldı. |
| Piyasa realtime | `api/runtime/realtime_bootstrap.py` → `api/realtime.py` | Provider yaşam döngüsü ve piyasa WS/SSE; eski SignalFeed runtime, SQL okuyucusu ve smoke scripti kaldırıldı. |
| Süreç kilidi | `infrastructure/runtime_lock.py` | `api/runtime/advanced_alarms.py` ve `api/runtime/server_alarms.py` tek alarm motoru sahipliğini korur; eski isimli `bot_instance_lock` işlevi genel kilit yardımcısı olarak kullanılır. |

**Handler yönü:** `scanner_side_effects.py` → `application.scanner.signal_handlers`. İki fonksiyonun gerçek gövdesi application dosyasındadır. Önceki belgenin application dosyasını wrapper olarak göstermesi ters ve yanlıştı.

Bu harita tamamlanmış bir katman bağımsızlığı iddiası değildir: `application/services/market_data_service.py`, hâlen `fastapi.HTTPException` ve `api.providers.market_data_provider.MarketDataProvider` kullanır. Mevcut boundary testleri tüm application modüllerinin API bağımlılığını yasaklamaz.

## Korunan wrapper envanteri

Kaynakta `register_wrapper_usage(...)` çağıran **10 modül** vardır. Tablodaki bütün modüller şu anda korunur; canonical hedefler kaldırılacak dosyalar değildir.

| Eski import yolu | Canonical import yolu | Depo içindeki doğrudan eski yol tüketicisi |
| --- | --- | --- |
| `scanner_events` | `domain.events.signal_domain_event` (`domain.events` export'u da geçerli) | `tests/test_packaging_compat.py` |
| `scanner_side_effects` | `application.scanner.signal_handlers` | `tests/test_packaging_compat.py`, `tests/test_scanner_side_effects.py` |
| `signal_repository` | `infrastructure.persistence.signal_repository` | `tests/test_packaging_compat.py` |
| `trade_repository` | `infrastructure.persistence.trade_repository` | `tests/test_packaging_compat.py` |
| `ops_repository` | `infrastructure.persistence.ops_repository` | `tests/test_packaging_compat.py` |
| `api.services.analysis_service` | `application.services.analysis_service` | `tests/test_packaging_compat.py` |
| `api.services.market_data_service` | `application.services.market_data_service` | Doğrudan import bulunmadı. |
| `api.services.signal_trade_service` | `application.services.signal_trade_service` | Doğrudan import bulunmadı. |
| `api.repositories.analysis_repository` | `infrastructure.repositories.analysis_repository` | `tests/test_packaging_compat.py` |
| `api.repositories.signal_trade_repository` | `infrastructure.repositories.signal_trade_repository` | Doğrudan import bulunmadı. |

Ek olarak `tests/test_wrapper_usage_telemetry.py`, `api.services.analysis_service`, `api.repositories.analysis_repository` ve `signal_repository` yollarını `importlib.import_module` / `importlib.reload` kullanan yardımcısıyla yükler. Boundary testlerindeki dosya/yol dizeleri çalışan import tüketicisi değildir.

Üç root repository wildcard re-export, diğer yedi wrapper açık isim re-export'u kullanır. `api/services/__init__.py` ve `api/repositories/__init__.py` paket işaretleyicileridir; ayrı telemetry kaydı üretmez. `domain/events/__init__.py`, `infrastructure/persistence/__init__.py` ve `infrastructure/compat/__init__.py` canonical paket export'larıdır; bu kaldırma listesine dahil değildir. `database.py` ve `db_session.py` gerçek kod içerir; isimlerinin root'ta olması onları wrapper yapmaz. Kaldırılan `main.py`/scheduler/scanner/Flask dosyaları önceki 12 wrapper'ın parçası değildi.

## Göçün mevcut durumu

| Tarihsel aşama | 2026-09-11 kaynak doğrulaması |
| --- | --- |
| Aşama 1: event ve handler yüzeyi | Event domain'e, handler application'a taşınmış; eski root yolları re-export. |
| Aşama 2: persistence | Gerçek repository'ler infrastructure altında; kritik runtime ve backfill importları canonical. |
| Aşama 3: API servis/repository yüzeyi | Dört servis ve üç okuma repository'si canonical paketlerde; eski API yolları wrapper. |
| Aşama 4: import sınırı ve telemetry | Kodda mevcut ve testli; önceki “sıradaki” etiketi geçerli değil. |
| Aşama 5: read-model telemetry / kaldırma | Opt-in telemetry kodu mevcut; wrapper kaldırma kabulü tamamlanmış değil. |

Güncel karar: `api.services.system_service` ve `api.repositories.system_repository`, eski geçmiş/read-model tüketicileriyle birlikte kaldırıldı; canonical system servis ve projeksiyonları da artık kullanılmıyor. **10 wrapper korunuyor**. Bu dar işlev kaldırımı genel wrapper takviminin tamamlandığı anlamına gelmez. Kaldırma öncesi tüketici, süreç ve sürüm kanıtları [Wrapper Deprecation Schedule](WRAPPER_DEPRECATION_SCHEDULE.md) içinde tanımlıdır.

## Doğrulama ve kanıt sınırı

2026-09-11'de Git'in izlediği **211 Python dosyası**, uygulama import edilmeden AST ile incelendi. `import` ve `from ... import ...` biçimlerinde wrapper kullanan runtime/script tüketicisi bulunmadı; yukarıdaki test tüketicileri korundu. Dinamik yollar ayrıca kaynak aramasıyla kontrol edildi. Bu tarama harici scriptleri, kurulu eski sürümleri, ignored dosyaları veya hesaplanan dinamik importları kanıtlamaz.

11 Eylül'de seçilen `.venv` / **Python 3.12.8** ile şu izole koşum **37/37 geçti**. Aşağıdaki komut tarihsel kayıttır; kaldırılan Flask sağlık ve system read-model testlerini içerdiğinden güncel koşum komutu olarak kullanılmaz:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_packaging_compat.py tests/test_wrapper_usage_telemetry.py tests/test_health_api_wrapper_telemetry.py tests/test_system_read_model.py tests/test_scanner_side_effects.py -q -p no:cacheprovider
```

Kapsam: 18 boundary, 7 alias kimliği, 3 import telemetry, 2 health telemetry, 5 system read-model ve 2 kayıt/publish davranış testi. Kök `conftest.py` gerçek dotenv yerine test ayarları kurar, dış ağı engeller ve SQLite/log/cache'i geçici alana ayırır. Bu koşum canlı endpoint, üretim telemetry gözlem dönemi, dış tüketici uyumluluğu veya tüm uygulamanın eksiksiz katman ayrımı kabulü değildir.

Boundary testlerinin bir bölümü seçilmiş dosyalardaki metin kalıplarını kontrol eder; alias testleri örnek export'ların aynı Python nesnesi olduğunu doğrular. Tüm export'lar ve bütün olası import biçimleri kapsanmış sayılmaz.

Güncel kaynak için denetim komutu:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_architecture_boundaries.py tests/test_packaging_compat.py tests/test_wrapper_usage_telemetry.py tests/test_scanner_side_effects.py tests/test_retired_history_routes.py -q
```

Güncel test sayısı tarihsel 37 sonucundan türetilmez. Flask `/status` ve API `/ops/read-model/overview` telemetry okuma yüzeyleri kaldırılmıştır. Telemetry kütüphanesi kalan wrapper'ların süreç içi importlarını izlemeye devam eder; bu HTTP üzerinden eski sinyal/scan geçmişi sunmaz.
