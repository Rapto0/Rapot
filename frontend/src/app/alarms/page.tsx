"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { fetchCandles } from "@/lib/api/client"
import { cn } from "@/lib/utils"
import {
    ALARM_INDICATOR_OPTIONS,
    ALARM_TIMEFRAME_OPTIONS,
    WATCHLIST_STORAGE_KEY,
    WATCHLIST_ALARMS_STORAGE_KEY,
    evaluateWatchlistAlarmRule,
    loadStoredWatchlists,
    loadWatchlistAlarmRules,
    saveWatchlistAlarmRules,
    type AlarmSide,
    type StoredWatchlistModel,
    type WatchlistAlarmRule,
    type WatchlistSymbolRow,
} from "@/lib/watchlist-alarms"
import { Bell, RefreshCw, Trash2 } from "lucide-react"

interface TriggerHit {
    symbol: string
    marketType: "BIST" | "Kripto"
    side: AlarmSide
    detail: string
    value: number | null
}

interface RuleRuntimeState {
    checkedAt: string
    checkedSymbols: number
    triggerHits: TriggerHit[]
    errors: string[]
}

const toWatchlistSymbols = (watchlist: StoredWatchlistModel): WatchlistSymbolRow[] =>
    watchlist.rows.filter((row): row is WatchlistSymbolRow => row.kind === "symbol")

const formatThresholdSummary = (rule: WatchlistAlarmRule): string => {
    if (rule.indicator === "rsi") {
        return `DIP<=${rule.thresholds.rsiDipThreshold} / TEPE>=${rule.thresholds.rsiTopThreshold}`
    }
    if (rule.indicator === "wr") {
        return `DIP<=${rule.thresholds.wrDipThreshold} / TEPE>=${rule.thresholds.wrTopThreshold}`
    }
    if (rule.indicator === "combo") {
        return `DIP>=${rule.thresholds.comboDipThreshold} / TEPE>=${rule.thresholds.comboTopThreshold}`
    }
    return `DIP>=${rule.thresholds.hunterDipThreshold} / TEPE>=${rule.thresholds.hunterTopThreshold}`
}

const formatSide = (side: AlarmSide) => (side === "dip" ? "DIP" : "TEPE")

