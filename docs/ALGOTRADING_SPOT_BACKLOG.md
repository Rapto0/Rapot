# ALGOTRADING SPOT - SPRINT BACKLOG (ISSUE FORMAT)

Bu backlog, botun urettigi Combo/Hunter sinyallerini spot piyasada otomatik al/sat emrine cevirmek icin hazirlandi.

## Sabit Kisitlar
- Spot-only (futures, margin, leverage yok)
- Etiket aksiyonlari:
- `BELES`, `COK_UCUZ` -> `BUY`
- `PAHALI`, `FAHIS_FIYAT` -> `SELL`
- Varsayilan akista once `dry-run`, sonra canliya gecis

## Sprint 0 - Platform Karari ve Hazirlik

### ALG-001 - Sinyal Sozlesmesi ve Is Kurallari
**Aciklama:** Combo/Hunter ciktilarinin emir motoruna tek formatta aktarilmasi icin `TradeSignal` sozlesmesi tanimlanir.
**Etkilenen Moduller:** strategy katmani, scanner, execution katmani
**Acceptance Criteria:**
- [ ] Zorunlu alanlar net: `strategy`, `symbol`, `tag`, `confidence`, `timestamp`, `source_run_id`
- [ ] Etiket -> emir yonu kurali dokumante edildi
- [ ] Eksik/bozuk sinyal icin reddetme kurali tanimlandi

### ALG-002 - Platform Aday Matrisi ve Skorlama
**Aciklama:** Spot otomasyon icin aday platformlar (dogrudan API, otomasyon platformu, open-source framework) kriter bazli skorlanir.
**Etkilenen Moduller:** dokumantasyon, operasyon karari
**Acceptance Criteria:**
- [ ] Kriter agirliklari yazildi (ucret, API kalitesi, guvenilirlik, operasyon maliyeti)
- [ ] En az 3 aday ayni cetvelde skorlandi
- [ ] 1 birincil + 1 yedek secim netlesti

### ALG-003 - Ucret, Limit, Min-Notional ve Precision Dogrulamasi
**Aciklama:** Secilen platformda emir gercekleme kisitlari kesinlestirilir.
**Etkilenen Moduller:** execution policy, order sizing
**Acceptance Criteria:**
- [ ] Her sembol icin min-notional/step-size/price precision kurallari kayda alindi
- [ ] Komisyon modeli (maker/taker) hesap mantigina eklendi
- [ ] Kural ihlalinde emir olusturmayan guard eklendi

### ALG-004 - Guvenlik Baseline (API Key ve Secret Yonetimi)
**Aciklama:** Emir atma anahtarlarinin guvenli kullanimi ve operasyonel guvenlik kurallari belirlenir.
**Etkilenen Moduller:** config/env, deploy, operasyon
**Acceptance Criteria:**
- [ ] API key scope sadece trade yetkisi ile sinirli
- [ ] Withdraw izni kapali oldugu dogrulandi
- [ ] Secret dosyaya yazilmiyor; sadece env/secret store uzerinden okunuyor

### ALG-005 - Platform Secim Karar Dokumani (ADR)
**Aciklama:** Final secim, neden secildigi ve neden digerleri secilmedigi kayda alinir.
**Etkilenen Moduller:** docs, operasyon karari
**Acceptance Criteria:**
- [ ] Karar dokumani repo icinde
- [ ] Birincil + fallback platform acikca yazildi
- [ ] Go/No-Go kriterleri net (PoC metriklerine bagli)

## Sprint 1 - Emir Motoru PoC (Dry-Run Once)

### ALG-101 - Signal Normalizer Katmani
**Aciklama:** Farkli scanner/strateji ciktilarini tek `TradeSignal` formatina ceviren katman eklenir.
**Etkilenen Moduller:** scanner, strategy, execution ingress
**Acceptance Criteria:**
- [ ] Tanimli format disi sinyal sisteme girmiyor
- [ ] Normalize edilen sinyal kaydi (audit) tutuluyor
- [ ] Birim testler eklendi

### ALG-102 - Execution Policy (Tag -> Action -> Order Intent)
**Aciklama:** Etiketi emir niyetine cevirmek icin merkezi karar modulu yazilir.
**Etkilenen Moduller:** execution policy
**Acceptance Criteria:**
- [ ] `BELES/COK_UCUZ` yalniz `BUY` uretiyor
- [ ] `PAHALI/FAHIS_FIYAT` yalniz `SELL` uretiyor
- [ ] Belirsiz etiketlerde `NO_TRADE` donuyor

### ALG-103 - Exchange Adapter Arayuzu
**Aciklama:** Platform bagimsiz calisma icin ortak adapter kontrati tanimlanir.
**Etkilenen Moduller:** execution adapter katmani
**Acceptance Criteria:**
- [ ] `get_balance`, `get_symbol_rules`, `place_order`, `cancel_order`, `get_order` metodlari mevcut
- [ ] Adapter hatalari standart hata tipine mapleniyor
- [ ] Mock adapter ile entegrasyon testi geciyor

### ALG-104 - Dry-Run Execution Mode
**Aciklama:** Gercek emir atmadan tum karar ve risk akislarini test eden mod eklenir.
**Etkilenen Moduller:** execution engine, logging
**Acceptance Criteria:**
- [ ] Dry-run modunda borsaya emir gitmiyor
- [ ] Uretilecek emir niyeti loglanip izlenebiliyor
- [ ] Dry-run/canli farki tek bir feature flag ile yonetiliyor

