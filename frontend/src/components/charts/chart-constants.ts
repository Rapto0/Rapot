import type { ComponentType } from "react"
import {
    Bell,
    CalendarDays,
    CircleHelp,
    LayoutGrid,
    MessageSquare,
} from "lucide-react"
import type { EconomicCalendarEvent } from "@/lib/api/client"
import { AVAILABLE_INDICATORS, type IndicatorMeta } from "@/lib/indicators"
import type { WorkerPaneSeriesResult } from "@/lib/types/indicator-worker"

export interface SignalMarker {
    time: string
    type: "AL" | "SAT"
    price: number
    label?: string
}

export type MarketType = "BIST" | "Kripto"

export interface ActiveIndicator {
    id: string
    meta: IndicatorMeta
    params: Record<string, number>
    visible: boolean
}

export interface PersistedActiveIndicator {
    id: string
    params: Record<string, number>
    visible: boolean
}

export interface WatchlistSymbolRow {
    kind: "symbol"
    rawSymbol: string
    marketType: MarketType
}

export interface WatchlistSectionRow {
    kind: "section"
    id: string
    title: string
}

export type WatchlistRow = WatchlistSymbolRow | WatchlistSectionRow

export interface WatchlistModel {
    id: string
    name: string
    alarmsEnabled: boolean
    notes: string
    rows: WatchlistRow[]
}

export type RightUtilityPanelId = "alerts" | "notes" | "calendar" | "layout" | "help"

export interface UtilityPanelItem {
    id: RightUtilityPanelId
    label: string
    icon: ComponentType<{ className?: string }>
}

export interface WorkerComputationState {
    requestId: number
    computeMs: number
    panes: Record<string, WorkerPaneSeriesResult>
    overlays: {
        combo: Array<{ time: string; signal: "AL" | "SAT" }>
        hunter: Array<{ time: string; signal: "AL" | "SAT" }>
    }
}

export type UtilityCalendarImpact = "Dusuk" | "Orta" | "Yuksek"

export interface UtilityCalendarItem {
    id: string
    date: string
    time: string
    country: string
    title: string
    impact: UtilityCalendarImpact
    actual: string
    forecast: string
    previous: string
    orderKey: string
}

export type WatchlistDialogState =
    | { type: "addSymbol"; value: string }
    | { type: "renameWatchlist"; watchlistId: string; value: string }
    | { type: "createWatchlist"; value: string }
    | { type: "deleteWatchlist"; watchlistId: string; watchlistName: string }
    | { type: "clearWatchlist"; watchlistId: string; watchlistName: string }
    | { type: "clearWatchlistNotes"; watchlistId: string; watchlistName: string }
    | null

export const INDICATOR_SETTINGS_STORAGE_KEY = "rapot.dashboard.indicators.v1"
export const DEFAULT_OVERLAY_INDICATOR_IDS = ["combo", "hunter"] as const
export const WATCHLIST_STORAGE_KEY = "rapot.dashboard.watchlists.v1"
export const ACTIVE_WATCHLIST_STORAGE_KEY = "rapot.dashboard.watchlists.active.v1"
export const WATCHLIST_PANEL_STORAGE_KEY = "rapot.dashboard.watchlists.panel.v1"
export const WATCHLIST_UTILITY_CALENDAR_REFRESH_MS = 300_000

export const WATCHLIST_UTILITY_ITEMS: UtilityPanelItem[] = [
    { id: "alerts", label: "Alarmlar", icon: Bell },
    { id: "notes", label: "Notlar", icon: MessageSquare },
    { id: "calendar", label: "Takvim", icon: CalendarDays },
    { id: "layout", label: "Yerleşim", icon: LayoutGrid },
    { id: "help", label: "Yardım", icon: CircleHelp },
]

export const makeWatchlistId = (name: string) =>
    `${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now().toString(36)}`

export const symbolRow = (rawSymbol: string, marketType: MarketType): WatchlistSymbolRow => ({
    kind: "symbol",
    rawSymbol,
    marketType,
})

