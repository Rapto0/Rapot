"use client"

import { useEffect, useRef, useState, useCallback, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { fetchCandles, fetchBistSymbols } from "@/lib/api/client"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { cn } from "@/lib/utils"
import {
    Search,
    TrendingUp,
    TrendingDown,
    Clock,
    BarChart3,
    Maximize2,
    Minimize2,
    ChevronDown,
    X,
    Zap,
    PanelRightOpen,
    PanelRightClose,
    LineChart,
    Ruler,
    Pencil,
    Type,
    Settings2,
    ChevronRight,
} from "lucide-react"

// ==================== TYPES ====================

interface SignalMarker {
    time: string
    type: 'AL' | 'SAT'
    price: number
    label?: string
}

// Extended Timeframe options organized by category
const TIMEFRAME_CATEGORIES = [
    {
        category: "Dakika",
        items: [
            { label: "15D", value: "15m", description: "15 Dakika" },
            { label: "30D", value: "30m", description: "30 Dakika" },
        ]
    },
    {
        category: "Saat",
        items: [
            { label: "1S", value: "1h", description: "1 Saat" },
            { label: "2S", value: "2h", description: "2 Saat" },
            { label: "4S", value: "4h", description: "4 Saat" },
            { label: "8S", value: "8h", description: "8 Saat" },
            { label: "12S", value: "12h", description: "12 Saat" },
            { label: "18S", value: "18h", description: "18 Saat" },
        ]
    },
    {
        category: "Gün",
        items: [
            { label: "1G", value: "1d", description: "1 Gün" },
            { label: "2G", value: "2d", description: "2 Gün" },
            { label: "3G", value: "3d", description: "3 Gün" },
            { label: "4G", value: "4d", description: "4 Gün" },
            { label: "5G", value: "5d", description: "5 Gün" },
            { label: "6G", value: "6d", description: "6 Gün" },
        ]
    },
    {
        category: "Hafta",
        items: [
            { label: "1H", value: "1wk", description: "1 Hafta" },
            { label: "2H", value: "2wk", description: "2 Hafta" },
            { label: "3H", value: "3wk", description: "3 Hafta" },
        ]
    },
    {
        category: "Ay",
        items: [
            { label: "1A", value: "1mo", description: "1 Ay" },
            { label: "2A", value: "2mo", description: "2 Ay" },
            { label: "3A", value: "3mo", description: "3 Ay" },
        ]
    },
]

// Quick timeframes for header
const QUICK_TIMEFRAMES = [
    { label: "1S", value: "1h" },
    { label: "4S", value: "4h" },
    { label: "1G", value: "1d" },
    { label: "1H", value: "1wk" },
    { label: "1A", value: "1mo" },
]

// Popular crypto symbols for watchlist
const CRYPTO_WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "SOLUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
    "AVAXUSDT", "LINKUSDT", "ATOMUSDT", "UNIUSDT", "XLMUSDT",
    "VETUSDT", "FILUSDT", "ICPUSDT", "ETCUSDT", "TRXUSDT",
    "NEARUSDT", "ALGOUSDT", "FTMUSDT", "SANDUSDT", "MANAUSDT",
    "AAVEUSDT", "GRTUSDT", "XTZUSDT", "EOSUSDT", "AXSUSDT",
]

// Popular BIST symbols
const BIST_WATCHLIST = [
    { symbol: "THYAO", name: "Türk Hava Yolları" },
    { symbol: "GARAN", name: "Garanti BBVA" },
    { symbol: "AKBNK", name: "Akbank" },
    { symbol: "SASA", name: "SASA Polyester" },
    { symbol: "ASELS", name: "Aselsan" },
    { symbol: "EREGL", name: "Ereğli Demir Çelik" },
    { symbol: "KCHOL", name: "Koç Holding" },
    { symbol: "TUPRS", name: "Tüpraş" },
    { symbol: "SAHOL", name: "Sabancı Holding" },
    { symbol: "BIMAS", name: "BİM Mağazalar" },
]

// ==================== CHART THEME (Cosmic Glass) ====================

