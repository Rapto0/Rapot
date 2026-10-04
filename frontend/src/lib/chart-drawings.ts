/** Time/price anchored, browser-local drawings. No screen coordinates are persisted. */
export type Anchor = { time: number; price: number }
export type Point = { x: number; y: number }
export type DrawingCandle = Anchor & { open: number; high: number; low: number; close: number }
export const DRAWING_TOOLS = [
    { id: "trend", name: "Trend çizgisi", group: "Çizgiler", points: 2, hint: "Başlangıç ve bitişi seçin." },
    { id: "ray", name: "Işın", group: "Çizgiler", points: 2, hint: "Başlangıç ve yön noktası seçin." },
    { id: "extended", name: "Sonsuz çizgi", group: "Çizgiler", points: 2, hint: "Doğru üzerindeki iki noktayı seçin." },
    { id: "horizontal", name: "Yatay çizgi", group: "Çizgiler", points: 1, hint: "Fiyat seviyesini seçin." },
    { id: "horizontal-ray", name: "Yatay ışın", group: "Çizgiler", points: 1, hint: "Başlangıç zamanı ve fiyatını seçin." },
    { id: "vertical", name: "Dikey çizgi", group: "Çizgiler", points: 1, hint: "Zamanı seçin." },
    { id: "cross", name: "Çapraz işaret", group: "Çizgiler", points: 1, hint: "Zaman ve fiyat kesişimini seçin." },
    { id: "arrow", name: "Ok", group: "Çizgiler", points: 2, hint: "Başlangıç ve okun ucunu seçin." },
    { id: "rectangle", name: "Dikdörtgen", group: "Şekiller", points: 2, hint: "Karşılıklı iki köşeyi seçin." },
    { id: "ellipse", name: "Elips", group: "Şekiller", points: 2, hint: "Elipsi çevreleyen iki köşeyi seçin." },
    { id: "triangle", name: "Üçgen", group: "Şekiller", points: 3, hint: "Üç köşeyi sırayla seçin." },
    { id: "channel", name: "Paralel kanal", group: "Kanallar", points: 3, hint: "Ana çizginin iki ucunu, sonra paralel sınırı seçin." },
    { id: "pitchfork", name: "Andrews dirgeni", group: "Kanallar", points: 3, hint: "Pivotu, ardından iki karşı pivotu seçin." },
    { id: "regression", name: "Regresyon kanalı", group: "Kanallar", points: 2, hint: "Mum aralığını seçin. Kapanışlara doğrusal uyum ve ±2σ bantları çizilir." },
    { id: "fib", name: "Fibonacci düzeltme", group: "Fibonacci", points: 2, hint: "0 ve 1 seviyelerini belirleyen iki noktayı seçin." },
    { id: "fib-extension", name: "Fibonacci uzatma", group: "Fibonacci", points: 3, hint: "İlk hareketin iki ucunu, ardından uzatmanın başlangıcını seçin." },
    { id: "fib-fan", name: "Fibonacci yelpaze", group: "Fibonacci", points: 2, hint: "Başlangıç ve karşı köşeyi seçin." },
    { id: "fib-time", name: "Fibonacci zaman", group: "Fibonacci", points: 2, hint: "Temel mum aralığının iki ucunu seçin; 1, 2, 3, 5, 8, 13 katları çizilir." },
    { id: "ruler", name: "Cetvel", group: "Ölçüm", points: 2, hint: "Fiyat, yüzde ve mum aralığını ölçmek için iki nokta seçin." },
    { id: "price-range", name: "Fiyat aralığı", group: "Ölçüm", points: 2, hint: "Alt ve üst fiyat sınırını seçin." },
    { id: "date-range", name: "Zaman aralığı", group: "Ölçüm", points: 2, hint: "Başlangıç ve bitişi seçin; geçen süre ve mum aralığı gösterilir." },
    { id: "long", name: "Uzun pozisyon", group: "Planlama", points: 3, hint: "Girişi, hedefi ve stopu seçin. Bu bir çizimdir; emir veya alarm oluşturmaz." },
    { id: "short", name: "Kısa pozisyon", group: "Planlama", points: 3, hint: "Girişi, aşağıdaki hedefi ve yukarıdaki stopu seçin. Emir veya alarm oluşturmaz." },
    { id: "text", name: "Metin", group: "Notlar", points: 1, hint: "Notun yerini seçin; metni düzenleme alanından değiştirin." },
    { id: "freehand", name: "Serbest kalem", group: "Notlar", points: 0, hint: "Basılı tutup çizin, bırakınca kaydedilir." },
    { id: "highlighter", name: "Vurgulayıcı", group: "Notlar", points: 0, hint: "Vurgulamak istediğiniz alanın üzerinde basılı tutup sürükleyin." },
] as const
export type ToolId = (typeof DRAWING_TOOLS)[number]["id"]
export type DrawingStyle = { color: string; width: number; dashed: boolean; fill: number }
export type Drawing = { id: string; tool: ToolId; points: Anchor[]; style: DrawingStyle; text: string; locked: boolean; hidden: boolean }
export const DEFAULT_DRAWING_STYLE: DrawingStyle = { color: "#60a5fa", width: 2, dashed: false, fill: 0.12 }
export const MAX_DRAWINGS = 80
export const MAX_POINTS = 240
export const MAX_STORAGE_BYTES = 500_000
export const toolDefinition = (id: ToolId) => DRAWING_TOOLS.find((tool) => tool.id === id)!
export const drawingStorageKey = (market: string, symbol: string, timeframe: string) =>
    `rapot.chart.drawings.v1:${encodeURIComponent(market)}:${encodeURIComponent(symbol.trim().toUpperCase())}:${encodeURIComponent(timeframe)}`

