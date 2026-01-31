'use client';

import React, { useEffect, useRef, useState, useMemo } from 'react';
import {
  Zap,
  TrendingUp,
  TrendingDown,
  Clock,
  Target,
  Activity,
  Filter,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Bell,
  BellOff,
  Calendar,
} from 'lucide-react';
import { useRealtimeStore } from '@/lib/hooks/use-realtime';
import { useSignals } from '@/lib/hooks/use-signals';
import { cn } from '@/lib/utils';

// ==================== TYPES ====================

interface Signal {
  id: number;
  symbol: string;
  marketType: string;
  strategy: string;
  signalType: 'AL' | 'SAT';
  timeframe: string;
  score: string;
  price: number;
  createdAt: string;
}

// ==================== PAGINATION COMPONENT ====================

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (items: number) => void;
}

function Pagination({
  currentPage,
  totalPages,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange,
}: PaginationProps) {
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  // Generate page numbers to show
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible + 2) {
      // Show all pages
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      // Show first, last, and pages around current
      pages.push(1);

      if (currentPage > 3) {
        pages.push('...');
      }

      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      if (currentPage < totalPages - 2) {
        pages.push('...');
      }

      if (totalPages > 1) {
        pages.push(totalPages);
      }
    }

    return pages;
  };

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 border-t border-border/30 bg-muted/5">
      {/* Info */}
      <div className="text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{startItem} - {endItem}</span>
        <span className="mx-1">/</span>
        <span className="font-medium text-primary">{totalItems.toLocaleString('tr-TR')}</span>
        <span className="ml-1">toplam sinyal</span>
      </div>

      {/* Page buttons */}
      <div className="flex items-center gap-1">
        {/* First page */}
        <button
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className={cn(
            "p-1.5 rounded-md transition-colors",
            currentPage === 1
              ? "text-muted-foreground/40 cursor-not-allowed"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title="İlk Sayfa"
        >
          <ChevronsLeft className="w-4 h-4" />
        </button>

        {/* Previous page */}
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className={cn(
            "p-1.5 rounded-md transition-colors",
            currentPage === 1
              ? "text-muted-foreground/40 cursor-not-allowed"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title="Önceki Sayfa"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* Page numbers */}
        <div className="flex items-center gap-1 mx-2">
          {getPageNumbers().map((page, index) => (
            page === '...' ? (
              <span key={`ellipsis-${index}`} className="px-2 text-muted-foreground">...</span>
            ) : (
              <button
                key={page}
                onClick={() => onPageChange(page as number)}
                className={cn(
                  "min-w-[32px] h-8 px-2 rounded-md text-sm font-medium transition-colors",
                  currentPage === page
                    ? "bg-primary/20 text-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                )}
              >
                {page}
              </button>
            )
          ))}
        </div>

        {/* Next page */}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className={cn(
            "p-1.5 rounded-md transition-colors",
            currentPage === totalPages
              ? "text-muted-foreground/40 cursor-not-allowed"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title="Sonraki Sayfa"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        {/* Last page */}
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className={cn(
            "p-1.5 rounded-md transition-colors",
            currentPage === totalPages
              ? "text-muted-foreground/40 cursor-not-allowed"
              : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
          )}
          title="Son Sayfa"
        >
          <ChevronsRight className="w-4 h-4" />
        </button>
      </div>

      {/* Items per page */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-muted-foreground">Satır:</span>
        <select
          value={itemsPerPage}
          onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
          className="bg-background/50 border border-border/50 rounded-md px-2 py-1 text-sm focus:outline-none focus:border-primary/50"
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>
    </div>
  );
}

// ==================== SIGNAL CARD ====================

interface SignalCardProps {
  signal: Signal;
  isNew?: boolean;
  onSelect?: (signal: Signal) => void;
}

function SignalCard({ signal, isNew, onSelect }: SignalCardProps) {
  const isBuy = signal.signalType === 'AL';
  const Icon = isBuy ? TrendingUp : TrendingDown;

  // Parse time
  const time = new Date(signal.createdAt);
  const timeStr = time.toLocaleTimeString('tr-TR', {
    hour: '2-digit',
    minute: '2-digit',
  });
  const dateStr = time.toLocaleDateString('tr-TR', {
    day: '2-digit',
    month: '2-digit',
  });

  return (
    <div
      onClick={() => onSelect?.(signal)}
      className={cn(
        'group relative flex items-center gap-4 p-4 rounded-lg cursor-pointer transition-all',
        'bg-card/30 border border-border/30',
        'hover:bg-card/50 hover:border-primary/20',
        isNew && 'matrix-item animate-glow-pulse border-primary/30'
      )}
    >
      {/* Signal Type Indicator */}
      <div
        className={cn(
          'flex items-center justify-center w-12 h-12 rounded-lg',
          isBuy
            ? 'bg-profit/10 text-profit'
            : 'bg-loss/10 text-loss'
        )}
      >
        <Icon className="w-6 h-6" />
      </div>

      {/* Signal Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-bold text-lg">{signal.symbol}</span>
          <span className={cn(
            'signal-badge',
            isBuy ? 'signal-buy' : 'signal-sell'
          )}>
            {signal.signalType}
          </span>
          <span className={cn(
            'text-xs px-2 py-0.5 rounded-full',
            signal.marketType === 'BIST'
              ? 'bg-primary/10 text-primary'
              : 'bg-secondary/10 text-secondary'
          )}>
            {signal.marketType}
          </span>
        </div>
        <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Target className="w-3 h-3" />
            {signal.strategy}
          </span>
          <span className="flex items-center gap-1">
            <Activity className="w-3 h-3" />
            {signal.score}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {signal.timeframe}
          </span>
        </div>
      </div>

      {/* Price & Time */}
      <div className="text-right">
        <div className="font-bold mono-numbers">
          {signal.marketType === 'Kripto' ? '$' : '₺'}
          {signal.price.toLocaleString('tr-TR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })}
        </div>
        <div className="text-xs text-muted-foreground">
          {dateStr} {timeStr}
        </div>
      </div>

      {/* New indicator */}
      {isNew && (
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full animate-ping" />
      )}
    </div>
  );
}

// ==================== SIGNAL TERMINAL ====================

interface SignalTerminalProps {
  showFilters?: boolean;
  onSignalSelect?: (signal: Signal) => void;
  className?: string;
  defaultTimeRange?: '24h' | '7d' | '30d' | 'all';
}

export function SignalTerminal({
  showFilters = true,
  onSignalSelect,
  className,
  defaultTimeRange = '24h',
}: SignalTerminalProps) {
  const [filter, setFilter] = useState<{
    strategy: string | null;
    signalType: string | null;
    marketType: string | null;
    timeRange: '24h' | '7d' | '30d' | 'all';
  }>({
    strategy: null,
    signalType: null,
    marketType: null,
    timeRange: defaultTimeRange,
  });
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [notifications, setNotifications] = useState(true);
  const [newSignalIds, setNewSignalIds] = useState<Set<number>>(new Set());
  const [lastUpdateTime, setLastUpdateTime] = useState<string>("");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);
  const prevSignalsRef = useRef<Signal[]>([]);

  // Get signals from API (fetch more for pagination)
  const { data: signalsData, isLoading } = useSignals({
    strategy: (filter.strategy as 'COMBO' | 'HUNTER' | 'all') || undefined,
    direction: (filter.signalType as 'AL' | 'SAT' | 'all') || undefined,
  });

  // Get realtime signals from WebSocket
  const realtimeSignals = useRealtimeStore((state) => state.realtimeSignals);

  // Calculate time filter cutoff
  const getTimeFilterCutoff = (timeRange: '24h' | '7d' | '30d' | 'all') => {
    const now = new Date();
    switch (timeRange) {
      case '24h':
        return new Date(now.getTime() - 24 * 60 * 60 * 1000);
      case '7d':
        return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      case '30d':
        return new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      default:
        return null;
    }
  };

  // Combine and filter signals
  const { allFilteredSignals, paginatedSignals, totalCount, totalPages } = useMemo(() => {
    const apiSignals: Signal[] = signalsData?.map((s) => ({
      id: s.id,
      symbol: s.symbol,
      marketType: s.marketType,
      strategy: s.strategy,
      signalType: s.signalType,
      timeframe: s.timeframe,
      score: s.score || '',
      price: s.price,
      createdAt: s.createdAt,
    })) || [];

    // Merge with realtime signals
    const all = [...realtimeSignals, ...apiSignals];

    // Remove duplicates
    const seen = new Set<number>();
    const unique = all.filter((s) => {
      if (seen.has(s.id)) return false;
      seen.add(s.id);
      return true;
    });

    // Apply filters including time range
    const timeCutoff = getTimeFilterCutoff(filter.timeRange);
    const filtered = unique
      .filter((s) => {
        if (filter.strategy && s.strategy !== filter.strategy) return false;
        if (filter.signalType && s.signalType !== filter.signalType) return false;
        if (filter.marketType && s.marketType !== filter.marketType) return false;
        if (timeCutoff) {
          const signalTime = new Date(s.createdAt);
          if (signalTime < timeCutoff) return false;
        }
        return true;
      })
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    // Calculate pagination
    const total = filtered.length;
    const pages = Math.ceil(total / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const paginated = filtered.slice(startIndex, startIndex + itemsPerPage);

    return {
      allFilteredSignals: filtered,
      paginatedSignals: paginated,
      totalCount: total,
      totalPages: pages,
    };
  }, [signalsData, realtimeSignals, filter, currentPage, itemsPerPage]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [filter, itemsPerPage]);

  // Track new signals
  useEffect(() => {
    if (prevSignalsRef.current.length > 0) {
      const prevIds = new Set(prevSignalsRef.current.map((s) => s.id));
      const newIds = allFilteredSignals
        .filter((s) => !prevIds.has(s.id))
        .map((s) => s.id);

      if (newIds.length > 0) {
        setNewSignalIds(new Set(newIds));

        // Play notification sound if enabled
        if (notifications && typeof window !== 'undefined') {
          // Could add notification sound here
        }

        // Clear new indicator after 5 seconds
        setTimeout(() => {
          setNewSignalIds(new Set());
        }, 5000);
      }
    }
    prevSignalsRef.current = allFilteredSignals;
  }, [allFilteredSignals, notifications]);

  // Update time only on client side (avoid hydration mismatch)
  useEffect(() => {
    const updateTime = () => {
      setLastUpdateTime(new Date().toLocaleTimeString('tr-TR'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Stats (based on all filtered signals, not just current page)
  const stats = useMemo(() => {
    const buyCount = allFilteredSignals.filter((s) => s.signalType === 'AL').length;
    const sellCount = allFilteredSignals.filter((s) => s.signalType === 'SAT').length;
    const bistCount = allFilteredSignals.filter((s) => s.marketType === 'BIST').length;
    const cryptoCount = allFilteredSignals.filter((s) => s.marketType === 'Kripto').length;
    return { buyCount, sellCount, bistCount, cryptoCount, total: totalCount };
  }, [allFilteredSignals, totalCount]);

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Terminal Header */}
      <div className="terminal-header">
        <div className="terminal-dot terminal-dot-red" />
        <div className="terminal-dot terminal-dot-yellow" />
        <div className="terminal-dot terminal-dot-green" />
        <div className="flex-1 flex items-center justify-between ml-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <span className="font-medium">Canlı Sinyal Terminali</span>
            <span className="text-xs text-muted-foreground">
              [{stats.total} sinyal]
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* Notification toggle */}
            <button
              onClick={() => setNotifications(!notifications)}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                notifications ? 'text-primary' : 'text-muted-foreground'
              )}
              title={notifications ? 'Bildirimleri Kapat' : 'Bildirimleri Aç'}
            >
              {notifications ? (
                <Bell className="w-4 h-4" />
              ) : (
                <BellOff className="w-4 h-4" />
              )}
            </button>

            {/* Filter toggle */}
            {showFilters && (
              <button
                onClick={() => setShowFilterMenu(!showFilterMenu)}
                className={cn(
                  'flex items-center gap-1 px-2 py-1 rounded-md transition-colors',
                  'text-muted-foreground hover:text-foreground',
                  (filter.strategy || filter.signalType || filter.marketType) && 'text-primary'
                )}
              >
                <Filter className="w-4 h-4" />
                <ChevronDown className={cn(
                  'w-3 h-3 transition-transform',
                  showFilterMenu && 'rotate-180'
                )} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Filter Menu */}
      {showFilterMenu && (
        <div className="flex flex-wrap items-center gap-3 px-4 py-2 bg-muted/20 border-b border-border/30 text-sm">
          {/* Time Range */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <select
              value={filter.timeRange}
              onChange={(e) => setFilter({ ...filter, timeRange: e.target.value as any })}
              className="bg-background/50 border border-border/50 rounded-md px-2 py-1 text-sm focus:outline-none focus:border-primary/50"
            >
              <option value="24h">Son 24 Saat</option>
              <option value="7d">Son 7 Gün</option>
              <option value="30d">Son 30 Gün</option>
              <option value="all">Tüm Zamanlar</option>
            </select>
          </div>

          <div className="w-px h-6 bg-border/50" />

          <select
            value={filter.strategy || ''}
            onChange={(e) => setFilter({ ...filter, strategy: e.target.value || null })}
            className="bg-background/50 border border-border/50 rounded-md px-2 py-1 text-sm focus:outline-none focus:border-primary/50"
          >
            <option value="">Tüm Stratejiler</option>
            <option value="COMBO">COMBO</option>
            <option value="HUNTER">HUNTER</option>
          </select>

          <select
            value={filter.signalType || ''}
            onChange={(e) => setFilter({ ...filter, signalType: e.target.value || null })}
            className="bg-background/50 border border-border/50 rounded-md px-2 py-1 text-sm focus:outline-none focus:border-primary/50"
          >
            <option value="">Tüm Sinyaller</option>
            <option value="AL">AL</option>
            <option value="SAT">SAT</option>
          </select>

          <select
            value={filter.marketType || ''}
            onChange={(e) => setFilter({ ...filter, marketType: e.target.value || null })}
            className="bg-background/50 border border-border/50 rounded-md px-2 py-1 text-sm focus:outline-none focus:border-primary/50"
          >
            <option value="">Tüm Piyasalar</option>
            <option value="BIST">BIST</option>
            <option value="Kripto">Kripto</option>
          </select>

          <button
            onClick={() => setFilter({ strategy: null, signalType: null, marketType: null, timeRange: '24h' })}
            className="text-xs text-muted-foreground hover:text-foreground ml-auto"
          >
            Temizle
          </button>
        </div>
      )}

      {/* Stats Bar */}
      <div className="flex items-center gap-4 px-4 py-2 bg-muted/10 border-b border-border/30 text-xs">
        <div className="flex items-center gap-1.5">
          <TrendingUp className="w-3 h-3 text-profit" />
          <span className="text-profit font-medium">{stats.buyCount} AL</span>
        </div>
        <div className="flex items-center gap-1.5">
          <TrendingDown className="w-3 h-3 text-loss" />
          <span className="text-loss font-medium">{stats.sellCount} SAT</span>
        </div>
        <div className="ml-auto flex items-center gap-4">
          <span className="text-primary">{stats.bistCount} BIST</span>
          <span className="text-secondary">{stats.cryptoCount} Kripto</span>
        </div>
      </div>

      {/* Signal List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {isLoading ? (
          // Loading skeleton
          Array(5).fill(null).map((_, i) => (
            <div key={i} className="h-20 bg-muted/20 rounded-lg shimmer" />
          ))
        ) : paginatedSignals.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <Zap className="w-8 h-8 mb-2 opacity-50" />
            <span>Henüz sinyal yok</span>
            <span className="text-xs mt-1">Filtrelerinizi kontrol edin</span>
          </div>
        ) : (
          paginatedSignals.map((signal) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              isNew={newSignalIds.has(signal.id)}
              onSelect={onSignalSelect}
            />
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          totalItems={totalCount}
          itemsPerPage={itemsPerPage}
          onPageChange={setCurrentPage}
          onItemsPerPageChange={setItemsPerPage}
        />
      )}

      {/* Footer */}
      <div className="px-4 py-2 border-t border-border/30 text-xs text-muted-foreground flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-profit animate-pulse" />
          Canlı bağlantı aktif
        </span>
        <span>Son güncelleme: {lastUpdateTime || '--:--:--'}</span>
      </div>
    </div>
  );
}

// ==================== MINI SIGNAL LIST ====================

interface MiniSignalListProps {
  limit?: number;
  className?: string;
}

export function MiniSignalList({ limit = 5, className }: MiniSignalListProps) {
  const { data: signals } = useSignals();

  return (
    <div className={cn('space-y-2', className)}>
      {signals?.slice(0, limit).map((signal) => {
        const isBuy = signal.signalType === 'AL';
        return (
          <div
            key={signal.id}
            className="flex items-center justify-between p-2 rounded-lg bg-card/30 border border-border/20"
          >
            <div className="flex items-center gap-2">
              <div className={cn(
                'w-1.5 h-8 rounded-full',
                isBuy ? 'bg-profit' : 'bg-loss'
              )} />
              <div>
                <span className="font-medium text-sm">{signal.symbol}</span>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span>{signal.strategy}</span>
                  <span>•</span>
                  <span>{signal.timeframe}</span>
                </div>
              </div>
            </div>
            <span className={cn(
              'text-xs font-medium px-2 py-1 rounded-full',
              isBuy ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss'
            )}>
              {signal.signalType}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default SignalTerminal;
