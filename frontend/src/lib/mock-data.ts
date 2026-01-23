// Mock Data for Rapot Dashboard
// Realistic financial data for BIST and Crypto markets

export interface Signal {
    id: number
    symbol: string
    marketType: "BIST" | "Kripto"
    strategy: "COMBO" | "HUNTER"
    signalType: "AL" | "SAT"
    timeframe: string
    score: string
    price: number
    createdAt: string
}

export interface Trade {
    id: number
    symbol: string
    marketType: "BIST" | "Kripto"
    direction: "BUY" | "SELL"
    entryPrice: number
    currentPrice: number
    quantity: number
    pnl: number
    pnlPercent: number
    status: "OPEN" | "CLOSED" | "CANCELLED"
    createdAt: string
    closedAt?: string
}

export interface CandlestickData {
    time: string
    open: number
    high: number
    low: number
    close: number
    volume: number
}

export interface MarketTicker {
    symbol: string
    name: string
    price: number
    change: number
    changePercent: number
}

export interface BotHealth {
    cpuUsage: number
    memoryUsage: number
    uptime: string
    lastScan: string
    totalScans: number
    activeSymbols: number
    apiStatus: "healthy" | "degraded" | "down"
}

export interface LogEntry {
    id: number
    timestamp: string
    level: "INFO" | "WARNING" | "ERROR"
    message: string
}

// ===== MARKET TICKERS =====
export const marketTickers: MarketTicker[] = [
    { symbol: "XU100", name: "BIST 100", price: 9847.52, change: 127.35, changePercent: 1.31 },
    { symbol: "BTCUSDT", name: "Bitcoin", price: 97234.50, change: 2150.25, changePercent: 2.26 },
    { symbol: "ETHUSDT", name: "Ethereum", price: 3456.78, change: -45.32, changePercent: -1.29 },
    { symbol: "THYAO", name: "THY", price: 312.40, change: 8.60, changePercent: 2.83 },
    { symbol: "GARAN", name: "Garanti", price: 127.80, change: -2.40, changePercent: -1.84 },
    { symbol: "SISE", name: "Şişecam", price: 56.45, change: 1.25, changePercent: 2.27 },
    { symbol: "SOLUSDT", name: "Solana", price: 198.45, change: 12.30, changePercent: 6.61 },
    { symbol: "ASELS", name: "Aselsan", price: 89.20, change: 3.15, changePercent: 3.66 },
]

// ===== SIGNALS =====
export const mockSignals: Signal[] = [
    { id: 1, symbol: "THYAO", marketType: "BIST", strategy: "COMBO", signalType: "AL", timeframe: "GÜNLÜK", score: "+4/-0", price: 304.50, createdAt: "2026-01-22T19:45:00" },
    { id: 2, symbol: "BTCUSDT", marketType: "Kripto", strategy: "HUNTER", signalType: "AL", timeframe: "4 SAATLİK", score: "12/15", price: 95100.00, createdAt: "2026-01-22T19:30:00" },
    { id: 3, symbol: "GARAN", marketType: "BIST", strategy: "HUNTER", signalType: "SAT", timeframe: "GÜNLÜK", score: "11/15", price: 130.20, createdAt: "2026-01-22T18:15:00" },
    { id: 4, symbol: "ASELS", marketType: "BIST", strategy: "COMBO", signalType: "AL", timeframe: "1 HAFTALIK", score: "+3/-1", price: 86.05, createdAt: "2026-01-22T17:00:00" },
    { id: 5, symbol: "ETHUSDT", marketType: "Kripto", strategy: "COMBO", signalType: "SAT", timeframe: "GÜNLÜK", score: "+2/-3", price: 3502.10, createdAt: "2026-01-22T16:45:00" },
    { id: 6, symbol: "SISE", marketType: "BIST", strategy: "HUNTER", signalType: "AL", timeframe: "GÜNLÜK", score: "13/15", price: 55.20, createdAt: "2026-01-22T15:30:00" },
    { id: 7, symbol: "SOLUSDT", marketType: "Kripto", strategy: "HUNTER", signalType: "AL", timeframe: "4 SAATLİK", score: "14/15", price: 186.15, createdAt: "2026-01-22T14:00:00" },
    { id: 8, symbol: "TUPRS", marketType: "BIST", strategy: "COMBO", signalType: "AL", timeframe: "GÜNLÜK", score: "+4/-0", price: 178.30, createdAt: "2026-01-22T13:15:00" },
    { id: 9, symbol: "EREGL", marketType: "BIST", strategy: "COMBO", signalType: "SAT", timeframe: "2 HAFTALIK", score: "+1/-4", price: 62.80, createdAt: "2026-01-22T12:00:00" },
    { id: 10, symbol: "AVAXUSDT", marketType: "Kripto", strategy: "HUNTER", signalType: "AL", timeframe: "1 SAATLİK", score: "10/15", price: 38.45, createdAt: "2026-01-22T11:30:00" },
]

