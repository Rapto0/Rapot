"use client"

import { useEffect, useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { fetchCandles } from "@/lib/api/market-api"
import { BORSAPY_INTERVALS, fetchBorsapyCandles, fetchBorsapyChartSnapshot, releaseBorsapyChart } from "@/lib/api/borsapy-chart-api"

const HISTORY_START_DELAY_MS = 900

export function useChartCandles(
    symbol: string, market: "BIST" | "Kripto", timeframe: string,
    allowed: boolean, username: string | undefined, expiresAt: number | undefined,
) {
    const bist = market === "BIST"
    const historySupported = allowed && (!bist || BORSAPY_INTERVALS.has(timeframe))
    const streamEnabled = bist && historySupported
    const scope = JSON.stringify([symbol, market, timeframe, username, expiresAt])
    const lease = useMemo(() => ({ scope: streamEnabled ? scope : "", id: "" }), [scope, streamEnabled])
    const [historyScope, setHistoryScope] = useState("")
    const stream = useQuery({
        queryKey: ["borsapy-chart-stream", symbol, timeframe, username, expiresAt],
        queryFn: ({ signal }) => {
            lease.id ||= crypto.randomUUID()
            return fetchBorsapyChartSnapshot(symbol, timeframe, signal, lease.id)
        },
        enabled: streamEnabled,
        refetchInterval: 1000,
        retry: false,
    })

    useEffect(() => {
        if (!lease.scope) return
        const timer = window.setTimeout(() => setHistoryScope(lease.scope), HISTORY_START_DELAY_MS)
        return () => {
            window.clearTimeout(timer)
            if (lease.id) void releaseBorsapyChart(symbol, timeframe, lease.id)
                .catch(() => { /* The server expires abandoned leases. */ })
        }
    }, [symbol, timeframe, lease])

    const history = useQuery({
        queryKey: ["chart-candles", symbol, market, timeframe, bist ? "borsapy" : "binance", username, expiresAt],
        queryFn: ({ signal }) => bist
            ? fetchBorsapyCandles(symbol, timeframe, signal)
            : fetchCandles(symbol, market, timeframe, 1000, { signal }),
        enabled: historySupported && (!streamEnabled || historyScope === scope ||
            stream.isError || Boolean(stream.data?.candles.length)),
        refetchInterval: 60_000,
        retry: false,
    })
    return { history, stream, streamEnabled, historySupported, scope }
}
