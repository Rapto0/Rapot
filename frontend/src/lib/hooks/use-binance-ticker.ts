"use client"

import { useEffect, useMemo, useRef, useState } from "react"

interface TickerData {
    s: string // Symbol
    c: string // Last price (current price)
    p: string // Price change
    P: string // Price Change Percent
}

interface UseBinanceTickerOptions {
    paused?: boolean
}

export function useBinanceTicker(symbols: string[], options?: UseBinanceTickerOptions) {
    const paused = options?.paused === true
    const [prices, setPrices] = useState<Record<string, { price: number; change: number; priceChange: number }>>({})
    const ws = useRef<WebSocket | null>(null)
    const reconnectTimerRef = useRef<number | null>(null)
    const flushTimerRef = useRef<number | null>(null)
    const pendingUpdatesRef = useRef<Record<string, { price: number; change: number; priceChange: number }>>({})

    const symbolsKey = useMemo(() => {
        const unique = Array.from(
            new Set(
                symbols
                    .map((symbol) => symbol.trim().toUpperCase())
                    .filter(Boolean)
            )
        )
        unique.sort()
        return unique.join("|")
    }, [symbols])

    const normalizedSymbols = useMemo(
        () => (symbolsKey ? symbolsKey.split("|") : []),
        [symbolsKey]
    )

    useEffect(() => {
        if (paused || normalizedSymbols.length === 0) {
            if (reconnectTimerRef.current !== null) {
                window.clearTimeout(reconnectTimerRef.current)
                reconnectTimerRef.current = null
            }
            if (flushTimerRef.current !== null) {
                window.clearTimeout(flushTimerRef.current)
                flushTimerRef.current = null
            }
            pendingUpdatesRef.current = {}
            ws.current?.close(1000, paused ? "Paused" : "No symbols")
            ws.current = null
            return
        }

        let disposed = false
        let reconnectDelay = 1000
        let socket: WebSocket | null = null
        const activeSymbols = new Set(normalizedSymbols)

        const flushPendingUpdates = () => {
            if (flushTimerRef.current !== null) {
                window.clearTimeout(flushTimerRef.current)
                flushTimerRef.current = null
            }

            const pending = pendingUpdatesRef.current
            const entries = Object.entries(pending)
            if (entries.length === 0) return
            pendingUpdatesRef.current = {}

            setPrices((prev) => {
                let changed = false
                const next = { ...prev }

                for (const [symbol, payload] of entries) {
                    // Ignore stale updates after symbols list changed.
                    if (!activeSymbols.has(symbol)) continue

                    const current = prev[symbol]
                    if (
                        current &&
                        current.price === payload.price &&
                        current.change === payload.change &&
                        current.priceChange === payload.priceChange
                    ) {
                        continue
                    }
                    next[symbol] = payload
                    changed = true
                }

                return changed ? next : prev
            })
        }

        const scheduleFlush = () => {
            if (flushTimerRef.current !== null) return
            flushTimerRef.current = window.setTimeout(flushPendingUpdates, 250)
        }

        const connect = () => {
            if (disposed) return
            if (reconnectTimerRef.current !== null) {
                window.clearTimeout(reconnectTimerRef.current)
                reconnectTimerRef.current = null
            }

            const streams = normalizedSymbols.map((symbol) => `${symbol.toLowerCase()}@ticker`)
            const url = streams.length === 1
                ? `wss://stream.binance.com:9443/ws/${streams[0]}`
                : `wss://stream.binance.com:9443/stream?streams=${streams.join("/")}`

            socket = new WebSocket(url)
            ws.current = socket

            socket.onopen = () => {
                reconnectDelay = 1000
            }

            socket.onmessage = (event) => {
                try {
                    const parsed = JSON.parse(event.data) as { data?: TickerData } | TickerData
                    const ticker = ("data" in parsed ? parsed.data : parsed) as TickerData | undefined
                    if (!ticker?.s) return

                    const symbol = ticker.s.toUpperCase()
                    const nextValue = {
                        price: parseFloat(ticker.c),
                        change: parseFloat(ticker.P),
                        priceChange: parseFloat(ticker.p),
                    }

                    pendingUpdatesRef.current[symbol] = nextValue
                    scheduleFlush()
                } catch {
                    // Ignore malformed packets from network edges/proxies.
                }
            }

            // Let onclose own retry policy to avoid duplicate reconnects.
            socket.onerror = () => undefined

            socket.onclose = (event) => {
                if (ws.current === socket) {
                    ws.current = null
                }
                if (disposed) return
                if (event.code === 1000 || event.code === 1001) return

                reconnectTimerRef.current = window.setTimeout(() => {
                    connect()
                }, reconnectDelay)
                reconnectDelay = Math.min(reconnectDelay * 2, 10000)
            }
        }

        connect()

        return () => {
            disposed = true
            if (reconnectTimerRef.current !== null) {
                window.clearTimeout(reconnectTimerRef.current)
                reconnectTimerRef.current = null
            }
            if (flushTimerRef.current !== null) {
                window.clearTimeout(flushTimerRef.current)
                flushTimerRef.current = null
            }
            pendingUpdatesRef.current = {}

            if (socket) {
                socket.onopen = null
                socket.onmessage = null
                socket.onerror = null
                socket.onclose = null
                if (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN) {
                    socket.close(1000, "Ticker hook cleanup")
                }
            }

            if (ws.current === socket) {
                ws.current = null
            }
        }
    }, [normalizedSymbols, symbolsKey, paused])

    return prices
}
