# Algotrading Spot — kapsam ve backlog durumları

Son eşleştirme: **11 Eylül 2026 / P2-2**. Güncel iş sırası ve kabul kanıtlarının ana kaynağı [RAPOT_DEVAM_PLANI.md](RAPOT_DEVAM_PLANI.md)'dir. Bu belge eski ALG kimliklerini korur; ilk taslaktaki boş kutular, tamamlanan P0/P1 işlerini yeniden açmak için kullanılmaz. Durumlar kod ile plandaki tarihli kabul kayıtlarının karşılaştırmasıdır; bu belge düzenlenirken dış servis veya emir testi yapılmadı.

## Mevcut kapsam ve çalışma sınırı

- Doğrulanan middleware girişi **TradingView webhook → Binance Spot** akışıdır. Python tarayıcısından middleware'e yeni doğrudan emir köprüsü tamamlanmış sayılmaz; ana bot/API ve middleware ayrı servis/veri alanlarıdır.
- Üretim **`MW_EXECUTION_MODE=DRY_RUN`, `MW_TRADING_ENABLED=false`, `MW_BINANCE_LIVE_ENABLED=false`** kalır. Gerçek/testnet emir gönderimi belge veya deploy yetkisiyle açılmaz.
- Kullanıcı **10 Eylül 2026'da** borsa/alarm dış kabulünü erteledi. Gerçek TradingView alarm JSON'u/HTTPS teslimi, ALL/FIRST ve saat filtresi runtime kabulü, sınırlı testnet emirleri ve canlı geçiş tamamlanmadı. Artık yanıt beklenmiyor; kullanıcı yeniden seçtiğinde mevcut araç/kanıtlardan devam edilir.
- Pine derlemesi ve standart Spot/engelli grafik kontrolleri **kullanıcı gözlemidir**. Ayrı PG16 üzerinde HTTPS, iki BUY/iki FIFO SELL ve restart/duplicate kabulü **operatör kaynaklı simülasyondur**; gerçek TradingView teslimi veya hesap dolumu değildir.
- P2-1 dashboard alarmları `/alarms` açıkken çalışan tarayıcı kurallarıdır; borsa emri, sunucu alarm servisi veya TradingView kabulü yerine geçmez.

## Eski taslaktan değişen kararlar

Gerçek sözleşme [TradingViewWebhookPayload](../middleware/domain/events.py)'dir. İlk taslağın `TradeSignal`, `confidence`, `timestamp`, `source_run_id` alanları v1 JSON'a eklenmiş değildir; fazla alanlar reddedilir. `barTime`, Pine'da **alarm üretim zamanı `timenow`** taşır; mum açılış zamanı değildir.

[Kanonik kod/yön eşlemesi](../middleware/domain/constants.py):

| BUY | SELL |
| --- | --- |
| `H_BLS`, `H_UCZ`, `C_BLS`, `C_UCZ` | `H_PAH`, `C_PAH` |

Ana tarayıcının `BELES`, `COK_UCUZ`, `PAHALI`, `FAHIS_FIYAT` etiketleri webhook `signalCode` alanına doğrudan gönderilmez. `FAHIS_FIYAT` için v1'de ayrı emir kodu yoktur. Ayrıntılar [middleware README](../middleware/README.md) ve [Pine sözleşmesi](../middleware/pine/README.md)'ndedir.

BUY quote bütçesi/çarpanıyla yeni tranche açar; SELL filtreleri karşılayan en eski açık tranche'ı seçer. Toz miktarlar silinmez. V1 tekrar kontrolü **aynı normalize payload + aynı execution/account kapsamı** içindir; aynı barın farklı kodu veya yeni üretim zamanı ayrı olay olabilir. “Bar başına yalnız bir emir” garantisi verilmez.

## ALG kimliklerinin güncel karşılığı

“Tamam”, ilgili **kod/izole kabul kapsamını** belirtir. Gerçek hesap ve canlı işlem kabulü ayrı ertelenmiş işlerde kalır.

### Platform ve sözleşme

