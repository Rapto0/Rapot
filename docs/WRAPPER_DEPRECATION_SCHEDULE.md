# Wrapper Deprecation Schedule

Bu takvim, compatibility wrapper modullerini geri uyumluluk korunarak
kademeli olarak kaldirmak icin referans plandir.

## Faz 1 - Gozlem (2026-04-01 -> 2026-06-30)

1. Tum wrapper importlari telemetry ile izlenir.
2. Kritik runtime patikalarinda canonical import disi kullanimlar raporlanir.
3. Migration owner'lari moduller bazinda atanir.

## Faz 2 - Uyari Donemi (2026-07-01 -> 2026-09-30)

1. `api.services.*` ve `api.repositories.*` wrapper modulleri aktif kalir.
2. Yeni kodda bu wrapper path'lerinin kullanimi yasaklanir.
3. Planlanan kaldirma tarihi:
   - `api.services.*` -> `2026-09-30`
   - `api.repositories.*` -> `2026-09-30`

## Faz 3 - Legacy Root Surface Kaldirma Hazirligi (2026-10-01 -> 2026-10-31)

1. Root-level wrapper path'leri yalnizca geriye uyumluluk icin korunur:
   - `signal_repository`
   - `trade_repository`
   - `ops_repository`
   - `scanner_events`
   - `application.scanner.signal_handlers`
2. Planlanan kaldirma tarihi:
   - Yukaridaki legacy root wrappers -> `2026-10-31`

## Faz 4 - Kaldirma (2026-11-01 +)

1. Telemetry'de kullanim kalmayan wrapper'lar kaldirilir.
2. Kaldirma sonrasi boundary/regression testleri zorunlu calistirilir:
   - `tests/test_architecture_boundaries.py`
   - `tests/test_packaging_compat.py`
   - `tests/test_wrapper_usage_telemetry.py`

## Kabul Kriteri

1. Canonical import graph:
   - `application.services` -> `infrastructure.repositories`
   - runtime -> `application.services` ve `infrastructure.persistence`
2. Wrapper kullanimi sifirlandiginda ilgili wrapper dosyasi repository'den silinir.
