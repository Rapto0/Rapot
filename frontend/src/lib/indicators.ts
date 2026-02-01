/**
 * Technical Indicator Calculations for TradingView Charts
 *
 * All calculations use OHLCV data and return series for chart display.
 */

export interface Candle {
    time: string
    open: number
    high: number
    low: number
    close: number
    volume: number
}

export interface IndicatorValue {
    time: string
    value: number
}

export interface MACDValue {
    time: string
    macd: number
    signal: number
    histogram: number
}

// ==================== HELPER FUNCTIONS ====================

function sma(data: number[], period: number): number[] {
    const result: number[] = []
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            result.push(NaN)
        } else {
            const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0)
            result.push(sum / period)
        }
    }
    return result
}

function ema(data: number[], period: number): number[] {
    const result: number[] = []
    const multiplier = 2 / (period + 1)

    for (let i = 0; i < data.length; i++) {
        if (i === 0) {
            result.push(data[i])
        } else if (i < period - 1) {
            // Use SMA for initial values
            const sum = data.slice(0, i + 1).reduce((a, b) => a + b, 0)
            result.push(sum / (i + 1))
        } else if (i === period - 1) {
            // First real EMA value
            const sum = data.slice(0, period).reduce((a, b) => a + b, 0)
            result.push(sum / period)
        } else {
            result.push((data[i] - result[i - 1]) * multiplier + result[i - 1])
        }
    }
    return result
}

// ==================== RSI ====================

export function calculateRSI(candles: Candle[], period: number = 14): IndicatorValue[] {
    const closes = candles.map(c => c.close)
    const result: IndicatorValue[] = []

    const gains: number[] = []
    const losses: number[] = []

    for (let i = 1; i < closes.length; i++) {
        const change = closes[i] - closes[i - 1]
        gains.push(change > 0 ? change : 0)
        losses.push(change < 0 ? Math.abs(change) : 0)
    }

    // First RSI uses simple average
    let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period
    let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period

    // Pad with NaN for initial period
    for (let i = 0; i < period; i++) {
        result.push({ time: candles[i].time, value: NaN })
    }

    // Calculate RSI
    for (let i = period; i < candles.length; i++) {
        if (i === period) {
            const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
            const rsi = 100 - (100 / (1 + rs))
            result.push({ time: candles[i].time, value: rsi })
        } else {
            avgGain = (avgGain * (period - 1) + gains[i - 1]) / period
            avgLoss = (avgLoss * (period - 1) + losses[i - 1]) / period
            const rs = avgLoss === 0 ? 100 : avgGain / avgLoss
            const rsi = 100 - (100 / (1 + rs))
            result.push({ time: candles[i].time, value: rsi })
        }
    }

    return result
}

// ==================== MACD ====================

export function calculateMACD(
    candles: Candle[],
    fastPeriod: number = 12,
    slowPeriod: number = 26,
    signalPeriod: number = 9
): MACDValue[] {
    const closes = candles.map(c => c.close)
    const result: MACDValue[] = []

    const fastEMA = ema(closes, fastPeriod)
    const slowEMA = ema(closes, slowPeriod)

    // MACD Line
    const macdLine = fastEMA.map((fast, i) => fast - slowEMA[i])

    // Signal Line (EMA of MACD)
    const signalLine = ema(macdLine.filter(v => !isNaN(v)), signalPeriod)

    // Pad signal line to match length
    const paddedSignal: number[] = []
    let signalIdx = 0
    for (let i = 0; i < macdLine.length; i++) {
        if (isNaN(macdLine[i]) || signalIdx >= signalLine.length) {
            paddedSignal.push(NaN)
        } else {
            paddedSignal.push(signalLine[signalIdx])
            signalIdx++
        }
    }

    for (let i = 0; i < candles.length; i++) {
        result.push({
            time: candles[i].time,
            macd: macdLine[i],
            signal: paddedSignal[i],
            histogram: macdLine[i] - paddedSignal[i]
        })
    }

    return result
}

// ==================== Williams %R ====================

export function calculateWilliamsR(candles: Candle[], period: number = 14): IndicatorValue[] {
    const result: IndicatorValue[] = []

    for (let i = 0; i < candles.length; i++) {
        if (i < period - 1) {
            result.push({ time: candles[i].time, value: NaN })
        } else {
            const slice = candles.slice(i - period + 1, i + 1)
            const highestHigh = Math.max(...slice.map(c => c.high))
            const lowestLow = Math.min(...slice.map(c => c.low))
            const close = candles[i].close

            const wr = highestHigh === lowestLow
                ? -50
                : ((highestHigh - close) / (highestHigh - lowestLow)) * -100

            result.push({ time: candles[i].time, value: wr })
        }
    }

    return result
}

// ==================== CCI ====================

export function calculateCCI(candles: Candle[], period: number = 20): IndicatorValue[] {
    const result: IndicatorValue[] = []

    // Typical Price
    const tp = candles.map(c => (c.high + c.low + c.close) / 3)

    // SMA of TP
    const tpSMA = sma(tp, period)

    for (let i = 0; i < candles.length; i++) {
        if (i < period - 1) {
            result.push({ time: candles[i].time, value: NaN })
        } else {
            const slice = tp.slice(i - period + 1, i + 1)
            const mean = tpSMA[i]

            // Mean Absolute Deviation
            const mad = slice.reduce((sum, val) => sum + Math.abs(val - mean), 0) / period

            const cci = mad === 0 ? 0 : (tp[i] - mean) / (0.015 * mad)
            result.push({ time: candles[i].time, value: cci })
        }
    }

    return result
}

// ==================== COMBO INDICATOR (Overlay) ====================

