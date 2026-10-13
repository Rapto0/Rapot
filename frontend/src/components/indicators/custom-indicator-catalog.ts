"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "@/lib/hooks/use-session"
import { fetchCustomIndicatorCatalog } from "@/lib/api/custom-indicators-api"

export function useCustomIndicatorCatalog() {
    const session = useSession()
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
    const identity = `${session?.user.username ?? "anonymous"}:${session?.expiresAt ?? 0}`
    const query = useQuery({
        queryKey: ["custom-indicator-catalog", identity],
        queryFn: ({ signal }) => fetchCustomIndicatorCatalog(signal),
        enabled: allowed,
        staleTime: 60_000,
        gcTime: 0,
        retry: false,
    })
    return { query, allowed, identity }
}
