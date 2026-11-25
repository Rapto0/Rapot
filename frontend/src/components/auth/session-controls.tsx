'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { signOut } from '@/lib/api/auth-api';
import { useSession } from '@/lib/hooks/use-session';

export function SessionControls() {
    const session = useSession();
    const pathname = usePathname();
    const className = 'inline-flex min-h-11 items-center border border-border px-3 text-xs hover:bg-raised md:min-h-8 md:px-2';
    if (!session) {
        return <Link className={className} href={`/login?next=${encodeURIComponent(pathname)}`}>Giriş yap</Link>;
    }
    return (
        <div className="flex items-center gap-2 text-xs">
            <span>{session.user.is_admin ? 'Admin' : session.user.username}</span>
            <button type="button" className={className} onClick={() => { void signOut(); }}>Çıkış yap</button>
        </div>
    );
}
