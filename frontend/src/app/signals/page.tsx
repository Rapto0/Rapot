"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { useSignals } from "@/lib/hooks/use-signals"
import { formatDate, cn } from "@/lib/utils"
import { SkeletonTableRow } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/shared/error-boundary"
import {
    ArrowUpRight,
    ArrowDownRight,
    Search,
    Download,
    Bell,
    RefreshCw,
} from "lucide-react"

type MarketFilter = "all" | "BIST" | "Kripto"
type StrategyFilter = "all" | "COMBO" | "HUNTER"
type DirectionFilter = "all" | "AL" | "SAT"

export default function SignalsPage() {
    const [marketFilter, setMarketFilter] = useState<MarketFilter>("all")
    const [strategyFilter, setStrategyFilter] = useState<StrategyFilter>("all")
    const [directionFilter, setDirectionFilter] = useState<DirectionFilter>("all")
    const [searchQuery, setSearchQuery] = useState("")

    // Use React Query hook with filters
    const { data: signals, isLoading, isError, refetch, isFetching } = useSignals({
        marketType: marketFilter,
        strategy: strategyFilter,
        direction: directionFilter,
        searchQuery,
    })

    const filteredSignals = signals || []

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Aktif Sinyaller</h1>
                    <p className="text-sm text-muted-foreground">
                        COMBO ve HUNTER stratejilerinden gelen tüm sinyaller
                    </p>
                </div>
                <div className="flex items-center gap-2">
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
                    <Button variant="outline" size="sm" className="gap-2">
                        <Download className="h-4 w-4" />
                        Dışa Aktar
                    </Button>
                </div>
            </div>

            {/* Filters */}
            <Card>
                <CardContent className="pt-4">
                    <div className="flex flex-wrap items-center gap-4">
                        {/* Search */}
                        <div className="relative flex-1 min-w-[200px]">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                            <Input
                                placeholder="Sembol ara..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-9"
                            />
                        </div>

                        {/* Market Filter */}
                        <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">Piyasa:</span>
                            <div className="flex gap-1">
                                {(["all", "BIST", "Kripto"] as const).map((market) => (
                                    <Button
                                        key={market}
                                        variant={marketFilter === market ? "default" : "outline"}
                                        size="sm"
                                        onClick={() => setMarketFilter(market)}
                                    >
                                        {market === "all" ? "Tümü" : market}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        {/* Strategy Filter */}
                        <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">Strateji:</span>
                            <div className="flex gap-1">
                                {(["all", "COMBO", "HUNTER"] as const).map((strategy) => (
                                    <Button
                                        key={strategy}
                                        variant={strategyFilter === strategy ? "default" : "outline"}
                                        size="sm"
                                        onClick={() => setStrategyFilter(strategy)}
                                    >
                                        {strategy === "all" ? "Tümü" : strategy}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        {/* Direction Filter */}
                        <div className="flex items-center gap-2">
                            <span className="text-sm text-muted-foreground">Yön:</span>
                            <div className="flex gap-1">
                                {(["all", "AL", "SAT"] as const).map((dir) => (
                                    <Button
                                        key={dir}
                                        variant={directionFilter === dir ? "default" : "outline"}
                                        size="sm"
                                        onClick={() => setDirectionFilter(dir)}
                                    >
                                        {dir === "all" ? "Tümü" : dir === "AL" ? "LONG" : "SHORT"}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Signals Table */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">
                        Sinyal Listesi
                        <span className="ml-2 text-sm font-normal text-muted-foreground">
                            ({isLoading ? "..." : filteredSignals.length} sinyal)
                        </span>
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Sembol</TableHead>
                                <TableHead>Piyasa</TableHead>
                                <TableHead>Strateji</TableHead>
                                <TableHead>Yön</TableHead>
                                <TableHead>Zaman Dilimi</TableHead>
                                <TableHead>Skor</TableHead>
                                <TableHead className="text-right">Fiyat</TableHead>
                                <TableHead className="text-right">Tarih</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {/* Loading State */}
                            {isLoading && (
                                <>
                                    <TableRow><TableCell colSpan={8}><SkeletonTableRow /></TableCell></TableRow>
                                    <TableRow><TableCell colSpan={8}><SkeletonTableRow /></TableCell></TableRow>
                                    <TableRow><TableCell colSpan={8}><SkeletonTableRow /></TableCell></TableRow>
                                    <TableRow><TableCell colSpan={8}><SkeletonTableRow /></TableCell></TableRow>
                                    <TableRow><TableCell colSpan={8}><SkeletonTableRow /></TableCell></TableRow>
                                </>
                            )}

                            {/* Error State */}
                            {isError && (
                                <TableRow>
                                    <TableCell colSpan={8}>
                                        <div className="py-8 text-center text-muted-foreground">
                                            Sinyaller yüklenirken hata oluştu.
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
                            {!isLoading && !isError && filteredSignals.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={8}>
                                        <EmptyState
                                            icon={Bell}
                                            title="Sinyal bulunamadı"
                                            description="Seçili filtrelere uygun sinyal yok. Filtreleri değiştirmeyi deneyin."
                                        />
                                    </TableCell>
                                </TableRow>
                            )}

                            {/* Data */}
                            {!isLoading && filteredSignals.map((signal) => (
                                <TableRow key={signal.id} className="group cursor-pointer hover:bg-muted/50">
                                    <TableCell className="font-medium">{signal.symbol}</TableCell>
                                    <TableCell>
                                        <Badge variant={signal.marketType === "BIST" ? "bist" : "crypto"}>
                                            {signal.marketType}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        <Badge variant={signal.strategy === "HUNTER" ? "hunter" : "combo"}>
                                            {signal.strategy}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        <div
                                            className={cn(
                                                "inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium",
                                                signal.signalType === "AL"
                                                    ? "bg-profit/10 text-profit"
                                                    : "bg-loss/10 text-loss"
                                            )}
                                        >
                                            {signal.signalType === "AL" ? (
                                                <ArrowUpRight className="h-3 w-3" />
                                            ) : (
                                                <ArrowDownRight className="h-3 w-3" />
                                            )}
                                            {signal.signalType === "AL" ? "LONG" : "SHORT"}
                                        </div>
                                    </TableCell>
                                    <TableCell>{signal.timeframe}</TableCell>
                                    <TableCell>
                                        <span className="font-mono text-sm">{signal.score}</span>
                                    </TableCell>
                                    <TableCell className="text-right font-mono">
                                        ₺{signal.price.toLocaleString("tr-TR", { minimumFractionDigits: 2 })}
                                    </TableCell>
                                    <TableCell className="text-right text-muted-foreground">
                                        {formatDate(signal.createdAt)}
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
