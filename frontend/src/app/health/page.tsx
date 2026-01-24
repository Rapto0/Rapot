"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2 } from "lucide-react"
import { useBotHealth } from "@/lib/hooks/use-health"
import { useQuery } from "@tanstack/react-query"
import { fetchLogs, fetchScanHistory } from "@/lib/api/client"
import { cn } from "@/lib/utils"
import {
    Activity,
    Cpu,
    HardDrive,
    Clock,
    Wifi,
    WifiOff,
    Terminal,
    CheckCircle2,
} from "lucide-react"

export default function HealthPage() {
    const health = useBotHealth()

    const { data: logs, isLoading: isLogsLoading } = useQuery({
        queryKey: ['logs'],
        queryFn: () => fetchLogs(50),
        refetchInterval: 5000,
    })

    const { data: recentScans, isLoading: isScansLoading } = useQuery({
        queryKey: ['scanHistory', 'health'],
        queryFn: () => fetchScanHistory(5),
        refetchInterval: 30000,
    })

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Bot Sağlığı</h1>
                    <p className="text-sm text-muted-foreground">
                        Sistem durumu ve performans metrikleri
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <div className={`h-3 w-3 rounded-full ${health.isRunning ? 'bg-profit' : 'bg-loss'}`} />
                        {health.isRunning && <div className="absolute inset-0 h-3 w-3 animate-ping rounded-full bg-profit opacity-75" />}
                    </div>
                    <span className={`text-sm font-medium ${health.isRunning ? 'text-profit' : 'text-loss'}`}>
                        {health.isRunning ? 'Çalışıyor' : 'Durdu'}
                    </span>
                </div>
            </div>

            {/* Health Metrics - Currently using placeholders as backend doesn't provide CPU/RAM yet,
                but structure is ready when added to API */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <HealthCard
                    title="CPU Kullanımı"
                    value="--%"
                    icon={Cpu}
                    status={health.isRunning ? "good" : "critical"}
                />
                <HealthCard
                    title="RAM Kullanımı"
                    value="--%"
                    icon={HardDrive}
                    status={health.isRunning ? "good" : "critical"}
                />
                <HealthCard
                    title="Uptime"
                    value={health.uptime}
                    icon={Clock}
                    status="good"
                />
                <HealthCard
                    title="API Durumu"
                    value={health.isError ? "Hata" : "Sağlıklı"}
                    icon={!health.isError ? Wifi : WifiOff}
                    status={!health.isError ? "good" : "critical"}
                />
            </div>

            {/* Stats Row */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                <Activity className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-2xl font-bold">{health.scanCount}</p>
                                <p className="text-xs text-muted-foreground">Toplam Tarama</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                <CheckCircle2 className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-2xl font-bold">~500+</p>
                                <p className="text-xs text-muted-foreground">Aktif Sembol</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                <Clock className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-2xl font-bold">
                                    {health.lastScan
                                        ? new Date(health.lastScan).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })
                                        : "--:--"}
                                </p>
                                <p className="text-xs text-muted-foreground">Son Tarama</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Terminal Logs & Scan History */}
            <div className="grid gap-4 lg:grid-cols-2">
                {/* Terminal View */}
                <Card className="lg:col-span-1 flex flex-col h-[500px]">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                            <Terminal className="h-4 w-4" />
                            Bot Logları
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 flex-1 overflow-hidden">
                        <div className="h-full overflow-auto bg-[#0d1117] font-mono text-xs p-2">
                            {isLogsLoading && (
                                <div className="flex items-center justify-center h-full text-muted-foreground">
                                    <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                    Yükleniyor...
                                </div>
                            )}
                            {!isLogsLoading && logs?.map((log, i) => (
                                <LogLine key={i} log={log as any} />
                            ))}
                            {!isLogsLoading && (!logs || logs.length === 0) && (
                                <div className="text-muted-foreground p-2">Log kaydı bulunamadı.</div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Scan History */}
                <Card className="lg:col-span-1 h-[500px] overflow-hidden">
                    <CardHeader>
                        <CardTitle className="text-base">Son Taramalar</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 overflow-auto h-full pb-16">
                        {isScansLoading && (
                            <div className="flex items-center justify-center p-8 text-muted-foreground">
                                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                                Yükleniyor...
                            </div>
                        )}
                        {!isScansLoading && recentScans && (
                            <div className="divide-y divide-border">
                                {recentScans.map((scan) => (
                                    <div
                                        key={scan.id}
                                        className="flex items-center justify-between px-4 py-3"
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-xs font-bold">
                                                #{scan.id}
                                            </div>
                                            <div>
                                                <Badge
                                                    variant={scan.scan_type === "BIST" ? "bist" : "crypto"}
                                                >
                                                    {scan.scan_type}
                                                </Badge>
                                                <p className="text-xs text-muted-foreground mt-1">
                                                    {scan.symbols_scanned} sembol • {scan.duration_seconds.toFixed(1)}s
                                                </p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-sm font-medium text-profit">
                                                {scan.signals_found} sinyal
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                {new Date(scan.created_at).toLocaleTimeString("tr-TR", {
                                                    hour: "2-digit",
                                                    minute: "2-digit",
                                                })}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}

interface HealthCardProps {
    title: string
    value: string
    icon: React.ElementType
    gauge?: number
    status: "good" | "warning" | "critical"
}

function HealthCard({ title, value, icon: Icon, gauge, status }: HealthCardProps) {
    return (
        <Card>
            <CardContent className="pt-4">
                <div className="flex items-center justify-between mb-3">
                    <p className="text-xs text-muted-foreground">{title}</p>
                    <div
                        className={cn(
                            "flex h-8 w-8 items-center justify-center rounded-lg",
                            status === "good" && "bg-profit/10 text-profit",
                            status === "warning" && "bg-yellow-500/10 text-yellow-500",
                            status === "critical" && "bg-loss/10 text-loss"
                        )}
                    >
                        <Icon className="h-4 w-4" />
                    </div>
                </div>
                <p className="text-2xl font-bold mb-2">{value}</p>
                {gauge !== undefined && (
                    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div
                            className={cn(
                                "h-full rounded-full transition-all",
                                status === "good" && "bg-profit",
                                status === "warning" && "bg-yellow-500",
                                status === "critical" && "bg-loss"
                            )}
                            style={{ width: `${gauge}%` }}
                        />
                    </div>
                )}
            </CardContent>
        </Card>
    )
}

interface LogLineProps {
    log: {
        timestamp: string
        level: string
        message: string
    }
}

function LogLine({ log }: LogLineProps) {
    // Check if timestamp is valid, if not (e.g. empty), don't show time
    let timeDisplay = "";
    if (log.timestamp) {
        try {
            // Try to parse YYYY-MM-DD HH:MM:SS format manually if date constructor fails
            // or just let Date handle standard formats
            const date = new Date(log.timestamp.replace(' ', 'T'));
            if (!isNaN(date.getTime())) {
                timeDisplay = date.toLocaleTimeString("tr-TR", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                });
            } else {
                timeDisplay = log.timestamp.split(' ')[1] || log.timestamp; // Fallback to part of string
            }
        } catch (e) {
            timeDisplay = log.timestamp;
        }
    }

    return (
        <div className="flex gap-2 px-2 py-1 hover:bg-muted/30 border-b border-white/5 last:border-0">
            <span className="text-muted-foreground shrink-0 w-16 text-[10px]">{timeDisplay}</span>
            <span
                className={cn(
                    "shrink-0 w-12 font-bold text-[10px]",
                    log.level === "INFO" && "text-blue-400",
                    log.level === "WARNING" && "text-yellow-400",
                    log.level === "ERROR" && "text-loss",
                    log.level === "CRITICAL" && "text-loss font-extrabold"
                )}
            >
                {log.level}
            </span>
            <span className="text-foreground break-all">{log.message}</span>
        </div>
    )
}
