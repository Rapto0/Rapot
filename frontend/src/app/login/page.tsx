'use client';

import { useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { signIn } from '@/lib/api/auth-api';
import { ApiError } from '@/lib/api/core';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PageShell } from '@/components/ui/page-shell';

export default function LoginPage() {
    const router = useRouter();
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
            // Restrict the return destination to this origin; never redirect to an external URL.
            const next = new URLSearchParams(window.location.search).get('next') || '/';
            let returnTo = '/';
            try {
                const destination = new URL(next, window.location.origin);
                if (destination.origin === window.location.origin && destination.pathname !== '/login') {
                    returnTo = destination.pathname + destination.search + destination.hash;
                }
            } catch {
                // A malformed return URL must not turn a successful login into an error.
            }
            router.replace(returnTo);
        } catch (cause) {
            setError(cause instanceof ApiError && cause.status === 401
                ? 'Kullanıcı adı veya şifre hatalı.'
                : cause instanceof Error ? cause.message : 'Giriş yapılamadı.');
        } finally {
            setPassword('');
            setPending(false);
        }
    }

    return (
        <PageShell label="Hesap" title="Giriş yap" description="AI analizi için giriş yapın. Loglar ve manuel tarama admin yetkisi gerektirir.">
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
                <p className="text-xs text-muted-foreground">Sayfayı yenilediğinizde veya oturum süreniz dolduğunda tekrar giriş yapmanız gerekir.</p>
            </form>
        </PageShell>
    );
}
