import type { AdvancedAlarmRule, AdvancedAlarmWrite, AlarmCategory, AlarmField, AlarmSymbol, AlarmTimeframe, CompareOp, Condition, ConditionGroup, ConditionLeaf, FieldRef } from "./api/advanced-alarms-api"

export const CATEGORY_LABELS: Record<AlarmCategory, string> = { price: "Fiyat", technical: "Teknik", watchlist: "İzleme listesi" }
export const TIMEFRAME_LABELS: Record<AlarmTimeframe, string> = { "1m": "1 dakika", "5m": "5 dakika", "15m": "15 dakika", "30m": "30 dakika", "1h": "1 saat", "4h": "4 saat", "1d": "1 gün", "1wk": "1 hafta", "1mo": "1 ay" }
export const FIELD_LABELS: Record<AlarmField, string> = { price: "Son fiyat", open: "Açılış", high: "En yüksek", low: "En düşük", close: "Kapanış", volume: "Hacim", rsi: "RSI", ema: "EMA", sma: "SMA", macd: "MACD", macd_signal: "MACD sinyal", atr: "ATR", wr: "Williams %R", combo: "COMBO", hunter: "HUNTER" }
export const OP_LABELS: Record<CompareOp, string> = { gt: "Büyüktür", gte: "Büyük veya eşit", lt: "Küçüktür", lte: "Küçük veya eşit", eq: "Eşittir", crossed_above: "Yukarı keser", crossed_below: "Aşağı keser" }
export const PERIOD_FIELDS = new Set<AlarmField>(["rsi", "ema", "sma", "atr", "wr"])
export const isGroup = (node: Condition): node is ConditionGroup => node.op === "and" || node.op === "or"
export const makeRef = (field: AlarmField): FieldRef => ({ field, ...(PERIOD_FIELDS.has(field) ? { period: field === "ema" || field === "sma" ? 20 : 14 } : {}), ...(field === "combo" || field === "hunter" ? { side: "buy" as const } : {}) })
export const defaultLeaf = (category: AlarmCategory = "technical"): ConditionLeaf => ({ op: "crossed_above", left: makeRef(category === "price" ? "price" : "rsi"), right: category === "price" ? 100 : 30 })

