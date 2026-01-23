'use client';

import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { X, Bell, ArrowUpRight, ArrowDownRight, CheckCircle, AlertTriangle } from 'lucide-react';

// Toast types
export interface Toast {
    id: string;
    type: 'signal' | 'success' | 'error' | 'info';
    title: string;
    message?: string;
    duration?: number;
    data?: {
        symbol?: string;
        signalType?: 'AL' | 'SAT';
        strategy?: string;
    };
}

interface ToastContextType {
    toasts: Toast[];
    addToast: (toast: Omit<Toast, 'id'>) => void;
    removeToast: (id: string) => void;
    clearAll: () => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
}

// Toast Provider Component
export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        const newToast = { ...toast, id };

        setToasts(prev => [newToast, ...prev].slice(0, 5)); // Max 5 toasts

        // Auto-remove after duration
        const duration = toast.duration ?? 5000;
        if (duration > 0) {
            setTimeout(() => {
                setToasts(prev => prev.filter(t => t.id !== id));
            }, duration);
        }
    }, []);

    const removeToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const clearAll = useCallback(() => {
        setToasts([]);
    }, []);

    return (
        <ToastContext.Provider value={{ toasts, addToast, removeToast, clearAll }}>
            {children}
            <ToastContainer toasts={toasts} onRemove={removeToast} />
        </ToastContext.Provider>
    );
}

// Toast Container
function ToastContainer({
    toasts,
    onRemove
}: {
    toasts: Toast[];
    onRemove: (id: string) => void;
}) {
    if (toasts.length === 0) return null;

    return (
        <div className="fixed bottom-20 md:bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
            {toasts.map(toast => (
                <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
            ))}
        </div>
    );
}

// Individual Toast
function ToastItem({
    toast,
    onRemove
}: {
    toast: Toast;
    onRemove: (id: string) => void;
}) {
    const [isExiting, setIsExiting] = useState(false);

    const handleRemove = () => {
        setIsExiting(true);
        setTimeout(() => onRemove(toast.id), 200);
    };

    const getIcon = () => {
        switch (toast.type) {
            case 'signal':
                if (toast.data?.signalType === 'AL') {
                    return <ArrowUpRight className="h-5 w-5 text-profit" />;
                }
                return <ArrowDownRight className="h-5 w-5 text-loss" />;
            case 'success':
                return <CheckCircle className="h-5 w-5 text-profit" />;
            case 'error':
                return <AlertTriangle className="h-5 w-5 text-loss" />;
            default:
                return <Bell className="h-5 w-5 text-primary" />;
        }
    };

    const getBorderColor = () => {
        switch (toast.type) {
            case 'signal':
                return toast.data?.signalType === 'AL' ? 'border-l-profit' : 'border-l-loss';
            case 'success':
                return 'border-l-profit';
            case 'error':
                return 'border-l-loss';
            default:
                return 'border-l-primary';
        }
    };

    return (
        <div
            className={cn(
                "flex items-start gap-3 p-4 bg-card border border-border rounded-lg shadow-lg border-l-4 transition-all duration-200",
                getBorderColor(),
                isExiting ? "opacity-0 translate-x-4" : "opacity-100 translate-x-0",
                "animate-in slide-in-from-right-5"
            )}
        >
            <div className="shrink-0 pt-0.5">
                {getIcon()}
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{toast.title}</p>
                {toast.message && (
                    <p className="text-xs text-muted-foreground mt-0.5">{toast.message}</p>
                )}
                {toast.data?.symbol && (
                    <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs font-mono font-bold">{toast.data.symbol}</span>
                        {toast.data.strategy && (
                            <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded">
                                {toast.data.strategy}
                            </span>
                        )}
                    </div>
                )}
            </div>
            <button
                onClick={handleRemove}
                className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
            >
                <X className="h-4 w-4" />
            </button>
        </div>
    );
}

// Signal toast helper
export function showSignalToast(
    addToast: ToastContextType['addToast'],
    signal: {
        symbol: string;
        signalType: 'AL' | 'SAT';
        strategy: string;
        timeframe: string;
    }
) {
    addToast({
        type: 'signal',
        title: `Yeni ${signal.signalType === 'AL' ? 'LONG' : 'SHORT'} Sinyal`,
        message: `${signal.timeframe}`,
        data: {
            symbol: signal.symbol,
            signalType: signal.signalType,
            strategy: signal.strategy,
        },
        duration: 8000,
    });
}
