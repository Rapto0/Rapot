# 📋 RAPOT DASHBOARD - DETAYLI İMPLEMENTASYON PLANI

> **Versiyon:** 1.0
> **Tahmini Süre:** 8-12 Hafta
> **Metodoloji:** Agile Sprint (2 haftalık döngüler)

---

## 📊 PROJE GENEL BAKIŞ

### Vizyon
TradingView kalitesinde, 7/24 kesintisiz çalışan, gerçek zamanlı finansal analiz ve bot yönetim platformu.

### Başarı Kriterleri
| Metrik | Hedef |
|--------|-------|
| First Contentful Paint (FCP) | < 1.5s |
| Largest Contentful Paint (LCP) | < 2.5s |
| Cumulative Layout Shift (CLS) | < 0.1 |
| WebSocket Latency | < 100ms |
| Uptime | 99.9% |
| Mobile Lighthouse Score | > 90 |

---

## 🗓️ SPRINT PLANI

### SPRINT 0: Hazırlık (1 Hafta)
**Hedef:** Proje altyapısını kurma ve standartları belirleme

#### Görevler

##### 0.1 Proje Kurulumu
```bash
# Next.js 14 projesi oluştur
npx create-next-app@latest rapot-dashboard --typescript --tailwind --eslint --app --src-dir=false

# Gerekli paketleri yükle
npm install @tanstack/react-query zustand @radix-ui/react-* clsx tailwind-merge
npm install lightweight-charts recharts lucide-react
npm install -D @types/node prettier eslint-config-prettier
```

##### 0.2 Shadcn/UI Kurulumu
```bash
npx shadcn@latest init
npx shadcn@latest add button card table badge input select tabs dialog sheet toast
```

##### 0.3 Tailwind v4 Konfigürasyonu
```css
/* app/globals.css */
@import "tailwindcss";

@theme {
  /* Arka Planlar */
  --color-bg-primary: #0e1117;
  --color-bg-secondary: #161b22;
  --color-bg-tertiary: #1c2128;
  --color-bg-elevated: #21262d;

  /* Metin */
  --color-text-primary: #e6edf3;
  --color-text-secondary: #8b949e;
  --color-text-muted: #6e7681;

  /* Semantik */
  --color-long: #00c853;
  --color-short: #ff3d00;
  --color-warning: #ffab00;
  --color-info: #2196f3;

  /* Kenarlıklar */
  --color-border-default: #30363d;
  --color-border-hover: #8b949e;
  --color-border-focus: #58a6ff;

  /* Spacing */
  --spacing-1: 4px;
  --spacing-2: 8px;
  --spacing-3: 12px;
  --spacing-4: 16px;
  --spacing-5: 24px;
  --spacing-6: 32px;
  --spacing-7: 48px;
}
```

##### 0.4 TypeScript Tip Tanımlamaları
```typescript
// types/index.ts
export interface Signal {
  id: string;
  symbol: string;
  type: 'HUNTER' | 'COMBO';
  direction: 'LONG' | 'SHORT';
  entry: number;
  target: number;
  stopLoss: number;
  confidence: number;
  timestamp: Date;
  status: 'ACTIVE' | 'HIT_TARGET' | 'HIT_STOP' | 'EXPIRED';
  metadata?: {
    timeframe: string;
    indicators: string[];
    notes?: string;
  };
}

export interface Trade {
  id: string;
  signalId?: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  leverage: number;
  status: 'OPEN' | 'CLOSED' | 'LIQUIDATED';
  pnl?: number;
  pnlPercent?: number;
  openedAt: Date;
  closedAt?: Date;
  fees: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  change24h: number;
  changePercent24h: number;
  volume24h: number;
  high24h: number;
  low24h: number;
  lastUpdate: Date;
}

export interface SystemHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  uptime: number;
  lastHeartbeat: Date;
  services: {
    name: string;
    status: 'UP' | 'DOWN';
    latency?: number;
  }[];
  resources: {
    cpu: number;
    memory: number;
    disk: number;
  };
}

export interface KPI {
  totalPnL: number;
  totalPnLPercent: number;
  winRate: number;
  totalTrades: number;
  openPositions: number;
  activeSignals: number;
  avgRiskReward: number;
  maxDrawdown: number;
  sharpeRatio: number;
}
```

