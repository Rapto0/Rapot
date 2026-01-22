import { Activity } from "lucide-react";

import { healthStats, logLines } from "@/lib/mock-data";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function HealthOverview() {
  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Bot Health</CardTitle>
          <Activity className="h-4 w-4 text-accent" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          {healthStats.map((stat) => (
            <div key={stat.label} className="rounded-lg border border-white/10 bg-black/20 p-2">
              <p className="text-xs text-white/50">{stat.label}</p>
              <p className="text-lg font-semibold text-white">{stat.value}%</p>
              <div className="mt-1 h-1.5 w-full rounded-full bg-white/10">
                <div
                  className="h-1.5 rounded-full bg-accent"
                  style={{ width: `${stat.value}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="rounded-lg border border-white/10 bg-black/40 p-3 font-mono text-xs text-white/70">
          {logLines.map((line) => (
            <div key={line} className="leading-5">
              {line}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
