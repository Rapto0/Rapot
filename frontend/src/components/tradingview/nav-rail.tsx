"use client"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { useDashboardStore } from "@/lib/stores"
import {
    List,
    Bell,
    Settings,
    MoreHorizontal,
    Lightbulb,
    Calendar,
    Newspaper,
    MessagesSquare,
    Layers,
} from "lucide-react"

export function NavRail() {
    const { activeSidebarTab, setActiveSidebarTab } = useDashboardStore()

    return (
        <div className="flex w-[50px] flex-col items-center border-l border-[#2a2e39] bg-[#1e222d] py-2">
            <div className="flex flex-col gap-2">
                <NavButton
                    icon={List}
                    active={activeSidebarTab === 'watchlist'}
                    onClick={() => setActiveSidebarTab('watchlist')}
                    tooltip="İzleme Listesi"
                />
                <NavButton
                    icon={Bell}
                    active={activeSidebarTab === 'signals'}
                    onClick={() => setActiveSidebarTab('signals')}
                    tooltip="Sinyaller"
                />
                <NavButton
                    icon={Newspaper}
                    active={activeSidebarTab === 'news'}
                    onClick={() => setActiveSidebarTab('news')}
                    tooltip="Haberler"
                />
                <NavButton
                    icon={Layers}
                    active={activeSidebarTab === 'data'}
                    onClick={() => setActiveSidebarTab('data')}
                    tooltip="Veri Penceresi"
                />
                <NavButton
                    icon={Calendar}
                    active={activeSidebarTab === 'calendar'}
                    onClick={() => setActiveSidebarTab('calendar')}
                    tooltip="Takvim"
                />
                <NavButton icon={Lightbulb} tooltip="Fikirler" />
                <NavButton icon={MessagesSquare} tooltip="Sohbet" />
            </div>

            <div className="mt-auto flex flex-col gap-2">
                <Separator className="bg-[#2a2e39]" />
                <NavButton icon={Settings} tooltip="Ayarlar" />
                <NavButton icon={MoreHorizontal} tooltip="Diğer" />
            </div>
        </div>
    )
}

function NavButton({ icon: Icon, active, onClick, tooltip }: { icon: any; active?: boolean; onClick?: () => void; tooltip?: string }) {
    return (
        <Button
            variant="ghost"
            size="icon"
            className={cn(
                "h-10 w-10 text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc] transition-colors",
                active && "text-[#2962ff] hover:text-[#2962ff] bg-[#2a2e39]"
            )}
            onClick={onClick}
            title={tooltip}
        >
            <Icon className="h-5 w-5" />
        </Button>
    )
}
