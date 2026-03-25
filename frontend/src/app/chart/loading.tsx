export default function ChartLoading() {
  return (
    <div className="flex h-full min-h-[420px] items-center justify-center border border-border bg-surface px-4">
      <div className="space-y-3 text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
        <p className="text-xs text-muted-foreground">Grafik çalışma alanı yükleniyor...</p>
      </div>
    </div>
  )
}
