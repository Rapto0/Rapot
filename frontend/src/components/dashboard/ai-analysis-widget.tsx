"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { BrainCircuit, TrendingUp, TrendingDown, Minus, AlertTriangle, ShieldCheck } from "lucide-react"

interface AIAnalysisData {
    sentiment_score: number
    sentiment_label: string
    summary: string[]
    explanation: string
    key_levels: {
        support: string[]
        resistance: string[]
    }
    risk_level: "Düşük" | "Orta" | "Yüksek"
}

interface AIAnalysisWidgetProps {
    symbol: string
    data?: AIAnalysisData
    isLoading: boolean
}

export function AIAnalysisWidget({ symbol, data, isLoading }: AIAnalysisWidgetProps) {
    if (isLoading) {
        return (
            <Card className="h-full border-[#2a2e39] bg-[#1e222d]">
                <CardContent className="flex flex-col items-center justify-center h-[400px] text-[#787b86]">
                    <BrainCircuit className="h-10 w-10 animate-pulse mb-4 text-[#2962ff]" />
                    <p>Yapay Zeka {symbol} verilerini analiz ediyor...</p>
                    <p className="text-xs mt-2">Bu işlem 5-10 saniye sürebilir.</p>
                </CardContent>
            </Card>
        )
    }

    if (!data) {
        return (
            <Card className="h-full border-[#2a2e39] bg-[#1e222d]">
                <CardContent className="flex items-center justify-center h-[400px]">
                    <p className="text-[#787b86]">Analiz verisi bulunamadı.</p>
                </CardContent>
            </Card>
        )
    }

    // Gauge Color Logic
    const getScoreColor = (score: number) => {
        if (score >= 75) return "text-[#089981]" // Strong Buy
        if (score >= 55) return "text-[#089981]" // Buy
        if (score <= 25) return "text-[#f23645]" // Strong Sell
        if (score <= 45) return "text-[#f23645]" // Sell
        return "text-[#d1d4dc]" // Neutral
    }

    const getScoreBg = (score: number) => {
        if (score >= 55) return "bg-[#089981]"
        if (score <= 45) return "bg-[#f23645]"
        return "bg-[#787b86]"
    }

    return (
        <Card className="h-full border-[#2a2e39] bg-[#1e222d] overflow-hidden flex flex-col">
            <CardHeader className="pb-2 border-b border-[#2a2e39] bg-[#1e222d]">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <BrainCircuit className="h-5 w-5 text-[#2962ff]" />
                        <div>
                            <CardTitle className="text-base font-bold text-[#d1d4dc]">AI Piyasa Analisti</CardTitle>
                            <CardDescription className="text-xs text-[#787b86]">Gemini 2.0 Flash • Canlı Yorum</CardDescription>
                        </div>
                    </div>
                    <Badge variant="outline" className={cn("text-xs font-mono", getScoreColor(data.sentiment_score), "border-current bg-transparent")}>
                        {data.sentiment_label} ({data.sentiment_score}/100)
                    </Badge>
                </div>
            </CardHeader>

            <ScrollArea className="flex-1">
                <CardContent className="p-4 space-y-6">

                    {/* 1. Sentiment Gauge Visualization */}
                    <div className="relative pt-2 pb-6 flex flex-col items-center">
                        <div className="w-full h-3 bg-[#2a2e39] rounded-full overflow-hidden relative">
                            {/* Gradient Background */}
                            <div className="absolute inset-0 bg-gradient-to-r from-[#f23645] via-[#787b86] to-[#089981] opacity-30" />
                            {/* Indicator */}
                            <div
                                className="absolute top-0 bottom-0 w-2 bg-white shadow-[0_0_10px_white] transition-all duration-1000 ease-out z-10"
                                style={{ left: `${data.sentiment_score}%`, transform: 'translateX(-50%)' }}
                            />
                        </div>
                        <div className="flex justify-between w-full text-[10px] text-[#787b86] mt-1.5 font-mono px-1">
                            <span>KORKU (0)</span>
                            <span>NÖTR (50)</span>
                            <span>AÇGÖZLÜLÜK (100)</span>
                        </div>
                    </div>

                    {/* 2. Main Explanation */}
                    <div className="bg-[#2a2e39]/30 p-3 rounded-lg border border-[#2a2e39]">
                        <p className="text-sm text-[#d1d4dc] leading-relaxed italic">
                            "{data.explanation}"
                        </p>
                    </div>

                    {/* 3. Bullet Points Summary */}
                    <div>
                        <h4 className="text-xs font-bold text-[#787b86] uppercase mb-2 tracking-wider flex items-center gap-1">
                            <ShieldCheck className="h-3 w-3" /> Önemli Tespitler
                        </h4>
                        <ul className="space-y-2">
                            {data.summary.map((item, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm text-[#b2b5be]">
                                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-[#2962ff] flex-shrink-0" />
                                    <span>{item}</span>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* 4. Risk & Levels Grid */}
                    <div className="grid grid-cols-2 gap-4">
                        {/* Risk Level */}
                        <div className="bg-[#2a2e39]/50 p-3 rounded-lg text-center border border-[#2a2e39]">
                            <h4 className="text-[10px] font-bold text-[#787b86] uppercase mb-1">Risk Seviyesi</h4>
                            <div className={cn(
                                "text-sm font-bold flex items-center justify-center gap-1.5",
                                data.risk_level === "Yüksek" ? "text-[#f23645]" :
                                    data.risk_level === "Düşük" ? "text-[#089981]" : "text-[#fb8c00]"
                            )}>
                                {data.risk_level === "Yüksek" && <AlertTriangle className="h-4 w-4" />}
                                {data.risk_level === "Düşük" && <ShieldCheck className="h-4 w-4" />}
                                {data.risk_level}
                            </div>
                        </div>

                        {/* Key Levels - Simplified */}
                        <div className="bg-[#2a2e39]/50 p-3 rounded-lg border border-[#2a2e39]">
                            <h4 className="text-[10px] font-bold text-[#787b86] uppercase mb-2 text-center">Referans Seviyeler</h4>
                            <div className="space-y-1.5 text-xs">
                                <div className="flex justify-between">
                                    <span className="text-[#089981]">Destek</span>
                                    <span className="font-mono text-[#d1d4dc]">{data.key_levels.support[0] || "-"}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-[#f23645]">Direnç</span>
                                    <span className="font-mono text-[#d1d4dc]">{data.key_levels.resistance[0] || "-"}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                </CardContent>
            </ScrollArea>
        </Card>
    )
}
