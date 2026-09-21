import type { ReactNode } from "react"

export function MainContent({ children }: { children: ReactNode }) {
  return (
    <main id="main-content" tabIndex={-1} className="min-h-dvh min-w-0 pb-[calc(80px+env(safe-area-inset-bottom))] pt-[56px] md:pb-4 md:pl-14 md:pt-10 xl:pl-44">
      {children}
    </main>
  )
}
