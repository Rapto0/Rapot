import { API_BASE_URL, fetchApi } from "./core"

export type AlarmCategory = "price" | "technical" | "watchlist"
export type AlarmTimeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d" | "1wk" | "1mo"
export type AlarmField = "price" | "open" | "high" | "low" | "close" | "volume" | "rsi" | "ema" | "sma" | "macd" | "macd_signal" | "atr" | "wr" | "combo" | "hunter"
export interface FieldRef { field: AlarmField; timeframe?: AlarmTimeframe; period?: number; side?: "buy" | "sell" }
export type CompareOp = "gt" | "gte" | "lt" | "lte" | "eq" | "crossed_above" | "crossed_below"
export interface ConditionLeaf { op: CompareOp; left: FieldRef; right: number | FieldRef }
export interface ConditionGroup { op: "and" | "or"; children: Condition[] }
export type Condition = ConditionLeaf | ConditionGroup
export interface AlarmSymbol { symbol: string; market_type: "BIST" | "Kripto" }
export interface AdvancedAlarmWrite {
    name: string
    category: AlarmCategory
    scope: "symbols" | "watchlist" | "all_bist"
    symbols: AlarmSymbol[]
    watchlist_id: string | null
    timeframe: AlarmTimeframe
    trigger: "intrabar" | "bar_close"
    condition: Condition
    mode: "on_enter" | "once_per_bar" | "cooldown"
    cooldown_seconds: number
    enabled: boolean
    notify_telegram: boolean
    revision?: number
}
export interface AdvancedAlarmRule extends AdvancedAlarmWrite {
    id: string
    revision: number
    created_at: string
    updated_at: string
    state: string
    last_triggered_at: string | null
    last_checked_at?: string | null
    last_error?: string | null
}
export interface ServerWatchlist {
    id: string
    name: string
    symbols: AlarmSymbol[]
    revision: number
    created_at: string
    updated_at: string
}
export interface AdvancedAlarmEvent {
    id: number
    rule_id: string
    rule_name: string
    category: AlarmCategory
    symbol: string
    market_type: string
    value: number | null
    values: Record<string, number>
    bar_time: string | null
    observed_at: string | null
    created_at: string
    delivery_status: string
    delivery_error: string | null
}
export interface AdvancedAlarmStatus {
    running: boolean
    last_cycle_at: string | null
    last_error: string | null
    evaluation: { total: number; checked: number; ready: number; backlog: number; cursor?: number[]; cycle_ms: number }
    market: Record<string, unknown>
    delivery: { pending: number; failed: number; sent: number }
    limits: Record<string, number>
    usage: Record<AlarmCategory, number>
    telegram_configured?: boolean
}
export interface AdvancedAlarmList {
    rules: AdvancedAlarmRule[]
    limits: Record<string, number>
    usage: Record<AlarmCategory, number>
    runtime: AdvancedAlarmStatus
}
const root = `${API_BASE_URL}/advanced-alarms`
export const fetchAdvancedAlarms = (signal?: AbortSignal): Promise<AdvancedAlarmList> => fetchApi(root, { signal })
export const fetchAdvancedAlarmStatus = (signal?: AbortSignal): Promise<AdvancedAlarmStatus> => fetchApi(`${root}/status`, { signal })
export const fetchAdvancedEvents = (afterId?: number, signal?: AbortSignal): Promise<{ events: AdvancedAlarmEvent[]; next_after_id: number; has_more: boolean }> =>
    fetchApi(`${root}/events?limit=100${afterId === undefined ? "" : `&after_id=${Math.max(0, Math.floor(afterId))}`}`, { signal })
export const saveAdvancedAlarm = (payload: AdvancedAlarmWrite, id?: string): Promise<AdvancedAlarmRule> =>
    fetchApi(id ? `${root}/${encodeURIComponent(id)}` : root, { method: id ? "PUT" : "POST", body: JSON.stringify(payload) })
export const removeAdvancedAlarm = (id: string): Promise<unknown> => fetchApi(`${root}/${encodeURIComponent(id)}`, { method: "DELETE" })
export const fetchServerWatchlists = (signal?: AbortSignal): Promise<{ watchlists: ServerWatchlist[] }> => fetchApi(`${root}/watchlists`, { signal })
export const saveServerWatchlist = (payload: { name: string; symbols: AlarmSymbol[]; revision?: number }, id?: string): Promise<ServerWatchlist> =>
    fetchApi(id ? `${root}/watchlists/${encodeURIComponent(id)}` : `${root}/watchlists`, { method: id ? "PUT" : "POST", body: JSON.stringify(payload) })
export const removeServerWatchlist = (id: string): Promise<unknown> => fetchApi(`${root}/watchlists/${encodeURIComponent(id)}`, { method: "DELETE" })
