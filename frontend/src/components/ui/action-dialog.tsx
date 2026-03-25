"use client"

import { useEffect } from "react"
import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

interface ActionDialogProps {
  open: boolean
  title: string
  description?: string
  mode?: "confirm" | "prompt"
  variant?: "default" | "danger"
  value?: string
  placeholder?: string
  confirmLabel?: string
  cancelLabel?: string
  pending?: boolean
  onValueChange?: (value: string) => void
  onConfirm: () => void
  onCancel: () => void
}

export function ActionDialog({
  open,
  title,
  description,
  mode = "confirm",
  variant = "default",
  value = "",
  placeholder,
  confirmLabel = "Onayla",
  cancelLabel = "Vazgec",
  pending = false,
  onValueChange,
  onConfirm,
  onCancel,
}: ActionDialogProps) {
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/55 p-3">
      <div className="w-full max-w-md border border-border bg-surface p-4">
        <div className="mb-3 flex items-start gap-2">
          {variant === "danger" ? (
            <div className="mt-0.5 flex h-6 w-6 items-center justify-center border border-loss/40 bg-loss/10 text-loss">
              <AlertTriangle className="h-3.5 w-3.5" />
            </div>
          ) : null}
          <div>
            <h2 className="text-sm font-semibold text-foreground">{title}</h2>
            {description ? <p className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
          </div>
        </div>

        {mode === "prompt" ? (
          <Input
            value={value}
            onChange={(event) => onValueChange?.(event.target.value)}
            placeholder={placeholder}
            className={cn("h-9 text-xs", pending && "opacity-70")}
            disabled={pending}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                onConfirm()
              }
            }}
          />
        ) : null}

        <div className="mt-4 flex items-center justify-end gap-2">
          <Button type="button" size="sm" variant="outline" className="h-8 text-xs" onClick={onCancel} disabled={pending}>
            {cancelLabel}
          </Button>
          <Button
            type="button"
            size="sm"
            variant={variant === "danger" ? "destructive" : "outline"}
            className="h-8 text-xs"
            onClick={onConfirm}
            disabled={pending}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
