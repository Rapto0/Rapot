import {
    evaluateWatchlistAlarmRule,
    type AlarmEvaluationResult,
    type AlarmSide,
    type StoredWatchlistModel,
    type WatchlistAlarmRule,
    type WatchlistSymbolRow,
} from "./watchlist-alarms"
import type { Candle } from "./indicators"

export interface TriggerHit {
    symbol: string
    marketType: "BIST" | "Kripto"
    side: AlarmSide
    detail: string
    value: number | null
}

export interface RuleRuntimeState {
    state: "checking" | "disabled" | "hit" | "no_hit" | "no_data" | "unknown" | "error" | "partial"
    checkedAt: string | null
    checkedSymbols: number
    totalSymbols: number
    triggerHits: TriggerHit[]
    errors: string[]
}

export interface LocalAlarmConfiguration {
    rules: WatchlistAlarmRule[]
    watchlists: StoredWatchlistModel[]
}

export interface LocalAlarmSnapshot {
    key: string
    isChecking: boolean
    lastCheckedAt: string | null
    runtimeByRuleId: Record<string, RuleRuntimeState>
}

export const alarmConfigurationKey = (configuration: LocalAlarmConfiguration) => JSON.stringify(configuration)

type ReadCandles = (row: WatchlistSymbolRow, rule: WatchlistAlarmRule, signal: AbortSignal) => Promise<Candle[]>
type SymbolResult = { row: WatchlistSymbolRow; evaluation?: AlarmEvaluationResult; error?: string }

const emptyRuntime = (state: RuleRuntimeState["state"], errors: string[] = []): RuleRuntimeState => ({
    state, errors, checkedAt: null, checkedSymbols: 0, totalSymbols: 0, triggerHits: [],
})

