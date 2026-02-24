"use client"

import { cn } from "@/lib/utils"
import { TrendingUp, TrendingDown } from "lucide-react"

// Şimdilik mock data kullanıyoruz, sonra API'ye bağlarız
const MARKET_DATA = [
    { symbol: "BTC/USDT", price: "42,150.00", change: 1.2, trend: "up" },
    { symbol: "ETH/USDT", price: "2,280.50", change: -0.5, trend: "down" },
    { symbol: "SOL/USDT", price: "98.40", change: 4.8, trend: "up" },
    { symbol: "AVAX/USDT", price: "35.20", change: 2.1, trend: "up" },
    { symbol: "XRP/USDT", price: "0.55", change: -1.1, trend: "down" },
    { symbol: "BIST100", price: "8,950.00", change: 0.8, trend: "up" },
    { symbol: "THYAO", price: "280.50", change: -1.5, trend: "down" },
    { symbol: "ASELS", price: "48.20", change: 0.5, trend: "up" },
]

export function TickerTape() {
    return (
        <div className="w-full border-b border-border/50 bg-background/50 backdrop-blur-sm overflow-hidden h-8 flex items-center mb-6">
            <div className="animate-ticker flex whitespace-nowrap gap-12 px-4">
                {/* Sonsuz döngü hissi için array'i iki kere map ediyoruz */}
                {[...MARKET_DATA, ...MARKET_DATA, ...MARKET_DATA].map((item, i) => (
                    <div key={i} className="flex items-center gap-2 font-mono text-xs">
                        <span className="font-bold text-muted-foreground">{item.symbol}</span>
                        <span className={cn(
                            "font-medium",
                            item.trend === "up" ? "text-profit" : "text-loss"
                        )}>
                            {item.price}
                        </span>
                        <div className={cn(
                            "flex items-center text-[10px]",
                            item.trend === "up" ? "text-profit" : "text-loss"
                        )}>
                            {item.trend === "up" ? <TrendingUp className="h-3 w-3 mr-0.5" /> : <TrendingDown className="h-3 w-3 mr-0.5" />}
                            <span>%{Math.abs(item.change)}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}
