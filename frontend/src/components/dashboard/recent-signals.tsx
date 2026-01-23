"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useRecentSignals } from "@/lib/hooks/use-signals"
import { getTimeAgo, cn } from "@/lib/utils"
import { ArrowUpRight, ArrowDownRight, Bell } from "lucide-react"
import Link from "next/link"
import { Skeleton } from "@/components/ui/skeleton"

export function RecentSignals() {
    const { data: recentSignals, isLoading, isError } = useRecentSignals(5)

    return (
        <Card className="col-span-full lg:col-span-4">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-base font-semibold">Son Sinyaller</CardTitle>
                <Link
                    href="/signals"
                    className="text-xs text-primary hover:underline"
                >
                    Tümünü Gör →
                </Link>
            </CardHeader>
            <CardContent className="p-0">
                {/* Loading State */}
                {isLoading && (
                    <div className="divide-y divide-border">
                        {[1, 2, 3, 4, 5].map((i) => (
                            <div key={i} className="flex items-center justify-between px-4 py-3">
                                <div className="flex items-center gap-3">
                                    <Skeleton className="h-8 w-8 rounded-lg" />
                                    <div>
                                        <Skeleton className="h-4 w-24 mb-1" />
                                        <Skeleton className="h-3 w-16" />
                                    </div>
                                </div>
                                <div className="text-right">
                                    <Skeleton className="h-4 w-12 mb-1" />
                                    <Skeleton className="h-3 w-16" />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Error State */}
                {isError && (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                        <Bell className="h-8 w-8 text-muted-foreground mb-2" />
                        <p className="text-sm text-muted-foreground">Sinyaller yüklenemedi</p>
                    </div>
                )}

                {/* Empty State */}
                {!isLoading && !isError && (!recentSignals || recentSignals.length === 0) && (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                        <Bell className="h-8 w-8 text-muted-foreground mb-2" />
                        <p className="text-sm text-muted-foreground">Henüz sinyal yok</p>
                    </div>
                )}

                {/* Data */}
                {!isLoading && recentSignals && recentSignals.length > 0 && (
                    <div className="divide-y divide-border">
                        {recentSignals.map((signal) => (
                            <SignalRow key={signal.id} signal={signal} />
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}

interface SignalRowProps {
    signal: {
        id: number
        symbol: string
        marketType: "BIST" | "Kripto"
        strategy: "COMBO" | "HUNTER"
        signalType: "AL" | "SAT"
        timeframe: string
        score: string
        price: number
        createdAt: string
    }
}

function SignalRow({ signal }: SignalRowProps) {
    const isLong = signal.signalType === "AL"

    return (
        <div className="flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors cursor-pointer">
            <div className="flex items-center gap-3">
                <div
                    className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg",
                        isLong ? "bg-profit/10" : "bg-loss/10"
                    )}
                >
                    {isLong ? (
                        <ArrowUpRight className="h-4 w-4 text-profit" />
                    ) : (
                        <ArrowDownRight className="h-4 w-4 text-loss" />
                    )}
                </div>
                <div>
                    <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{signal.symbol}</span>
                        <Badge
                            variant={signal.strategy === "HUNTER" ? "hunter" : "combo"}
                            className="text-[10px] px-1.5 py-0"
                        >
                            {signal.strategy}
                        </Badge>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <span>{signal.timeframe}</span>
                        <span>•</span>
                        <span>{signal.score}</span>
                    </div>
                </div>
            </div>
            <div className="text-right">
                <div
                    className={cn(
                        "text-sm font-medium",
                        isLong ? "text-profit" : "text-loss"
                    )}
                >
                    {isLong ? "LONG" : "SHORT"}
                </div>
                <div className="text-xs text-muted-foreground">
                    {getTimeAgo(signal.createdAt)}
                </div>
            </div>
        </div>
    )
}