// ===== TRADES =====
export const mockTrades: Trade[] = [
    { id: 1, symbol: "THYAO", marketType: "BIST", direction: "BUY", entryPrice: 298.20, currentPrice: 312.40, quantity: 100, pnl: 1420, pnlPercent: 4.76, status: "OPEN", createdAt: "2026-01-20T09:30:00" },
    { id: 2, symbol: "BTCUSDT", marketType: "Kripto", direction: "BUY", entryPrice: 94500, currentPrice: 97234.50, quantity: 0.5, pnl: 1367.25, pnlPercent: 2.89, status: "OPEN", createdAt: "2026-01-19T14:00:00" },
    { id: 3, symbol: "GARAN", marketType: "BIST", direction: "SELL", entryPrice: 131.50, currentPrice: 127.80, quantity: 200, pnl: 740, pnlPercent: 2.81, status: "OPEN", createdAt: "2026-01-21T10:15:00" },
    { id: 4, symbol: "ASELS", marketType: "BIST", direction: "BUY", entryPrice: 82.30, currentPrice: 89.20, quantity: 150, pnl: 1035, pnlPercent: 8.38, status: "CLOSED", createdAt: "2026-01-15T11:00:00", closedAt: "2026-01-22T16:30:00" },
    { id: 5, symbol: "SOLUSDT", marketType: "Kripto", direction: "BUY", entryPrice: 175.80, currentPrice: 198.45, quantity: 10, pnl: 226.50, pnlPercent: 12.88, status: "OPEN", createdAt: "2026-01-18T08:45:00" },
]

