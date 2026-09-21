# Rapot belgeleri

Güncel iş sırası, kullanıcı yetkileri ve tarihli kabul kanıtları
[devam planında](RAPOT_DEVAM_PLANI.md) tutulur. Kod tabanıyla çalışma kuralları
[AGENTS.md](../AGENTS.md), ilk kurulum ise [kök README](../README.md) içindedir.

## Mimari ve geliştirme

- [Mimari ve veri akışları](ARCHITECTURE.md)
- [Frontend: kurulum, testler ve ekran davranışları](FRONTEND.md)
- [Canonical paketler ve compatibility importları](PACKAGING_REFACTOR_MAP.md)
- [Wrapper kaldırma koşulları](WRAPPER_DEPRECATION_SCHEDULE.md)
- [Veritabanı şema ve veri göçü](DB_MIGRATION_POLICY.md)

## Strateji ve backtest

- [Python, TypeScript ve Pine hesaplayıcı farkları](STRATEGY_COMPARISON.md)
- [Backtest nakit, maliyet ve FIFO](BACKTEST_ACCOUNTING.md)
- [Günlük veri, cutoff ve yürütme](BACKTEST_EXECUTION.md)
- [Ortak nakitli çoklu sembol portföyü](BACKTEST_PORTFOLIO.md)
- [Benchmark karşılaştırması](BACKTEST_BENCHMARK.md)
- [Dönemsel al-tut analizi ve eski WFA uyumluluğu](BACKTEST_WINDOW_ANALYSIS.md)
- [Sabit verili CLI ve raporların tekrar üretimi](BACKTEST_CLI.md)

## Middleware ve Pine

- [Binance Spot middleware: erişim, emir ve muhasebe sözleşmeleri](MIDDLEWARE.md)
- [Pine grafik, payload ve alarm sözleşmesi](PINE_CONTRACT.md)
- [Spot kapsamı ve eski ALG işlerinin karşılıkları](ALGOTRADING_SPOT_BACKLOG.md)

Gerçek alarm teslimi ve testnet/gerçek emir kabulü kullanıcı tarafından ertelidir;
rehberlerdeki hazırlık adımları tamamlanmış emir testi veya işlem yetkisi değildir.

## Dağıtım ve kabul kayıtları

- [Doğrulanmış commit ile Docker Compose dağıtımı](DEPLOY.md)
- [Frontend bağımlılık güvenliği ve üretim kabulü](FRONTEND_DEPENDENCY_SECURITY.md)
- [21 Eylül Pine derleme/grafik kabulü](PINE_RUNTIME_ACCEPTANCE.md)
- [Backup branch karşılaştırması ve aktarım yapmama kararı](BACKUP_BRANCH_REVIEW.md)
- [6–21 Eylül ayrıntılı devam geçmişi](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md)

Eski mimari backlog/sprint ve tasarım direktifi Git geçmişinde tutulur. Güncel
belgelerdeki tarihsel kayıtlar yeni iş, dosya silme veya üretim değişikliği emri değildir.

Kök `README.md` paket metadata'sı ve proje girişi, `AGENTS.md`/`CLAUDE.md`
araçların çalışma rehberleri olduğu için yerlerinde kalır. Frontend, middleware
ve Pine dizinlerindeki kısa README'ler buradaki ana rehberlere yönlendirir.
Kurulu bağımlılıkların lisans/README dosyaları ve hash ile doğrulanmış eski
operasyon kayıtları kendi paket veya kanıt dizinlerinde tutulur.