##### 0.5 Dizin Yapısı
```
rapot-dashboard/
├── app/
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── scanner/page.tsx
│   │   ├── signals/page.tsx
│   │   ├── trades/page.tsx
│   │   ├── health/page.tsx
│   │   └── settings/page.tsx
│   ├── api/
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/
│   ├── charts/
│   ├── dashboard/
│   ├── layout/
│   └── shared/
├── lib/
│   ├── api/
│   ├── hooks/
│   ├── stores/
│   ├── utils/
│   └── constants/
├── types/
└── public/
```

#### Çıktılar
- [ ] Boş proje yapısı hazır
- [ ] Tüm paketler yüklü
- [ ] Tailwind konfigürasyonu tamam
- [ ] TypeScript tipleri tanımlı
- [ ] ESLint/Prettier ayarlı

---

### SPRINT 1: Temel Layout ve Navigasyon (2 Hafta)
**Hedef:** Sidebar, Header ve temel sayfa yapısı

#### Hafta 1: Layout Komponentleri

##### 1.1 Sidebar Komponenti
```typescript
// components/layout/Sidebar.tsx
// Özellikler:
// - Collapsible (daraltılabilir)
// - Aktif sayfa highlight
// - Icon + text navigation
// - Alt kısımda kullanıcı/ayarlar
// - Keyboard navigation desteği
```

**Navigasyon Items:**
| Icon | Label | Path | Badge |
|------|-------|------|-------|
| LayoutDashboard | Dashboard | / | - |
| Scan | Piyasa Tarayıcı | /scanner | Tarama durumu |
| Signal | Aktif Sinyaller | /signals | Sayı |
| History | İşlem Geçmişi | /trades | - |
| Activity | Bot Sağlığı | /health | Status dot |
| Settings | Ayarlar | /settings | - |

##### 1.2 Header Komponenti
```typescript
// components/layout/Header.tsx
// Özellikler:
// - Breadcrumb navigation
// - Global search (CMD+K)
// - Notification bell
// - Connection status indicator
// - Quick actions menu
```

##### 1.3 Mobile Navigation
```typescript
// components/layout/MobileNav.tsx
// Özellikler:
// - Bottom tab bar (iOS style)
// - Hamburger menu
// - Gesture support
```

#### Hafta 2: Temel Sayfa İskeletleri

##### 1.4 Dashboard Layout
```typescript
// app/(dashboard)/layout.tsx
export default function DashboardLayout({ children }) {
  return (
    <div className="flex h-screen bg-bg-primary">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

##### 1.5 Her Sayfa İçin Placeholder
- `/` → Dashboard grid layout
- `/scanner` → Tarayıcı durumu
- `/signals` → Sinyal tablosu layout
- `/trades` → İşlem geçmişi layout
- `/health` → Sistem metrikleri layout
- `/settings` → Ayar kategorileri layout

#### Çıktılar
- [ ] Sidebar tam fonksiyonel
- [ ] Header tam fonksiyonel
- [ ] Mobile navigation çalışıyor
- [ ] Tüm sayfalar navigasyona bağlı
- [ ] Keyboard shortcuts (CMD+K, etc.)

---

### SPRINT 2: Dashboard Ana Sayfa (2 Hafta)
**Hedef:** KPI kartları, mini grafikler ve canlı veri gösterimi

#### Hafta 3: KPI Kartları

##### 2.1 KPI Veri Yapısı
```typescript
// lib/api/dashboard.ts
export async function fetchDashboardKPIs(): Promise<KPI> {
  // API'den veya WebSocket'ten veri çek
}

