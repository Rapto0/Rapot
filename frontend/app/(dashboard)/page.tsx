import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCards } from "@/components/dashboard/kpi-cards";
import { TradingChart } from "@/components/dashboard/trading-chart";
import { SignalsTable } from "@/components/dashboard/signals-table";
import { PerformanceChart } from "@/components/dashboard/performance-chart";
import { HealthOverview } from "@/components/dashboard/health-overview";

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <KpiCards />
      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <Card className="bg-panel/95">
          <CardHeader>
            <CardTitle>Market Overview · BIST 100</CardTitle>
          </CardHeader>
          <CardContent>
            <TradingChart />
          </CardContent>
        </Card>
        <HealthOverview />
      </div>
      <div className="grid gap-6 lg:grid-cols-[1.4fr,1fr]">
        <Card className="bg-panel/95">
          <CardHeader>
            <CardTitle>Haftalık Performans</CardTitle>
          </CardHeader>
          <CardContent>
            <PerformanceChart />
          </CardContent>
        </Card>
        <Card className="bg-panel/95">
          <CardHeader>
            <CardTitle>Strateji Notları</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-white/70">
            <div className="rounded-lg border border-white/10 bg-black/30 p-3">
              COMBO: MACD + RSI çift doğrulama ile volatilite filtrelendi.
            </div>
            <div className="rounded-lg border border-white/10 bg-black/30 p-3">
              HUNTER: 15 indikatörün 11'i aynı yönde. Risk ölçekleme +%12.
            </div>
            <div className="rounded-lg border border-white/10 bg-black/30 p-3">
              Portföy: BIST %55, Crypto %45. Korelasyon dengeleniyor.
            </div>
          </CardContent>
        </Card>
      </div>
      <SignalsTable />
    </div>
  );
}
