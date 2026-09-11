# Packaging Refactor Map

**Güncelleme: 2026-09-11 — P2-2.** Bu harita gerçek implementasyon yerlerini ve korunan eski import yüzeylerini gösterir. İncelenen kaynak tabanı `ee49508`; bu güncellemede çalışan kod veya wrapper kaldırılmadı.

Eski belgedeki `P2-4` adı, `5515324` (2026-04-01) paketleme çalışmasının tarihsel iş numarasıdır. Güncel [devam planında](RAPOT_DEVAM_PLANI.md) belge/wrapper kapanışı **P2-2**, API yükü ve gecikme çalışması **P2-4** olarak izlenir.

## Gerçek implementasyon ve import yönleri

| Bileşen | Canonical implementasyon | Mevcut uygulama tüketicileri / sınır |
| --- | --- | --- |
| Sinyal olayı | `domain/events/signal_domain_event.py` | `domain.events` paket export'u üzerinden sync/async scanner ve handler kullanır. |
| Sinyali kaydetme ve yayına iletme | `application/scanner/signal_handlers.py` | `market_scanner.py` ve `async_scanner.py`, `persist_and_publish_signal_event` çağırır. Kayıt, payload ve publish fonksiyonları çağırandan alınır. |
| Scanner kalıcılığı | `infrastructure/persistence/{signal,trade,ops}_repository.py` | Scanner, scheduler, health API, trade manager ve `scripts/backfill_special_tags.py` gerçek alt modülleri kullanır. |
| Tarama geçmişi | `application/scanner/scan_history.py` → `infrastructure/persistence/ops_repository.py` | Sync/async tarama yaşam döngüsünün history yazımı; eski root wrapper üzerinden geçmez. |
| API servisleri | `application/services/{analysis,signal_trade,system,market_data}_service.py` | `api/main.py` ve `api/routes/system_routes.py` canonical servisleri kullanır. |
| API okuma repository'leri | `infrastructure/repositories/{analysis,signal_trade,system}_repository.py` | Analysis, signal/trade ve system servisleri bu katmana erişir; ORM/session erişimi repository'dedir. |
| Süreçler arası sinyal okuma | `infrastructure/persistence/signal_feed_repository.py` | `api/runtime/signal_feed.py`; eski wrapper karşılığı bulunmaz. |

**Handler yönü:** `scanner_side_effects.py` → `application.scanner.signal_handlers`. İki fonksiyonun gerçek gövdesi application dosyasındadır. Önceki belgenin application dosyasını wrapper olarak göstermesi ters ve yanlıştı.

Bu harita tamamlanmış bir katman bağımsızlığı iddiası değildir: `application/services/market_data_service.py`, hâlen `fastapi.HTTPException` ve `api.providers.market_data_provider.MarketDataProvider` kullanır. Mevcut boundary testleri tüm application modüllerinin API bağımlılığını yasaklamaz.

## Korunan wrapper envanteri

Kaynakta `register_wrapper_usage(...)` çağıran **12 modül** vardır. Tablodaki bütün modüller şu anda korunur; canonical hedefler kaldırılacak dosyalar değildir.

