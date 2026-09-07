'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clearSession } from '@/lib/auth/session';
import { useSession } from '@/lib/hooks/use-session';

export function SessionControls() {
    const session = useSession();
    const pathname = usePathname();
    const className = 'border border-border px-2 py-1 text-xs hover:bg-raised';
    if (!session) {
        return <Link className={className} href={`/login?next=${encodeURIComponent(pathname)}`}>Giriş yap</Link>;
    }
    return (
        <div className="flex items-center gap-2 text-xs">
            <span>{session.user.is_admin ? 'Admin' : session.user.username}</span>
            <button type="button" className={className} onClick={() => clearSession()}>Çıkış yap</button>
        </div>
    );
}
