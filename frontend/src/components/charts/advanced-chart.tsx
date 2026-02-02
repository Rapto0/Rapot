"use client"

import { useEffect, useRef, useState, useCallback, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { fetchCandles, fetchBistSymbols, fetchTicker } from "@/lib/api/client"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { cn } from "@/lib/utils"
import {
    calculateRSI,
    calculateMACD,
    calculateWilliamsR,
    calculateCCI,
    calculateCombo,
    calculateHunter,
    AVAILABLE_INDICATORS,
    type Candle,
    type IndicatorMeta,
} from "@/lib/indicators"
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
    Plus,
    RefreshCw,
    MoreHorizontal,
    Trash2,
} from "lucide-react"

// ==================== TYPES ====================

interface SignalMarker {
    time: string
    type: 'AL' | 'SAT'
    price: number
    label?: string
}

interface ActiveIndicator {
    id: string
    meta: IndicatorMeta
    params: Record<string, number>
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
        ]
    },
    {
        category: "Gün",
        items: [
            { label: "1G", value: "1d", description: "1 Gün" },
            { label: "2G", value: "2d", description: "2 Gün" },
            { label: "3G", value: "3d", description: "3 Gün" },
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
    },
    indicators: {
        rsi: "#2962ff",
        macd: "#f23645",
        macdSignal: "#089981",
        macdHistogram: "#787b86",
        wr: "#9c27b0",
        cci: "#ff9800",
    }
}

