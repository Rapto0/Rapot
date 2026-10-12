# Rapot belgeleri

Güncel iş sırası, kullanıcı yetkileri ve tarihli kabul kanıtları
[devam planında](RAPOT_DEVAM_PLANI.md) tutulur. Kod tabanıyla çalışma kuralları
[AGENTS.md](../AGENTS.md), ilk kurulum ise [kök README](../README.md) içindedir.

12 Ekim güncel kaynak düzeni: API, frontend, middleware ve PostgreSQL sürekli
servislerdir; init/migrate işleri tek seferliktir. Eski otomatik COMBO/HUNTER
Telegram tarayıcısı, Telegram komutları ve tarayıcıya bağlı AI kaldırılmıştır.
Site Borsapy taraması, indikatörler, backtest, `/ai` ve kullanıcı alarmlarının
isteğe bağlı Telegram teslimi korunur. `a099dbb` API/frontend yayını 12:05:39 UTC'de
yapıldı ve eski bot kaldırıldı; bağımsız kabulün güncel sonucu
[sunucu geçiş kaydında](SERVER_ONLY_MIGRATION_2026-10-12.md) tutulur.

## Mimari ve geliştirme

- [Mimari ve veri akışları](ARCHITECTURE.md) — güncel giriş noktaları, veri yolları ve korunan geçmiş kayıtlar.
- [Frontend: kurulum, testler ve ekran davranışları](FRONTEND.md)
- [Sunucuda çalışan alarmlar: kurallar, bildirim ve sınırlar](SERVER_ALARMS.md)
- [Borsapy araştırma merkezi, hesap bağlantısı ve kabul sınırları](BORSAPY_INTEGRATION.md)
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

Gerçek TradingView webhook teslimi ve testnet/gerçek emir kabulü kullanıcı tarafından ertelidir;
rehberlerdeki hazırlık adımları tamamlanmış emir testi veya işlem yetkisi değildir.
Rapot sunucu alarmından Telegram tesliminin 7 Ekim dar canlı kabulü bu ayrı
middleware/emir kabulünü tamamlamaz.

## Dağıtım ve kabul kayıtları

- [Doğrulanmış commit ile Docker Compose dağıtımı](DEPLOY.md)
- [12 Ekim eski otomatik botun kaldırılması ve sunucu geçişi](SERVER_ONLY_MIGRATION_2026-10-12.md)
- [Frontend bağımlılık güvenliği ve üretim kabulü](FRONTEND_DEPENDENCY_SECURITY.md)
- [21 Eylül Pine derleme/grafik kabulü](PINE_RUNTIME_ACCEPTANCE.md)
- [7 Ekim canlı BIST, Telegram ve veri kalitesi kabulü](LIVE_MARKET_ACCEPTANCE_2026-10-07.md)
- [8 Ekim tam seans ve 3.000 alarm kabulü; hacim/takvim bulguları](FULL_SESSION_ACCEPTANCE_2026-10-08.md)
- [12 Ekim izleme listeleri, CPU/RAM ve ihtiyaç temelli mum kuyruğu](WATCHLIST_EFFICIENCY_2026-10-12.md)
- [Backup branch karşılaştırması ve aktarım yapmama kararı](BACKUP_BRANCH_REVIEW.md)
- [6–21 Eylül ayrıntılı devam geçmişi](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md)

Eski mimari backlog/sprint ve tasarım direktifi Git geçmişinde tutulur. Güncel
belgelerdeki tarihsel kayıtlar yeni iş, dosya silme veya üretim değişikliği emri değildir.

Kök `README.md` paket metadata'sı ve proje girişi, `AGENTS.md`/`CLAUDE.md`
araçların çalışma rehberleri olduğu için yerlerinde kalır. Frontend, middleware
ve Pine dizinlerindeki kısa README'ler buradaki ana rehberlere yönlendirir.
Kurulu bağımlılıkların lisans/README dosyaları ve hash ile doğrulanmış eski
operasyon kayıtları kendi paket veya kanıt dizinlerinde tutulur.
