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
        // AL needs 3+ OS conditions, SAT needs 3+ OB conditions
        if (buyScore >= 3) signal = 'AL'
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
// Uses 15 oscillators with N-of-M logic based on Pine Script

export interface HunterSignal {
    time: string
    dipScore: number  // Number of oversold (OS) conditions met
    topScore: number  // Number of overbought (OB) conditions met
    signal: 'AL' | 'SAT' | null
    details: {
        rsi: number
        rsiFast: number
        wr: number
        cci: number
        cmo: number
        ultimate: number
        bbPercent: number
        roc: number
        bop: number
        demarker: number
        psy: number
        zscore: number
        keltnerPercent: number
        macd: number
        rsi2: number
    }
}

// Helper: Calculate CMO (Chande Momentum Oscillator)
function calculateCMO(candles: Candle[], period: number = 14): number[] {
    const result: number[] = []
    const closes = candles.map(c => c.close)

    for (let i = 0; i < closes.length; i++) {
        if (i < period) {
            result.push(NaN)
            continue
        }

        let sumUp = 0
        let sumDown = 0
        for (let j = i - period + 1; j <= i; j++) {
            const change = closes[j] - closes[j - 1]
            if (change > 0) sumUp += change
            else sumDown += Math.abs(change)
        }

        const cmo = (sumUp + sumDown) === 0 ? 0 : ((sumUp - sumDown) / (sumUp + sumDown)) * 100
        result.push(cmo)
    }
    return result
}

// Helper: Calculate Ultimate Oscillator
function calculateUltimate(candles: Candle[], p1: number = 7, p2: number = 14, p3: number = 28): number[] {
    const result: number[] = []

    for (let i = 0; i < candles.length; i++) {
        if (i < p3) {
            result.push(NaN)
            continue
        }

        const bp: number[] = []
        const tr: number[] = []

        for (let j = i - p3 + 1; j <= i; j++) {
            const prevClose = candles[j - 1].close
            const low = Math.min(candles[j].low, prevClose)
            const high = Math.max(candles[j].high, prevClose)
            bp.push(candles[j].close - low)
            tr.push(high - low)
        }

        const avg1 = bp.slice(-p1).reduce((a, b) => a + b, 0) / tr.slice(-p1).reduce((a, b) => a + b, 0) || 0
        const avg2 = bp.slice(-p2).reduce((a, b) => a + b, 0) / tr.slice(-p2).reduce((a, b) => a + b, 0) || 0
        const avg3 = bp.reduce((a, b) => a + b, 0) / tr.reduce((a, b) => a + b, 0) || 0

        const uo = ((avg1 * 4) + (avg2 * 2) + avg3) / 7 * 100
        result.push(uo)
    }
    return result
}

// Helper: Calculate Bollinger %B
function calculateBBPercent(candles: Candle[], period: number = 20, mult: number = 2): number[] {
    const result: number[] = []
    const closes = candles.map(c => c.close)
    const smaValues = sma(closes, period)

    for (let i = 0; i < closes.length; i++) {
        if (i < period - 1) {
            result.push(NaN)
            continue
        }

        const slice = closes.slice(i - period + 1, i + 1)
        const mean = smaValues[i]
        const variance = slice.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / period
        const stdDev = Math.sqrt(variance)

        const upper = mean + mult * stdDev
        const lower = mean - mult * stdDev

        const percentB = (upper - lower) === 0 ? 0.5 : (closes[i] - lower) / (upper - lower)
        result.push(percentB * 100)
    }
    return result
}

// Helper: Calculate ROC%
function calculateROC(candles: Candle[], period: number = 14): number[] {
    const result: number[] = []
    const closes = candles.map(c => c.close)

    for (let i = 0; i < closes.length; i++) {
        if (i < period) {
            result.push(NaN)
            continue
        }
        const roc = ((closes[i] - closes[i - period]) / closes[i - period]) * 100
        result.push(roc)
    }
    return result
}

// Helper: Calculate BOP (Balance of Power)
function calculateBOP(candles: Candle[]): number[] {
    return candles.map(c => {
        const range = c.high - c.low
        return range === 0 ? 0 : (c.close - c.open) / range
    })
}