// lib/hooks/useDashboardKPIs.ts
export function useDashboardKPIs() {
  return useQuery({
    queryKey: ['dashboard', 'kpis'],
    queryFn: fetchDashboardKPIs,
    refetchInterval: 10000, // 10 saniye
  });
}
```

##### 2.2 KPI Kart Tipleri

**Toplam PnL Kartı:**
```
┌─────────────────────────────────────┐
│ Toplam P&L                    📈   │
│ $12,458.32                         │
│ ▲ +8.4% (24s)                      │
│ [═══════════════      ] Sparkline  │
└─────────────────────────────────────┘
```

**Win Rate Kartı:**
```
┌─────────────────────────────────────┐
│ Win Rate                      🎯   │
│ 68.5%                              │
│ 137/200 işlem                      │
│ [Donut chart - Kazanç/Kayıp]       │
└─────────────────────────────────────┘
```

**Açık Pozisyonlar:**
```
┌─────────────────────────────────────┐
│ Açık Pozisyonlar              📊   │
│ 5                                  │
│ $2,340 marjin kullanımda           │
│ [Mini position bars]               │
└─────────────────────────────────────┘
```

**Aktif Sinyaller:**
```
┌─────────────────────────────────────┐
│ Aktif Sinyaller               🔔   │
│ 12                                 │
│ 8 Hunter • 4 Combo                 │
│ [Type breakdown mini bars]         │
└─────────────────────────────────────┘
```

#### Hafta 4: Grafikler ve Canlı Veri

##### 2.3 Ana PnL Grafiği
```typescript
// components/charts/PnLChart.tsx
// Özellikler:
// - Recharts AreaChart
// - Zaman aralığı seçici (1S, 1G, 1H, 1A, Tümü)
// - Hover tooltip
// - Gradient fill (yeşil/kırmızı)
// - Responsive
```

##### 2.4 Mini Sparkline Komponenti
```typescript
// components/charts/MiniSparkline.tsx
// Özellikler:
// - Lightweight Charts
// - 50px yükseklik
// - Son 24 veri noktası
// - Trend renklendirme
```

##### 2.5 Son İşlemler Widget
```typescript
// components/dashboard/RecentTrades.tsx
// Özellikler:
// - Son 5 işlem
// - Compact card view
// - Real-time update
// - "Tümünü Gör" linki
```

##### 2.6 Canlı Sinyal Feed
```typescript
// components/dashboard/LiveSignalFeed.tsx
// Özellikler:
// - WebSocket bağlantısı
// - Yeni sinyal animasyonu
// - Ses bildirimi (opsiyonel)
// - Son 10 sinyal
```

#### Dashboard Grid Layout
```
┌──────────────────────────────────────────────────────────────────┐
│  KPI 1      │  KPI 2      │  KPI 3      │  KPI 4                │
├─────────────┴─────────────┴─────────────┴───────────────────────┤
│                                                                  │
│                     ANA PNL GRAFİĞİ                             │
│                                                                  │
├──────────────────────────────────┬───────────────────────────────┤
│                                  │                               │
│      SON İŞLEMLER                │      CANLI SİNYAL FEED       │
│                                  │                               │
└──────────────────────────────────┴───────────────────────────────┘
```

#### Çıktılar
- [ ] 4 KPI kartı tam fonksiyonel
- [ ] Ana PnL grafiği çalışıyor
- [ ] Sparkline'lar render ediliyor
- [ ] Son işlemler widget
- [ ] Canlı sinyal feed (mock data ile)
- [ ] Responsive grid layout

---

### SPRINT 3: Sinyal Yönetimi Sayfası (2 Hafta)
**Hedef:** Filtrelenebilir, sıralanabilir sinyal tablosu

#### Hafta 5: Tablo Altyapısı

##### 3.1 Tablo Komponenti
```typescript
// components/dashboard/SignalTable.tsx
// Teknoloji: TanStack Table v8
// Özellikler:
// - Sıralama (tüm kolonlar)
// - Filtreleme (multi-select)
// - Pagination
// - Row selection
// - Column visibility toggle
// - Export to CSV
```

##### 3.2 Tablo Kolonları
| Kolon | Tip | Sıralama | Filtre |
|-------|-----|----------|--------|
| Sembol | Text + Icon | ✓ | Arama |
| Tip | Badge | ✓ | Multi-select |
| Yön | Badge | ✓ | Multi-select |
| Giriş | Number | ✓ | Range |
| Hedef | Number | ✓ | Range |
| Stop | Number | ✓ | Range |
| R:R | Number | ✓ | Range |
| Güven | Progress | ✓ | Range |
| Durum | Badge | ✓ | Multi-select |
| Zaman | Relative | ✓ | Date range |
| Aksiyon | Buttons | - | - |

##### 3.3 Filtre Paneli
```typescript
// components/dashboard/SignalFilters.tsx
// Özellikler:
// - Collapsible panel
// - Preset filtreler (Aktif, Bugünkü, Hunter, Combo)
// - Filtre kaydetme
// - Filtre temizleme
```

#### Hafta 6: Detay ve Aksiyonlar

##### 3.4 Sinyal Detay Modal
```typescript
// components/dashboard/SignalDetailModal.tsx
// Özellikler:
// - Full signal info
// - Mini chart (entry/target/stop görsel)
// - İlgili işlemler
// - Notlar
// - Aksiyon butonları
```

##### 3.5 Batch Aksiyonlar
```typescript
// Özellikler:
// - Çoklu seçim
// - Toplu silme
// - Toplu export
// - Toplu durum güncelleme
```

##### 3.6 Yeni Sinyal Form (Manuel)
```typescript
// components/dashboard/NewSignalForm.tsx
// Özellikler:
// - Sembol arama (autocomplete)
// - Tip seçimi
// - Fiyat girişleri (validation)
// - Otomatik R:R hesaplama
// - Preview
```

#### Çıktılar
- [ ] Sinyal tablosu tam fonksiyonel
- [ ] Tüm filtreler çalışıyor
- [ ] Sıralama çalışıyor
- [ ] Detay modal
- [ ] Batch aksiyonlar
- [ ] Manuel sinyal ekleme

---

### SPRINT 4: İşlem Geçmişi ve PnL Analizi (2 Hafta)
**Hedef:** Detaylı işlem takibi ve performans analizi

#### Hafta 7: İşlem Tablosu

##### 4.1 Trade Tablosu
```typescript
// components/dashboard/TradeHistory.tsx
// Özellikler:
// - Açık/Kapalı sekmeleri
// - Detaylı PnL görünümü
// - Fee breakdown
// - Duration hesaplama
```

##### 4.2 Trade Kolonları
| Kolon | Açık | Kapalı |
|-------|------|--------|
| Sembol | ✓ | ✓ |
| Yön | ✓ | ✓ |
| Miktar | ✓ | ✓ |
| Giriş Fiyatı | ✓ | ✓ |
| Mevcut/Çıkış Fiyatı | ✓ | ✓ |
| Unrealized/Realized PnL | ✓ | ✓ |
| Kaldıraç | ✓ | ✓ |
| Açılış Zamanı | ✓ | ✓ |
| Kapanış Zamanı | - | ✓ |
| Süre | - | ✓ |
| Fee | ✓ | ✓ |

#### Hafta 8: PnL Dashboard

##### 4.3 PnL Özet Kartları
```
┌─────────────────────────────────────────────────────────┐
│  Bugün      │  Bu Hafta   │  Bu Ay      │  Tüm Zamanlar │
│  +$234.50   │  +$1,245.30 │  +$4,567.80 │  +$12,458.32  │
│  ▲ 2.3%     │  ▲ 5.1%     │  ▲ 12.4%    │  ▲ 45.2%      │
└─────────────────────────────────────────────────────────┘
```

##### 4.4 PnL Breakdown Chart
```typescript
// components/charts/PnLBreakdown.tsx
// Özellikler:
// - Stacked bar chart (günlük)
// - Long vs Short breakdown
// - Cumulative line overlay
// - Zaman aralığı seçici
```

##### 4.5 Performans Metrikleri
```typescript
// components/dashboard/PerformanceMetrics.tsx
// Metrikler:
// - Sharpe Ratio
// - Max Drawdown
// - Avg Win / Avg Loss
// - Profit Factor
// - Recovery Factor
// - Best/Worst Trade
```

##### 4.6 Trade Detay Modal
```typescript
// components/dashboard/TradeDetailModal.tsx
// Özellikler:
// - Full trade info
// - Entry/Exit chart
// - İlgili sinyal link
// - PnL timeline
// - Notlar
```

#### Çıktılar
- [ ] Trade tablosu (açık/kapalı)
- [ ] PnL özet kartları
- [ ] PnL breakdown chart
- [ ] Performans metrikleri widget
- [ ] Trade detay modal
- [ ] Export fonksiyonu

---

### SPRINT 5: Piyasa Tarayıcı ve Bot Sağlığı (2 Hafta)
**Hedef:** Tarama durumu ve sistem monitoring

#### Hafta 9: Piyasa Tarayıcı

##### 5.1 Scanner Status Dashboard
```
┌─────────────────────────────────────────────────────────────────┐
│  BIST Scanner          │  Kripto Scanner                       │
│  ⏳ Taraniyor...        │  ✓ Tamamlandı                         │
│  345/500 sembol        │  250/250 sembol                       │
│  [Progress bar]        │  Son: 2 dk önce                       │
├─────────────────────────────────────────────────────────────────┤
│                     TARAMA SONUÇLARI                           │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Sembol │ Puan │ Sinyaller │ Son Fiyat │ Değişim │ Aksiyon│  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

