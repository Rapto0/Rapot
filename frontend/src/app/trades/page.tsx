"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { useTrades, useTradeStats } from "@/lib/hooks/use-trades"
import { formatDate, formatCurrency, cn } from "@/lib/utils"
import { SkeletonTableRow } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/shared/error-boundary"
import {
    ArrowUpRight,
    ArrowDownRight,
    TrendingUp,
    Target,
    DollarSign,
    RefreshCw,
    History,
} from "lucide-react"

type StatusFilter = "all" | "OPEN" | "CLOSED"

export default function TradesPage() {
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")

    // Use React Query hooks
    const { data: trades, isLoading, isError, refetch, isFetching } = useTrades({ status: statusFilter })
    const { data: stats } = useTradeStats()

    const filteredTrades = trades || []

    // Stats with fallbacks
    const totalPnL = stats?.totalPnL ?? 0
    const openCount = stats?.open ?? 0
    const closedCount = stats?.closed ?? 0
    const winRate = stats?.winRate ?? 0

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">İşlem Geçmişi</h1>
                    <p className="text-sm text-muted-foreground">
                        Tüm açık ve kapalı trade'lerin listesi
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    className="gap-2"
                    onClick={() => refetch()}
                    disabled={isFetching}
                >
                    <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
                    Yenile
                </Button>
            </div>

            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className={cn(
                                "flex h-10 w-10 items-center justify-center rounded-lg",
                                totalPnL >= 0 ? "bg-profit/10 text-profit" : "bg-loss/10 text-loss"
                            )}>
                                <DollarSign className="h-5 w-5" />
                            </div>
                            <div>
                                <p className={cn(
                                    "text-xl font-bold",
                                    totalPnL >= 0 ? "text-profit" : "text-loss"
                                )}>
                                    {totalPnL >= 0 ? "+" : ""}{formatCurrency(totalPnL)}
                                </p>
                                <p className="text-xs text-muted-foreground">Toplam PnL</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                <TrendingUp className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-xl font-bold">{openCount}</p>
                                <p className="text-xs text-muted-foreground">Açık Pozisyon</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                                <Target className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-xl font-bold">{closedCount}</p>
                                <p className="text-xs text-muted-foreground">Kapalı İşlem</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4">
                        <div className="flex items-center gap-3">
                            <div className={cn(
                                "flex h-10 w-10 items-center justify-center rounded-lg",
                                winRate >= 50 ? "bg-profit/10 text-profit" : "bg-loss/10 text-loss"
                            )}>
                                <Target className="h-5 w-5" />
                            </div>
                            <div>
                                <p className="text-xl font-bold">{winRate.toFixed(1)}%</p>
                                <p className="text-xs text-muted-foreground">Win Rate</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Filter */}
            <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Durum:</span>
                {(["all", "OPEN", "CLOSED"] as const).map((status) => (
                    <Button
                        key={status}
                        variant={statusFilter === status ? "default" : "outline"}
                        size="sm"
                        onClick={() => setStatusFilter(status)}
                    >
                        {status === "all" ? "Tümü" : status === "OPEN" ? "Açık" : "Kapalı"}
                    </Button>
                ))}
            </div>

            {/* Trades Table */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">
                        İşlem Listesi
                        <span className="ml-2 text-sm font-normal text-muted-foreground">
                            ({isLoading ? "..." : filteredTrades.length} işlem)
                        </span>
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Sembol</TableHead>
                                <TableHead>Piyasa</TableHead>
                                <TableHead>Yön</TableHead>
                                <TableHead className="text-right">Giriş Fiyatı</TableHead>
                                <TableHead className="text-right">Güncel Fiyat</TableHead>
                                <TableHead className="text-right">Miktar</TableHead>
                                <TableHead className="text-right">PnL</TableHead>
                                <TableHead>Durum</TableHead>
                                <TableHead className="text-right">Tarih</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {/* Loading State */}
                            {isLoading && (
                                <>
                                    <TableRow><TableCell colSpan={9}><SkeletonTableRow /></TableCell></TableRow>
                                    <TableRow><TableCell colSpan={9}><SkeletonTableRow /></TableCell></TableRow>
                                    <TableRow><TableCell colSpan={9}><SkeletonTableRow /></TableCell></TableRow>
                                </>
                            )}

                            {/* Error State */}
                            {isError && (
                                <TableRow>
                                    <TableCell colSpan={9}>
                                        <div className="py-8 text-center text-muted-foreground">
                                            İşlemler yüklenirken hata oluştu.
                                            <Button
                                                variant="link"
                                                onClick={() => refetch()}
                                                className="ml-2"
                                            >
                                                Tekrar dene
                                            </Button>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            )}

                            {/* Empty State */}
                            {!isLoading && !isError && filteredTrades.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={9}>
                                        <EmptyState
                                            icon={History}
                                            title="İşlem bulunamadı"
                                            description="Seçili filtrelere uygun işlem yok."
                                        />
                                    </TableCell>
                                </TableRow>
                            )}

                            {/* Data */}
                            {!isLoading && filteredTrades.map((trade) => (
                                <TableRow key={trade.id} className="hover:bg-muted/50">
                                    <TableCell className="font-medium">{trade.symbol}</TableCell>
                                    <TableCell>
                                        <Badge variant={trade.marketType === "BIST" ? "bist" : "crypto"}>
                                            {trade.marketType}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        <div
                                            className={cn(
                                                "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium",
                                                trade.direction === "BUY"
                                                    ? "bg-profit/10 text-profit"
                                                    : "bg-loss/10 text-loss"
                                            )}
                                        >
                                            {trade.direction === "BUY" ? (
                                                <ArrowUpRight className="h-3 w-3" />
                                            ) : (
                                                <ArrowDownRight className="h-3 w-3" />
                                            )}
                                            {trade.direction === "BUY" ? "LONG" : "SHORT"}
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-right font-mono">
                                        {trade.marketType === "Kripto" ? "$" : "₺"}
                                        {trade.entryPrice.toLocaleString("tr-TR")}
                                    </TableCell>
                                    <TableCell className="text-right font-mono">
                                        {trade.marketType === "Kripto" ? "$" : "₺"}
                                        {trade.currentPrice.toLocaleString("tr-TR")}
                                    </TableCell>
                                    <TableCell className="text-right">{trade.quantity}</TableCell>
                                    <TableCell className="text-right">
                                        <div className={cn(
                                            "font-medium",
                                            trade.pnl >= 0 ? "text-profit" : "text-loss"
                                        )}>
                                            {trade.pnl >= 0 ? "+" : ""}{formatCurrency(trade.pnl)}
                                        </div>
                                        <div className={cn(
                                            "text-xs",
                                            trade.pnlPercent >= 0 ? "text-profit" : "text-loss"
                                        )}>
                                            {trade.pnlPercent >= 0 ? "+" : ""}{trade.pnlPercent.toFixed(2)}%
                                        </div>
                                    </TableCell>
                                    <TableCell>
                                        <Badge
                                            variant={trade.status === "OPEN" ? "default" : "secondary"}
                                        >
                                            {trade.status === "OPEN" ? "Açık" : "Kapalı"}
                                        </Badge>
                                    </TableCell>
                                    <TableCell className="text-right text-muted-foreground">
                                        {formatDate(trade.createdAt)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    )
}
