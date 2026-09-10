'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { ToastProvider } from '@/components/ui/toast';
import { SidebarProvider } from '@/components/layout/sidebar-context';
import { useSession } from '@/lib/hooks/use-session';
import { ApiError } from '@/lib/api/core';
import { RealtimeBridge } from '@/components/realtime-bridge';
import { cleanupLegacyBrowserSettings } from '@/lib/browser-preferences';

export function Providers({ children }: { children: React.ReactNode }) {
    useEffect(() => { cleanupLegacyBrowserSettings(); }, []);
    const session = useSession();
    const sessionKey = session ? `${session.user.username}:${session.expiresAt}` : 'guest';
    // Remount private component state as well as the cache when the account changes.
    return <SessionProviders key={sessionKey}>{children}</SessionProviders>;
}

function SessionProviders({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: 30 * 1000, // 30 seconds
                        refetchInterval: false, // Disable global auto-refetch; each query sets its own
                        refetchOnWindowFocus: false,
                        retry: (count, error) => !(error instanceof ApiError &&
                            [401, 403, 429].includes(error.status)) && count < 2,
                    },
                },
            })
    );

    useEffect(() => () => {
        void queryClient.cancelQueries();
        queryClient.clear();
    }, [queryClient]);

    return (
        <QueryClientProvider client={queryClient}>
            <RealtimeBridge />
            <SidebarProvider>
                <ToastProvider>
                    {children}
                </ToastProvider>
            </SidebarProvider>
        </QueryClientProvider>
    );
}