// ===== CANDLESTICK DATA (THYAO - Last 50 candles) =====
// Using deterministic values to avoid SSR hydration mismatch
export const mockCandlestickData: CandlestickData[] = [
    { time: "2025-12-04", open: 280.00, high: 284.20, low: 278.50, close: 282.15, volume: 2500000 },
    { time: "2025-12-05", open: 282.15, high: 285.80, low: 281.00, close: 284.50, volume: 2800000 },
    { time: "2025-12-06", open: 284.50, high: 286.40, low: 282.20, close: 283.00, volume: 2200000 },
    { time: "2025-12-07", open: 283.00, high: 287.50, low: 282.80, close: 286.75, volume: 3100000 },
    { time: "2025-12-08", open: 286.75, high: 289.00, low: 285.50, close: 288.20, volume: 2900000 },
    { time: "2025-12-09", open: 288.20, high: 290.50, low: 286.00, close: 287.10, volume: 2400000 },
    { time: "2025-12-10", open: 287.10, high: 288.80, low: 284.50, close: 285.60, volume: 2600000 },
    { time: "2025-12-11", open: 285.60, high: 289.20, low: 285.00, close: 288.45, volume: 2750000 },
    { time: "2025-12-12", open: 288.45, high: 292.00, low: 287.80, close: 291.30, volume: 3200000 },
    { time: "2025-12-13", open: 291.30, high: 293.50, low: 289.00, close: 290.20, volume: 2850000 },
    { time: "2025-12-14", open: 290.20, high: 291.80, low: 287.50, close: 288.90, volume: 2300000 },
    { time: "2025-12-15", open: 288.90, high: 292.40, low: 288.00, close: 291.75, volume: 2650000 },
    { time: "2025-12-16", open: 291.75, high: 295.00, low: 290.50, close: 294.10, volume: 3400000 },
    { time: "2025-12-17", open: 294.10, high: 296.80, low: 292.20, close: 293.50, volume: 2900000 },
    { time: "2025-12-18", open: 293.50, high: 295.20, low: 291.00, close: 292.80, volume: 2500000 },
    { time: "2025-12-19", open: 292.80, high: 296.50, low: 292.00, close: 295.90, volume: 3100000 },
    { time: "2025-12-20", open: 295.90, high: 298.40, low: 294.50, close: 297.25, volume: 3350000 },
    { time: "2025-12-21", open: 297.25, high: 299.00, low: 295.80, close: 296.40, volume: 2700000 },
    { time: "2025-12-22", open: 296.40, high: 298.60, low: 294.20, close: 295.10, volume: 2450000 },
    { time: "2025-12-23", open: 295.10, high: 297.80, low: 294.00, close: 297.50, volume: 2600000 },
    { time: "2025-12-24", open: 297.50, high: 300.20, low: 296.80, close: 299.80, volume: 3200000 },
    { time: "2025-12-25", open: 299.80, high: 302.50, low: 298.50, close: 301.20, volume: 2100000 },
    { time: "2025-12-26", open: 301.20, high: 303.80, low: 299.90, close: 300.50, volume: 2350000 },
    { time: "2025-12-27", open: 300.50, high: 302.40, low: 298.20, close: 299.10, volume: 2500000 },
    { time: "2025-12-28", open: 299.10, high: 301.80, low: 298.00, close: 301.40, volume: 2700000 },
    { time: "2025-12-29", open: 301.40, high: 304.50, low: 300.80, close: 303.90, volume: 3000000 },
    { time: "2025-12-30", open: 303.90, high: 306.20, low: 302.50, close: 305.10, volume: 3250000 },
    { time: "2025-12-31", open: 305.10, high: 307.00, low: 303.80, close: 304.20, volume: 2400000 },
    { time: "2026-01-01", open: 304.20, high: 306.50, low: 303.00, close: 305.80, volume: 1800000 },
    { time: "2026-01-02", open: 305.80, high: 308.40, low: 304.50, close: 307.60, volume: 2900000 },
    { time: "2026-01-03", open: 307.60, high: 310.00, low: 306.20, close: 308.90, volume: 3100000 },
    { time: "2026-01-04", open: 308.90, high: 311.50, low: 307.80, close: 310.40, volume: 3300000 },
    { time: "2026-01-05", open: 310.40, high: 312.80, low: 308.90, close: 309.50, volume: 2800000 },
    { time: "2026-01-06", open: 309.50, high: 311.20, low: 307.00, close: 308.20, volume: 2600000 },
    { time: "2026-01-07", open: 308.20, high: 310.80, low: 307.50, close: 310.10, volume: 2750000 },
    { time: "2026-01-08", open: 310.10, high: 313.00, low: 309.20, close: 312.40, volume: 3400000 },
    { time: "2026-01-09", open: 312.40, high: 315.20, low: 311.00, close: 313.80, volume: 3550000 },
    { time: "2026-01-10", open: 313.80, high: 316.00, low: 312.50, close: 314.60, volume: 3200000 },
    { time: "2026-01-11", open: 314.60, high: 316.80, low: 313.20, close: 315.90, volume: 2950000 },
    { time: "2026-01-12", open: 315.90, high: 318.50, low: 314.80, close: 317.20, volume: 3100000 },
    { time: "2026-01-13", open: 317.20, high: 319.00, low: 315.50, close: 316.40, volume: 2800000 },
    { time: "2026-01-14", open: 316.40, high: 318.20, low: 314.00, close: 315.10, volume: 2650000 },
    { time: "2026-01-15", open: 315.10, high: 317.50, low: 313.80, close: 316.80, volume: 2900000 },
    { time: "2026-01-16", open: 316.80, high: 319.40, low: 315.60, close: 318.50, volume: 3150000 },
    { time: "2026-01-17", open: 318.50, high: 321.00, low: 317.20, close: 319.80, volume: 3350000 },
    { time: "2026-01-18", open: 319.80, high: 322.50, low: 318.50, close: 321.40, volume: 3500000 },
    { time: "2026-01-19", open: 321.40, high: 323.80, low: 319.90, close: 320.50, volume: 3100000 },
    { time: "2026-01-20", open: 320.50, high: 322.00, low: 318.00, close: 319.20, volume: 2850000 },
    { time: "2026-01-21", open: 319.20, high: 321.50, low: 317.80, close: 320.80, volume: 3000000 },
    { time: "2026-01-22", open: 320.80, high: 323.00, low: 319.50, close: 312.40, volume: 3200000 },
]

