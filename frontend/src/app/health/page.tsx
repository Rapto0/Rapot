"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { mockBotHealth, mockLogs, mockScanHistory } from "@/lib/mock-data"
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
    AlertTriangle,
    XCircle,
} from "lucide-react"

export default function HealthPage() {
    const health = mockBotHealth

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
                        <div className="h-3 w-3 rounded-full bg-profit" />
                        <div className="absolute inset-0 h-3 w-3 animate-ping rounded-full bg-profit opacity-75" />
                    </div>
                    <span className="text-sm font-medium text-profit">Çalışıyor</span>
                </div>
            </div>

            {/* Health Metrics */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <HealthCard
                    title="CPU Kullanımı"
                    value={`${health.cpuUsage}%`}
                    icon={Cpu}
                    gauge={health.cpuUsage}
                    status={health.cpuUsage < 50 ? "good" : health.cpuUsage < 80 ? "warning" : "critical"}
                />
                <HealthCard
                    title="RAM Kullanımı"
                    value={`${health.memoryUsage}%`}
                    icon={HardDrive}
                    gauge={health.memoryUsage}
                    status={health.memoryUsage < 60 ? "good" : health.memoryUsage < 85 ? "warning" : "critical"}
                />
                <HealthCard
                    title="Uptime"
                    value={health.uptime}
                    icon={Clock}
                    status="good"
                />
                <HealthCard
                    title="API Durumu"
                    value={health.apiStatus === "healthy" ? "Sağlıklı" : health.apiStatus === "degraded" ? "Yavaş" : "Kapalı"}
                    icon={health.apiStatus === "healthy" ? Wifi : WifiOff}
                    status={health.apiStatus === "healthy" ? "good" : health.apiStatus === "degraded" ? "warning" : "critical"}
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
                                <p className="text-2xl font-bold">{health.totalScans}</p>
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
                                <p className="text-2xl font-bold">{health.activeSymbols}</p>
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
                                    {new Date(health.lastScan).toLocaleTimeString("tr-TR", {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                    })}
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
                <Card className="lg:col-span-1">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                            <Terminal className="h-4 w-4" />
                            Bot Logları
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="h-80 overflow-auto bg-[#0d1117] font-mono text-xs">
                            {mockLogs.map((log) => (
                                <LogLine key={log.id} log={log} />
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Scan History */}
                <Card className="lg:col-span-1">
                    <CardHeader>
                        <CardTitle className="text-base">Son Taramalar</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                        <div className="divide-y divide-border">
                            {mockScanHistory.map((scan) => (
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
                                                variant={scan.scanType === "BIST" ? "bist" : "crypto"}
                                            >
                                                {scan.scanType}
                                            </Badge>
                                            <p className="text-xs text-muted-foreground mt-1">
                                                {scan.symbolsScanned} sembol • {scan.duration.toFixed(1)}s
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-sm font-medium text-profit">
                                            {scan.signalsFound} sinyal
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {new Date(scan.createdAt).toLocaleTimeString("tr-TR", {
                                                hour: "2-digit",
                                                minute: "2-digit",
                                            })}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
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
        level: "INFO" | "WARNING" | "ERROR"
        message: string
    }
}

function LogLine({ log }: LogLineProps) {
    const time = new Date(log.timestamp).toLocaleTimeString("tr-TR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    })

    return (
        <div className="flex gap-2 px-4 py-1.5 hover:bg-muted/30">
            <span className="text-muted-foreground shrink-0">{time}</span>
            <span
                className={cn(
                    "shrink-0 w-12",
                    log.level === "INFO" && "text-blue-400",
                    log.level === "WARNING" && "text-yellow-400",
                    log.level === "ERROR" && "text-loss"
                )}
            >
                {log.level}
            </span>
            <span className="text-foreground break-all">{log.message}</span>
        </div>
    )
}
