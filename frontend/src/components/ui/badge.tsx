import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
    "inline-flex items-center rounded-sm border px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em] uppercase transition-colors focus:outline-none focus:ring-0",
    {
        variants: {
            variant: {
                default: "border-border bg-muted text-foreground",
                secondary: "border-border bg-muted text-muted-foreground",
                destructive: "border-loss bg-loss/10 text-loss",
                outline: "border-border bg-transparent text-foreground",
                profit: "border-profit bg-profit/10 text-profit",
                loss: "border-loss bg-loss/10 text-loss",
                long: "border-profit bg-profit/10 text-profit",
                short: "border-loss bg-loss/10 text-loss",
                bist: "border-border bg-muted text-foreground",
                crypto: "border-border bg-muted text-foreground",
                combo: "border-border bg-muted text-foreground",
                hunter: "border-border bg-muted text-foreground",
            },
        },
        defaultVariants: {
            variant: "default",
        },
    }
)

export interface BadgeProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
    return (
        <div className={cn(badgeVariants({ variant }), className)} {...props} />
    )
}

export { Badge, badgeVariants }