// Helper: Calculate DeMarker
function calculateDeMarker(candles: Candle[], period: number = 14): number[] {
    const result: number[] = []

    for (let i = 0; i < candles.length; i++) {
        if (i < period) {
            result.push(NaN)
            continue
        }

        let sumDeMax = 0
        let sumDeMin = 0

        for (let j = i - period + 1; j <= i; j++) {
            const deMax = candles[j].high > candles[j - 1].high ? candles[j].high - candles[j - 1].high : 0
            const deMin = candles[j].low < candles[j - 1].low ? candles[j - 1].low - candles[j].low : 0
            sumDeMax += deMax
            sumDeMin += deMin
        }

        const demarker = (sumDeMax + sumDeMin) === 0 ? 0.5 : sumDeMax / (sumDeMax + sumDeMin)
        result.push(demarker * 100)
    }
    return result
}

// Helper: Calculate PSY (Psychological Line)
function calculatePSY(candles: Candle[], period: number = 12): number[] {
    const result: number[] = []
    const closes = candles.map(c => c.close)

    for (let i = 0; i < closes.length; i++) {
        if (i < period) {
            result.push(NaN)
            continue
        }

        let upDays = 0
        for (let j = i - period + 1; j <= i; j++) {
            if (closes[j] > closes[j - 1]) upDays++
        }

        result.push((upDays / period) * 100)
    }
    return result
}

// Helper: Calculate Z-Score
function calculateZScore(candles: Candle[], period: number = 20): number[] {
    const result: number[] = []
    const closes = candles.map(c => c.close)
    const smaValues = sma(closes, period)

    for (let i = 0; i < closes.length; i++) {
        if (i < period - 1) {
            result.push(NaN)
            continue
        }

        const slice = closes.slice(i - period + 1, i + 1)
        const mean = smaValues[i]
        const variance = slice.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / period
        const stdDev = Math.sqrt(variance)

        const zscore = stdDev === 0 ? 0 : (closes[i] - mean) / stdDev
        result.push(zscore)
    }
    return result
}

// Helper: Calculate Keltner Channel %B
function calculateKeltnerPercent(candles: Candle[], period: number = 20, mult: number = 2): number[] {
    const result: number[] = []
    const closes = candles.map(c => c.close)
    const emaValues = ema(closes, period)

    // ATR calculation
    const atrValues: number[] = []
    for (let i = 0; i < candles.length; i++) {
        if (i === 0) {
            atrValues.push(candles[i].high - candles[i].low)
            continue
        }
        const tr = Math.max(
            candles[i].high - candles[i].low,
            Math.abs(candles[i].high - candles[i - 1].close),
            Math.abs(candles[i].low - candles[i - 1].close)
        )
        atrValues.push(tr)
    }
    const atrEma = ema(atrValues, period)

    for (let i = 0; i < closes.length; i++) {
        if (i < period - 1) {
            result.push(NaN)
            continue
        }

        const upper = emaValues[i] + mult * atrEma[i]
        const lower = emaValues[i] - mult * atrEma[i]

        const percentK = (upper - lower) === 0 ? 0.5 : (closes[i] - lower) / (upper - lower)
        result.push(percentK * 100)
    }
    return result
}

