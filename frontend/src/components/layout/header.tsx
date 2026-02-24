"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { fetchTicker, fetchSignals, transformSignal } from "@/lib/api/client"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { cn } from "@/lib/utils"
import { Bell, RefreshCw, TrendingUp, TrendingDown, X } from "lucide-react"
import { useEffect, useState, useRef } from "react"
import Link from "next/link"
import { useSidebar } from "./sidebar-context"

// Crypto symbols to track via WebSocket
const CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

// LocalStorage key for read signal IDs
const READ_SIGNALS_KEY = "rapot_read_signal_ids"

export function Header() {
    const queryClient = useQueryClient()
    const [currentTime, setCurrentTime] = useState<string>("")
    const [showNotificationPanel, setShowNotificationPanel] = useState(false)
    const [readSignalIds, setReadSignalIds] = useState<Set<number>>(new Set())
    const notificationRef = useRef<HTMLDivElement>(null)
    const { isPinned } = useSidebar()

    // Live Binance WebSocket prices
    const cryptoPrices = useBinanceTicker(CRYPTO_SYMBOLS)

    // BIST prices from API
    const { data: apiTickers, refetch } = useQuery({
        queryKey: ['ticker'],
        queryFn: fetchTicker,
        refetchInterval: 60000,
        initialData: []
    })

    // Poll signals for notifications (every 30 seconds, get last 30)
    const { data: signals } = useQuery({
        queryKey: ['signals', 'notifications'],
        queryFn: () => fetchSignals({ limit: 30 }),
        refetchInterval: 30000,
        select: (data) => data.map(transformSignal)
    })

    // Load read signal IDs from localStorage
    useEffect(() => {
        const stored = localStorage.getItem(READ_SIGNALS_KEY)
        if (stored) {
            try {
                const ids = JSON.parse(stored)
                setReadSignalIds(new Set(ids))
            } catch {
                // Ignore parse errors
            }
        }
    }, [])

    // Save read signal IDs to localStorage
    const markSignalsAsRead = (ids: number[]) => {
        setReadSignalIds(prev => {
            const newSet = new Set([...prev, ...ids])
            localStorage.setItem(READ_SIGNALS_KEY, JSON.stringify([...newSet]))
            return newSet
        })
    }

    // Calculate unread count
    const unreadSignals = signals?.filter(s => !readSignalIds.has(s.id)) || []
    const unreadCount = unreadSignals.length

    // Handle notification panel toggle
    const handleNotificationClick = () => {
        setShowNotificationPanel(prev => !prev)
    }

    // Mark all visible signals as read when panel opens
    const handleMarkAllRead = () => {
        if (signals) {
            markSignalsAsRead(signals.map(s => s.id))
        }
    }

    // Close panel when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
                setShowNotificationPanel(false)
            }
        }
        document.addEventListener("mousedown", handleClickOutside)
        return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])

    // Time update - every 10 seconds to reduce re-renders
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
        const interval = setInterval(updateTime, 10000)
        return () => clearInterval(interval)
    }, [])

    // Merge API tickers with live WebSocket crypto data
    const mergedTickers = (apiTickers || []).map(ticker => {
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

    return (
        <header className={cn(
            "fixed top-0 right-0 left-0 z-50 h-14 border-b border-border bg-background backdrop-blur supports-[backdrop-filter]:bg-background/95 hidden md:block transition-all duration-300",
            isPinned ? "md:left-56" : "md:left-16"
        )}>
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
                        title="Verileri Yenile"
                    >
                        <RefreshCw className="h-4 w-4" />
                    </button>

                    {/* Notifications */}
                    <div ref={notificationRef} className="relative">
                        <button
                            onClick={handleNotificationClick}
                            className={cn(
                                "relative flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors",
                                showNotificationPanel && "bg-accent text-foreground"
                            )}
                            title="Bildirimler"
                        >
                            <Bell className={cn("h-4 w-4", unreadCount > 0 && "text-primary")} />
                            {unreadCount > 0 && (
                                <span className="absolute -top-0.5 -right-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-white">
                                    {unreadCount > 99 ? "99+" : unreadCount}
                                </span>
                            )}
                        </button>

                        {/* Notification Panel */}
                        {showNotificationPanel && (
                            <div className="absolute top-10 right-0 w-80 bg-card border border-border rounded-lg shadow-xl z-50 overflow-hidden">
                                {/* Header */}
                                <div className="flex items-center justify-between p-3 border-b border-border bg-muted/30">
                                    <span className="text-sm font-semibold">
                                        Sinyaller {unreadCount > 0 && `(${unreadCount} yeni)`}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        {unreadCount > 0 && (
                                            <button
                                                onClick={handleMarkAllRead}
                                                className="text-xs text-primary hover:underline"
                                            >
                                                Tümünü Okundu İşaretle
                                            </button>
                                        )}
                                        <button
                                            onClick={() => setShowNotificationPanel(false)}
                                            className="text-muted-foreground hover:text-foreground"
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    </div>
                                </div>

                                {/* Signal List */}
                                <div className="max-h-96 overflow-y-auto">
                                    {signals && signals.length > 0 ? (
                                        signals.map((signal) => {
                                            const isUnread = !readSignalIds.has(signal.id)
                                            return (
                                                <Link
                                                    key={signal.id}
                                                    href={`/chart?symbol=${signal.symbol}&market=${signal.marketType}`}
                                                    onClick={() => markSignalsAsRead([signal.id])}
                                                    className={cn(
                                                        "flex items-center gap-3 p-3 hover:bg-accent/50 transition-colors border-b border-border/50 last:border-b-0",
                                                        isUnread && "bg-primary/5"
                                                    )}
                                                >
                                                    {signal.signalType === "AL" ? (
                                                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-profit/10">
                                                            <TrendingUp className="h-4 w-4 text-profit" />
                                                        </div>
                                                    ) : (
                                                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-loss/10">
                                                            <TrendingDown className="h-4 w-4 text-loss" />
                                                        </div>
                                                    )}
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-medium text-sm">{signal.symbol}</span>
                                                            <span className={cn(
                                                                "text-xs px-1.5 py-0.5 rounded",
                                                                signal.signalType === "AL"
                                                                    ? "bg-profit/10 text-profit"
                                                                    : "bg-loss/10 text-loss"
                                                            )}>
                                                                {signal.signalType}
                                                            </span>
                                                            {isUnread && (
                                                                <span className="h-2 w-2 rounded-full bg-primary" />
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                            <span>{signal.strategy}</span>
                                                            <span>•</span>
                                                            <span>{signal.timeframe}</span>
                                                            <span>•</span>
                                                            <span>{new Date(signal.createdAt).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}</span>
                                                        </div>
                                                    </div>
                                                </Link>
                                            )
                                        })
                                    ) : (
                                        <div className="p-8 text-center text-muted-foreground text-sm">
                                            Henüz sinyal yok
                                        </div>
                                    )}
                                </div>

                                {/* Footer */}
                                <div className="p-2 border-t border-border bg-muted/30">
                                    <Link
                                        href="/signals"
                                        onClick={() => setShowNotificationPanel(false)}
                                        className="block w-full text-center text-sm text-primary hover:underline py-1"
                                    >
                                        Tüm Sinyalleri Gör
                                    </Link>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
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
