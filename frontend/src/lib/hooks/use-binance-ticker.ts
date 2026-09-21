"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"

interface TickerPrice {
    price: number
    change: number
    priceChange: number
}

interface UseBinanceTickerOptions {
    paused?: boolean
    flushIntervalMs?: number
}

export type BinanceTickerStatus = "connecting" | "connected" | "reconnecting" | "offline" | "paused"

interface TickerSnapshot {
    prices: Record<string, TickerPrice>
    receivedAtBySymbol: Record<string, number>
}

function numericField(value: unknown): number | null {
    if (typeof value === "string") {
        // Number/parseFloat alone also accept empty strings or numeric prefixes.
        if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(value.trim())) return null
        value = Number(value)
    }
    return typeof value === "number" && Number.isFinite(value) ? value : null
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value)
}

export function useBinanceTickerFeed(symbols: string[], options?: UseBinanceTickerOptions) {
    const paused = options?.paused === true
    const requestedInterval = options?.flushIntervalMs ?? 250
    const flushIntervalMs = Number.isFinite(requestedInterval) ? Math.max(100, requestedInterval) : 250
    const symbolsKey = useMemo(() => Array.from(new Set(symbols
        .map((symbol) => symbol.trim().toUpperCase())
        .filter((symbol) => /^[A-Z0-9]{1,32}$/.test(symbol)))).sort().join("|"), [symbols])
    const normalizedSymbols = useMemo(() => symbolsKey ? symbolsKey.split("|") : [], [symbolsKey])
    const scope = `${symbolsKey}:${paused}`
    const [snapshot, setSnapshot] = useState<TickerSnapshot>({ prices: {}, receivedAtBySymbol: {} })
    const [connection, setConnection] = useState<{ scope: string; status: BinanceTickerStatus }>({
        scope, status: paused ? "paused" : symbolsKey ? "connecting" : "offline",
    })
    const reconnectRef = useRef<(() => void) | null>(null)
    const reconnect = useCallback(() => reconnectRef.current?.(), [])

    useEffect(() => {
        const setStatus = (status: BinanceTickerStatus) => setConnection((previous) =>
            previous.scope === scope && previous.status === status ? previous : { scope, status })
        if (paused || normalizedSymbols.length === 0) {
            setStatus(paused ? "paused" : "offline")
            return
        }

        let disposed = false
        let generation = 0
        let socket: WebSocket | null = null
        let reconnectTimer: number | null = null
        let openingTimer: number | null = null
        let flushTimer: number | null = null
        let reconnectDelay = 1000
        let pending = new Map<string, { price: TickerPrice; receivedAt: number }>()
        const activeSymbols = new Set(normalizedSymbols)
        const online = () => window.navigator.onLine !== false
        const streams = normalizedSymbols.map((symbol) => `${symbol.toLowerCase()}@ticker`)
        const url = streams.length === 1
            ? `wss://stream.binance.com:9443/ws/${streams[0]}`
            : `wss://stream.binance.com:9443/stream?streams=${streams.join("/")}`

        const clearRetry = () => {
            if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
            reconnectTimer = null
        }
        const clearOpeningTimer = () => {
            if (openingTimer !== null) window.clearTimeout(openingTimer)
            openingTimer = null
        }
        const retireSocket = () => {
            generation++
            clearOpeningTimer()
            if (flushTimer !== null) window.clearTimeout(flushTimer)
            flushTimer = null
            pending.clear()
            const previous = socket
            socket = null
            if (!previous) return
            previous.onopen = null
            previous.onmessage = null
            previous.onerror = null
            previous.onclose = null
            if (previous.readyState === WebSocket.CONNECTING || previous.readyState === WebSocket.OPEN) {
                previous.close(1000, "Ticker connection retired")
            }
        }
        const scheduleFlush = () => {
            if (flushTimer !== null) return
            const version = generation
            const timer = window.setTimeout(() => {
                if (disposed || generation !== version || flushTimer !== timer) return
                flushTimer = null
                const updates = pending
                pending = new Map()
                setSnapshot((previous) => {
                    const prices = { ...previous.prices }
                    const receivedAtBySymbol = { ...previous.receivedAtBySymbol }
                    for (const [symbol, update] of updates) {
                        prices[symbol] = update.price
                        receivedAtBySymbol[symbol] = update.receivedAt
                    }
                    return { prices, receivedAtBySymbol }
                })
            }, flushIntervalMs)
            flushTimer = timer
        }
        const scheduleRetry = () => {
            if (disposed || reconnectTimer !== null) return
            if (!online()) { setStatus("offline"); return }
            setStatus("reconnecting")
            const version = generation
            const timer = window.setTimeout(() => {
                if (disposed || generation !== version || reconnectTimer !== timer) return
                reconnectTimer = null
                connect(true)
            }, reconnectDelay)
            reconnectTimer = timer
            reconnectDelay = Math.min(reconnectDelay * 2, 10000)
        }
        const connect = (retrying = false) => {
            if (disposed) return
            if (!online()) { setStatus("offline"); return }
            setStatus(retrying ? "reconnecting" : "connecting")
            const version = ++generation
            let current: WebSocket
            try {
                current = new WebSocket(url)
            } catch {
                scheduleRetry()
                return
            }
            socket = current
            const isCurrent = () => !disposed && generation === version && socket === current
            current.onopen = () => {
                if (!isCurrent()) return
                clearOpeningTimer()
                reconnectDelay = 1000
                setStatus("connected")
            }
            current.onmessage = (event) => {
                if (!isCurrent() || typeof event.data !== "string") return
                try {
                    const parsed: unknown = JSON.parse(event.data)
                    if (!isRecord(parsed)) return
                    const ticker = "data" in parsed ? parsed.data : parsed
                    if (!isRecord(ticker) || typeof ticker.s !== "string") return
                    const symbol = ticker.s.toUpperCase()
                    if (!activeSymbols.has(symbol)) return
                    const price = numericField(ticker.c)
                    const change = numericField(ticker.P)
                    const priceChange = numericField(ticker.p)
                    if (price === null || price <= 0 || change === null || priceChange === null) return
                    // Browser receipt time, not an exchange/source price timestamp.
                    pending.set(symbol, { price: { price, change, priceChange }, receivedAt: Date.now() })
                    scheduleFlush()
                } catch {
                    // Malformed packets do not replace the last valid quote or its receipt time.
                }
            }
            const disconnected = () => {
                if (!isCurrent()) return
                retireSocket()
                scheduleRetry()
            }
            current.onerror = disconnected
            // Normal remote closes also retry. Local closes detach their handlers first.
            current.onclose = disconnected
            const timer = window.setTimeout(() => {
                if (openingTimer !== timer) return
                openingTimer = null
                disconnected()
            }, 20000)
            openingTimer = timer
        }
        const reconnectNow = () => {
            if (disposed) return
            clearRetry()
            retireSocket()
            reconnectDelay = 1000
            connect(true)
        }
        const wentOffline = () => {
            if (disposed) return
            clearRetry()
            retireSocket()
            setStatus("offline")
        }
        const wentOnline = () => {
            if (!disposed && socket === null && reconnectTimer === null) reconnectNow()
        }
        reconnectRef.current = reconnectNow
        window.addEventListener("offline", wentOffline)
        window.addEventListener("online", wentOnline)
        connect()

        return () => {
            disposed = true
            clearRetry()
            retireSocket()
            window.removeEventListener("offline", wentOffline)
            window.removeEventListener("online", wentOnline)
            if (reconnectRef.current === reconnectNow) reconnectRef.current = null
        }
    }, [normalizedSymbols, paused, flushIntervalMs, scope])

    // Removed symbols disappear on the request render, before effect cleanup.
    const visible = useMemo(() => ({
        prices: Object.fromEntries(normalizedSymbols.filter((symbol) => snapshot.prices[symbol])
            .map((symbol) => [symbol, snapshot.prices[symbol]])),
        receivedAtBySymbol: Object.fromEntries(normalizedSymbols
            .filter((symbol) => snapshot.receivedAtBySymbol[symbol] !== undefined)
            .map((symbol) => [symbol, snapshot.receivedAtBySymbol[symbol]])),
    }), [snapshot, normalizedSymbols])
    const status: BinanceTickerStatus = paused ? "paused" : !symbolsKey ? "offline"
        : connection.scope === scope ? connection.status : "connecting"
    return { ...visible, status, reconnect }
}

/** Compatibility API for chart/watchlist consumers that only need quote values. */
export function useBinanceTicker(symbols: string[], options?: UseBinanceTickerOptions) {
    return useBinanceTickerFeed(symbols, options).prices
}
