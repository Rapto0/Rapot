"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { Bot, Play, Pause, Activity, TrendingUp, DollarSign, Clock } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { fetchBotStatus, fetchStats, fetchTrades } from "@/lib/api/client"

export function BotDashboard() {
    // 1. Fetch Bot Status
    const { data: botStatus } = useQuery({
        queryKey: ["botStatus"],
        queryFn: fetchBotStatus,
        refetchInterval: 5000 // Real-timeish
    })

    // 2. Fetch Performance Stats
    const { data: stats } = useQuery({
        queryKey: ["stats"],
        queryFn: fetchStats,
        refetchInterval: 15000
    })

    // 3. Fetch Recent Trades
    const { data: trades } = useQuery({
        queryKey: ["recent_trades"],
        queryFn: () => fetchTrades({ limit: 5 }),
        refetchInterval: 10000
    })

    const isRunning = botStatus?.bot.is_running
    const uptime = botStatus?.bot.uptime_human || "0s"

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 h-full">
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
                            <div className={cn("h-10 w-10 rounded-full flex items-center justify-center transition-all", isRunning ? "bg-[#089981]/20 text-[#089981]" : "bg-[#f23645]/20 text-[#f23645]")}>
                                {isRunning ? <Activity className="h-6 w-6 animate-pulse" /> : <Pause className="h-6 w-6" />}
                            </div>
                            <div>
                                <h3 className={cn("text-xl font-bold", isRunning ? "text-[#089981]" : "text-[#f23645]")}>
                                    {isRunning ? "AKTİF" : "DURDURULDU"}
                                </h3>
                                <p className="text-xs text-[#787b86]">Uptime: {uptime}</p>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 mt-4">
                        <div className="bg-[#2a2e39]/50 p-3 rounded border border-[#2a2e39]">
                            <span className="text-[10px] text-[#787b86] block mb-1">SON TARAMA</span>
                            <span className="text-sm font-mono text-[#d1d4dc]">{botStatus?.scanning.last_scan_time ? new Date(botStatus?.scanning.last_scan_time).toLocaleTimeString() : "-"}</span>
                        </div>
                        <div className="bg-[#2a2e39]/50 p-3 rounded border border-[#2a2e39]">
                            <span className="text-[10px] text-[#787b86] block mb-1">BULUNAN SİNYAL</span>
                            <span className="text-sm font-mono text-[#d1d4dc]">{botStatus?.scanning.signal_count || 0}</span>
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
                                <span className="text-[10px] text-[#787b86] block uppercase tracking-wide">Toplam PnL</span>
                                <span className={cn("text-2xl font-bold font-mono", (stats?.total_pnl || 0) >= 0 ? "text-[#089981]" : "text-[#f23645]")}>
                                    {(stats?.total_pnl || 0) >= 0 ? "+" : ""}{stats?.total_pnl?.toLocaleString() || "0.00"} ₺
                                </span>
                            </div>
                            <Badge variant="outline" className="text-[#2962ff] border-[#2962ff] mb-1">Win Rate: {(stats?.win_rate || 0).toFixed(1)}%</Badge>
                        </div>

                        <div className="w-full bg-[#2a2e39] h-2 rounded-full overflow-hidden">
                            <div className="h-full bg-[#2962ff]" style={{ width: `${stats?.win_rate || 0}%` }} />
                        </div>

                        <div className="flex justify-between text-xs mt-1">
                            <span className="text-[#a3a6af]">Toplam İşlem: <strong className="text-white">{stats?.total_trades || 0}</strong></span>
                            <span className="text-[#089981]">Açık: <strong className="text-[#089981]">{stats?.open_trades || 0}</strong></span>
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
                    <ScrollArea className="h-[180px]">
                        <div className="divide-y divide-[#2a2e39]">
                            {trades?.map((trade) => (
                                <div key={trade.id} className="p-3 hover:bg-[#2a2e39] transition-colors flex items-center justify-between text-xs">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-bold text-[#d1d4dc]">{trade.symbol}</span>
                                            <Badge variant="secondary" className={cn("text-[9px] px-1 h-4", trade.direction === "BUY" ? "bg-[#089981]/20 text-[#089981]" : "bg-[#f23645]/20 text-[#f23645]")}>
                                                {trade.direction}
                                            </Badge>
                                        </div>
                                        <span className="text-[#787b86] text-[10px]">{new Date(trade.created_at || "").toLocaleTimeString()}</span>
                                    </div>
                                    <div className="text-right">
                                        <div className="font-mono text-[#d1d4dc]">{trade.price}</div>
                                        <div className={cn("font-mono", trade.pnl >= 0 ? "text-[#089981]" : "text-[#f23645]")}>
                                            {trade.status === "OPEN" ? "AÇIK" : `${trade.pnl > 0 ? "+" : ""}${trade.pnl}`}
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
                    </ScrollArea>
                </CardContent>
            </Card>
        </div>
    )
}