##### 5.2 Scanner Ayarları
```typescript
// Özellikler:
// - Tarama sıklığı
// - İzleme listesi yönetimi
// - Alarm kuralları
// - Filtreleme kriterleri
```

#### Hafta 10: Bot Sağlığı Sayfası

##### 5.3 Sistem Durumu Panel
```
┌─────────────────────────────────────────────────────────────────┐
│  BOT DURUMU: 🟢 ÇALIŞIYOR                                      │
│  Uptime: 15g 23s 45dk │ Son heartbeat: 3 sn önce              │
├─────────────────────────────────────────────────────────────────┤
│  API Bağlantıları                                              │
│  ├─ Binance API      🟢 45ms                                   │
│  ├─ BIST API         🟢 120ms                                  │
│  ├─ Database         🟢 12ms                                   │
│  └─ Redis Cache      🟢 5ms                                    │
├─────────────────────────────────────────────────────────────────┤
│  Sistem Kaynakları                                             │
│  CPU: [████████░░] 78%  │  RAM: [██████░░░░] 62%              │
│  Disk: [███░░░░░░░] 34% │  Network: ↓ 1.2MB/s ↑ 0.8MB/s       │
└─────────────────────────────────────────────────────────────────┘
```

##### 5.4 Terminal Log Viewer
```typescript
// components/health/LogViewer.tsx
// Özellikler:
// - Virtual scrolling (binlerce satır)
// - Log level filtreleme (DEBUG, INFO, WARN, ERROR)
// - Arama
// - Zaman filtresi
// - Auto-scroll toggle
// - Syntax highlighting
```

