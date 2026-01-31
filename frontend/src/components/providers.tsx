'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { ToastProvider } from '@/components/ui/toast';
import { SidebarProvider } from '@/components/layout/sidebar-context';

export function Providers({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: 10 * 1000, // 10 seconds
                        refetchInterval: 30 * 1000, // 30 seconds
                        refetchOnWindowFocus: true,
                        retry: 2,
                    },
                },
            })
    );

    return (
        <QueryClientProvider client={queryClient}>
            <SidebarProvider>
                <ToastProvider>
                    {children}
                </ToastProvider>
            </SidebarProvider>
        </QueryClientProvider>
    );
}