const finite = (n: unknown): n is number => typeof n === "number" && Number.isFinite(n)
const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v)
export function validAnchor(v: unknown): v is Anchor {
    return object(v) && finite(v.time) && v.time >= 0 && v.time <= 32_503_680_000 && finite(v.price) && Math.abs(v.price) <= 1e15
}
export function parseDrawings(raw: string | null): { drawings: Drawing[]; error: string | null } {
    if (!raw) return { drawings: [], error: null }
    const invalid = { drawings: [], error: "Kayıtlı çizimler okunamadı. Eski kayıt korunuyor; yeni bir değişiklik yaptığınızda değiştirilir." }
    if (raw.length > MAX_STORAGE_BYTES) return invalid
    try {
        const value: unknown = JSON.parse(raw)
        if (!object(value) || value.version !== 1 || !Array.isArray(value.drawings) || value.drawings.length > MAX_DRAWINGS) return invalid
        const ids = new Set<string>()
        const drawings: Drawing[] = []
        for (const d of value.drawings) {
            if (!object(d) || typeof d.id !== "string" || !/^[\w-]{1,100}$/.test(d.id) || ids.has(d.id)) return invalid
            const definition = DRAWING_TOOLS.find((tool) => tool.id === d.tool)
            if (!definition || !Array.isArray(d.points) || d.points.length > MAX_POINTS || !d.points.every(validAnchor)) return invalid
            if (definition.points ? d.points.length !== definition.points : d.points.length < 2) return invalid
            if (!object(d.style) || typeof d.style.color !== "string" || !/^#[\da-f]{6}$/i.test(d.style.color) ||
                !finite(d.style.width) || d.style.width < 1 || d.style.width > 5 || typeof d.style.dashed !== "boolean" ||
                !finite(d.style.fill) || d.style.fill < 0 || d.style.fill > 0.5 || typeof d.text !== "string" || d.text.length > 180 ||
                typeof d.locked !== "boolean" || typeof d.hidden !== "boolean") return invalid
            ids.add(d.id)
            drawings.push({ id: d.id, tool: definition.id, points: d.points.map((p) => ({ time: p.time, price: p.price })),
                style: { color: d.style.color, width: d.style.width, dashed: d.style.dashed, fill: d.style.fill },
                text: d.text, locked: d.locked, hidden: d.hidden })
        }
        return { drawings, error: null }
    } catch { return invalid }
}
export function serializeDrawings(drawings: Drawing[]): string {
    const raw = JSON.stringify({ version: 1, drawings })
    if (raw.length > MAX_STORAGE_BYTES || parseDrawings(raw).error) throw new Error("Çizim kayıt sınırı aşıldı veya çizim geçersiz.")
    return raw
}
export type DrawingHistory = { past: Drawing[][]; present: Drawing[]; future: Drawing[][] }
export function changeDrawings(history: DrawingHistory, next: Drawing[]): DrawingHistory {
    serializeDrawings(next)
    if (JSON.stringify(history.present) === JSON.stringify(next)) return history
    return { past: [...history.past, history.present].slice(-35), present: next, future: [] }
}
export function undoDrawing(history: DrawingHistory): DrawingHistory {
    return history.past.length ? { past: history.past.slice(0, -1), present: history.past.at(-1)!, future: [history.present, ...history.future] } : history
}
export function redoDrawing(history: DrawingHistory): DrawingHistory {
    return history.future.length ? { past: [...history.past, history.present], present: history.future[0], future: history.future.slice(1) } : history
}

