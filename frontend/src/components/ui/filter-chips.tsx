import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface FilterChipOption<T extends string> {
  value: T
  label: string
}

interface FilterChipsProps<T extends string> {
  label: string
  options: readonly FilterChipOption<T>[]
  value: T
  onChange: (value: T) => void
  className?: string
}

function FilterChips<T extends string>({
  label,
  options,
  value,
  onChange,
  className,
}: FilterChipsProps<T>) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="flex items-center gap-1">
        {options.map((option) => (
          <Button
            key={option.value}
            type="button"
            size="sm"
            variant={value === option.value ? "default" : "outline"}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </Button>
        ))}
      </div>
    </div>
  )
}

export type { FilterChipOption }
export { FilterChips }
