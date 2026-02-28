"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { Bell, Check, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { useRecentSignals } from "@/lib/hooks/use-signals"
import { useBotHealth } from "@/lib/hooks/use-health"

const READ_SIGNALS_KEY = "rapot_read_signal_ids"

export function Header() {
  const [currentTime, setCurrentTime] = useState<Date>(new Date())
  const [showNotifications, setShowNotifications] = useState(false)
  const [readSignalIds, setReadSignalIds] = useState<Set<number>>(() => {
    if (typeof window === "undefined") {
      return new Set()
    }

    const stored = window.localStorage.getItem(READ_SIGNALS_KEY)
    if (!stored) {
      return new Set()
    }

    try {
      const ids = JSON.parse(stored) as number[]
      return new Set(ids)
    } catch {
      return new Set()
    }
  })
  const panelRef = useRef<HTMLDivElement | null>(null)

  const { data: signals } = useRecentSignals(30)
  const { isError } = useBotHealth()

  const unreadSignals = useMemo(
    () => (signals ?? []).filter((signal) => !readSignalIds.has(signal.id)),
    [readSignalIds, signals]
  )

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    const onDocumentClick = (event: MouseEvent) => {
      if (!panelRef.current) return
      if (panelRef.current.contains(event.target as Node)) return
      setShowNotifications(false)
    }

    document.addEventListener("mousedown", onDocumentClick)
    return () => document.removeEventListener("mousedown", onDocumentClick)
  }, [])

  const markRead = (ids: number[]) => {
    setReadSignalIds((prev) => {
      const next = new Set(prev)
      ids.forEach((id) => next.add(id))
      localStorage.setItem(READ_SIGNALS_KEY, JSON.stringify(Array.from(next)))
      return next
    })
  }

  const markAllRead = () => {
    markRead((signals ?? []).map((signal) => signal.id))
  }

  return (
    <header className="fixed left-0 right-0 top-0 z-50 hidden h-10 border-b border-border bg-surface md:left-14 md:block">
      <div className="flex h-full items-center justify-between px-4">
        <div className="flex items-center gap-2 text-sm">
          <Link href="/" className="font-semibold text-foreground">
            Rapot
          </Link>
          <span className="text-muted-foreground">|</span>
          <span className="text-muted-foreground">Otonom Piyasa Analizi</span>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isError ? "bg-loss" : "bg-profit"
              )}
            />
            <span className="label-uppercase text-[10px] tracking-[0.06em]">
              {isError ? "API Kopuk" : "API Bağlı"}
            </span>
          </div>

          <div className="mono-numbers text-xs text-muted-foreground">
            {currentTime.toLocaleDateString("tr-TR", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })}
            <span className="mx-2 text-ghost">|</span>
            {currentTime.toLocaleTimeString("tr-TR", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </div>

          <div ref={panelRef} className="relative">
            <button
              type="button"
              onClick={() => setShowNotifications((prev) => !prev)}
              className="relative flex h-8 w-8 items-center justify-center border border-border bg-base text-muted-foreground transition-colors hover:bg-raised hover:text-foreground"
              aria-label="Bildirimler"
            >
              <Bell className="h-4 w-4" />
              {unreadSignals.length > 0 ? (
                <span className="absolute -right-1 -top-1 min-w-4 border border-border bg-overlay px-1 text-center text-[10px] font-semibold text-foreground">
                  {unreadSignals.length > 99 ? "99+" : unreadSignals.length}
                </span>
              ) : null}
            </button>

            {showNotifications ? (
              <div className="absolute right-0 top-10 z-50 w-[360px] border border-border bg-overlay">
                <div className="flex items-center justify-between border-b border-border px-3 py-2">
                  <span className="label-uppercase">Bildirimler</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={markAllRead}
                      className="inline-flex items-center gap-1 border border-border px-2 py-1 text-[10px] text-muted-foreground hover:bg-raised hover:text-foreground"
                    >
                      <Check className="h-3 w-3" />
                      Tümünü oku
                    </button>
                    <button
                      type="button"
                      onClick={() => setShowNotifications(false)}
                      className="flex h-6 w-6 items-center justify-center border border-border text-muted-foreground hover:bg-raised hover:text-foreground"
                      aria-label="Kapat"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                <div className="max-h-[320px] overflow-y-auto">
                  {signals && signals.length > 0 ? (
                    signals.map((signal) => {
                      const isUnread = !readSignalIds.has(signal.id)
                      return (
                        <Link
                          key={signal.id}
                          href={`/chart?symbol=${signal.symbol}&market=${signal.marketType}`}
                          onClick={() => markRead([signal.id])}
                          className={cn(
                            "flex items-center justify-between border-b border-[rgba(255,255,255,0.04)] px-3 py-2 last:border-b-0 hover:bg-raised",
                            isUnread && "bg-[rgba(255,255,255,0.03)]"
                          )}
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold text-foreground">{signal.symbol}</span>
                              <span
                                className={cn(
                                  "signal-badge",
                                  signal.signalType === "AL" ? "signal-buy" : "signal-sell"
                                )}
                              >
                                {signal.signalType}
                              </span>
                            </div>
                            <div className="mt-0.5 text-[10px] text-muted-foreground">
                              {signal.strategy} • {signal.timeframe}
                            </div>
                          </div>

                          <div className="mono-numbers text-[10px] text-muted-foreground">
                            {new Date(signal.createdAt).toLocaleTimeString("tr-TR", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </div>
                        </Link>
                      )
                    })
                  ) : (
                    <div className="px-3 py-6 text-center text-xs text-muted-foreground">
                      Bildirim bulunmuyor.
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  )
}
