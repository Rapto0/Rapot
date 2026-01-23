"use client"

import { marketTickers } from "@/lib/mock-data"
import { cn } from "@/lib/utils"
import { Bell, RefreshCw } from "lucide-react"
import { useEffect, useState } from "react"

export function Header() {
    const [currentTime, setCurrentTime] = useState<string>("")

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

    return (
        <header className="fixed top-0 right-0 left-0 md:left-56 z-30 h-14 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 hidden md:block">
            <div className="flex h-full items-center justify-between px-4">
                {/* Ticker Tape */}
                <div className="relative flex-1 overflow-hidden">
                    <div className="flex animate-ticker whitespace-nowrap">
                        {[...marketTickers, ...marketTickers].map((ticker, index) => (
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
                    <button className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
                        <RefreshCw className="h-4 w-4" />
                    </button>

                    {/* Notifications */}
                    <button className="relative flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
                        <Bell className="h-4 w-4" />
                        <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-white">
                            3
                        </span>
                    </button>
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
    const isPositive = ticker.change >= 0

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
