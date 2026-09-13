# Frontend bağımlılık güvenliği — P1-G2

İnceleme tarihi: **13 Eylül 2026**. Başlangıç kaynak sürümü
`d79f4cc841b3de411777730eb91a245ade96cd6e`; frontend kodu ve lock,
P3-1 dördüncü adım kapanışındaki durumdur. İş sırası ve üretim kabulü
[devam planında](RAPOT_DEVAM_PLANI.md#p1-g2--frontend-bağımlılık-güvenliği-takibi)
tutulur.

## Sonuç ve kapsam

Başlangıç `npm audit` raporu **11 etkilenmiş paket adı ve 46 benzersiz advisory**
bildirdi. Bir paket birden fazla advisory içerir; `minimatch` kendi yeni advisory'si
yerine `brace-expansion` etkisini taşır. Bu sayılar, kanıtlanmış 11 veya 46 üretim
açığı anlamına gelmez. Başlangıç bağımlılık yollarında altı paket yalnız geliştirme
araçlarına, beş paket üretim bağımlılıklarına da bağlıdır.

46 kaydın etki ve düzeltilmiş sürüm alanları ayrı ayrı okundu. 43 kayıt için
bakımcı security advisory sayfası, üçü için bakımcı düzeltme/release kaydı da
kontrol edildi. Tablo satırları özgün kaynaklara bağlantı verir. Özellik
erişilebilirliği değerlendirmeleri Rapot kaynak kodundan yapılan **statik
çıkarımlardır**; saldırı denemesi veya üretimde istismar edilebilirlik testi
yapılmadı.

Next'in Windows dosya sistemi gerektiren kritik bulgusu, kayıtlı Alpine/Linux
üretim yapısının işletim sistemi koşuluyla uyuşmaz. Bu durum diğer Next
bulgularını elemez. Özellikle self-hosted WebSocket upgrade SSRF ve varsayılan
image optimizer yüzeyi statik incelemeyle güvenli ilan edilemez. Bu nedenle
Next ve geçişli bağımlılıklar, yalnız kullanılmadığı düşünülen özelliklere
dayanarak istisna tanımlanmadan yükseltildi.

## Rapot'ta incelenen yollar

| Kanıt | Çıkarım ve sınır |
|---|---|
| [Dockerfile](../frontend/Dockerfile), [Next yapılandırması](../frontend/next.config.ts) | `node:20.20.2-alpine`, `output: standalone`, `node server.js`; self-hosted Node sunucusu. Dockerfile tek başına canlı imaj kimliği kanıtı değildir. Yerel geliştirme Windows'tadır. |
| [App Router kökü](../frontend/src/app/layout.tsx), `frontend/src/app/` | App Router ve RSC altyapısı var. Kaynakta `use server`, `use cache`, Next middleware/proxy dosyası, Pages Router, Edge runtime veya App Route Handler bulunmadı. Bunların yokluğu çerçevenin bütün dahili uçlarını yok saymak için kullanılmadı. |
| [Next yapılandırması](../frontend/next.config.ts) | `cacheComponents`, `i18n`, CSP nonce veya özel image ayarı yok. Önceki yerel derlemenin config'inde `cacheComponents=false`, `unoptimized=false`, `remotePatterns=[]` ve yerel `**` deseni vardı; bu kayıt yeni üretim imajının kabulü değildir. |
| `frontend/src/`, `frontend/public/` | `next/image`, `next/script`, `beforeInteractive`, kullanıcı CSS yükleme/derleme veya `dangerouslySetInnerHTML` bulunmadı. Raster public dosyalar `Rapot.png`, `hero-bg.png`; SVG ikonlar da var, AVIF bulunmadı. Image optimizer açıkça kapatılmış değil; yalnız import/dosya aramasıyla erişilemez denmez. |
| [API fetch katmanı](../frontend/src/lib/api/core.ts), [provider](../frontend/src/components/providers.tsx), [WebSocket URL](../frontend/src/lib/realtime/url.ts) | Veriler client React Query üzerinden alınır; ortak `fetchApi` varsayılan `cache: no-store` kullanır. Kaynakta `fetch(new Request(...), farklıInit)` veya Next sunucusunda önbelleklenen POST veri akışı bulunmadı. HTTP ve WS aynı API proxy yolunu kullanabilir. |
| [Next rewrites](../frontend/next.config.ts) | Hedef host `API_PROXY_TARGET` / `HEALTH_PROXY_TARGET` ortam ayarından sabittir; istekten yalnız `:path*` eklenir. Hostname içine istek capture'ı yerleştirilmiyor. |
| [ESLint](../frontend/eslint.config.mjs), [PostCSS](../frontend/postcss.config.mjs), [CI](../.github/workflows/ci.yml) | Lint/derleme bağımlılıkları proje kaynak ve config dosyalarını işler. Uygulamada ziyaretçi girdisini Babel, YAML, glob, Browserslist veya PostCSS'e taşıyan bir API bulunmadı. Dış katkı/dependency kaynaklarının araç zincirine girmesi ayrı güven sınırıdır. |

## Next.js: 25 doğrudan advisory

Aşağıdaki bütün satırlar başlangıç `next@16.2.1` üretim bağımlılık yolundadır.
"Düzeltme" sütunu **16.x hattındaki ilk düzeltilmiş sürümü** gösterir; seçilen
`16.3.5` bütün bu aralıkların dışındadır. "Koşul bulunmadı" kaynak incelemesidir,
çerçeve endpointlerine karşı saldırı testi sonucu değildir.

| Advisory / etki | Gerekli koşul ve Rapot değerlendirmesi | Düzeltme |
|---|---|---|
| [GHSA-q4gf-8mx6-v5v3](https://github.com/vercel/next.js/security/advisories/GHSA-q4gf-8mx6-v5v3) — RSC CPU tüketimi | App Router Server Function deserialize yolu. App Router var; açık Server Action tanımı bulunmadı. Üretilen dahili yollar için yalnız kaynak araması yeterli değil. | 16.2.3 |
| [GHSA-8h8q-6873-q5fj](https://github.com/vercel/next.js/security/advisories/GHSA-8h8q-6873-q5fj) — diğer RSC CPU tüketimi | Aynı Server Function önkoşulu; ayrı upstream RSC açığı. Açık action bulunmadı, çalışma zamanı istismarı doğrulanmadı. | 16.2.5 |
| [GHSA-267c-6grr-h53f](https://github.com/vercel/next.js/security/advisories/GHSA-267c-6grr-h53f) — segment-prefetch yetki atlama | App Router middleware/proxy tabanlı yetki kontrolü gerektirir. Rapot'ta Next middleware/proxy yok; API yetkisi FastAPI'dedir. | 16.2.5 |
| [GHSA-26hh-7cqf-hhc6](https://github.com/vercel/next.js/security/advisories/GHSA-26hh-7cqf-hhc6) — önceki düzeltmenin Turbopack eksiği | Turbopack + `middleware.ts`. Turbopack kullanılır; middleware bulunmadığından birleşik koşul bulunmadı. | 16.2.6 |
| [GHSA-3g8h-86w9-wvmq](https://github.com/vercel/next.js/security/advisories/GHSA-3g8h-86w9-wvmq) — redirect cache zehirleme | Middleware redirect + 3xx yanıtlarını uygun ayrım olmadan saklayan ortak cache. Middleware redirect yok. `/tradingview` sayfasındaki normal `redirect('/ai')` aynı mekanizma değildir. | 16.2.5 |
| [GHSA-ffhc-5mcf-pf4q](https://github.com/vercel/next.js/security/advisories/GHSA-ffhc-5mcf-pf4q) — CSP nonce XSS | İstek kaynaklı nonce ve ortak HTML cache gerekir. Kaynakta nonce üretimi yok; canlı proxy'nin tüm header/cache davranışı bu statik taramayla doğrulanmadı. | 16.2.5 |
| [GHSA-vfv6-92ff-j949](https://github.com/vercel/next.js/security/advisories/GHSA-vfv6-92ff-j949) — RSC cache anahtarı çakışması | Ortak cache'in RSC varyantlarını yetersiz ayırması gerekir. RSC var; mevcut cache/header zincirinin tüm koşulları doğrulanmadığından etki belirsiz. | 16.2.5 |
| [GHSA-gx5p-jg67-6x7h](https://github.com/vercel/next.js/security/advisories/GHSA-gx5p-jg67-6x7h) — script XSS | Güvenilmeyen içerikle `beforeInteractive` script gerekir. `next/script` ve bu kullanım bulunmadı. | 16.2.5 |
| [GHSA-mg66-mrh9-m8jx](https://github.com/vercel/next.js/security/advisories/GHSA-mg66-mrh9-m8jx) — bağlantı tüketimi | Cache Components / Partial Prerendering ve action POST yolu gerekir. Özellik açık değil; açık action bulunmadı. | 16.2.5 |
| [GHSA-h64f-5h5j-jqjh](https://github.com/vercel/next.js/security/advisories/GHSA-h64f-5h5j-jqjh) — optimizer bellek tüketimi | Self-hosted varsayılan image loader, izinli büyük yerel kaynak. Bu çerçeve/config önkoşulları var; zararlı/büyük girdinin erişimi sınanmadı. `next/image` importu olmaması koruma kanıtı değildir. | 16.2.5 |
| [GHSA-c4j6-fc7j-m34r](https://github.com/vercel/next.js/security/advisories/GHSA-c4j6-fc7j-m34r) — WebSocket SSRF | Self-hosted dahili Node sunucusuna ulaşan upgrade isteği gerekir. Rapot standalone ve WS proxy kullanır; yerel topolojiyle elenemeyen üretim önceliğidir. | 16.2.5 |
| [GHSA-492v-c6pp-mqqv](https://github.com/vercel/next.js/security/advisories/GHSA-492v-c6pp-mqqv) — dinamik rota yetki atlama | Dinamik rotayı yalnız middleware ile koruma gerekir. Next middleware veya bu yetki modeli bulunmadı. | 16.2.5 |
| [GHSA-wfc6-r584-vfw7](https://github.com/vercel/next.js/security/advisories/GHSA-wfc6-r584-vfw7) — RSC yanıt cache zehirleme | RSC + ortak cache'in yanıt türlerini yanlış ayırması gerekir. RSC var; canlı cache zinciri ve istismar doğrulanmadı. | 16.2.5 |
| [GHSA-36qx-fr4f-26g5](https://github.com/vercel/next.js/security/advisories/GHSA-36qx-fr4f-26g5) — i18n veri rotası yetki atlama | Pages Router + i18n + middleware yetkisi gerekir. Üçü de kaynakta bulunmadı. | 16.2.5 |
| [GHSA-6gpp-xcg3-4w24](https://github.com/vercel/next.js/security/advisories/GHSA-6gpp-xcg3-4w24) — tek locale yetki atlama | App Router + Turbopack + tek `i18n.locales` + middleware yetkisi gerekir. İlk ikisi var; locale ve middleware koşulları yok. | 16.2.11 |
| [GHSA-m99w-x7hq-7vfj](https://github.com/vercel/next.js/security/advisories/GHSA-m99w-x7hq-7vfj) — Server Action CPU tüketimi | En az bir Server Action gerekir. `use server` bulunmadı; bakımcı actions kullanmayan uygulamaları kapsam dışında tanımlar. | 16.2.11 |
| [GHSA-89xv-2m56-2m9x](https://github.com/vercel/next.js/security/advisories/GHSA-89xv-2m56-2m9x) — custom server Action SSRF | Action ve istemcinin host header kontrolü gerekir. Action/custom server yok; bakımcı 14.2+ standalone sunucunun origin'i sabitlediğini ayrıca belirtir. | 16.2.11 |
| [GHSA-68g3-v927-f742](https://github.com/vercel/next.js/security/advisories/GHSA-68g3-v927-f742) — POST yanıt cache karışması | Sunucu `fetch` çağrısında `Request` ile ikinci init'in farklı olması gerekir. Bu kullanım bulunmadı; ortak fetch katmanı no-store'dur. | 16.2.11 |
| [GHSA-4633-3j49-mh5q](https://github.com/vercel/next.js/security/advisories/GHSA-4633-3j49-mh5q) — UTF-8 dışı POST cache karışması | Sunucuda cache'lenen farklı gövdeler/UTF-8 dışı baytlar gerekir. Böyle bir akış bulunmadı; browser API çağrıları ve FastAPI proxy'si Next data-cache kullanımının kanıtı değildir. | 16.2.11 |
| [GHSA-4c39-4ccg-62r3](https://github.com/vercel/next.js/security/advisories/GHSA-4c39-4ccg-62r3) — Edge Action bellek tüketimi | App Router Server Action'ın Edge runtime kullanması gerekir. Action/Edge tanımı bulunmadı. | 16.2.11 |
| [GHSA-p9j2-gv94-2wf4](https://github.com/vercel/next.js/security/advisories/GHSA-p9j2-gv94-2wf4) — rewrite SSRF/open redirect | İstek capture'ından dış hedef hostname üretilmesi gerekir. Rapot'ta hedef host ortamdan sabit, yalnız path dinamik; bildirilen koşul bulunmadı. | 16.2.11 |
| [GHSA-q8wf-6r8g-63ch](https://github.com/vercel/next.js/security/advisories/GHSA-q8wf-6r8g-63ch) — SVG optimizer CPU tüketimi | Bakımcı açıklamasında uzak image kaynaklarına `remotePatterns` ile izin verilmesi gerekir. Kaynakta bu ayar yok; önceki yerel config'te dizi boş. Başka image açıklarına genellenmez. | 16.2.11 |
| [GHSA-955p-x3mx-jcvp](https://github.com/vercel/next.js/security/advisories/GHSA-955p-x3mx-jcvp) — dahili action kimliği ifşası | `use server` / `use cache` endpoint referansları gerekir. İkisi de kaynakta bulunmadı; istemciye çıkan action ID'leri yetki sırrı olarak görülmemelidir. | 16.2.11 |
| [GHSA-p293-qw3h-jr36](https://github.com/vercel/next.js/security/advisories/GHSA-p293-qw3h-jr36) — kritik Windows RCE | Windows dosya sistemi ve Cache Components kullanmayan App/Pages sunucusu. Kayıtlı Linux üretim OS koşulunu sağlamaz; Windows yerel sunucu eski sürümle açılırsa bu gerekçe geçerli değildir. | 16.3.3 |
| [GHSA-2xp9-vwfh-vxw4](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4) — kritik AVIF RCE | Image optimizer → sharp → libheif üzerinden AVIF işleme gerekir. Public AVIF veya upload yolu bulunmadı; optimizer etkinliği nedeniyle tam erişim reddi kanıtlanmadı. Next yaması AVIF optimizasyonunu kapatır; sharp da ayrıca yükseltildi. | 16.3.3 |

## Geçişli paketler: 21 benzersiz advisory

"Dev" başlangıç lock'unda yalnız araç zincirine bağlı; "prod + dev" her iki
bağımlılık yolunda demektir. Bu ayrım, ilgili modülün canlı standalone trace'e
dahil olduğunu veya ziyaretçi girdisini işlediğini kanıtlamaz. İlk düzeltilmiş
sürümler yalnız Rapot'un kullandığı major hatları için listelenir.

| Paket / kapsam | Advisory ve önkoşul | Rapot değerlendirmesi | İlk düzeltme |
|---|---|---|---|
| `@babel/core` / dev | [GHSA-4x5r-pxfx-6jf8](https://github.com/babel/babel/security/advisories/GHSA-4x5r-pxfx-6jf8): derlenen kötü niyetli kod, bilinen map yolu ve çıktıyı okuyabilme | React Hooks lint bağımlılığı. Ziyaretçi kodu derleyen API yok; CI'de derlenen dış katkı araç zinciri sınırındadır. | 7.29.6 |
| `@humanfs/node` / dev | [GHSA-p498-v437-472g](https://github.com/humanwhocodes/humanfs/security/advisories/GHSA-p498-v437-472g): saldırganın symlink yerleştirdiği ağacı `copy` / `copyAll` ile kopyalama | ESLint bağımlılığı; uygulamada çağrı yok. Düzeltme sürümü için aşağıdaki kaynak farkı kontrol edildi. | 0.16.8; aşağıdaki not |
| `baseline-browser-mapping` / prod + dev | [GHSA-w5vr-8v7q-w6rv](https://github.com/advisories/GHSA-w5vr-8v7q-w6rv): hatalı/çelişkili seçeneklerin `process.exit` çağırması; [bakımcı düzeltmesi](https://github.com/web-platform-dx/baseline-browser-mapping/commit/de733e2d8959559f7bb255d5927f3afcb6f31589) | Next ve Browserslist yolları. Ziyaretçi parametresinden mapping API'sine akış bulunmadı; production dependency etiketi HTTP erişimi kanıtı değildir. | 2.11.0 |
| `brace-expansion` / dev | [GHSA-3jxr-9vmj-r5cp](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-3jxr-9vmj-r5cp): güvenilmeyen glob'da aşırı CPU | ESLint/TypeScript ESTree minimatch yolları; uygulama pattern API'si yok. | 1.1.16 / 2.1.2 |
| `brace-expansion` / dev | [GHSA-mh99-v99m-4gvg](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-mh99-v99m-4gvg): genişlemenin uzunluğu sınırsız, OOM | Aynı araç zinciri; try/catch fatal OOM için güvence değildir. | 1.1.17 / 2.1.3 |
| `brace-expansion` / dev | [GHSA-rgw5-rvv9-x895](https://github.com/juliangruber/brace-expansion/security/advisories/GHSA-rgw5-rvv9-x895): ara diziler önceki sınırı aşar | Aynı araç zinciri; eski override değerleri güncellenmeden lock yenilemesi yetmez. | 1.1.18 / 2.1.4 |
| `browserslist` / dev | [GHSA-c83g-rgw3-j3cx](https://github.com/browserslist/browserslist/security/advisories/GHSA-c83g-rgw3-j3cx): uzun yaşayan süreçte çok sayıda farklı dış sorgu ve sınırsız cache | Babel compilation targets yolu. Ziyaretçi kontrollü sorgu/servis bulunmadı. | 4.28.7 |
| `browserslist` / dev | [GHSA-73wf-gq98-2v4g](https://github.com/browserslist/browserslist/security/advisories/GHSA-73wf-gq98-2v4g): kötü niyetli stats dosyası/options ile crash/prototype yazımı | Araç zinciri dış katkı/config girdisi önemlidir; yalnız varsayılan query seçmek dosya keşfini engellemez. | 4.28.7 |
| `js-yaml` / dev | [GHSA-h67p-54hq-rp68](https://github.com/nodeca/js-yaml/security/advisories/GHSA-h67p-54hq-rp68): tekrarlanan alias merge ile CPU | ESLint eslintrc yolu; uygulamada ziyaretçi YAML parsing endpoint'i yok. | 4.2.0 |
| `js-yaml` / dev | [GHSA-52cp-r559-cp3m](https://github.com/nodeca/js-yaml/security/advisories/GHSA-52cp-r559-cp3m): merge zincirinde karesel CPU | Aynı araç zinciri; merge bütçesi sonraki yamalarla birlikte değerlendirilir. | 4.3.0 |
| `js-yaml` / dev | [GHSA-5p4m-2wfm-xmqj](https://github.com/nodeca/js-yaml/security/advisories/GHSA-5p4m-2wfm-xmqj): varsayılan `!!omap` anahtar kontrolünde CPU | Aynı araç zinciri; özel schema gerekmiyor. | 4.3.1 |
| `js-yaml` / dev | [GHSA-2883-xcg3-v3hh](https://github.com/nodeca/js-yaml/security/advisories/GHSA-2883-xcg3-v3hh): boş merge kaynakları bütçeye sayılmıyor | Aynı araç zinciri; 4.3.0 tek başına bütün merge açıklarını kapatmaz. | 4.3.2 |
| `nanoid` / prod + dev | [GHSA-28wg-ghj8-5hjv](https://github.com/advisories/GHSA-28wg-ghj8-5hjv): non-secure generator'a negatif size; [3.x release](https://github.com/ai/nanoid/releases/tag/3.3.16) | PostCSS bağımlılığı; uygulamada nanoid veya dış size aktarımı bulunmadı. | 3.3.16 |
| `nanoid` / prod + dev | [GHSA-2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8): custom generator'a sıfır size; [3.x release](https://github.com/ai/nanoid/releases/tag/3.3.18) | Aynı yol; generator/size API'si bulunmadı. | 3.3.18 |
| `nanoid` / prod + dev | [GHSA-xwg4-73v4-xw9w](https://github.com/ai/nanoid/security/advisories/GHSA-xwg4-73v4-xw9w): aşırı dış size ile rastgelelik havuzunu bozma | Ana JWT/token üretimi bu pakette değildir; kullanıcı kontrollü size yolu bulunmadı. | 3.3.12 |
| `postcss` / prod + dev | [GHSA-qx2v-qp2m-jg93](https://github.com/postcss/postcss/security/advisories/GHSA-qx2v-qp2m-jg93): güvenilmeyen CSS çıktısını HTML style içine gömme | Next ve Tailwind build yolları; kullanıcı CSS dönüştürme/gömme akışı bulunmadı. | 8.5.10 |
| `postcss` / prod + dev | [GHSA-6g55-p6wh-862q](https://github.com/postcss/postcss/security/advisories/GHSA-6g55-p6wh-862q): CSS sourceMappingURL üzerinden dosya okuma ve çıktıda ifşa | Güvenilmeyen CSS veya bağımlılık derleme girdisi gerekir; uygulama endpoint'i bulunmadı. | 8.5.12 |
| `postcss` / prod + dev | [GHSA-r28c-9q8g-f849](https://github.com/postcss/postcss/security/advisories/GHSA-r28c-9q8g-f849): kaynak map path traversal | Aynı girdi sınırı; yalnız `.map` uzantısı kontrolü yeterli değildir. | 8.5.18 |
| `postcss` / prod + dev | [GHSA-fxqj-rqcc-2cmp](https://github.com/postcss/postcss/security/advisories/GHSA-fxqj-rqcc-2cmp): `from` yokken map okuma kalıntısı | Aynı girdi sınırı; 8.5.22 son kalıntıyı kapatmaz. | 8.5.23 |
| `sharp` / prod, optional | [GHSA-f88m-g3jw-g9cj](https://github.com/lovell/sharp/security/advisories/GHSA-f88m-g3jw-g9cj): libvips'te güvenilmeyen image girdisi | Next optimizer yolu; uygulamanın doğrudan import etmemesi bu native parser'ın erişilemediğini kanıtlamaz. | 0.35.0 |
| `sharp` / prod, optional | [GHSA-rgj7-g3m4-5g8c](https://github.com/lovell/sharp/security/advisories/GHSA-rgj7-g3m4-5g8c): libheif/AVIF, bazı koşullarda RCE | Bakımcı özel RCE koşulunu glibc Linux ile sınırlar; Rapot Alpine/musl kaydı bütün decoder bellek risklerini yok saymaz. Girdi erişimi sınanmadı; prebuilt bağımlılık yükseltildi. | 0.35.4 |

**humanfs kaynak farkı:** Bakımcı advisory sayfasındaki `Patched versions` alanı
`None`, GitHub Advisory Database alanı ise `0.16.8` gösteriyordu. Yalnız bu
metadata'ya dayanılmadı: [bakımcı düzeltmesi
22bbaa4](https://github.com/humanwhocodes/humanfs/commit/22bbaa4487a3e6c1197ca619840de4615d0c3404)
ile yeni kurulumdaki `@humanfs/node/src/node-hfs.js` karşılaştırıldı.
`copy()` içinde `lstat`/`isSymbolicLink`, `copyAll()` içinde `entry.isSymlink`
dalları mevcut; kopyalama linki yeniden oluşturuyor. Bu statik düzeltme
doğrulamasıdır, dosya kopyalama veya exploit testi yapılmadı.

## Seçilen lock değişikliği

| Paket | Başlangıç | Yeni lock |
|---|---|---|
| next / eslint-config-next | 16.2.1 | 16.3.5 |
| @babel/core | 7.28.6 | 7.29.7 |
| @humanfs/node | 0.16.7 | 0.16.8 |
| baseline-browser-mapping | 2.10.10 | 2.11.23 |
| brace-expansion | 1.1.13 / 2.0.3 | 1.1.18 / 2.1.4 |
| browserslist | 4.28.1 | 4.28.9 |
| js-yaml | 4.1.1 | 4.3.2 |
| minimatch | 3.1.5 / 9.0.9 | Aynı; brace-expansion yolu düzeltildi |
| nanoid | 3.3.11 | 3.3.19 |
| postcss | 8.4.31 / 8.5.6 | 8.5.23; iki yol aynı düğümde |
| sharp | 0.34.5 | 0.35.4 |

Next ile `eslint-config-next` aynı sürüme sabitlendi. Brace-expansion için iki
dar minimatch override'ı yeni güvenli sürümlere taşındı. Ardından yalnız kalan
beş geçişli paket (`@babel/core`, `@humanfs/node`, `baseline-browser-mapping`,
`browserslist`, `js-yaml`) lock üzerinde yenilendi. Diğer doğrudan bağımlılık
sürümleri korunuyor; `npm audit fix --force` kullanılmadı. Lock farkında kök
dahil 506 kayıt ve 76 değişiklik kaydı vardır; bu sayı 76 güvenlik açığı demek
değildir.

`@img/sharp-libvips-*` paketinin `1.3.3` sürümü npm dağıtım paketinin sürümüdür;
native **libvips** kitaplığı sürümü değildir. Bakımcı sharp 0.35.4 prebuilt
dağıtımında **libheif 1.23.2** bildirir. Yeni yerel Windows kurulumunun
`sharp.versions` çıktısı sharp **0.35.4**, heif **1.23.2**, vips **8.18.6**
gösterdi; bu Windows native binary doğrulamasıdır. Linux imajının native
kitaplıkları üretim kabulünde ayrıca doğrulanır.

## Doğrulama ve kapanış sınırı

Lock üretimi sırasında npm sonucu **11 → 5 → 0** oldu. Yeni lock sürümleri bu
belge için doğrudan okundu. Node 20.20.2 / npm 10.9.9 ile yerel `npm ci`,
**113 frontend testi** (önceki 105 + audit denetimi için sekiz yeni test), lint,
typecheck, Next 16.3.5 build ve standalone HTTP/auth proxy/chart RSC/bot proxy/WS
kabulü geçti. Yeniden audit, kök hariç **505 lock paket düğümünü** kapsadı ve
**0 bulgu** bildirdi; lock SHA256
`508e4358715d32a25949f6a9fc1484ade3169d3cc47b4b853383f68bb29be42f`.
CI ve üretim kabulünün sürüm kimliği/sonuçları [devam planında](RAPOT_DEVAM_PLANI.md)
ayrı kaydedilir. Yeşil build tek başına advisory kapanışı değildir; sıfır npm
bulgusu da gelecekteki açıkların yokluğu değildir.

[Audit aracı](../frontend/scripts/audit-dependencies.mjs) prod/dev/optional/peer
kapsamlarını açıkça dahil eder ve `--offline=false` ile çevrimdışı tarama
atlamasını önler. Bulgu, eksik kapsam, bozuk JSON, araç/ağ hatası,
timeout, çelişkili çıkış kodu veya koşum sırasında değişen lock başarısızlık
sayılır. Ham rapor, lock hash'i, paket listesi ve özet saklanır. CI frontend job'u
bu denetimi çalıştırır ve raporu artifact olarak yükler; Python güvenlik
taramasındaki report-only politikadan ayrıdır.

**Kalan yerel araç uyarısı:** `npm ls --all`, `@img/sharp-wasm32` ve
`@emnapi/runtime` için `extraneous` bildiriyor. İki paket platforma bağlı
optional yolların ortak çocuklarıdır; version/resolved/integrity değerleri
proje lock'u ve npm'in hidden lock'uyla eşleşir, ikisi de 505 düğümlük audit
kapsamındadır. Bu durum npm Arborist'in [bakımcı PR 9221'de açıklanan
optional ortak bağımlılık sorunuyla](https://github.com/npm/cli/pull/9221)
örtüşür. Native Windows sharp yüklemesi ve build geçti; uyarı saklanır.
Bu görevde npm 10.9.9 değiştirilmedi veya düğümler elle silinmedi.

Üretimde Next çalıştığı için paket/lock güncellemesi **yeni frontend imajı ve
üretim kabulü** gerektirir. Kaynak dosyalarının sunucuya aktarılması bu koşulu
karşılamaz. Sabit 528 MiB disk rezervi, imaj katmanlarının ek alanı, taze yedek ve
çalışan servisler ölçülmeden deploy tamamlandı denmez. Bu inceleme PostgreSQL,
SQLite, backend imajı, borsa emirleri veya ücretli kapasite değişikliği gerektirmez.

Yerel kanıtlar Git dışında `runtime-data/` altında tutulur:

- Başlangıç audit: `p31-execution-npm-audit.json`, SHA256
  `cd1fc2e7b87a0f1816cbc512f9f5138ab9cbc1f7f57e7391e455b829f867e0ba`.
- Başlangıç paket yolları: `p31-execution-npm-triage.json`.
- Salt okunur kaynak notları: `p1g2-readonly-source-preflight.json`.
- 46 GitHub advisory yanıtı ve bakımcı kaynakları:
  `p1g2-advisory-source-review.json`.
- Seçilen lock farkı: `p1g2-lock-delta.json`.
- Yeni tam audit/lock kapsamı: `p1g2-npm-security/` içindeki `npm-audit.json`,
  `manifest.json`, `summary.json`; npm ağaç uyarısı: `p1g2-npm-tree.json`.

Bu belgede mevcut uygulamaya yönelik exploit çalıştırılmadı; dış ağ okumaları
paket registry ve açık bakımcı güvenlik kaynaklarıyla sınırlıdır. Paket sürümü,
statik özellik koşulu ve gerçek üretim kabulü ayrı kanıtlar olarak tutulur.
