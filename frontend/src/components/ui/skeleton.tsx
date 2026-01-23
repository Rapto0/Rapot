import { cn } from "@/lib/utils"

function Skeleton({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn("animate-pulse rounded-md bg-muted", className)}
            {...props}
        />
    )
}

// Common skeleton patterns
function SkeletonCard({ className }: { className?: string }) {
    return (
        <div className={cn("rounded-lg border border-border bg-card p-4", className)}>
            <div className="space-y-3">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-8 w-1/2" />
                <Skeleton className="h-4 w-1/4" />
            </div>
        </div>
    )
}

function SkeletonKPICard() {
    return (
        <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-start justify-between">
                <div className="space-y-2 flex-1">
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-7 w-24" />
                    <Skeleton className="h-3 w-16" />
                </div>
                <Skeleton className="h-10 w-10 rounded-lg" />
            </div>
        </div>
    )
}

function SkeletonTableRow() {
    return (
        <div className="flex items-center gap-4 py-4 px-4 border-b border-border">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-5 w-12 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-24" />
        </div>
    )
}

function SkeletonChart({ className }: { className?: string }) {
    return (
        <div className={cn("rounded-lg border border-border bg-card p-4", className)}>
            <div className="flex items-center justify-between mb-4">
                <Skeleton className="h-5 w-32" />
                <div className="flex gap-2">
                    <Skeleton className="h-8 w-12" />
                    <Skeleton className="h-8 w-12" />
                    <Skeleton className="h-8 w-12" />
                </div>
            </div>
            <Skeleton className="h-64 w-full" />
        </div>
    )
}

export {
    Skeleton,
    SkeletonCard,
    SkeletonKPICard,
    SkeletonTableRow,
    SkeletonChart
}
