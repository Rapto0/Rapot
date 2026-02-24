"use server"

import { fetchGlobalIndices } from "@/lib/api/client"

export interface MarketData {
    symbol: string
    regularMarketPrice: number
    regularMarketChangePercent: number
    shortName?: string
}

interface QuoteResult {
    symbol: string
    regularMarketPrice?: number
    regularMarketChangePercent?: number
    shortName?: string
}

export async function getMarketData(symbols: string[]): Promise<MarketData[]> {
    try {
        const quotes = (await fetchGlobalIndices(symbols)) as QuoteResult[]
        return quotes.map((quote: QuoteResult) => ({
            symbol: quote.symbol,
            regularMarketPrice: quote.regularMarketPrice || 0,
            regularMarketChangePercent: quote.regularMarketChangePercent || 0,
            shortName: quote.shortName,
        }))
    } catch (error) {
        console.error("Yahoo Finance API Error:", error)
        return []
    }
}