/** Logical indexes preserve market gaps. Extrapolation is visual, not a future session calendar. */
export function timeToLogical(time: number, times: number[], step: number): number {
    if (!times.length) return 0
    if (time <= times[0]) return (time - times[0]) / step
    const last = times.length - 1
    if (time >= times[last]) return last + (time - times[last]) / step
    let lo = 0, hi = last
    while (hi - lo > 1) { const mid = (lo + hi) >>> 1; if (times[mid] <= time) lo = mid; else hi = mid }
    return lo + (time - times[lo]) / (times[hi] - times[lo])
}
export function logicalToTime(logical: number, times: number[], step: number): number {
    if (!times.length) return 0
    if (logical <= 0) return times[0] + logical * step
    const last = times.length - 1
    if (logical >= last) return times[last] + (logical - last) * step
    const i = Math.floor(logical)
    return times[i] + (times[i + 1] - times[i]) * (logical - i)
}
export function snapAnchor(anchor: Anchor, candles: DrawingCandle[], times: number[], step: number): Anchor {
    if (!candles.length) return anchor
    const index = Math.round(timeToLogical(anchor.time, times, step))
    if (index < 0 || index >= candles.length) return anchor
    const candle = candles[index]
    const price = [candle.open, candle.high, candle.low, candle.close].reduce((best, value) =>
        Math.abs(value - anchor.price) < Math.abs(best - anchor.price) ? value : best, candle.close)
    return { time: candle.time, price }
}
export function positionMetrics(drawing: Drawing) {
    const [entry, target, stop] = drawing.points
    if (!entry || !target || !stop) return null
    const direction = drawing.tool === "short" ? -1 : 1
    const reward = (target.price - entry.price) * direction
    const risk = (entry.price - stop.price) * direction
    return { reward, risk, ratio: risk > 0 && reward > 0 ? reward / risk : null }
}

export type Primitive =
    | { kind: "line"; a: Point; b: Point; dashed?: boolean; color?: string }
    | { kind: "polygon" | "polyline"; points: Point[]; color?: string; opacity?: number }
    | { kind: "ellipse"; a: Point; b: Point }
    | { kind: "text"; at: Point; text: string; color?: string }