export const DEFAULT_WATCHLISTS: WatchlistModel[] = [
    {
        id: "binance-spot",
        name: "BINANCE SPOT",
        alarmsEnabled: false,
        notes: "",
        rows: [
            symbolRow("BTCUSDT", "Kripto"),
            symbolRow("ETHUSDT", "Kripto"),
            symbolRow("BNBUSDT", "Kripto"),
            symbolRow("XRPUSDT", "Kripto"),
            symbolRow("SOLUSDT", "Kripto"),
            symbolRow("DOGEUSDT", "Kripto"),
            symbolRow("ADAUSDT", "Kripto"),
            symbolRow("AVAXUSDT", "Kripto"),
        ],
    },
    {
        id: "gem",
        name: "Gem",
        alarmsEnabled: false,
        notes: "",
        rows: [
            symbolRow("ARBUSDT", "Kripto"),
            symbolRow("SEIUSDT", "Kripto"),
            symbolRow("INJUSDT", "Kripto"),
            symbolRow("TIAUSDT", "Kripto"),
            symbolRow("SUIUSDT", "Kripto"),
        ],
    },
    {
        id: "global",
        name: "Global",
        alarmsEnabled: false,
        notes: "",
        rows: [
            symbolRow("BTCUSDT", "Kripto"),
            symbolRow("ETHUSDT", "Kripto"),
            symbolRow("THYAO", "BIST"),
            symbolRow("GARAN", "BIST"),
            symbolRow("ASELS", "BIST"),
        ],
    },
    {
        id: "bist-portfolio",
        name: "BIST Portföy",
        alarmsEnabled: false,
        notes: "",
        rows: [
            symbolRow("THYAO", "BIST"),
            symbolRow("ASELS", "BIST"),
            symbolRow("EREGL", "BIST"),
            symbolRow("BIMAS", "BIST"),
            symbolRow("KCHOL", "BIST"),
        ],
    },
]

export const getDefaultActiveIndicators = (): ActiveIndicator[] => {
    const defaults: ActiveIndicator[] = []
    for (const id of DEFAULT_OVERLAY_INDICATOR_IDS) {
        const meta = AVAILABLE_INDICATORS.find((indicator) => indicator.id === id)
        if (!meta) continue
        defaults.push({
            id,
            meta,
            params: { ...meta.defaultParams },
            visible: true,
        })
    }
    return defaults
}

export const TIMEFRAME_CATEGORIES = [
    {
        category: "Dakika",
        items: [
            { label: "1D", value: "1m", description: "1 Dakika" },
            { label: "5D", value: "5m", description: "5 Dakika" },
            { label: "15D", value: "15m", description: "15 Dakika" },
            { label: "30D", value: "30m", description: "30 Dakika" },
        ],
    },
    {
        category: "Saat",
        items: [
            { label: "1S", value: "1h", description: "1 Saat" },
            { label: "2S", value: "2h", description: "2 Saat" },
            { label: "4S", value: "4h", description: "4 Saat" },
            { label: "8S", value: "8h", description: "8 Saat" },
            { label: "12S", value: "12h", description: "12 Saat" },
        ],
    },
    {
        category: "Gün",
        items: [
            { label: "1G", value: "1d", description: "1 Gün" },
            { label: "2G", value: "2d", description: "2 Gün" },
            { label: "3G", value: "3d", description: "3 Gün" },
            { label: "4G", value: "4d", description: "4 Gün" },
            { label: "5G", value: "5d", description: "5 Gün" },
            { label: "6G", value: "6d", description: "6 Gün" },
        ],
    },
    {
        category: "Hafta",
        items: [
            { label: "1H", value: "1wk", description: "1 Hafta" },
            { label: "2H", value: "2wk", description: "2 Hafta" },
            { label: "3H", value: "3wk", description: "3 Hafta" },
        ],
    },
    {
        category: "Ay",
        items: [
            { label: "1A", value: "1mo", description: "1 Ay" },
            { label: "2A", value: "2mo", description: "2 Ay" },
            { label: "3A", value: "3mo", description: "3 Ay" },
        ],
    },
]

export const QUICK_TIMEFRAMES = [
    { label: "1D", value: "1m" },
    { label: "5D", value: "5m" },
    { label: "1S", value: "1h" },
    { label: "4S", value: "4h" },
    { label: "1G", value: "1d" },
    { label: "1H", value: "1wk" },
    { label: "1A", value: "1mo" },
]

export const BIST_ALLOWED_TIMEFRAMES = new Set([
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "1d",
    "2d",
    "3d",
    "4d",
    "5d",
    "6d",
    "1wk",
    "2wk",
    "3wk",
    "1mo",
    "2mo",
    "3mo",
])

export const CRYPTO_WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "SOLUSDT", "DOTUSDT", "POLUSDT", "LTCUSDT",
]