export interface AdvancedDraft extends Omit<AdvancedAlarmWrite, "symbols" | "revision"> { bist: string; crypto: string }
export function emptyAdvancedDraft(category: AlarmCategory = "price"): AdvancedDraft {
    return { name: "", category, scope: category === "watchlist" ? "all_bist" : "symbols", bist: "", crypto: "", watchlist_id: null, timeframe: "1m", trigger: "intrabar", condition: defaultLeaf(category), mode: "on_enter", cooldown_seconds: 60, enabled: true, notify_telegram: false }
}
export function parseAlarmSymbols(bist: string, crypto: string): AlarmSymbol[] {
    const rows: AlarmSymbol[] = []
    const seen = new Set<string>()
    for (const [raw, market] of [[bist, "BIST"], [crypto, "Kripto"]] as const) {
        for (const token of raw.toUpperCase().split(/[\s,;]+/).filter(Boolean)) {
            const symbol = market === "BIST" ? token.replace(/\.IS$/, "") : token
            if (!(market === "BIST" ? /^[A-Z0-9]{1,20}$/ : /^[A-Z0-9]{2,20}USDT$/).test(symbol)) throw new Error(`Geçersiz sembol: ${token}. Kripto için Binance USDT çifti kullanın.`)
            const key = `${market}:${symbol}`
            if (!seen.has(key)) { seen.add(key); rows.push({ symbol, market_type: market }) }
        }
    }
    if (rows.length > 2000) throw new Error("Bir liste en fazla 2.000 sembol içerebilir.")
    return rows
}
export function validateTree(tree: Condition): void {
    let leaves = 0, nodes = 0
    function ref(value: FieldRef) {
        if (!Object.hasOwn(FIELD_LABELS, value.field)) throw new Error("Gösterge desteklenmiyor.")
        if (value.timeframe && !Object.hasOwn(TIMEFRAME_LABELS, value.timeframe)) throw new Error("Gösterge periyodu desteklenmiyor.")
        if (PERIOD_FIELDS.has(value.field) && (!Number.isInteger(value.period) || (value.period ?? 0) < 2 || (value.period ?? 0) > 200)) throw new Error("Gösterge uzunluğu 2–200 arasında olmalıdır.")
    }
    function visit(node: Condition, depth: number) {
        if (++nodes > 63 || depth > 4) throw new Error("En fazla 4 seviye koşul grubu kullanılabilir.")
        if (isGroup(node)) {
            if (!node.children.length || node.children.length > 32) throw new Error("Koşul grubu boş olamaz; en fazla 32 öğe kullanılabilir.")
            node.children.forEach(child => visit(child, depth + 1))
        } else {
            if (++leaves > 32) throw new Error("Bir alarm en fazla 32 karşılaştırma içerebilir.")
            if (!Object.hasOwn(OP_LABELS, node.op)) throw new Error("Karşılaştırma desteklenmiyor.")
            ref(node.left)
            if (typeof node.right === "number") {
                if (!Number.isFinite(node.right) || Math.abs(node.right) > 1e15) throw new Error("Karşılaştırma değeri geçerli bir sayı olmalıdır.")
            } else ref(node.right)
        }
    }
    visit(tree, 1)
}
export function writeFromAdvancedDraft(draft: AdvancedDraft, revision?: number): AdvancedAlarmWrite {
    const name = draft.name.trim()
    if (!name || name.length > 80 || /[\u0000-\u001f]/.test(name)) throw new Error("Alarm adı 1–80 karakter olmalıdır.")
    validateTree(draft.condition)
    const symbols = draft.scope === "symbols" ? parseAlarmSymbols(draft.bist, draft.crypto) : []
    if (draft.scope === "symbols" && !symbols.length) throw new Error("En az bir hisse veya kripto çifti girin.")
    if (draft.scope === "watchlist" && !draft.watchlist_id) throw new Error("Sunucuda kayıtlı bir izleme listesi seçin.")
    if (!Number.isInteger(draft.cooldown_seconds) || draft.cooldown_seconds < 1 || draft.cooldown_seconds > 86400) throw new Error("Tekrar bekleme süresi 1–86.400 saniye olmalıdır.")
    const { bist: _bist, crypto: _crypto, ...rest } = draft
    void _bist; void _crypto
    return { ...rest, name, symbols, condition: structuredClone(draft.condition), watchlist_id: draft.scope === "watchlist" ? draft.watchlist_id : null, ...(revision === undefined ? {} : { revision }) }
}
export function draftFromAdvancedRule(rule: AdvancedAlarmRule): AdvancedDraft {
    return { name: rule.name, category: rule.category, scope: rule.scope, bist: rule.symbols.filter(x => x.market_type === "BIST").map(x => x.symbol).join(", "), crypto: rule.symbols.filter(x => x.market_type === "Kripto").map(x => x.symbol).join(", "), watchlist_id: rule.watchlist_id, timeframe: rule.timeframe, trigger: rule.trigger, condition: structuredClone(rule.condition), mode: rule.mode, cooldown_seconds: rule.cooldown_seconds, enabled: rule.enabled, notify_telegram: rule.notify_telegram }
}
export function conditionLabel(node: Condition): string {
    if (isGroup(node)) return `(${node.children.map(conditionLabel).join(node.op === "and" ? " VE " : " VEYA ")})`
    const field = (ref: FieldRef) => `${FIELD_LABELS[ref.field]}${ref.period ? `(${ref.period})` : ""}${ref.side ? ref.side === "buy" ? " alış" : " satış" : ""}${ref.timeframe ? ` · ${TIMEFRAME_LABELS[ref.timeframe]}` : ""}`
    return `${field(node.left)} ${OP_LABELS[node.op].toLocaleLowerCase("tr-TR")} ${typeof node.right === "number" ? node.right : field(node.right)}`
}
export function mergeAlarmEvents<T extends { id: number }>(oldRows: T[], incoming: T[], limit = 200): T[] {
    const byId = new Map(oldRows.map(row => [row.id, row]))
    incoming.forEach(row => byId.set(row.id, row))
    return [...byId.values()].sort((a, b) => b.id - a.id).slice(0, limit)
}
