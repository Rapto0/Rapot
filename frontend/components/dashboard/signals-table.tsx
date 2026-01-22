"use client";

import { useMemo, useState } from "react";
import { Filter } from "lucide-react";

import { signals } from "@/lib/mock-data";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { cn } from "@/lib/utils";

const filters = ["Tümü", "HUNTER", "COMBO"];

export function SignalsTable() {
  const [activeFilter, setActiveFilter] = useState("Tümü");

  const filteredSignals = useMemo(() => {
    if (activeFilter === "Tümü") return signals;
    return signals.filter((item) => item.strategy === activeFilter);
  }, [activeFilter]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">The Screener</h2>
          <p className="text-xs text-white/50">Signals · Son 24 saat</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <Filter className="h-3 w-3 text-white/40" />
          {filters.map((filter) => (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={cn(
                "rounded-full border border-white/10 px-3 py-1 text-white/60 transition hover:text-white",
                activeFilter === filter && "border-accent text-white"
              )}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>
      <div className="rounded-xl border border-white/10 bg-panel/90">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Sembol</TableHead>
              <TableHead>Piyasa</TableHead>
              <TableHead>Strateji</TableHead>
              <TableHead>Yön</TableHead>
              <TableHead>Sinyal Skoru</TableHead>
              <TableHead>Tarih</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredSignals.map((signal) => (
              <TableRow key={`${signal.symbol}-${signal.time}`}>
                <TableCell className="font-semibold text-white">{signal.symbol}</TableCell>
                <TableCell className="text-white/60">{signal.market}</TableCell>
                <TableCell>
                  <Badge variant={signal.strategy === "HUNTER" ? "accent" : "default"}>
                    {signal.strategy}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={signal.direction === "LONG" ? "long" : "short"}>
                    {signal.direction}
                  </Badge>
                </TableCell>
                <TableCell>
                  <span
                    className={cn(
                      "rounded-full px-2 py-1 text-xs",
                      signal.score >= 85
                        ? "bg-long/10 text-long"
                        : signal.score >= 70
                        ? "bg-accent/10 text-accent"
                        : "bg-short/10 text-short"
                    )}
                  >
                    {signal.score}
                  </span>
                </TableCell>
                <TableCell className="text-white/50">{signal.time}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
