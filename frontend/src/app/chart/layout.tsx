import type { ReactNode } from "react"

export default function ChartLayout({
  children,
}: Readonly<{
  children: ReactNode
}>) {
  return (
    <div className="-mb-[16px] h-[calc(100dvh-120px-env(safe-area-inset-bottom))] overflow-hidden md:-mb-4 md:h-[calc(100dvh-2.5rem)]">
      {children}
    </div>
  )
}
