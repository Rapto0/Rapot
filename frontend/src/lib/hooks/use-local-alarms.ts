import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { fetchCandles } from "@/lib/api/client"
import { alarmConfigurationKey, createLocalAlarmMonitor, type LocalAlarmSnapshot } from "@/lib/local-alarm-monitor"
import type { StoredWatchlistModel, WatchlistAlarmRule } from "@/lib/watchlist-alarms"
import { useSession } from "./use-session"

const EMPTY: LocalAlarmSnapshot = { key: "", isChecking: false, lastCheckedAt: null, runtimeByRuleId: {} }

export function useLocalAlarms(rules: WatchlistAlarmRule[], watchlists: StoredWatchlistModel[], hydrated: boolean) {
    const session = useSession()
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
    const sessionKey = session ? `${session.user.username}:${session.expiresAt}` : "guest"
    const [snapshot, setSnapshot] = useState<LocalAlarmSnapshot>(EMPTY)
    const monitor = useRef<ReturnType<typeof createLocalAlarmMonitor> | null>(null)
    const configuration = useMemo(() => ({ rules, watchlists }), [rules, watchlists])
    const key = alarmConfigurationKey(configuration)

    useEffect(() => {
        if (!allowed) return
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
    }, [allowed, sessionKey])

    useEffect(() => {
        if (hydrated && allowed) void monitor.current?.replace(configuration)
    }, [configuration, hydrated, allowed, sessionKey])

    const run = useCallback(() => monitor.current?.run() ?? Promise.resolve(), [])
    // A render with edited/deleted rules cannot briefly display results from the old configuration.
    const visible = allowed && hydrated && snapshot.key === key ? snapshot : EMPTY
    return { ...visible, isChecking: allowed && hydrated && (snapshot.key !== key || snapshot.isChecking), run }
}
