"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { fetchTicker, fetchSignals, transformSignal } from "@/lib/api/client"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { cn } from "@/lib/utils"
import { Bell, RefreshCw, TrendingUp, TrendingDown } from "lucide-react"
import { useEffect, useState, useRef } from "react"

// Crypto symbols to track via WebSocket
const CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

export function Header() {
    const queryClient = useQueryClient()
    const [currentTime, setCurrentTime] = useState<string>("")
    const [newSignalCount, setNewSignalCount] = useState(0)
    const [showNotification, setShowNotification] = useState(false)
    const lastSignalIdRef = useRef<number | null>(null)

    // Live Binance WebSocket prices
    const cryptoPrices = useBinanceTicker(CRYPTO_SYMBOLS)

    // BIST prices from API (faster polling - 15 seconds)
    const { data: apiTickers, refetch } = useQuery({
        queryKey: ['ticker'],
        queryFn: fetchTicker,
        refetchInterval: 15000, // 15 saniye
        initialData: []
    })

    // Poll signals for new notification count (every 30 seconds)
    const { data: signals } = useQuery({
        queryKey: ['signals', 'header'],
        queryFn: () => fetchSignals({ limit: 5 }),
        refetchInterval: 30000,
        select: (data) => data.map(transformSignal)
    })

    // Check for new signals
    useEffect(() => {
        if (signals && signals.length > 0) {
            const latestId = signals[0].id
            if (lastSignalIdRef.current !== null && latestId > lastSignalIdRef.current) {
                const newCount = signals.filter(s => s.id > lastSignalIdRef.current!).length
                setNewSignalCount(prev => prev + newCount)
                setShowNotification(true)
                setTimeout(() => setShowNotification(false), 3000)
            }
            lastSignalIdRef.current = latestId
        }
    }, [signals])

    // Time update
    useEffect(() => {
        const updateTime = () => {
            setCurrentTime(
                new Date().toLocaleTimeString("tr-TR", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                })
            )
        }
        updateTime()
        const interval = setInterval(updateTime, 1000)
        return () => clearInterval(interval)
    }, [])

    // Merge API tickers with live WebSocket crypto data
    const mergedTickers = (apiTickers || []).map(ticker => {
        // Check if this is a crypto symbol we're tracking
        const cryptoSymbol = CRYPTO_SYMBOLS.find(s =>
            ticker.name.toUpperCase().includes(s.replace("USDT", ""))
        )
        if (cryptoSymbol && cryptoPrices[cryptoSymbol]) {
            return {
                ...ticker,
                price: cryptoPrices[cryptoSymbol].price,
                changePercent: cryptoPrices[cryptoSymbol].change
            }
        }
        return ticker
    })

    const handleRefresh = () => {
        refetch()
        queryClient.invalidateQueries({ queryKey: ['signals'] })
    }

    const handleNotificationClick = () => {
        setNewSignalCount(0)
    }

    return (
        <header className="fixed top-0 right-0 left-0 md:left-56 z-30 h-14 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 hidden md:block">
            <div className="flex h-full items-center justify-between px-4">
                {/* Ticker Tape */}
                <div className="relative flex-1 overflow-hidden">
                    <div className="flex animate-ticker whitespace-nowrap">
                        {mergedTickers && [...mergedTickers, ...mergedTickers].map((ticker, index) => (
                            <TickerItem key={`${ticker.symbol}-${index}`} ticker={ticker} />
                        ))}
                    </div>
                </div>

                {/* Right Side */}
                <div className="flex items-center gap-4 pl-4">
                    {/* Live Time */}
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <div className="relative">
                            <div className="h-2 w-2 rounded-full bg-profit" />
                            <div className="absolute inset-0 h-2 w-2 animate-ping rounded-full bg-profit opacity-75" />
                        </div>
                        <span className="font-mono">{currentTime}</span>
                    </div>

                    {/* Refresh Button */}
                    <button
                        onClick={handleRefresh}
                        className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                    >
                        <RefreshCw className="h-4 w-4" />
                    </button>

                    {/* Notifications */}
                    <button
                        onClick={handleNotificationClick}
                        className={cn(
                            "relative flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors",
                            showNotification && "animate-bounce"
                        )}
                    >
                        <Bell className={cn("h-4 w-4", showNotification && "text-primary")} />
                        {newSignalCount > 0 && (
                            <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-white">
                                {newSignalCount > 9 ? "9+" : newSignalCount}
                            </span>
                        )}
                    </button>
                </div>
            </div>

            {/* New Signal Toast */}
            {showNotification && signals && signals.length > 0 && (
                <div className="absolute top-16 right-4 bg-card border border-border rounded-lg shadow-lg p-3 animate-in slide-in-from-top-2 z-50">
                    <div className="flex items-center gap-2">
                        {signals[0].signalType === "AL" ? (
                            <TrendingUp className="h-4 w-4 text-profit" />
                        ) : (
                            <TrendingDown className="h-4 w-4 text-loss" />
                        )}
                        <span className="text-sm font-medium">
                            Yeni sinyal: {signals[0].symbol} - {signals[0].signalType}
                        </span>
                    </div>
                </div>
            )}
        </header>
    )
}

interface TickerItemProps {
    ticker: {
        symbol: string
        name: string
        price: number
        change: number
        changePercent: number
    }
}

function TickerItem({ ticker }: TickerItemProps) {
    const isPositive = ticker.changePercent >= 0

    return (
        <div className="flex items-center gap-4 px-6 border-r border-border/50">
            <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">
                    {ticker.symbol}
                </span>
                <span className="text-sm text-muted-foreground">{ticker.name}</span>
            </div>
            <div className="flex items-center gap-2">
                <span className="text-sm font-mono font-medium text-foreground">
                    {ticker.price.toLocaleString("tr-TR", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                    })}
                </span>
                <span
                    className={cn(
                        "text-xs font-medium",
                        isPositive ? "text-profit" : "text-loss"
                    )}
                >
                    {isPositive ? "+" : ""}
                    {ticker.changePercent.toFixed(2)}%
                </span>
            </div>
        </div>
    )
}
