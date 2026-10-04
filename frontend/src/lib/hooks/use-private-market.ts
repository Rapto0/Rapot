"use client"

import { useQuery } from "@tanstack/react-query"
import { useSession } from "./use-session"
import { fetchResearchConnection } from "@/lib/api/borsapy-api"

export function usePrivateMarket() {
    const session = useSession()
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
    const sessionKey = session ? `${session.user.username}:${session.expiresAt}` : "guest"
    const connection = useQuery({
        queryKey: ["borsapy-connection", sessionKey],
        queryFn: ({ signal }) => fetchResearchConnection(signal),
        enabled: allowed,
        staleTime: 30_000,
        refetchInterval: 30_000,
        retry: false,
    })
    return { allowed, sessionKey, connection }
}