/** One page owns this monitor. Disposal invalidates results and all future polling. */
export function createLocalAlarmMonitor(options: {
    readCandles: ReadCandles
    onUpdate: (snapshot: LocalAlarmSnapshot) => void
    intervalMs?: number
    requestTimeoutMs?: number
}) {
    let configuration: LocalAlarmConfiguration = { rules: [], watchlists: [] }
    let key = ""
    let generation = 0
    let disposed = false
    let timer: ReturnType<typeof setInterval> | null = null
    let active: { controller: AbortController; promise: Promise<void> } | null = null
    const timeoutMs = options.requestTimeoutMs ?? 20_000

    function readSymbol(row: WatchlistSymbolRow, rule: WatchlistAlarmRule, parent: AbortSignal): Promise<SymbolResult> {
        return new Promise((resolve) => {
            const controller = new AbortController()
            let finished = false
            const finish = (result: SymbolResult) => {
                if (finished) return
                finished = true
                clearTimeout(timeout)
                parent.removeEventListener("abort", onAbort)
                resolve(result)
            }
            const onAbort = () => {
                controller.abort()
                finish({ row, error: "Kontrol iptal edildi" })
            }
            const timeout = setTimeout(() => {
                controller.abort()
                finish({ row, error: "Veri isteği zaman aşımına uğradı" })
            }, timeoutMs)
            if (parent.aborted) return onAbort()
            parent.addEventListener("abort", onAbort, { once: true })
            // Both branches settle even if an adapter ignores AbortSignal or rejects after disposal.
            Promise.resolve().then(() => {
                if (controller.signal.aborted) return
                return options.readCandles(row, rule, controller.signal)
            }).then((candles) => {
                if (finished) return
                try {
                    finish({ row, evaluation: evaluateWatchlistAlarmRule(rule, candles as Candle[]) })
                } catch {
                    finish({ row, error: "Gösterge hesaplanamadı" })
                }
            }, () => finish({ row, error: "Veri isteği başarısız" }))
        })
    }

    async function evaluateRule(rule: WatchlistAlarmRule, signal: AbortSignal): Promise<RuleRuntimeState> {
        if (!rule.enabled) return emptyRuntime("disabled", ["Kural kapalı"])
        const watchlist = configuration.watchlists.find((item) => item.id === rule.watchlistId)
        if (!watchlist) return emptyRuntime("unknown", ["Liste bulunamadı"])
        if (!watchlist.alarmsEnabled) return emptyRuntime("disabled", ["Bu liste için alarmlar kapalı"])
        const symbols = [...new Map(watchlist.rows
            .filter((row): row is WatchlistSymbolRow => row.kind === "symbol")
            .map((row) => [`${row.marketType}:${row.rawSymbol}`, row])).values()]
        if (!symbols.length) return emptyRuntime("no_data", ["Listede sembol yok"])
        const results: SymbolResult[] = []
        let next = 0
        async function worker() {
            while (!signal.aborted && next < symbols.length) {
                const row = symbols[next++]
                results.push(await readSymbol(row, rule, signal))
            }
        }
        await Promise.all(Array.from({ length: Math.min(4, symbols.length) }, worker))
        const runtime = emptyRuntime("no_hit")
        runtime.checkedAt = new Date().toISOString()
        runtime.totalSymbols = symbols.length
        for (const { row, evaluation, error } of results) {
            if (error || !evaluation || evaluation.state === "unknown" || evaluation.state === "no_data") {
                runtime.errors.push(`${row.rawSymbol}: ${error ?? evaluation?.detail ?? "Sonuç bilinmiyor"}`)
                continue
            }
            runtime.checkedSymbols++
            if (evaluation.triggered && evaluation.side) {
                runtime.triggerHits.push({
                    symbol: row.rawSymbol, marketType: row.marketType, side: evaluation.side,
                    detail: evaluation.detail, value: evaluation.value,
                })
            }
        }
        if (runtime.errors.length) {
            runtime.state = runtime.checkedSymbols > 0 ? "partial"
                : results.every((item) => item.error) ? "error"
                    : results.every((item) => item.evaluation?.state === "no_data") ? "no_data" : "unknown"
        } else if (runtime.triggerHits.length) runtime.state = "hit"
        return runtime
    }

    function run(): Promise<void> {
        if (disposed || !key) return Promise.resolve()
        if (active) return active.promise
        const controller = new AbortController()
        const runGeneration = generation
        const runKey = key
        const rules = configuration.rules
        const current = () => !disposed && generation === runGeneration && !controller.signal.aborted
        options.onUpdate({ key: runKey, isChecking: true, lastCheckedAt: null, runtimeByRuleId: {} })
        const promise = Promise.resolve().then(async () => {
            const runtimeByRuleId: Record<string, RuleRuntimeState> = {}
            for (const rule of rules) {
                if (!current()) return
                runtimeByRuleId[rule.id] = await evaluateRule(rule, controller.signal)
            }
            if (current()) options.onUpdate({
                key: runKey, isChecking: false,
                lastCheckedAt: rules.some((rule) => rule.enabled) ? new Date().toISOString() : null,
                runtimeByRuleId,
            })
        }).finally(() => {
            if (generation === runGeneration) active = null
        })
        active = { controller, promise }
        return promise
    }

    return {
        run,
        replace(next: LocalAlarmConfiguration): Promise<void> {
            if (disposed) return Promise.resolve()
            const nextKey = alarmConfigurationKey(next)
            if (nextKey === key) return active?.promise ?? Promise.resolve()
            generation++
            active?.controller.abort()
            active = null
            // Detached values prevent in-place caller edits from changing an in-flight pass.
            configuration = JSON.parse(nextKey) as LocalAlarmConfiguration
            key = nextKey
            if (timer === null) timer = setInterval(() => { void run() }, options.intervalMs ?? 60_000)
            return run()
        },
        dispose() {
            disposed = true
            generation++
            active?.controller.abort()
            active = null
            if (timer !== null) clearInterval(timer)
            timer = null
        },
    }
}
