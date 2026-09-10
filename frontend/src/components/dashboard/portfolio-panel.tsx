'use client';

import React, { useState, useMemo } from 'react';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  RefreshCcw,
  Eye,
  EyeOff,
  BarChart3,
  DollarSign,
  Percent,
  Zap,
} from 'lucide-react';
import { useTrades, useTradeStats } from '@/lib/hooks';
import { cn } from '@/lib/utils';
import { formatMetric, formatMetricPercent, formatTradePrice, metricTextClass, metricTone } from '@/lib/metric-display';

// ==================== TYPES ====================

interface Position {
  symbol: string;
  marketType: string;
  quantity: number | null;
  avgPrice: number | null;
  currentPrice: number | null;
  pnl: number | null;
  pnlPercent: number | null;
}

// ==================== QUICK TRADE BUTTONS ====================

function QuickTradeButtons() {
  return (
    <div className="flex flex-col gap-3 p-4 rounded-lg bg-card/30 border border-border/30">
      <span className="text-sm font-medium">Hızlı İşlem</span>
      <p className="text-xs text-muted-foreground">İşlem gönderimi bağlı değil.</p>
      <div className="grid grid-cols-2 gap-2">
        <button type="button" disabled className="btn-profit py-3 opacity-50 cursor-not-allowed">AL</button>
        <button type="button" disabled className="btn-loss py-3 opacity-50 cursor-not-allowed">SAT</button>
      </div>
    </div>
  );
}

// ==================== POSITION CARD ====================

interface PositionCardProps {
  position: Position;
}

function PositionCard({ position }: PositionCardProps) {
  const tone = metricTone(position.pnl);
  const percentTone = metricTone(position.pnlPercent);

  return (
    <div className="flex items-center gap-4 p-3 rounded-lg bg-card/30 border border-border/20 hover:border-primary/20 transition-colors">
      {/* Symbol */}
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-bold">{position.symbol}</span>
          <span className="text-xs px-1.5 py-0.5 rounded bg-muted/30 text-muted-foreground">
            {position.marketType}
          </span>
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">
          {formatMetric(position.quantity, 4)} adet @ {formatTradePrice(position.avgPrice, position.marketType)}
        </div>
      </div>

      {/* Current Price */}
      <div className="text-right">
        <div className="mono-numbers font-medium">
          {formatTradePrice(position.currentPrice, position.marketType)}
        </div>
        <div className={cn(
          'flex items-center justify-end gap-1 text-xs',
          metricTextClass(position.pnlPercent)
        )}>
          {percentTone === 'profit' ? <TrendingUp className="w-3 h-3" /> : percentTone === 'loss' ? <TrendingDown className="w-3 h-3" /> : null}
          <span className="mono-numbers">
            {formatMetricPercent(position.pnlPercent, 2, true)}
          </span>
        </div>
      </div>

      {/* PnL */}
      <div className={cn(
        'text-right min-w-[80px] px-3 py-2 rounded-lg',
        tone === 'profit' ? 'bg-profit/10' : tone === 'loss' ? 'bg-loss/10' : 'bg-muted/10'
      )}>
        <div className={cn(
          'font-bold mono-numbers',
          metricTextClass(position.pnl)
        )}>
          {position.pnl === null ? '—' : `${position.pnl >= 0 ? '+' : ''}${formatTradePrice(position.pnl, position.marketType)}`}
        </div>
      </div>

      <button
        type="button"
        disabled
        className="p-2 rounded-lg bg-muted/30 opacity-50 cursor-not-allowed"
        title="Pozisyonu Kapat — işlem gönderimi bağlı değil"
        aria-label="Pozisyonu Kapat"
      >
        <RefreshCcw className="w-4 h-4" />
      </button>
    </div>
  );
}

// ==================== STATS CARD ====================

interface StatCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

function StatCard({ label, value, subValue, icon, trend, className }: StatCardProps) {
  return (
    <div className={cn(
      'flex flex-col p-4 rounded-lg bg-card/30 border border-border/20',
      className
    )}>
      <div className="flex items-center justify-between mb-2">
        <span className="data-label">{label}</span>
        <span className="text-muted-foreground">{icon}</span>
      </div>
      <div className={cn(
        'data-value',
        trend === 'up' && 'text-profit',
        trend === 'down' && 'text-loss'
      )}>
        {value}
      </div>
      {subValue && (
        <div className="text-xs text-muted-foreground mt-1">{subValue}</div>
      )}
    </div>
  );
}

// ==================== PORTFOLIO PANEL ====================

interface PortfolioPanelProps {
  selectedSymbol?: string;
  selectedPrice?: number;
  className?: string;
}

