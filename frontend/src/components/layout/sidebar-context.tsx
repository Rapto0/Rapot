"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from "react"

interface SidebarContextType {
    isPinned: boolean
    setIsPinned: (value: boolean) => void
    isHovered: boolean
    setIsHovered: (value: boolean) => void
    isExpanded: boolean
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined)

const SIDEBAR_PINNED_KEY = "rapot_sidebar_pinned"

export function SidebarProvider({ children }: { children: ReactNode }) {
    const [isPinned, setIsPinnedState] = useState(true)
    const [isHovered, setIsHovered] = useState(false)
    const [isLoaded, setIsLoaded] = useState(false)

    // Load pinned state from localStorage
    useEffect(() => {
        const stored = localStorage.getItem(SIDEBAR_PINNED_KEY)
        if (stored !== null) {
            setIsPinnedState(stored === "true")
        }
        setIsLoaded(true)
    }, [])

    const setIsPinned = (value: boolean) => {
        setIsPinnedState(value)
        localStorage.setItem(SIDEBAR_PINNED_KEY, String(value))
    }

    const isExpanded = isPinned || isHovered

    // Return null during SSR to prevent hydration mismatch
    if (!isLoaded) {
        return (
            <SidebarContext.Provider
                value={{
                    isPinned: true,
                    setIsPinned,
                    isHovered: false,
                    setIsHovered,
                    isExpanded: true
                }}
            >
                {children}
            </SidebarContext.Provider>
        )
    }

    return (
        <SidebarContext.Provider
            value={{
                isPinned,
                setIsPinned,
                isHovered,
                setIsHovered,
                isExpanded
            }}
        >
            {children}
        </SidebarContext.Provider>
    )
}

export function useSidebar() {
    const context = useContext(SidebarContext)
    if (context === undefined) {
        throw new Error("useSidebar must be used within a SidebarProvider")
    }
    return context
}
