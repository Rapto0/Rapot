"use client"

import { useEffect, useRef, useState } from "react"

interface TickerData {
    s: string // Symbol
    c: string // Last price (current price)
    p: string // Price change
    P: string // Price Change Percent
}

export function useBinanceTicker(symbols: string[]) {
    const [prices, setPrices] = useState<Record<string, { price: number; change: number; priceChange: number }>>({})
    const ws = useRef<WebSocket | null>(null)

    useEffect(() => {
        if (symbols.length === 0) return

        // Construct stream names (e.g., btcusdt@ticker)
        const streams = symbols.map((s) => `${s.toLowerCase()}@ticker`).join("/")
        const url = `wss://stream.binance.com:9443/ws/${streams}`

        ws.current = new WebSocket(url)

        ws.current.onmessage = (event) => {
            const data: TickerData = JSON.parse(event.data)
            setPrices((prev) => ({
                ...prev,
                [data.s]: {
                    price: parseFloat(data.c),       // Last price (correct!)
                    change: parseFloat(data.P),      // Price change percent
                    priceChange: parseFloat(data.p), // Absolute price change
                },
            }))
        }

        return () => {
            ws.current?.close()
        }
    }, [JSON.stringify(symbols)])

    return prices
}
