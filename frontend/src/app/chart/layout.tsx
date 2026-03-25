import type { ReactNode } from "react"

export default function ChartLayout({
  children,
}: Readonly<{
  children: ReactNode
}>) {
  return (
    <div className="-mb-16 h-[calc(100vh-40px+4rem)] overflow-hidden md:mb-0 md:h-[calc(100vh-40px)]">
      {children}
    </div>
  )
}
