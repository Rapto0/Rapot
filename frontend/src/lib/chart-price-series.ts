import type { CandlestickData, ISeriesApi, ITimeScaleApi, Time } from "lightweight-charts"

export type PriceBar = CandlestickData<Time>

function sameBar(left: PriceBar, right: PriceBar) {
    return left.time === right.time && left.open === right.open && left.high === right.high &&
        left.low === right.low && left.close === right.close
}

export function paintPriceBars(
    series: ISeriesApi<"Candlestick">,
    scale: ITimeScaleApi<Time>,
    previous: PriceBar[],
    next: PriceBar[],
    sameSelection: boolean,
) {
    if (sameSelection && previous.length > 0 && next.length >= previous.length) {
        let changed = 0
        while (changed < previous.length && sameBar(previous[changed], next[changed])) changed++
        if (changed === previous.length ||
            (changed === previous.length - 1 && previous[changed].time === next[changed].time)) {
            for (let index = changed; index < next.length; index++) series.update(next[index])
            return
        }
    }
    if (sameSelection && !previous.length && !next.length) return
    const visible = sameSelection && previous.length ? scale.getVisibleRange() : null
    series.setData(next)
    if (!next.length) return
    if (visible) scale.setVisibleRange(visible)
    else scale.fitContent()
}
