# Packaging Refactor Map

Bu harita, `P2-4` kapsamina giren kademeli tasima adimlarinda
geri uyumlulugu korumak icin kullanilir.

## Asama 1 (Tamamlandi)

1. `scanner_events.py` -> `domain/events/signal_domain_event.py`
   - Durum: tasindi
   - Uyumluluk: `scanner_events.py` icinde re-export alias var.

2. Scanner side-effect handler surface
   - Canonical hedef: `application/scanner/signal_handlers.py`
   - Mevcut implementasyon: `scanner_side_effects.py`
   - Uyumluluk: `application` katmani wrapper olarak export ediyor.

## Asama 2 (Tamamlandi)

1. `signal_repository.py`, `trade_repository.py`, `ops_repository.py`
   icin canonical konum `infrastructure/persistence/*` olarak tanimlandi.
2. Legacy root importlar compatibility wrapper olarak korunuyor.
3. Runtime importlari canonical yola tasindi
   (`market_scanner`, `async_scanner`, `health_api`, `scheduler`, `trade_manager`).
4. Import-path regression testleri genisletildi
   (`tests/test_packaging_compat.py`, `tests/test_architecture_boundaries.py`).

## Asama 3 (Tamamlandi)

1. Canonical service package acildi: `application/services/*`
   - `analysis_service.py`
   - `signal_trade_service.py`
   - `system_service.py`
   - `market_data_service.py`
2. Canonical repository package acildi: `infrastructure/repositories/*`
   - `analysis_repository.py`
   - `signal_trade_repository.py`
   - `system_repository.py`
3. `api/services/*` ve `api/repositories/*` compatibility wrapper'a cevrildi.
4. Import boundary testleri canonical package ayrimini zorlayacak sekilde genisletildi
   (`tests/test_architecture_boundaries.py`, `tests/test_packaging_compat.py`).

## Asama 4 (Siradaki)

1. `api/main.py` ve `api/routes/system_routes.py` importlari canonical package
   (`application.services`) yoluna tasindi.
2. Compatibility wrapper kullanimi telemetry ile olculebilir hale getirildi.
   - Teknik: `infrastructure/compat/wrapper_telemetry.py`
   - Wrapper importlari `register_wrapper_usage(...)` ile kayit aliyor.
   - Test kapsami: `tests/test_wrapper_usage_telemetry.py`
3. Wrapper kaldirma takvimi tanimlandi:
   - Dokuman: `docs/WRAPPER_DEPRECATION_SCHEDULE.md`

## Asama 5 (Devam Ediyor)

1. Runtime telemetry snapshot'i ops read-model (`/ops/read-model/overview`) ve
   health read-model (`health_api:/status`) icin opt-in query param ile baglandi.
   - Query: `include_compat_telemetry=true`
   - Detail query: `include_wrapper_details=true` (production ortaminda otomatik gizlenir)
2. Takvim asamalarina gore eski import yuzeylerini kademeli kaldir.
   - Scanner runtime modulleri `scanner_events` wrapper yolundan
     `domain.events` canonical yoluna tasindi.
   - Scanner runtime modulleri `scanner_side_effects` wrapper yolundan
     `application.scanner.signal_handlers` canonical yoluna tasindi.
