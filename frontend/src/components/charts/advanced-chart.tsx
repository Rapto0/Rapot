"use client"

import { useEffect, useRef, useState, useCallback } from "react"
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
    Settings,
    ChevronDown,
    X
} from "lucide-react"

// Timeframe options
const TIMEFRAMES = [
    { label: "1G", value: "1d", description: "Günlük" },
    { label: "1H", value: "1wk", description: "Haftalık" },
    { label: "2H", value: "2wk", description: "2 Haftalık" },
    { label: "1A", value: "1mo", description: "Aylık" },
]

// Popular symbols for quick access
const POPULAR_SYMBOLS = [
    { symbol: "THYAO", name: "Türk Hava Yolları", market: "BIST" },
    { symbol: "GARAN", name: "Garanti BBVA", market: "BIST" },
    { symbol: "AKBNK", name: "Akbank", market: "BIST" },
    { symbol: "SASA", name: "SASA Polyester", market: "BIST" },
    { symbol: "BTCUSDT", name: "Bitcoin", market: "Kripto" },
    { symbol: "ETHUSDT", name: "Ethereum", market: "Kripto" },
]

interface ChartPageProps {
    initialSymbol?: string
    initialMarket?: "BIST" | "Kripto"
}

export function AdvancedChartPage({ initialSymbol = "THYAO", initialMarket = "BIST" }: ChartPageProps) {
    const [symbol, setSymbol] = useState(initialSymbol)
    const [marketType, setMarketType] = useState<"BIST" | "Kripto">(initialMarket)
    const [timeframe, setTimeframe] = useState("1d")
    const [showSymbolSearch, setShowSymbolSearch] = useState(false)
    const [searchQuery, setSearchQuery] = useState("")
    const [isFullscreen, setIsFullscreen] = useState(false)

    const chartContainerRef = useRef<HTMLDivElement>(null)
    const chartInstance = useRef<any>(null)
    const seriesInstance = useRef<any>(null)
    const volumeSeriesInstance = useRef<any>(null)

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

    // Live crypto prices
    const cryptoPrices = useBinanceTicker(
        marketType === "Kripto" ? [symbol] : []
    )

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

    // OHLCV of current candle
    const currentCandle = candles.length > 0 ? candles[candles.length - 1] : null

    // Create/update chart
    useEffect(() => {
        if (!chartContainerRef.current) return

        import("lightweight-charts").then(({ createChart, ColorType, CandlestickSeries, HistogramSeries }) => {
            if (!chartContainerRef.current) return

            // Destroy existing chart
            if (chartInstance.current) {
                chartInstance.current.remove()
                chartInstance.current = null
                seriesInstance.current = null
                volumeSeriesInstance.current = null
            }

            const containerWidth = chartContainerRef.current.clientWidth
            const containerHeight = isFullscreen ? window.innerHeight - 120 : 600

            const chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { type: ColorType.Solid, color: "#131722" },
                    textColor: "#d1d4dc",
                },
                grid: {
                    vertLines: { color: "#1e222d" },
                    horzLines: { color: "#1e222d" },
                },
                width: containerWidth,
                height: containerHeight,
                rightPriceScale: {
                    borderColor: "#2a2e39",
                    scaleMargins: {
                        top: 0.1,
                        bottom: 0.2,
                    },
                },
                timeScale: {
                    borderColor: "#2a2e39",
                    timeVisible: true,
                    secondsVisible: false,
                },
                crosshair: {
                    mode: 1,
                    vertLine: {
                        color: "#758696",
                        width: 1,
                        style: 2,
                        labelBackgroundColor: "#2962ff",
                    },
                    horzLine: {
                        color: "#758696",
                        width: 1,
                        style: 2,
                        labelBackgroundColor: "#2962ff",
                    },
                },
            })

            // Candlestick series
            const candlestickSeries = chart.addSeries(CandlestickSeries, {
                upColor: "#089981",
                downColor: "#f23645",
                borderDownColor: "#f23645",
                borderUpColor: "#089981",
                wickDownColor: "#f23645",
                wickUpColor: "#089981",
            })

            // Volume series
            const volumeSeries = chart.addSeries(HistogramSeries, {
                color: "#26a69a",
                priceFormat: {
                    type: "volume",
                },
                priceScaleId: "",
            })

            volumeSeries.priceScale().applyOptions({
                scaleMargins: {
                    top: 0.85,
                    bottom: 0,
                },
            })

            chartInstance.current = chart
            seriesInstance.current = candlestickSeries
            volumeSeriesInstance.current = volumeSeries

            // Handle resize
            const handleResize = () => {
                if (chartContainerRef.current && chartInstance.current) {
                    const newHeight = isFullscreen ? window.innerHeight - 120 : 600
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
                color: item.close >= item.open ? "#089981" : "#f23645",
            }))

            candleData.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())
            volumeData.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())

            try {
                seriesInstance.current.setData(candleData)
                volumeSeriesInstance.current.setData(volumeData)
                chartInstance.current?.timeScale().fitContent()
            } catch (e) {
                console.error("Chart update error:", e)
            }
        }
    }, [candles])

    // Symbol selection
    const handleSymbolSelect = (sym: string, market: "BIST" | "Kripto") => {
        setSymbol(sym)
        setMarketType(market)
        setShowSymbolSearch(false)
        setSearchQuery("")
    }

    // Filter symbols for search
    const filteredSymbols = searchQuery
        ? [...POPULAR_SYMBOLS, ...(bistSymbols?.symbols || []).map(s => ({ symbol: s, name: s, market: "BIST" as const }))].filter(s =>
            s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.name.toLowerCase().includes(searchQuery.toLowerCase())
        ).slice(0, 20)
        : POPULAR_SYMBOLS

    return (
        <div className={cn(
            "flex flex-col bg-[#131722] text-[#d1d4dc]",
            isFullscreen ? "fixed inset-0 z-50" : "min-h-[calc(100vh-4rem)] -m-4"
        )}>
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-[#2a2e39]">
                {/* Symbol Selector */}
                <div className="flex items-center gap-4">
                    <div className="relative">
                        <button
                            onClick={() => setShowSymbolSearch(!showSymbolSearch)}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#1e222d] hover:bg-[#2a2e39] transition-colors"
                        >
                            <span className="text-lg font-bold">{symbol}</span>
                            <span className="text-sm text-[#787b86]">{marketType}</span>
                            <ChevronDown className="h-4 w-4 text-[#787b86]" />
                        </button>

                        {/* Symbol Search Dropdown */}
                        {showSymbolSearch && (
                            <div className="absolute top-full left-0 mt-1 w-80 bg-[#1e222d] border border-[#2a2e39] rounded-lg shadow-xl z-50">
                                <div className="p-2 border-b border-[#2a2e39]">
                                    <div className="relative">
                                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#787b86]" />
                                        <input
                                            type="text"
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            placeholder="Sembol ara..."
                                            className="w-full pl-10 pr-4 py-2 bg-[#131722] border border-[#2a2e39] rounded-lg text-sm focus:outline-none focus:border-[#2962ff]"
                                            autoFocus
                                        />
                                    </div>
                                </div>
                                <div className="max-h-64 overflow-y-auto">
                                    {filteredSymbols.map((s, index) => (
                                        <button
                                            key={`${s.symbol}-${s.market}-${index}`}
                                            onClick={() => handleSymbolSelect(s.symbol, s.market as "BIST" | "Kripto")}
                                            className="w-full flex items-center justify-between px-3 py-2 hover:bg-[#2a2e39] transition-colors"
                                        >
                                            <div className="flex items-center gap-2">
                                                <span className="font-medium">{s.symbol}</span>
                                                <span className="text-sm text-[#787b86]">{s.name}</span>
                                            </div>
                                            <span className={cn(
                                                "text-xs px-2 py-0.5 rounded",
                                                s.market === "BIST" ? "bg-blue-500/20 text-blue-400" : "bg-orange-500/20 text-orange-400"
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
                        <span className="text-2xl font-bold">
                            {marketType === "Kripto" ? "$" : "₺"}
                            {livePrice.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                        <div className={cn(
                            "flex items-center gap-1 px-2 py-1 rounded",
                            isPositive ? "bg-[#089981]/20 text-[#089981]" : "bg-[#f23645]/20 text-[#f23645]"
                        )}>
                            {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                            <span className="font-medium">
                                {isPositive ? "+" : ""}{priceChange.toFixed(2)} ({isPositive ? "+" : ""}{priceChangePercent.toFixed(2)}%)
                            </span>
                        </div>
                    </div>
                </div>

                {/* Timeframe & Controls */}
                <div className="flex items-center gap-2">
                    {/* Timeframes */}
                    <div className="flex items-center bg-[#1e222d] rounded-lg p-1">
                        {TIMEFRAMES.map((tf) => (
                            <button
                                key={tf.value}
                                onClick={() => setTimeframe(tf.value)}
                                className={cn(
                                    "px-3 py-1 rounded text-sm font-medium transition-colors",
                                    timeframe === tf.value
                                        ? "bg-[#2962ff] text-white"
                                        : "text-[#787b86] hover:text-[#d1d4dc]"
                                )}
                                title={tf.description}
                            >
                                {tf.label}
                            </button>
                        ))}
                    </div>

                    {/* Data Source */}
                    <div className="flex items-center gap-2 px-3 py-1 bg-[#1e222d] rounded-lg text-xs text-[#787b86]">
                        <Clock className="h-3 w-3" />
                        <span>{dataSource}</span>
                    </div>

                    {/* Fullscreen */}
                    <button
                        onClick={() => setIsFullscreen(!isFullscreen)}
                        className="p-2 rounded-lg bg-[#1e222d] hover:bg-[#2a2e39] transition-colors"
                    >
                        {isFullscreen ? <X className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                    </button>
                </div>
            </div>

            {/* OHLCV Info Bar */}
            {currentCandle && (
                <div className="flex items-center gap-6 px-4 py-2 border-b border-[#2a2e39] text-sm">
                    <div className="flex items-center gap-2">
                        <span className="text-[#787b86]">A:</span>
                        <span className="font-medium">{currentCandle.open.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-[#787b86]">Y:</span>
                        <span className="font-medium text-[#089981]">{currentCandle.high.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-[#787b86]">D:</span>
                        <span className="font-medium text-[#f23645]">{currentCandle.low.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-[#787b86]">K:</span>
                        <span className="font-medium">{currentCandle.close.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-[#787b86]">H:</span>
                        <span className="font-medium">{(currentCandle.volume / 1000000).toFixed(2)}M</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-[#787b86]">Mum:</span>
                        <span className="font-medium">{candles.length}</span>
                    </div>
                </div>
            )}

            {/* Chart Area */}
            <div className="flex-1 relative">
                {isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-[#131722]/80 z-10">
                        <div className="flex items-center gap-2 text-[#787b86]">
                            <BarChart3 className="h-5 w-5 animate-pulse" />
                            <span>Grafik yükleniyor...</span>
                        </div>
                    </div>
                )}
                <div ref={chartContainerRef} className="w-full h-full" />
            </div>

            {/* Status Bar */}
            <div className="flex items-center justify-between px-4 py-1 border-t border-[#2a2e39] text-xs text-[#787b86]">
                <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-[#089981]"></span>
                        Piyasa Açık
                    </span>
                    <span>{candles.length} mum yüklendi</span>
                </div>
                <div className="flex items-center gap-4">
                    <span>Kaynak: {dataSource}</span>
                    <span>TradingView Lightweight Charts</span>
                </div>
            </div>
        </div>
    )
}
