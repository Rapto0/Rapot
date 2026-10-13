import { API_BASE_URL, fetchApi } from "./core"

export type CustomInputs = Record<string, string | number | boolean>
export interface CustomInputSpec {
    key: string
    label: string
    type: "bool" | "int" | "float" | "timeframe" | "string"
    default: string | number | boolean
    group: string
    min?: number
    max?: number
    step?: number
    options?: Array<string | { value: string; label: string }>
    visual?: boolean
    tooltip?: string
}
export interface CustomOutputSpec { key: string; label: string; kind: "number" | "boolean" }
export interface CustomIndicatorSpec {
    id: string
    name: string
    inputs: CustomInputSpec[]
    outputs: CustomOutputSpec[]
    base_policy: "any" | "daily" | "minimum"
}
export interface CustomCatalog { version: string | number; indicators: CustomIndicatorSpec[]; max_history_bars: number }
export interface CustomPreviewRequest {
    indicator: string
    inputs: CustomInputs
    symbol: string
    market_type: "BIST" | "Kripto"
    chart_timeframe: string
}
export interface CustomPoint {
    time: number
    end?: number | null
    confirmed: boolean
    outputs: Record<string, number | null>
    rows: Array<Record<string, string | number | boolean | null>>
    ready: boolean
    reason?: string | null
}
export interface CustomPreview {
    state: string
    reason?: string | null
    source: string
    received_at?: string | number | null
    points: CustomPoint[]
    latest: CustomPoint | null
    requirements: unknown[]
    limits: Record<string, number | string | boolean>
}
const root = `${API_BASE_URL}/advanced-alarms/indicators`
export const fetchCustomIndicatorCatalog = (signal?: AbortSignal): Promise<CustomCatalog> => fetchApi(`${root}/catalog`, { signal })
export const previewCustomIndicator = (payload: CustomPreviewRequest, signal?: AbortSignal): Promise<CustomPreview> =>
    fetchApi(`${root}/preview`, { method: "POST", body: JSON.stringify(payload), signal })
