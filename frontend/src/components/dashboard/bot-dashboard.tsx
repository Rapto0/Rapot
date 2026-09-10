"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Bot, Pause, Activity, TrendingUp, Clock } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { fetchStats, fetchTrades, transformStats, transformTrade } from "@/lib/api/client"
import { useBotHealth } from "@/lib/hooks/use-health"
import { formatMetric, formatMetricPercent, formatTradePrice, metricTextClass } from "@/lib/metric-display"

export function BotDashboard() {
    // 1. Fetch Bot Status
    const health = useBotHealth()

    // 2. Fetch Performance Stats
    const { data: stats } = useQuery({
        queryKey: ["stats"],
        queryFn: fetchStats,
        select: transformStats,
        refetchInterval: 60000
    })

    // 3. Fetch Recent Trades
    const { data: trades } = useQuery({
        queryKey: ["recent_trades"],
        queryFn: () => fetchTrades({ limit: 5 }),
        select: (rows) => rows.map(transformTrade),
        refetchInterval: 60000
    })

    const isRunning = health.state === "running"
    const statusTone = isRunning ? "text-[#089981]" : health.state === "stopped" ? "text-[#f23645]" : "text-muted-foreground"

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Status Card */}
            <Card className="bg-[#1e222d] border-[#2a2e39] col-span-1">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-[#787b86] flex items-center gap-2">
                        <Bot className="h-4 w-4" />
                        Otonom Bot Durumu
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className={cn("h-10 w-10 rounded-full flex items-center justify-center transition-all", statusTone)}>
                                {isRunning ? <Activity className="h-6 w-6 animate-pulse" /> : <Pause className="h-6 w-6" />}
                            </div>
                            <div>
                                <h3 className={cn("text-xl font-bold", statusTone)}>
                                    {health.label}
                                </h3>
                                <p className="text-xs text-[#787b86]">Uptime: {health.uptime}</p>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 mt-4">
                        <div className="bg-[#2a2e39]/50 p-3 rounded border border-[#2a2e39]">
                            <span className="text-[10px] text-[#787b86] block mb-1">SON TARAMA</span>
                            <span className="text-sm font-mono text-[#d1d4dc]">{health.lastScan ? new Date(health.lastScan).toLocaleTimeString() : "--"}</span>
                        </div>
                        <div className="bg-[#2a2e39]/50 p-3 rounded border border-[#2a2e39]">
                            <span className="text-[10px] text-[#787b86] block mb-1">BULUNAN SİNYAL</span>
                            <span className="text-sm font-mono text-[#d1d4dc]">{health.signalCount ?? "--"}</span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Performance Card */}
            <Card className="bg-[#1e222d] border-[#2a2e39] col-span-1">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-[#787b86] flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        Bot Performansı
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col gap-4">
                        <div className="flex items-end justify-between">
                            <div>
                                <span className="text-[10px] text-[#787b86] block uppercase tracking-wide" title="Para birimi dönüşümü yapılmaz.">Gerçekleşmiş PnL</span>
                                <span className={cn("text-2xl font-bold font-mono", metricTextClass(stats?.totalPnL))}>
                                    {formatMetric(stats?.totalPnL, 2, true)}
                                </span>
                            </div>
                            <Badge variant="outline" className="text-[#2962ff] border-[#2962ff] mb-1">Win Rate: {formatMetricPercent(stats?.winRate, 1)}</Badge>
                        </div>

                        {stats?.winRate != null && <div className="w-full bg-[#2a2e39] h-2 rounded-full overflow-hidden">
                            <div className="h-full bg-[#2962ff]" style={{ width: `${stats.winRate}%` }} />
                        </div>}

                        <div className="flex justify-between text-xs mt-1">
                            <span className="text-[#a3a6af]">Toplam İşlem: <strong className="text-white">{formatMetric(stats?.totalTrades, 0)}</strong></span>
                            <span className="text-[#a3a6af]">Açık: <strong className="text-white">{formatMetric(stats?.openPositions, 0)}</strong></span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Recent Activities List */}
            <Card className="bg-[#1e222d] border-[#2a2e39] col-span-1 md:col-span-1">
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-[#787b86] flex items-center gap-2">
                        <Clock className="h-4 w-4" />
                        Son İşlemler
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <div className="max-h-[180px] overflow-y-auto">
                        <div className="divide-y divide-[#2a2e39]">
                            {trades?.map((trade) => (
                                <div key={trade.id} className="p-3 hover:bg-[#2a2e39] transition-colors flex items-center justify-between text-xs">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-bold text-[#d1d4dc]">{trade.symbol}</span>
                                            <Badge variant="secondary" className={cn("text-[9px] px-1 h-4", trade.direction === "BUY" ? "bg-[#089981]/20 text-[#089981]" : trade.direction === "SELL" ? "bg-[#f23645]/20 text-[#f23645]" : "text-muted-foreground")}>
                                                {trade.direction ?? "—"}
                                            </Badge>
                                        </div>
                                        <span className="text-[#787b86] text-[10px]">{trade.createdAt ? new Date(trade.createdAt).toLocaleTimeString() : "—"}</span>
                                    </div>
                                    <div className="text-right">
                                        <div className="font-mono text-[#d1d4dc]">{formatTradePrice(trade.entryPrice, trade.marketType)}</div>
                                        <div className={cn("font-mono", metricTextClass(trade.pnl))}>
                                            {trade.status === "OPEN" ? "AÇIK" : trade.status === "CANCELLED" ? "İPTAL" : trade.status === null ? "BİLİNMİYOR" : formatMetric(trade.pnl, 2, true)}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {(!trades || trades.length === 0) && (
                                <div className="p-4 text-center text-[#787b86] text-xs">
                                    Henüz işlem yok.
                                </div>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
