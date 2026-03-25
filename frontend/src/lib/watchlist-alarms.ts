import {
    calculateCombo,
    calculateHunter,
    calculateRSI,
    calculateWilliamsR,
    type Candle,
} from "@/lib/indicators"

export const WATCHLIST_STORAGE_KEY = "rapot.dashboard.watchlists.v1"
export const WATCHLIST_ALARMS_STORAGE_KEY = "rapot.dashboard.watchlist-alarms.v1"

export type AlarmTimeframe =
    | "4h"
    | "1d"
    | "2d"
    | "3d"
    | "4d"
    | "5d"
    | "6d"
    | "1wk"
    | "2wk"
    | "3wk"
    | "1mo"
    | "2mo"

export const ALARM_TIMEFRAME_OPTIONS: Array<{ value: AlarmTimeframe; label: string }> = [
    { value: "4h", label: "4 Saat" },
    { value: "1d", label: "1 Gün" },
    { value: "2d", label: "2 Gün" },
    { value: "3d", label: "3 Gün" },
    { value: "4d", label: "4 Gün" },
    { value: "5d", label: "5 Gün" },
    { value: "6d", label: "6 Gün" },
    { value: "1wk", label: "1 Hafta" },
    { value: "2wk", label: "2 Hafta" },
    { value: "3wk", label: "3 Hafta" },
    { value: "1mo", label: "1 Ay" },
    { value: "2mo", label: "2 Ay" },
]

export type AlarmIndicator = "rsi" | "wr" | "combo" | "hunter"

export const ALARM_INDICATOR_OPTIONS: Array<{ value: AlarmIndicator; label: string }> = [
    { value: "rsi", label: "RSI" },
    { value: "wr", label: "W%R" },
    { value: "combo", label: "COMBO" },
    { value: "hunter", label: "HUNTER" },
]

export type AlarmSide = "dip" | "top"

export interface AlarmThresholds {
    rsiDipThreshold: number
    rsiTopThreshold: number
    wrDipThreshold: number
    wrTopThreshold: number
    comboDipThreshold: number
    comboTopThreshold: number
    hunterDipThreshold: number
    hunterTopThreshold: number
}

export const DEFAULT_ALARM_THRESHOLDS: AlarmThresholds = {
    rsiDipThreshold: 30,
    rsiTopThreshold: 70,
    wrDipThreshold: -80,
    wrTopThreshold: -20,
    comboDipThreshold: 2,
    comboTopThreshold: 2,
    hunterDipThreshold: 3,
    hunterTopThreshold: 4,
}

export interface WatchlistAlarmRule {
    id: string
    watchlistId: string
    watchlistName: string
    indicator: AlarmIndicator
    timeframe: AlarmTimeframe
    enabled: boolean
    thresholds: AlarmThresholds
    createdAt: string
    updatedAt: string
}

export interface WatchlistSymbolRow {
    kind: "symbol"
    rawSymbol: string
    marketType: "BIST" | "Kripto"
}

export interface WatchlistSectionRow {
    kind: "section"
    id: string
    title: string
}

export type WatchlistRow = WatchlistSymbolRow | WatchlistSectionRow

export interface StoredWatchlistModel {
    id: string
    name: string
    alarmsEnabled: boolean
    notes: string
    rows: WatchlistRow[]
}

export interface AlarmEvaluationResult {
    triggered: boolean
    side: AlarmSide | null
    value: number | null
    detail: string
}

const makeAlarmId = () => `alarm-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`

export const createWatchlistAlarmRule = (
    watchlistId: string,
    watchlistName: string,
    indicator: AlarmIndicator,
    timeframe: AlarmTimeframe,
    thresholds: AlarmThresholds
): WatchlistAlarmRule => {
    const now = new Date().toISOString()
    return {
        id: makeAlarmId(),
        watchlistId,
        watchlistName,
        indicator,
        timeframe,
        enabled: true,
        thresholds: { ...thresholds },
        createdAt: now,
        updatedAt: now,
    }
}

const isAlarmIndicator = (value: unknown): value is AlarmIndicator =>
    value === "rsi" || value === "wr" || value === "combo" || value === "hunter"

const isAlarmTimeframe = (value: unknown): value is AlarmTimeframe =>
    ALARM_TIMEFRAME_OPTIONS.some((opt) => opt.value === value)

const clampThreshold = (value: unknown, fallback: number) =>
    typeof value === "number" && Number.isFinite(value) ? value : fallback

