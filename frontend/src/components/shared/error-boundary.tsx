'use client'

import { Component, type ErrorInfo, type PropsWithChildren } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

interface ErrorBoundaryProps extends PropsWithChildren {
  fallback?: React.ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Dashboard Error:', error, errorInfo)
    this.props.onError?.(error, errorInfo)
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: undefined })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex min-h-[320px] flex-col items-center justify-center border border-border bg-surface p-8">
          <div className="mb-3 flex h-10 w-10 items-center justify-center border border-border bg-base text-neutral">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <h2 className="text-lg font-semibold text-foreground">Bir hata oluştu</h2>
          <p className="mt-2 max-w-md text-center text-xs text-muted-foreground">
            Bu bölüm yüklenirken bir sorun oldu. Sayfayı yeniden deneyin.
          </p>
          {this.state.error ? (
            <pre className="mt-4 max-w-md overflow-auto border border-border bg-base p-3 text-[11px] text-muted-foreground">
              {this.state.error.message}
            </pre>
          ) : null}
          <Button onClick={this.handleRetry} className="mt-4 gap-2" variant="outline">
            <RefreshCw className="h-3.5 w-3.5" />
            Tekrar dene
          </Button>
        </div>
      )
    }

    return this.props.children
  }
}

export function ErrorFallback({
  message = 'Bir hata oluştu',
  onRetry,
}: {
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center border border-border bg-surface p-6 text-center">
      <AlertTriangle className="mb-2 h-5 w-5 text-neutral" />
      <p className="mb-3 text-xs text-muted-foreground">{message}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Tekrar dene
        </Button>
      ) : null}
    </div>
  )
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: React.ElementType
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center border border-border bg-surface p-8 text-center">
      {Icon ? (
        <div className="mb-3 flex h-9 w-9 items-center justify-center border border-border bg-base text-muted-foreground">
          <Icon className="h-4 w-4" />
        </div>
      ) : null}
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {description ? <p className="mt-1 max-w-sm text-xs text-muted-foreground">{description}</p> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  )
}