export default function AlarmsPage() {
    const [watchlists, setWatchlists] = useState<StoredWatchlistModel[]>([])
    const [alarmRules, setAlarmRules] = useState<WatchlistAlarmRule[]>([])
    const [runtimeByRuleId, setRuntimeByRuleId] = useState<Record<string, RuleRuntimeState>>({})
    const [isChecking, setIsChecking] = useState(false)
    const [lastCheckedAt, setLastCheckedAt] = useState<string | null>(null)
    const [hydrated, setHydrated] = useState(false)

    const hydrateFromStorage = useCallback(() => {
        setWatchlists(loadStoredWatchlists())
        setAlarmRules(loadWatchlistAlarmRules())
        setHydrated(true)
    }, [])

    useEffect(() => {
        hydrateFromStorage()
    }, [hydrateFromStorage])

    useEffect(() => {
        if (!hydrated) return
        saveWatchlistAlarmRules(alarmRules)
    }, [alarmRules, hydrated])

    useEffect(() => {
        const onStorage = (event: StorageEvent) => {
            if (!event.key) return
            if (event.key === WATCHLIST_STORAGE_KEY || event.key === WATCHLIST_ALARMS_STORAGE_KEY) {
                hydrateFromStorage()
            }
        }
        window.addEventListener("storage", onStorage)
        return () => window.removeEventListener("storage", onStorage)
    }, [hydrateFromStorage])

    const watchlistById = useMemo(
        () => new Map(watchlists.map((watchlist) => [watchlist.id, watchlist])),
        [watchlists]
    )

    const evaluateRules = useCallback(async () => {
        if (!hydrated) return
        setIsChecking(true)
        try {
            const enabledRules = alarmRules.filter((rule) => rule.enabled)
            const nextRuntime: Record<string, RuleRuntimeState> = {}

            for (const rule of enabledRules) {
                const watchlist = watchlistById.get(rule.watchlistId)
                if (!watchlist) {
                    nextRuntime[rule.id] = {
                        checkedAt: new Date().toISOString(),
                        checkedSymbols: 0,
                        triggerHits: [],
                        errors: ["Liste bulunamadi"],
                    }
                    continue
                }

                if (!watchlist.alarmsEnabled) {
                    nextRuntime[rule.id] = {
                        checkedAt: new Date().toISOString(),
                        checkedSymbols: 0,
                        triggerHits: [],
                        errors: ["Bu liste icin alarmlar kapali"],
                    }
                    continue
                }

                const symbols = toWatchlistSymbols(watchlist)
                const hits: TriggerHit[] = []
                const errors: string[] = []

                const symbolResults = await Promise.all(
                    symbols.map(async (row) => {
                        try {
                            const candles = await fetchCandles(row.rawSymbol, row.marketType, rule.timeframe, 320)
                            const evaluated = evaluateWatchlistAlarmRule(rule, candles.candles)
                            return {
                                row,
                                evaluated,
                            }
                        } catch (error) {
                            return {
                                row,
                                evaluated: null,
                                error:
                                    error instanceof Error
                                        ? error.message
                                        : "Veri cekimi basarisiz",
                            }
                        }
                    })
                )

                for (const item of symbolResults) {
                    if ("error" in item && item.error) {
                        errors.push(`${item.row.rawSymbol}: ${item.error}`)
                        continue
                    }
                    if (!item.evaluated || !item.evaluated.triggered || !item.evaluated.side) continue
                    hits.push({
                        symbol: item.row.rawSymbol,
                        marketType: item.row.marketType,
                        side: item.evaluated.side,
                        detail: item.evaluated.detail,
                        value: item.evaluated.value,
                    })
                }

                nextRuntime[rule.id] = {
                    checkedAt: new Date().toISOString(),
                    checkedSymbols: symbols.length,
                    triggerHits: hits,
                    errors,
                }
            }

            setRuntimeByRuleId(nextRuntime)
            setLastCheckedAt(new Date().toISOString())
        } finally {
            setIsChecking(false)
        }
    }, [alarmRules, hydrated, watchlistById])

    useEffect(() => {
        if (!hydrated) return
        evaluateRules()
        const timer = window.setInterval(() => evaluateRules(), 60_000)
        return () => window.clearInterval(timer)
    }, [evaluateRules, hydrated])

    const handleToggleRule = useCallback((ruleId: string) => {
        setAlarmRules((prev) =>
            prev.map((rule) =>
                rule.id === ruleId
                    ? { ...rule, enabled: !rule.enabled, updatedAt: new Date().toISOString() }
                    : rule
            )
        )
    }, [])

    const handleDeleteRule = useCallback((ruleId: string) => {
        setAlarmRules((prev) => prev.filter((rule) => rule.id !== ruleId))
        setRuntimeByRuleId((prev) => {
            const next = { ...prev }
            delete next[ruleId]
            return next
        })
    }, [])

    const triggeredTotal = useMemo(
        () =>
            Object.values(runtimeByRuleId).reduce(
                (sum, runtime) => sum + runtime.triggerHits.length,
                0
            ),
        [runtimeByRuleId]
    )

    const enabledRulesCount = useMemo(
        () => alarmRules.filter((rule) => rule.enabled).length,
        [alarmRules]
    )

    return (
        <div className="flex h-full min-h-[calc(100vh-40px)] flex-col gap-3 p-3 md:min-h-screen md:p-4">
            <section className="border border-border bg-surface p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <div className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">Frontend Alarm Merkezi</div>
                        <h1 className="mt-1 text-xl font-semibold">/alarms</h1>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Bu sayfa sadece frontend alarm kurallarini calistirir. Bot sinyal/telegram ayarlarindan bagimsizdir.
                        </p>
                    </div>
                    <button
                        onClick={evaluateRules}
                        className={cn(
                            "inline-flex items-center gap-2 rounded border border-border px-3 py-1.5 text-xs",
                            isChecking ? "opacity-70" : "hover:bg-raised"
                        )}
                    >
                        <RefreshCw className={cn("h-3.5 w-3.5", isChecking && "animate-spin")} />
                        Simdi kontrol et
                    </button>
                </div>
            </section>

            <section className="grid grid-cols-2 gap-2 md:grid-cols-4">
                <div className="border border-border bg-surface p-3">
                    <div className="text-[11px] uppercase text-muted-foreground">Toplam kural</div>
                    <div className="mt-1 text-lg font-semibold">{alarmRules.length}</div>
                </div>
                <div className="border border-border bg-surface p-3">
                    <div className="text-[11px] uppercase text-muted-foreground">Aktif kural</div>
                    <div className="mt-1 text-lg font-semibold">{enabledRulesCount}</div>
                </div>
                <div className="border border-border bg-surface p-3">
                    <div className="text-[11px] uppercase text-muted-foreground">Tetik sayisi</div>
                    <div className="mt-1 text-lg font-semibold">{triggeredTotal}</div>
                </div>
                <div className="border border-border bg-surface p-3">
                    <div className="text-[11px] uppercase text-muted-foreground">Son kontrol</div>
                    <div className="mt-1 text-xs">
                        {lastCheckedAt ? new Date(lastCheckedAt).toLocaleString("tr-TR") : "--"}
                    </div>
                </div>
            </section>

            <section className="flex min-h-0 flex-1 flex-col gap-2 border border-border bg-surface p-3">
                <div className="text-xs text-muted-foreground">
                    Kurallari chart ekraninin sag panelindeki alarmlar ikonundan olusturabilirsiniz.
                </div>

                <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
                    {alarmRules.length === 0 && (
                        <div className="rounded border border-border/50 bg-base px-3 py-4 text-sm text-muted-foreground">
                            Alarm kurali yok. `/chart` sayfasinda bir watchlist icin alarm ekleyin.
                        </div>
                    )}

                    {alarmRules.map((rule) => {
                        const runtime = runtimeByRuleId[rule.id]
                        const timeframeLabel =
                            ALARM_TIMEFRAME_OPTIONS.find((item) => item.value === rule.timeframe)?.label || rule.timeframe
                        const indicatorLabel =
                            ALARM_INDICATOR_OPTIONS.find((item) => item.value === rule.indicator)?.label || rule.indicator

                        return (
                            <article key={rule.id} className="rounded border border-border/60 bg-base p-3">
                                <div className="flex flex-wrap items-start justify-between gap-2">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <Bell className="h-3.5 w-3.5 text-primary" />
                                            <span className="text-sm font-semibold">{indicatorLabel}</span>
                                            <span className="text-[11px] text-muted-foreground">{timeframeLabel}</span>
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            {rule.watchlistName} • {formatThresholdSummary(rule)}
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-1">
                                        <button
                                            onClick={() => handleToggleRule(rule.id)}
                                            className={cn(
                                                "rounded px-2 py-1 text-[11px]",
                                                rule.enabled
                                                    ? "bg-primary text-primary-foreground"
                                                    : "bg-raised text-muted-foreground"
                                            )}
                                        >
                                            {rule.enabled ? "Acik" : "Kapali"}
                                        </button>
                                        <button
                                            onClick={() => handleDeleteRule(rule.id)}
                                            className="rounded p-1 text-muted-foreground hover:bg-loss/10 hover:text-loss"
                                            title="Kurali sil"
                                        >
                                            <Trash2 className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                </div>

                                <div className="mt-2 text-[11px] text-muted-foreground">
                                    Son kontrol: {runtime?.checkedAt ? new Date(runtime.checkedAt).toLocaleString("tr-TR") : "--"} • Kontrol edilen sembol: {runtime?.checkedSymbols ?? 0}
                                </div>

                                {runtime?.errors && runtime.errors.length > 0 && (
                                    <div className="mt-2 rounded border border-loss/30 bg-loss/10 px-2 py-1 text-[11px] text-loss">
                                        {runtime.errors[0]}
                                        {runtime.errors.length > 1 ? ` (+${runtime.errors.length - 1} hata)` : ""}
                                    </div>
                                )}

                                <div className="mt-2 space-y-1">
                                    {runtime?.triggerHits && runtime.triggerHits.length > 0 ? (
                                        runtime.triggerHits.map((hit) => (
                                            <div
                                                key={`${rule.id}-${hit.symbol}-${hit.side}`}
                                                className={cn(
                                                    "flex items-center justify-between rounded px-2 py-1 text-[11px]",
                                                    hit.side === "dip"
                                                        ? "bg-profit/10 text-profit"
                                                        : "bg-loss/10 text-loss"
                                                )}
                                            >
                                                <span>{hit.symbol} ({hit.marketType}) • {formatSide(hit.side)}</span>
                                                <span>{hit.value !== null ? hit.value.toFixed(2) : "--"}</span>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-[11px] text-muted-foreground">Tetik yok.</div>
                                    )}
                                </div>
                            </article>
                        )
                    })}
                </div>
            </section>
        </div>
    )
}

