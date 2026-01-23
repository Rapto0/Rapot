'use client';

import { Component, type ErrorInfo, type PropsWithChildren } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorBoundaryState {
    hasError: boolean;
    error?: Error;
}

interface ErrorBoundaryProps extends PropsWithChildren {
    fallback?: React.ReactNode;
    onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    state: ErrorBoundaryState = { hasError: false };

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
        console.error('Dashboard Error:', error, errorInfo);
        this.props.onError?.(error, errorInfo);
        // TODO: Send to error tracking service (Sentry, etc.)
    }

    handleRetry = (): void => {
        this.setState({ hasError: false, error: undefined });
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-yellow-500/10 mb-4">
                        <AlertTriangle className="h-8 w-8 text-yellow-500" />
                    </div>
                    <h2 className="text-xl font-semibold mb-2">Bir şeyler yanlış gitti</h2>
                    <p className="text-muted-foreground text-center max-w-md mb-6">
                        Bu bölüm yüklenirken bir hata oluştu. Sayfayı yenilemeyi deneyin.
                    </p>
                    {this.state.error && (
                        <pre className="text-xs text-muted-foreground bg-muted p-3 rounded-lg mb-6 max-w-md overflow-auto">
                            {this.state.error.message}
                        </pre>
                    )}
                    <Button onClick={this.handleRetry} className="gap-2">
                        <RefreshCw className="h-4 w-4" />
                        Tekrar Dene
                    </Button>
                </div>
            );
        }

        return this.props.children;
    }
}

// Simple error fallback for smaller components
export function ErrorFallback({
    message = "Bir hata oluştu",
    onRetry
}: {
    message?: string;
    onRetry?: () => void;
}) {
    return (
        <div className="flex flex-col items-center justify-center p-6 text-center">
            <AlertTriangle className="h-8 w-8 text-yellow-500 mb-2" />
            <p className="text-sm text-muted-foreground mb-3">{message}</p>
            {onRetry && (
                <Button variant="outline" size="sm" onClick={onRetry}>
                    Tekrar Dene
                </Button>
            )}
        </div>
    );
}

// Empty state component
export function EmptyState({
    icon: Icon,
    title,
    description,
    action,
}: {
    icon?: React.ElementType;
    title: string;
    description?: string;
    action?: React.ReactNode;
}) {
    return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
            {Icon && (
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-4">
                    <Icon className="h-6 w-6 text-muted-foreground" />
                </div>
            )}
            <h3 className="text-lg font-medium mb-1">{title}</h3>
            {description && (
                <p className="text-sm text-muted-foreground max-w-sm mb-4">{description}</p>
            )}
            {action}
        </div>
    );
}
