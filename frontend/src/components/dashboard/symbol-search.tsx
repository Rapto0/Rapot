"use client"

import { useId, useRef, useState, type FormEvent } from "react"
import { useRouter } from "next/navigation"
import { ArrowRight, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function SymbolSearch() {
  const router = useRouter()
  const id = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [market, setMarket] = useState<"BIST" | "Kripto">("BIST")
  const [query, setQuery] = useState("")
  const [error, setError] = useState<string | null>(null)
  const example = market === "BIST" ? "THYAO" : "BTCUSDT"

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const symbol = query.trim().toUpperCase()
    if (!symbol || !/^[A-Z0-9]{1,32}$/.test(symbol)) {
      setError(!symbol
        ? `Bir sembol yazın. Örneğin ${example}.`
        : "Sembol 1–32 harf (A–Z) veya rakam (0–9) içermelidir; boşluk ve noktalama kullanmayın.")
      inputRef.current?.focus()
      return
    }
    setError(null)
    router.push(`/chart?symbol=${encodeURIComponent(symbol)}&market=${market}`)
  }

  return (
    <form role="search" aria-label="Grafik için sembol ara" onSubmit={handleSubmit} noValidate className="w-full min-w-0 space-y-2">
      <div className="grid gap-3 sm:grid-cols-[7.5rem_minmax(0,1fr)_auto] sm:items-end">
        <div className="space-y-2">
          <label htmlFor={`${id}-market`} className="label-uppercase block">Piyasa</label>
          <select
            id={`${id}-market`}
            name="market"
            value={market}
            onChange={(event) => {
              setMarket(event.target.value === "Kripto" ? "Kripto" : "BIST")
              setError(null)
            }}
            className="h-[44px] w-full rounded-sm border border-input bg-input px-3 text-sm text-foreground focus-visible:border-ring focus-visible:outline-none"
          >
            <option value="BIST">BIST</option>
            <option value="Kripto">Kripto</option>
          </select>
        </div>
        <div className="min-w-0 space-y-2">
          <label htmlFor={`${id}-symbol`} className="label-uppercase block">Sembol</label>
          <div className="relative">
            <Search aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              ref={inputRef}
              id={`${id}-symbol`}
              name="symbol"
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                setError(null)
              }}
              aria-invalid={Boolean(error)}
              aria-describedby={`${id}-hint${error ? ` ${id}-error` : ""}`}
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              className="h-[44px] pl-9"
              style={{ fontSize: 16 }}
              placeholder={`Örn. ${example}`}
            />
          </div>
        </div>
        <Button type="submit" className="h-[44px] w-full px-4 sm:w-auto">
          Grafiği aç
          <ArrowRight aria-hidden="true" className="h-4 w-4" />
        </Button>
      </div>
      <p id={`${id}-hint`} className="text-xs text-muted-foreground">
        {market === "BIST" ? "BIST hisse sembolü" : "Kripto işlem çifti"} yazın. Örnek: {example}.
      </p>
      {error && <p id={`${id}-error`} role="alert" className="text-sm text-loss">{error}</p>}
    </form>
  )
}
