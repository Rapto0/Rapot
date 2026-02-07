"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import {
    Bell,
    Key,
    Sliders,
    Save,
    Eye,
    EyeOff,
    CheckCircle2,
} from "lucide-react"

export default function SettingsPage() {
    const [showApiKey, setShowApiKey] = useState(false)
    const [showTelegramToken, setShowTelegramToken] = useState(false)
    const [saved, setSaved] = useState(false)

    // Mock settings state
    const [settings, setSettings] = useState({
        telegramChatId: "123456789",
        telegramToken: "bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        binanceApiKey: "aBcDeFgHiJkLmNoPqRsTuVwXyZ123456",
        binanceSecretKey: "aBcDeFgHiJkLmNoPqRsTuVwXyZ789012",
        rsiOversold: 30,
        rsiOverbought: 70,
        macdSignalThreshold: 0,
        hunterMinScore: 10,
        scanInterval: 30,
        notifications: true,
    })

    const handleSave = () => {
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
    }

    return (
        <div className="space-y-4 max-w-4xl">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Ayarlar</h1>
                    <p className="text-sm text-muted-foreground">
                        Bot yapılandırması ve strateji parametreleri
                    </p>
                </div>
                <Button onClick={handleSave} className="gap-2">
                    {saved ? (
                        <>
                            <CheckCircle2 className="h-4 w-4" />
                            Kaydedildi
                        </>
                    ) : (
                        <>
                            <Save className="h-4 w-4" />
                            Kaydet
                        </>
                    )}
                </Button>
            </div>

            {/* Telegram Settings */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                        <Bell className="h-4 w-4" />
                        Telegram Bildirimleri
                    </CardTitle>
                    <CardDescription>
                        Sinyal bildirimlerinin gönderileceği Telegram hesap ayarları
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Chat ID</label>
                            <Input
                                value={settings.telegramChatId}
                                onChange={(e) =>
                                    setSettings({ ...settings, telegramChatId: e.target.value })
                                }
                                placeholder="Telegram Chat ID"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Bot Token</label>
                            <div className="relative">
                                <Input
                                    type={showTelegramToken ? "text" : "password"}
                                    value={settings.telegramToken}
                                    onChange={(e) =>
                                        setSettings({ ...settings, telegramToken: e.target.value })
                                    }
                                    placeholder="Bot Token"
                                    className="pr-10"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowTelegramToken(!showTelegramToken)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showTelegramToken ? (
                                        <EyeOff className="h-4 w-4" />
                                    ) : (
                                        <Eye className="h-4 w-4" />
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* API Keys */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                        <Key className="h-4 w-4" />
                        Binance API Anahtarları
                    </CardTitle>
                    <CardDescription>
                        Kripto piyasası verilerine erişim için API anahtarları
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">API Key</label>
                            <div className="relative">
                                <Input
                                    type={showApiKey ? "text" : "password"}
                                    value={settings.binanceApiKey}
                                    onChange={(e) =>
                                        setSettings({ ...settings, binanceApiKey: e.target.value })
                                    }
                                    placeholder="API Key"
                                    className="pr-10"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowApiKey(!showApiKey)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showApiKey ? (
                                        <EyeOff className="h-4 w-4" />
                                    ) : (
                                        <Eye className="h-4 w-4" />
                                    )}
                                </button>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Secret Key</label>
                            <div className="relative">
                                <Input
                                    type="password"
                                    value={settings.binanceSecretKey}
                                    onChange={(e) =>
                                        setSettings({ ...settings, binanceSecretKey: e.target.value })
                                    }
                                    placeholder="Secret Key"
                                />
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Strategy Parameters */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                        <Sliders className="h-4 w-4" />
                        Strateji Parametreleri
                    </CardTitle>
                    <CardDescription>
                        COMBO ve HUNTER stratejileri için teknik indikatör ayarları
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* RSI Settings */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-medium">RSI Ayarları</h4>
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <div className="flex justify-between">
                                    <label className="text-sm text-muted-foreground">
                                        Aşırı Satım (Oversold)
                                    </label>
                                    <span className="text-sm font-medium">{settings.rsiOversold}</span>
                                </div>
                                <input
                                    type="range"
                                    min="10"
                                    max="40"
                                    value={settings.rsiOversold}
                                    onChange={(e) =>
                                        setSettings({ ...settings, rsiOversold: Number(e.target.value) })
                                    }
                                    className="w-full h-2 rounded-full bg-muted appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                                />
                            </div>
                            <div className="space-y-2">
                                <div className="flex justify-between">
                                    <label className="text-sm text-muted-foreground">
                                        Aşırı Alım (Overbought)
                                    </label>
                                    <span className="text-sm font-medium">{settings.rsiOverbought}</span>
                                </div>
                                <input
                                    type="range"
                                    min="60"
                                    max="90"
                                    value={settings.rsiOverbought}
                                    onChange={(e) =>
                                        setSettings({ ...settings, rsiOverbought: Number(e.target.value) })
                                    }
                                    className="w-full h-2 rounded-full bg-muted appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                                />
                            </div>
                        </div>
                    </div>

                    {/* HUNTER Settings */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-medium">HUNTER Strateji Ayarları</h4>
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <div className="flex justify-between">
                                    <label className="text-sm text-muted-foreground">
                                        Minimum Skor (15 üzerinden)
                                    </label>
                                    <span className="text-sm font-medium">{settings.hunterMinScore}</span>
                                </div>
                                <input
                                    type="range"
                                    min="5"
                                    max="15"
                                    value={settings.hunterMinScore}
                                    onChange={(e) =>
                                        setSettings({ ...settings, hunterMinScore: Number(e.target.value) })
                                    }
                                    className="w-full h-2 rounded-full bg-muted appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                                />
                            </div>
                            <div className="space-y-2">
                                <div className="flex justify-between">
                                    <label className="text-sm text-muted-foreground">
                                        Tarama Aralığı (dakika)
                                    </label>
                                    <span className="text-sm font-medium">{settings.scanInterval}</span>
                                </div>
                                <input
                                    type="range"
                                    min="5"
                                    max="60"
                                    step="5"
                                    value={settings.scanInterval}
                                    onChange={(e) =>
                                        setSettings({ ...settings, scanInterval: Number(e.target.value) })
                                    }
                                    className="w-full h-2 rounded-full bg-muted appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Notification Toggle */}
                    <div className="flex items-center justify-between rounded-lg border border-border p-4">
                        <div>
                            <p className="text-sm font-medium">Telegram Bildirimleri</p>
                            <p className="text-xs text-muted-foreground">
                                Yeni sinyaller için bildirim gönder
                            </p>
                        </div>
                        <Switch
                            checked={settings.notifications}
                            onCheckedChange={(checked) =>
                                setSettings({ ...settings, notifications: checked })
                            }
                            className="data-[state=checked]:bg-blue-600"
                        />
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