const normalizeThresholds = (value: unknown): AlarmThresholds => {
    if (!value || typeof value !== "object") {
        return { ...DEFAULT_ALARM_THRESHOLDS }
    }
    const raw = value as Partial<AlarmThresholds>
    return {
        rsiDipThreshold: clampThreshold(raw.rsiDipThreshold, DEFAULT_ALARM_THRESHOLDS.rsiDipThreshold),
        rsiTopThreshold: clampThreshold(raw.rsiTopThreshold, DEFAULT_ALARM_THRESHOLDS.rsiTopThreshold),
        wrDipThreshold: clampThreshold(raw.wrDipThreshold, DEFAULT_ALARM_THRESHOLDS.wrDipThreshold),
        wrTopThreshold: clampThreshold(raw.wrTopThreshold, DEFAULT_ALARM_THRESHOLDS.wrTopThreshold),
        comboDipThreshold: clampThreshold(raw.comboDipThreshold, DEFAULT_ALARM_THRESHOLDS.comboDipThreshold),
        comboTopThreshold: clampThreshold(raw.comboTopThreshold, DEFAULT_ALARM_THRESHOLDS.comboTopThreshold),
        hunterDipThreshold: clampThreshold(raw.hunterDipThreshold, DEFAULT_ALARM_THRESHOLDS.hunterDipThreshold),
        hunterTopThreshold: clampThreshold(raw.hunterTopThreshold, DEFAULT_ALARM_THRESHOLDS.hunterTopThreshold),
    }
}

export const normalizeWatchlistAlarmRules = (input: unknown): WatchlistAlarmRule[] => {
    if (!Array.isArray(input)) return []
    return input
        .map((entry): WatchlistAlarmRule | null => {
            if (!entry || typeof entry !== "object") return null
            const candidate = entry as Partial<WatchlistAlarmRule>
            if (typeof candidate.id !== "string" || typeof candidate.watchlistId !== "string") return null
            if (typeof candidate.watchlistName !== "string") return null
            if (!isAlarmIndicator(candidate.indicator)) return null
            if (!isAlarmTimeframe(candidate.timeframe)) return null
            return {
                id: candidate.id,
                watchlistId: candidate.watchlistId,
                watchlistName: candidate.watchlistName,
                indicator: candidate.indicator,
                timeframe: candidate.timeframe,
                enabled: candidate.enabled !== false,
                thresholds: normalizeThresholds(candidate.thresholds),
                createdAt: typeof candidate.createdAt === "string" ? candidate.createdAt : new Date().toISOString(),
                updatedAt: typeof candidate.updatedAt === "string" ? candidate.updatedAt : new Date().toISOString(),
            }
        })
        .filter((entry): entry is WatchlistAlarmRule => entry !== null)
}

export const loadWatchlistAlarmRules = (): WatchlistAlarmRule[] => {
    if (typeof window === "undefined") return []
    try {
        const raw = window.localStorage.getItem(WATCHLIST_ALARMS_STORAGE_KEY)
        if (!raw) return []
        return normalizeWatchlistAlarmRules(JSON.parse(raw))
    } catch {
        return []
    }
}

export const saveWatchlistAlarmRules = (rules: WatchlistAlarmRule[]) => {
    if (typeof window === "undefined") return
    window.localStorage.setItem(WATCHLIST_ALARMS_STORAGE_KEY, JSON.stringify(rules))
}

export const normalizeStoredWatchlists = (input: unknown): StoredWatchlistModel[] => {
    if (!Array.isArray(input)) return []
    return input
        .map((candidate): StoredWatchlistModel | null => {
            if (!candidate || typeof candidate !== "object") return null
            const item = candidate as Partial<StoredWatchlistModel>
            if (typeof item.id !== "string" || typeof item.name !== "string") return null

            const rows = Array.isArray(item.rows)
                ? item.rows
                      .map((row): WatchlistRow | null => {
                          if (!row || typeof row !== "object") return null
                          const maybeRow = row as Partial<WatchlistRow>
                          if (
                              maybeRow.kind === "symbol" &&
                              typeof (maybeRow as WatchlistSymbolRow).rawSymbol === "string" &&
                              (((maybeRow as WatchlistSymbolRow).marketType === "Kripto") ||
                                  ((maybeRow as WatchlistSymbolRow).marketType === "BIST"))
                          ) {
                              return {
                                  kind: "symbol",
                                  rawSymbol: (maybeRow as WatchlistSymbolRow).rawSymbol.toUpperCase(),
                                  marketType: (maybeRow as WatchlistSymbolRow).marketType,
                              }
                          }
                          if (
                              maybeRow.kind === "section" &&
                              typeof (maybeRow as WatchlistSectionRow).id === "string" &&
                              typeof (maybeRow as WatchlistSectionRow).title === "string"
                          ) {
                              return {
                                  kind: "section",
                                  id: (maybeRow as WatchlistSectionRow).id,
                                  title: (maybeRow as WatchlistSectionRow).title,
                              }
                          }
                          return null
                      })
                      .filter((row): row is WatchlistRow => row !== null)
                : []

            return {
                id: item.id,
                name: item.name,
                alarmsEnabled: item.alarmsEnabled === true,
                notes: typeof item.notes === "string" ? item.notes : "",
                rows,
            }
        })
        .filter((item): item is StoredWatchlistModel => item !== null)
}

