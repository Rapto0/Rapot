"use client"

import { useEffect, useRef, useState, type FormEvent } from "react"
import { useQuery } from "@tanstack/react-query"
import { CheckCircle2, KeyRound, RefreshCw, Trash2 } from "lucide-react"
import { ActionDialog } from "@/components/ui/action-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { clearResearchConnection, fetchResearchConnection, saveResearchConnection, verifyResearchConnection, type ResearchSecrets } from "@/lib/api/borsapy-api"
import { getSession } from "@/lib/auth/session"
import { researchError } from "./research-utils"

const EMPTY = { session: "", session_sign: "", evds_key: "", twitter_auth_token: "", twitter_ct0: "" }
export function ConnectionPanel({ sessionKey }: { sessionKey: string }) {
    const connection = useQuery({ queryKey: ["borsapy-connection", sessionKey], queryFn: ({ signal }) => fetchResearchConnection(signal), retry: false })
    const [draft, setDraft] = useState({ ...EMPTY })
    const [pending, setPending] = useState(false)
    const [error, setError] = useState("")
    const [notice, setNotice] = useState("")
    const [confirmClear, setConfirmClear] = useState(false)
    const request = useRef<AbortController | null>(null)
    useEffect(() => () => request.current?.abort(), [])
    async function perform(operation: (signal: AbortSignal) => Promise<unknown>, message: string) {
        if (request.current) return
        const controller = new AbortController()
        request.current = controller
        setPending(true); setError(""); setNotice("")
        const canContinue = () => {
            const current = getSession()
            return !controller.signal.aborted && current?.user.is_admin && !current.user.disabled
                && current.expiresAt > Date.now() && `${current.user.username}:${current.expiresAt}` === sessionKey
        }
        try {
            let failure: unknown
            let failed = false
            try { await operation(controller.signal) }
            catch (cause) { failed = true; failure = cause }
            if (!canContinue()) return
            const failureStatus = typeof failure === "object" && failure !== null && "status" in failure ? failure.status : null
            if (failureStatus === 401 || failureStatus === 403) { setError(researchError(failure)); return }

            // A provider rejection can occur after the credentials were saved. Refresh the
            // shared status on either outcome, without automatically retrying authentication.
            const failureMessage = failed ? researchError(failure) : ""
            try {
                const refreshed = await connection.refetch()
                if (!canContinue()) return
                if (refreshed.isError || !refreshed.data) throw new Error("Status unavailable")
                const latest = refreshed.data
                if (latest.state === "storage_error") {
                    setError(`${failureMessage} Bağlantı kaydının durumu alınamadı. Durumu yenileyip tekrar kontrol edin.`.trim())
                } else if (failed) {
                    setError(failureStatus === 409 && latest.configured && latest.state === "auth_needed"
                        ? "Bağlantı bilgileri sunucuda kayıtlı; TradingView oturumu doğrulanamadı. Oturumu doğrula ile tekrar deneyebilirsiniz."
                        : failureMessage)
                } else {
                    setNotice(message); setConfirmClear(false)
                }
            } catch {
                if (canContinue()) setError(`${failureMessage} Güncel bağlantı durumu alınamadı. Durumu yenileyip tekrar kontrol edin.`.trim())
            }
        } finally {
            if (canContinue()) { setDraft({ ...EMPTY }); setPending(false) }
            if (request.current === controller) request.current = null
        }
    }
    function submit(event: FormEvent) {
        event.preventDefault()
        if (Boolean(draft.session.trim()) !== Boolean(draft.session_sign.trim())) { setError("TradingView oturumu ve imza alanlarını birlikte doldurun."); return }
        if (Boolean(draft.twitter_auth_token.trim()) !== Boolean(draft.twitter_ct0.trim())) { setError("X erişim bilgisi ve ct0 alanlarını birlikte doldurun."); return }
        const secrets = Object.fromEntries(Object.entries(draft).filter(([, value]) => value.trim()).map(([key, value]) => [key, value.trim()])) as ResearchSecrets
        if (!Object.keys(secrets).length) { setError("Kaydetmek için en az bir bağlantı bilgisi girin."); return }
        setDraft({ ...EMPTY })
        void perform(signal => saveResearchConnection(secrets, signal), "Bağlantı bilgileri sunucuya gönderildi. Güncel doğrulama durumu aşağıda.")
    }
    const storageUnavailable = connection.data?.state === "storage_error"
    const status = connection.isError || storageUnavailable ? undefined : connection.data
    const field = (name: keyof typeof EMPTY, label: string) => <label className="block space-y-1 text-sm"><span>{label}</span><Input type="password" name={name} autoComplete="new-password" spellCheck={false} value={draft[name]} onChange={event => setDraft(current => ({ ...current, [name]: event.target.value }))} className="min-h-11" placeholder="Yeni bilgi girin" maxLength={4096} /></label>
    return <section className="space-y-4" aria-labelledby="connections-title">
        <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 id="connections-title" className="flex items-center gap-2 text-[16px] text-foreground font-semibold"><KeyRound className="h-4 w-4" aria-hidden="true" />Veri bağlantıları</h2><p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted-foreground">Yalnız kullanma yetkiniz olan hesap bilgilerini girin. Kaydedilen bilgiler geri gösterilmez. Boş bıraktığınız alanlar mevcut kaydı korur.</p></div><Button className="min-h-11" variant="outline" disabled={connection.isFetching || pending} onClick={() => void connection.refetch()}><RefreshCw aria-hidden="true" />Durumu yenile</Button></div>
        {connection.isLoading && <p role="status" className="text-sm text-muted-foreground">Bağlantılar kontrol ediliyor…</p>}
        {connection.isError && <p role="alert" className="text-sm text-loss">Bağlantı durumu alınamadı. {researchError(connection.error)}</p>}
        {storageUnavailable && <p role="alert" className="text-sm text-loss">Bağlantı kaydının durumu alınamadı. Durumu yenileyip tekrar kontrol edin.</p>}
        {status && <><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{[
            ["Borsapy", status.installed ? `Kurulu · ${status.version ?? "sürüm bilinmiyor"}` : "Sunucuda kurulu değil", status.installed],
            ["TradingView", status.authenticated ? "Oturum doğrulandı" : status.configured ? "Kayıtlı · doğrulanmadı" : "Yapılandırılmadı", status.authenticated],
            ["TCMB EVDS", status.evds_configured ? "Anahtar kayıtlı" : "Yapılandırılmadı", status.evds_configured],
            ["X / Twitter", status.twitter_configured ? "Bilgiler kayıtlı" : "Yapılandırılmadı", status.twitter_configured],
        ].map(([name, value, good]) => <div className="border border-border bg-surface p-4" key={String(name)}><p className="text-xs text-muted-foreground">{name}</p><p className="mt-2 flex items-center gap-2 text-sm">{good && <CheckCircle2 className="h-4 w-4 shrink-0 text-profit" aria-hidden="true" />}{value}</p></div>)}</div><p role="status" className="border border-border bg-raised/40 p-3 text-sm">{status.message || "Durum bilgisi alındı."}</p></>}
        <p className="text-xs leading-relaxed text-muted-foreground">Oturum doğrulaması, gerçek zamanlı BIST veri yetkisini veya canlı piyasa testini doğrulamaz. Erişim sağlayıcıdaki hesabınızın yetkilerine bağlıdır.</p>
        {error && <p role="alert" className="border border-loss/40 bg-loss/5 p-3 text-sm text-loss">{error}</p>}
        {notice && <p role="status" className="border border-border p-3 text-sm">{notice}</p>}
        <form onSubmit={submit} aria-busy={pending} className="space-y-4">
            <fieldset disabled={pending} className="grid min-w-0 gap-4 lg:grid-cols-3">
                <section className="space-y-3 border border-border bg-surface p-4"><h3 className="text-sm font-medium">TradingView</h3><p className="text-xs text-muted-foreground">Mevcut oturumunuzun iki bilgisi birlikte kullanılır.</p>{field("session", "Oturum bilgisi (session)")}{field("session_sign", "Oturum imzası (session_sign)")}</section>
                <section className="space-y-3 border border-border bg-surface p-4"><h3 className="text-sm font-medium">TCMB EVDS</h3><p className="text-xs text-muted-foreground">Makro veri sorguları için kendi EVDS anahtarınız.</p>{field("evds_key", "EVDS API anahtarı")}</section>
                <section className="space-y-3 border border-border bg-surface p-4"><h3 className="text-sm font-medium">X / Twitter</h3><p className="text-xs text-muted-foreground">X aramaları için sunucudaki isteğe bağlı sağlayıcı kullanılır.</p>{field("twitter_auth_token", "X erişim bilgisi (auth_token)")}{field("twitter_ct0", "X oturum doğrulaması (ct0)")}</section>
            </fieldset>
            <div className="flex flex-wrap gap-2"><Button type="submit" className="min-h-11" disabled={pending}>{pending ? "İşleniyor…" : "Bağlantıları kaydet"}</Button><Button type="button" variant="outline" className="min-h-11" disabled={pending || !status?.configured} onClick={() => void perform(signal => verifyResearchConnection(signal), "TradingView oturumu yeniden kontrol edildi.")}><RefreshCw aria-hidden="true" />Oturumu doğrula</Button><Button type="button" variant="ghost" className="min-h-11 text-loss" disabled={pending || !connection.data} onClick={() => setConfirmClear(true)}><Trash2 aria-hidden="true" />Bağlantıları kaldır</Button></div>
        </form>
        <ActionDialog open={confirmClear} title="Veri bağlantılarını kaldır" description="Kayıtlı TradingView, EVDS ve X bilgileri silinir; açık veri akışı kapatılır." confirmLabel="Bağlantıları kaldır" cancelLabel="Vazgeç" variant="danger" pending={pending} onCancel={() => setConfirmClear(false)} onConfirm={() => void perform(signal => clearResearchConnection(signal), "Bağlantı bilgileri kaldırıldı.")} />
    </section>
}
