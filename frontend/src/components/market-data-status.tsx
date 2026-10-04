"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { usePrivateMarket } from "@/lib/hooks/use-private-market"
import type { MarketSourceMetadata } from "@/lib/api/types"

export function MarketDataStatus({ metadata, compact = false }: { metadata?: MarketSourceMetadata; compact?: boolean }) {
    const pathname = usePathname()
    const { allowed, connection } = usePrivateMarket()
    const status = connection.data
    const binance = metadata?.source?.toLowerCase().includes("binance")
    const message = !allowed ? "Piyasa verileri için yönetici hesabınızla giriş yapın."
        : binance ? metadata?.message || "Binance · USDT piyasası"
        : connection.isError ? "Veri bağlantısının durumu alınamadı."
        : status && !status.installed ? "Veri hizmeti henüz hazır değil."
        : status && !status.configured ? "TradingView hesabınızı bağlayın."
        : status && !status.authenticated ? "Hesap bağlantınızı doğrulayın."
        : metadata?.message || "Borsapy / TradingView · gerçek zamanlı veri kabulü doğrulanmadı."
    return <div className={`flex flex-wrap items-center justify-between gap-2 border border-border bg-surface text-xs text-muted-foreground ${compact ? "px-3 py-2" : "p-3"}`} role="status">
        <div className="min-w-0 space-y-1"><p>{message}</p>{!compact && metadata?.provider_time && <p>Sağlayıcı zamanı: {metadata.provider_time}</p>}{!compact && metadata?.received_at && <p>Son alım: {new Date(metadata.received_at).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul" })}</p>}</div>
        {(!allowed || !binance) && <Link className="inline-flex min-h-11 shrink-0 items-center text-primary underline" href={allowed ? "/research?tab=connection" : `/login?next=${encodeURIComponent(pathname || "/")}`}>{allowed ? "Hesap bağlantıları" : "Giriş yap"}</Link>}
    </div>
}
