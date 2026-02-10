import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-sm border border-border bg-background text-xs font-medium tracking-[0.04em] transition-colors focus-visible:outline-none focus-visible:border-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
    {
        variants: {
            variant: {
                default: "bg-raised text-foreground hover:bg-overlay",
                destructive: "border-loss bg-loss/10 text-loss hover:bg-loss/20",
                outline: "bg-background text-foreground hover:bg-muted",
                secondary: "bg-muted text-foreground hover:bg-overlay",
                ghost: "border-transparent bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground",
                link: "border-transparent bg-transparent p-0 text-foreground underline-offset-4 hover:underline",
                profit: "border-profit bg-profit/10 text-profit hover:bg-profit/20",
                loss: "border-loss bg-loss/10 text-loss hover:bg-loss/20",
            },
            size: {
                default: "h-8 px-3 py-1.5",
                sm: "h-7 px-2.5 py-1 text-[10px]",
                lg: "h-9 px-4 py-2 text-sm",
                icon: "h-8 w-8 p-0",
            },
        },
        defaultVariants: {
            variant: "default",
            size: "default",
        },
    }
)

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
    asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant, size, asChild = false, ...props }, ref) => {
        const Comp = asChild ? Slot : "button"
        return (
            <Comp
                className={cn(buttonVariants({ variant, size, className }))}
                ref={ref}
                {...props}
            />
        )
    }
)
Button.displayName = "Button"

export { Button, buttonVariants }