### ALG-105 - Order Sizing ve Symbol Rule Guard
**Aciklama:** Emir miktari bakiye, risk limiti ve sembol kurallarina gore hesaplanir.
**Etkilenen Moduller:** risk, execution policy
**Acceptance Criteria:**
- [ ] Min-notional alti emir uretilmiyor
- [ ] Bakiyeden fazla emir olusturulmuyor
- [ ] Precision kurallari emirden once duzeltiliyor

### ALG-106 - Idempotency ve Order Journal
**Aciklama:** Ayni sinyalin tekrarinda cift emir olusmasini engelleyen mekanizma kurulur.
**Etkilenen Moduller:** persistence, execution, state management
**Acceptance Criteria:**
- [ ] `idempotency_key` uretiliyor ve saklaniyor
- [ ] Ayni key ile ikinci emir reddediliyor
- [ ] Emir yasam dongusu journal tablosunda izleniyor

## Sprint 2 - Risk, Gozlemleme, Dayaniklilik

### ALG-201 - Risk Guardrail Seti
**Aciklama:** Gunluk islem adedi, gunluk zarar limiti, cooldown ve kill-switch eklenir.
**Etkilenen Moduller:** risk engine, runtime control
**Acceptance Criteria:**
- [ ] Limit asiminda yeni emir olusmuyor
- [ ] Kill-switch aktifken tum trade kararlari bloklaniyor
- [ ] Guardrail tetiklenmeleri alarmlaniyor

### ALG-202 - Reconciliation Worker
**Aciklama:** Lokal order state ile platform state arasindaki farklari duzelten periyodik isci yazilir.
**Etkilenen Moduller:** scheduler, execution, persistence
**Acceptance Criteria:**
- [ ] `OPEN/PARTIAL/FILLED/CANCELED` durumlari dogru eslestiriliyor
- [ ] Yetim order tespit edilip raporlaniyor
- [ ] Reconciliation raporu gunluk olusuyor

### ALG-203 - Metrics, Logging, Alerting
**Aciklama:** Basari orani, reject oranlari, latency, hata kodlari ve kritik alarmlar izlenir.
**Etkilenen Moduller:** prometheus/logging, ops
**Acceptance Criteria:**
- [ ] Temel metrikler dashboardda gorunur
- [ ] Kritik hata siniflari icin alarm esigi tanimli
- [ ] Run bazli iz surulebilirlik (trace-id/source_run_id) mevcut

### ALG-204 - Failure Testleri (Timeout/RateLimit/Reject)
**Aciklama:** Borsa kaynakli tipik hata senaryolari test edilip geri toparlanma davranisi dogrulanir.
**Etkilenen Moduller:** adapter, retry/backoff, risk
**Acceptance Criteria:**
- [ ] Timeout durumunda kontrollu retry var
- [ ] Rate limitte backoff calisiyor
- [ ] Reject durumunda pozisyon/state bozulmuyor

### ALG-205 - Operasyon Komutlari (Arm/Disarm/Status)
**Aciklama:** Trade motorunu ac/kapat ve durum sorgulama komutlari standart hale getirilir.
**Etkilenen Moduller:** API/command handler/ops
**Acceptance Criteria:**
- [ ] `status`, `arm`, `disarm` komutlari mevcut
- [ ] Yetkisiz cagri engelleniyor
- [ ] Komutlar audit loga dusuyor

## Sprint 3 - Canary Canli Gecis

### ALG-301 - Kucuk Sermaye ile Canary Live
**Aciklama:** Sinirli butce ile canli trade baslatilip sistem davranisi izlenir.
**Etkilenen Moduller:** tum execution zinciri
**Acceptance Criteria:**
- [ ] Canary butce limiti teknik olarak enforce ediliyor
- [ ] Ilk canli hafta boyunca kritik olay yok
- [ ] Her islem sonrasinda otomatik post-trade kaydi olusuyor

### ALG-302 - SLO ve Isletim Esikleri
**Aciklama:** Canli ortam icin hedef servis seviyeleri ve operasyon esikleri netlestirilir.
**Etkilenen Moduller:** ops, monitoring
**Acceptance Criteria:**
- [ ] Emir basari orani hedefi tanimli
- [ ] Maksimum kabul edilen hata oranlari tanimli
- [ ] Alarm runbooklari dokumante edildi

### ALG-303 - Rollback ve Incident Drill
**Aciklama:** Beklenmeyen durumda trade motorunu guvenli sekilde durdurup geri donus tatbikati yapilir.
**Etkilenen Moduller:** deploy, runtime control
**Acceptance Criteria:**
- [ ] Tek komutla `disarm` ve yeni emir blokaj test edildi
- [ ] Rollback adimlari uygulanip dogrulandi
- [ ] Olay sonrasi rapor sabloni hazir

### ALG-304 - Production Sign-Off
**Aciklama:** PoC -> production gecisi icin teknik ve operasyonel kapanis kontrolu.
**Etkilenen Moduller:** tum sistem
**Acceptance Criteria:**
- [ ] Tum kritik issue'lar kapali
- [ ] Dokumantasyon ve runbook tamam
- [ ] Isletim sorumlulari tarafindan onaylandi

## Basari Metrikleri (Global)
- Cift emir orani: `0`
- Sinyalden emre median gecikme: hedef esigin altinda
- Reject orani: kabul edilen sinirin altinda
- Guardrail ihlali sonrasi hatali emir: `0`
- Canary donemde beklenmeyen kritik incident: `0`
