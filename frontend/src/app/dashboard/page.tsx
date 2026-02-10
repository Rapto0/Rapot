'use client'

import { useMemo, useState } from 'react'
import { AdvancedChartPage } from '@/components/charts/advanced-chart'
import { useDashboardKPIs } from '@/lib/hooks/use-dashboard'
import { useRecentSignals } from '@/lib/hooks/use-signals'
import { cn } from '@/lib/utils'

type MarketType = 'BIST' | 'Kripto'

export default function DashboardPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('THYAO')
  const [selectedMarket, setSelectedMarket] = useState<MarketType>('BIST')
  const { data: kpis } = useDashboardKPIs()
  const { data: recentSignals } = useRecentSignals(12)

  const pnlLabel = useMemo(() => {
    if (!kpis) return '--'
    return `${kpis.totalPnL >= 0 ? '+' : ''}${kpis.totalPnL.toLocaleString('tr-TR', { maximumFractionDigits: 2 })} ₺`
  }, [kpis])

  return (
    <div className="flex h-[calc(100vh-40px)] flex-col gap-2 p-2 md:gap-3 md:p-3">
      <section className="grid h-16 shrink-0 grid-cols-2 border border-border bg-surface md:grid-cols-5">
        <RibbonStat label="Toplam PNL" value={pnlLabel} tone={kpis && kpis.totalPnL < 0 ? 'loss' : 'profit'} />
        <RibbonStat
          label="Win Rate"
          value={typeof kpis?.winRate === 'number' ? `${kpis.winRate.toFixed(2)}%` : '--'}
        />
        <RibbonStat label="Açık Pozisyon" value={typeof kpis?.openPositions === 'number' ? `${kpis.openPositions}` : '--'} />
        <RibbonStat label="Toplam İşlem" value={typeof kpis?.totalTrades === 'number' ? `${kpis.totalTrades}` : '--'} />
        <RibbonStat label="Toplam Sinyal" value={typeof kpis?.totalSignals === 'number' ? `${kpis.totalSignals}` : '--'} />
      </section>

      <section className="min-h-0 flex-1 border border-border bg-surface">
        <AdvancedChartPage
          initialSymbol={selectedSymbol}
          initialMarket={selectedMarket}
          showSignals={false}
          showWatchlist={true}
        />
      </section>

      <section className="h-40 border border-border bg-surface">
        <div className="flex h-8 items-center justify-between border-b border-border px-3">
          <span className="label-uppercase">Sinyal Akışı</span>
          <span className="text-[10px] text-muted-foreground">Son 12 kayıt</span>
        </div>

        <div className="h-[calc(100%-32px)] overflow-y-auto">
          {(recentSignals ?? []).length === 0 ? (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">Sinyal verisi bulunamadı.</div>
          ) : (
            (recentSignals ?? []).map((signal) => (
              <button
                key={signal.id}
                type="button"
                onClick={() => {
                  setSelectedSymbol(signal.symbol)
                  setSelectedMarket(signal.marketType)
                }}
                className="grid w-full grid-cols-[64px_1fr_100px_52px] items-center gap-2 border-b border-[rgba(255,255,255,0.02)] px-3 py-1.5 text-left hover:bg-raised"
              >
                <span
                  className={cn(
                    'inline-flex w-fit items-center border px-1.5 py-0.5 text-[10px] font-semibold tracking-[0.06em]',
                    signal.signalType === 'AL'
                      ? 'border-profit bg-profit/10 text-profit'
                      : 'border-loss bg-loss/10 text-loss'
                  )}
                >
                  {signal.signalType}
                </span>
                <div className="min-w-0">
                  <div className="truncate text-xs font-medium text-foreground">{signal.symbol}</div>
                  <div className="truncate text-[10px] text-muted-foreground">{signal.strategy} • {signal.timeframe}</div>
                </div>
                <div className="mono-numbers text-right text-xs text-foreground">
                  {signal.marketType === 'Kripto' ? '$' : '₺'}
                  {signal.price.toLocaleString('tr-TR', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: signal.marketType === 'Kripto' ? 4 : 2,
                  })}
                </div>
                <div className="mono-numbers text-right text-[10px] text-muted-foreground">
                  {new Date(signal.createdAt).toLocaleTimeString('tr-TR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </button>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

function RibbonStat({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: 'profit' | 'loss'
}) {
  return (
    <div className="flex min-w-0 flex-col justify-center gap-1 border-r border-border px-3 last:border-r-0">
      <span className="label-uppercase">{label}</span>
      <span className={cn('mono-numbers truncate text-lg font-semibold', tone === 'profit' && 'text-profit', tone === 'loss' && 'text-loss')}>
        {value}
      </span>
    </div>
  )
}
