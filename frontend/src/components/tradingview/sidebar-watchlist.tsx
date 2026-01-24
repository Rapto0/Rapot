"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchTicker } from "@/lib/api/client"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { MoreHorizontal, Plus, RefreshCw } from "lucide-react"

// Crypto symbols for WebSocket
const CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

export function SidebarWatchlist() {
    // Fetch BIST tickers from API
    const { data: tickers, isLoading, refetch } = useQuery({
        queryKey: ['watchlist-ticker'],
        queryFn: fetchTicker,
        refetchInterval: 30000,
    })

    // Live crypto prices via WebSocket
    const cryptoPrices = useBinanceTicker(CRYPTO_SYMBOLS)

    // Merge API tickers with live crypto
    const mergedData = [
        // Add live crypto data
        ...CRYPTO_SYMBOLS.map(symbol => ({
            symbol: symbol.replace("USDT", "/USD"),
            price: cryptoPrices[symbol]?.price?.toFixed(2) || "---",
            change: cryptoPrices[symbol]?.change || 0,
            type: "Kripto"
        })),
        // Add BIST data
        ...(tickers || []).map(t => ({
            symbol: t.symbol,
            price: t.price?.toFixed(2) || "---",
            change: t.changePercent || 0,
            type: "BIST"
        }))
    ]

    return (
        <div className="flex h-[55%] flex-col bg-[#131722]">
            <div className="flex items-center justify-between border-b border-[#2a2e39] px-3 py-2">
                <span className="text-sm font-medium text-[#d1d4dc]">İzleme Listesi</span>
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => refetch()}
                        className="flex h-6 w-6 items-center justify-center rounded hover:bg-[#2a2e39] text-[#787b86]"
                    >
                        <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
                    </button>
                    <button className="flex h-6 w-6 items-center justify-center rounded hover:bg-[#2a2e39] text-[#787b86]">
                        <Plus className="h-4 w-4" />
                    </button>
                    <button className="flex h-6 w-6 items-center justify-center rounded hover:bg-[#2a2e39] text-[#787b86]">
                        <MoreHorizontal className="h-4 w-4" />
                    </button>
                </div>
            </div>

            <ScrollArea className="flex-1">
                <div className="flex flex-col">
                    {mergedData.map((item, index) => (
                        <WatchlistItem key={`${item.symbol}-${index}`} {...item} />
                    ))}
                    {mergedData.length === 0 && !isLoading && (
                        <div className="text-center text-[#787b86] py-4 text-sm">
                            Veri bulunamadı
                        </div>
                    )}
                </div>
            </ScrollArea>
        </div>
    )
}

function WatchlistItem({ symbol, price, change, type }: {
    symbol: string
    price: string
    change: number
    type: string
}) {
    const isPositive = change >= 0
    return (
        <div className="flex cursor-pointer items-center justify-between px-3 py-2 hover:bg-[#2a2e39] group">
            <div className="flex flex-col">
                <span className="text-sm font-medium text-[#d1d4dc] group-hover:text-blue-400">{symbol}</span>
                <span className="text-xs text-[#787b86]">{type}</span>
            </div>
            <div className="text-right">
                <div className="text-sm font-mono text-[#d1d4dc] tabular-nums">{price}</div>
                <div className={cn("text-xs font-mono tabular-nums", isPositive ? "text-[#089981]" : "text-[#f23645]")}>
                    {isPositive ? "+" : ""}{change.toFixed(2)}%
                </div>
            </div>
        </div>
    )
}
