"use client"

import { useEffect, useMemo, useState } from "react"
import { cn } from "@/lib/utils"
import { useHealthCheck } from "@/lib/hooks/use-health"

export function Header() {
  const [now, setNow] = useState<Date>(new Date())
  const { data: health, isError } = useHealthCheck()

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const dateLabel = useMemo(
    () =>
      now.toLocaleDateString("tr-TR", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }),
    [now]
  )

  const timeLabel = useMemo(
    () =>
      now.toLocaleTimeString("tr-TR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
    [now]
  )

  const isOnline =
    !isError && (health?.status === "healthy" || health?.status === "running")

  return (
    <header className="fixed left-0 right-0 top-0 z-50 hidden h-10 items-center justify-between border-b border-border bg-surface px-3 md:flex md:left-14">
      <div className="flex items-center gap-2 text-[13px]">
        <span className="font-semibold text-foreground">Rapot</span>
        <span className="text-muted-foreground">|</span>
        <span className="text-muted-foreground">Otonom Piyasa Analizi</span>
      </div>

      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-2 label-uppercase">
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              isOnline ? "bg-profit animate-pulse-dot" : "bg-loss"
            )}
          />
          <span>{isOnline ? "API BAĞLI" : "API KAPALI"}</span>
        </div>
        <span className="text-muted-foreground">{dateLabel}</span>
        <span className="mono-numbers text-foreground">{timeLabel}</span>
      </div>
    </header>
  )
}
