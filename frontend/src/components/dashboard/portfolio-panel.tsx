'use client';

import React, { useState, useMemo } from 'react';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCcw,
  Eye,
  EyeOff,
  BarChart3,
  DollarSign,
  Percent,
  Zap,
  AlertTriangle,
} from 'lucide-react';
import { useTrades, useTradeStats } from '@/lib/hooks';
import { cn } from '@/lib/utils';

// ==================== TYPES ====================

interface Position {
  symbol: string;
  marketType: string;
  quantity: number;
  avgPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
}

// ==================== QUICK TRADE BUTTONS ====================

interface QuickTradeProps {
  symbol: string;
  currentPrice: number;
  onBuy: (symbol: string, amount: number) => void;
  onSell: (symbol: string, amount: number) => void;
  disabled?: boolean;
}

function QuickTradeButtons({ symbol, currentPrice, onBuy, onSell, disabled }: QuickTradeProps) {
  const [amount, setAmount] = useState('');
  const [mode, setMode] = useState<'paper' | 'real'>('paper');

  const handleBuy = () => {
    const qty = parseFloat(amount) || 0;
    if (qty > 0) {
      onBuy(symbol, qty);
      setAmount('');
    }
  };

  const handleSell = () => {
    const qty = parseFloat(amount) || 0;
    if (qty > 0) {
      onSell(symbol, qty);
      setAmount('');
    }
  };

  return (
    <div className="flex flex-col gap-3 p-4 rounded-lg bg-card/30 border border-border/30">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Hızlı İşlem</span>
        <div className="flex items-center gap-1 bg-muted/30 rounded-lg p-0.5">
          <button
            onClick={() => setMode('paper')}
            className={cn(
              'px-2 py-1 text-xs rounded-md transition-all',
              mode === 'paper'
                ? 'bg-primary/20 text-primary'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            Paper
          </button>
          <button
            onClick={() => setMode('real')}
            className={cn(
              'px-2 py-1 text-xs rounded-md transition-all',
              mode === 'real'
                ? 'bg-loss/20 text-loss'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            Gerçek
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="Miktar"
          className="flex-1 px-3 py-2 bg-background/50 border border-border/50 rounded-lg text-sm focus:outline-none focus:border-primary/50 mono-numbers"
        />
        <div className="text-xs text-muted-foreground">
          ≈ ${((parseFloat(amount) || 0) * currentPrice).toFixed(2)}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={handleBuy}
          disabled={disabled || !amount}
          className={cn(
            'btn-profit flex items-center justify-center gap-2 py-3',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <ArrowUpRight className="w-4 h-4" />
          <span>AL</span>
        </button>
        <button
          onClick={handleSell}
          disabled={disabled || !amount}
          className={cn(
            'btn-loss flex items-center justify-center gap-2 py-3',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <ArrowDownRight className="w-4 h-4" />
          <span>SAT</span>
        </button>
      </div>

      {mode === 'real' && (
        <div className="flex items-center gap-2 text-xs text-loss">
          <AlertTriangle className="w-3 h-3" />
          <span>Gerçek mod - Dikkatli olun!</span>
        </div>
      )}
    </div>
  );
}

// ==================== POSITION CARD ====================

interface PositionCardProps {
  position: Position;
  onClose?: (symbol: string) => void;
}

function PositionCard({ position, onClose }: PositionCardProps) {
  const isProfit = position.pnl >= 0;

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
          {position.quantity} adet @ ₺{position.avgPrice.toFixed(2)}
        </div>
      </div>

      {/* Current Price */}
      <div className="text-right">
        <div className="mono-numbers font-medium">
          ₺{position.currentPrice.toFixed(2)}
        </div>
        <div className={cn(
          'flex items-center justify-end gap-1 text-xs',
          isProfit ? 'text-profit' : 'text-loss'
        )}>
          {isProfit ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          <span className="mono-numbers">
            {isProfit ? '+' : ''}{position.pnlPercent.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* PnL */}
      <div className={cn(
        'text-right min-w-[80px] px-3 py-2 rounded-lg',
        isProfit ? 'bg-profit/10' : 'bg-loss/10'
      )}>
        <div className={cn(
          'font-bold mono-numbers',
          isProfit ? 'text-profit' : 'text-loss'
        )}>
          {isProfit ? '+' : ''}₺{position.pnl.toFixed(2)}
        </div>
      </div>

      {/* Close button */}
      {onClose && (
        <button
          onClick={() => onClose(position.symbol)}
          className="p-2 rounded-lg bg-muted/30 hover:bg-loss/20 hover:text-loss transition-colors"
          title="Pozisyonu Kapat"
        >
          <RefreshCcw className="w-4 h-4" />
        </button>
      )}
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
  selectedSymbol = 'BTCUSDT',
  selectedPrice = 0,
  className,
}: PortfolioPanelProps) {
  const [hideBalance, setHideBalance] = useState(false);

  // Get trades and stats from API
  const { data: trades } = useTrades({ status: 'OPEN' });
  const { data: stats } = useTradeStats();

  // Calculate portfolio stats
  const portfolioStats = useMemo(() => {
    const totalPnl = stats?.totalPnL || 0;
    const winRate = stats?.winRate || 0;
    const openTrades = stats?.open || 0;
    const totalTrades = stats?.total || 0;

    return {
      totalPnl,
      winRate,
      openTrades,
      totalTrades,
      isProfit: totalPnl >= 0,
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

  // Handlers
  const handleBuy = (symbol: string, amount: number) => {
    console.log('Buy', symbol, amount);
    // TODO: Implement actual buy logic
  };

  const handleSell = (symbol: string, amount: number) => {
    console.log('Sell', symbol, amount);
    // TODO: Implement actual sell logic
  };

  const handleClosePosition = (symbol: string) => {
    console.log('Close position', symbol);
    // TODO: Implement close position logic
  };

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
            label="Toplam PnL"
            value={hideBalance ? '****' : `${portfolioStats.isProfit ? '+' : ''}₺${portfolioStats.totalPnl.toFixed(2)}`}
            icon={<DollarSign className="w-4 h-4" />}
            trend={portfolioStats.isProfit ? 'up' : 'down'}
          />
          <StatCard
            label="Kazanma Oranı"
            value={`%${portfolioStats.winRate.toFixed(1)}`}
            subValue={`${portfolioStats.totalTrades} işlem`}
            icon={<Percent className="w-4 h-4" />}
            trend={portfolioStats.winRate >= 50 ? 'up' : 'down'}
          />
          <StatCard
            label="Açık Pozisyon"
            value={portfolioStats.openTrades}
            icon={<BarChart3 className="w-4 h-4" />}
          />
          <StatCard
            label="Toplam İşlem"
            value={portfolioStats.totalTrades}
            icon={<Zap className="w-4 h-4" />}
          />
        </div>

        {/* Quick Trade */}
        <QuickTradeButtons
          symbol={selectedSymbol}
          currentPrice={selectedPrice}
          onBuy={handleBuy}
          onSell={handleSell}
        />

        {/* Open Positions */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium">Açık Pozisyonlar</span>
            <span className="text-xs text-muted-foreground">
              {positions.length} pozisyon
            </span>
          </div>

          {positions.length === 0 ? (
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
                  onClose={handleClosePosition}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-border/30 text-xs text-muted-foreground">
        <div className="flex items-center justify-between">
          <span>Paper Trading Aktif</span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-profit animate-pulse" />
            Bağlı
          </span>
        </div>
      </div>
    </div>
  );
}

// ==================== MINI PORTFOLIO ====================

export function MiniPortfolio() {
  const { data: stats } = useTradeStats();

  const totalPnl = stats?.totalPnL || 0;
  const isProfit = totalPnl >= 0;

  return (
    <div className="flex items-center gap-4 p-3 rounded-lg bg-card/30 border border-border/20">
      <Wallet className="w-5 h-5 text-primary" />
      <div className="flex-1">
        <div className="text-xs text-muted-foreground">Toplam PnL</div>
        <div className={cn(
          'font-bold mono-numbers',
          isProfit ? 'text-profit' : 'text-loss'
        )}>
          {isProfit ? '+' : ''}₺{totalPnl.toFixed(2)}
        </div>
      </div>
      <div className="text-right">
        <div className="text-xs text-muted-foreground">Açık</div>
        <div className="font-medium">{stats?.open || 0}</div>
      </div>
    </div>
  );
}

export default PortfolioPanel;
