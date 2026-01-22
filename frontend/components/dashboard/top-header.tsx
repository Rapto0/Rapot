import { Bell, Wifi } from "lucide-react";

import { tickerItems } from "@/lib/mock-data";
import { Badge } from "@/components/ui/badge";

export function TopHeader() {
  return (
    <header className="flex flex-col gap-3 border-b border-white/10 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Admin Panel</h1>
          <p className="text-xs text-white/50">
            OtonomTradingbot · Gerçek zamanlı operasyon ekranı
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="accent" className="gap-1">
            <Wifi className="h-3 w-3" />
            Live
          </Badge>
          <button className="rounded-full border border-white/10 p-2 text-white/60 hover:text-white">
            <Bell className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="relative overflow-hidden rounded-lg border border-white/10 bg-white/5">
        <div className="ticker flex w-[200%] gap-8 px-4 py-2 text-xs text-white/70">
          {[...tickerItems, ...tickerItems].map((item, index) => (
            <div key={`${item.label}-${index}`} className="flex items-center gap-2">
              <span className="text-white/50">{item.label}</span>
              <span className="font-semibold text-white">{item.value}</span>
              <span
                className={
                  item.change.startsWith("-")
                    ? "text-short"
                    : "text-long"
                }
              >
                {item.change}
              </span>
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}
