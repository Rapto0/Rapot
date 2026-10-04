"use client"

import { useCallback, useEffect, useId, useMemo, useRef, useState, type PointerEvent, type RefObject } from "react"
import { Check, ChevronDown, Copy, Eye, EyeOff, Hand, Layers, Lock, Magnet, MousePointer2, Pencil, Redo2, Trash2, Undo2, Unlock, X } from "lucide-react"
import { cn } from "@/lib/utils"
import {
    DRAWING_TOOLS, DEFAULT_DRAWING_STYLE, MAX_DRAWINGS, MAX_POINTS, changeDrawings, drawingGeometry,
    drawingStorageKey, logicalToTime, parseDrawings, redoDrawing, serializeDrawings, snapAnchor,
    timeToLogical, toolDefinition, undoDrawing, validAnchor,
    type Anchor, type Drawing, type DrawingCandle, type DrawingHistory, type DrawingStyle,
    type Point, type Primitive, type ToolId,
} from "@/lib/chart-drawings"

interface TimeScale {
    coordinateToLogical(x: number): number | null
    logicalToCoordinate(logical: number): number | null
    width(): number
    height(): number
    subscribeVisibleLogicalRangeChange(handler: () => void): void
    unsubscribeVisibleLogicalRangeChange(handler: () => void): void
}
interface ChartHandle { timeScale(): TimeScale; paneSize(paneIndex?: number): { width: number; height: number } }
interface SeriesHandle { coordinateToPrice(y: number): number | null; priceToCoordinate(price: number): number | null }
interface Props {
    chartRef: RefObject<ChartHandle | null>
    seriesRef: RefObject<SeriesHandle | null>
    containerRef: RefObject<HTMLDivElement | null>
    ready: boolean
    market: string
    symbol: string
    timeframe: string
    step: number
    candles: { time: string; open: number; high: number; low: number; close: number }[]
    parseTime: (value: string) => number | null
    projectionVersion: number
    open: boolean
    onOpenChange: (open: boolean) => void
    onDrawingMode: (active: boolean) => void
    onCountChange: (count: number) => void
}
const button = "inline-flex h-8 min-w-8 shrink-0 items-center justify-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-35 disabled:pointer-events-none"
const input = "h-8 min-w-0 rounded-md border border-border bg-background px-2 text-xs text-foreground"
const emptyHistory = (): DrawingHistory => ({ past: [], present: [], future: [] })
const uid = () => globalThis.crypto?.randomUUID?.() ?? `drawing-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
type Drag = { id: string; handle: number | null; start: Anchor; original: Drawing; moved: boolean }

function Shape({ shape, drawing, hit = false }: { shape: Primitive; drawing: Drawing; hit?: boolean }) {
    const color = shape.kind !== "ellipse" && shape.color || drawing.style.color
    const width = drawing.tool === "highlighter" ? drawing.style.width * 7 : drawing.style.width
    const common = { stroke: hit ? "transparent" : color, strokeWidth: hit ? Math.max(14, width) : width,
        strokeDasharray: !hit && (drawing.style.dashed || (shape.kind === "line" && shape.dashed)) ? "6 4" : undefined,
        strokeLinecap: "round" as const, strokeLinejoin: "round" as const, vectorEffect: "non-scaling-stroke" }
    switch (shape.kind) {
        case "line": return <line {...common} x1={shape.a.x} y1={shape.a.y} x2={shape.b.x} y2={shape.b.y} />
        case "polygon": return <polygon {...common} points={shape.points.map((p) => `${p.x},${p.y}`).join(" ")} fill={hit ? "transparent" : color} fillOpacity={hit ? 1 : drawing.style.fill} />
        case "polyline": return <polyline {...common} points={shape.points.map((p) => `${p.x},${p.y}`).join(" ")} fill="none" opacity={hit ? 1 : shape.opacity ?? 1} />
        case "ellipse": return <ellipse {...common} cx={(shape.a.x + shape.b.x) / 2} cy={(shape.a.y + shape.b.y) / 2} rx={Math.abs(shape.b.x - shape.a.x) / 2} ry={Math.abs(shape.b.y - shape.a.y) / 2} fill={hit ? "transparent" : color} fillOpacity={hit ? 1 : drawing.style.fill} />
        case "text": return hit
            ? <rect x={shape.at.x - 4} y={shape.at.y - 16} width={Math.min(1100, Math.max(30, shape.text.length * 7))} height={22} fill="transparent" />
            : <text x={shape.at.x} y={shape.at.y} fontSize={12} fontWeight={500} fill={color} stroke="#111827" strokeWidth={3} paintOrder="stroke" strokeLinejoin="round">{shape.text}</text>
    }
}

/** Mounted with a context key by the chart: switching symbol/period cannot save into another context. */
export function ChartDrawingTools(props: Props) {
    const { chartRef, seriesRef, containerRef, ready, step, onDrawingMode, onCountChange, candles, parseTime } = props
    const key = drawingStorageKey(props.market, props.symbol, props.timeframe)
    const clipId = useId().replace(/:/g, "")
    const [history, setHistory] = useState<DrawingHistory>(emptyHistory)
    const historyRef = useRef(history)
    const [hydrated, setHydrated] = useState(false)
    const dirtyRef = useRef(false)
    const [notice, setNotice] = useState<string | null>(null)
    const [mode, setMode] = useState<"select" | "pan" | ToolId>("select")
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [style, setStyle] = useState<DrawingStyle>(DEFAULT_DRAWING_STYLE)
    const [snap, setSnap] = useState(false)
    const [hideAll, setHideAll] = useState(false)
    const [showObjects, setShowObjects] = useState(false)
    const [query, setQuery] = useState("")
    const [draft, setDraft] = useState<Anchor[]>([])
    const draftRef = useRef<Anchor[]>([])
    const [hover, setHover] = useState<Anchor | null>(null)
    const [dragPreview, setDragPreview] = useState<Drawing | null>(null)
    const dragRef = useRef<Drag | null>(null)
    const previewRef = useRef<Drawing | null>(null)
    const freehandRef = useRef(false)
    const [size, setSize] = useState({ width: 0, height: 0 })
    const [projection, setProjection] = useState<{ chart: ChartHandle; series: SeriesHandle } | null>(null)
    const [clearConfirm, setClearConfirm] = useState(false)
    const svgRef = useRef<SVGSVGElement>(null)
    const sectionRef = useRef<HTMLDivElement>(null)
    const drawingMode = mode !== "select" && mode !== "pan"
    const definition = drawingMode ? toolDefinition(mode) : null
    const data = useMemo<DrawingCandle[]>(() => candles.flatMap((candle) => {
        const time = parseTime(candle.time)
        return time !== null && [time, candle.open, candle.high, candle.low, candle.close].every(Number.isFinite)
            ? [{ time, price: candle.close, open: candle.open, high: candle.high, low: candle.low, close: candle.close }] : []
    }), [candles, parseTime])
    const times = useMemo(() => data.map((row) => row.time), [data])
    const selected = history.present.find((drawing) => drawing.id === selectedId) ?? null

    useEffect(() => {
        try {
            const loaded = parseDrawings(localStorage.getItem(key))
            const next = { ...emptyHistory(), present: loaded.drawings }
            historyRef.current = next
            setHistory(next)
            setNotice(loaded.error)
        } catch { setNotice("Tarayıcı depolaması kullanılamıyor; çizimler yalnız bu oturumda tutulacak.") }
        setHydrated(true)
    }, [key])
    useEffect(() => {
        if (!hydrated || !dirtyRef.current) return
        try { localStorage.setItem(key, serializeDrawings(history.present)) }
        catch { setNotice("Çizimler tarayıcıya kaydedilemedi. Bu oturumdaki çizimler korunuyor.") }
    }, [history.present, hydrated, key])
    useEffect(() => { onDrawingMode(drawingMode || !!dragPreview) }, [drawingMode, dragPreview, onDrawingMode])
    useEffect(() => { onCountChange(history.present.length) }, [history.present.length, onCountChange])
    useEffect(() => () => { onDrawingMode(false); onCountChange(0) }, [onDrawingMode, onCountChange])

    useEffect(() => {
        if (!ready || !chartRef.current || !containerRef.current) return
        const container = containerRef.current, chart = chartRef.current
        let raf: number | null = null
        const refresh = () => {
            if (raf !== null) return
            raf = requestAnimationFrame(() => {
                raf = null
                try {
                    // A hidden main time axis reports width 0 when indicator panes own
                    // the visible axis. Drawing coordinates belong to the price pane.
                    const pane = chart.paneSize(0)
                    setSize({ width: pane.width, height: pane.height })
                    if (seriesRef.current) setProjection({ chart, series: seriesRef.current })
                } catch { /* Chart may have been disposed during a layout change. */ }
            })
        }
        refresh()
        const observer = new ResizeObserver(refresh)
        observer.observe(container)
        chart.timeScale().subscribeVisibleLogicalRangeChange(refresh)
        // Price-axis dragging has no public price-scale-change event in Lightweight Charts.
        container.addEventListener("pointermove", refresh)
        container.addEventListener("wheel", refresh, { passive: true })
        return () => {
            observer.disconnect()
            container.removeEventListener("pointermove", refresh)
            container.removeEventListener("wheel", refresh)
            try { chart.timeScale().unsubscribeVisibleLogicalRangeChange(refresh) } catch { /* disposed */ }
            if (raf !== null) cancelAnimationFrame(raf)
        }
    }, [ready, chartRef, seriesRef, containerRef, props.projectionVersion])

    const project = (anchor: Anchor): Point | null => {
        try {
            if (!times.length) return null
            const x = projection?.chart.timeScale().logicalToCoordinate(timeToLogical(anchor.time, times, step))
            const y = projection?.series.priceToCoordinate(anchor.price)
            return x != null && y != null && Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null
        } catch { return null }
    }
    const anchorAt = (event: { clientX: number; clientY: number }, magnet = snap): Anchor | null => {
        const bounds = containerRef.current?.getBoundingClientRect()
        if (!bounds || !times.length) return null
        const x = Math.max(0, Math.min(size.width, event.clientX - bounds.left))
        const y = Math.max(0, Math.min(size.height, event.clientY - bounds.top))
        const logical = chartRef.current?.timeScale().coordinateToLogical(x)
        const price = seriesRef.current?.coordinateToPrice(y)
        if (logical == null || price == null) return null
        const anchor = { time: logicalToTime(logical, times, step), price }
        if (!validAnchor(anchor)) return null
        return magnet ? snapAnchor(anchor, data, times, step) : anchor
    }
    const commit = (next: Drawing[]) => {
        try {
            const updated = changeDrawings(historyRef.current, next)
            dirtyRef.current = true
            historyRef.current = updated
            setHistory(updated)
        } catch { setNotice("En fazla 80 çizim saklanabilir. Bazı çizimleri silip tekrar deneyin.") }
    }
    const cancel = useCallback(() => {
        draftRef.current = []; freehandRef.current = false; dragRef.current = null; previewRef.current = null
        setDraft([]); setHover(null); setDragPreview(null); setMode("select")
    }, [])
    const travel = (direction: "undo" | "redo") => {
        cancel()
        const next = direction === "undo" ? undoDrawing(historyRef.current) : redoDrawing(historyRef.current)
        dirtyRef.current = true; historyRef.current = next; setHistory(next)
    }
    const updateSelected = (patch: Partial<Drawing>) => {
        if (!selected || selected.locked) return
        commit(historyRef.current.present.map((drawing) => drawing.id === selected.id ? { ...drawing, ...patch } : drawing))
    }
    const addDrawing = (points: Anchor[]) => {
        if (!definition || historyRef.current.present.length >= MAX_DRAWINGS) {
            setNotice("80 çizim sınırına ulaşıldı. Yeni çizim için birini silin."); cancel(); return
        }
        const drawing: Drawing = { id: uid(), tool: definition.id, points, style: { ...style }, text: definition.id === "text" ? "Not" : "", locked: false, hidden: false }
        commit([...historyRef.current.present, drawing]); setSelectedId(drawing.id); cancel()
        if (drawing.tool === "text") props.onOpenChange(true)
    }
    const setTool = (tool: typeof mode) => {
        cancel(); setMode(tool); setSelectedId(null); setHideAll(false); setClearConfirm(false)
        props.onOpenChange(false)
        requestAnimationFrame(() => svgRef.current?.focus())
    }
    const pointerDown = (event: PointerEvent<SVGSVGElement>) => {
        if (!drawingMode || event.button !== 0 || !hydrated) return
        event.preventDefault()
        svgRef.current?.focus()
        const point = anchorAt(event)
        if (!point || !definition) return
        if (definition.points === 0) {
            freehandRef.current = true; draftRef.current = [point]; setDraft([point])
            event.currentTarget.setPointerCapture(event.pointerId)
        } else {
            const next = [...draftRef.current, point]
            if (next.length === definition.points) addDrawing(next)
            else { draftRef.current = next; setDraft(next); setHover(point) }
        }
    }
    const beginDrag = (event: PointerEvent<SVGGElement | SVGCircleElement>, drawing: Drawing, handle: number | null) => {
        if (mode !== "select" || event.button !== 0) return
        event.stopPropagation(); event.preventDefault(); setSelectedId(drawing.id); svgRef.current?.focus()
        if (drawing.locked) return
        const start = anchorAt(event, false)
        if (!start) return
        dragRef.current = { id: drawing.id, handle, start, original: drawing, moved: false }
        svgRef.current?.setPointerCapture(event.pointerId)
    }
    const pointerMove = (event: PointerEvent<SVGSVGElement>) => {
        const point = anchorAt(event)
        if (!point) return
        const drag = dragRef.current
        if (drag) {
            drag.moved = true
            const deltaLogical = timeToLogical(point.time, times, step) - timeToLogical(drag.start.time, times, step)
            const next = { ...drag.original, points: drag.original.points.map((anchor, index) => drag.handle === null
                ? { time: logicalToTime(timeToLogical(anchor.time, times, step) + deltaLogical, times, step), price: anchor.price + point.price - drag.start.price }
                : index === drag.handle ? point : anchor) }
            if (!next.points.every(validAnchor)) return
            previewRef.current = next; setDragPreview(next); return
        }
        if (freehandRef.current) {
            const last = project(draftRef.current.at(-1)!)
            const current = project(point)
            if (last && current && Math.hypot(current.x - last.x, current.y - last.y) < 2) return
            // Keep the stroke bounded while preserving both endpoints.
            const existing = draftRef.current.length >= MAX_POINTS ? draftRef.current.filter((_, i) => i % 2 === 0) : draftRef.current
            draftRef.current = [...existing, point]; setDraft(draftRef.current)
        } else if (drawingMode && draftRef.current.length) setHover(point)
    }
    const pointerUp = () => {
        const drag = dragRef.current
        if (drag?.moved && previewRef.current) commit(historyRef.current.present.map((drawing) => drawing.id === drag.id ? previewRef.current! : drawing))
        dragRef.current = null; previewRef.current = null; setDragPreview(null)
        if (freehandRef.current) {
            freehandRef.current = false
            if (draftRef.current.length >= 2) addDrawing(draftRef.current)
            else { draftRef.current = []; setDraft([]) }
        }
    }
    const context = { ...size, project, candles: data, times, step }
    const rendered = history.present.map((drawing) => dragPreview?.id === drawing.id ? dragPreview : drawing)
    const previewPoints = definition && draft.length ? definition.points === 0 ? draft : [...draft, ...(hover ? [hover] : [])].slice(0, definition.points) : []
    // Repeat the last point only while previewing an unfinished three-point drawing.
    while (definition && previewPoints.length && previewPoints.length < definition.points) previewPoints.push(previewPoints.at(-1)!)
    const preview: Drawing | null = definition && previewPoints.length > 1 ? { id: "draft", tool: definition.id, points: previewPoints, style, text: "Not", locked: false, hidden: false } : null
    const groups = [...new Set(DRAWING_TOOLS.map((tool) => tool.group))]
    const changeStyle = (patch: Partial<DrawingStyle>) => {
        setStyle((previous) => ({ ...previous, ...patch }))
        if (selected && !selected.locked) updateSelected({ style: { ...selected.style, ...patch } })
    }
    const currentStyle = selected?.style ?? style
    const removeSelected = () => { if (selected && !selected.locked) { commit(historyRef.current.present.filter((d) => d.id !== selected.id)); setSelectedId(null) } }
    return <div ref={sectionRef} className="pointer-events-none absolute inset-0 z-[22]" onKeyDown={(event) => {
        if (event.key === "Escape") { cancel(); props.onOpenChange(false); setSelectedId(null); return }
        if ((event.target as HTMLElement).closest?.("input,textarea,select")) return
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") { event.preventDefault(); travel(event.shiftKey ? "redo" : "undo") }
        else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") { event.preventDefault(); travel("redo") }
        else if (event.key === "Delete" || event.key === "Backspace") { event.preventDefault(); removeSelected() }
    }}>
        <svg ref={svgRef} tabIndex={0} aria-label="Grafik çizim alanı. Çizim araçlarından birini seçin. Escape iptal, Delete sil, Control Z geri al."
            width={size.width} height={size.height} className="absolute left-0 top-0 overflow-hidden outline-none"
            style={{ touchAction: drawingMode || dragPreview ? "none" : "auto" }}
            onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerCancel={cancel}>
            <defs><clipPath id={clipId}><rect width={size.width} height={size.height} /></clipPath></defs>
            <g clipPath={`url(#${clipId})`}>
                {drawingMode && <rect width={size.width} height={size.height} fill="transparent" className="pointer-events-auto cursor-crosshair" />}
                {!hideAll && rendered.filter((drawing) => !drawing.hidden).map((drawing) => {
                    const shapes = drawingGeometry(drawing, context)
                    return <g key={drawing.id} opacity={selectedId && selectedId !== drawing.id ? .7 : 1}>
                        <g className="pointer-events-none">{shapes.map((shape, index) => <Shape key={index} drawing={drawing} shape={shape} />)}</g>
                        {mode === "select" && <g className={drawing.locked ? "pointer-events-auto cursor-pointer" : "pointer-events-auto cursor-move"}
                            aria-label={`${toolDefinition(drawing.tool).name}${drawing.locked ? ", kilitli" : ""}`} role="button" tabIndex={0}
                            onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelectedId(drawing.id); props.onOpenChange(true) } }}
                            onPointerDown={(event) => beginDrag(event, drawing, null)} onDoubleClick={() => { setSelectedId(drawing.id); props.onOpenChange(true) }}>
                            {shapes.map((shape, index) => <Shape key={index} drawing={drawing} shape={shape} hit />)}
                        </g>}
                        {mode === "select" && selectedId === drawing.id && !drawing.locked && drawing.points.map((anchor, index) => {
                            // Freehand has at most two visible handles; moving the line still moves every point.
                            if (drawing.points.length > 3 && index !== 0 && index !== drawing.points.length - 1) return null
                            const point = project(anchor)
                            return point && <circle key={index} cx={point.x} cy={point.y} r={5} fill="#0f172a" stroke={drawing.style.color} strokeWidth={2}
                                className="pointer-events-auto cursor-grab" onPointerDown={(event) => beginDrag(event, drawing, index)} />
                        })}
                    </g>
                })}
                {preview && <g opacity={.75}>{drawingGeometry(preview, context).map((shape, index) => <Shape key={index} drawing={preview} shape={shape} />)}</g>}
                {draft.map((anchor, index) => { const p = project(anchor); return p && <circle key={index} cx={p.x} cy={p.y} r={3} fill={style.color} /> })}
            </g>
        </svg>

        {(drawingMode || selected) && !props.open && <div className="pointer-events-auto absolute right-2 top-2 flex max-w-[min(26rem,calc(100%-1rem))] items-center gap-2 rounded-lg border border-border bg-card/95 p-2 shadow-lg backdrop-blur">
            <div className="min-w-0 text-xs text-foreground"><strong>{definition?.name ?? (selected ? toolDefinition(selected.tool).name : "")}</strong>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{definition ? `${definition.hint} ${definition.points > 1 ? `(${draft.length}/${definition.points})` : ""}` : selected?.locked ? "Kilitli çizim. Düzenlemek için kilidi açın." : "Çizgiyi veya tutamaçları sürükleyin."}</p></div>
            {!drawingMode && <button className={button} onClick={() => props.onOpenChange(true)} aria-label="Seçili çizimi düzenle"><Pencil size={14} /></button>}
            <button className={button} onClick={() => { cancel(); setSelectedId(null) }} aria-label="Çizim seçimini kapat"><X size={14} /></button>
        </div>}

        {props.open && <section aria-label="Çizim araçları ve nesneler" className="pointer-events-auto absolute right-2 top-2 flex max-h-[calc(100%-1rem)] w-[min(360px,calc(100%-1rem))] flex-col overflow-hidden rounded-xl border border-border bg-card/98 shadow-2xl backdrop-blur">
            <header className="flex shrink-0 items-center justify-between border-b border-border px-3 py-2">
                <div><h3 className="text-sm font-semibold text-foreground">Çizim stüdyosu <span className="ml-1 text-xs font-normal text-muted-foreground">26 araç</span></h3><p className="text-[10px] text-muted-foreground">{props.symbol} · {props.timeframe} · {history.present.length}/80 çizim</p></div>
                <button className={button} onClick={() => props.onOpenChange(false)} aria-label="Çizim araçlarını kapat"><X size={16} /></button>
            </header>
            <div className="flex shrink-0 flex-wrap gap-0.5 border-b border-border p-1.5" role="toolbar" aria-label="Çizim işlemleri">
                <button className={cn(button, mode === "select" && "bg-primary/15 text-primary")} onClick={() => setTool("select")} title="Seç ve düzenle" aria-label="Seç ve düzenle"><MousePointer2 size={16} /></button>
                <button className={cn(button, mode === "pan" && "bg-primary/15 text-primary")} onClick={() => setTool("pan")} title="Grafiği kaydır" aria-label="Grafiği kaydır"><Hand size={16} /></button>
                <button className={button} disabled={!history.past.length} onClick={() => travel("undo")} title="Geri al (Ctrl Z)" aria-label="Çizimi geri al"><Undo2 size={16} /></button>
                <button className={button} disabled={!history.future.length} onClick={() => travel("redo")} title="Yinele (Ctrl Shift Z)" aria-label="Çizimi yinele"><Redo2 size={16} /></button>
                <button className={cn(button, snap && "bg-primary/15 text-primary")} aria-pressed={snap} onClick={() => setSnap(!snap)} title="Mumun en yakın OHLC fiyatına yapış" aria-label="Mum fiyatına mıknatıs"><Magnet size={16} /></button>
                <button className={button} aria-pressed={hideAll} onClick={() => setHideAll(!hideAll)} title="Tüm çizimleri gizle/göster" aria-label="Tüm çizimleri gizle veya göster">{hideAll ? <EyeOff size={16} /> : <Eye size={16} />}</button>
                <button className={cn(button, showObjects && "bg-primary/15 text-primary")} aria-pressed={showObjects} onClick={() => setShowObjects(!showObjects)} title="Nesne listesi" aria-label="Çizim nesneleri"><Layers size={16} /></button>
            </div>
            <div className="min-h-0 overflow-y-auto overscroll-contain p-3">
                {selected && <div className="mb-3 rounded-lg border border-primary/30 bg-primary/5 p-2">
                    <div className="mb-2 flex items-center gap-1 text-xs text-foreground"><strong className="mr-auto">{toolDefinition(selected.tool).name}</strong>
                        <button className={button} aria-label={selected.locked ? "Çizim kilidini aç" : "Çizimi kilitle"} onClick={() => commit(historyRef.current.present.map((d) => d.id === selected.id ? { ...d, locked: !d.locked } : d))}>{selected.locked ? <Lock size={14} /> : <Unlock size={14} />}</button>
                        <button className={button} disabled={selected.locked || history.present.length >= MAX_DRAWINGS} aria-label="Çizimi çoğalt" onClick={() => {
                            const copy = { ...selected, id: uid(), points: selected.points.map((p) => ({ ...p, time: logicalToTime(timeToLogical(p.time, times, step) + 2, times, step) })) }
                            commit([...historyRef.current.present, copy]); setSelectedId(copy.id)
                        }}><Copy size={14} /></button>
                        <button className={cn(button, "hover:text-red-400")} disabled={selected.locked} aria-label="Seçili çizimi sil" onClick={removeSelected}><Trash2 size={14} /></button>
                    </div>
                    {selected.tool === "text" && <label className="mb-2 block text-xs text-muted-foreground">Not metni<input className={cn(input, "mt-1 w-full")} maxLength={180} value={selected.text} disabled={selected.locked} onChange={(event) => updateSelected({ text: event.target.value })} /></label>}
                    {selected.locked && <p className="text-[11px] text-muted-foreground">Kilit açıkken taşıma, düzenleme ve silme yapılabilir.</p>}
                </div>}
                <fieldset disabled={selected?.locked} className="mb-3 flex flex-wrap items-end gap-2">
                    <legend className="mb-1 text-[11px] text-muted-foreground">{selected ? "Çizim görünümü" : "Yeni çizim görünümü"}</legend>
                    <label className="text-[10px] text-muted-foreground">Renk<input className="mt-1 block h-8 w-9 cursor-pointer rounded border border-border bg-background p-0.5" type="color" value={currentStyle.color} onChange={(e) => changeStyle({ color: e.target.value })} /></label>
                    <label className="text-[10px] text-muted-foreground">Kalınlık<select className={cn(input, "mt-1 block")} value={currentStyle.width} onChange={(e) => changeStyle({ width: Number(e.target.value) })}>{[1, 2, 3, 4, 5].map((v) => <option key={v} value={v}>{v} px</option>)}</select></label>
                    <label className="text-[10px] text-muted-foreground">Dolgu<select className={cn(input, "mt-1 block")} value={currentStyle.fill} onChange={(e) => changeStyle({ fill: Number(e.target.value) })}>{[0, .12, .25, .5].map((v) => <option key={v} value={v}>%{v * 100}</option>)}</select></label>
                    <label className="flex h-8 items-center gap-1 text-xs text-muted-foreground"><input type="checkbox" checked={currentStyle.dashed} onChange={(e) => changeStyle({ dashed: e.target.checked })} />Kesikli</label>
                </fieldset>
                {showObjects ? <div className="space-y-1">
                    <p className="mb-2 text-xs text-muted-foreground">{history.present.length ? "Bir çizimi seçin; görünürlüğünü ve kilidini buradan yönetin." : "Henüz çizim yok. Araç listesinden başlayın."}</p>
                    {history.present.map((drawing, index) => <div key={drawing.id} className={cn("flex items-center rounded-md border border-border/50", selectedId === drawing.id && "border-primary/60 bg-primary/10")}>
                        <button className="min-w-0 flex-1 truncate px-2 py-2 text-left text-xs text-foreground" onClick={() => { cancel(); setSelectedId(drawing.id) }}><span style={{ color: drawing.style.color }}>●</span> {index + 1}. {toolDefinition(drawing.tool).name}{drawing.text && ` · ${drawing.text}`}</button>
                        <button className={button} aria-label={`${index + 1}. çizimi ${drawing.hidden ? "göster" : "gizle"}`} onClick={() => commit(historyRef.current.present.map((d) => d.id === drawing.id ? { ...d, hidden: !d.hidden } : d))}>{drawing.hidden ? <EyeOff size={13} /> : <Eye size={13} />}</button>
                        <button className={button} aria-label={`${index + 1}. çizimin kilidini ${drawing.locked ? "aç" : "kapat"}`} onClick={() => commit(historyRef.current.present.map((d) => d.id === drawing.id ? { ...d, locked: !d.locked } : d))}>{drawing.locked ? <Lock size={13} /> : <Unlock size={13} />}</button>
                    </div>)}
                    {!!history.present.length && <button className={cn(button, "mt-2 w-full text-red-400")} onClick={() => {
                        if (!clearConfirm) { setClearConfirm(true); return }
                        commit(historyRef.current.present.filter((d) => d.locked)); setSelectedId(null); setClearConfirm(false)
                    }}><Trash2 size={13} />{clearConfirm ? "Onayla: kilitsiz çizimleri sil" : "Kilitsiz çizimleri temizle"}</button>}
                </div> : <>
                    <label className="sr-only" htmlFor={`${clipId}-search`}>Çizim aracı ara</label>
                    <input id={`${clipId}-search`} className={cn(input, "mb-3 w-full")} placeholder="Araç ara: Fibonacci, kanal…" value={query} onChange={(e) => setQuery(e.target.value)} />
                    {groups.map((group) => {
                        const tools = DRAWING_TOOLS.filter((tool) => tool.group === group && tool.name.toLocaleLowerCase("tr").includes(query.toLocaleLowerCase("tr")))
                        return tools.length ? <div key={group} className="mb-3"><h4 className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{group}</h4><div className="grid grid-cols-2 gap-1">{tools.map((tool) => <button key={tool.id} className="flex min-h-9 items-center gap-1.5 rounded-md border border-border/50 px-2 py-1.5 text-left text-xs text-foreground hover:border-primary/50 hover:bg-primary/10 focus-visible:outline-2 focus-visible:outline-primary" title={tool.hint} onClick={() => setTool(tool.id)}><span className="min-w-0 flex-1">{tool.name}</span>{mode === tool.id ? <Check size={12} /> : <ChevronDown className="-rotate-90 opacity-40" size={12} />}</button>)}</div></div> : null
                    })}
                </>}
                <p className="mt-3 text-[10px] leading-relaxed text-muted-foreground">Çizimler bu tarayıcıda, sembol ve periyoda göre saklanır. Ctrl Z: geri al · Ctrl Shift Z: yinele · Delete: sil · Escape: iptal. Mıknatıs, mevcut mumun en yakın açılış/yüksek/düşük/kapanışına yapışır. Gelecek zaman uzantısı görsel tahmindir; seans takvimi değildir. Pozisyon araçları emir veya alarm çalıştırmaz.</p>
            </div>
        </section>}
        {notice && <div role="status" className="pointer-events-auto absolute bottom-2 left-2 right-2 flex items-center gap-2 rounded-lg border border-amber-500/30 bg-card p-2 text-xs text-amber-300"><p className="flex-1">{notice}</p><button className={button} onClick={() => setNotice(null)} aria-label="Çizim bildirimini kapat"><X size={14} /></button></div>}
    </div>
}
