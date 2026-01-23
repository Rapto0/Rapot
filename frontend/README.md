# Rapot Dashboard 📈

Rapot finansal analiz botu için geliştirilmiş, TradingView kalitesinde profesyonel Admin Paneli.

## 🚀 Başlangıç

Geliştirme sunucusunu başlatmak için:

```bash
npm run dev
# veya
yarn dev
# veya
pnpm dev
# veya
bun dev
```

Tarayıcınızda [http://localhost:3000](http://localhost:3000) adresine gidin.

## 🛠️ Teknolojiler

- **Framework:** Next.js 14 (App Router)
- **Dil:** TypeScript
- **Stil:** Tailwind CSS v4
- **UI:** Shadcn/UI
- **Grafikler:** TradingView Lightweight Charts & Recharts
- **State:** Zustand & React Query

## 📱 Sayfalar

| Sayfa | Açıklama |
|-------|----------|
| **Dashboard** | Ana ekran, KPI kartları, Canlı grafik ve PnL özeti |
| **Piyasa Tarayıcı** | `/scanner` - BIST ve Kripto tarama durumu |
| **Aktif Sinyaller** | `/signals` - Filtrelenebilir sinyal tablosu (Hunter/Combo) |
| **İşlem Geçmişi** | `/trades` - Açık/Kapalı işlemler ve detaylı PnL |
| **Bot Sağlığı** | `/health` - Terminal logları ve sistem metrikleri |
| **Ayarlar** | `/settings` - API anahtarları ve strateji parametreleri |

## 🎨 Tema

Proje **Dark Mode** odaklı tasarlanmıştır. Renk paleti TradingView dark temasıyla uyumludur:
- **Arka Plan:** `#0e1117`
- **Kartlar:** `#161b22`
- **Yükseliş (Long):** `#00c853`
- **Düşüş (Short):** `#ff3d00`
