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
    if (candles.length === 0) return []
    if (candles.length <= period) {
        return candles.map((c) => ({ time: c.time, value: NaN }))
    }

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

    const resolveRsiValue = (gain: number, loss: number): number => {
        if (loss === 0 && gain === 0) return 50
        if (loss === 0) return 100
        if (gain === 0) return 0
        const rs = gain / loss
        return 100 - (100 / (1 + rs))
    }

    // Pad with NaN for initial period
    for (let i = 0; i < period; i++) {
        result.push({ time: candles[i].time, value: NaN })
    }

    // Calculate RSI
    for (let i = period; i < candles.length; i++) {
        if (i === period) {
            const rsi = resolveRsiValue(avgGain, avgLoss)
            result.push({ time: candles[i].time, value: rsi })
        } else {
            avgGain = (avgGain * (period - 1) + gains[i - 1]) / period
            avgLoss = (avgLoss * (period - 1) + losses[i - 1]) / period
            const rsi = resolveRsiValue(avgGain, avgLoss)
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

export interface ComboParams {
    rsiBuyThreshold: number
    rsiSellThreshold: number
    wrBuyThreshold: number
    wrSellThreshold: number
    cciBuyThreshold: number
    cciSellThreshold: number
    minBuyScore: number
    minSellScore: number
}

const DEFAULT_COMBO_PARAMS: ComboParams = {
    rsiBuyThreshold: 40,
    rsiSellThreshold: 80,
    wrBuyThreshold: -80,
    wrSellThreshold: -10,
    cciBuyThreshold: -100,
    cciSellThreshold: 200,
    minBuyScore: 2,
    minSellScore: 2,
}

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

export function calculateCombo(
    candles: Candle[],
    params: Partial<ComboParams> = {}
): ComboSignal[] {
    if (candles.length < 26) return []

    const cfg = { ...DEFAULT_COMBO_PARAMS, ...params }

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
        if (!isNaN(rsiVal) && rsiVal < cfg.rsiBuyThreshold) buyScore++
        if (!isNaN(wrVal) && wrVal < cfg.wrBuyThreshold) buyScore++
        if (!isNaN(cciVal) && cciVal < cfg.cciBuyThreshold) buyScore++

        // Sell conditions
        if (!isNaN(macdVal) && macdVal > 0) sellScore++
        if (!isNaN(rsiVal) && rsiVal > cfg.rsiSellThreshold) sellScore++
        if (!isNaN(wrVal) && wrVal > cfg.wrSellThreshold) sellScore++
        if (!isNaN(cciVal) && cciVal > cfg.cciSellThreshold) sellScore++

        let signal: 'AL' | 'SAT' | null = null
        if (buyScore >= cfg.minBuyScore) signal = 'AL'
        if (sellScore >= cfg.minSellScore) signal = 'SAT'

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

export interface HunterParams {
    requiredDipScore: number
    requiredTopScore: number
    rsiDipThreshold: number
    rsiTopThreshold: number
    rsiFastDipThreshold: number
    rsiFastTopThreshold: number
    wrDipThreshold: number
    wrTopThreshold: number
    cciDipThreshold: number
    cciTopThreshold: number
    cmoDipThreshold: number
    cmoTopThreshold: number
    ultimateDipThreshold: number
    ultimateTopThreshold: number
    bbPercentDipThreshold: number
    bbPercentTopThreshold: number
    rocDipThreshold: number
    rocTopThreshold: number
    bopDipThreshold: number
    bopTopThreshold: number
    demarkerDipThreshold: number
    demarkerTopThreshold: number
    psyDipThreshold: number
    psyTopThreshold: number
    zscoreDipThreshold: number
    zscoreTopThreshold: number
    keltnerPercentDipThreshold: number
    keltnerPercentTopThreshold: number
    macdDipThreshold: number
    macdTopThreshold: number
    rsi2DipThreshold: number
    rsi2TopThreshold: number
}

const DEFAULT_HUNTER_PARAMS: HunterParams = {
    requiredDipScore: 3,
    requiredTopScore: 4,
    rsiDipThreshold: 30,
    rsiTopThreshold: 70,
    rsiFastDipThreshold: 20,
    rsiFastTopThreshold: 80,
    wrDipThreshold: -80,
    wrTopThreshold: -20,
    cciDipThreshold: -100,
    cciTopThreshold: 100,
    cmoDipThreshold: -50,
    cmoTopThreshold: 50,
    ultimateDipThreshold: 30,
    ultimateTopThreshold: 70,
    bbPercentDipThreshold: 0,
    bbPercentTopThreshold: 100,
    rocDipThreshold: -5,
    rocTopThreshold: 5,
    bopDipThreshold: -0.5,
    bopTopThreshold: 0.5,
    demarkerDipThreshold: 30,
    demarkerTopThreshold: 70,
    psyDipThreshold: 25,
    psyTopThreshold: 75,
    zscoreDipThreshold: -2,
    zscoreTopThreshold: 2,
    keltnerPercentDipThreshold: 0,
    keltnerPercentTopThreshold: 100,
    macdDipThreshold: 0,
    macdTopThreshold: 0,
    rsi2DipThreshold: 10,
    rsi2TopThreshold: 90,
}

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

export function calculateHunter(
    candles: Candle[],
    params: Partial<HunterParams> = {}
): HunterSignal[] {
    if (candles.length < 30) return []

    const cfg = { ...DEFAULT_HUNTER_PARAMS, ...params }

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
        if (!isNaN(rsiVal) && rsiVal < cfg.rsiDipThreshold) dipScore++
        if (!isNaN(rsiFastVal) && rsiFastVal < cfg.rsiFastDipThreshold) dipScore++
        if (!isNaN(wrVal) && wrVal < cfg.wrDipThreshold) dipScore++
        if (!isNaN(cciVal) && cciVal < cfg.cciDipThreshold) dipScore++
        if (!isNaN(cmoVal) && cmoVal < cfg.cmoDipThreshold) dipScore++
        if (!isNaN(ultimateVal) && ultimateVal < cfg.ultimateDipThreshold) dipScore++
        if (!isNaN(bbPercentVal) && bbPercentVal < cfg.bbPercentDipThreshold) dipScore++
        if (!isNaN(rocVal) && rocVal < cfg.rocDipThreshold) dipScore++
        if (!isNaN(bopVal) && bopVal < cfg.bopDipThreshold) dipScore++
        if (!isNaN(demarkerVal) && demarkerVal < cfg.demarkerDipThreshold) dipScore++
        if (!isNaN(psyVal) && psyVal < cfg.psyDipThreshold) dipScore++
        if (!isNaN(zscoreVal) && zscoreVal < cfg.zscoreDipThreshold) dipScore++
        if (!isNaN(keltnerPercentVal) && keltnerPercentVal < cfg.keltnerPercentDipThreshold) dipScore++
        if (!isNaN(macdVal) && macdVal < cfg.macdDipThreshold) dipScore++
        if (!isNaN(rsi2Val) && rsi2Val < cfg.rsi2DipThreshold) dipScore++

        // Count overbought (OB) conditions - TEPE
        let topScore = 0
        if (!isNaN(rsiVal) && rsiVal > cfg.rsiTopThreshold) topScore++
        if (!isNaN(rsiFastVal) && rsiFastVal > cfg.rsiFastTopThreshold) topScore++
        if (!isNaN(wrVal) && wrVal > cfg.wrTopThreshold) topScore++
        if (!isNaN(cciVal) && cciVal > cfg.cciTopThreshold) topScore++
        if (!isNaN(cmoVal) && cmoVal > cfg.cmoTopThreshold) topScore++
        if (!isNaN(ultimateVal) && ultimateVal > cfg.ultimateTopThreshold) topScore++
        if (!isNaN(bbPercentVal) && bbPercentVal > cfg.bbPercentTopThreshold) topScore++
        if (!isNaN(rocVal) && rocVal > cfg.rocTopThreshold) topScore++
        if (!isNaN(bopVal) && bopVal > cfg.bopTopThreshold) topScore++
        if (!isNaN(demarkerVal) && demarkerVal > cfg.demarkerTopThreshold) topScore++
        if (!isNaN(psyVal) && psyVal > cfg.psyTopThreshold) topScore++
        if (!isNaN(zscoreVal) && zscoreVal > cfg.zscoreTopThreshold) topScore++
        if (!isNaN(keltnerPercentVal) && keltnerPercentVal > cfg.keltnerPercentTopThreshold) topScore++
        if (!isNaN(macdVal) && macdVal > cfg.macdTopThreshold) topScore++
        if (!isNaN(rsi2Val) && rsi2Val > cfg.rsi2TopThreshold) topScore++

        let signal: 'AL' | 'SAT' | null = null

        if (dipScore >= cfg.requiredDipScore) signal = 'AL'
        if (topScore >= cfg.requiredTopScore) signal = 'SAT'

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

export interface IndicatorParamSchema {
    key: string
    label: string
    min: number
    max: number
    step?: number
}

export interface IndicatorMeta {
    id: string
    name: string
    shortName: string
    description: string
    category: 'momentum' | 'trend' | 'volatility' | 'custom'
    isOverlay: boolean
    defaultParams: Record<string, number>
    paramSchema?: IndicatorParamSchema[]
}

export const AVAILABLE_INDICATORS: IndicatorMeta[] = [
    {
        id: 'rsi',
        name: 'Relative Strength Index',
        shortName: 'RSI',
        description: 'Aşırı alım/satım göstergesi (0-100)',
        category: 'momentum',
        isOverlay: false,
        defaultParams: { period: 14 },
        paramSchema: [
            { key: 'period', label: 'Periyot', min: 2, max: 100, step: 1 },
        ],
    },
    {
        id: 'macd',
        name: 'MACD',
        shortName: 'MACD',
        description: 'Moving Average Convergence Divergence',
        category: 'trend',
        isOverlay: false,
        defaultParams: { fast: 12, slow: 26, signal: 9 },
        paramSchema: [
            { key: 'fast', label: 'Hızlı EMA', min: 2, max: 50, step: 1 },
            { key: 'slow', label: 'Yavaş EMA', min: 5, max: 100, step: 1 },
            { key: 'signal', label: 'Sinyal', min: 2, max: 30, step: 1 },
        ],
    },
    {
        id: 'wr',
        name: 'Williams %R',
        shortName: 'W%R',
        description: 'Momentum göstergesi (-100 to 0)',
        category: 'momentum',
        isOverlay: false,
        defaultParams: { period: 14 },
        paramSchema: [
            { key: 'period', label: 'Periyot', min: 2, max: 100, step: 1 },
        ],
    },
    {
        id: 'cci',
        name: 'Commodity Channel Index',
        shortName: 'CCI',
        description: 'Trend sapma göstergesi',
        category: 'momentum',
        isOverlay: false,
        defaultParams: { period: 20 },
        paramSchema: [
            { key: 'period', label: 'Periyot', min: 2, max: 100, step: 1 },
        ],
    },
    {
        id: 'combo',
        name: 'COMBO Sinyali',
        shortName: 'COMBO',
        description: 'Rapot özel AL/SAT sinyali (4 indikatör birleşimi)',
        category: 'custom',
        isOverlay: true,
        defaultParams: { ...DEFAULT_COMBO_PARAMS },
        paramSchema: [
            { key: 'rsiBuyThreshold', label: 'RSI AL Eşik', min: 1, max: 60, step: 1 },
            { key: 'rsiSellThreshold', label: 'RSI SAT Eşik', min: 40, max: 99, step: 1 },
            { key: 'wrBuyThreshold', label: 'W%R AL Eşik', min: -100, max: 0, step: 1 },
            { key: 'wrSellThreshold', label: 'W%R SAT Eşik', min: -100, max: 0, step: 1 },
            { key: 'cciBuyThreshold', label: 'CCI AL Eşik', min: -300, max: 0, step: 1 },
            { key: 'cciSellThreshold', label: 'CCI SAT Eşik', min: 0, max: 300, step: 1 },
            { key: 'minBuyScore', label: 'AL Skor Min', min: 1, max: 4, step: 1 },
            { key: 'minSellScore', label: 'SAT Skor Min', min: 1, max: 4, step: 1 },
        ],
    },
    {
        id: 'hunter',
        name: 'HUNTER Sinyali',
        shortName: 'HUNTER',
        description: 'Rapot özel dip/tepe tespit sinyali',
        category: 'custom',
        isOverlay: true,
        defaultParams: { ...DEFAULT_HUNTER_PARAMS },
        paramSchema: [
            { key: 'requiredDipScore', label: 'DIP Min Skor', min: 1, max: 15, step: 1 },
            { key: 'requiredTopScore', label: 'TEPE Min Skor', min: 1, max: 15, step: 1 },
            { key: 'rsiDipThreshold', label: 'RSI DIP Esik', min: 1, max: 50, step: 1 },
            { key: 'rsiTopThreshold', label: 'RSI TEPE Esik', min: 50, max: 99, step: 1 },
            { key: 'rsiFastDipThreshold', label: 'RSI Fast DIP', min: 1, max: 50, step: 1 },
            { key: 'rsiFastTopThreshold', label: 'RSI Fast TEPE', min: 50, max: 99, step: 1 },
            { key: 'wrDipThreshold', label: 'W%R DIP Esik', min: -100, max: 0, step: 1 },
            { key: 'wrTopThreshold', label: 'W%R TEPE Esik', min: -100, max: 0, step: 1 },
            { key: 'cciDipThreshold', label: 'CCI DIP Esik', min: -300, max: 0, step: 1 },
            { key: 'cciTopThreshold', label: 'CCI TEPE Esik', min: 0, max: 300, step: 1 },
            { key: 'cmoDipThreshold', label: 'CMO DIP Esik', min: -100, max: 0, step: 1 },
            { key: 'cmoTopThreshold', label: 'CMO TEPE Esik', min: 0, max: 100, step: 1 },
            { key: 'ultimateDipThreshold', label: 'Ultimate DIP Esik', min: 1, max: 50, step: 1 },
            { key: 'ultimateTopThreshold', label: 'Ultimate TEPE Esik', min: 50, max: 99, step: 1 },
            { key: 'bbPercentDipThreshold', label: '%B DIP Esik', min: -50, max: 100, step: 1 },
            { key: 'bbPercentTopThreshold', label: '%B TEPE Esik', min: 0, max: 150, step: 1 },
            { key: 'rocDipThreshold', label: 'ROC% DIP Esik', min: -50, max: 0, step: 0.5 },
            { key: 'rocTopThreshold', label: 'ROC% TEPE Esik', min: 0, max: 50, step: 0.5 },
            { key: 'bopDipThreshold', label: 'BOP DIP Esik', min: -1, max: 0, step: 0.05 },
            { key: 'bopTopThreshold', label: 'BOP TEPE Esik', min: 0, max: 1, step: 0.05 },
            { key: 'demarkerDipThreshold', label: 'DeM DIP Esik', min: 1, max: 50, step: 1 },
            { key: 'demarkerTopThreshold', label: 'DeM TEPE Esik', min: 50, max: 99, step: 1 },
            { key: 'psyDipThreshold', label: 'PSY DIP Esik', min: 1, max: 50, step: 1 },
            { key: 'psyTopThreshold', label: 'PSY TEPE Esik', min: 50, max: 99, step: 1 },
            { key: 'zscoreDipThreshold', label: 'Z-Score DIP Esik', min: -5, max: 0, step: 0.1 },
            { key: 'zscoreTopThreshold', label: 'Z-Score TEPE Esik', min: 0, max: 5, step: 0.1 },
            { key: 'keltnerPercentDipThreshold', label: 'Kelt %B DIP Esik', min: -50, max: 100, step: 1 },
            { key: 'keltnerPercentTopThreshold', label: 'Kelt %B TEPE Esik', min: 0, max: 150, step: 1 },
            { key: 'macdDipThreshold', label: 'MACD Trend DIP', min: -10, max: 0, step: 0.1 },
            { key: 'macdTopThreshold', label: 'MACD Trend TEPE', min: 0, max: 10, step: 0.1 },
            { key: 'rsi2DipThreshold', label: 'RSI(2) DIP Esik', min: 1, max: 50, step: 1 },
            { key: 'rsi2TopThreshold', label: 'RSI(2) TEPE Esik', min: 50, max: 99, step: 1 },
        ],
    }
]