export function calculateHunter(candles: Candle[]): HunterSignal[] {
    if (candles.length < 30) return []

    // Calculate all 15 oscillators
    const rsi14 = calculateRSI(candles, 14)
    const rsi7 = calculateRSI(candles, 7)  // RSI Fast
    const rsi2 = calculateRSI(candles, 2)  // RSI(2)
    const wr = calculateWilliamsR(candles, 14)
    const cci = calculateCCI(candles, 20)
    const cmo = calculateCMO(candles, 14)
    const ultimate = calculateUltimate(candles, 7, 14, 28)
    const bbPercent = calculateBBPercent(candles, 20, 2)
    const roc = calculateROC(candles, 14)
    const bop = calculateBOP(candles)
    const demarker = calculateDeMarker(candles, 14)
    const psy = calculatePSY(candles, 12)
    const zscore = calculateZScore(candles, 20)
    const keltnerPercent = calculateKeltnerPercent(candles, 20, 2)
    const macd = calculateMACD(candles)

    const result: HunterSignal[] = []

    // Required counts for signals (adjusted for more responsive signals)
    const REQ_DIP = 5   // Need at least 5 oversold conditions for DIP (buy)
    const REQ_TOP = 7   // Need at least 7 overbought conditions for TEPE (sell)

    for (let i = 0; i < candles.length; i++) {
        // Get all indicator values at this index
        const rsiVal = rsi14[i]?.value ?? 50
        const rsiFastVal = rsi7[i]?.value ?? 50
        const rsi2Val = rsi2[i]?.value ?? 50
        const wrVal = wr[i]?.value ?? -50
        const cciVal = cci[i]?.value ?? 0
        const cmoVal = cmo[i] ?? 0
        const ultimateVal = ultimate[i] ?? 50
        const bbPercentVal = bbPercent[i] ?? 50
        const rocVal = roc[i] ?? 0
        const bopVal = bop[i] ?? 0
        const demarkerVal = demarker[i] ?? 50
        const psyVal = psy[i] ?? 50
        const zscoreVal = zscore[i] ?? 0
        const keltnerPercentVal = keltnerPercent[i] ?? 50
        const macdVal = macd[i]?.macd ?? 0

        // Count oversold (OS) conditions - DIP
        let dipScore = 0
        if (!isNaN(rsiVal) && rsiVal < 30) dipScore++
        if (!isNaN(rsiFastVal) && rsiFastVal < 20) dipScore++
        if (!isNaN(wrVal) && wrVal < -80) dipScore++
        if (!isNaN(cciVal) && cciVal < -100) dipScore++
        if (!isNaN(cmoVal) && cmoVal < -50) dipScore++
        if (!isNaN(ultimateVal) && ultimateVal < 30) dipScore++
        if (!isNaN(bbPercentVal) && bbPercentVal < 0) dipScore++
        if (!isNaN(rocVal) && rocVal < -5) dipScore++
        if (!isNaN(bopVal) && bopVal < -0.5) dipScore++
        if (!isNaN(demarkerVal) && demarkerVal < 30) dipScore++
        if (!isNaN(psyVal) && psyVal < 25) dipScore++
        if (!isNaN(zscoreVal) && zscoreVal < -2) dipScore++
        if (!isNaN(keltnerPercentVal) && keltnerPercentVal < 0) dipScore++
        if (!isNaN(macdVal) && macdVal < 0) dipScore++
        if (!isNaN(rsi2Val) && rsi2Val < 10) dipScore++

        // Count overbought (OB) conditions - TEPE
        let topScore = 0
        if (!isNaN(rsiVal) && rsiVal > 70) topScore++
        if (!isNaN(rsiFastVal) && rsiFastVal > 80) topScore++
        if (!isNaN(wrVal) && wrVal > -20) topScore++
        if (!isNaN(cciVal) && cciVal > 100) topScore++
        if (!isNaN(cmoVal) && cmoVal > 50) topScore++
        if (!isNaN(ultimateVal) && ultimateVal > 70) topScore++
        if (!isNaN(bbPercentVal) && bbPercentVal > 100) topScore++
        if (!isNaN(rocVal) && rocVal > 5) topScore++
        if (!isNaN(bopVal) && bopVal > 0.5) topScore++
        if (!isNaN(demarkerVal) && demarkerVal > 70) topScore++
        if (!isNaN(psyVal) && psyVal > 75) topScore++
        if (!isNaN(zscoreVal) && zscoreVal > 2) topScore++
        if (!isNaN(keltnerPercentVal) && keltnerPercentVal > 100) topScore++
        if (!isNaN(macdVal) && macdVal > 0) topScore++
        if (!isNaN(rsi2Val) && rsi2Val > 90) topScore++

        let signal: 'AL' | 'SAT' | null = null

        // DIP signal when at least 7 oscillators are oversold
        if (dipScore >= REQ_DIP) signal = 'AL'
        // TEPE signal when at least 10 oscillators are overbought
        if (topScore >= REQ_TOP) signal = 'SAT'

        result.push({
            time: candles[i].time,
            dipScore,
            topScore,
            signal,
            details: {
                rsi: rsiVal,
                rsiFast: rsiFastVal,
                wr: wrVal,
                cci: cciVal,
                cmo: cmoVal,
                ultimate: ultimateVal,
                bbPercent: bbPercentVal,
                roc: rocVal,
                bop: bopVal,
                demarker: demarkerVal,
                psy: psyVal,
                zscore: zscoreVal,
                keltnerPercent: keltnerPercentVal,
                macd: macdVal,
                rsi2: rsi2Val
            }
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
