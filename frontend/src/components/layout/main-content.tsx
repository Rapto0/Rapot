import type { ReactNode } from "react"

export function MainContent({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-screen pb-16 pt-10 md:pl-14 md:pb-4">
      {children}
    </main>
  )
}
