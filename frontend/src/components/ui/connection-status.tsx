'use client';

import { useConnectionStatus } from '@/lib/hooks/use-websocket';
import { cn } from '@/lib/utils';

interface ConnectionStatusProps {
    className?: string;
    showLabel?: boolean;
}

export function ConnectionStatus({ className, showLabel = true }: ConnectionStatusProps) {
    const { isOnline, apiStatus } = useConnectionStatus();

    // Determine overall status
    const status = !isOnline ? 'offline' : apiStatus;

    const getStatusConfig = () => {
        switch (status) {
            case 'connected':
                return {
                    color: 'text-profit',
                    pulseColor: 'bg-profit',
                    label: 'Bağlı',
                };
            case 'disconnected':
                return {
                    color: 'text-loss',
                    pulseColor: 'bg-loss',
                    label: 'Bağlantı Yok',
                };
            case 'offline':
                return {
                    color: 'text-muted-foreground',
                    pulseColor: 'bg-muted-foreground',
                    label: 'Çevrimdışı',
                };
            case 'checking':
            default:
                return {
                    color: 'text-yellow-500',
                    pulseColor: 'bg-yellow-500',
                    label: 'Kontrol Ediliyor',
                };
        }
    };

    const config = getStatusConfig();

    return (
        <div className={cn('flex items-center gap-2', className)}>
            <div className="relative">
                <div className={cn('h-2 w-2 rounded-full', config.pulseColor)} />
                {status === 'connected' && (
                    <div
                        className={cn(
                            'absolute inset-0 h-2 w-2 rounded-full animate-ping opacity-75',
                            config.pulseColor
                        )}
                    />
                )}
            </div>
            {showLabel && <span className={cn('text-xs', config.color)}>{config.label}</span>}
        </div>
    );
}

// Compact version for header
export function ConnectionDot() {
    const { isOnline, apiStatus } = useConnectionStatus();

    const status = !isOnline ? 'offline' : apiStatus;

    const color = status === 'connected' ? 'bg-profit' : status === 'checking' ? 'bg-yellow-500' : 'bg-loss';

    return (
        <div className="relative">
            <div className={cn('h-2 w-2 rounded-full', color)} />
            {status === 'connected' && (
                <div className={cn('absolute inset-0 h-2 w-2 rounded-full animate-ping opacity-75', color)} />
            )}
        </div>
    );
}