| Eski import yolu | Canonical import yolu | Depo içindeki doğrudan eski yol tüketicisi |
| --- | --- | --- |
| `scanner_events` | `domain.events.signal_domain_event` (`domain.events` export'u da geçerli) | `tests/test_packaging_compat.py` |
| `scanner_side_effects` | `application.scanner.signal_handlers` | `tests/test_packaging_compat.py`, `tests/test_scanner_side_effects.py` |
| `signal_repository` | `infrastructure.persistence.signal_repository` | `tests/test_packaging_compat.py` |
| `trade_repository` | `infrastructure.persistence.trade_repository` | `tests/test_packaging_compat.py` |
| `ops_repository` | `infrastructure.persistence.ops_repository` | `tests/test_packaging_compat.py` |
| `api.services.analysis_service` | `application.services.analysis_service` | Doğrudan import bulunmadı. |
| `api.services.market_data_service` | `application.services.market_data_service` | Doğrudan import bulunmadı. |
| `api.services.signal_trade_service` | `application.services.signal_trade_service` | Doğrudan import bulunmadı. |
| `api.services.system_service` | `application.services.system_service` | `tests/test_packaging_compat.py` |
| `api.repositories.analysis_repository` | `infrastructure.repositories.analysis_repository` | Doğrudan import bulunmadı. |
| `api.repositories.signal_trade_repository` | `infrastructure.repositories.signal_trade_repository` | Doğrudan import bulunmadı. |
| `api.repositories.system_repository` | `infrastructure.repositories.system_repository` | `tests/test_packaging_compat.py` |

Ek olarak `tests/test_wrapper_usage_telemetry.py`, `api.services.analysis_service`, `api.repositories.system_repository` ve `signal_repository` yollarını `importlib.import_module` / `importlib.reload` kullanan yardımcısıyla yükler. Boundary testlerindeki dosya/yol dizeleri çalışan import tüketicisi değildir.

Üç root repository wildcard re-export, diğer dokuz wrapper açık isim re-export'u kullanır. `api/services/__init__.py` ve `api/repositories/__init__.py` paket işaretleyicileridir; ayrı telemetry kaydı üretmez. `domain/events/__init__.py`, `infrastructure/persistence/__init__.py` ve `infrastructure/compat/__init__.py` canonical paket export'larıdır; bu kaldırma listesine dahil değildir. `database.py`, `db_session.py` ve root scanner modülleri gerçek kod içerir; isimlerinin root'ta olması onları wrapper yapmaz.

## Göçün mevcut durumu

| Tarihsel aşama | 2026-09-11 kaynak doğrulaması |
| --- | --- |
| Aşama 1: event ve handler yüzeyi | Event domain'e, handler application'a taşınmış; eski root yolları re-export. |
| Aşama 2: persistence | Gerçek repository'ler infrastructure altında; kritik runtime ve backfill importları canonical. |
| Aşama 3: API servis/repository yüzeyi | Dört servis ve üç okuma repository'si canonical paketlerde; eski API yolları wrapper. |
| Aşama 4: import sınırı ve telemetry | Kodda mevcut ve testli; önceki “sıradaki” etiketi geçerli değil. |
| Aşama 5: read-model telemetry / kaldırma | Opt-in telemetry kodu mevcut; wrapper kaldırma kabulü tamamlanmış değil. |

Güncel karar: paketleme/belge yönleri netleştirildi, **12 wrapper korunuyor**. Kaldırma öncesi tüketici, süreç ve sürüm kanıtları [Wrapper Deprecation Schedule](WRAPPER_DEPRECATION_SCHEDULE.md) içinde tanımlıdır.

## Doğrulama ve kanıt sınırı

2026-09-11'de Git'in izlediği **211 Python dosyası**, uygulama import edilmeden AST ile incelendi. `import` ve `from ... import ...` biçimlerinde wrapper kullanan runtime/script tüketicisi bulunmadı; yukarıdaki test tüketicileri korundu. Dinamik yollar ayrıca kaynak aramasıyla kontrol edildi. Bu tarama harici scriptleri, kurulu eski sürümleri, ignored dosyaları veya hesaplanan dinamik importları kanıtlamaz.

Seçilen `.venv` / **Python 3.12.8** ile şu izole koşum **37/37 geçti**:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_packaging_compat.py tests/test_wrapper_usage_telemetry.py tests/test_health_api_wrapper_telemetry.py tests/test_system_read_model.py tests/test_scanner_side_effects.py -q -p no:cacheprovider
```

Kapsam: 18 boundary, 7 alias kimliği, 3 import telemetry, 2 health telemetry, 5 system read-model ve 2 kayıt/publish davranış testi. Kök `conftest.py` gerçek dotenv yerine test ayarları kurar, dış ağı engeller ve SQLite/log/cache'i geçici alana ayırır. Bu koşum canlı endpoint, üretim telemetry gözlem dönemi, dış tüketici uyumluluğu veya tüm uygulamanın eksiksiz katman ayrımı kabulü değildir.

Boundary testlerinin bir bölümü seçilmiş dosyalardaki metin kalıplarını kontrol eder; alias testleri örnek export'ların aynı Python nesnesi olduğunu doğrular. Tüm export'lar ve bütün olası import biçimleri kapsanmış sayılmaz.
