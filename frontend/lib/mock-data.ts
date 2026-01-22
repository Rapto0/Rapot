export const tickerItems = [
  { label: "BIST 100", value: "10,482.20", change: "+1.42%" },
  { label: "BTC/USDT", value: "63,540", change: "+2.91%" },
  { label: "ETH/USDT", value: "3,412", change: "+0.88%" },
  { label: "XU030", value: "11,207", change: "-0.32%" }
];

export const kpis = [
  { label: "Toplam PnL", value: "₺1,284,400", delta: "+6.4%", tone: "long" },
  { label: "Win Rate", value: "%64.8", delta: "+1.2%", tone: "long" },
  { label: "Açık Pozisyon", value: "12", delta: "-2", tone: "short" },
  { label: "Son Tarama", value: "35 sn önce", delta: "Realtime", tone: "accent" }
];

export const signals = [
  {
    symbol: "THYAO",
    market: "BIST",
    strategy: "COMBO",
    direction: "LONG",
    score: 82,
    time: "2024-07-21 11:02"
  },
  {
    symbol: "GARAN",
    market: "BIST",
    strategy: "HUNTER",
    direction: "SHORT",
    score: 91,
    time: "2024-07-21 10:58"
  },
  {
    symbol: "AKBNK",
    market: "BIST",
    strategy: "COMBO",
    direction: "LONG",
    score: 76,
    time: "2024-07-21 10:52"
  },
  {
    symbol: "BTCUSDT",
    market: "Crypto",
    strategy: "HUNTER",
    direction: "LONG",
    score: 88,
    time: "2024-07-21 10:44"
  },
  {
    symbol: "ETHUSDT",
    market: "Crypto",
    strategy: "COMBO",
    direction: "SHORT",
    score: 69,
    time: "2024-07-21 10:40"
  }
];

export const performanceSeries = [
  { name: "Mon", pnl: 42000, trades: 18 },
  { name: "Tue", pnl: 56000, trades: 24 },
  { name: "Wed", pnl: 38000, trades: 16 },
  { name: "Thu", pnl: 72000, trades: 27 },
  { name: "Fri", pnl: 61000, trades: 21 },
  { name: "Sat", pnl: 54000, trades: 19 },
  { name: "Sun", pnl: 68000, trades: 22 }
];

export const healthStats = [
  { label: "CPU", value: 48 },
  { label: "RAM", value: 62 },
  { label: "DB IO", value: 38 }
];

export const logLines = [
  "[11:02:12] Scanner: BIST taraması tamamlandı. 18 sinyal üretildi.",
  "[11:02:10] Risk Manager: THYAO LONG pozisyonu doğrulandı.",
  "[11:01:52] Order Engine: BTCUSDT alış emri gönderildi.",
  "[11:01:35] Strategy HUNTER: RSI < 30 tetiklendi.",
  "[11:01:10] DB: trades tablosu güncellendi."
];
