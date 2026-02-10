# RAPOT DASHBOARD — UI/UX TASARIM DİREKTİFİ
## Codex Geliştirme Kılavuzu v1.0

---

## 1. PROJE KİMLİĞİ

**Proje:** Rapot — Otonom Finansal Piyasa Analiz ve Takip Platformu
**Hedef Kullanıcı:** Kripto ve borsa yatırımcıları, teknik analistler
**Platform:** Web (desktop-first, responsive secondary)
**Tech Stack:** Next.js 14, TanStack Query, Zustand, TailwindCSS
**Referans Kalite Seviyesi:** Bloomberg Terminal, TradingView Pro, Linear.app

---

## 2. TASARIM FELSEFESİ

### 2.1 Temel İlke
Bu bir "dashboard uygulaması" değil, bir **bilgi terminali**dir. Her piksel bilgi taşımalı, dekoratif eleman SIFIR olmalıdır. Estetik, bilginin kendisinden doğmalıdır — bilginin üzerine yapıştırılmış süslemelerden değil.

### 2.2 Karakter Tanımı
- **Sessiz güven:** Kendini kanıtlamaya çalışan parlak renkler yok. Sakin, kontrollü, profesyonel.
- **Veri odaklı:** İlk bakışta göze çarpan şey dekorasyon değil, veri olmalı.
- **Terminal estetiği:** Bloomberg ve Reuters terminallerinin bilgi yoğunluğunu modern tipografi ile birleştir.
- **Kasıtlı sadelik:** Her eleman bir sebepten var. Sebebi yoksa kaldır.

### 2.3 Kaçınılması Gereken "AI Yapımı" Kalıplar
Aşağıdaki kalıpları ASLA kullanma — bunlar projeyi anında "AI tarafından üretilmiş" gösterir:

