"use client"

import { useSidebar } from "./sidebar-context"
import { cn } from "@/lib/utils"

export function MainContent({ children }: { children: React.ReactNode }) {
    const { isPinned } = useSidebar()

    return (
        <main className={cn(
            "min-h-screen px-4 pb-20 md:pb-4 pt-[72px] transition-all duration-300",
            isPinned ? "md:ml-56" : "md:ml-16"
        )}>
            {children}
        </main>
    )
}