// Helper to format date for Lightweight Charts (yyyy-mm-dd only)
const formatTime = (timeStr: string): string => {
    if (timeStr.includes(' ')) {
        return timeStr.split(' ')[0]
    }
    return timeStr
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
    // Basic state
    const [symbol, setSymbol] = useState(initialSymbol)
    const [marketType, setMarketType] = useState<"BIST" | "Kripto">(initialMarket)
    const [timeframe, setTimeframe] = useState("1d")
    const [showSymbolSearch, setShowSymbolSearch] = useState(false)
    const [showTimeframeMenu, setShowTimeframeMenu] = useState(false)
    const [searchQuery, setSearchQuery] = useState("")
    const [isFullscreen, setIsFullscreen] = useState(false)
    const [showRightPanel, setShowRightPanel] = useState(showWatchlist)

    // Indicator state
    const [showIndicatorSearch, setShowIndicatorSearch] = useState(false)
    const [indicatorSearchQuery, setIndicatorSearchQuery] = useState("")
    const [activeIndicators, setActiveIndicators] = useState<ActiveIndicator[]>([])

    // Drawing tools state
    const [activeTool, setActiveTool] = useState<'none' | 'ruler' | 'pencil' | 'text'>('none')

    // Chart ready state
    const [chartReady, setChartReady] = useState(false)

    // Crosshair data
    const [crosshairData, setCrosshairData] = useState<{
        time: string
        open: number
        high: number
        low: number
        close: number
        volume: number
    } | null>(null)

    // Refs
    const chartContainerRef = useRef<HTMLDivElement>(null)
    const chartInstance = useRef<any>(null)
    const seriesInstance = useRef<any>(null)
    const volumeSeriesInstance = useRef<any>(null)
    const lastCrosshairTimeRef = useRef<string | null>(null)
    const fullscreenContainerRef = useRef<HTMLDivElement>(null)

    // Fetch candle data
    const { data: candlesResponse, isLoading } = useQuery({
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
        staleTime: 3600000,
    })

    // Fetch BIST tickers for watchlist
    const { data: bistTickers, refetch: refetchTickers } = useQuery({
        queryKey: ['watchlist-ticker'],
        queryFn: fetchTicker,
        refetchInterval: 30000,
    })

    // Live crypto prices for watchlist
    const cryptoPrices = useBinanceTicker(CRYPTO_WATCHLIST)

    const candles: Candle[] = candlesResponse?.candles || []
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

    // OHLCV display data
    const displayOHLCV = crosshairData || (candles.length > 0 ? candles[candles.length - 1] : null)

    // Handle fullscreen toggle
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
                setChartReady(false)
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

            // Crosshair move handler
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
            setChartReady(true)

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
        if (!chartReady || candles.length === 0 || !seriesInstance.current || !volumeSeriesInstance.current) return

            const candleData = candles.map((item) => ({
                time: formatTime(item.time),
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }))

            const volumeData = candles.map((item) => ({
                time: formatTime(item.time),
                value: item.volume,
                color: item.close >= item.open ? chartColors.volume.up : chartColors.volume.down,
            }))

            candleData.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
            volumeData.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())

            try {
                seriesInstance.current.setData(candleData)
                volumeSeriesInstance.current.setData(volumeData)

                // Add signal markers (including Combo/Hunter overlays)
                const markers: any[] = []

                // Original signals
                if (showSignals && signals.length > 0) {
                    signals.forEach((signal) => {
                        markers.push({
                            time: formatTime(signal.time),
                            position: signal.type === 'AL' ? 'belowBar' : 'aboveBar',
                            shape: signal.type === 'AL' ? 'arrowUp' : 'arrowDown',
                            color: signal.type === 'AL' ? chartColors.bullish : chartColors.bearish,
                            text: signal.type,
                            size: 2,
                        })
                    })
                }

                // Combo overlay markers
                if (activeIndicators.some(i => i.id === 'combo')) {
                    const comboSignals = calculateCombo(candles)
                    comboSignals.forEach((sig) => {
                        if (sig.signal) {
                            markers.push({
                                time: formatTime(sig.time),
                                position: sig.signal === 'AL' ? 'belowBar' : 'aboveBar',
                                shape: sig.signal === 'AL' ? 'arrowUp' : 'arrowDown',
                                color: sig.signal === 'AL' ? '#00e676' : '#ff5252',
                                text: `COMBO`,
                                size: 2,
                            })
                        }
                    })
                }

                // Hunter overlay markers
                if (activeIndicators.some(i => i.id === 'hunter')) {
                    const hunterSignals = calculateHunter(candles)
                    hunterSignals.forEach((sig) => {
                        if (sig.signal) {
                            markers.push({
                                time: formatTime(sig.time),
                                position: sig.signal === 'AL' ? 'belowBar' : 'aboveBar',
                                shape: 'circle',
                                color: sig.signal === 'AL' ? '#76ff03' : '#ff1744',
                                text: `HUNTER`,
                                size: 2,
                            })
                        }
                    })
                }

                if (markers.length > 0 && typeof seriesInstance.current.setMarkers === 'function') {
                    seriesInstance.current.setMarkers(markers)
                } else if (markers.length === 0 && typeof seriesInstance.current.setMarkers === 'function') {
                    // Clear markers if none
                    seriesInstance.current.setMarkers([])
                }

                chartInstance.current?.timeScale().fitContent()
            } catch (e) {
                console.error("Chart update error:", e)
            }
    }, [candles, signals, showSignals, activeIndicators, chartReady])

    // Add indicator
    const addIndicator = useCallback((indicatorId: string) => {
        const meta = AVAILABLE_INDICATORS.find(i => i.id === indicatorId)
        if (!meta) return
        if (activeIndicators.some(i => i.id === indicatorId)) return

        setActiveIndicators(prev => [...prev, {
            id: indicatorId,
            meta,
            params: { ...meta.defaultParams }
        }])
        setShowIndicatorSearch(false)
        setIndicatorSearchQuery("")
    }, [activeIndicators])

    // Remove indicator
    const removeIndicator = useCallback((indicatorId: string) => {
        setActiveIndicators(prev => prev.filter(i => i.id !== indicatorId))
    }, [])

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
            symbol: s, name: s, market: "BIST" as const
        }))
        const cryptoList = (binanceSymbols || CRYPTO_WATCHLIST).map((s: string) => ({
            symbol: s, name: s.replace('USDT', ''), market: "Kripto" as const
        }))
        const allSymbols = [...bistList, ...cryptoList]
        if (!searchQuery) return allSymbols.slice(0, 30)
        return allSymbols.filter(s =>
            s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.name.toLowerCase().includes(searchQuery.toLowerCase())
        ).slice(0, 30)
    }, [searchQuery, bistSymbols, binanceSymbols])

    // Filter indicators for search
    const filteredIndicators = useMemo(() => {
        if (!indicatorSearchQuery) return AVAILABLE_INDICATORS
        return AVAILABLE_INDICATORS.filter(i =>
            i.name.toLowerCase().includes(indicatorSearchQuery.toLowerCase()) ||
            i.shortName.toLowerCase().includes(indicatorSearchQuery.toLowerCase())
        )
    }, [indicatorSearchQuery])

    // Merged watchlist data
    const watchlistData = useMemo(() => {
        const cryptoData = CRYPTO_WATCHLIST.map(sym => ({
            symbol: sym.replace("USDT", "/USD"),
            rawSymbol: sym,
            price: cryptoPrices[sym]?.price?.toFixed(2) || "---",
            change: cryptoPrices[sym]?.change || 0,
            type: "Kripto" as const
        }))
        const bistData = (bistTickers || []).map(t => ({
            symbol: t.symbol,
            rawSymbol: t.symbol,
            price: t.price?.toFixed(2) || "---",
            change: t.changePercent || 0,
            type: "BIST" as const
        }))
        return [...cryptoData, ...bistData]
    }, [cryptoPrices, bistTickers])

    return (
        <div
            ref={fullscreenContainerRef}
            className={cn(
                "flex rounded-xl overflow-hidden bg-background glass-panel-intense",
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
                                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-card/50 hover:bg-card border border-border/50 hover:border-primary/30 transition-all"
                            >
                                <BarChart3 className="h-4 w-4 text-primary" />
                                <span className="text-lg font-bold">{symbol}</span>
                                <span className={cn(
                                    "text-xs px-2 py-0.5 rounded-full font-medium",
                                    marketType === "BIST" ? "bg-primary/20 text-primary" : "bg-orange-500/20 text-orange-400"
                                )}>{marketType}</span>
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            </button>

                            {showSymbolSearch && (
                                <div className="absolute top-full left-0 mt-2 w-96 glass-panel shadow-xl z-50 overflow-hidden">
                                    <div className="p-3 border-b border-border/30">
                                        <div className="relative">
                                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                            <input
                                                type="text"
                                                value={searchQuery}
                                                onChange={(e) => setSearchQuery(e.target.value)}
                                                placeholder="Sembol ara..."
                                                className="w-full pl-10 pr-4 py-2 bg-background/50 border border-border/50 rounded-lg text-sm focus:outline-none focus:border-primary/50"
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
                                                    <span className={cn("w-2 h-2 rounded-full", s.market === "BIST" ? "bg-primary" : "bg-orange-500")} />
                                                    <span className="font-medium">{s.symbol}</span>
                                                </div>
                                                <span className={cn("text-xs px-2 py-0.5 rounded-full", s.market === "BIST" ? "bg-primary/10 text-primary" : "bg-orange-500/10 text-orange-400")}>{s.market}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Price Info */}
                        <div className="flex flex-col">
                            <span className="text-2xl font-bold mono-numbers">
                                {marketType === "Kripto" ? "$" : "₺"}
                                {livePrice.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: marketType === "Kripto" ? 4 : 2 })}
                            </span>
                            <div className={cn("flex items-center gap-1.5 text-sm", isPositive ? "text-profit" : "text-loss")}>
                                {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                                <span className="font-medium mono-numbers">{isPositive ? "+" : ""}{priceChange.toFixed(2)}</span>
                                <span className="mono-numbers">({isPositive ? "+" : ""}{priceChangePercent.toFixed(2)}%)</span>
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
                                        timeframe === tf.value ? "bg-primary/20 text-primary neon-text" : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                    )}
                                >{tf.label}</button>
                            ))}
                            <div className="relative">
                                <button onClick={() => setShowTimeframeMenu(!showTimeframeMenu)} className="px-2 py-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50">
                                    <ChevronDown className="h-4 w-4" />
                                </button>
                                {showTimeframeMenu && (
                                    <div className="absolute top-full right-0 mt-2 w-64 glass-panel shadow-xl z-50 overflow-hidden">
                                        {TIMEFRAME_CATEGORIES.map((cat) => (
                                            <div key={cat.category}>
                                                <div className="px-3 py-2 text-xs font-semibold text-muted-foreground bg-muted/30">{cat.category}</div>
                                                <div className="grid grid-cols-3 gap-1 p-2">
                                                    {cat.items.map((tf) => (
                                                        <button
                                                            key={tf.value}
                                                            onClick={() => { setTimeframe(tf.value); setShowTimeframeMenu(false) }}
                                                            className={cn("px-2 py-1.5 rounded text-sm font-medium transition-all", timeframe === tf.value ? "bg-primary/20 text-primary" : "hover:bg-muted/50")}
                                                            title={tf.description}
                                                        >{tf.label}</button>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Tools */}
                        <div className="flex items-center gap-1 bg-muted/30 rounded-lg p-1">
                            <div className="relative">
                                <button
                                    onClick={() => setShowIndicatorSearch(!showIndicatorSearch)}
                                    className={cn("p-2 rounded-md transition-all", activeIndicators.length > 0 ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")}
                                    title="İndikatörler"
                                >
                                    <LineChart className="h-4 w-4" />
                                </button>
                                {showIndicatorSearch && (
                                    <div className="absolute top-full right-0 mt-2 w-80 glass-panel shadow-xl z-50 overflow-hidden">
                                        <div className="p-3 border-b border-border/30">
                                            <div className="relative">
                                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                                <input type="text" value={indicatorSearchQuery} onChange={(e) => setIndicatorSearchQuery(e.target.value)} placeholder="İndikatör ara..." className="w-full pl-10 pr-4 py-2 bg-background/50 border border-border/50 rounded-lg text-sm focus:outline-none focus:border-primary/50" autoFocus />
                                            </div>
                                        </div>
                                        {activeIndicators.length > 0 && (
                                            <div className="p-2 border-b border-border/30">
                                                <div className="text-xs text-muted-foreground mb-2 px-2">Aktif İndikatörler</div>
                                                {activeIndicators.map((ind) => (
                                                    <div key={ind.id} className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-muted/30">
                                                        <span className="text-sm font-medium">{ind.meta.shortName}</span>
                                                        <button onClick={() => removeIndicator(ind.id)} className="text-muted-foreground hover:text-loss"><Trash2 className="h-4 w-4" /></button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        <div className="max-h-60 overflow-y-auto p-2">
                                            {filteredIndicators.map((ind) => (
                                                <button
                                                    key={ind.id}
                                                    onClick={() => addIndicator(ind.id)}
                                                    disabled={activeIndicators.some(i => i.id === ind.id)}
                                                    className={cn("w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors text-left", activeIndicators.some(i => i.id === ind.id) ? "opacity-50 cursor-not-allowed bg-muted/20" : "hover:bg-muted/30")}
                                                >
                                                    <div>
                                                        <div className="font-medium text-sm">{ind.shortName}</div>
                                                        <div className="text-xs text-muted-foreground">{ind.description}</div>
                                                    </div>
                                                    {ind.isOverlay && <span className="text-xs px-2 py-0.5 rounded bg-secondary/20 text-secondary">Overlay</span>}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                            <button onClick={() => setActiveTool(activeTool === 'ruler' ? 'none' : 'ruler')} className={cn("p-2 rounded-md transition-all", activeTool === 'ruler' ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")} title="Ölçüm Cetveli"><Ruler className="h-4 w-4" /></button>
                            <button onClick={() => setActiveTool(activeTool === 'pencil' ? 'none' : 'pencil')} className={cn("p-2 rounded-md transition-all", activeTool === 'pencil' ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")} title="Çizim Araçları"><Pencil className="h-4 w-4" /></button>
                            <button onClick={() => setActiveTool(activeTool === 'text' ? 'none' : 'text')} className={cn("p-2 rounded-md transition-all", activeTool === 'text' ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")} title="Metin Ekle"><Type className="h-4 w-4" /></button>
                        </div>

                        <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/30 rounded-lg text-xs">
                            <Zap className="h-3 w-3 text-primary animate-pulse" />
                            <span className="text-muted-foreground">{dataSource}</span>
                        </div>

                        <button onClick={() => setShowRightPanel(!showRightPanel)} className={cn("p-2 rounded-lg transition-all bg-muted/30 hover:bg-muted/50", showRightPanel && "text-primary")} title={showRightPanel ? "Paneli Gizle" : "Paneli Göster"}>
                            {showRightPanel ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
                        </button>

                        <button onClick={toggleFullscreen} className="p-2 rounded-lg bg-muted/30 hover:bg-muted/50 hover:text-primary transition-all" title={isFullscreen ? "Küçült" : "Tam Ekran"}>
                            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
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
                                <span className={cn("font-medium mono-numbers", displayOHLCV.close >= displayOHLCV.open ? "text-profit" : "text-loss")}>{displayOHLCV.close.toFixed(2)}</span>
                            </div>
                        </div>
                        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span>{crosshairData ? crosshairData.time : 'Son Mum'}</span>
                        </div>
                    </div>
                )}

                {/* Active Tool Info */}
                {activeTool !== 'none' && (
                    <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary text-sm">
                        {activeTool === 'ruler' && "Ölçüm modu aktif. Grafikte iki nokta seçin."}
                        {activeTool === 'pencil' && "Çizim modu aktif. Grafikte serbest çizim yapabilirsiniz."}
                        {activeTool === 'text' && "Metin modu aktif. Grafikte bir noktaya tıklayarak metin ekleyin."}
                        <button onClick={() => setActiveTool('none')} className="ml-auto hover:text-white"><X className="h-4 w-4" /></button>
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

                {/* Indicator Panels */}
                {activeIndicators.filter(i => !i.meta.isOverlay).map((ind) => (
                    <IndicatorPane key={ind.id} indicator={ind} candles={candles} onRemove={() => removeIndicator(ind.id)} />
                ))}

                {/* Status Bar */}
                <div className="flex items-center justify-between px-4 py-2 border-t border-border/30 text-xs text-muted-foreground">
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-profit animate-pulse" />Canlı</span>
                        <span>{candles.length} mum</span>
                        <span>Periyot: {currentTimeframeLabel}</span>
                        {activeIndicators.length > 0 && <span className="flex items-center gap-1"><LineChart className="h-3 w-3 text-primary" />{activeIndicators.length} indikatör</span>}
                    </div>
                    <div className="flex items-center gap-4">
                        <span>Kaynak: {dataSource}</span>
                        <span className="text-primary/60">TradingView Charts</span>
                    </div>
                </div>
            </div>

            {/* Right Panel - Watchlist (TradingView Style) */}
            {showRightPanel && (
                <div className="w-[280px] border-l border-border/30 flex flex-col bg-[#131722]">
                    <div className="flex items-center justify-between px-3 py-2 border-b border-border/30">
                        <span className="text-sm font-medium">İzleme Listesi</span>
                        <div className="flex items-center gap-1">
                            <button onClick={() => refetchTickers()} className="flex h-6 w-6 items-center justify-center rounded hover:bg-muted/30 text-muted-foreground"><RefreshCw className="h-4 w-4" /></button>
                            <button className="flex h-6 w-6 items-center justify-center rounded hover:bg-muted/30 text-muted-foreground"><Plus className="h-4 w-4" /></button>
                            <button className="flex h-6 w-6 items-center justify-center rounded hover:bg-muted/30 text-muted-foreground"><MoreHorizontal className="h-4 w-4" /></button>
                        </div>
                    </div>
                    <div className="flex-1 overflow-y-auto">
                        {watchlistData.map((item, index) => (
                            <button
                                key={`${item.symbol}-${index}`}
                                onClick={() => handleSymbolSelect(item.rawSymbol, item.type)}
                                className={cn("w-full flex items-center justify-between px-3 py-2 hover:bg-muted/30 transition-colors", symbol === item.rawSymbol && "bg-primary/10")}
                            >
                                <div className="flex flex-col text-left">
                                    <span className="text-sm font-medium">{item.symbol}</span>
                                    <span className="text-xs text-muted-foreground">{item.type}</span>
                                </div>
                                <div className="text-right">
                                    <div className="text-sm font-mono tabular-nums">{item.price}</div>
                                    <div className={cn("text-xs font-mono tabular-nums", item.change >= 0 ? "text-profit" : "text-loss")}>{item.change >= 0 ? "+" : ""}{item.change.toFixed(2)}%</div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

// ==================== INDICATOR PANE COMPONENT ====================

interface IndicatorPaneProps {
    indicator: ActiveIndicator
    candles: Candle[]
    onRemove: () => void
}

function IndicatorPane({ indicator, candles, onRemove }: IndicatorPaneProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<any>(null)

    useEffect(() => {
        if (!containerRef.current || candles.length === 0) return

        import("lightweight-charts").then(({ createChart, ColorType, LineSeries, HistogramSeries }) => {
            if (!containerRef.current) return

            if (chartRef.current) {
                chartRef.current.remove()
            }

            const chart = createChart(containerRef.current, {
                layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#8b949e', fontSize: 10 },
                grid: { vertLines: { color: 'rgba(48, 54, 61, 0.3)' }, horzLines: { color: 'rgba(48, 54, 61, 0.3)' } },
                width: containerRef.current.clientWidth,
                height: 100,
                rightPriceScale: { borderColor: 'rgba(48, 54, 61, 0.3)' },
                timeScale: { visible: false },
                handleScroll: { mouseWheel: true, pressedMouseMove: true },
                handleScale: { mouseWheel: true },
            })

            if (indicator.id === 'rsi') {
                const rsiData = calculateRSI(candles, indicator.params.period || 14)
                const series = chart.addSeries(LineSeries, { color: chartColors.indicators.rsi, lineWidth: 2, priceScaleId: 'right' })
                series.setData(rsiData.filter(d => !isNaN(d.value)).map(d => ({ time: formatTime(d.time), value: d.value })))
            } else if (indicator.id === 'macd') {
                const macdData = calculateMACD(candles)
                const macdSeries = chart.addSeries(LineSeries, { color: chartColors.indicators.macd, lineWidth: 2 })
                macdSeries.setData(macdData.filter(d => !isNaN(d.macd)).map(d => ({ time: formatTime(d.time), value: d.macd })))
                const signalSeries = chart.addSeries(LineSeries, { color: chartColors.indicators.macdSignal, lineWidth: 2 })
                signalSeries.setData(macdData.filter(d => !isNaN(d.signal)).map(d => ({ time: formatTime(d.time), value: d.signal })))
                const histSeries = chart.addSeries(HistogramSeries, { color: chartColors.indicators.macdHistogram })
                histSeries.setData(macdData.filter(d => !isNaN(d.histogram)).map(d => ({ time: formatTime(d.time), value: d.histogram, color: d.histogram >= 0 ? 'rgba(0, 200, 83, 0.5)' : 'rgba(255, 61, 0, 0.5)' })))
            } else if (indicator.id === 'wr') {
                const wrData = calculateWilliamsR(candles, indicator.params.period || 14)
                const series = chart.addSeries(LineSeries, { color: chartColors.indicators.wr, lineWidth: 2 })
                series.setData(wrData.filter(d => !isNaN(d.value)).map(d => ({ time: formatTime(d.time), value: d.value })))
            } else if (indicator.id === 'cci') {
                const cciData = calculateCCI(candles, indicator.params.period || 20)
                const series = chart.addSeries(LineSeries, { color: chartColors.indicators.cci, lineWidth: 2 })
                series.setData(cciData.filter(d => !isNaN(d.value)).map(d => ({ time: formatTime(d.time), value: d.value })))
            }

            chart.timeScale().fitContent()
            chartRef.current = chart

            const handleResize = () => {
                if (containerRef.current && chartRef.current) {
                    chartRef.current.applyOptions({ width: containerRef.current.clientWidth })
                }
            }
            window.addEventListener('resize', handleResize)
            return () => window.removeEventListener('resize', handleResize)
        })
    }, [indicator, candles])

    return (
        <div className="border-t border-border/30">
            <div className="flex items-center justify-between px-4 py-1 bg-muted/10">
                <span className="text-xs font-medium text-muted-foreground">{indicator.meta.shortName}</span>
                <button onClick={onRemove} className="text-muted-foreground hover:text-loss"><X className="h-3 w-3" /></button>
            </div>
            <div ref={containerRef} className="w-full h-[100px]" />
        </div>
    )
}

export default AdvancedChartPage
