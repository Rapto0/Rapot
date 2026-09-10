import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { fetchCandles } from "@/lib/api/client"
import { alarmConfigurationKey, createLocalAlarmMonitor, type LocalAlarmSnapshot } from "@/lib/local-alarm-monitor"
import type { StoredWatchlistModel, WatchlistAlarmRule } from "@/lib/watchlist-alarms"

const EMPTY: LocalAlarmSnapshot = { key: "", isChecking: false, lastCheckedAt: null, runtimeByRuleId: {} }

export function useLocalAlarms(rules: WatchlistAlarmRule[], watchlists: StoredWatchlistModel[], hydrated: boolean) {
    const [snapshot, setSnapshot] = useState<LocalAlarmSnapshot>(EMPTY)
    const monitor = useRef<ReturnType<typeof createLocalAlarmMonitor> | null>(null)
    const configuration = useMemo(() => ({ rules, watchlists }), [rules, watchlists])
    const key = alarmConfigurationKey(configuration)

    useEffect(() => {
        const instance = createLocalAlarmMonitor({
            readCandles: async (row, rule, signal) => {
                const response = await fetchCandles(row.rawSymbol, row.marketType, rule.timeframe, 320, { signal })
                return response.candles
            },
            onUpdate: setSnapshot,
        })
        monitor.current = instance
        return () => {
            instance.dispose()
            if (monitor.current === instance) monitor.current = null
        }
    }, [])

    useEffect(() => {
        if (hydrated) void monitor.current?.replace(configuration)
    }, [configuration, hydrated])

    const run = useCallback(() => monitor.current?.run() ?? Promise.resolve(), [])
    // A render with edited/deleted rules cannot briefly display results from the old configuration.
    const visible = hydrated && snapshot.key === key ? snapshot : EMPTY
    return { ...visible, isChecking: hydrated && (snapshot.key !== key || snapshot.isChecking), run }
}