export type GeometryContext = { width: number; height: number; project: (anchor: Anchor) => Point | null; candles: DrawingCandle[]; times: number[]; step: number }
const add = (a: Point, b: Point): Point => ({ x: a.x + b.x, y: a.y + b.y })
const sub = (a: Point, b: Point): Point => ({ x: a.x - b.x, y: a.y - b.y })
const scale = (a: Point, f: number): Point => ({ x: a.x * f, y: a.y * f })
const midpoint = (a: Point, b: Point) => scale(add(a, b), .5)
const num = (n: number) => Number.isFinite(n) ? n.toLocaleString("tr-TR", { maximumFractionDigits: 4 }) : "—"
/** Clips a line/ray/segment without enormous SVG coordinates or slope singularities. */
export function clipLine(a: Point, b: Point, width: number, height: number, mode: "segment" | "ray" | "line" = "segment"): [Point, Point] | null {
    const dx = b.x - a.x, dy = b.y - a.y
    if (Math.abs(dx) + Math.abs(dy) < 1e-8) return null
    let low = mode === "line" ? -Infinity : 0, high = mode === "segment" ? 1 : Infinity
    for (const [p, q] of [[-dx, a.x], [dx, width - a.x], [-dy, a.y], [dy, height - a.y]]) {
        if (Math.abs(p) < 1e-10) { if (q < 0) return null; continue }
        if (p < 0) low = Math.max(low, q / p); else high = Math.min(high, q / p)
        if (low > high) return null
    }
    return [add(a, scale({ x: dx, y: dy }, low)), add(a, scale({ x: dx, y: dy }, high))]
}
export function drawingGeometry(d: Drawing, ctx: GeometryContext): Primitive[] {
    if (d.hidden || !d.points.length) return []
    const p = d.points.map(ctx.project)
    if (p.some((point) => !point)) return []
    const [a, b = a, c = b] = p as Point[]
    const out: Primitive[] = []
    const line = (start: Point, end: Point, mode: "segment" | "ray" | "line" = "segment", dashed = false, color?: string) => {
        const clipped = clipLine(start, end, ctx.width, ctx.height, mode)
        if (clipped) out.push({ kind: "line", a: clipped[0], b: clipped[1], dashed, color })
    }
    const text = (at: Point, label: string, color?: string) => out.push({ kind: "text", at, text: label, color })
    const box = (start: Point, end: Point, color?: string) => out.push({ kind: "polygon", points: [start, { x: end.x, y: start.y }, end, { x: start.x, y: end.y }], color })
    const priceDiff = (d.points[1]?.price ?? d.points[0].price) - d.points[0].price
    const pct = d.points[0].price ? `${num(priceDiff / d.points[0].price * 100)}%` : "yüzde yok"
    const logical = (anchor: Anchor) => timeToLogical(anchor.time, ctx.times, ctx.step)
    const bars = Math.abs(logical(d.points[1] ?? d.points[0]) - logical(d.points[0]))
    switch (d.tool) {
        case "trend": line(a, b); break
        case "ray": line(a, b, "ray"); break
        case "extended": line(a, b, "line"); break
        case "horizontal": line({ x: 0, y: a.y }, { x: ctx.width, y: a.y }); text({ x: 8, y: a.y - 6 }, num(d.points[0].price)); break
        case "horizontal-ray": line(a, { x: ctx.width, y: a.y }); text({ x: a.x + 6, y: a.y - 6 }, num(d.points[0].price)); break
        case "vertical": line({ x: a.x, y: 0 }, { x: a.x, y: ctx.height }); break
        case "cross": line({ x: 0, y: a.y }, { x: ctx.width, y: a.y }); line({ x: a.x, y: 0 }, { x: a.x, y: ctx.height }); break
        case "arrow": {
            line(a, b)
            const angle = Math.atan2(b.y - a.y, b.x - a.x)
            for (const offset of [-.5, .5]) line(b, { x: b.x - 12 * Math.cos(angle + offset), y: b.y - 12 * Math.sin(angle + offset) })
            break
        }
        case "rectangle": box(a, b); break
        case "ellipse": out.push({ kind: "ellipse", a, b }); break
        case "triangle": out.push({ kind: "polygon", points: [a, b, c] }); break
        case "channel": {
            // The third anchor offsets the base line vertically at its own time.
            const dy = Math.abs(b.x - a.x) > .01 ? c.y - (a.y + (b.y - a.y) * (c.x - a.x) / (b.x - a.x)) : c.y - a.y
            const offset = { x: 0, y: dy }
            out.push({ kind: "polygon", points: [a, b, add(b, offset), add(a, offset)] })
            line(add(a, scale(offset, .5)), add(b, scale(offset, .5)), "segment", true)
            break
        }
        case "pitchfork": {
            const mid = midpoint(b, c), direction = sub(mid, a)
            line(b, c); line(a, mid, "ray"); line(b, add(b, direction), "ray"); line(c, add(c, direction), "ray")
            break
        }
        case "regression": {
            const start = Math.min(d.points[0].time, d.points[1].time), end = Math.max(d.points[0].time, d.points[1].time)
            const samples = ctx.candles.filter((candle) => candle.time >= start && candle.time <= end)
            if (samples.length < 2) { text(a, "En az iki mevcut mum seçin"); break }
            const n = samples.length, mx = (n - 1) / 2, my = samples.reduce((sum, row) => sum + row.close, 0) / n
            let cov = 0, variance = 0
            samples.forEach((row, i) => { cov += (i - mx) * (row.close - my); variance += (i - mx) ** 2 })
            const slope = cov / variance, intercept = my - slope * mx
            const sigma = Math.sqrt(samples.reduce((sum, row, i) => sum + (row.close - (intercept + slope * i)) ** 2, 0) / n)
            for (const offset of [-2, 0, 2]) {
                const from = ctx.project({ time: samples[0].time, price: intercept + offset * sigma })
                const to = ctx.project({ time: samples[n - 1].time, price: intercept + slope * (n - 1) + offset * sigma })
                if (from && to) line(from, to, "segment", offset === 0)
            }
            text({ x: Math.min(a.x, b.x) + 4, y: Math.min(a.y, b.y) - 8 }, `${n} mum · ±2σ ${num(2 * sigma)}`)
            break
        }
        case "fib":
        case "fib-extension": {
            const extension = d.tool === "fib-extension"
            const base = extension ? d.points[2].price : d.points[0].price
            for (const ratio of extension ? [0, .618, 1, 1.272, 1.618, 2.618] : [0, .236, .382, .5, .618, .786, 1]) {
                const price = base + priceDiff * ratio
                const point = ctx.project({ time: d.points[0].time, price })
                if (!point) continue
                const left = Math.min(a.x, b.x, ...(extension ? [c.x] : [])), right = Math.max(a.x, b.x, ...(extension ? [c.x] : []))
                line({ x: left, y: point.y }, { x: right, y: point.y }, "segment", ratio !== 0 && ratio !== 1)
                text({ x: left + 4, y: point.y - 5 }, `${num(ratio)} · ${num(price)}`)
            }
            line(a, b, "segment", true); if (extension) line(b, c, "segment", true)
            break
        }
        case "fib-fan":
            for (const ratio of [.382, .5, .618]) {
                const end = { x: b.x, y: a.y + (b.y - a.y) * ratio }
                line(a, end, "ray"); text(end, num(ratio))
            }
            line(a, b, "segment", true); break
        case "fib-time": {
            const first = logical(d.points[0]), distance = logical(d.points[1]) - first
            for (const multiple of [0, 1, 2, 3, 5, 8, 13]) {
                const point = ctx.project({ time: logicalToTime(first + distance * multiple, ctx.times, ctx.step), price: d.points[0].price })
                if (!point) continue
                line({ x: point.x, y: 0 }, { x: point.x, y: ctx.height }); text({ x: point.x + 4, y: 18 }, String(multiple))
            }
            break
        }
        case "ruler": box(a, b); line(a, b, "segment", true); text(midpoint(a, b), `${num(priceDiff)} · ${pct} · ${num(bars)} mum aralığı`); break
        case "price-range": {
            box(a, b)
            const center = (a.x + b.x) / 2
            line({ x: center, y: a.y }, { x: center, y: b.y }); text({ x: center + 6, y: (a.y + b.y) / 2 }, `${num(priceDiff)} · ${pct}`)
            break
        }
        case "date-range": {
            box({ x: a.x, y: 0 }, { x: b.x, y: ctx.height })
            const seconds = Math.abs(d.points[1].time - d.points[0].time)
            text({ x: Math.min(a.x, b.x) + 6, y: Math.max(20, a.y) }, `${num(bars)} mum aralığı · ${num(seconds / (seconds >= 86400 ? 86400 : 3600))} ${seconds >= 86400 ? "gün" : "saat"}`)
            break
        }
        case "long":
        case "short": {
            const right = Math.max(b.x, c.x, a.x + 45)
            box(a, { x: right, y: b.y }, "#34d399"); box(a, { x: right, y: c.y }, "#fb7185")
            line(a, { x: right, y: a.y })
            const metrics = positionMetrics(d)
            text({ x: a.x + 5, y: a.y - 5 }, metrics?.ratio == null ? "Hedef/stop yönünü düzeltin" : `Getiri / risk ${num(metrics.ratio)}`)
            text({ x: a.x + 5, y: b.y - 5 }, `Hedef ${num(d.points[1].price)}`, "#34d399")
            text({ x: a.x + 5, y: c.y - 5 }, `Stop ${num(d.points[2].price)}`, "#fb7185")
            break
        }
        case "text": text(a, d.text || "Not"); break
        case "freehand": out.push({ kind: "polyline", points: p as Point[] }); break
        case "highlighter": out.push({ kind: "polyline", points: p as Point[], opacity: .35 }); break
    }
    return out
}
