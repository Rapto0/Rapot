# Veritabanı şema ve veri göçü politikası

Son kaynak doğrulaması: **11 Eylül 2026 / P2-2**. Rapot'un iki ayrı veritabanı yaşam döngüsü vardır. **Ana SQLite şemasında Alembic kullanılmaz; trading middleware PostgreSQL şeması Alembic ile yönetilir.** `db_session.py` ve `migrate_db.py` içindeki eski “No Alembic” ifadeleri yalnız ana uygulama için geçerlidir.

## İki ayrı veri alanı

| Alan | Kaynak / bağlantı | Şema yönetimi | Üretim başlangıcı |
| --- | --- | --- | --- |
| Ana bot/API | [models.py](../models.py), [db_session.py](../db_session.py); `DATABASE_URL` veya `DATABASE_PATH` | `init_db()` → `create_all()` → `ensure_sqlite_columns()` | Compose `main-init` başarısından sonra API/bot; API ve bot başlangıcı da `init_db()` çağırır. |
| Trading middleware | [middleware/infra/models.py](../middleware/infra/models.py), [db.py](../middleware/infra/db.py); ayrı `MW_DATABASE_URL` | [Alembic revision zinciri](../middleware/infra/alembic/versions), [schema.py](../middleware/infra/schema.py) | PostgreSQL sağlığı → `middleware-migrate` → güncel revision kontrolü → middleware. |

[docker-compose.yml](../docker-compose.yml) ana SQLite **dizinini** `main-init`, API ve bot arasında paylaşır; DB, WAL/SHM ve süreç kilidi birlikte kalır. Middleware bu dizini bağlamaz; PostgreSQL'in ayrı volume'u vardır. Fiyat önbelleği ayrı bir SQLite dosyasıdır. Ana uygulamanın SQLite PRAGMA/DDL kodu, farklı bir URL verilerek PostgreSQL desteği varmış gibi yorumlanmamalıdır.

## Ana SQLite: eklemeli şema güncellemeleri

`db_session.init_db()` eksik tabloları oluşturur ve mevcut tablolara açıkça tanımlanan eklemeleri uygular:

- `signals.special_tag` ve `idx_signals_special_tag` indeksi.
- `ai_analyses` sağlayıcı/model, skor, risk, haber, gecikme ve hata metadata alanları.
- `scan_history.mode`, `errors_count`, `status`; geçmiş için bilinmeyen mod/durum `unknown`, ölçülmemiş hata sayısı `NULL` kalır.

`ensure_sqlite_columns()` mevcut sütun adlarını `PRAGMA table_info` ile karşılaştırır; eksik sütuna `ALTER TABLE ... ADD COLUMN`, tanımlı indekse `CREATE INDEX IF NOT EXISTS` uygular. Mevcut sütunun tipini/constraint'ini veya bütün şemanın doğruluğunu karşılaştırmaz. `create_all()` da var olan tabloları modelle tamamen eşitlemez.

Yeni model/alan için hem model hem açık ekleme yolu incelenir. Eski şema örneğinde iki ardışık `init_db()` çağrısı, kayıt korunumu ve yeni okuma/yazma yolu test edilir. Drop, rename, tip daraltma veya tarihsel veri dönüşümü başlangıca sessizce eklenmez; ayrı veri koruma ve geri dönüş planı gerekir. Bu yolun Alembic revision numarası veya otomatik downgrade'i yoktur.

