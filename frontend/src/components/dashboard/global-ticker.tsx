'use client';

import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { TrendingUp, TrendingDown, Minus, Wifi, WifiOff } from 'lucide-react';
import { useRealtime, useTickerData, useAnimatedNumber } from '@/lib/hooks/use-realtime';
import { cn } from '@/lib/utils';

// ==================== TYPES ====================

interface TickerItem {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  market: 'crypto' | 'bist';
  flash?: 'up' | 'down' | null;
}

// ==================== ANIMATED PRICE ====================

function AnimatedPrice({ value, decimals = 2 }: { value: number; decimals?: number }) {
  const { displayValue, direction } = useAnimatedNumber(value);

  return (
    <span
      className={cn(
        'mono-numbers transition-colors duration-300',
        direction === 'up' && 'text-profit',
        direction === 'down' && 'text-loss'
      )}
    >
      {displayValue.toLocaleString('tr-TR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
    </span>
  );
}

// ==================== TICKER ITEM ====================

function TickerItemComponent({ item }: { item: TickerItem }) {
  const [isFlashing, setIsFlashing] = useState(false);
  const prevPrice = useRef(item.price);

  useEffect(() => {
    if (item.price !== prevPrice.current) {
      setIsFlashing(true);
      prevPrice.current = item.price;
      const timeout = setTimeout(() => setIsFlashing(false), 500);
      return () => clearTimeout(timeout);
    }
  }, [item.price]);

  const isPositive = item.changePercent >= 0;
  const Icon = isPositive ? TrendingUp : TrendingDown;

  // Determine decimal places based on price magnitude
  const decimals = item.price < 1 ? 6 : item.price < 100 ? 4 : 2;

  return (
    <div
      className={cn(
        'inline-flex items-center gap-3 px-4 py-2 mx-2 rounded-lg transition-all duration-300',
        'bg-card/30 border border-border/50 hover:border-primary/30',
        isFlashing && isPositive && 'flash-profit',
        isFlashing && !isPositive && 'flash-loss'
      )}
    >
      {/* Market indicator */}
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          item.market === 'crypto' ? 'bg-secondary' : 'bg-primary'
        )}
      />

      {/* Symbol */}
      <div className="flex flex-col">
        <span className="text-sm font-semibold text-foreground">
          {item.name}
        </span>
        <span className="text-xs text-muted-foreground">
          {item.market === 'crypto' ? 'Kripto' : 'BIST'}
        </span>
      </div>

      {/* Price */}
      <div className="flex flex-col items-end min-w-[80px]">
        <span className="text-sm font-bold mono-numbers">
          <AnimatedPrice value={item.price} decimals={decimals} />
        </span>
        <div
          className={cn(
            'flex items-center gap-1 text-xs font-medium',
            isPositive ? 'text-profit' : 'text-loss'
          )}
        >
          <Icon className="w-3 h-3" />
          <span className="mono-numbers">
            {isPositive ? '+' : ''}
            {item.changePercent.toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ==================== GLOBAL TICKER ====================

export function GlobalTicker() {
  const { connectionState } = useRealtime();
  const { combinedTickers } = useTickerData();
  const [isPaused, setIsPaused] = useState(false);

  // Double the items for seamless loop
  const tickerItems = useMemo(() => {
    if (combinedTickers.length === 0) {
      // Placeholder data while loading
      return Array(10).fill(null).map((_, i) => ({
        symbol: `LOADING${i}`,
        name: '---',
        price: 0,
        change: 0,
        changePercent: 0,
        market: 'crypto' as const,
        flash: null,
      }));
    }
    return [...combinedTickers, ...combinedTickers];
  }, [combinedTickers]);

  const isConnected = connectionState === 'connected';

  return (
    <div
      className="relative w-full overflow-hidden bg-background-secondary/80 backdrop-blur-xl border-b border-border/50"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Connection status indicator */}
      <div className="absolute left-0 top-0 bottom-0 z-10 flex items-center px-3 bg-gradient-to-r from-background to-transparent">
        <div
          className={cn(
            'flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium',
            isConnected
              ? 'bg-profit/10 text-profit'
              : 'bg-loss/10 text-loss'
          )}
        >
          {isConnected ? (
            <>
              <Wifi className="w-3 h-3" />
              <span className="hidden sm:inline">Canlı</span>
              <span className="w-2 h-2 rounded-full bg-profit animate-pulse" />
            </>
          ) : (
            <>
              <WifiOff className="w-3 h-3" />
              <span className="hidden sm:inline">Bağlantı Yok</span>
            </>
          )}
        </div>
      </div>

      {/* Fade edges */}
      <div className="absolute left-16 top-0 bottom-0 w-16 bg-gradient-to-r from-background to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-background to-transparent z-10 pointer-events-none" />

      {/* Ticker tape */}
      <div
        className={cn(
          'flex whitespace-nowrap py-2 pl-24',
          !isPaused && 'animate-ticker'
        )}
        style={{
          animationDuration: `${Math.max(tickerItems.length * 3, 30)}s`,
        }}
      >
        {tickerItems.map((item, index) => (
          <TickerItemComponent
            key={`${item.symbol}-${index}`}
            item={item}
          />
        ))}
      </div>
    </div>
  );
}

// ==================== MINI TICKER (for sidebar) ====================

interface MiniTickerProps {
  symbols?: string[];
  className?: string;
}

export function MiniTicker({ symbols, className }: MiniTickerProps) {
  const { combinedTickers } = useTickerData(symbols);

  const displayTickers = useMemo(() => {
    return combinedTickers.slice(0, 5);
  }, [combinedTickers]);

  return (
    <div className={cn('space-y-2', className)}>
      {displayTickers.map((item) => {
        const isPositive = item.changePercent >= 0;
        return (
          <div
            key={item.symbol}
            className={cn(
              'flex items-center justify-between px-3 py-2 rounded-lg',
              'bg-card/50 border border-border/30 transition-all',
              item.flash === 'up' && 'flash-profit',
              item.flash === 'down' && 'flash-loss'
            )}
          >
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'w-1.5 h-1.5 rounded-full',
                  item.market === 'crypto' ? 'bg-secondary' : 'bg-primary'
                )}
              />
              <span className="text-sm font-medium">{item.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold mono-numbers">
                {item.price.toLocaleString('tr-TR', { maximumFractionDigits: 2 })}
              </span>
              <span
                className={cn(
                  'text-xs font-medium mono-numbers',
                  isPositive ? 'text-profit' : 'text-loss'
                )}
              >
                {isPositive ? '+' : ''}
                {item.changePercent.toFixed(2)}%
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ==================== PRICE BADGE ====================

interface PriceBadgeProps {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  size?: 'sm' | 'md' | 'lg';
}

export function PriceBadge({
  symbol,
  price,
  change,
  changePercent,
  size = 'md',
}: PriceBadgeProps) {
  const isPositive = changePercent >= 0;
  const Icon = changePercent === 0 ? Minus : isPositive ? TrendingUp : TrendingDown;

  const sizeClasses = {
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5',
    lg: 'text-base px-4 py-2',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 rounded-lg bg-card border border-border',
        sizeClasses[size]
      )}
    >
      <span className="font-semibold">{symbol}</span>
      <span className="mono-numbers font-bold">
        {price.toLocaleString('tr-TR', { maximumFractionDigits: 2 })}
      </span>
      <div
        className={cn(
          'flex items-center gap-0.5',
          isPositive ? 'text-profit' : changePercent === 0 ? 'text-neutral' : 'text-loss'
        )}
      >
        <Icon className={cn(size === 'sm' ? 'w-3 h-3' : 'w-4 h-4')} />
        <span className="mono-numbers font-medium">
          {isPositive ? '+' : ''}
          {changePercent.toFixed(2)}%
        </span>
      </div>
    </div>
  );
}

export default GlobalTicker;
