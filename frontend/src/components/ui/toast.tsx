'use client'

import { useState, createContext, useContext, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { X, Bell, ArrowUpRight, ArrowDownRight, CheckCircle, AlertTriangle } from 'lucide-react'

export interface Toast {
  id: string
  type: 'signal' | 'success' | 'error' | 'info'
  title: string
  message?: string
  duration?: number
  data?: {
    symbol?: string
    signalType?: 'AL' | 'SAT'
    strategy?: string
  }
}

interface ToastContextType {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
  clearAll: () => void
}

const ToastContext = createContext<ToastContextType | null>(null)

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const newToast = { ...toast, id }

    setToasts((prev) => [newToast, ...prev].slice(0, 5))

    const duration = toast.duration ?? 5000
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, duration)
    }
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const clearAll = useCallback(() => {
    setToasts([])
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, clearAll }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  )
}

function ToastContainer({
  toasts,
  onRemove,
}: {
  toasts: Toast[]
  onRemove: (id: string) => void
}) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-20 right-4 z-50 flex max-w-sm flex-col gap-2 md:bottom-4">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  )
}

function ToastItem({
  toast,
  onRemove,
}: {
  toast: Toast
  onRemove: (id: string) => void
}) {
  const [isExiting, setIsExiting] = useState(false)

  const handleRemove = () => {
    setIsExiting(true)
    setTimeout(() => onRemove(toast.id), 180)
  }

  const getIcon = () => {
    switch (toast.type) {
      case 'signal':
        return toast.data?.signalType === 'AL' ? (
          <ArrowUpRight className="h-4 w-4 text-profit" />
        ) : (
          <ArrowDownRight className="h-4 w-4 text-loss" />
        )
      case 'success':
        return <CheckCircle className="h-4 w-4 text-profit" />
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-loss" />
      default:
        return <Bell className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getAccentClass = () => {
    switch (toast.type) {
      case 'signal':
        return toast.data?.signalType === 'AL' ? 'border-profit' : 'border-loss'
      case 'success':
        return 'border-profit'
      case 'error':
        return 'border-loss'
      default:
        return 'border-border'
    }
  }

  return (
    <div
      className={cn(
        'flex items-start gap-3 border bg-overlay p-3 transition-all duration-150',
        getAccentClass(),
        isExiting ? 'translate-x-3 opacity-0' : 'translate-x-0 opacity-100'
      )}
    >
      <div className="mt-0.5 shrink-0">{getIcon()}</div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-foreground">{toast.title}</p>
        {toast.message ? (
          <p className="mt-0.5 text-[11px] text-muted-foreground">{toast.message}</p>
        ) : null}
        {toast.data?.symbol ? (
          <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
            <span className="mono-numbers text-foreground">{toast.data.symbol}</span>
            {toast.data.strategy ? <span>{toast.data.strategy}</span> : null}
          </div>
        ) : null}
      </div>
      <button
        onClick={handleRemove}
        className="shrink-0 text-muted-foreground transition-colors hover:text-foreground"
        aria-label="Kapat"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

export function showSignalToast(
  addToast: ToastContextType['addToast'],
  signal: {
    symbol: string
    signalType: 'AL' | 'SAT'
    strategy: string
    timeframe: string
  }
) {
  addToast({
    type: 'signal',
    title: `Yeni ${signal.signalType === 'AL' ? 'AL' : 'SAT'} sinyali`,
    message: signal.timeframe,
    data: {
      symbol: signal.symbol,
      signalType: signal.signalType,
      strategy: signal.strategy,
    },
    duration: 8000,
  })
}