export function PortfolioPanel({
  className,
}: PortfolioPanelProps) {
  const [hideBalance, setHideBalance] = useState(false);

  // Get trades and stats from API
  const { data: trades, isLoading, isError } = useTrades({ status: 'OPEN' });
  const { data: stats } = useTradeStats();

  // Calculate portfolio stats
  const portfolioStats = useMemo(() => {
    const totalPnl = stats?.totalPnL;
    const winRate = stats?.winRate;
    const openTrades = stats?.open;
    const totalTrades = stats?.total;

    return {
      totalPnl,
      winRate,
      openTrades,
      totalTrades,
      tone: metricTone(totalPnl),
    };
  }, [stats]);

  // Convert trades to positions
  const positions: Position[] = useMemo(() => {
    if (!trades) return [];

    return trades.map((trade) => ({
      symbol: trade.symbol,
      marketType: trade.marketType,
      quantity: trade.quantity,
      avgPrice: trade.entryPrice,
      currentPrice: trade.currentPrice,
      pnl: trade.pnl,
      pnlPercent: trade.pnlPercent,
    }));
  }, [trades]);


  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/30">
        <div className="flex items-center gap-2">
          <Wallet className="w-5 h-5 text-primary" />
          <span className="font-semibold">Portföy & İşlemler</span>
        </div>
        <button
          onClick={() => setHideBalance(!hideBalance)}
          className="p-1.5 rounded-lg hover:bg-muted/30 transition-colors"
          title={hideBalance ? 'Bakiyeyi Göster' : 'Bakiyeyi Gizle'}
        >
          {hideBalance ? (
            <EyeOff className="w-4 h-4 text-muted-foreground" />
          ) : (
            <Eye className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            label="Gerçekleşmiş PnL"
            value={hideBalance ? '****' : formatMetric(portfolioStats.totalPnl, 2, true)}
            subValue="Para birimi dönüşümü yapılmaz."
            icon={<DollarSign className="w-4 h-4" />}
            trend={portfolioStats.tone === 'profit' ? 'up' : portfolioStats.tone === 'loss' ? 'down' : 'neutral'}
          />
          <StatCard
            label="Kazanma Oranı"
            value={formatMetricPercent(portfolioStats.winRate, 1)}
            subValue={`${formatMetric(portfolioStats.totalTrades, 0)} işlem`}
            icon={<Percent className="w-4 h-4" />}
            trend={metricTone(portfolioStats.winRate, 50) === 'neutral' ? 'neutral' : (portfolioStats.winRate ?? 0) >= 50 ? 'up' : 'down'}
          />
          <StatCard
            label="Açık Pozisyon"
            value={formatMetric(portfolioStats.openTrades, 0)}
            icon={<BarChart3 className="w-4 h-4" />}
          />
          <StatCard
            label="Toplam İşlem"
            value={formatMetric(portfolioStats.totalTrades, 0)}
            icon={<Zap className="w-4 h-4" />}
          />
        </div>

        {/* Quick Trade */}
        <QuickTradeButtons />

        {/* Open Positions */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium">Açık Pozisyonlar</span>
            <span className="text-xs text-muted-foreground">
              {trades ? positions.length : '—'} pozisyon
            </span>
          </div>

          {isError ? (
            <p className="text-sm text-muted-foreground">Pozisyonlar yüklenemedi.</p>
          ) : isLoading || !trades ? (
            <p className="text-sm text-muted-foreground">Pozisyonlar yükleniyor...</p>
          ) : positions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Wallet className="w-8 h-8 mb-2 opacity-50" />
              <span className="text-sm">Açık pozisyon yok</span>
            </div>
          ) : (
            <div className="space-y-2">
              {positions.map((position) => (
                <PositionCard
                  key={position.symbol}
                  position={position}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-border/30 text-xs text-muted-foreground">
        <div className="flex items-center justify-between">
          <span>İşlem gönderimi bağlı değil.</span>
        </div>
      </div>
    </div>
  );
}

// ==================== MINI PORTFOLIO ====================

export function MiniPortfolio() {
  const { data: stats } = useTradeStats();

  const totalPnl = stats?.totalPnL;

  return (
    <div className="flex items-center gap-4 p-3 rounded-lg bg-card/30 border border-border/20">
      <Wallet className="w-5 h-5 text-primary" />
      <div className="flex-1">
        <div className="text-xs text-muted-foreground" title="Para birimi dönüşümü yapılmaz.">Gerçekleşmiş PnL</div>
        <div className={cn(
          'font-bold mono-numbers',
          metricTextClass(totalPnl)
        )}>
          {formatMetric(totalPnl, 2, true)}
        </div>
      </div>
      <div className="text-right">
        <div className="text-xs text-muted-foreground">Açık</div>
        <div className="font-medium">{formatMetric(stats?.open, 0)}</div>
      </div>
    </div>
  );
}

export default PortfolioPanel;
