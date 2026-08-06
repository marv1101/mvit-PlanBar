import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorBoundary } from './ErrorBoundary'

function ThrowError({ message = 'Test error' }: { message?: string }): React.JSX.Element {
  throw new Error(message)
}

function NoError({ children }: { children: React.ReactNode }) {
  return <div>{children}</div>
}

describe('ErrorBoundary', () => {
  // Suppress React console.error for expected thrown errors in tests
  const originalError = console.error
  beforeEach(() => {
    console.error = vi.fn()
  })
  afterEach(() => {
    console.error = originalError
  })

  it('rendert Children wenn kein Fehler vorliegt', () => {
    render(
      <ErrorBoundary>
        <NoError>Kind-Inhalt</NoError>
      </ErrorBoundary>
    )
    expect(screen.getByText('Kind-Inhalt')).toBeInTheDocument()
  })

  it('zeigt ErrorFallback bei Rendering-Fehler an', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    )
    expect(screen.getByText(/etwas ist schiefgelaufen/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /neu laden/i })).toBeInTheDocument()
  })

  it('ruft onError-Callback mit Error und ErrorInfo auf', () => {
    const onError = vi.fn()
    render(
      <ErrorBoundary onError={onError}>
        <ThrowError message="Callback-Test" />
      </ErrorBoundary>
    )
    expect(onError).toHaveBeenCalledOnce()
    const [error, errorInfo] = onError.mock.calls[0]
    expect(error).toBeInstanceOf(Error)
    expect(error.message).toBe('Callback-Test')
    expect(errorInfo).toHaveProperty('componentStack')
  })

  it('zeigt custom fallback wenn prop gesetzt ist', () => {
    render(
      <ErrorBoundary fallback={<div>Mein Fallback</div>}>
        <ThrowError />
      </ErrorBoundary>
    )
    expect(screen.getByText('Mein Fallback')).toBeInTheDocument()
    expect(screen.queryByText(/etwas ist schiefgelaufen/i)).not.toBeInTheDocument()
  })

  it('setzt Fehler nach Klick auf Neu laden zurück', async () => {
    const user = userEvent.setup()
    let shouldThrow = true

    function ConditionalThrower() {
      if (shouldThrow) {
        throw new Error('Dynamischer Fehler')
      }
      return <div>Erholt!</div>
    }

    render(
      <ErrorBoundary>
        <ConditionalThrower />
      </ErrorBoundary>
    )

    // Fehler wird angezeigt
    expect(screen.getByText(/etwas ist schiefgelaufen/i)).toBeInTheDocument()

    // Fehler wird behoben, dann "Neu laden" geklickt
    shouldThrow = false
    await user.click(screen.getByRole('button', { name: /neu laden/i }))

    // Kind-Komponente wird neu gerendert
    expect(screen.getByText('Erholt!')).toBeInTheDocument()
  })

  it('zeigt Fehler-Details nur im DEV-Modus', () => {
    vi.stubEnv('DEV', true)
    render(
      <ErrorBoundary>
        <ThrowError message="Dev-Details-Test" />
      </ErrorBoundary>
    )
    expect(screen.getByText(/Dev-Details-Test/)).toBeInTheDocument()
    vi.unstubAllEnvs()
  })

  it('versteckt Fehler-Details im Produktionsmodus', () => {
    vi.stubEnv('DEV', false)
    render(
      <ErrorBoundary>
        <ThrowError message="Secret-Info" />
      </ErrorBoundary>
    )
    expect(screen.queryByText('Secret-Info')).not.toBeInTheDocument()
    expect(screen.getByText(/etwas ist schiefgelaufen/i)).toBeInTheDocument()
    vi.unstubAllEnvs()
  })
})
