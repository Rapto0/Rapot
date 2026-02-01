'use client';

import { useState } from 'react';
import { KPICards } from "@/components/dashboard/kpi-cards"
import { AdvancedChartPage } from "@/components/charts/advanced-chart"
import { SignalTerminal } from "@/components/dashboard/signal-terminal"
import { PortfolioPanel } from "@/components/dashboard/portfolio-panel"
import { MarketOverview } from "@/components/dashboard/market-overview"
import { BotDashboard } from "@/components/dashboard/bot-dashboard"
import { useRealtime } from "@/lib/hooks/use-realtime"
import { Zap, BarChart3, Wallet, Activity } from "lucide-react"

export default function DashboardPage() {
    const [selectedSymbol, setSelectedSymbol] = useState('THYAO');
    const [selectedMarket, setSelectedMarket] = useState<'BIST' | 'Kripto'>('BIST');
    const [selectedPrice, setSelectedPrice] = useState(0);

    // Initialize real-time connection
    const { connectionState } = useRealtime({
        onSignal: (signal) => {
            // Could show notification for new signals
            console.log('New signal:', signal);
        },
    });

    // Handle signal selection from terminal
    const handleSignalSelect = (signal: any) => {
        setSelectedSymbol(signal.symbol);
        setSelectedMarket(signal.marketType as 'BIST' | 'Kripto');
        setSelectedPrice(signal.price);
    };

    return (
        <div className="flex flex-col min-h-screen -m-4">
            {/* Main Content */}
            <div className="flex-1 p-4 space-y-4">
                {/* Page Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold heading-glow">
                            Komuta Merkezi
                        </h1>
                        <p className="text-sm text-muted-foreground flex items-center gap-2">
                            <Zap className="w-3 h-3 text-primary" />
                            Gerçek zamanlı piyasa analizi ve sinyal takibi
                        </p>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                        <span className={`w-2 h-2 rounded-full ${
                            connectionState === 'connected'
                                ? 'bg-profit animate-pulse'
                                : connectionState === 'connecting'
                                ? 'bg-neutral animate-pulse'
                                : 'bg-loss'
                        }`} />
                        <span className="text-muted-foreground">
                            {connectionState === 'connected'
                                ? 'Canlı Bağlantı'
                                : connectionState === 'connecting'
                                ? 'Bağlanıyor...'
                                : 'Bağlantı Yok'}
                        </span>
                    </div>
                </div>

                {/* KPI Cards - Top Row */}
                <KPICards />

                {/* Main Bento Grid */}
                <div className="bento-grid">
                    {/* Trading Chart - Large */}
                    <div className="col-span-12 lg:col-span-8 row-span-2 bento-item p-0 overflow-hidden">
                        <AdvancedChartPage
                            initialSymbol={selectedSymbol}
                            initialMarket={selectedMarket}
                        />
                    </div>

                    {/* Signal Terminal - Side Panel */}
                    <div className="col-span-12 lg:col-span-4 row-span-2 bento-item p-0 overflow-hidden terminal">
                        <SignalTerminal
                            showFilters={true}
                            onSignalSelect={handleSignalSelect}
                            defaultTimeRange="24h"
                        />
                    </div>

                    {/* Bot Dashboard */}
                    <div className="col-span-12 lg:col-span-5 bento-item p-0 overflow-hidden">
                        <div className="p-4">
                            <div className="flex items-center gap-2 mb-4">
                                <Activity className="w-5 h-5 text-primary" />
                                <span className="font-semibold">Bot Durumu</span>
                            </div>
                            <BotDashboard />
                        </div>
                    </div>

                    {/* Market Overview */}
                    <div className="col-span-12 lg:col-span-4 bento-item p-0 overflow-hidden">
                        <div className="p-4">
                            <div className="flex items-center gap-2 mb-4">
                                <BarChart3 className="w-5 h-5 text-primary" />
                                <span className="font-semibold">Piyasa Özeti</span>
                            </div>
                            <MarketOverview />
                        </div>
                    </div>

                    {/* Portfolio Panel */}
                    <div className="col-span-12 lg:col-span-3 bento-item p-0 overflow-hidden">
                        <PortfolioPanel
                            selectedSymbol={selectedSymbol}
                            selectedPrice={selectedPrice}
                        />
                    </div>
                </div>

                {/* Footer Stats */}
                <div className="flex items-center justify-between pt-4 border-t border-border/30 text-xs text-muted-foreground">
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1.5">
                            <Zap className="w-3 h-3 text-primary" />
                            Rapot Trading Platform v1.0
                        </span>
                        <span>•</span>
                        <span>7/24 Otonom Analiz</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <span>TradingView Charts</span>
                        <span>•</span>
                        <span>Binance & BIST Data</span>
                    </div>
                </div>
            </div>
        </div>
    )
}