export const loadStoredWatchlists = (): StoredWatchlistModel[] => {
    if (typeof window === "undefined") return []
    try {
        const raw = window.localStorage.getItem(WATCHLIST_STORAGE_KEY)
        if (!raw) return []
        return normalizeStoredWatchlists(JSON.parse(raw))
    } catch {
        return []
    }
}

const getLastFiniteValue = (values: number[]): number | null => {
    for (let i = values.length - 1; i >= 0; i--) {
        const value = values[i]
        if (typeof value === "number" && Number.isFinite(value)) return value
    }
    return null
}

export const evaluateWatchlistAlarmRule = (
    rule: WatchlistAlarmRule,
    candles: Candle[]
): AlarmEvaluationResult => {
    if (!candles || candles.length === 0) {
        return {
            triggered: false,
            side: null,
            value: null,
            detail: "Veri yok",
        }
    }

    if (rule.indicator === "rsi") {
        const latest = getLastFiniteValue(calculateRSI(candles, 14).map((item) => item.value))
        if (latest === null) return { triggered: false, side: null, value: null, detail: "RSI hesaplanamadi" }
        if (latest <= rule.thresholds.rsiDipThreshold) {
            return { triggered: true, side: "dip", value: latest, detail: `RSI <= ${rule.thresholds.rsiDipThreshold}` }
        }
        if (latest >= rule.thresholds.rsiTopThreshold) {
            return { triggered: true, side: "top", value: latest, detail: `RSI >= ${rule.thresholds.rsiTopThreshold}` }
        }
        return { triggered: false, side: null, value: latest, detail: "RSI esik disi" }
    }

    if (rule.indicator === "wr") {
        const latest = getLastFiniteValue(calculateWilliamsR(candles, 14).map((item) => item.value))
        if (latest === null) return { triggered: false, side: null, value: null, detail: "W%R hesaplanamadi" }
        if (latest <= rule.thresholds.wrDipThreshold) {
            return { triggered: true, side: "dip", value: latest, detail: `W%R <= ${rule.thresholds.wrDipThreshold}` }
        }
        if (latest >= rule.thresholds.wrTopThreshold) {
            return { triggered: true, side: "top", value: latest, detail: `W%R >= ${rule.thresholds.wrTopThreshold}` }
        }
        return { triggered: false, side: null, value: latest, detail: "W%R esik disi" }
    }

    if (rule.indicator === "combo") {
        const latest = calculateCombo(candles, {
            minBuyScore: Math.max(1, Math.round(rule.thresholds.comboDipThreshold)),
            minSellScore: Math.max(1, Math.round(rule.thresholds.comboTopThreshold)),
        }).at(-1)
        if (!latest) return { triggered: false, side: null, value: null, detail: "COMBO hesaplanamadi" }
        if (latest.buyScore >= rule.thresholds.comboDipThreshold && latest.signal === "AL") {
            return {
                triggered: true,
                side: "dip",
                value: latest.buyScore,
                detail: `COMBO AL skoru ${latest.buyScore.toFixed(0)} >= ${rule.thresholds.comboDipThreshold.toFixed(0)}`,
            }
        }
        if (latest.sellScore >= rule.thresholds.comboTopThreshold && latest.signal === "SAT") {
            return {
                triggered: true,
                side: "top",
                value: latest.sellScore,
                detail: `COMBO SAT skoru ${latest.sellScore.toFixed(0)} >= ${rule.thresholds.comboTopThreshold.toFixed(0)}`,
            }
        }
        return { triggered: false, side: null, value: null, detail: "COMBO esik disi" }
    }

    const latestHunter = calculateHunter(candles, {
        requiredDipScore: Math.max(1, Math.round(rule.thresholds.hunterDipThreshold)),
        requiredTopScore: Math.max(1, Math.round(rule.thresholds.hunterTopThreshold)),
    }).at(-1)
    if (!latestHunter) return { triggered: false, side: null, value: null, detail: "HUNTER hesaplanamadi" }
    if (latestHunter.dipScore >= rule.thresholds.hunterDipThreshold && latestHunter.signal === "AL") {
        return {
            triggered: true,
            side: "dip",
            value: latestHunter.dipScore,
            detail: `HUNTER DIP skoru ${latestHunter.dipScore.toFixed(0)} >= ${rule.thresholds.hunterDipThreshold.toFixed(0)}`,
        }
    }
    if (latestHunter.topScore >= rule.thresholds.hunterTopThreshold && latestHunter.signal === "SAT") {
        return {
            triggered: true,
            side: "top",
            value: latestHunter.topScore,
            detail: `HUNTER TEPE skoru ${latestHunter.topScore.toFixed(0)} >= ${rule.thresholds.hunterTopThreshold.toFixed(0)}`,
        }
    }
    return { triggered: false, side: null, value: null, detail: "HUNTER esik disi" }
}
