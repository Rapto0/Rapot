export default function HealthLoading() {
  return (
    <div className="mx-auto flex w-full max-w-[1700px] flex-col gap-3 p-3 md:p-4">
      <section className="border border-border bg-surface p-4">
        <div className="h-5 w-44 animate-pulse border border-border bg-base" />
        <div className="mt-2 h-3 w-64 animate-pulse border border-border bg-base" />
      </section>
      <section className="grid gap-3 lg:grid-cols-2">
        <div className="min-h-[320px] border border-border bg-surface p-3">
          <div className="space-y-2">
            {Array.from({ length: 7 }).map((_, index) => (
              <div key={`health-logs-loading-${index}`} className="h-6 animate-pulse border border-border bg-base" />
            ))}
          </div>
        </div>
        <div className="min-h-[320px] border border-border bg-surface p-3">
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={`health-scans-loading-${index}`} className="h-7 animate-pulse border border-border bg-base" />
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
