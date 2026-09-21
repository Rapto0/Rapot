import { Activity, AlarmClock, BarChart3, Bell, Brain, CalendarDays, History, Home, Search, Settings } from "lucide-react"

export const navigation = [
  { name: "Ana Sayfa", shortName: "Ana", href: "/", icon: Home },
  { name: "Grafik", shortName: "Grafik", href: "/chart", icon: BarChart3 },
  { name: "Tarayıcı", shortName: "Tarayıcı", href: "/scanner", icon: Search },
  { name: "Sinyaller", shortName: "Sinyaller", href: "/signals", icon: Bell },
  { name: "Alarmlar", shortName: "Alarmlar", href: "/alarms", icon: AlarmClock },
  { name: "İşlemler", shortName: "İşlemler", href: "/trades", icon: History },
  { name: "Bot Sağlığı", shortName: "Sağlık", href: "/health", icon: Activity },
  { name: "AI Analizi", shortName: "AI", href: "/ai", icon: Brain },
  { name: "Takvim", shortName: "Takvim", href: "/calendar", icon: CalendarDays },
  { name: "Ayarlar", shortName: "Ayarlar", href: "/settings", icon: Settings },
]

export function isActiveRoute(pathname: string, href: string) {
  return pathname === href || (href !== "/" && pathname.startsWith(`${href}/`))
}

export function pageName(pathname: string) {
  return navigation.find((item) => isActiveRoute(pathname, item.href))?.name
    ?? (pathname === "/login" ? "Giriş yap" : "Rapot")
}
