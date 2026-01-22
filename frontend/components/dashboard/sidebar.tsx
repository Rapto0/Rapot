"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  CandlestickChart,
  LayoutDashboard,
  Settings,
  ShieldCheck,
  Signal,
  Rows3
} from "lucide-react";

import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/screener", label: "Piyasa Tarayıcı", icon: Rows3 },
  { href: "/signals", label: "Aktif Sinyaller", icon: Signal },
  { href: "/history", label: "İşlem Geçmişi", icon: CandlestickChart },
  { href: "/health", label: "Bot Sağlığı", icon: Activity },
  { href: "/settings", label: "Ayarlar", icon: Settings }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-white/10 bg-black/40 px-4 py-6">
      <div className="flex items-center gap-2 px-2 text-lg font-semibold">
        <ShieldCheck className="h-5 w-5 text-accent" />
        OtonomTradingbot
      </div>
      <nav className="mt-8 flex flex-1 flex-col gap-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-white/70 transition hover:bg-white/5 hover:text-white",
                isActive && "bg-white/10 text-white"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-xs text-white/60">
        <p className="text-white">Canlı Mod</p>
        Bot: BIST + Binance<br />
        Risk Modu: Dinamik
      </div>
    </aside>
  );
}