export const DEV_PERF_ENABLED = process.env.NODE_ENV !== "production"
export const DEV_PERF_THROTTLE_MS = 2000

export const chartColors = {
    background: "transparent",
    text: "rgba(255, 255, 255, 0.5)",
    grid: "rgba(255, 255, 255, 0.04)",
    crosshair: "rgba(255, 255, 255, 0.18)",
    crosshairLabel: "#16161e",
    bullish: "#22c55e",
    bearish: "#ef4444",
    volume: {
        up: "rgba(34, 197, 94, 0.18)",
        down: "rgba(239, 68, 68, 0.18)",
    },
    indicators: {
        rsi: "#3b82f6",
        macd: "#8b5cf6",
        macdSignal: "#06b6d4",
        macdHistogram: "rgba(255, 255, 255, 0.28)",
        wr: "#8b5cf6",
        cci: "#3b82f6",
    },
}

export const DATE_ONLY_RE = /^(\d{4})-(\d{2})-(\d{2})$/
export const INTRADAY_RE = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/

export const normalizeHorzTimeToUnix = (value: unknown): number | null => {
    if (typeof value === "number" && Number.isFinite(value)) {
        return Math.floor(value)
    }
    if (typeof value === "string") {
        if (!value.trim()) return null
        return parseChartTimeToUnix(value)
    }
    if (value && typeof value === "object" && "year" in value && "month" in value && "day" in value) {
        const typed = value as { year: number; month: number; day: number }
        return Math.floor(Date.UTC(typed.year, typed.month - 1, typed.day, 0, 0, 0) / 1000)
    }
    return null
}

export const getTimeframeStepSeconds = (timeframe: string): number => {
    const mapping: Record<string, number> = {
        "1m": 60,
        "5m": 5 * 60,
        "15m": 15 * 60,
        "30m": 30 * 60,
        "1h": 60 * 60,
        "2h": 2 * 60 * 60,
        "4h": 4 * 60 * 60,
        "8h": 8 * 60 * 60,
        "12h": 12 * 60 * 60,
        "18h": 18 * 60 * 60,
        "1d": 24 * 60 * 60,
        "2d": 2 * 24 * 60 * 60,
        "3d": 3 * 24 * 60 * 60,
        "4d": 4 * 24 * 60 * 60,
        "5d": 5 * 24 * 60 * 60,
        "6d": 6 * 24 * 60 * 60,
        "1wk": 7 * 24 * 60 * 60,
        "2wk": 14 * 24 * 60 * 60,
        "3wk": 21 * 24 * 60 * 60,
        "1mo": 30 * 24 * 60 * 60,
        "2mo": 60 * 24 * 60 * 60,
        "3mo": 90 * 24 * 60 * 60,
    }
    return mapping[timeframe] ?? 24 * 60 * 60
}

export const findNearestSeriesPointByTime = (
    points: Array<{ timeKey: number; rawTime: string | number; value: number }>,
    targetTime: number
): { timeKey: number; rawTime: string | number; value: number } | null => {
    if (points.length === 0) return null

    let left = 0
    let right = points.length - 1
    while (left <= right) {
        const mid = Math.floor((left + right) / 2)
        const current = points[mid].timeKey
        if (current === targetTime) return points[mid]
        if (current < targetTime) left = mid + 1
        else right = mid - 1
    }

    const leftPoint = left < points.length ? points[left] : null
    const rightPoint = right >= 0 ? points[right] : null
    if (!leftPoint) return rightPoint
    if (!rightPoint) return leftPoint
    return Math.abs(leftPoint.timeKey - targetTime) < Math.abs(rightPoint.timeKey - targetTime)
        ? leftPoint
        : rightPoint
}

export const buildMarkerHash = (
    markers: Array<{ time: string | number; text?: string; position?: string; color?: string }>
): string => {
    if (markers.length === 0) return "0"
    let hash = 17
    for (let i = 0; i < markers.length; i++) {
        const marker = markers[i]
        const encoded = `${marker.time}|${marker.text || ""}|${marker.position || ""}|${marker.color || ""}`
        for (let j = 0; j < encoded.length; j++) {
            hash = (hash * 31 + encoded.charCodeAt(j)) >>> 0
        }
    }
    return `${markers.length}:${hash}`
}

