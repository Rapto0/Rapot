# Architecture Refactor Sprint Plan

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
