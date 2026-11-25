"use client"

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html lang="tr" className="dark">
      <body className="flex min-h-screen items-center justify-center bg-[#08080c] p-4 font-sans text-[#e8e8ec]">
        <div className="w-full max-w-lg space-y-4 border border-[#ef4444]/40 bg-[#0c0c12] p-5">
          <h1 className="text-base font-semibold text-[#ef4444]">Uygulama beklenmeyen bir hata ile karşılaştı</h1>
          <p className="text-xs leading-5 text-white/70">
            {error?.message || "Oturumunuz veya sunucu alarmlarınız bundan etkilenmez. Sayfayı yeniden deneyin."}
          </p>
          <button
            type="button"
            onClick={reset}
            className="inline-flex min-h-11 items-center border border-white/15 bg-[#111118] px-4 text-xs text-white hover:bg-[#16161e]"
          >
            Yeniden yükle
          </button>
        </div>
      </body>
    </html>
  )
}