##### 5.5 Metrik Grafikleri
```typescript
// components/health/MetricCharts.tsx
// Grafikler:
// - CPU usage over time
// - Memory usage over time
// - Request latency histogram
// - Error rate trend
```

##### 5.6 Alert Yönetimi
```typescript
// components/health/AlertManager.tsx
// Özellikler:
// - Aktif alertler listesi
// - Alert geçmişi
// - Alert kuralları düzenleme
// - Bildirim ayarları
```

#### Çıktılar
- [ ] Scanner status dashboard
- [ ] Tarama sonuçları tablosu
- [ ] Sistem durumu panel
- [ ] Log viewer
- [ ] Metrik grafikleri
- [ ] Alert yönetimi

---

### SPRINT 6: Ayarlar ve Son Rötuşlar (2 Hafta)
**Hedef:** Konfigürasyon, polish ve deployment

#### Hafta 11: Ayarlar Sayfası

##### 6.1 Ayar Kategorileri
```
┌───────────────────┬─────────────────────────────────────────────┐
│                   │                                             │
│  📍 API Anahtarları │  API yapılandırması                       │
│  🔔 Bildirimler    │  Telegram, Discord, Email ayarları        │
│  ⚙️ Strateji       │  Hunter/Combo parametreleri               │
│  💰 Risk Yönetimi  │  Pozisyon boyutu, max drawdown            │
│  🎨 Görünüm       │  Tema, dil, timezone                       │
│  📊 Veri          │  Export, backup, temizlik                  │
│                   │                                             │
└───────────────────┴─────────────────────────────────────────────┘
```

##### 6.2 API Anahtarları Yönetimi
```typescript
// components/settings/APIKeys.tsx
// Özellikler:
// - Şifreli gösterim
// - Bağlantı testi
// - Yetki kontrolü
// - Son kullanım
```

##### 6.3 Strateji Parametreleri
```typescript
// components/settings/StrategyParams.tsx
// Özellikler:
// - Hunter parametreleri
// - Combo parametreleri
// - Backtest preview
// - Preset yönetimi
```

#### Hafta 12: Polish ve Deployment

##### 6.4 Loading States
- [ ] Tüm sayfalar için skeleton loaders
- [ ] Button loading states
- [ ] Progressive loading

##### 6.5 Error States
- [ ] 404 sayfası
- [ ] 500 sayfası
- [ ] Network error handling
- [ ] Empty states

##### 6.6 Accessibility
- [ ] Keyboard navigation
- [ ] Screen reader support
- [ ] Focus management
- [ ] ARIA labels

##### 6.7 Performance Audit
- [ ] Lighthouse audit
- [ ] Bundle size optimization
- [ ] Image optimization
- [ ] Code splitting review

##### 6.8 Deployment Setup
```yaml
# vercel.json veya docker-compose.yml
# Production environment variables
# CI/CD pipeline
# Monitoring setup (Sentry, etc.)
```

#### Çıktılar
- [ ] Ayarlar sayfası tam
- [ ] Tüm loading states
- [ ] Tüm error states
- [ ] A11y compliance
- [ ] Performance optimized
- [ ] Deployment ready

---

## 🔌 API ENTEGRASYONLARİ

