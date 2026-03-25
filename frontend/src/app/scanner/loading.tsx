export default function ScannerLoading() {
  return (
    <div className="mx-auto flex w-full max-w-[1900px] flex-col gap-3 px-3 py-3 md:px-4">
      <section className="border border-border bg-surface p-4">
        <div className="h-5 w-44 animate-pulse border border-border bg-base" />
        <div className="mt-2 h-3 w-72 animate-pulse border border-border bg-base" />
      </section>
      <section className="border border-border bg-surface p-3">
        <div className="space-y-2">
          {Array.from({ length: 10 }).map((_, index) => (
            <div key={`scanner-loading-${index}`} className="h-7 animate-pulse border border-border bg-base" />
          ))}
        </div>
      </section>
    </div>
  )
}