| Kimlik | Durum | Kanıt ve kalan sınır |
| --- | --- | --- |
| ALG-001 — Sinyal sözleşmesi | **Tamam; v1 seçildi** | `TradingViewWebhookPayload`, schema/symbol/side/zaman doğrulaması; P1-3. Eski önerideki alanlar güncel zorunluluk değildir. [Sözleşme testleri](../middleware/tests/test_tradingview_contract.py). |
| ALG-002 — Platform matrisi | **Tarihsel araştırma önerisi** | [Broker factory](../middleware/broker_adapters/factory.py) yalnız `BINANCE_SPOT` seçer. Üç adaylı puan matrisi doğrulanmadı; mevcut Binance motorunu yeniden yazma işi açmaz. |
| ALG-003 — Limit/hassasiyet/komisyon | **Kod kapsamı tamam** | [Binance filtreleri](../middleware/risk/binance_filters.py), Decimal sizing, varlık bazlı ücret muhasebesi; P1-1. Gerçek hesap kabulü erteli; üçüncü varlık ücretinin quote dönüşümü yok. |
| ALG-004 — Anahtar ve yetki güvenliği | **Uygulama tabanı tamam; hesap kanıtı sınırlı** | Ayrı webhook/admin anahtarı, [yönetim auth](../middleware/api/dependencies.py), özel env dosyaları; P0-2/P1-2. Salt okunur testnet `canTrade=true` gözlemi, withdraw izninin kapalı veya canlı hesabın uygun olduğunun kanıtı değildir. |
| ALG-005 — Platform ADR | **Karar kod/README'de; formal ADR yok** | Birincil Binance Spot uygulanmış; fallback adapter yok. Yeni sağlayıcı ihtiyacında karşılaştırma/ADR hazırlanır; eski belge kutusu mevcut motoru geri açmaz. |

### Emir motoru

| Kimlik | Durum | Kanıt ve kalan sınır |
| --- | --- | --- |
| ALG-101 — Normalizasyon/audit | **Tamam** | [TradingService.process_webhook](../middleware/services/trading_service.py), doğrulanmış olay/order kayıtları; [webhook testleri](../middleware/tests/test_webhook_validation.py). Geçersiz payload emir işleyişine alınmaz. |
| ALG-102 — Kod → yön → niyet | **Tamam** | Altı kod, side eşleşmesi, `_build_binance_spot_intent`. Belirsiz kod yeni `NO_TRADE` nesnesi yerine validation/risk reddi alır. |
| ALG-103 — Adapter | **Binance Spot kapsamı tamam** | [BrokerClient](../middleware/broker_adapters/base.py): `submit_limit_order` ve client-ID recovery; somut adapter'da kural/bakiye sorguları var. Genel `cancel_order` veya çoklu broker arayüzü yok; IOC motorunun kabulü bunlara bağlı değildir. |
| ALG-104 — DRY_RUN | **Tamam** | [Adapter](../middleware/broker_adapters/binance_spot.py), [dry-run testleri](../middleware/tests/test_dry_run_flow.py), P1-3 izole VPS simülasyonu. Order POST'u yok; public kural/fiyat GET'i yapılabilir. LIVE geçişi eski taslaktaki tek bayrakla yönetilmez. |
| ALG-105 — Sizing/risk filtreleri | **Kod kapsamı tamam** | `PRICE_FILTER`, `LOT_SIZE`, `MIN_NOTIONAL`, `NOTIONAL`, yönlü fiyat yuvarlama/quantity floor; [testler](../middleware/tests/test_binance_filters.py). LIVE BUY bakiye kontrolü ayara bağlıdır; eşzamanlı dış hesap hareketini engellemez. |
| ALG-106 — Idempotency/journal | **Tamam** | Kapsamlı anahtar, POST öncesi kalıcı dispatch, execution report, restart/duplicate/FIFO; P0-3/P0-4/P1-1. [Idempotency](../middleware/tests/test_idempotency.py), [durable dispatch](../middleware/tests/test_durable_dispatch.py). Yetkili bypass replay açıkça yeni niyet oluşturabilir. |

### Risk, gözlemleme ve dayanıklılık

