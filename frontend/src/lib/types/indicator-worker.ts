import type { Candle } from "@/lib/indicators"

export interface WorkerIndicatorDescriptor {
    id: string
    params: Record<string, number>
    visible: boolean
    isOverlay: boolean
}

export interface WorkerLinePoint {
    time: string
    value: number
}

export interface WorkerHistogramPoint extends WorkerLinePoint {
    color: string
}

export interface WorkerLineSeriesResult {
    kind: "line"
    line: WorkerLinePoint[]
}

export interface WorkerMacdSeriesResult {
    kind: "macd"
    macd: WorkerLinePoint[]
    signal: WorkerLinePoint[]
    histogram: WorkerHistogramPoint[]
}

export type WorkerPaneSeriesResult = WorkerLineSeriesResult | WorkerMacdSeriesResult

export interface WorkerOverlaySignal {
    time: string
    signal: "AL" | "SAT"
}

export interface IndicatorWorkerComputeRequest {
    type: "compute-indicators"
    requestId: number
    candles: Candle[]
    indicators: WorkerIndicatorDescriptor[]
}

export interface IndicatorWorkerComputeResponse {
    type: "compute-indicators-result"
    requestId: number
    computeMs: number
    panes: Record<string, WorkerPaneSeriesResult>
    overlays: {
        combo: WorkerOverlaySignal[]
        hunter: WorkerOverlaySignal[]
    }
}
