"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchSignals, transformSignal } from "@/lib/api/client"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { useDashboardStore } from "@/lib/stores"

export function ScreenerTable() {
    const { setSelectedSymbol, selectedSymbol } = useDashboardStore()
    const { data: signals, isLoading } = useQuery({
        queryKey: ['signals', 'screener'],
        queryFn: () => fetchSignals({ limit: 50 }),
        select: (data) => data.map(transformSignal),
        refetchInterval: 30000,
    })

    if (isLoading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-[#131722]">
                <div className="text-[#787b86] animate-pulse">Veriler yükleniyor...</div>
            </div>
        )
    }

    return (
        <div className="flex-1 overflow-auto bg-[#131722]">
            <Table>
                <TableHeader className="bg-[#1e222d] sticky top-0 z-10">
                    <TableRow className="border-[#2a2e39] hover:bg-[#1e222d]">
                        <TableHead className="w-[200px] text-[#787b86]">Sembol</TableHead>
                        <TableHead className="text-right text-[#787b86]">Fiyat</TableHead>
                        <TableHead className="text-right text-[#787b86]">Strateji</TableHead>
                        <TableHead className="text-right text-[#787b86]">Timeframe</TableHead>
                        <TableHead className="text-right text-[#787b86]">Puan</TableHead>
                        <TableHead className="text-right text-[#787b86]">Tarih</TableHead>
                        <TableHead className="text-right text-[#787b86]">Sinyal</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {signals?.map((signal) => (
                        <TableRow
                            key={signal.id}
                            onClick={() => setSelectedSymbol(signal.symbol)}
                            className={cn(
                                "border-[#2a2e39] h-9 transition-colors cursor-pointer group",
                                selectedSymbol === signal.symbol ? "bg-[#2a2e39]" : "hover:bg-[#2a2e39]"
                            )}
                        >
                            <TableCell className="font-medium text-[#d1d4dc] py-1">
                                <div className="flex items-center gap-2">
                                    <div className={cn(
                                        "flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold",
                                        signal.marketType === "BIST"
                                            ? "bg-[#2962ff]/10 text-[#2962ff]"
                                            : "bg-[#f7931a]/10 text-[#f7931a]"
                                    )}>
                                        {signal.symbol[0]}
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-xs font-bold leading-none text-[#d1d4dc] group-hover:text-blue-400">
                                            {signal.symbol}
                                        </span>
                                        <span className="text-[10px] text-[#787b86] leading-none mt-0.5">
                                            {signal.marketType}
                                        </span>
                                    </div>
                                </div>
                            </TableCell>
                            <TableCell className="text-right text-xs text-[#d1d4dc] py-1 font-mono">
                                {signal.price.toFixed(2)}
                            </TableCell>
                            <TableCell className="text-right text-xs text-[#787b86] py-1">
                                {signal.strategy}
                            </TableCell>
                            <TableCell className="text-right text-xs text-[#787b86] py-1">
                                {signal.timeframe}
                            </TableCell>
                            <TableCell className="text-right text-xs text-[#d1d4dc] py-1 font-mono">
                                {signal.score || "-"}
                            </TableCell>
                            <TableCell className="text-right text-xs text-[#787b86] py-1">
                                {new Date(signal.createdAt).toLocaleDateString("tr-TR")}
                            </TableCell>
                            <TableCell className="text-right py-1">
                                <Badge
                                    variant="outline"
                                    className={cn(
                                        "border-transparent text-[10px] px-1.5 py-0",
                                        signal.signalType === "AL" && "bg-[#089981]/10 text-[#089981]",
                                        signal.signalType === "SAT" && "bg-[#f23645]/10 text-[#f23645]"
                                    )}
                                >
                                    {signal.signalType === "AL" ? "Al" : "Sat"}
                                </Badge>
                            </TableCell>
                        </TableRow>
                    ))}
                    {(!signals || signals.length === 0) && (
                        <TableRow>
                            <TableCell colSpan={7} className="text-center text-[#787b86] py-8">
                                Henüz sinyal bulunamadı
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    )
}
