"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Check, Eye, EyeOff, Save } from "lucide-react"

export default function SettingsPage() {
  const [showApiKey, setShowApiKey] = useState(false)
  const [showTelegramToken, setShowTelegramToken] = useState(false)
  const [saved, setSaved] = useState(false)

  const [settings, setSettings] = useState({
    telegramChatId: "123456789",
    telegramToken: "bot1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
    binanceApiKey: "aBcDeFgHiJkLmNoPqRsTuVwXyZ123456",
    binanceSecretKey: "aBcDeFgHiJkLmNoPqRsTuVwXyZ789012",
    rsiOversold: 30,
    rsiOverbought: 70,
    hunterMinScore: 10,
    scanInterval: 30,
    notifications: true,
  })

  const handleSave = () => {
    setSaved(true)
    window.setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-3 p-3">
      <section className="border border-border bg-surface p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label-uppercase">Ayarlar</div>
            <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em]">Bot ve strateji parametreleri</h1>
            <p className="mt-1 text-xs text-muted-foreground">API anahtarları, bildirimler ve temel eşik değerleri.</p>
          </div>
          <Button onClick={handleSave} variant="outline" className="gap-1.5">
            {saved ? <Check className="h-3.5 w-3.5" /> : <Save className="h-3.5 w-3.5" />}
            {saved ? "Kaydedildi" : "Kaydet"}
          </Button>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <ConfigPanel title="Telegram">
          <Field label="Chat ID">
            <Input
              value={settings.telegramChatId}
              onChange={(event) => setSettings({ ...settings, telegramChatId: event.target.value })}
              placeholder="Telegram Chat ID"
            />
          </Field>

          <Field label="Bot Token">
            <SecretInput
              value={settings.telegramToken}
              show={showTelegramToken}
              onToggle={() => setShowTelegramToken((prev) => !prev)}
              onChange={(value) => setSettings({ ...settings, telegramToken: value })}
            />
          </Field>
        </ConfigPanel>

        <ConfigPanel title="Binance API">
          <Field label="API Key">
            <SecretInput
              value={settings.binanceApiKey}
              show={showApiKey}
              onToggle={() => setShowApiKey((prev) => !prev)}
              onChange={(value) => setSettings({ ...settings, binanceApiKey: value })}
            />
          </Field>

          <Field label="Secret Key">
            <Input
              type="password"
              value={settings.binanceSecretKey}
              onChange={(event) => setSettings({ ...settings, binanceSecretKey: event.target.value })}
            />
          </Field>
        </ConfigPanel>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <ConfigPanel title="RSI Eşikleri">
          <RangeField
            label="Aşırı satım"
            min={10}
            max={40}
            value={settings.rsiOversold}
            onChange={(value) => setSettings({ ...settings, rsiOversold: value })}
          />
          <RangeField
            label="Aşırı alım"
            min={60}
            max={90}
            value={settings.rsiOverbought}
            onChange={(value) => setSettings({ ...settings, rsiOverbought: value })}
          />
        </ConfigPanel>

        <ConfigPanel title="HUNTER Ayarları">
          <RangeField
            label="Minimum skor"
            min={5}
            max={15}
            value={settings.hunterMinScore}
            onChange={(value) => setSettings({ ...settings, hunterMinScore: value })}
          />
          <RangeField
            label="Tarama aralığı (dk)"
            min={5}
            max={60}
            step={5}
            value={settings.scanInterval}
            onChange={(value) => setSettings({ ...settings, scanInterval: value })}
          />
        </ConfigPanel>
      </section>

      <section className="border border-border bg-surface p-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold">Telegram bildirimleri</div>
            <div className="text-xs text-muted-foreground">Yeni sinyaller geldiğinde bildirim gönder.</div>
          </div>
          <Switch
            checked={settings.notifications}
            onCheckedChange={(checked) => setSettings({ ...settings, notifications: checked })}
          />
        </div>
      </section>
    </div>
  )
}

function ConfigPanel({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="border border-border bg-surface p-3">
      <div className="mb-3 border-b border-border pb-2">
        <span className="label-uppercase">{title}</span>
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
    </label>
  )
}

function SecretInput({
  value,
  show,
  onToggle,
  onChange,
}: {
  value: string
  show: boolean
  onToggle: () => void
  onChange: (value: string) => void
}) {
  return (
    <div className="relative">
      <Input
        type={show ? "text" : "password"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="pr-8"
      />
      <button
        type="button"
        onClick={onToggle}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        aria-label="Göster/Gizle"
      >
        {show ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
      </button>
    </div>
  )
}

function RangeField({
  label,
  min,
  max,
  step = 1,
  value,
  onChange,
}: {
  label: string
  min: number
  max: number
  step?: number
  value: number
  onChange: (value: number) => void
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="mono-numbers text-foreground">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none border border-border bg-base"
      />
    </div>
  )
}
