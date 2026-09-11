# Architecture Refactor Backlog

## Güncel durum ve tarihsel iş numaraları — 11 Eylül 2026

Bu dosya önceki mimari taslağı korur; güncel uygulama sırası ve kabul durumu
[Rapot Devam Planı](RAPOT_DEVAM_PLANI.md) üzerinden takip edilir. Aşağıdaki `P0-*`,
`P1-*`, `P2-*` numaraları **bu eski mimari planın numaralarıdır**; devam planındaki
aynı numaralı işlerle aynı anlama gelmez. Örneğin buradaki `P2-2` read-model,
güncel plandaki `P2-2` ise belge ve wrapper göçü işidir. Eski listeleri yeniden
uygulanacak açık işler olarak okumayın.

Kaynakta mevcut olan parçalar ve sınırları:

- Eski `P0-1` / `P1-1`: [application/services](../application/services) ve
  [infrastructure/repositories](../infrastructure/repositories) mevcut;
  [api/main.py](../api/main.py) bunlara delegasyon yapıyor, fakat bazı endpoint ve
  sağlayıcı işlemleri hâlâ bu dosyada. Bütün API'nin ince route katmanına taşındığı
  iddia edilmiyor.
- Eski `P0-2` / `P1-5`: [typed event](../domain/events/signal_domain_event.py) ve
  [canonical handler](../application/scanner/signal_handlers.py) mevcut.
  [Realtime bootstrap](../api/runtime/realtime_bootstrap.py) da ayrı (`P0-3`);
  P1-5 güncellemesinden sonra süreçler arası sinyallerin kaynağı
  [SQLite SignalFeed](../api/runtime/signal_feed.py). Eski publisher-register
  önerisi, scanner belleğinden ayrı API sürecine doğrudan teslim garantisi değildir.
- Eski `P1-2` / `P1-3` / `P1-4`: [MarketDataProvider adaptörü](../api/providers/market_data_provider.py),
  [frontend API facade](../frontend/src/lib/api/client.ts) ve
  [realtime modülleri](../frontend/src/lib/realtime) mevcut. Bu, bütün veri
  sağlayıcılarının veya tüm sorumlulukların taşındığı anlamına gelmez.
- Eski `P0-4` / `P0-5` / `P2-2` / `P2-3` / `P2-4`: boundary, contract ve
  compatibility testleri; read-model uçları; domain/application/infrastructure
  klasörleri mevcut. [Sprint planındaki durum notu](ARCHITECTURE_REFACTOR_SPRINT_PLAN.md)
  bunların kapsamını ayırır. Güncel **P2-2** belge kapanışı wrapper'ları koruma
  kararını ve koşullu kaldırma politikasını kaydeder; fiziksel kaldırma kabulü
  değildir. Ölçülmüş gecikme/kapasite kabulü güncel **P2-4** altında açık kalır.

## Korunan tarihsel taslak

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
