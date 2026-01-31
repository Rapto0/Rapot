"use client"

import { useSidebar } from "./sidebar-context"
import { cn } from "@/lib/utils"

export function MainContent({ children }: { children: React.ReactNode }) {
    const { isPinned } = useSidebar()

    return (
        <main className={cn(
            "pt-14 pb-20 md:pb-4 min-h-screen p-4 transition-all duration-300",
            isPinned ? "md:ml-56" : "md:ml-16"
        )}>
            {children}
        </main>
    )
}