export interface ComboSignal {
    time: string
    buyScore: number
    sellScore: number
    signal: 'AL' | 'SAT' | null
    details: {
        macd: number
        rsi: number
        wr: number
        cci: number
    }
}

export function calculateCombo(candles: Candle[]): ComboSignal[] {
    if (candles.length < 26) return []

    const rsi = calculateRSI(candles, 14)
    const macd = calculateMACD(candles)
    const wr = calculateWilliamsR(candles, 14)
    const cci = calculateCCI(candles, 20)

    const result: ComboSignal[] = []

    for (let i = 0; i < candles.length; i++) {
        let buyScore = 0
        let sellScore = 0

        const macdVal = macd[i]?.macd || 0
        const rsiVal = rsi[i]?.value || 50
        const wrVal = wr[i]?.value || -50
        const cciVal = cci[i]?.value || 0

        // Buy conditions
        if (!isNaN(macdVal) && macdVal < 0) buyScore++
        if (!isNaN(rsiVal) && rsiVal < 40) buyScore++
        if (!isNaN(wrVal) && wrVal < -80) buyScore++
        if (!isNaN(cciVal) && cciVal < -100) buyScore++

        // Sell conditions
        if (!isNaN(macdVal) && macdVal > 0) sellScore++
        if (!isNaN(rsiVal) && rsiVal > 80) sellScore++
        if (!isNaN(wrVal) && wrVal > -10) sellScore++
        if (!isNaN(cciVal) && cciVal > 200) sellScore++

        let signal: 'AL' | 'SAT' | null = null
        if (buyScore >= 4) signal = 'AL'
        if (sellScore >= 3) signal = 'SAT'

        result.push({
            time: candles[i].time,
            buyScore,
            sellScore,
            signal,
            details: {
                macd: macdVal,
                rsi: rsiVal,
                wr: wrVal,
                cci: cciVal
            }
        })
    }

    return result
}

// ==================== HUNTER INDICATOR (Overlay) ====================

export interface HunterSignal {
    time: string
    dipScore: number
    topScore: number
    signal: 'AL' | 'SAT' | null
    rsiConfirm: boolean
}

export function calculateHunter(candles: Candle[]): HunterSignal[] {
    if (candles.length < 15) return []

    const rsi = calculateRSI(candles, 14)
    const result: HunterSignal[] = []

    const REQ_DIP = 7
    const REQ_TOP = 10

    for (let i = 0; i < candles.length; i++) {
        if (i < 14) {
            result.push({
                time: candles[i].time,
                dipScore: 0,
                topScore: 0,
                signal: null,
                rsiConfirm: false
            })
            continue
        }

        // Count consecutive down/up days
        let dipScore = 0
        let topScore = 0

        // Look back for dips (lower lows)
        for (let j = i; j > Math.max(0, i - 14); j--) {
            if (j > 0 && candles[j].low < candles[j - 1].low) {
                dipScore++
            } else {
                break
            }
        }

        // Look back for tops (higher highs)
        for (let j = i; j > Math.max(0, i - 14); j--) {
            if (j > 0 && candles[j].high > candles[j - 1].high) {
                topScore++
            } else {
                break
            }
        }

        const rsiVal = rsi[i]?.value || 50
        const rsiDipConfirm = rsiVal < 30
        const rsiTopConfirm = rsiVal > 70

        let signal: 'AL' | 'SAT' | null = null
        let rsiConfirm = false

        if (dipScore >= REQ_DIP && rsiDipConfirm) {
            signal = 'AL'
            rsiConfirm = true
        }
        if (topScore >= REQ_TOP && rsiTopConfirm) {
            signal = 'SAT'
            rsiConfirm = true
        }

        result.push({
            time: candles[i].time,
            dipScore,
            topScore,
            signal,
            rsiConfirm
        })
    }

    return result
}

// ==================== INDICATOR METADATA ====================

export interface IndicatorMeta {
    id: string
    name: string
    shortName: string
    description: string
    category: 'momentum' | 'trend' | 'volatility' | 'custom'
    isOverlay: boolean
    defaultParams: Record<string, number>
}

export const AVAILABLE_INDICATORS: IndicatorMeta[] = [
    {
        id: 'rsi',
        name: 'Relative Strength Index',
        shortName: 'RSI',
        description: 'Aşırı alım/satım göstergesi (0-100)',
        category: 'momentum',
        isOverlay: false,
        defaultParams: { period: 14 }
    },
    {
        id: 'macd',
        name: 'MACD',
        shortName: 'MACD',
        description: 'Moving Average Convergence Divergence',
        category: 'trend',
        isOverlay: false,
        defaultParams: { fast: 12, slow: 26, signal: 9 }
    },
    {
        id: 'wr',
        name: 'Williams %R',
        shortName: 'W%R',
        description: 'Momentum göstergesi (-100 to 0)',
        category: 'momentum',
        isOverlay: false,
        defaultParams: { period: 14 }
    },
    {
        id: 'cci',
        name: 'Commodity Channel Index',
        shortName: 'CCI',
        description: 'Trend sapma göstergesi',
        category: 'momentum',
        isOverlay: false,
        defaultParams: { period: 20 }
    },
    {
        id: 'combo',
        name: 'COMBO Sinyali',
        shortName: 'COMBO',
        description: 'Rapot özel AL/SAT sinyali (4 indikatör birleşimi)',
        category: 'custom',
        isOverlay: true,
        defaultParams: {}
    },
    {
        id: 'hunter',
        name: 'HUNTER Sinyali',
        shortName: 'HUNTER',
        description: 'Rapot özel dip/tepe tespit sinyali',
        category: 'custom',
        isOverlay: true,
        defaultParams: {}
    }
]