| Kimlik | Durum | Kanıt ve kalan sınır |
| --- | --- | --- |
| ALG-201 — Risk sınırları | **Kısmen tamam** | [RiskEngine](../middleware/risk/checks.py): günlük emir/zarar, açık tranche, sembol exposure/allowed-symbol sınırları ayara bağlı olarak mevcut. LIVE engeli için trading/live bayrakları var. Ayrı cooldown, anlık arm/disarm ve guard alarm sistemi yok. |
| ALG-202 — Reconciliation | **REPORT_ONLY kapsamı tamam** | [Testler](../middleware/tests/test_reconciliation.py), `GET /admin/reconcile/{symbol}`; free/locked/total farkı ve öneri. Periyodik onarım işçisi/günlük rapor yok. **Otomatik envanter tamiri bilinçli olarak desteklenmez:** manuel işlem, transfer, diğer kapsam ve ücret farkı tek başına düzeltme kanıtı değildir. |
| ALG-203 — Metrik/log/alarmlar | **Kısmen tamam** | [JSON logging/maskeleme](../middleware/infra/logging.py), sinyal-order-client kimlikleri, execution report ve health mevcut. Middleware dashboard/Prometheus, gecikme SLO'su ve kritik alarm eşikleri tamamlanmadı; ana dashboard metrikleri middleware emir metrikleri değildir. |
| ALG-204 — Hata kabulü | **Temel recovery/muhasebe testleri tamam** | [Recovery](../middleware/tests/test_order_recovery.py), [commission recovery](../middleware/tests/test_binance_commission_recovery.py), [muhasebe sınırları](../middleware/tests/test_accounting_edge_cases.py). Timeout/`-1006`/`-1007` sonrası aynı client-ID sorgulanır; belirsiz sonuçta kör order retry yoktur. Genel rate-limit backoff ve gerçek borsa arıza tatbikatı tamamlanmış sayılmaz. |
| ALG-205 — Operasyon komutları | **Kısmen tamam** | Auth korumalı replay/recovery/reconcile ve health var. Runtime `arm`/`disarm` endpoint/komutu yok; env ile canlı işlem açılması ayrı operasyon ve yetki gerektirir. Replay/recovery salt durum okuması değildir. |

### Gerçek hesap / canlı geçiş — kullanıcı tarafından ertelendi

| Kimlik | Durum | Yeniden ele alınırsa gereken kanıt |
| --- | --- | --- |
| ALG-301 — Canary live | **Ertelendi, yapılmadı** | Önce gerçek alarm teslimi ve ayrı kapsam/DB'de sınırlı testnet kabulü; ardından açık bütçe, sembol, hesap ve emir yetkisi. Bütçe ayarları canary yapıldığını göstermez. |
| ALG-302 — İşletim SLO'ları | **Açık; canlı kapsam erteli** | Ölçülebilir başarı/hata/gecikme hedefi, ölçüm kaynağı ve alarm/runbook. İzole testte duplicate çıkmaması üretim süreklilik SLO'su değildir. |
| ALG-303 — Rollback/incident drill | **Uygulama rollback'i doğrulandı; işlem tatbikatı erteli** | P1-6 uygulama rollback'leri DB restore olmadan kaydedildi. Gerçek açık emirlerle disarm/incident tatbikatı yapılmış sayılmaz. |
| ALG-304 — Production sign-off | **Canlı emir sign-off'u yok** | P1-2/P1-6/P2-1 servis/UI yayını kabul edildi. Hesap yetkileri, gerçek/testnet kabulü ve canlı işletim onayı ayrıca doğrulanmadan “canlı trading hazır” sonucu çıkarılmaz. |

## Devam yolu

Sırayı [devam planı](RAPOT_DEVAM_PLANI.md) belirler: bu belge P2-2 kapsamındadır; borsa emri gerektirmeyen P2 işleri ertelenen dış kabulü beklemez. ALG-002/005 araştırması, genel adapter/cancel veya otomatik reconciliation, eski kutular boş diye kendiliğinden yeni kapsam olmaz.

Kullanıcı dış kabulü yeniden seçerse P1-3 araçları ve sınırları korunur: testnet taslağı ayrı PG16/kapsamda en fazla **25 sanal USDT × 2 BUY + 2 FIFO SELL**, başlangıç bakiye/açık emir kontrolü, partial/unknown/eksik komisyon durumunda duruş ve audit/dust korunumu içerir. **Hazır taslak, çalıştırılmış emir testi değildir.** Otomatik temizleme/düzeltme emri eklenmez.

Şema/CLI sınırları için [DB_MIGRATION_POLICY.md](DB_MIGRATION_POLICY.md), dağıtım/rollback ve bileşen SHA kaydı için [scripts/DEPLOY.md](../scripts/DEPLOY.md) kullanılır. Bu eşleştirme yeni migration, gerçek alarm veya emir çalıştırma yetkisi oluşturmaz.
