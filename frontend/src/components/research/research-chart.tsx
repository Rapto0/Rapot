"use client"

import { useEffect, useRef, useState } from "react"
import { Pause, Play, RotateCcw, StepForward } from "lucide-react"
import type { IChartApi, ISeriesApi, UTCTimestamp } from "lightweight-charts"
import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import type { ResearchCandle } from "@/lib/api/borsapy-api"
import { createChartTimeFormatters } from "@/lib/chart-time"
import { formatResearchValue, researchDate, validResearchCandles } from "./research-utils"

const researchTime = createChartTimeFormatters("Europe/Istanbul")

export function ResearchChart({ candles }: { candles: ResearchCandle[] }) {
    const element = useRef<HTMLDivElement>(null)
    const chart = useRef<IChartApi | null>(null)
    const series = useRef<ISeriesApi<"Candlestick"> | null>(null)
    const current = useRef(candles)
    const fitted = useRef(false)
    const [error, setError] = useState(false)
    useEffect(() => {
        current.current = candles
        if (series.current) {
            series.current.setData(candles.map(candle => ({ ...candle, time: candle.time as UTCTimestamp })))
            if (candles.length && !fitted.current) { chart.current?.timeScale().fitContent(); fitted.current = true }
        }
    }, [candles])
    useEffect(() => {
        let disposed = false
        let observer: ResizeObserver | undefined
        import("lightweight-charts").then(({ createChart, CandlestickSeries, ColorType }) => {
            if (disposed || !element.current) return
            chart.current = createChart(element.current, {
                width: element.current.clientWidth, height: 330,
                layout: { background: { type: ColorType.Solid, color: "#101218" }, textColor: "#9ca3af", attributionLogo: true },
                grid: { vertLines: { color: "#20242e" }, horzLines: { color: "#20242e" } },
                rightPriceScale: { borderColor: "#303540" },
                timeScale: { borderColor: "#303540", timeVisible: true, secondsVisible: false, tickMarkFormatter: researchTime.tickMarkFormatter },
                localization: { locale: "tr-TR", timeFormatter: researchTime.timeFormatter },
            })
            series.current = chart.current.addSeries(CandlestickSeries, { upColor: "#22c55e", downColor: "#ef4444", borderVisible: false, wickUpColor: "#22c55e", wickDownColor: "#ef4444" })
            series.current.setData(current.current.map(candle => ({ ...candle, time: candle.time as UTCTimestamp })))
            if (current.current.length) { chart.current.timeScale().fitContent(); fitted.current = true }
            observer = new ResizeObserver(entries => { const width = entries[0]?.contentRect.width; if (width) chart.current?.applyOptions({ width }) })
            observer.observe(element.current)
        }).catch(() => { if (!disposed) setError(true) })
        return () => { disposed = true; observer?.disconnect(); chart.current?.remove(); chart.current = null; series.current = null; fitted.current = false }
    }, [])
    const last = candles.at(-1)
    return <section className="min-w-0 overflow-hidden border border-border bg-surface" aria-label="Araştırma mum grafiği">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border p-3 text-xs"><span className="font-medium">{candles.length.toLocaleString("tr-TR")} mum</span>{last && <span className="font-mono text-muted-foreground">A {formatResearchValue(last.open)} · Y {formatResearchValue(last.high)} · D {formatResearchValue(last.low)} · K {formatResearchValue(last.close)}</span>}</div>
        {error ? <p role="alert" className="p-4 text-sm text-loss">Grafik yüklenemedi. Alınan kayıtları tablodan inceleyebilirsiniz.</p> : <div ref={element} className="h-[330px] w-full" />}
        <p className="border-t border-border px-3 py-2 text-xs text-muted-foreground">{researchTime.label} · Son gösterilen mum: {researchDate(last?.time)}. Açık mumun değerleri değişebilir.</p>
    </section>
}

export function CandleView({ candles, replay = false }: { candles: ResearchCandle[]; replay?: boolean }) {
    const valid = validResearchCandles(candles)
    const [cursor, setCursor] = useState(1)
    const [playing, setPlaying] = useState(false)
    const [speed, setSpeed] = useState(1)
    const count = Math.min(cursor, valid.length)
    useEffect(() => {
        if (!playing || !replay) return
        const timer = setInterval(() => setCursor(value => {
            if (value >= valid.length) return value
            return value + 1
        }), 1000 / speed)
        return () => clearInterval(timer)
    }, [playing, replay, speed, valid.length])
    const atEnd = count >= valid.length
    const displayed = replay ? valid.slice(0, count) : valid
    return <div className="space-y-3">
        {candles.length !== valid.length && <p role="status" className="text-xs text-amber-300">Grafikte geçersiz veya yinelenen {candles.length - valid.length} kayıt gösterilmedi.</p>}
        {replay && <section className="space-y-3 border border-border bg-surface p-4" aria-label="Mum oynatma kontrolleri">
            <div className="flex flex-wrap items-center gap-2"><Button className="min-h-11" disabled={!valid.length} onClick={() => { if (atEnd) setCursor(1); setPlaying(!playing || atEnd) }}>{playing && !atEnd ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}{playing && !atEnd ? "Duraklat" : "Oynat"}</Button><Button className="min-h-11" variant="outline" disabled={atEnd} onClick={() => { setPlaying(false); setCursor(value => Math.min(valid.length, value + 1)) }}><StepForward aria-hidden="true" />Bir mum</Button><Button className="min-h-11" variant="ghost" onClick={() => { setPlaying(false); setCursor(1) }}><RotateCcw aria-hidden="true" />Başa dön</Button><label className="flex items-center gap-2 text-xs">Hız<Select className="min-h-11 w-24" value={speed} onChange={event => setSpeed(Number(event.target.value))}>{[0.5, 1, 2, 5, 10].map(value => <option value={value} key={value}>{value}×</option>)}</Select></label><span className="ml-auto text-xs text-muted-foreground">{count} / {valid.length} mum{atEnd && valid.length > 0 ? " · Tamamlandı" : ""}</span></div>
            <input className="w-full accent-emerald-500" type="range" min={1} max={Math.max(1, valid.length)} value={Math.max(1, count)} aria-label="Gösterilen mum sayısı" onChange={event => { setPlaying(false); setCursor(Number(event.target.value)) }} />
            <p className="text-xs text-muted-foreground">Geçmiş mumları bu sayfada adım adım izlersiniz. Oynatma yeni alarm veya işlem oluşturmaz.</p>
        </section>}
        {valid.length ? <ResearchChart candles={displayed} /> : <p className="border border-border p-5 text-sm text-muted-foreground">Gösterilecek geçerli mum bulunamadı.</p>}
    </div>
}
