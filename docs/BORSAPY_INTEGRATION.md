# Borsapy araştırma merkezi

4 Ekim 2026. Kullanıcı, mevcut TradingView Premium ve BIST gerçek zamanlı veri
paketiyle kişisel Rapot sitesinde borsapy README'sindeki özellik ailelerini
istedi. Canlı piyasa/hesap kabulü piyasa açıkken yapılmak üzere ertelendi.

Kaynak: borsapy 0.11.0,
[`a9e41ae398fc2d25b35f864a5c7028d5f98862c3`](https://github.com/saidsurucu/borsapy/tree/a9e41ae398fc2d25b35f864a5c7028d5f98862c3).
`borsapy[twitter]==0.11.0` ve geliştirme/CI bağımlılıkları kilitlidir. Kurulan
paketin stream, ticker, technical, TradingView provider ve fund dosyaları,
satır sonları normalleştirilince incelenen Git kaynağıyla aynıdır.

## Ekran ve kapsam

`/research` yalnız yönetici oturumuyla kullanılır. Katalogdaki işlem; etiketli
form, kaynak, alım zamanı, uyarı, tablo, CSV ve uygun işlemlerde mum grafiği üretir.
Yalnız açıkça tanımlı işlemler ve sınırlı girdiler kabul edilir; Python konsolu
veya sağlayıcının bütün metotlarına serbest erişim değildir.

| README'deki özellik ailesi | Web karşılığı |
|---|---|
| TradingViewStream | Hesap bağlantısı, fiyat/mum akışı, uzak Pine gösterge kimliği |
| Backtest Engine | Sabit stratejili deneysel borsapy backtest |
| Replay Mode | Mum grafiğinde oynat/duraklat/adım/hız |
| Search | Piyasa türüne göre sembol arama |
| TA Signals | TradingView teknik alış/satış/nötr özeti |
| Heikin Ashi | Standart mumlardan sentetik grafik |
| ETF Holders | Hissede ETF sahipliği tablosu |
| Portfolio | Çoklu varlıklarla sanal portföy ve risk analizi |
| FX | Döviz/emtia, geçmiş ve banka kurları |
| Crypto | BtcTurk çiftleri ve verileri; Binance emir sistemi ayrıdır |
| Fund | TEFAS bilgi/geçmiş/dağılım/tarama/karşılaştırma/stopaj |
| Inflation | Enflasyon serileri ve hesaplayıcı |
| EVDS | Katalog, arama ve anahtarlı zaman serileri |
| VIOP | Vadeli/opsiyon verileri, kontrat arama ve yetkiye bağlı akış |
| Bond | Devlet tahvili faizleri ve risksiz oran |
| TCMB | Politika/gecelik/LON faizleri ve geçmiş |
| Eurobond | Devlet eurobondları |
| EconomicCalendar | Ülke/önem filtreli ekonomik takvim |
| Screener | Temel tarama, ölçütler ve teknik koşullar |
| Teknik Analiz | OHLCV üzerinde borsapy yerel göstergeleri |
| Twitter/X | Ayrı X oturumu tanımlandıktan sonra sınırlı arama |
| KAP | Bildirimler ve şirket takvimi |

Şirket finansalları ve temettü/sermaye işlemleri de sunulur. Her aile için web
yüzeyi bulunması, bütün sağlayıcıların canlı kabul edildiği anlamına gelmez.

Yerel çevrimdışı kabul: 1.177 Python testi, ayrıca 27 dağıtım doğrulayıcı testi;
222 frontend testi, lint/typecheck, build ve standalone proxy kontrolü geçti.
Sentetik tarayıcı oturumunda katalog/formlar, kaydetme, replay, akış kontrolleri,
özel grafik kaynağı, bağlantı sekmesi ve 320 px görünüm sınandı. Sağlayıcı,
TradingView oturumu, gerçek fiyat gecikmesi veya bildirim teslimi sınanmadı.

`/chart` BIST kaynağı olarak Borsapy/TradingView seçimini sunar. Özel
`/borsapy/candles/{symbol}` ve `/borsapy/stream` kullanılır. Göstergeler mevcut
TypeScript hesaplayıcısıyla çalışır. İş Yatırım/Yahoo seçimi korunur. Koşulsuz
“Canlı” etiketi kaldırılır. Araştırmadaki borsapy göstergeleriyle mevcut
COMBO/HUNTER motorlarının eşdeğerliği iddia edilmez.

## Kalıcılık ve erişim

- Araştırma ve sanal portföy girdileri ana SQLite `research_workspaces`
  tablosunda kullanıcıya bağlı saklanır. Kullanıcı başına en fazla 100 kayıt;
  sonuçlar ve kimlikler bu tabloda tutulmaz. `init_db()` tabloyu ekler.
- TradingView session/session_sign, isteğe bağlı EVDS ve X anahtarları yalnız
  yönetici POST'uyla alınır; yanıtta, tarayıcı depolamasında veya Git'te tutulmaz.
- Kimlikler, mevcut en az 32 karakter JWT anahtarından HKDF türetilmiş anahtar
  ve Fernet ile şifrelenir. Varsayılan ana DB yanında `.borsapy/credentials.enc`;
  `BORSAPY_CREDENTIALS_PATH` ile değişebilir. Linux dizin/dosya izinleri 0700/0600.
  JWT değişirse bağlantı yeniden tanımlanır. Dosya kalıcı özel volume'da olmalı.
- API'de kimlik değişince ayrı bot süreci sonraki sağlayıcı çağrısında dosya
  revizyonunu yeniden okur; aktif akışlar da en geç kiralama kontrolünde yenilenir.
  Süresi dolan TradingView oturumu, bağımsız TEFAS/EVDS gibi sorguları engellemez;
  okunamayan şifreli dosyada bütün kimlikli yollar durur.
- `.borsapy/` Git ve Docker build context'inden çıkarılır. Gizli yedekler genel
  rapora veya Git'e alınmaz. Windows'ta ciphertext JWT anahtarından ayrı tutulur.
- `/borsapy/catalog`, `/query`, `/saved`, `/connection`, `/stream`, `/candles`
  yönetici ister. Kaynaklar anonim endpointlere otomatik açılmaz. Sağlayıcı
  oturumu ile Rapot JWT oturumu ayrıdır.

## Akış ve hesaplayıcı

Upstream'in çoklu chart eşlemesindeki sabit seri kimliği nedeniyle her
sembol/periyot/gösterge ayrı bağlantı kullanır. `BORSAPY_MAX_STREAMS` varsayılan 3,
en fazla 5; `BORSAPY_STREAM_IDLE_SECONDS` varsayılan 120. Kullanılmayan grafik
aboneliği kapanır; bu kiralar sunucu alarm döngüsünü durdurmaz. Mum tamponu sınırlı.
Sekmeler ayrı abone kimliği kullanır; bir sekmeyi kapatmak diğer sekmenin ortak
akışını kapatmaz. VİOP veri hakkı ayrıca doğrulanır; BIST paketi bunu kanıtlamaz.

Kimlikli istek token yokken anonim veriye düşmez. Oturumun süresiz geçerli olması
veya bütün mesajların eksiksiz teslimi garanti edilmez. Sağlayıcının işlem zamanı
ve yerel alınma zamanı ayrıdır. `realtime_verified` canlı kabulden önce false;
açık bağlantı tek başına anlık veri kanıtı değildir.

Pine alanı TradingView üzerinde erişilebilen gösterge kimliğidir; serbest Pine
veya Python kaynak metni çalıştırmaz. Deneysel borsapy backtest aynı mum kapanışı
sözleşmesine sahiptir. Rapot'un önceki kapalı mum → sonraki gerçek Open motoru
değişmez. Araştırma işlemleri borsaya emir veya kullanıcı adına alarm göndermez.

## Scanner ve sunucu alarmları

`BORSAPY_USE_FOR_BIST=true` açık seçimiyle `get_bist_data` ve günlük BIST alarm
sağlayıcısı kimlikli gateway'i kullanabilir. Varsayılan false; canlı kabulden
önce çalışan taramalar kendiliğinden dönüştürülmez. Seçildiğinde başarısızlıkta
başka sağlayıcıya sessiz fallback olmaz. Günlük İstanbul işlem tarihi mevcut
hesaplamaya uyarlanır; `open_quality=provider`, `adjustment=splits` taşınır.
Scanner'ın alım tazeliği metadata'sı korunur; alım zamanı işlem zamanı değildir.
Genel mum endpointi açıkça eski kaynağı seçer; borsapy verisi ortak genel fiyat
önbelleğine yazılmaz. Özel grafik geçmişi kimlikli ayrı endpointten alınır.

BIST sunucu alarmlarının günlük kısıtı korunur. Gün içi grafik bulunması BIST
seans/tatil/yarım gün ve mum kapanış takviminin doğrulandığı anlamına gelmez.
Mevcut alarm kalıcılığı, sahiplik, Telegram sınırları ve DRY_RUN/emir ayarları korunur.

## Ertelenen canlı kabul

1. Kullanıcının mevcut TradingView oturumunun kendi sunucusundan doğrulanması.
2. İşlem gören hisselerde fiyat, sağlayıcı işlem zamanı, 1m/5m/günlük mumların
   TradingView ekranıyla karşılaştırılması.
3. Çoklu bağlantı ayrımı, bağlantı kaybı/yenileme ve oturum sona ermesi.
4. Tarihsel kapsam, bölünme/bedelli/temettü düzeltmeleri ve geçmiş revizyonları.
5. EVDS/X bağlantıları; ekonomik takvim saat dilimi ve KAP bildirim kapsamı.
   Bilanço beklenen son tarihi kesin yayın anı değildir.

Üretim öncesinde yeni bağımlılıkların disk bütçesi ölçülür; mevcut $6/ay plan ve
528 MiB rezerv korunur. Yerel doğrulama ve yayın sonuçları devam planında tutulur.
