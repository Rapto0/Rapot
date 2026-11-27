"use client"

import { createContext, useContext, useMemo, useSyncExternalStore } from "react"
import { BinanceTickerFeed, emptyTickerSnapshot } from "@/lib/binance-ticker-feed"

interface UseBinanceTickerOptions {
    paused?: boolean
    flushIntervalMs?: number
    firstFlushMs?: number
}

function view(feed: BinanceTickerFeed | null, key: string, paused: boolean, interval: number, firstInterval: number) {
    const symbols = new Set(key ? key.split("|") : [])
    const active = !!feed && !paused && symbols.size > 0
    const server = emptyTickerSnapshot(paused ? "paused" : active ? "connecting" : "offline")
    let snapshot = active ? feed.read(symbols) : server
    let flushTimer: number | undefined
    let flushAt = 0
    let listener: (() => void) | undefined

    function clear() {
        if (flushTimer !== undefined) window.clearTimeout(flushTimer)
        flushTimer = undefined
    }
    function publish() {
        clear()
        if (!listener || !feed) return
        snapshot = feed.read(symbols)
        listener()
    }
    function onUpdate(symbol?: string) {
        if (!listener || !feed) return
        if (symbol === undefined) {
            const status = feed.read(symbols).status
            if (snapshot.status === status) return
            clear()
            snapshot = { ...snapshot, status, liveBySymbol: {} }
            listener()
            return
        }
        const delay = snapshot.liveBySymbol[symbol] ? interval : firstInterval
        const at = Date.now() + delay
        if (flushTimer !== undefined && flushAt <= at) return
        clear()
        flushAt = at
        const timer = window.setTimeout(() => {
            if (flushTimer === timer) publish()
        }, delay)
        flushTimer = timer
    }
    return {
        getSnapshot: () => snapshot,
        getServerSnapshot: () => server,
        subscribe(notify: () => void) {
            if (!active) return () => {}
            listener = notify
            const unwatch = feed.watch({ symbols, notify: onUpdate })
            snapshot = feed.read(symbols)
            return () => {
                listener = undefined
                clear()
                unwatch()
            }
        },
        reconnect() { if (active && listener) feed.reconnect() },
        flush() { if (flushTimer !== undefined) publish() },
    }
}

export const BinanceTickerContext = createContext<BinanceTickerFeed | null>(null)

export function useBinanceTickerFeed(symbols: string[], options?: UseBinanceTickerOptions) {
    const feed = useContext(BinanceTickerContext)
    const paused = options?.paused === true
    const requestedInterval = options?.flushIntervalMs ?? 250
    const interval = Number.isFinite(requestedInterval) ? Math.max(100, requestedInterval) : 250
    const requestedFirst = options?.firstFlushMs ?? interval
    const firstInterval = Number.isFinite(requestedFirst) ? Math.max(0, requestedFirst) : interval
    const key = useMemo(() => [...new Set(symbols
        .map(symbol => symbol.trim().toUpperCase())
        .filter(symbol => /^[A-Z0-9]{1,32}$/.test(symbol)))].sort().join("|"), [symbols])
    const observer = useMemo(() => view(feed, key, paused, interval, firstInterval),
        [feed, key, paused, interval, firstInterval])
    const snapshot = useSyncExternalStore(observer.subscribe, observer.getSnapshot, observer.getServerSnapshot)
    return { ...snapshot, reconnect: observer.reconnect, flush: observer.flush }
}

/** Compatibility API for consumers that only need quote values. */
export function useBinanceTicker(symbols: string[], options?: UseBinanceTickerOptions) {
    return useBinanceTickerFeed(symbols, options).prices
}
