import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ===== DASHBOARD STORE =====
interface DashboardState {
    // Selected symbol for chart
    selectedSymbol: string;
    setSelectedSymbol: (symbol: string) => void;

    // Time range for charts
    timeRange: '1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL';
    setTimeRange: (range: DashboardState['timeRange']) => void;

    // Sidebar collapsed state
    sidebarCollapsed: boolean;
    setSidebarCollapsed: (collapsed: boolean) => void;
    toggleSidebar: () => void;

    // Connection status
    isConnected: boolean;
    setIsConnected: (connected: boolean) => void;

    // Last update timestamp
    lastUpdate: Date | null;
    setLastUpdate: (date: Date) => void;
}

export const useDashboardStore = create<DashboardState>()(
    persist(
        (set) => ({
            // Symbol
            selectedSymbol: 'THYAO',
            setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),

            // Time range
            timeRange: '1M',
            setTimeRange: (range) => set({ timeRange: range }),

            // Sidebar
            sidebarCollapsed: false,
            setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
            toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

            // Connection
            isConnected: true,
            setIsConnected: (connected) => set({ isConnected: connected }),

            // Last update
            lastUpdate: null,
            setLastUpdate: (date) => set({ lastUpdate: date }),
        }),
        {
            name: 'rapot-dashboard',
            partialize: (state) => ({
                selectedSymbol: state.selectedSymbol,
                timeRange: state.timeRange,
                sidebarCollapsed: state.sidebarCollapsed,
            }),
        }
    )
);

// ===== SETTINGS STORE =====
interface SettingsState {
    // Telegram
    telegramChatId: string;
    telegramToken: string;

    // Binance API
    binanceApiKey: string;
    binanceSecretKey: string;

    // Strategy params
    rsiOversold: number;
    rsiOverbought: number;
    hunterMinScore: number;
    scanInterval: number;

    // Notifications
    notifications: boolean;

    // Actions
    updateSettings: (settings: Partial<SettingsState>) => void;
    resetSettings: () => void;
}

const defaultSettings = {
    telegramChatId: '',
    telegramToken: '',
    binanceApiKey: '',
    binanceSecretKey: '',
    rsiOversold: 30,
    rsiOverbought: 70,
    hunterMinScore: 10,
    scanInterval: 30,
    notifications: true,
};

export const useSettingsStore = create<SettingsState>()(
    persist(
        (set) => ({
            ...defaultSettings,
            updateSettings: (newSettings) => set((state) => ({ ...state, ...newSettings })),
            resetSettings: () => set(defaultSettings),
        }),
        {
            name: 'rapot-settings',
        }
    )
);

// ===== SIGNAL FILTERS STORE =====
interface SignalFiltersState {
    marketType: 'all' | 'BIST' | 'Kripto';
    strategy: 'all' | 'COMBO' | 'HUNTER';
    direction: 'all' | 'AL' | 'SAT';
    searchQuery: string;

    setMarketType: (type: SignalFiltersState['marketType']) => void;
    setStrategy: (strategy: SignalFiltersState['strategy']) => void;
    setDirection: (direction: SignalFiltersState['direction']) => void;
    setSearchQuery: (query: string) => void;
    resetFilters: () => void;
}

export const useSignalFiltersStore = create<SignalFiltersState>((set) => ({
    marketType: 'all',
    strategy: 'all',
    direction: 'all',
    searchQuery: '',

    setMarketType: (type) => set({ marketType: type }),
    setStrategy: (strategy) => set({ strategy: strategy }),
    setDirection: (direction) => set({ direction: direction }),
    setSearchQuery: (query) => set({ searchQuery: query }),
    resetFilters: () => set({
        marketType: 'all',
        strategy: 'all',
        direction: 'all',
        searchQuery: '',
    }),
}));

// ===== TRADE FILTERS STORE =====
interface TradeFiltersState {
    status: 'all' | 'OPEN' | 'CLOSED';
    setStatus: (status: TradeFiltersState['status']) => void;
}

export const useTradeFiltersStore = create<TradeFiltersState>((set) => ({
    status: 'all',
    setStatus: (status) => set({ status }),
}));
