"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useLocalAlarms } from "@/lib/hooks/use-local-alarms"
import { readAlarmRuleStorage, updateAlarmRuleStorage, type AlarmRuleChange } from "@/lib/alarm-rule-storage"
import { cn } from "@/lib/utils"
import {
    ALARM_INDICATOR_OPTIONS,
    ALARM_TIMEFRAME_OPTIONS,
    WATCHLIST_STORAGE_KEY,
    WATCHLIST_ALARMS_STORAGE_KEY,
    loadStoredWatchlists,
    type StoredWatchlistModel,
    type WatchlistAlarmRule,
} from "@/lib/watchlist-alarms"
import { Bell, RefreshCw, Trash2 } from "lucide-react"

const RUNTIME_LABELS = {
    checking: "Kontrol ediliyor",
    disabled: "Kontrol kapalı",
    hit: "Tetik bulundu",
    no_hit: "Tetik yok.",
    no_data: "Veri yok; kural değerlendirilemedi.",
    unknown: "Sonuç bilinmiyor; gösterge değerlendirilemedi.",
    error: "Veri alınamadı; kontrol başarısız.",
    partial: "Kısmi kontrol; bazı semboller değerlendirilemedi.",
} as const

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

const formatSide = (side: "dip" | "top") => (side === "dip" ? "DIP" : "TEPE")

export default function AlarmsPage() {
    const [watchlists, setWatchlists] = useState<StoredWatchlistModel[]>([])
    const [alarmRules, setAlarmRules] = useState<WatchlistAlarmRule[]>([])
    const [hydrated, setHydrated] = useState(false)
    const [storageError, setStorageError] = useState<string | null>(null)
    const { runtimeByRuleId, isChecking, lastCheckedAt, run: evaluateRules } = useLocalAlarms(alarmRules, watchlists, hydrated)

    const hydrateFromStorage = useCallback(() => {
        setWatchlists(loadStoredWatchlists())
        const result = readAlarmRuleStorage()
        if (result.ok) {
            setAlarmRules(result.rules)
            setStorageError(null)
        } else {
            setStorageError("Yerel alarm kuralları okunamadı. Kayıtlar değiştirilmiyor.")
        }
        setHydrated(true)
    }, [])

    useEffect(() => {
        hydrateFromStorage()
    }, [hydrateFromStorage])

    useEffect(() => {
        const onStorage = (event: StorageEvent) => {
            if (event.key === null || event.key === WATCHLIST_STORAGE_KEY || event.key === WATCHLIST_ALARMS_STORAGE_KEY) {
                hydrateFromStorage()
            }
        }
        window.addEventListener("storage", onStorage)
        return () => window.removeEventListener("storage", onStorage)
    }, [hydrateFromStorage])

    const applyRuleChange = useCallback((change: AlarmRuleChange) => {
        const result = updateAlarmRuleStorage(change)
        if (result.ok) {
            setAlarmRules(result.rules)
            setStorageError(null)
        } else {
            setStorageError("Alarm değişikliği kaydedilemedi. Yerel depolamayı kontrol edin; önceki kural korunuyor.")
        }
    }, [])

    const handleToggleRule = useCallback((ruleId: string) => {
        const rule = alarmRules.find((item) => item.id === ruleId)
        if (rule) applyRuleChange({ type: "set-enabled", id: ruleId, enabled: !rule.enabled, updatedAt: new Date().toISOString() })
    }, [alarmRules, applyRuleChange])

    const handleDeleteRule = useCallback((ruleId: string) => {
        applyRuleChange({ type: "remove", id: ruleId })
    }, [applyRuleChange])

    const triggeredTotal = useMemo(() => {
        const results = Object.values(runtimeByRuleId)
        return results.some((runtime) => runtime.checkedSymbols > 0)
            ? results.reduce((sum, runtime) => sum + runtime.triggerHits.length, 0)
            : null
    }, [runtimeByRuleId])

    const enabledRulesCount = useMemo(
        () => alarmRules.filter((rule) => rule.enabled).length,
        [alarmRules]
    )

    return (
        <div className="flex h-full min-h-[calc(100vh-40px)] flex-col gap-3 p-3 md:min-h-screen md:p-4">
            <section className="border border-border bg-surface p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <div className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">Yerel Alarm Merkezi</div>
                        <h1 className="mt-1 text-xl font-semibold">/alarms</h1>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Kurallar yalnız bu tarayıcıda saklanır ve bu sayfa açıkken yaklaşık 60 saniyede bir kontrol edilir. Önceki kontrol bitmeden yenisi başlamaz. Sayfa kapanınca kontroller durur; Telegram bildirimi veya 7/24 arka plan hizmeti değildir.
                        </p>
                    </div>
                    <button
                        onClick={() => void evaluateRules()}
                        disabled={isChecking || !hydrated}
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

            {storageError && <div role="alert" className="border border-border bg-surface p-3 text-xs text-muted-foreground">{storageError}</div>}

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
                    <div className="text-[11px] uppercase text-muted-foreground">Bulunan tetik</div>
                    <div className="mt-1 text-lg font-semibold">{triggeredTotal ?? "—"}</div>
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
                            {storageError ? "Yerel alarm kuralları okunamadı." : "Alarm kurali yok. `/chart` sayfasinda bir watchlist icin alarm ekleyin."}
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
                                    Son kontrol: {runtime?.checkedAt ? new Date(runtime.checkedAt).toLocaleString("tr-TR") : "--"} • Kontrol edilen sembol: {runtime?.checkedSymbols ?? "—"}
                                </div>

                                {runtime?.errors && runtime.errors.length > 0 && (
                                    <div className="mt-2 rounded border border-border px-2 py-1 text-[11px] text-muted-foreground">
                                        {runtime.errors[0]}
                                        {runtime.errors.length > 1 ? ` (+${runtime.errors.length - 1} değerlendirilemeyen sembol)` : ""}
                                    </div>
                                )}

                                {runtime?.state === "partial" && runtime.triggerHits.length > 0 && (
                                    <div className="mt-2 text-[11px] text-muted-foreground">{RUNTIME_LABELS.partial}</div>
                                )}
                                <div className="mt-2 space-y-1">
                                    {rule.enabled && !isChecking && runtime?.triggerHits && runtime.triggerHits.length > 0 ? (
                                        runtime.triggerHits.map((hit) => (
                                            <div
                                                key={`${rule.id}-${hit.marketType}-${hit.symbol}-${hit.side}`}
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
                                        <div className="text-[11px] text-muted-foreground">{!rule.enabled ? "Kural kapalı" : isChecking ? "Kontrol ediliyor" : runtime ? RUNTIME_LABELS[runtime.state] : "Henüz kontrol edilmedi"}</div>
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
