"use client"

import { useEffect, useId, useRef } from "react"
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
  const dialogRef = useRef<HTMLDialogElement>(null)
  const id = useId()
  const titleId = `${id}-title`
  const descriptionId = description ? `${id}-description` : undefined

  useEffect(() => {
    const dialog = dialogRef.current
    if (!open || !dialog) return

    const previousFocus = document.activeElement
    // showModal keeps keyboard focus inside the dialog and makes the page inert.
    if (!dialog.open) dialog.showModal()
    const initialFocus = dialog.querySelector<HTMLElement>("input:not(:disabled), button:not(:disabled)")
    initialFocus?.focus()

    return () => {
      if (dialog.open) dialog.close()
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) {
        previousFocus.focus()
      }
    }
  }, [open])

  if (!open) return null

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      aria-busy={pending}
      onCancel={(event) => {
        event.preventDefault()
        if (!pending) onCancel()
      }}
      onKeyDown={(event) => {
        if (event.key !== "Tab") return
        const controls = event.currentTarget.querySelectorAll<HTMLElement>("input:not(:disabled), button:not(:disabled)")
        const first = controls[0]
        const last = controls[controls.length - 1]
        const focused = event.currentTarget.ownerDocument.activeElement
        if (!first) {
          event.preventDefault()
        } else if (event.shiftKey && focused === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && focused === last) {
          event.preventDefault()
          first.focus()
        }
      }}
      className="m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-md overflow-y-auto border border-border bg-surface p-0 text-foreground backdrop:bg-black/55"
    >
      <form
        className="p-4"
        onSubmit={(event) => {
          event.preventDefault()
          if (!pending) onConfirm()
        }}
      >
        <div className="mb-3 flex items-start gap-2">
          {variant === "danger" ? (
            <div className="mt-0.5 flex h-6 w-6 items-center justify-center border border-loss/40 bg-loss/10 text-loss">
              <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
            </div>
          ) : null}
          <div>
            <h2 id={titleId} className="text-sm font-semibold text-foreground">{title}</h2>
            {description ? <p id={descriptionId} className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
          </div>
        </div>

        {mode === "prompt" ? (
          <Input
            value={value}
            onChange={(event) => onValueChange?.(event.target.value)}
            placeholder={placeholder}
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
            className={cn("h-[44px] text-foreground", pending && "opacity-70")}
            style={{ fontSize: 16 }}
            disabled={pending}
          />
        ) : null}

        <div className="mt-4 flex items-center justify-end gap-2">
          <Button type="button" size="sm" variant="outline" className="min-h-[44px] px-3 text-sm" onClick={() => { if (!pending) onCancel() }} disabled={pending}>
            {cancelLabel}
          </Button>
          <Button
            type="submit"
            size="sm"
            variant={variant === "danger" ? "destructive" : "outline"}
            className="min-h-[44px] px-3 text-sm"
            disabled={pending}
          >
            {confirmLabel}
          </Button>
        </div>
      </form>
    </dialog>
  )
}
