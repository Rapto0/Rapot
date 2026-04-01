# Architecture Refactor Backlog

Bu doküman, mimari iyileştirmeleri uygulama önceliğine göre P0/P1/P2 olarak sınıflandırır ve önerilen implementasyon sırasını tanımlar.

## P0 (Kritik)

1. `P0-1` `api/main.py` parçalama:
   - HTTP route/controller kodunu application service katmanından ayır.
   - Hedef: route dosyaları sadece request/response ve validation işlesin.

2. `P0-2` Scanner side-effect ayrımı:
   - `market_scanner.py` ve `async_scanner.py` içinde sinyal üretimi ile side-effect adımlarını ayır.
   - Side-effect örnekleri: DB yazımı, realtime publish, Telegram bildirimi, AI enrichment.

3. `P0-3` Realtime bootstrap ayrımı:
   - Realtime startup wiring (`ws_manager`, `bist_service`, publisher register) için ayrı runtime/bootstrap modülü çıkar.

4. `P0-4` Mimari boundary test kapısı:
   - Domain -> API transport direkt bağımlılığı gibi ihlalleri CI’da fail edecek testlerle genişlet.

5. `P0-5` Contract davranış sabitleme:
   - Kritik endpointler (`/signals`, `/trades`, `/candles`, `/market/*`) için refactor öncesi/sonrası davranışı contract testleriyle eşitle.

## P1 (Yüksek)

1. `P1-1` Repository standardizasyonu:
   - API tarafındaki doğrudan ORM query kullanımını service/repository katmanına konsolide et.

2. `P1-2` Veri sağlayıcı soyutlaması:
   - BIST/Kripto veri kaynaklarını ortak provider arayüzü altında topla (`MarketDataProvider` benzeri).

3. `P1-3` Frontend API facade bölme:
   - `frontend/src/lib/api/client.ts` dosyasını domain bazlı modüllere ayır (`signalsApi`, `marketApi`, `opsApi`).

4. `P1-4` Realtime istemci modülerleşmesi:
   - `use-realtime.ts` içinde connection lifecycle, parser ve state mutation sorumluluklarını ayır.

5. `P1-5` Domain event akışı:
   - Scanner çıktısını typed domain event listesi olarak üret, handler’lar ayrı sorumluluklarla tüketsin.

## P2 (Orta/Uzun Vade)

1. `P2-1` Persistence sadeleştirme:
   - Legacy DB yolu ile ORM kullanımını tekil birincil erişim modeline doğru kademeli sadeleştir.

2. `P2-2` Read-model/CQRS iyileştirmesi:
   - Dashboard/health/signal ekranları için optimize read model yaklaşımı tanımla.

3. `P2-3` Dependency governance:
   - Import graph kuralları ve mimari lint kontrolleri ekle.

4. `P2-4` Paketleme refactor:
   - Kod tabanını domain/application/infrastructure sınırlarına göre klasörleyerek kademeli taşı.

## Önerilen Implementasyon Sırası

1. `P0-4` Boundary test kapılarını güçlendir.
2. `P0-5` Contract/smoke baseline’ı sabitle.
3. `P0-1` API service layer extraction (`/signals`, `/trades`, `/stats`).
4. `P0-1` devam: market endpointleri (`/candles`, `/market/*`).
5. `P0-3` Realtime bootstrap ayrımını tamamla.
6. `P0-2` Scanner compute ve side-effect ayrımını uygula.
7. `P1-5` Typed domain event + handler modelini devreye al.
8. `P1-1` Repository standardizasyonunu tamamla.
9. `P1-2` Provider soyutlamasını uygula.
10. `P1-3` Frontend API facade modülerleşmesini bitir.
11. `P1-4` Realtime hook modülerleşmesini bitir.
12. `P2-1` Persistence consolidation planını uygula.
13. `P2-2`, `P2-3`, `P2-4` başlıklarını sprintlere bölerek ilerlet.
