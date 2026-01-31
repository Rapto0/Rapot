"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn, formatCurrency } from "@/lib/utils"
import { useQuery } from "@tanstack/react-query"
import { fetchMarketOverview, fetchTrades } from "@/lib/api/client"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { TrendingUp, TrendingDown, Loader2, Zap } from "lucide-react"
import {
    AreaChart,
    Area,
    ResponsiveContainer
} from "recharts"

export function MarketOverview() {
    // Live BTC price from Binance WebSocket
    const cryptoPrices = useBinanceTicker(["BTCUSDT"])

    const { data: marketData, isLoading } = useQuery({
        queryKey: ['marketOverview'],
        queryFn: fetchMarketOverview,
        refetchInterval: 60000,
    })

    // Get live BTC price if available
    const liveBTC = cryptoPrices["BTCUSDT"]

    if (isLoading && !liveBTC) {
        return (
            <div className="grid gap-4 md:grid-cols-2">
                <SkeletonChart title="BIST 100" />
                <SkeletonChart title="BTC/USDT" />
            </div>
        )
    }

    // Use live BTC data if available, otherwise use API data
    const btcValue = liveBTC?.price || marketData?.crypto?.currentValue || 0
    const btcChange = liveBTC?.change || marketData?.crypto?.change || 0
    const btcHistory = marketData?.crypto?.history || []

    // BIST data from API
    const bistValue = marketData?.bist?.currentValue || 0
    const bistChange = marketData?.bist?.change || 0
    const bistHistory = marketData?.bist?.history || []

    return (
        <div className="grid gap-4 md:grid-cols-2">
            <MarketMiniChart
                title="BIST 100"
                data={bistHistory}
                currentValue={bistValue}
                change={bistChange}
                color="#2962ff"
            />
            <MarketMiniChart
                title="BTC/USDT"
                data={btcHistory}
                currentValue={btcValue}
                change={btcChange}
                color="#f7931a"
                prefix="$"
                isLive={!!liveBTC}
            />
        </div>
    )
}

function SkeletonChart({ title }: { title: string }) {
    return (
        <Card className="h-full">
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">{title}</CardTitle>
                <div className="h-5 w-20 animate-pulse bg-muted rounded" />
            </CardHeader>
            <CardContent>
                <div className="h-16 animate-pulse bg-muted/20 rounded-md" />
            </CardContent>
        </Card>
    )
}

interface MarketMiniChartProps {
    title: string
    data: { time: string; value: number }[]
    currentValue: number
    change: number
    color: string
    prefix?: string
    isLive?: boolean
}

function MarketMiniChart({
    title,
    data,
    currentValue,
    change,
    color,
    prefix = "₺",
    isLive = false,
}: MarketMiniChartProps) {
    const isPositive = change >= 0

    return (
        <Card className="glass-panel">
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <CardTitle className="text-sm font-medium">{title}</CardTitle>
                        {isLive && (
                            <span className="flex items-center gap-1 text-[10px] text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                                <Zap className="h-2.5 w-2.5" />
                                CANLI
                            </span>
                        )}
                    </div>
                    <div
                        className={cn(
                            "flex items-center gap-1 text-xs font-medium",
                            isPositive ? "text-profit" : "text-loss"
                        )}
                    >
                        {isPositive ? (
                            <TrendingUp className="h-3 w-3" />
                        ) : (
                            <TrendingDown className="h-3 w-3" />
                        )}
                        {isPositive ? "+" : ""}
                        {change.toFixed(2)}%
                    </div>
                </div>
                <div className="text-xl font-bold mono-numbers">
                    {prefix}
                    {currentValue.toLocaleString("tr-TR", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: prefix === "$" ? 2 : 2,
                    })}
                </div>
            </CardHeader>
            <CardContent className="pb-2">
                <div className="h-16">
                    {data.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={data}>
                                <defs>
                                    <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                                        <stop offset="100%" stopColor={color} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <Area
                                    type="monotone"
                                    dataKey="value"
                                    stroke={color}
                                    fill={`url(#gradient-${title})`}
                                    strokeWidth={2}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="flex items-center justify-center h-full text-xs text-muted-foreground">
                            Grafik verisi yükleniyor...
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}

export function OpenPositions() {
    const { data: trades, isLoading } = useQuery({
        queryKey: ['openTrades'],
        queryFn: () => fetchTrades({ status: 'OPEN' }),
        refetchInterval: 15000,
    })

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold">Açık Pozisyonlar</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                {isLoading && (
                    <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
                        <span className="text-muted-foreground text-sm">Yükleniyor...</span>
                    </div>
                )}

                {!isLoading && (!trades || trades.length === 0) && (
                    <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
                        Açık pozisyon yok
                    </div>
                )}

                {!isLoading && trades && trades.length > 0 && (
                    <div className="divide-y divide-border">
                        {trades.map((trade) => (
                            <div
                                key={trade.id}
                                className="flex items-center justify-between px-4 py-3"
                            >
                                <div className="flex items-center gap-3">
                                    <div
                                        className={cn(
                                            "flex h-8 w-8 items-center justify-center rounded-lg text-xs font-bold",
                                            trade.direction === "BUY"
                                                ? "bg-profit/10 text-profit"
                                                : "bg-loss/10 text-loss"
                                        )}
                                    >
                                        {trade.direction === "BUY" ? "L" : "S"}
                                    </div>
                                    <div>
                                        <div className="font-medium text-sm">{trade.symbol}</div>
                                        <div className="text-xs text-muted-foreground">
                                            {trade.market_type} • Adet: {trade.quantity}
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div
                                        className={cn(
                                            "font-medium text-sm",
                                            trade.pnl >= 0 ? "text-profit" : "text-loss"
                                        )}
                                    >
                                        {trade.pnl >= 0 ? "+" : ""}
                                        {formatCurrency(trade.pnl)}
                                    </div>
                                    <div
                                        className={cn(
                                            "text-xs",
                                            // PnL percent calculation if needed, currently just showing PnL
                                            trade.pnl >= 0 ? "text-profit" : "text-loss"
                                        )}
                                    >
                                        {trade.price > 0
                                            ? `${((trade.pnl / (trade.price * trade.quantity)) * 100).toFixed(2)}%`
                                            : '0.00%'}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}