[scripts/runtime.py](../scripts/runtime.py) içindeki `init-main-db` komutu **şemaya yazabilir**. Üretim env/veri yolu ve Compose override dosyaları [dağıtım runbook'u](../scripts/DEPLOY.md) ile seçilmelidir; komut bir sağlık kontrolü yerine çalıştırılmaz. Kanonik uygulama runtime'ı Python **3.12**'dir.

## Veri taşıma ve backfill araçlarının sınırları

Bu araçlar otomatik deploy adımı değildir. Kaynak/hedef, tekrar çalıştırma davranışı, yedek ve geri dönüş ayrı incelenir.

| Araç | Gerçek hedef ve seçenekler | Kullanım sınırı |
| --- | --- | --- |
| [migrate_db.py](../migrate_db.py) | Kaynak `OLD_DB_PATH`, repo kökündeki `trading_bot.db` dosyasına sabittir; ORM hedefi settings üzerinden seçilir. `--dry-run`, `--backup`, `--no-backup`; normal koşumda yedek varsayılan olarak açıktır. | Genel veya tekrar çalıştırılabilir üretim migration'ı değildir. Sinyal eşleştirmesi sınırlıdır; trade ve scan-history kopyalarında tekrar eklemeyi önleyen kontrol yoktur. Kaynak/hedef aynı dosya olabilir. Dry-run kayıtları sayar; gerçek dönüşümün doğruluğunu kanıtlamaz. |
| [backfill_special_tags.py](../scripts/backfill_special_tags.py) | Kanonik `infrastructure.persistence.ops_repository` ve yapılandırılmış ana DB. Varsayılan BIST, tüm geçmiş, 900 saniye pencere. `--since-hours`, `--strategy`, `--market-type`, `--dry-run`, `--override-existing`, `--json`. | Dry-run etiket `UPDATE` işlemini atlar; DB bağlantısı ve coverage sorgularını yapar. Varsayılan dolu etiketi korur; `--override-existing` bunu değiştirir. Bütün geçmiş sorgusu pahalı olabilir. |
| [backfill_signal_details.py](../scripts/backfill_signal_details.py) | Repo kökündeki sabit `trading_bot.db`; `--limit` (5000), `--mode scanner-latest` veya `all`. | Dry-run ve DB yolu seçeneği yoktur. Piyasa verisi/önbellek çağrıları yapar ve doğrudan `signals.details` günceller. Bugünkü veriden hesaplama, tarihsel sinyal anının yeniden üretildiğinin kanıtı değildir. Salt okunur incelemede çalıştırılmaz. |

`migrate_db.create_backup()` yalnız ana dosyayı `shutil.copy2` ile kopyalar; aktif WAL kullanan DB'nin tutarlı çevrimiçi yedeğini garanti etmez. Üretim için doğrulanmış SQLite backup API snapshot'ı veya sahipliği bilinen yazıcılar durdurularak tutarlı veri/WAL işlemi gerekir. PostgreSQL yedeği bağımsızdır. “Dry-run” adı, import/log ve SQLite bağlantı ayarlarının tüm dosya yan etkilerinden arındırılmış olduğu iddiası değildir.

## Middleware PostgreSQL: Alembic ve üretim kontrolü

[scripts/runtime.py](../scripts/runtime.py), `migrate-middleware` ve `middleware` için açık `MW_DATABASE_URL` ister. Migration komutu `migrate_schema(get_engine())` çağırır; normal middleware başlangıcı revision'ı kontrol eder. [FastAPI lifespan](../middleware/api/main.py) da production ortamında aynı kontrolü uygular.

- Mevcut `mw_*` tabloları var ama Alembic revision yoksa `migrate_schema()` durur. **Otomatik `stamp head` yoktur.** Kaynağı belirsiz tablolar, yedek ve gerçek şema incelemesi olmadan başlangıç revision'ına atanmaz.
- Ardından `upgrade head` çalışır. `require_current_schema()`, DB revision kümesini repo graph'ının head kümesiyle karşılaştırır; eksik/eski/farklı revision başlangıcı engeller.
- `middleware/infra/alembic/env.py`, bağlantıyı middleware settings'ten alır. `alembic.ini` içindeki örnek URL hedefin doğrulandığı anlamına gelmez.
- Geliştirme/test ortamında doğrudan middleware FastAPI başlangıcı `create_all()` kullanabilir. Bu revision oluşturmaz ve migration kanıtı değildir. Kanonik container giriş noktası ortamdan bağımsız revision kontrolünü korur.

11 Eylül 2026 kaynak head'i **`20260907_0006`**:

| Revision | Şema/veri etkisi |
| --- | --- |
| `20260423_0001` | Temel `mw_*` tabloları ve ilişkiler. |
| `20260423_0002` | Sinyal/FIFO alanları, constraint ve indekslerin güçlendirilmesi. |
| `20260501_0003` | Decimal miktar/quote alanları; eski lot değerlerinden miktar alanlarına geçiş. |
| `20260907_0004` | Mod ve `inventory_scope`; kökeni bilinmeyen geçmiş `LEGACY_UNCLASSIFIED` olarak saklanır. |
| `20260907_0005` | Kapsam içinde benzersiz, geçmiş kayıtlar için nullable `client_order_id`. |
| `20260907_0006` | Fiyat/quote muhasebesinde 12 ondalık, komisyon toplamları ve `commission_complete`. Geçmiş ücretler tahmin edilmez; completeness başlangıcı `false`. |

İlk iki revision doğrudan foreign-key/check-constraint DDL'i içerir; **boş SQLite üzerinde tam `upgrade head` desteklenen kabul yolu değildir**. SQLite fixture'ları ve seçili sonraki revision testleri, tam PostgreSQL migration kabulünün yerine geçmez. Boş PostgreSQL'de zincirin tamamı ve production başlangıcı CI'de ayrıca doğrulanır.

`LEGACY_UNCLASSIFIED` kayıtlar aktif FIFO/risk kapsamlarından dışlanır; silinmez. Hesap/venue kökeni doğrulanmadan DRY_RUN veya LIVE kapsamına taşınmaz. Envanter kapsamı şema revision'ından ayrı bir iş kuralıdır. Downgrade sütun ve hassasiyet kaybettirebilir; uygulama rollback'i otomatik DB downgrade/restore değildir.

## Üretim ön kontrolü

1. Bileşen source SHA/image digest'lerini, `current` hedefini, gerçek env ve veri yollarını belirle. Yalnız frontend yayını backend migration'ı gerektirmez; karma imaj sürümleri bileşen bazında kaydedilir.
2. Şemaya/veriye yazılacaksa SQLite ve PostgreSQL için ayrı, geri okunarak doğrulanmış yedek hazırla. WAL, yazıcılar, disk rezervi ve önceki kodun yeni şemayı okuyabilirliği incelenir. Genel Compose config çıktısı sırları gösterebilir; `config --quiet` veya çıktısı yayımlanmayan kontrollü inceleme kullanılır.
3. Ana SQLite'da sütun/indeks ve temsilî okumalar; middleware'de mevcut revision/head eşleşmesi kontrol edilir. Ana `/health` tablolara erişimi sınar; bütün alanların, veri dönüşümlerinin veya tarama ilerlemesinin kanıtı değildir.
4. İncelenmiş tam deploy'da `main-init` ve `middleware-migrate` kendi veri alanlarında çalışır; korunması gereken veri ve servis kabulü kaydedilir. Bot durdurulmadıysa doğal yeni kayıtları koşulsuz öncesi/sonrası eşitlik hatası sayma.
5. Üretim middleware ayarları `MW_EXECUTION_MODE=DRY_RUN`, `MW_TRADING_ENABLED=false`, `MW_BINANCE_LIVE_ENABLED=false` kalır. Migration/deploy başarısı gerçek veya testnet emir yetkisi sağlamaz.

[Devam planındaki P1-2/P1-3/P1-4 kayıtları](RAPOT_DEVAM_PLANI.md), PG16/head `0006` üretim geçişini, ayrı boş PG16 simülasyon kabulünü ve ana scan-history şema kabulünü ayrı kanıtlarla içerir. P2-2 belge düzenlemesinde üretim DB'si açılmadı; üretim migration/backfill'i çalıştırılmadı. Gerçek TradingView alarm teslimi ve testnet/canlı emir kabulü kullanıcı tarafından ertelenmiştir.

## İzole test kanıtı

11 Eylül 2026'da `.venv` Python 3.12.8 ile mevcut testler **30/30 geçti**:

```text
python -m pytest tests/test_db_session.py tests/test_scan_history_repository.py middleware/tests/test_schema_gate.py middleware/tests/test_inventory_migration.py -q
```

Geçici SQLite/sentetik veriler kullanıldı; gerçek DB, PostgreSQL sunucusu veya borsaya bağlantı yoktu. Tekrarlı ana şema eklemesi, eski kayıtların bilinmeyen alanlarını koruma, eksik/eski revision reddi, otomatik stamp engeli ve seçili `0004–0006` dönüşümleri kapsanır. Mevcut `datetime.utcnow()` kullanımından **10 deprecation warning** alındı; P2-3 borcudur. Tam PostgreSQL zinciri için [CI](../.github/workflows/ci.yml) kanıtı ayrıca gereklidir.