const chartColors = {
    background: "transparent",
    text: "#8b949e",
    grid: "rgba(48, 54, 61, 0.3)",
    crosshair: "rgba(0, 242, 234, 0.5)",
    crosshairLabel: "#161b22",
    bullish: "#00c853",
    bearish: "#ff3d00",
    volume: {
        up: "rgba(0, 200, 83, 0.4)",
        down: "rgba(255, 61, 0, 0.4)"
    }
}

interface ChartPageProps {
    initialSymbol?: string
    initialMarket?: "BIST" | "Kripto"
    signals?: SignalMarker[]
    showSignals?: boolean
    showWatchlist?: boolean
}

export function AdvancedChartPage({
    initialSymbol = "THYAO",
    initialMarket = "BIST",
    signals = [],
    showSignals = true,
    showWatchlist = true,
}: ChartPageProps) {
    const [symbol, setSymbol] = useState(initialSymbol)
    const [marketType, setMarketType] = useState<"BIST" | "Kripto">(initialMarket)
    const [timeframe, setTimeframe] = useState("1d")
    const [showSymbolSearch, setShowSymbolSearch] = useState(false)
    const [showTimeframeMenu, setShowTimeframeMenu] = useState(false)
    const [searchQuery, setSearchQuery] = useState("")
    const [isFullscreen, setIsFullscreen] = useState(false)
    const [showRightPanel, setShowRightPanel] = useState(showWatchlist)
    const [rightPanelTab, setRightPanelTab] = useState<"bist" | "kripto">("bist")
    const [crosshairData, setCrosshairData] = useState<{
        time: string
        open: number
        high: number
        low: number
        close: number
        volume: number
    } | null>(null)

    const chartContainerRef = useRef<HTMLDivElement>(null)
    const chartInstance = useRef<any>(null)
    const seriesInstance = useRef<any>(null)
    const volumeSeriesInstance = useRef<any>(null)
    const lastCrosshairTimeRef = useRef<string | null>(null)
    const fullscreenContainerRef = useRef<HTMLDivElement>(null)

    // Fetch candle data
    const { data: candlesResponse, isLoading, refetch } = useQuery({
        queryKey: ['chart-candles', symbol, marketType, timeframe],
        queryFn: () => fetchCandles(symbol, marketType, timeframe, 1000),
        refetchInterval: 60000,
    })

    // Fetch BIST symbols for search
    const { data: bistSymbols } = useQuery({
        queryKey: ['bist-symbols'],
        queryFn: fetchBistSymbols,
        staleTime: 300000,
    })

    // Fetch all Binance USDT pairs
    const { data: binanceSymbols } = useQuery({
        queryKey: ['binance-symbols'],
        queryFn: async () => {
            const res = await fetch('https://api.binance.com/api/v3/exchangeInfo')
            const data = await res.json()
            return data.symbols
                .filter((s: any) => s.quoteAsset === 'USDT' && s.status === 'TRADING')
                .map((s: any) => s.symbol)
                .sort()
        },
        staleTime: 3600000, // 1 hour
    })

    // Live crypto prices for watchlist
    const watchlistCryptoSymbols = useMemo(() => {
        if (rightPanelTab === "kripto") {
            return CRYPTO_WATCHLIST.slice(0, 20)
        }
        return marketType === "Kripto" ? [symbol] : []
    }, [rightPanelTab, marketType, symbol])

    const cryptoPrices = useBinanceTicker(watchlistCryptoSymbols)

    const candles = candlesResponse?.candles || []
    const dataSource = candlesResponse?.source || "loading"

    // Calculate price info
    const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0
    const prevPrice = candles.length > 1 ? candles[candles.length - 2].close : currentPrice
    const priceChange = currentPrice - prevPrice
    const priceChangePercent = prevPrice > 0 ? (priceChange / prevPrice) * 100 : 0
    const isPositive = priceChange >= 0

    // Live price for crypto
    const livePrice = marketType === "Kripto" && cryptoPrices[symbol]
        ? cryptoPrices[symbol].price
        : currentPrice

    // OHLCV display data (crosshair or current candle)
    const displayOHLCV = crosshairData || (candles.length > 0 ? candles[candles.length - 1] : null)

    // Handle fullscreen toggle with browser API
    const toggleFullscreen = useCallback(() => {
        if (!document.fullscreenElement) {
            fullscreenContainerRef.current?.requestFullscreen?.()
            setIsFullscreen(true)
        } else {
            document.exitFullscreen?.()
            setIsFullscreen(false)
        }
    }, [])

    // Listen for fullscreen change
    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement)
        }
        document.addEventListener('fullscreenchange', handleFullscreenChange)
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
    }, [])

    // Create/update chart
    useEffect(() => {
        if (!chartContainerRef.current) return

        import("lightweight-charts").then(({ createChart, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries }) => {
            if (!chartContainerRef.current) return

            // Destroy existing chart
            if (chartInstance.current) {
                chartInstance.current.remove()
                chartInstance.current = null
                seriesInstance.current = null
                volumeSeriesInstance.current = null
            }

            const containerWidth = chartContainerRef.current.clientWidth
            const containerHeight = isFullscreen ? window.innerHeight - 120 : 500

            const chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { type: ColorType.Solid, color: chartColors.background },
                    textColor: chartColors.text,
                    fontSize: 12,
                },
                grid: {
                    vertLines: { color: chartColors.grid },
                    horzLines: { color: chartColors.grid },
                },
                width: containerWidth,
                height: containerHeight,
                rightPriceScale: {
                    borderColor: chartColors.grid,
                    scaleMargins: { top: 0.1, bottom: 0.2 },
                },
                timeScale: {
                    borderColor: chartColors.grid,
                    timeVisible: true,
                    secondsVisible: false,
                },
                crosshair: {
                    mode: CrosshairMode.Normal,
                    vertLine: {
                        color: chartColors.crosshair,
                        width: 1,
                        style: 0,
                        labelBackgroundColor: chartColors.crosshairLabel,
                    },
                    horzLine: {
                        color: chartColors.crosshair,
                        width: 1,
                        style: 0,
                        labelBackgroundColor: chartColors.crosshairLabel,
                    },
                },
                handleScroll: {
                    mouseWheel: true,
                    pressedMouseMove: true,
                    horzTouchDrag: true,
                    vertTouchDrag: true,
                },
                handleScale: {
                    axisPressedMouseMove: true,
                    mouseWheel: true,
                    pinch: true,
                },
            })

            // Candlestick series
            const candlestickSeries = chart.addSeries(CandlestickSeries, {
                upColor: chartColors.bullish,
                downColor: chartColors.bearish,
                borderDownColor: chartColors.bearish,
                borderUpColor: chartColors.bullish,
                wickDownColor: chartColors.bearish,
                wickUpColor: chartColors.bullish,
            })

            // Volume series
            const volumeSeries = chart.addSeries(HistogramSeries, {
                color: chartColors.volume.up,
                priceFormat: { type: "volume" },
                priceScaleId: "",
            })

            volumeSeries.priceScale().applyOptions({
                scaleMargins: { top: 0.85, bottom: 0 },
            })

            // Crosshair move handler (throttled to prevent infinite loops)
            chart.subscribeCrosshairMove((param) => {
                if (!param.time || !param.seriesData.size) {
                    if (lastCrosshairTimeRef.current !== null) {
                        lastCrosshairTimeRef.current = null
                        setCrosshairData(null)
                    }
                    return
                }

                const timeStr = param.time.toString()
                if (timeStr === lastCrosshairTimeRef.current) {
                    return
                }

                const candleData = param.seriesData.get(candlestickSeries)
                if (candleData && 'open' in candleData) {
                    lastCrosshairTimeRef.current = timeStr
                    setCrosshairData({
                        time: timeStr,
                        open: candleData.open,
                        high: candleData.high,
                        low: candleData.low,
                        close: candleData.close,
                        volume: 0,
                    })
                }
            })

            chartInstance.current = chart
            seriesInstance.current = candlestickSeries
            volumeSeriesInstance.current = volumeSeries

            // Handle resize
            const handleResize = () => {
                if (chartContainerRef.current && chartInstance.current) {
                    const newHeight = isFullscreen ? window.innerHeight - 120 : 500
                    chartInstance.current.applyOptions({
                        width: chartContainerRef.current.clientWidth,
                        height: newHeight,
                    })
                }
            }
            window.addEventListener("resize", handleResize)

            return () => {
                window.removeEventListener("resize", handleResize)
            }
        })
    }, [isFullscreen])

    // Update chart data
    useEffect(() => {
        if (candles.length > 0 && seriesInstance.current && volumeSeriesInstance.current) {
            const candleData = candles.map((item) => ({
                time: item.time,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }))

            const volumeData = candles.map((item) => ({
                time: item.time,
                value: item.volume,
                color: item.close >= item.open ? chartColors.volume.up : chartColors.volume.down,
            }))

            candleData.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
            volumeData.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())

            try {
                seriesInstance.current.setData(candleData)
                volumeSeriesInstance.current.setData(volumeData)

                // Add signal markers
                if (showSignals && signals.length > 0) {
                    const markers = signals.map((signal) => ({
                        time: signal.time,
                        position: signal.type === 'AL' ? 'belowBar' : 'aboveBar',
                        shape: signal.type === 'AL' ? 'arrowUp' : 'arrowDown',
                        color: signal.type === 'AL' ? chartColors.bullish : chartColors.bearish,
                        text: signal.type,
                        size: 2,
                    }))
                    seriesInstance.current.setMarkers(markers)
                }

                chartInstance.current?.timeScale().fitContent()
            } catch (e) {
                console.error("Chart update error:", e)
            }
        }
    }, [candles, signals, showSignals])

    // Symbol selection
    const handleSymbolSelect = (sym: string, market: "BIST" | "Kripto") => {
        setSymbol(sym)
        setMarketType(market)
        setShowSymbolSearch(false)
        setSearchQuery("")
    }

    // Get current timeframe label
    const currentTimeframeLabel = useMemo(() => {
        for (const cat of TIMEFRAME_CATEGORIES) {
            const found = cat.items.find(tf => tf.value === timeframe)
            if (found) return found.label
        }
        return timeframe
    }, [timeframe])

    // Filter symbols for search
    const filteredSymbols = useMemo(() => {
        const bistList = (bistSymbols?.symbols || []).map(s => ({
            symbol: s,
            name: s,
            market: "BIST" as const
        }))

        const cryptoList = (binanceSymbols || CRYPTO_WATCHLIST).map(s => ({
            symbol: s,
            name: s.replace('USDT', ''),
            market: "Kripto" as const
        }))

        const allSymbols = [...bistList, ...cryptoList]

        if (!searchQuery) {
            return allSymbols.slice(0, 30)
        }

        return allSymbols.filter(s =>
            s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.name.toLowerCase().includes(searchQuery.toLowerCase())
        ).slice(0, 30)
    }, [searchQuery, bistSymbols, binanceSymbols])

    return (
        <div
            ref={fullscreenContainerRef}
            className={cn(
                "flex rounded-xl overflow-hidden bg-background",
                "glass-panel-intense",
                isFullscreen ? "fixed inset-0 z-50 rounded-none" : ""
            )}
        >
            {/* Main Chart Area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border/30">
                    {/* Symbol Selector */}
                    <div className="flex items-center gap-4">
                        <div className="relative">
                            <button
                                onClick={() => setShowSymbolSearch(!showSymbolSearch)}
                                className={cn(
                                    "flex items-center gap-2 px-4 py-2 rounded-lg transition-all",
                                    "bg-card/50 hover:bg-card border border-border/50 hover:border-primary/30"
                                )}
                            >
                                <BarChart3 className="h-4 w-4 text-primary" />
                                <span className="text-lg font-bold">{symbol}</span>
                                <span className={cn(
                                    "text-xs px-2 py-0.5 rounded-full font-medium",
                                    marketType === "BIST"
                                        ? "bg-primary/20 text-primary"
                                        : "bg-orange-500/20 text-orange-400"
                                )}>
                                    {marketType}
                                </span>
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            </button>

                            {/* Symbol Search Dropdown */}
                            {showSymbolSearch && (
                                <div className="absolute top-full left-0 mt-2 w-96 glass-panel shadow-xl z-50 overflow-hidden">
                                    <div className="p-3 border-b border-border/30">
                                        <div className="relative">
                                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                            <input
                                                type="text"
                                                value={searchQuery}
                                                onChange={(e) => setSearchQuery(e.target.value)}
                                                placeholder="Sembol ara... (BTCUSDT, THYAO, vb.)"
                                                className="w-full pl-10 pr-4 py-2 bg-background/50 border border-border/50 rounded-lg text-sm focus:outline-none focus:border-primary/50 placeholder:text-muted-foreground"
                                                autoFocus
                                            />
                                        </div>
                                    </div>
                                    <div className="max-h-80 overflow-y-auto">
                                        {filteredSymbols.map((s, index) => (
                                            <button
                                                key={`${s.symbol}-${s.market}-${index}`}
                                                onClick={() => handleSymbolSelect(s.symbol, s.market)}
                                                className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-muted/30 transition-colors"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <span className={cn(
                                                        "w-2 h-2 rounded-full",
                                                        s.market === "BIST" ? "bg-primary" : "bg-orange-500"
                                                    )} />
                                                    <span className="font-medium">{s.symbol}</span>
                                                    <span className="text-sm text-muted-foreground">{s.name}</span>
                                                </div>
                                                <span className={cn(
                                                    "text-xs px-2 py-0.5 rounded-full",
                                                    s.market === "BIST"
                                                        ? "bg-primary/10 text-primary"
                                                        : "bg-orange-500/10 text-orange-400"
                                                )}>
                                                    {s.market}
                                                </span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Price Info */}
                        <div className="flex items-center gap-4">
                            <div className="flex flex-col">
                                <span className="text-2xl font-bold mono-numbers">
                                    {marketType === "Kripto" ? "$" : "₺"}
                                    {livePrice.toLocaleString("tr-TR", {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: marketType === "Kripto" ? 4 : 2
                                    })}
                                </span>
                                <div className={cn(
                                    "flex items-center gap-1.5 text-sm",
                                    isPositive ? "text-profit" : "text-loss"
                                )}>
                                    {isPositive ? (
                                        <TrendingUp className="h-4 w-4" />
                                    ) : (
                                        <TrendingDown className="h-4 w-4" />
                                    )}
                                    <span className="font-medium mono-numbers">
                                        {isPositive ? "+" : ""}{priceChange.toFixed(2)}
                                    </span>
                                    <span className="mono-numbers">
                                        ({isPositive ? "+" : ""}{priceChangePercent.toFixed(2)}%)
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Timeframe & Controls */}
                    <div className="flex items-center gap-3">
                        {/* Quick Timeframes */}
                        <div className="flex items-center bg-muted/30 rounded-lg p-1">
                            {QUICK_TIMEFRAMES.map((tf) => (
                                <button
                                    key={tf.value}
                                    onClick={() => setTimeframe(tf.value)}
                                    className={cn(
                                        "px-3 py-1.5 rounded-md text-sm font-medium transition-all",
                                        timeframe === tf.value
                                            ? "bg-primary/20 text-primary neon-text"
                                            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                    )}
                                >
                                    {tf.label}
                                </button>
                            ))}

                            {/* More Timeframes Dropdown */}
                            <div className="relative">
                                <button
                                    onClick={() => setShowTimeframeMenu(!showTimeframeMenu)}
                                    className={cn(
                                        "px-2 py-1.5 rounded-md text-sm font-medium transition-all",
                                        "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                    )}
                                >
                                    <ChevronDown className="h-4 w-4" />
                                </button>

                                {showTimeframeMenu && (
                                    <div className="absolute top-full right-0 mt-2 w-64 glass-panel shadow-xl z-50 overflow-hidden">
                                        {TIMEFRAME_CATEGORIES.map((cat) => (
                                            <div key={cat.category}>
                                                <div className="px-3 py-2 text-xs font-semibold text-muted-foreground bg-muted/30">
                                                    {cat.category}
                                                </div>
                                                <div className="grid grid-cols-3 gap-1 p-2">
                                                    {cat.items.map((tf) => (
                                                        <button
                                                            key={tf.value}
                                                            onClick={() => {
                                                                setTimeframe(tf.value)
                                                                setShowTimeframeMenu(false)
                                                            }}
                                                            className={cn(
                                                                "px-2 py-1.5 rounded text-sm font-medium transition-all",
                                                                timeframe === tf.value
                                                                    ? "bg-primary/20 text-primary"
                                                                    : "hover:bg-muted/50"
                                                            )}
                                                            title={tf.description}
                                                        >
                                                            {tf.label}
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Tools - Coming Soon */}
                        <div className="flex items-center gap-1 bg-muted/30 rounded-lg p-1">
                            <button
                                className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all"
                                title="İndikatörler (Yakında)"
                            >
                                <LineChart className="h-4 w-4" />
                            </button>
                            <button
                                className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all"
                                title="Ölçüm Cetveli (Yakında)"
                            >
                                <Ruler className="h-4 w-4" />
                            </button>
                            <button
                                className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all"
                                title="Çizim Araçları (Yakında)"
                            >
                                <Pencil className="h-4 w-4" />
                            </button>
                            <button
                                className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-all"
                                title="Metin Ekle (Yakında)"
                            >
                                <Type className="h-4 w-4" />
                            </button>
                        </div>

                        {/* Data Source */}
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/30 rounded-lg text-xs">
                            <Zap className="h-3 w-3 text-primary animate-pulse" />
                            <span className="text-muted-foreground">{dataSource}</span>
                        </div>

                        {/* Watchlist Toggle */}
                        <button
                            onClick={() => setShowRightPanel(!showRightPanel)}
                            className={cn(
                                "p-2 rounded-lg transition-all",
                                "bg-muted/30 hover:bg-muted/50",
                                showRightPanel && "text-primary"
                            )}
                            title={showRightPanel ? "Paneli Gizle" : "Paneli Göster"}
                        >
                            {showRightPanel ? (
                                <PanelRightClose className="h-4 w-4" />
                            ) : (
                                <PanelRightOpen className="h-4 w-4" />
                            )}
                        </button>

                        {/* Fullscreen */}
                        <button
                            onClick={toggleFullscreen}
                            className={cn(
                                "p-2 rounded-lg transition-all",
                                "bg-muted/30 hover:bg-muted/50 hover:text-primary"
                            )}
                            title={isFullscreen ? "Küçült" : "Tam Ekran"}
                        >
                            {isFullscreen ? (
                                <Minimize2 className="h-4 w-4" />
                            ) : (
                                <Maximize2 className="h-4 w-4" />
                            )}
                        </button>
                    </div>
                </div>

                {/* OHLCV Info Bar */}
                {displayOHLCV && (
                    <div className="flex items-center gap-6 px-4 py-2 border-b border-border/30 bg-muted/10">
                        <div className="flex items-center gap-6 text-sm">
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs uppercase">Açılış</span>
                                <span className="font-medium mono-numbers">{displayOHLCV.open.toFixed(2)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs uppercase">Yüksek</span>
                                <span className="font-medium mono-numbers text-profit">{displayOHLCV.high.toFixed(2)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs uppercase">Düşük</span>
                                <span className="font-medium mono-numbers text-loss">{displayOHLCV.low.toFixed(2)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs uppercase">Kapanış</span>
                                <span className={cn(
                                    "font-medium mono-numbers",
                                    displayOHLCV.close >= displayOHLCV.open ? "text-profit" : "text-loss"
                                )}>
                                    {displayOHLCV.close.toFixed(2)}
                                </span>
                            </div>
                        </div>
                        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span>{crosshairData ? crosshairData.time : 'Son Mum'}</span>
                        </div>
                    </div>
                )}

                {/* Chart Area */}
                <div className="flex-1 relative min-h-[400px]">
                    {isLoading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-10">
                            <div className="flex flex-col items-center gap-3">
                                <div className="w-10 h-10 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                                <span className="text-sm text-muted-foreground">Grafik yükleniyor...</span>
                            </div>
                        </div>
                    )}
                    <div ref={chartContainerRef} className="w-full h-full" />
                </div>

                {/* Status Bar */}
                <div className="flex items-center justify-between px-4 py-2 border-t border-border/30 text-xs text-muted-foreground">
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full bg-profit animate-pulse" />
                            Canlı
                        </span>
                        <span>{candles.length} mum</span>
                        <span>Periyot: {currentTimeframeLabel}</span>
                        {showSignals && signals.length > 0 && (
                            <span className="flex items-center gap-1">
                                <Zap className="h-3 w-3 text-primary" />
                                {signals.length} sinyal
                            </span>
                        )}
                    </div>
                    <div className="flex items-center gap-4">
                        <span>Kaynak: {dataSource}</span>
                        <span className="text-primary/60">TradingView Charts</span>
                    </div>
                </div>
            </div>

            {/* Right Panel - Watchlist */}
            {showRightPanel && (
                <div className="w-64 border-l border-border/30 flex flex-col bg-card/30">
                    {/* Panel Header */}
                    <div className="flex items-center border-b border-border/30">
                        <button
                            onClick={() => setRightPanelTab("bist")}
                            className={cn(
                                "flex-1 px-4 py-3 text-sm font-medium transition-all",
                                rightPanelTab === "bist"
                                    ? "text-primary border-b-2 border-primary bg-primary/5"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            BIST
                        </button>
                        <button
                            onClick={() => setRightPanelTab("kripto")}
                            className={cn(
                                "flex-1 px-4 py-3 text-sm font-medium transition-all",
                                rightPanelTab === "kripto"
                                    ? "text-orange-400 border-b-2 border-orange-400 bg-orange-500/5"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            Kripto
                        </button>
                    </div>

                    {/* Panel Content */}
                    <div className="flex-1 overflow-y-auto">
                        {rightPanelTab === "bist" ? (
                            <div className="divide-y divide-border/20">
                                {BIST_WATCHLIST.map((item) => (
                                    <button
                                        key={item.symbol}
                                        onClick={() => handleSymbolSelect(item.symbol, "BIST")}
                                        className={cn(
                                            "w-full flex items-center justify-between px-4 py-3 hover:bg-muted/30 transition-colors",
                                            symbol === item.symbol && marketType === "BIST" && "bg-primary/10"
                                        )}
                                    >
                                        <div className="text-left">
                                            <div className="font-medium text-sm">{item.symbol}</div>
                                            <div className="text-xs text-muted-foreground truncate max-w-[120px]">{item.name}</div>
                                        </div>
                                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className="divide-y divide-border/20">
                                {CRYPTO_WATCHLIST.map((sym) => {
                                    const price = cryptoPrices[sym]
                                    return (
                                        <button
                                            key={sym}
                                            onClick={() => handleSymbolSelect(sym, "Kripto")}
                                            className={cn(
                                                "w-full flex items-center justify-between px-4 py-3 hover:bg-muted/30 transition-colors",
                                                symbol === sym && marketType === "Kripto" && "bg-orange-500/10"
                                            )}
                                        >
                                            <div className="text-left">
                                                <div className="font-medium text-sm">{sym.replace('USDT', '')}</div>
                                                <div className="text-xs text-muted-foreground">{sym}</div>
                                            </div>
                                            <div className="text-right">
                                                {price ? (
                                                    <>
                                                        <div className="font-medium text-sm mono-numbers">
                                                            ${price.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                                                        </div>
                                                        <div className={cn(
                                                            "text-xs mono-numbers",
                                                            price.change >= 0 ? "text-profit" : "text-loss"
                                                        )}>
                                                            {price.change >= 0 ? "+" : ""}{price.change.toFixed(2)}%
                                                        </div>
                                                    </>
                                                ) : (
                                                    <div className="text-xs text-muted-foreground">--</div>
                                                )}
                                            </div>
                                        </button>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

export default AdvancedChartPage
