import {
    calculateRSI,
    calculateMACD,
    calculateWilliamsR,
    calculateCCI,
    calculateCombo,
    calculateHunter,
    type Candle,
} from "@/lib/indicators"
import type {
    IndicatorWorkerComputeRequest,
    IndicatorWorkerComputeResponse,
    WorkerHistogramPoint,
    WorkerIndicatorDescriptor,
    WorkerLinePoint,
    WorkerPaneSeriesResult,
} from "@/lib/types/indicator-worker"

const workerScope = self as unknown as {
    onmessage: ((event: MessageEvent<IndicatorWorkerComputeRequest>) => void) | null
    postMessage: (message: IndicatorWorkerComputeResponse) => void
}

const isFinitePoint = (value: number) => Number.isFinite(value) && !Number.isNaN(value)

function computePaneSeries(candles: Candle[], descriptor: WorkerIndicatorDescriptor): WorkerPaneSeriesResult | null {
    switch (descriptor.id) {
        case "rsi": {
            const period = descriptor.params.period || 14
            const line: WorkerLinePoint[] = calculateRSI(candles, period)
                .filter((point) => isFinitePoint(point.value))
                .map((point) => ({ time: point.time, value: point.value }))
            return { kind: "line", line }
        }
        case "wr": {
            const period = descriptor.params.period || 14
            const line: WorkerLinePoint[] = calculateWilliamsR(candles, period)
                .filter((point) => isFinitePoint(point.value))
                .map((point) => ({ time: point.time, value: point.value }))
            return { kind: "line", line }
        }
        case "cci": {
            const period = descriptor.params.period || 20
            const line: WorkerLinePoint[] = calculateCCI(candles, period)
                .filter((point) => isFinitePoint(point.value))
                .map((point) => ({ time: point.time, value: point.value }))
            return { kind: "line", line }
        }
        case "macd": {
            const fast = descriptor.params.fast || 12
            const slow = descriptor.params.slow || 26
            const signal = descriptor.params.signal || 9
            const macd = calculateMACD(candles, fast, slow, signal)

            const macdLine: WorkerLinePoint[] = macd
                .filter((point) => isFinitePoint(point.macd))
                .map((point) => ({ time: point.time, value: point.macd }))

            const signalLine: WorkerLinePoint[] = macd
                .filter((point) => isFinitePoint(point.signal))
                .map((point) => ({ time: point.time, value: point.signal }))

            const histogram: WorkerHistogramPoint[] = macd
                .filter((point) => isFinitePoint(point.histogram))
                .map((point) => ({
                    time: point.time,
                    value: point.histogram,
                    color: point.histogram >= 0 ? "rgba(0, 200, 83, 0.5)" : "rgba(255, 61, 0, 0.5)",
                }))

            return {
                kind: "macd",
                macd: macdLine,
                signal: signalLine,
                histogram,
            }
        }
        default:
            return null
    }
}

workerScope.onmessage = (event: MessageEvent<IndicatorWorkerComputeRequest>) => {
    const message = event.data
    if (!message || message.type !== "compute-indicators") {
        return
    }

    const start = performance.now()
    const panes: Record<string, WorkerPaneSeriesResult> = {}
    const overlays: IndicatorWorkerComputeResponse["overlays"] = {
        combo: [],
        hunter: [],
    }

    for (const indicator of message.indicators) {
        if (!indicator.visible) {
            continue
        }

        if (indicator.isOverlay) {
            if (indicator.id === "combo") {
                overlays.combo = calculateCombo(message.candles, indicator.params)
                    .filter((point) => point.signal === "AL" || point.signal === "SAT")
                    .map((point) => ({
                        time: point.time,
                        signal: point.signal as "AL" | "SAT",
                    }))
            } else if (indicator.id === "hunter") {
                overlays.hunter = calculateHunter(message.candles, indicator.params)
                    .filter((point) => point.signal === "AL" || point.signal === "SAT")
                    .map((point) => ({
                        time: point.time,
                        signal: point.signal as "AL" | "SAT",
                    }))
            }
            continue
        }

        const series = computePaneSeries(message.candles, indicator)
        if (series) {
            panes[indicator.id] = series
        }
    }

    const response: IndicatorWorkerComputeResponse = {
        type: "compute-indicators-result",
        requestId: message.requestId,
        computeMs: performance.now() - start,
        panes,
        overlays,
    }
    workerScope.postMessage(response)
}

export {}
