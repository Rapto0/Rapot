"use client"

import { useEffect, useState } from "react"
import { bistSessionLabel } from "@/lib/bist-session"

export function BistSessionStatus() {
    const [now, setNow] = useState(0)
    useEffect(() => {
        const update = () => setNow(Date.now())
        update()
        const timer = setInterval(update, 30_000)
        return () => clearInterval(timer)
    }, [])

    return <span>{bistSessionLabel(now)}</span>
}
