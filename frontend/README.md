# Rapot Dashboard 📈

Rapot finansal analiz botu için geliştirilmiş, TradingView kalitesinde profesyonel Admin Paneli.

## 🚀 Başlangıç

Node 20.20.2 ve npm 10.9.9 kullanılır. Kurulum ve doğrulama adımları
[devam planında](../docs/RAPOT_DEVAM_PLANI.md#geliştirme-ortamı-ve-komutlar) kayıtlıdır.
Bu klasörde geliştirme sunucusunu başlatmak için:

```bash
npm ci
npm run dev
```

Tarayıcınızda [http://localhost:3000](http://localhost:3000) adresine gidin.

## Oturum ve doğrulama

Üst çubuktaki **Giriş yap** bağlantısı `/login` ekranını açar. Ana API'de tanımlı
`admin` veya `user` hesabını kullanın; parolalar backend ortamından yönetilir.
AI analizi ve strateji inceleme giriş, loglar ve manuel tarama admin yetkisi ister.

Token yalnız sekme belleğinde tutulur; sayfa yenileme, süre dolumu veya çıkış oturumu
sonlandırır. Oturum değişince sorgu önbelleği ve önceki kullanıcıya ait bileşen durumu
temizlenir. Token yalnız yapılandırılmış ana API adresine eklenir; health API'ye
ve başka servislere gönderilmez. `MW_ADMIN_AUTH_TOKEN` frontend'e verilmez.

```bash
npm test
npm run lint
npx tsc --noEmit --incremental false
npm run build
```

`npm test`, gerçek TypeScript oturum/API modüllerini bellekte derleyip sahte HTTP
yanıtlarıyla sınar; backend, dış ağ veya gerçek kullanıcı hesabı gerekmez.

## 🛠️ Teknolojiler

- **Framework:** Next.js 16.2.1 (App Router)
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
