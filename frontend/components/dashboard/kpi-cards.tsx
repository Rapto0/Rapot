import { ArrowDownRight, ArrowUpRight } from "lucide-react";

import { kpis } from "@/lib/mock-data";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function KpiCards() {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      {kpis.map((kpi) => {
        const isPositive = kpi.delta.startsWith("+") || kpi.delta === "Realtime";
        return (
          <Card key={kpi.label} className="bg-panel/90">
            <CardContent className="flex h-full flex-col gap-2">
              <span className="text-xs text-white/50">{kpi.label}</span>
              <div className="flex items-end justify-between">
                <span className="text-lg font-semibold text-white">{kpi.value}</span>
                <span
                  className={cn(
                    "flex items-center gap-1 text-xs",
                    kpi.tone === "long" && "text-long",
                    kpi.tone === "short" && "text-short",
                    kpi.tone === "accent" && "text-accent"
                  )}
                >
                  {isPositive ? (
                    <ArrowUpRight className="h-3 w-3" />
                  ) : (
                    <ArrowDownRight className="h-3 w-3" />
                  )}
                  {kpi.delta}
                </span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