- Mor-mavi gradient arka planlar
- Neon glow efektleri, box-shadow glow
- Her kartta farklı renkli dekoratif ikon
- Eşit boyutlu 3-4 kart sırası layout
- Aşırı yuvarlak köşeler (border-radius > 8px)
- "Welcome back, User!" tarzı generic başlıklar
- Sparkle (✨) emoji ve "AI-powered" badge'leri
- Gradient butonlar
- Her yerde aynı card component tekrarı
- Animasyonlu sayaç efektleri (sayı yukarı sayan counter'lar)
- Kalın renkli sidebar ikonları
- "Komuta Merkezi", "Kontrol Paneli" gibi abartılı isimlendirmeler

---

## 3. RENK SİSTEMİ

### 3.1 Zemin Katmanları (Background Layers)
Saf siyah (#000000) KULLANMA. Hafif mavi-siyah tonlar derinlik hissi verir:

```css
--bg-base:      #08080C;    /* Ana arka plan */
--bg-surface:   #0C0C12;    /* Sidebar, panel arka planları */
--bg-raised:    #111118;    /* Hover state, aktif panel */
--bg-overlay:   #16161E;    /* Modal, dropdown arka planları */
```

### 3.2 Border ve Ayırıcılar
Solid renkler yerine alpha değerleri kullan — böylece farklı arka planlarda tutarlı görünür:

```css
--border-subtle:   rgba(255, 255, 255, 0.04);   /* Grid çizgileri, bölüm ayırıcılar */
--border-default:  rgba(255, 255, 255, 0.06);   /* Kart kenarları, input border */
--border-strong:   rgba(255, 255, 255, 0.10);   /* Aktif elementler, focus state */
```

### 3.3 Metin Hiyerarşisi
4 kademeli metin opaklığı yeterlidir, daha fazlası kafa karıştırır:

```css
--text-primary:    #E8E8EC;                      /* Başlıklar, önemli veriler */
--text-secondary:  rgba(255, 255, 255, 0.50);    /* Açıklamalar, etiketler */
--text-tertiary:   rgba(255, 255, 255, 0.30);    /* Placeholder, ipucu metinleri */
--text-ghost:      rgba(255, 255, 255, 0.15);    /* Dekoratif, grid numaraları */
```

### 3.4 Piyasa Renkleri (ve SADECE Bunlar)
Accent renk olarak YALNIZCA piyasa standart renklerini kullan. Ek dekoratif renk YASAK:

```css
--positive:    #22C55E;    /* Yeşil — yükseliş, kâr, alım sinyali */
--negative:    #EF4444;    /* Kırmızı — düşüş, zarar, satım sinyali */
--neutral:     #F59E0B;    /* Amber — nötr, uyarı, beklemede (TUTUMLU KULLAN) */
```

Renk kullanım kuralları:
- Yeşil ve kırmızı YALNIZCA veri anlamı taşıdığında kullanılır (fiyat değişimi, PNL, sinyal)
- Navigasyon, buton, başlık gibi UI elementlerinde renk KULLANMA — gri tonlarıyla çöz
- Amber sadece uyarı ve dikkat gerektiren durumlar için ayrılmıştır
- Renkler hiçbir zaman arka plan olarak kullanılmaz, yalnızca metin ve ince göstergeler için

### 3.5 Veri Görselleştirme Renkleri
Grafiklerde ek renklere ihtiyaç duyarsan:

```css
--chart-1:    #3B82F6;    /* Mavi — ana gösterge, fiyat çizgisi */
--chart-2:    #8B5CF6;    /* Mor — ikincil gösterge (RSI, MACD) */
--chart-3:    #06B6D4;    /* Cyan — hacim, üçüncü gösterge */
```

Bu 3 renk YALNIZCA grafik içi göstergeler için kullanılır, UI elementlerinde kullanılmaz.

---

## 4. TİPOGRAFİ

### 4.1 Font Seçimi
İki font ailesi yeterlidir. Üçüncü font EKLEME:

```css
--font-sans:   'DM Sans', system-ui, sans-serif;     /* UI metinleri */
--font-mono:   'DM Mono', 'JetBrains Mono', monospace; /* Sayısal veriler */
```

Alternatif kombinasyonlar (biri seçilecek, karıştırılmayacak):
- Seçenek A: DM Sans + DM Mono (önerilen — tutarlı aile)
- Seçenek B: Satoshi + JetBrains Mono
- Seçenek C: Outfit + IBM Plex Mono

Inter, Roboto, Arial, system-ui KULLANMA — bunlar generic AI görünümü yaratır.

### 4.2 Font Ölçekleri
Finansal platformlarda veri yoğunluğu kritiktir. Büyük fontlar yer israf eder:

```css
--text-xs:     10px;    /* Etiketler, zaman damgaları, badge'ler */
--text-sm:     11px;    /* Tablo satırları, sinyal detayları */
--text-base:   13px;    /* Genel UI metni (varsayılan 16px DEĞİL) */
--text-md:     14px;    /* Alt başlıklar, sembol isimleri */
--text-lg:     18px;    /* Fiyat rakamları, ana veri */
--text-xl:     24px;    /* Hero rakamlar (ekranda en fazla 1-2 tane) */
```

### 4.3 Sayısal Gösterim Kuralları
Finansal verilerin okunabilirliği için:

```css
font-feature-settings: 'tnum' 1;  /* Tabular numbers — rakamlar alt alta hizalanır */
letter-spacing: -0.01em;           /* Sayılarda hafif sıkıştırma */
```

- Fiyatlar DAIMA monospace fontta gösterilir
- Yüzdelik değişimler DAIMA işaret ile gösterilir: +2.34%, -1.56%
- Büyük sayılarda binlik ayracı kullanılır: 69,003.35
- Sıfır değerler "0.00" yerine "—" (em dash) ile gösterilir (veri yoksa)

### 4.4 Harf Aralığı (Letter Spacing)

```css
/* Normal metin */
letter-spacing: -0.01em;

/* Büyük başlıklar */
letter-spacing: -0.02em;

/* Uppercase etiketler (SEMBOL, WATCHLIST gibi) */
letter-spacing: 0.06em;
font-weight: 600;
font-size: 10px;
text-transform: uppercase;
```

---

## 5. LAYOUT SİSTEMİ

### 5.1 Genel Yapı
Dashboard SİMETRİK KART GRIDI olarak tasarlanmayacak. Asimetrik, bilgi hiyerarşisi olan bir yapı kullan:

```
┌──────────────────────────────────────────────────────┐
│ [NAV 56px] │ [TOP BAR 40px - zaman, durum, bağlantı]│
│            ├──────────────────────────────────────────│
│            │ [STAT RIBBON 64px - PNL | WinRate | vs] │
│            ├─────────────────────┬────────────────────│
│            │                     │  WATCHLIST          │
│            │   ANA GRAFİK       │  (ticker listesi)   │
│            │   (ekranın %70'i)  │                      │
│            │                     ├────────────────────│
│            │                     │  SİNYALLER          │
│            │                     │  (akış listesi)     │
│            ├─────────────────────┴────────────────────│
│            │ [ALT PANEL - opsiyonel: order book, log] │
└──────────────────────────────────────────────────────┘
```

### 5.2 Boyut Oranları
- Sol navigasyon: sabit 56px genişlik
- Sağ sidebar: sabit 280px genişlik
- Ana içerik: kalan alan (fluid)
- Üst bar: sabit 40px yükseklik
- Stat ribbon: sabit 64-72px yükseklik

### 5.3 Spacing Sistemi
Tailwind varsayılanları yerine özel scale:

```css
--space-1:   4px;     /* İç element boşluğu */
--space-2:   8px;     /* Element arası minimum boşluk */
--space-3:   12px;    /* Grup içi boşluk */
--space-4:   16px;    /* Bölüm içi boşluk, padding */
--space-5:   20px;    /* Ana padding */
--space-6:   24px;    /* Bölümler arası boşluk */
--space-8:   32px;    /* Büyük ayrımlar */
```

### 5.4 Grid Kuralları
- Ana grafik her zaman en büyük alanı kaplar — bu platformun kalbi
- Eşit boyutlu kart sırası ASLA kullanma
- Stat değerleri büyük kartlar yerine compact ribbon formatında göster
- Sidebar, ana içeriği ezmemeli — sabit genişlik
- Panel yükseklikleri içeriğe göre değişebilir (sabit kart yüksekliği yok)

---

## 6. KOMPONENT TASARIM KURALLARI

### 6.1 Genel Kurallar
```css
border-radius: 2px;     /* MAKSIMUM. Çoğu yerde 0px. */
                         /* 8px, 12px, 16px gibi değerler YASAK */

box-shadow: none;        /* Box-shadow KULLANMA */
                         /* Glow efekti KULLANMA */
                         /* Derinlik, border ile sağlanır */

outline: none;
border: 1px solid var(--border-subtle);  /* Ayırıcılar border ile */
```

### 6.2 Stat Göstergeleri (PNL, Win Rate, vb.)
Büyük kartlar yerine compact ribbon:

```
YAPMA:                              YAP:
┌──────────┐ ┌──────────┐          ──────────────────────────────
│ 🔼 ICON  │ │ 🎯 ICON  │          PNL          WIN RATE    AÇIK POZ.
│ TOPLAM   │ │ WIN RATE  │          ₺0,00        —           0
│ PNL      │ │           │          ──────────────────────────────
│ ₺0,00    │ │ 0.0%      │
│ +0.00%   │ │           │
└──────────┘ └──────────┘
```

Kurallar:
- İkon KULLANMA. Veri kendini anlatır.
- Etiket küçük uppercase (10px, 0.06em letter-spacing)
- Değer büyük monospace (18px)
- Hücre ayırıcısı: dikey border (1px solid var(--border-subtle))
- Arka plan rengi: şeffaf (kart arka planı YOK)
- Her stat eşit genişlik almak zorunda DEĞİL

### 6.3 Watchlist (Ticker Listesi)

```
YAP:
─────────────────────────────
 WATCHLIST
─────────────────────────────
│ BTC/USDT    ▁▂▃▅▃  69,003 │  ← aktif satır: sol kenarda 2px beyaz border
│ ETH/USDT    ▃▂▁▂▁   2,011 │     + hafif arka plan tonu
│ SOL/USDT    ▅▃▂▁▂      84 │
│ BNB/USDT    ▂▃▄▃▂     618 │
─────────────────────────────
```

Kurallar:
- Satır yüksekliği: 36-40px (sıkı ama okunabilir)
- Aktif sembol: `border-left: 2px solid var(--text-primary)` + `background: var(--bg-raised)`
- Hover: sadece background değişimi (subtle)
- Mini sparkline chart: 48x20px, çizgi kalınlığı 1.5px
- Fiyat sağa hizalı, monospace
- Yüzde değişimi fiyatın altında, küçük font

### 6.4 Sinyal Akışı

```
YAP:
─────────────────────────────
 SİNYALLER
─────────────────────────────
 SELL  BTC  $69,180    21:34
 RSI aşırı alım + MACD
 kesişim             %78
─────────────────────────────
 BUY   ETH  $2,008    21:12
 Destek seviyesi testi %65
─────────────────────────────
```

Kurallar:
- Tag stili: `padding: 2px 6px`, `border-radius: 2px`, `font-size: 10px`, `font-weight: 600`
- BUY tag: `background: rgba(34,197,94,0.12)`, `color: #22c55e`
- SELL tag: `background: rgba(239,68,68,0.12)`, `color: #ef4444`
- INFO tag: `background: rgba(255,255,255,0.06)`, `color: rgba(255,255,255,0.5)`
- Güven yüzdesi sağ alt köşede, ghost renkte
- Satırlar arası ayırıcı: `border-bottom: 1px solid rgba(255,255,255,0.02)`

### 6.5 Grafik Alanı

Grafik header:
```
BTC/USDT    $69,003.35  -2.24%    [1D] [4S] [1S] [1H] [15M] [5M]
A 70,580.26  Y 72,271.41  D 67,300.00  K 69,002.02
```

Kurallar:
- Timeframe selector: pill butonlar, `border-radius: 2px`, aktif olan `background: rgba(255,255,255,0.10)`
- OHLC değerleri küçük boyutta, grafik header'ın altında tek satırda
- Grafik grid çizgileri: `rgba(255,255,255,0.04)` — çok hafif, görünür ama baskın değil
- Fiyat ekseni (sağ) monospace, `rgba(255,255,255,0.25)`
- Son fiyat göstergesi: kırmızı/yeşil küçük etiket, kesikli yatay çizgi
- Mum grafik renkleri: yeşil mum outline (içi boş), kırmızı mum dolu
- Hacim barları: mum renginde, %10 opaklık, grafik altında

### 6.6 Navigasyon (Sol Sidebar)

```
┌────┐
│ R  │  ← Logo: 28x28px, beyaz-gri gradient, border-radius: 6px
├────┤
│ ◫  │  ← Aktif: bg rgba(255,255,255,0.06), renk: beyaz
│ ◩  │  ← Pasif: renk rgba(255,255,255,0.3)
│ ⬡  │
│ ▦  │
│ ◎  │
│    │
│ ⚙  │  ← Alt kısımda
└────┘
```

Kurallar:
- Genişlik: 56px sabit
- İkon boyutu: 36x36px touch target, 16px ikon
- Arka plan: `var(--bg-surface)` + sağ kenar border
- Aktif göstergesi: hafif arka plan tonu (renkli highlight KULLANMA)
- Tooltip: hover'da sağda küçük label göster
- Renkli ikon KULLANMA — tamamı mono beyaz/gri tonlarında

### 6.7 Top Bar

```
Rapot | Otonom Piyasa Analizi                    ● Binance   10 Şub 2026   21:37:41
```

Kurallar:
- Yükseklik: 40px sabit
- Sol: proje adı (600 weight) + açıklama (secondary renk)
- Sağ: bağlantı durumu (yeşil/kırmızı dot, pulse animasyonu) + tarih + saat
- Saat monospace, saniye dahil, her saniye güncellenir
- Alt border: `1px solid var(--border-subtle)`

### 6.8 Butonlar ve İnteraktif Elementler

```css
/* Primary action (nadiren kullanılır) */
.btn-primary {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 2px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
}
.btn-primary:hover {
  background: rgba(255, 255, 255, 0.12);
}

/* Renkli buton KULLANMA */
/* Gradient buton KULLANMA */
/* Gölgeli buton KULLANMA */
```

### 6.9 Input ve Select

```css
input, select {
  background: var(--bg-base);
  border: 1px solid var(--border-default);
  border-radius: 2px;
  color: var(--text-primary);
  font-size: 13px;
  padding: 6px 10px;
}
input:focus {
  border-color: var(--border-strong);
  outline: none;
  /* box-shadow YOK, glow YOK */
}
```

---

## 7. ANİMASYON ve GEÇİŞLER

### 7.1 Genel Prensipler
- Animasyonlar FONKSİYONEL olmalı, dekoratif DEĞİL
- Süre: 100-200ms arası (hızlı geçişler)
- Easing: `ease` veya `ease-out` (bounce, elastic KULLANMA)
- Paralel animasyon sayısı: aynı anda en fazla 2

### 7.2 İzin Verilen Animasyonlar

```css
/* Hover geçişleri */
transition: background-color 0.1s ease;
transition: color 0.15s ease;
transition: opacity 0.15s ease;
transition: border-color 0.1s ease;

/* Liste elemanları yüklenirken stagger */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
animation-delay: calc(var(--index) * 40ms);

/* Bağlantı durumu pulse */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Fiyat değişimi flash */
@keyframes priceFlash {
  0% { background: rgba(34,197,94,0.15); }
  100% { background: transparent; }
}
```

### 7.3 YASAK Animasyonlar
- Scale transform (büyüme/küçülme)
- Rotate
- Bounce / elastic easing
- Uzun süren animasyonlar (> 300ms)
- Glow pulse efektleri
- Parallax scrolling
- Sayaç animasyonları (counting up)
- Gradient animasyonları
- Skeleton loading shimmer (tercih: opacity fade-in)

---

## 8. RESPONSIVE DAVRANIŞ

### 8.1 Breakpoint'ler
```css
--bp-desktop:   1440px+    /* Tam layout */
--bp-laptop:    1024-1439  /* Sidebar daraltılabilir */
--bp-tablet:    768-1023   /* Sidebar overlay, tek kolon */
--bp-mobile:    <768       /* Tam mobil layout */
```

### 8.2 Davranış Kuralları
- Desktop: Tam grid layout (nav + ana alan + sidebar)
- Laptop: Sidebar toggle ile açılıp kapanabilir
- Tablet: Nav icon-only, sidebar overlay olarak açılır, tek kolonlu içerik
- Mobile: Bottom tab navigation, tam genişlik içerik, grafik horizontal scroll

### 8.3 Öncelik Sırası (Mobilde Ne Gizlenir)
1. Grafik her zaman görünür (ana içerik)
2. Watchlist ve fiyat verileri görünür
3. Stat ribbon compact moda geçer
4. Sinyal listesi alt tab'a taşınır
5. OHLC detayları gizlenir

---

## 9. DARK/LIGHT MODE

### 9.1 Kısa Cevap
Sadece dark mode var. Light mode planlanmamıştır.

### 9.2 Neden
- Finansal terminaller geleneksel olarak dark theme kullanır (Bloomberg, TradingView, broker uygulamaları)
- 24/7 izleme senaryosunda göz yorgunluğu dark theme ile azalır
- Grafik ve mum çubukları dark arka planda daha okunabilir

---

## 10. KODLAMA STANDARTLARI

### 10.1 CSS Yazım Kuralları
```
- Tailwind utility class'ları kullan, ancak custom değerler için CSS variables
- !important ASLA kullanma
- Inline style ASLA kullanma (tek seferlik prototipler hariç)
- Her komponent kendi CSS module'üne sahip olmalı
- Tailwind'de varsayılan renk class'larını (bg-blue-500 vb.) KULLANMA — custom palette kullan
```

### 10.2 Komponent Yapısı
```
src/
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── TopBar.tsx
│   │   └── StatRibbon.tsx
│   ├── chart/
│   │   ├── CandlestickChart.tsx
│   │   ├── MiniSparkline.tsx
│   │   └── ChartControls.tsx
│   ├── market/
│   │   ├── Watchlist.tsx
│   │   ├── WatchlistRow.tsx
│   │   ├── PriceDisplay.tsx
│   │   └── TickerTape.tsx
│   ├── signals/
│   │   ├── SignalFeed.tsx
│   │   ├── SignalCard.tsx
│   │   └── SignalTag.tsx
│   └── ui/
│       ├── Pill.tsx
│       ├── StatusDot.tsx
│       └── Divider.tsx
├── styles/
│   ├── tokens.css          /* Tüm CSS variables burada */
│   ├── typography.css
│   └── animations.css
├── lib/
│   ├── formatters.ts       /* Sayı formatlama fonksiyonları */
│   └── colors.ts           /* Renk helper'ları */
└── types/
    └── market.ts           /* Tip tanımları */
```

### 10.3 Naming Convention
```
- Komponentler: PascalCase (WatchlistRow.tsx)
- Fonksiyonlar: camelCase (formatPrice, getChangeColor)
- CSS variables: kebab-case (--bg-surface, --text-primary)
- Dosyalar: PascalCase (komponent), camelCase (utility)
- Boolean prop'lar: is/has prefix (isActive, hasData)
```

### 10.4 Performans Kuralları
```
- Grafik re-render: requestAnimationFrame ile throttle
- Fiyat güncellemesi: WebSocket, polling KULLANMA
- Liste render: virtualization (react-window) 50+ item için
- Resim: SVG ikon tercih et, PNG/JPG KULLANMA (ikon için)
- Bundle: her route lazy load
- Font: preload, display: swap
```

### 10.5 Encoding ve Metin Bütünlüğü (ZORUNLU)
```
- Tüm metin dosyaları UTF-8 (tercihen BOM'suz) olarak okunur/yazılır.
- Türkçe karakter içeren dosyalarda platform varsayılan encoding'i ASLA kullanılmaz.
- PowerShell ile dosya işleniyorsa daima açık encoding kullan:
  Get-Content -Raw -Encoding utf8
  Set-Content -Encoding utf8
- Toplu replace sonrası metin bozulması kontrolü zorunlu:
  rg -n "(\\uFFFD|\\xC3|\\xC4|\\xC5)" frontend/src docs
- Arayüzde bozuk/okunmayan karakter çıktısı görülürse değişiklik yayınlanmaz;
  önce encoding düzeltilir, sonra commit/push yapılır.
```

---

## 11. ÖRNEK KOD REFERANSLARI

### 11.1 Token Dosyası (tokens.css)
```css
:root {
  /* Backgrounds */
  --bg-base: #08080C;
  --bg-surface: #0C0C12;
  --bg-raised: #111118;
  --bg-overlay: #16161E;

  /* Borders */
  --border-subtle: rgba(255, 255, 255, 0.04);
  --border-default: rgba(255, 255, 255, 0.06);
  --border-strong: rgba(255, 255, 255, 0.10);

  /* Text */
  --text-primary: #E8E8EC;
  --text-secondary: rgba(255, 255, 255, 0.50);
  --text-tertiary: rgba(255, 255, 255, 0.30);
  --text-ghost: rgba(255, 255, 255, 0.15);

  /* Market */
  --positive: #22C55E;
  --negative: #EF4444;
  --neutral: #F59E0B;

  /* Chart */
  --chart-1: #3B82F6;
  --chart-2: #8B5CF6;
  --chart-3: #06B6D4;

  /* Typography */
  --font-sans: 'DM Sans', system-ui, sans-serif;
  --font-mono: 'DM Mono', 'JetBrains Mono', monospace;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
}
```

### 11.2 Tailwind Config Uzantısı
```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#08080C',
          surface: '#0C0C12',
          raised: '#111118',
          overlay: '#16161E',
        },
        border: {
          subtle: 'rgba(255,255,255,0.04)',
          default: 'rgba(255,255,255,0.06)',
          strong: 'rgba(255,255,255,0.10)',
        },
        text: {
          primary: '#E8E8EC',
          secondary: 'rgba(255,255,255,0.50)',
          tertiary: 'rgba(255,255,255,0.30)',
          ghost: 'rgba(255,255,255,0.15)',
        },
        market: {
          positive: '#22C55E',
          negative: '#EF4444',
          neutral: '#F59E0B',
        },
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['DM Mono', 'JetBrains Mono', 'monospace'],
      },
      fontSize: {
        xs: '10px',
        sm: '11px',
        base: '13px',
        md: '14px',
        lg: '18px',
        xl: '24px',
      },
      borderRadius: {
        none: '0px',
        sm: '2px',
        DEFAULT: '2px',
        md: '4px',
        lg: '6px',    /* SADECE logo ve avatar için */
      },
      spacing: {
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
        '8': '32px',
      },
    },
  },
};
```

---

## 12. KALİTE KONTROL CHECKLIST

Her komponent veya sayfa tamamlandığında şu kontrolü yap:

### Görsel Kontrol
- [ ] Border-radius hiçbir yerde 6px'i geçmiyor
- [ ] Box-shadow hiçbir yerde kullanılmıyor
- [ ] Gradient arka plan hiçbir yerde yok
- [ ] Glow efekti hiçbir yerde yok
- [ ] Renkli (mavi, mor, turuncu) dekoratif ikon yok
- [ ] Eşit boyutlu kart sırası layout yok
- [ ] Tüm sayılar monospace fontta

### Tipografi Kontrol
- [ ] Font ailesi DM Sans veya DM Mono dışında bir şey kullanılmamış
- [ ] Uppercase etiketlerde letter-spacing: 0.06em uygulanmış
- [ ] Fiyat verilerinde font-feature-settings: 'tnum' 1 var

### Renk Kontrol
- [ ] Accent renk olarak sadece piyasa renkleri (yeşil/kırmızı) kullanılmış
- [ ] Metin opaklıkları 4 kademeli sistemle uyumlu
- [ ] Border'lar alpha değerli rgba ile tanımlı

### Performans Kontrol
- [ ] Gereksiz re-render yok
- [ ] Animasyon süresi 300ms'yi geçmiyor
- [ ] 60fps'in altına düşmüyor

---

## 13. CODEX'E ÖZEL DİREKTİFLER

### Ne Zaman Bu Dokümanı Referans Almalısın
- HER yeni komponent oluşturulduğunda
- HER stil değişikliği yapıldığında
- HER layout kararı alındığında

### Çelişki Durumunda Öncelik Sırası
1. Bu doküman (en yüksek öncelik)
2. Figma/tasarım mockup (varsa)
3. Mevcut kod tabanındaki pattern'ler
4. Kendi en iyi yargın (en düşük öncelik)

### Emin Olmadığında
- Daha minimal olanı seç
- Daha az renk kullan
- Daha küçük border-radius kullan
- Daha az animasyon kullan
- Veri okunabilirliğini dekorasyona tercih et

### Asla Yapma
- Sorulmadan yeni renk ekleme
- Sorulmadan animasyon ekleme
- Sorulmadan border-radius artırma
- Sorulmadan ikon ekleme
- Sorulmadan font değiştirme
- Generic "dashboard template" kodu yapıştırma

---

*Bu doküman Rapot projesinin tek tasarım kaynağıdır. Tüm UI kararları bu dokümanla uyumlu olmalıdır.*
