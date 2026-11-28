'use client';

import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { signIn } from '@/lib/api/auth-api';
import { ApiError } from '@/lib/api/core';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PageShell } from '@/components/ui/page-shell';
import { useSession } from '@/lib/hooks/use-session';

function returnDestination(search: string, origin: string) {
    try {
        const next = new URLSearchParams(search).get('next') || '/';
        const destination = new URL(next, origin);
        const path = decodeURIComponent(destination.pathname);
        if (destination.origin === origin && !path.startsWith('//') && !path.startsWith('/\\')
            && path.replace(/\/+$/, '') !== '/login') {
            return destination.pathname + destination.search + destination.hash;
        }
    } catch { /* A malformed return URL falls back to the home page. */ }
    return '/';
}

export default function LoginPage() {
    const router = useRouter();
    const session = useSession();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [pending, setPending] = useState(false);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (pending) return;
        setPending(true);
        setError('');
        try {
            await signIn(username.trim(), password);
            router.replace(returnDestination(window.location.search, window.location.origin));
        } catch (cause) {
            setError(cause instanceof ApiError && cause.status === 401
                ? 'Kullanıcı adı veya şifre hatalı.'
                : cause instanceof Error ? cause.message : 'Giriş yapılamadı.');
        } finally {
            setPassword('');
            setPending(false);
        }
    }

    if (session && typeof window !== 'undefined') return (
        <PageShell label="Hesap" title="Oturum açık" description="Rapot oturumunuz etkin.">
            <Link href={returnDestination(window.location.search, window.location.origin)} className="inline-flex min-h-11 items-center text-sm text-primary underline">Terminale dön</Link>
        </PageShell>
    );

    return (
        <PageShell label="Hesap" title="Giriş yap" description="Kişisel terminalinize yönetici hesabınızla giriş yapın. Piyasa verileri, grafikler, tarayıcı, ekonomik takvim, araştırmalar ve alarm yönetimi özel erişim gerektirir.">
            <form onSubmit={submit} className="mx-auto flex w-full max-w-sm flex-col gap-4 border border-border bg-surface p-5">
                <label className="space-y-2 text-sm">
                    <span>Kullanıcı adı</span>
                    <Input name="username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required disabled={pending} />
                </label>
                <label className="space-y-2 text-sm">
                    <span>Şifre</span>
                    <Input name="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required disabled={pending} />
                </label>
                {error && <p role="alert" className="text-sm text-loss">{error}</p>}
                <Button type="submit" disabled={pending}>{pending ? 'Giriş yapılıyor…' : 'Giriş yap'}</Button>
                <p className="text-xs text-muted-foreground">Oturumunuz güvenli HttpOnly çerez ile korunur; sayfa yenilemelerinde ve yeni sekmelerde oturum süreniz dolana kadar geçerlidir.</p>
            </form>
        </PageShell>
    );
}