// Keep data timestamps unchanged: Borsapy BIST supplies offset-aware ISO values,
// and stream epochs refer to the same instant. Timezone-free legacy crypto values
// remain UTC; daily date strings preserve their calendar date. Exchange-time labels
// are formatted separately. Legacy naive BIST wall-times are not used by this UI.
export const parseChartTimeToUnix = (timeStr: string): number => {
    const value = timeStr.trim()
    const intradayMatch = value.match(INTRADAY_RE)
    if (intradayMatch) {
        const year = Number(intradayMatch[1])
        const month = Number(intradayMatch[2])
        const day = Number(intradayMatch[3])
        const hour = Number(intradayMatch[4])
        const minute = Number(intradayMatch[5])
        const second = Number(intradayMatch[6] || "0")
        return Math.floor(Date.UTC(year, month - 1, day, hour, minute, second) / 1000)
    }

    const dateOnlyMatch = value.match(DATE_ONLY_RE)
    if (dateOnlyMatch) {
        const year = Number(dateOnlyMatch[1])
        const month = Number(dateOnlyMatch[2])
        const day = Number(dateOnlyMatch[3])
        return Math.floor(Date.UTC(year, month - 1, day, 0, 0, 0) / 1000)
    }

    const parsed = Date.parse(value)
    if (!Number.isNaN(parsed)) {
        return Math.floor(parsed / 1000)
    }
    return 0
}

export const formatTime = (timeStr: string): string | number => {
    if (timeStr.includes(" ") || timeStr.includes("T")) {
        return parseChartTimeToUnix(timeStr)
    }
    return timeStr
}

export const deduplicateByTime = <T extends { time: string | number }>(data: T[]): T[] => {
    const seen = new Map<string | number, T>()
    for (const item of data) {
        seen.set(item.time, item)
    }
    return Array.from(seen.values()).sort((a, b) => {
        const timeA = typeof a.time === "number" ? a.time : parseChartTimeToUnix(a.time)
        const timeB = typeof b.time === "number" ? b.time : parseChartTimeToUnix(b.time)
        return timeA - timeB
    })
}

const mapUtilityCalendarImpact = (value: string | null): UtilityCalendarImpact => {
    const normalized = (value || "").toLowerCase()
    if (normalized.includes("high") || normalized === "3" || normalized.includes("critical")) return "Yuksek"
    if (normalized.includes("medium") || normalized === "2" || normalized.includes("med")) return "Orta"
    return "Dusuk"
}

const formatUtilityCalendarMetric = (value: number | string | null, unit: string | null): string => {
    if (value === null || value === undefined) return ""
    if (typeof value === "string") return value
    const numeric = Number(value)
    const formatted = Number.isInteger(numeric) ? numeric.toString() : numeric.toFixed(2)
    return `${formatted}${unit || ""}`
}

const parseUtilityCalendarDateTime = (
    value: string | null
): { date: string; time: string; orderKey: string } | null => {
    if (!value) return null
    const direct = value.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/)
    if (direct) {
        const date = direct[1]
        const time = direct[2]
        return { date, time, orderKey: `${date}T${time}` }
    }

    const normalized = value.includes("T") ? value : value.replace(" ", "T")
    const dateObj = new Date(normalized)
    if (Number.isNaN(dateObj.getTime())) return null

    return {
        date: dateObj.toISOString().slice(0, 10),
        time: dateObj.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }),
        orderKey: dateObj.toISOString(),
    }
}

export const buildUtilityCalendarItems = (rawEvents: EconomicCalendarEvent[]): UtilityCalendarItem[] => {
    return rawEvents
        .map((event, index) => {
            const parsed = event.date
                ? {
                    date: event.date,
                    time: event.source_time || "Saat belirsiz",
                    orderKey: `${event.date}T${event.source_time || "99:99"}`,
                }
                : parseUtilityCalendarDateTime(event.time)
            if (!parsed) return null
            return {
                id: `${parsed.orderKey}-${event.country || "ROW"}-${index}`,
                date: parsed.date,
                time: parsed.time,
                country: (event.country || event.currency || "ROW").toUpperCase(),
                title: event.event || "Ekonomik veri",
                impact: mapUtilityCalendarImpact(event.impact),
                actual: formatUtilityCalendarMetric(event.actual, event.unit),
                forecast: formatUtilityCalendarMetric(event.estimate, event.unit),
                previous: formatUtilityCalendarMetric(event.previous, event.unit),
                orderKey: parsed.orderKey,
            }
        })
        .filter((item): item is UtilityCalendarItem => item !== null)
        .sort((a, b) => a.orderKey.localeCompare(b.orderKey))
}
