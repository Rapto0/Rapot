"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useBotHealth } from "@/lib/hooks/use-health"
import { useQuery } from "@tanstack/react-query"
import { fetchScanHistory } from "@/lib/api/client"
import { cn } from "@/lib/utils"
import {
    Search,
    TrendingUp,
    Clock,
    BarChart3,
    Play,
    RefreshCw,
} from "lucide-react"
import { Button } from "@/components/ui/button"

export default function ScannerPage() {
    const health = useBotHealth()

    // Fetch recent scans
    const { data: recentScans, isLoading: isScansLoading } = useQuery({
        queryKey: ['scanHistory'],
        queryFn: () => fetchScanHistory(10),
        refetchInterval: 30000,
    })

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Piyasa Tarayıcı</h1>
                    <p className="text-sm text-muted-foreground">
                        BIST ve Kripto piyasalarını tarama ve izleme
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" className="gap-2">
                        <RefreshCw className="h-4 w-4" />
                        Yenile
                    </Button>
                    <Button size="sm" className="gap-2">
                        <Play className="h-4 w-4" />
                        Taramayı Başlat
                    </Button>
                </div>
            </div>

            {/* Scanner Stats */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                <Search className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-2xl font-bold">{health.isScanning ? "Taranıyor..." : "Hazır"}</p>
                                <p className="text-xs text-muted-foreground">Bot Durumu</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-profit/10 text-profit">
                                <TrendingUp className="h-5 w-5" />
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
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-500/10 text-yellow-500">
                                <Clock className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-2xl font-bold">{health.uptime}</p>
                                <p className="text-xs text-muted-foreground">Çalışma Süresi</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                                <BarChart3 className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-2xl font-bold">~30s</p>
                                <p className="text-xs text-muted-foreground">Ort. Süre</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Market Sections */}
            <div className="grid gap-4 lg:grid-cols-2">
                {/* BIST Scanner */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle className="flex items-center gap-2 text-base">
                                <Badge variant="bist">BIST</Badge>
                                Borsa İstanbul
                            </CardTitle>
                            <div className="flex items-center gap-2">
                                <div className="relative">
                                    <div className={`h-2 w-2 rounded-full ${health.isRunning ? 'bg-profit' : 'bg-loss'}`} />
                                    {health.isRunning && <div className="absolute inset-0 h-2 w-2 animate-ping rounded-full bg-profit opacity-75" />}
                                </div>
                                <span className="text-xs text-muted-foreground">Aktif</span>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">Taranan Sembol</span>
                                <span className="font-medium">500+</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">Aktif Strateji</span>
                                <span className="font-medium">COMBO + HUNTER</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">Son Tarama</span>
                                <span className="font-medium">
                                    {health.lastScan ? new Date(health.lastScan).toLocaleTimeString('tr-TR') : '-'}
                                </span>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Crypto Scanner */}
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle className="flex items-center gap-2 text-base">
                                <Badge variant="crypto">Kripto</Badge>
                                Binance
                            </CardTitle>
                            <div className="flex items-center gap-2">
                                <div className="relative">
                                    <div className={`h-2 w-2 rounded-full ${health.isRunning ? 'bg-profit' : 'bg-loss'}`} />
                                    {health.isRunning && <div className="absolute inset-0 h-2 w-2 animate-ping rounded-full bg-profit opacity-75" />}
                                </div>
                                <span className="text-xs text-muted-foreground">Aktif</span>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-3">
                            <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">Taranan Sembol</span>
                                <span className="font-medium">150+</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">Aktif Strateji</span>
                                <span className="font-medium">COMBO + HUNTER</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">Son Tarama</span>
                                <span className="font-medium">
                                    {health.lastScan ? new Date(health.lastScan).toLocaleTimeString('tr-TR') : '-'}
                                </span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Recent Scans */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Son Taramalar</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {isScansLoading && <div className="p-4 text-center text-sm text-muted-foreground">Yükleniyor...</div>}
                    {!isScansLoading && (!recentScans || recentScans.length === 0) && (
                        <div className="p-4 text-center text-sm text-muted-foreground">Kayıt yok</div>
                    )}

                    {!isScansLoading && recentScans && recentScans.length > 0 && (
                        <div className="divide-y divide-border">
                            {recentScans.map((scan) => (
                                <div
                                    key={scan.id}
                                    className="flex items-center justify-between px-4 py-3"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-sm font-bold">
                                            #{scan.id}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <Badge
                                                    variant={scan.scan_type === "BIST" ? "bist" : "crypto"}
                                                >
                                                    {scan.scan_type}
                                                </Badge>
                                                <span className="text-sm font-medium">
                                                    {scan.symbols_scanned} sembol tarandı
                                                </span>
                                            </div>
                                            <p className="text-xs text-muted-foreground mt-1">
                                                Süre: {scan.duration_seconds.toFixed(1)} saniye
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-sm font-medium text-profit">
                                            {scan.signals_found} sinyal bulundu
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {new Date(scan.created_at).toLocaleString("tr-TR", {
                                                day: "2-digit",
                                                month: "2-digit",
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
    )
}
