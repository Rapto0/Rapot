import {
    normalizeWatchlistAlarmRules,
    WATCHLIST_ALARMS_STORAGE_KEY,
    type WatchlistAlarmRule,
} from "@/lib/watchlist-alarms"

type AlarmStorage = Pick<Storage, "getItem" | "setItem">
export type AlarmRuleStorageResult =
    | { ok: true; rules: WatchlistAlarmRule[] }
    | { ok: false }

export type AlarmRuleChange =
    | { type: "add"; rule: WatchlistAlarmRule }
    | { type: "set-enabled"; id: string; enabled: boolean; updatedAt: string }
    | { type: "remove"; id: string }
    | { type: "rename-watchlist"; watchlistId: string; name: string; updatedAt: string }
    | { type: "remove-watchlist"; watchlistId: string }

export function readAlarmRuleStorage(storage?: AlarmStorage): AlarmRuleStorageResult {
    try {
        const source = storage ?? window.localStorage
        const raw = source.getItem(WATCHLIST_ALARMS_STORAGE_KEY)
        const parsed: unknown = raw === null ? [] : JSON.parse(raw)
        if (!Array.isArray(parsed)) return { ok: false }
        const rules = normalizeWatchlistAlarmRules(parsed)
        // Refuse a write that would silently discard malformed or ambiguous saved rows.
        if (rules.length !== parsed.length || new Set(rules.map((rule) => rule.id)).size !== rules.length) {
            return { ok: false }
        }
        return { ok: true, rules }
    } catch {
        return { ok: false }
    }
}

// Apply user intent to the latest stored rules, never a React render's old snapshot.
// localStorage has no cross-tab transaction: truly simultaneous writes remain last-writer-wins.
export function updateAlarmRuleStorage(
    change: AlarmRuleChange,
    storage?: AlarmStorage
): AlarmRuleStorageResult {
    try {
        const source = storage ?? window.localStorage
        const current = readAlarmRuleStorage(source)
        if (!current.ok) return current
        let rules = current.rules
        switch (change.type) {
            case "add": {
                const valid = normalizeWatchlistAlarmRules([change.rule])
                if (valid.length !== 1) return { ok: false }
                if (!rules.some((rule) => rule.id === change.rule.id)) rules = [valid[0], ...rules]
                break
            }
            case "set-enabled":
                rules = rules.map((rule) => rule.id === change.id && rule.enabled !== change.enabled
                    ? { ...rule, enabled: change.enabled, updatedAt: change.updatedAt }
                    : rule)
                break
            case "remove":
                rules = rules.filter((rule) => rule.id !== change.id)
                break
            case "rename-watchlist":
                rules = rules.map((rule) => rule.watchlistId === change.watchlistId && rule.watchlistName !== change.name
                    ? { ...rule, watchlistName: change.name, updatedAt: change.updatedAt }
                    : rule)
                break
            case "remove-watchlist":
                rules = rules.filter((rule) => rule.watchlistId !== change.watchlistId)
                break
        }
        if (JSON.stringify(rules) !== JSON.stringify(current.rules)) {
            source.setItem(WATCHLIST_ALARMS_STORAGE_KEY, JSON.stringify(rules))
        }
        return { ok: true, rules }
    } catch {
        return { ok: false }
    }
}

export function subscribeAlarmRuleStorage(
    onChange: (result: AlarmRuleStorageResult) => void,
    target: Pick<Window, "localStorage" | "addEventListener" | "removeEventListener"> = window
): () => void {
    const refresh = () => {
        try {
            onChange(readAlarmRuleStorage(target.localStorage))
        } catch {
            onChange({ ok: false })
        }
    }
    const onStorage = (event: StorageEvent) => {
        if (event.key !== null && event.key !== WATCHLIST_ALARMS_STORAGE_KEY) return
        try {
            if (event.storageArea && event.storageArea !== target.localStorage) return
        } catch {
            onChange({ ok: false })
            return
        }
        // An event can be delayed; read current storage instead of replaying event.newValue.
        refresh()
    }
    target.addEventListener("storage", onStorage)
    refresh()
    return () => target.removeEventListener("storage", onStorage)
}
