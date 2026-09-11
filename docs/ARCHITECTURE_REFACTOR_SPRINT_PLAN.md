# Architecture Refactor Sprint Plan

## Güncel durum ve tarihsel iş numaraları — 11 Eylül 2026

Bu sprintler [eski mimari backlog](ARCHITECTURE_REFACTOR_BACKLOG.md) numaralarını
kullanır. Güncel öncelik ve kabul kaynağı [Rapot Devam Planı](RAPOT_DEVAM_PLANI.md);
aynı `P2-*` numaraları bu iki planda farklı işleri anlatır. Aşağıdaki tarihsel
adımların tamamını yeniden başlatmayın veya tüm sprintleri tamamlandı saymayın.

- **Sprint A:** `/ops/read-model/overview` ve `/ops/read-model/scanner-feed`
  [system routes](../api/routes/system_routes.py) içinde mevcut. Overview tek SQL
  çağrısında birden çok alt sorgu, scanner-feed ise UNION ALL projection kullanır
  ([repository](../infrastructure/repositories/system_repository.py)).
  [Response sözleşmesi testleri](../tests/test_system_read_model.py) ve
  [scan-history entegrasyon testleri](../tests/test_scan_history_repository.py)
  var; bunlar üretim gecikmesi veya sorgu maliyeti bütçesini kanıtlamaz. Güncel
  **P2-4** eşzamanlı yük ve gecikme işi açıktır.
- **Sprint B:** [Mimari sınır testleri](../tests/test_architecture_boundaries.py)
  route/service/repository ve canonical import kurallarını, ayrıca frontend'deki
  doğrudan Binance URL kullanımını denetler. [CI](../.github/workflows/ci.yml)
  bu dosyayı kapsayan `tests` paketini çalıştırır. Mevcut kaynak-temelli kontroller
  genel amaçlı, eksiksiz bir import-graph denetimi olarak sunulmamalıdır.
- **Sprint C:** [domain](../domain), [application](../application) ve
  [infrastructure](../infrastructure) klasörleri,
  [taşıma haritası](PACKAGING_REFACTOR_MAP.md) ve
  [compatibility regresyonları](../tests/test_packaging_compat.py) mevcut.
  Wrapper'ların kaldırılması ayrı kullanım kanıtı ve kabul ister;
  [kaldırma takvimi](WRAPPER_DEPRECATION_SCHEDULE.md) ve güncel **P2-2** izlenir.

## Korunan tarihsel sprint taslağı

Bu plan, `ARCHITECTURE_REFACTOR_BACKLOG.md` icindeki `P2-2`, `P2-3`, `P2-4`
basliklarini uygulanabilir sprint dilimlerine boler.

## Sprint A - Read Models (`P2-2`)

1. Health/ops dashboard icin tek sorguda ozet read-model endpointi ekle.
2. Scanner ekrani icin sinyal + trade + scan history birlesik projection katmani ekle.
3. Read-model response suresini ve sorgu sayisini testlerle sabitle.

## Sprint B - Dependency Governance (`P2-3`)

1. Route/Service/Repository sinirlari icin import-kurali testlerini genislet.
2. Frontend API katmaninda domain-modul disina dogrudan vendor URL yasagi ekle.
3. CI kapisina architecture boundary test grubunu zorunlu adim olarak bagla.

## Sprint C - Packaging Refactor (`P2-4`)

1. `domain`, `application`, `infrastructure` klasor ayirimini backend icin baslat.
2. Mevcut moduller icin kademeli tasima haritasi (alias + compatibility imports) cikar.
3. Tasima sonrasi import-path regression testleri ekle.

## Exit Criteria

1. Her sprintte en az bir davranis testi + bir boundary testi guncellenmis olacak.
2. `pytest -q` ve `frontend npm run build` her sprint sonunda yesil olacak.
3. Backward compatibility icin public API endpoint contractlari korunacak.
