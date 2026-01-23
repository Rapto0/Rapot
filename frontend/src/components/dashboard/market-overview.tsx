"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { marketOverviewData, mockTrades } from "@/lib/mock-data"
import { cn, formatCurrency } from "@/lib/utils"
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    ResponsiveContainer,
    Tooltip,
    Area,
    AreaChart,
} from "recharts"
import { TrendingUp, TrendingDown } from "lucide-react"

export function MarketOverview() {
    return (
        <div className="grid gap-4 md:grid-cols-2">
            <MarketMiniChart
                title="BIST 100"
                data={marketOverviewData.bist}
                currentValue={9847.52}
                change={1.31}
                color="#2962ff"
            />
            <MarketMiniChart
                title="BTC/USDT"
                data={marketOverviewData.crypto}
                currentValue={97234.5}
                change={2.26}
                color="#f7931a"
                prefix="$"
            />
        </div>
    )
}

interface MarketMiniChartProps {
    title: string
    data: { time: string; value: number }[]
    currentValue: number
    change: number
    color: string
    prefix?: string
}

function MarketMiniChart({
    title,
    data,
    currentValue,
    change,
    color,
    prefix = "₺",
}: MarketMiniChartProps) {
    const isPositive = change >= 0

    return (
        <Card>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">{title}</CardTitle>
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
                <div className="text-xl font-bold">
                    {prefix}
                    {currentValue.toLocaleString("tr-TR", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                    })}
                </div>
            </CardHeader>
            <CardContent className="pb-2">
                <div className="h-16">
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
                </div>
            </CardContent>
        </Card>
    )
}

export function OpenPositions() {
    const openTrades = mockTrades.filter((t) => t.status === "OPEN")

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold">Açık Pozisyonlar</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
                <div className="divide-y divide-border">
                    {openTrades.map((trade) => (
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
                                        {trade.marketType} • Qty: {trade.quantity}
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
                                        trade.pnlPercent >= 0 ? "text-profit" : "text-loss"
                                    )}
                                >
                                    {trade.pnlPercent >= 0 ? "+" : ""}
                                    {trade.pnlPercent.toFixed(2)}%
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
        </Card>
    )
}
