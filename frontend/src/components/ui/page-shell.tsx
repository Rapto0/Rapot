import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

type PageShellWidth = "narrow" | "default" | "wide"

interface PageShellProps {
  children: ReactNode
  title: string
  description?: string
  label?: string
  actions?: ReactNode
  width?: PageShellWidth
  className?: string
  contentClassName?: string
}

const WIDTH_CLASS: Record<PageShellWidth, string> = {
  narrow: "max-w-[1280px]",
  default: "max-w-[1680px]",
  wide: "max-w-[1900px]",
}

function PageShell({
  children,
  title,
  description,
  label,
  actions,
  width = "default",
  className,
  contentClassName,
}: PageShellProps) {
  return (
    <div className={cn("mx-auto flex w-full flex-col gap-3 p-3", WIDTH_CLASS[width], className)}>
      <section className="border border-border bg-surface p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            {label ? <div className="label-uppercase">{label}</div> : null}
            <h1 className={cn("mt-1 text-lg font-semibold tracking-[-0.02em]", !label && "mt-0")}>{title}</h1>
            {description ? <p className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
          </div>
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </div>
      </section>
      <div className={cn("flex min-h-0 flex-1 flex-col gap-3", contentClassName)}>{children}</div>
    </div>
  )
}

export { PageShell }
