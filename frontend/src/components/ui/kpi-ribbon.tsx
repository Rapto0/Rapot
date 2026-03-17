import { cn } from "@/lib/utils"

type RibbonTone = "profit" | "loss" | "neutral"

interface KpiRibbonItem {
  label: string
  value: string
  tone?: RibbonTone
}

interface KpiRibbonProps {
  items: KpiRibbonItem[]
  columnsClassName?: string
  className?: string
}

function KpiRibbon({ items, columnsClassName, className }: KpiRibbonProps) {
  return (
    <section
      className={cn(
        "grid h-16 shrink-0 border border-border bg-surface",
        columnsClassName ?? "grid-cols-2 md:grid-cols-4",
        className
      )}
    >
      {items.map((item) => (
        <div
          key={item.label}
          className="flex min-w-0 flex-col justify-center gap-1 border-r border-border px-3 last:border-r-0"
        >
          <span className="label-uppercase">{item.label}</span>
          <span
            className={cn(
              "mono-numbers truncate text-lg font-semibold",
              item.tone === "profit" && "text-profit",
              item.tone === "loss" && "text-loss",
              item.tone === "neutral" && "text-neutral"
            )}
          >
            {item.value}
          </span>
        </div>
      ))}
    </section>
  )
}

export type { KpiRibbonItem, RibbonTone }
export { KpiRibbon }