### Backend API Endpoints (Python)

```yaml
# Signals
GET    /api/signals              # Tüm sinyaller
GET    /api/signals/:id          # Tek sinyal
POST   /api/signals              # Yeni sinyal
PUT    /api/signals/:id          # Sinyal güncelle
DELETE /api/signals/:id          # Sinyal sil

# Trades
GET    /api/trades               # Tüm işlemler
GET    /api/trades/:id           # Tek işlem
GET    /api/trades/open          # Açık pozisyonlar
GET    /api/trades/history       # Kapalı işlemler

# Dashboard
GET    /api/dashboard/kpis       # KPI metrikleri
GET    /api/dashboard/pnl        # PnL verileri

# Scanner
GET    /api/scanner/status       # Tarama durumu
GET    /api/scanner/results      # Tarama sonuçları
POST   /api/scanner/start        # Tarama başlat
POST   /api/scanner/stop         # Tarama durdur

# Health
GET    /api/health               # Sistem sağlığı
GET    /api/health/logs          # Loglar
GET    /api/health/metrics       # Metrikler

# Settings
GET    /api/settings             # Tüm ayarlar
PUT    /api/settings             # Ayarları güncelle

# WebSocket
WS     /api/ws/signals           # Canlı sinyal stream
WS     /api/ws/trades            # Canlı trade stream
WS     /api/ws/prices            # Canlı fiyat stream
```

### WebSocket Message Format
```typescript
// Sinyal güncellemesi
{
  type: 'SIGNAL_UPDATE',
  payload: Signal
}

// Yeni sinyal
{
  type: 'NEW_SIGNAL',
  payload: Signal
}

// Trade güncellemesi
{
  type: 'TRADE_UPDATE',
  payload: Trade
}

// Fiyat güncellemesi
{
  type: 'PRICE_UPDATE',
  payload: {
    symbol: string,
    price: number,
    timestamp: number
  }
}

// Sistem durumu
{
  type: 'HEALTH_UPDATE',
  payload: SystemHealth
}
```

---

## 📦 PAKET LİSTESİ

### Production Dependencies
```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.0.0",
    "@tanstack/react-table": "^8.0.0",
    "zustand": "^4.4.0",
    "lightweight-charts": "^4.1.0",
    "recharts": "^2.10.0",
    "lucide-react": "^0.300.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "date-fns": "^3.0.0",
    "zod": "^3.22.0",
    "react-hot-toast": "^2.4.0"
  }
}
```

### Dev Dependencies
```json
{
  "devDependencies": {
    "typescript": "^5.3.0",
    "@types/react": "^18.2.0",
    "@types/node": "^20.0.0",
    "tailwindcss": "^4.0.0",
    "eslint": "^8.0.0",
    "eslint-config-next": "^14.0.0",
    "prettier": "^3.0.0",
    "prettier-plugin-tailwindcss": "^0.5.0"
  }
}
```

---

## 🧪 TEST STRATEJİSİ

### Unit Tests
```typescript
// Jest + React Testing Library
// - Utility fonksiyonları
// - Custom hooks
// - İzole komponentler
```

### Integration Tests
```typescript
// - API entegrasyonları
// - Form submissions
// - Data fetching flows
```

### E2E Tests
```typescript
// Playwright
// - Critical user journeys
// - Cross-browser testing
// - Mobile testing
```

---

## 📈 BAŞARI METRİKLERİ

### Sprint Bazlı Kontrol Noktaları

| Sprint | Hafta | Tamamlanma % | Kontrol |
|--------|-------|--------------|---------|
| 0 | 1 | 10% | Proje yapısı hazır |
| 1 | 3 | 25% | Navigation çalışıyor |
| 2 | 5 | 45% | Dashboard fonksiyonel |
| 3 | 7 | 60% | Sinyaller yönetilebilir |
| 4 | 9 | 75% | İşlemler takip edilebilir |
| 5 | 11 | 90% | Tüm sayfalar hazır |
| 6 | 12 | 100% | Production ready |

---

## 🚀 DEPLOYMENT CHECKLIST

- [ ] Environment variables set
- [ ] Database migrations run
- [ ] SSL certificates configured
- [ ] CDN configured
- [ ] Error tracking (Sentry) enabled
- [ ] Analytics (Vercel Analytics) enabled
- [ ] Backup strategy implemented
- [ ] Monitoring dashboards ready
- [ ] Documentation complete
- [ ] Team training done

---

*Bu döküman, proje ilerledikçe güncellenmelidir.*
