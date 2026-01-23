"use client"

import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"
import { useDashboardKPIs } from "@/lib/hooks/use-dashboard"
import { TrendingUp, TrendingDown, Target, Clock, Briefcase, BarChart3 } from "lucide-react"
import { formatCurrency, getTimeAgo } from "@/lib/utils"
import { SkeletonKPICard } from "@/components/ui/skeleton"

interface KPICardProps {
    title: string
    value: string | number
    change?: number
    icon: React.ElementType
    trend?: "up" | "down" | "neutral"
    suffix?: string
    isLoading?: boolean
}

function KPICard({ title, value, change, icon: Icon, trend = "neutral", suffix, isLoading }: KPICardProps) {
    if (isLoading) {
        return <SkeletonKPICard />
    }

    return (
        <Card className="relative overflow-hidden">
            <CardContent className="p-4">
                <div className="flex items-start justify-between">
                    <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                            {title}
                        </p>
                        <div className="flex items-baseline gap-1">
                            <span className={cn(
                                "text-2xl font-bold",
                                trend === "up" && "text-profit",
                                trend === "down" && "text-loss"
                            )}>
                                {value}
                            </span>
                            {suffix && (
                                <span className="text-sm text-muted-foreground">{suffix}</span>
                            )}
                        </div>
                        {change !== undefined && (
                            <div className={cn(
                                "flex items-center gap-1 text-xs font-medium",
                                change >= 0 ? "text-profit" : "text-loss"
                            )}>
                                {change >= 0 ? (
                                    <TrendingUp className="h-3 w-3" />
                                ) : (
                                    <TrendingDown className="h-3 w-3" />
                                )}
                                <span>{change >= 0 ? "+" : ""}{change.toFixed(2)}%</span>
                            </div>
                        )}
                    </div>
                    <div className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-lg",
                        trend === "up" && "bg-profit/10 text-profit",
                        trend === "down" && "bg-loss/10 text-loss",
                        trend === "neutral" && "bg-primary/10 text-primary"
                    )}>
                        <Icon className="h-5 w-5" />
                    </div>
                </div>
            </CardContent>
            {/* Gradient Accent Line */}
            <div className={cn(
                "absolute bottom-0 left-0 right-0 h-0.5",
                trend === "up" && "bg-gradient-to-r from-profit/50 to-profit",
                trend === "down" && "bg-gradient-to-r from-loss/50 to-loss",
                trend === "neutral" && "bg-gradient-to-r from-primary/50 to-primary"
            )} />
        </Card>
    )
}

export function KPICards() {
    const { data: stats, isLoading, isError } = useDashboardKPIs()

    // Show skeletons while loading
    if (isLoading || !stats) {
        return (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <SkeletonKPICard />
                <SkeletonKPICard />
                <SkeletonKPICard />
                <SkeletonKPICard />
            </div>
        )
    }

    // Error fallback - show cards with default values
    if (isError) {
        return (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KPICard title="Toplam PnL" value="--" icon={TrendingUp} trend="neutral" />
                <KPICard title="Win Rate" value="--" suffix="%" icon={Target} trend="neutral" />
                <KPICard title="Açık Pozisyonlar" value="--" icon={Briefcase} trend="neutral" />
                <KPICard title="Son Tarama" value="--" icon={Clock} trend="neutral" />
            </div>
        )
    }

    return (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KPICard
                title="Toplam PnL"
                value={formatCurrency(stats.totalPnL)}
                change={stats.totalPnLPercent}
                icon={TrendingUp}
                trend={stats.totalPnL >= 0 ? "up" : "down"}
            />
            <KPICard
                title="Win Rate"
                value={stats.winRate.toFixed(1)}
                suffix="%"
                icon={Target}
                trend={stats.winRate >= 50 ? "up" : "down"}
            />
            <KPICard
                title="Açık Pozisyonlar"
                value={stats.openPositions}
                icon={Briefcase}
                trend="neutral"
            />
            <KPICard
                title="Son Tarama"
                value={getTimeAgo(stats.lastScanTime)}
                icon={Clock}
                trend="neutral"
            />
        </div>
    )
}

export function MiniStats() {
    const { data: stats, isLoading } = useDashboardKPIs()

    if (isLoading || !stats) {
        return (
            <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-card border border-border p-3 animate-pulse">
                    <div className="h-3 w-24 bg-muted rounded mb-2" />
                    <div className="h-5 w-8 bg-muted rounded" />
                </div>
                <div className="rounded-lg bg-card border border-border p-3 animate-pulse">
                    <div className="h-3 w-24 bg-muted rounded mb-2" />
                    <div className="h-5 w-8 bg-muted rounded" />
                </div>
            </div>
        )
    }

    return (
        <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-card border border-border p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <BarChart3 className="h-3 w-3" />
                    Bugünkü Sinyaller
                </div>
                <div className="text-lg font-bold">{stats.todaySignals}</div>
            </div>
            <div className="rounded-lg bg-card border border-border p-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <Target className="h-3 w-3" />
                    Toplam İşlem
                </div>
                <div className="text-lg font-bold">{stats.totalTrades}</div>
            </div>
        </div>
    )
}
