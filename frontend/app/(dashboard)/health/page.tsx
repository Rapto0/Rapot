import { HealthOverview } from "@/components/dashboard/health-overview";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function HealthPage() {
  return (
    <div className="grid gap-6 lg:grid-cols-[1.3fr,1fr]">
      <HealthOverview />
      <Card className="bg-panel/95">
        <CardHeader>
          <CardTitle>Prometheus Metrikleri</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-white/70">
          <div className="rounded-lg border border-white/10 bg-black/30 p-3">
            API Latency: 120ms · Target &lt; 200ms
          </div>
          <div className="rounded-lg border border-white/10 bg-black/30 p-3">
            Event Loop Lag: 18ms · Normal
          </div>
          <div className="rounded-lg border border-white/10 bg-black/30 p-3">
            Scheduler: 5 jobs running · 0 failures
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