// ===== BOT HEALTH =====
export const mockBotHealth: BotHealth = {
    cpuUsage: 23.5,
    memoryUsage: 45.2,
    uptime: "3 gün 14 saat 27 dk",
    lastScan: "2026-01-22T20:08:19",
    totalScans: 847,
    activeSymbols: 595,
    apiStatus: "healthy"
}

// ===== LOG ENTRIES =====
export const mockLogs: LogEntry[] = [
    { id: 1, timestamp: "2026-01-22T20:08:50", level: "INFO", message: "Tarama #847 tamamlandı - 595 hisse tarandı, 7 sinyal bulundu" },
    { id: 2, timestamp: "2026-01-22T20:08:23", level: "INFO", message: "BIST: MIATK >>> COMBO AL: MIATK GÜNLÜK" },
    { id: 3, timestamp: "2026-01-22T20:08:22", level: "INFO", message: "BIST: OTTO >>> HUNTER DİP: OTTO 2 HAFTALIK" },
    { id: 4, timestamp: "2026-01-22T20:08:21", level: "WARNING", message: "BIST retry 2/3 for LYDHO: No data was fetched" },
    { id: 5, timestamp: "2026-01-22T20:08:20", level: "INFO", message: "BIST: UFUK >>> COMBO AL: UFUK GÜNLÜK" },
    { id: 6, timestamp: "2026-01-22T20:08:19", level: "INFO", message: "🚀 Bot Başlatılıyor... (🔄 Sync Mode)" },
    { id: 7, timestamp: "2026-01-22T20:08:19", level: "INFO", message: "Health API başlatıldı: http://0.0.0.0:5000" },
    { id: 8, timestamp: "2026-01-22T19:38:15", level: "ERROR", message: "API rate limit aşıldı, 60 saniye bekleniyor..." },
    { id: 9, timestamp: "2026-01-22T19:08:19", level: "INFO", message: "Tarama #846 tamamlandı - 595 hisse tarandı, 4 sinyal bulundu" },
    { id: 10, timestamp: "2026-01-22T18:38:19", level: "INFO", message: "Tarama #845 tamamlandı - 595 hisse tarandı, 6 sinyal bulundu" },
]

// ===== KPI STATS =====
export const mockKPIStats = {
    totalPnL: 4788.75,
    totalPnLPercent: 5.23,
    winRate: 73.5,
    openPositions: 4,
    closedPositions: 12,
    totalTrades: 16,
    lastScanTime: "2026-01-22T20:08:50",
    totalSignals: 847,
    todaySignals: 23,
}

// ===== SCAN HISTORY =====
export const mockScanHistory = [
    { id: 847, scanType: "BIST", symbolsScanned: 595, signalsFound: 7, duration: 31.2, createdAt: "2026-01-22T20:08:50" },
    { id: 846, scanType: "BIST", symbolsScanned: 595, signalsFound: 4, duration: 28.5, createdAt: "2026-01-22T19:08:19" },
    { id: 845, scanType: "Kripto", symbolsScanned: 150, signalsFound: 6, duration: 12.3, createdAt: "2026-01-22T18:38:19" },
    { id: 844, scanType: "BIST", symbolsScanned: 595, signalsFound: 3, duration: 29.8, createdAt: "2026-01-22T18:08:19" },
    { id: 843, scanType: "BIST", symbolsScanned: 595, signalsFound: 5, duration: 30.1, createdAt: "2026-01-22T17:08:19" },
]

// ===== MARKET OVERVIEW DATA =====
export const marketOverviewData = {
    bist: [
        { time: "09:00", value: 9720 },
        { time: "10:00", value: 9745 },
        { time: "11:00", value: 9780 },
        { time: "12:00", value: 9810 },
        { time: "13:00", value: 9790 },
        { time: "14:00", value: 9825 },
        { time: "15:00", value: 9848 },
    ],
    crypto: [
        { time: "00:00", value: 95100 },
        { time: "04:00", value: 95800 },
        { time: "08:00", value: 96200 },
        { time: "12:00", value: 96800 },
        { time: "16:00", value: 96500 },
        { time: "20:00", value: 97234 },
    ]
}
