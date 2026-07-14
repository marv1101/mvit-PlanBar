import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RotateCw } from 'lucide-react'

interface ErrorFallbackProps {
  error: Error
  resetErrorBoundary: () => void
}

function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Etwas ist schiefgelaufen
        </h2>
        <p className="text-gray-600 mb-6">
          Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es erneut.
        </p>
        {import.meta.env.DEV && (
          <pre className="text-left text-xs bg-gray-100 p-3 rounded mb-4 overflow-auto max-h-40 text-red-600">
            {error.message}
            {error.stack && `\n\n${error.stack}`}
          </pre>
        )}
        <button
          onClick={resetErrorBoundary}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RotateCw className="h-4 w-4" />
          Neu laden
        </button>
      </div>
    </div>
  )
}

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.props.onError?.(error, errorInfo)
  }

  handleReset = () => {
    this.setState({ error: null })
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback
      return (
        <ErrorFallback
          error={this.state.error}
          resetErrorBoundary={this.handleReset}
        />
      )
    }
    return this.props.children
  }
}
