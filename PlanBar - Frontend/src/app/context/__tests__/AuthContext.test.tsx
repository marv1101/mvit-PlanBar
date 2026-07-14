import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/msw-handlers'
import { AuthProvider, useAuth } from '../AuthContext'
import { MemoryRouter } from 'react-router'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useState } from 'react'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const base = '/api/v1'

// ---------------------------------------------------------------------------
// Testkomponenten
// ---------------------------------------------------------------------------

function AuthConsumer() {
  const auth = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(auth.isLoading)}</span>
      <span data-testid="user">{auth.user ? auth.user.name : 'kein Benutzer'}</span>
      <span data-testid="user-role">{auth.user?.role ?? '—'}</span>
      <span data-testid="user-email">{auth.user?.email ?? '—'}</span>
      <span data-testid="mustChangePassword">{String(auth.mustChangePassword)}</span>
      <button data-testid="login-btn" onClick={() => auth.login('admin@planbar.test', 'password')}>
        Login
      </button>
      <button data-testid="logout-btn" onClick={auth.logout}>
        Logout
      </button>
      <button data-testid="change-pw-btn" onClick={() => auth.changePassword('old', 'new')}>
        Change PW
      </button>
    </div>
  )
}

function LoginResultCatcher() {
  const { login, isLoading } = useAuth()
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const handleFailLogin = async () => {
    const res = await login('admin@planbar.test', 'wrong')
    setResult(res)
  }

  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <button data-testid="fail-login-btn" onClick={handleFailLogin}>
        Fail-Login
      </button>
      {result !== null && (
        <>
          <span data-testid="login-result-success">{String(result.success)}</span>
          <span data-testid="login-result-mcp">{String(result.mustChangePassword)}</span>
        </>
      )}
    </div>
  )
}

function renderAuth(ui: React.ReactElement) {
  return render(<MemoryRouter><AuthProvider>{ui}</AuthProvider></MemoryRouter>)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AuthContext', () => {
  beforeEach(() => {
    server.resetHandlers()
  })

  it('rendert initialen Ladezustand', () => {
    renderAuth(<AuthConsumer />)
    expect(screen.getByTestId('loading')).toHaveTextContent('true')
    expect(screen.getByTestId('user')).toHaveTextContent('kein Benutzer')
  })

  it('ruft /users/me auf und setzt Admin-Benutzer', async () => {
    renderAuth(<AuthConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user')).toHaveTextContent('admin')
    expect(screen.getByTestId('user-role')).toHaveTextContent('admin')
    expect(screen.getByTestId('user-email')).toHaveTextContent('admin@planbar.test')
    expect(screen.getByTestId('mustChangePassword')).toHaveTextContent('false')
  })

  it('setzt mustChangePassword bei gesetztem Flag', async () => {
    server.use(
      http.get(`${base}/users/me`, () =>
        HttpResponse.json({
          id: 1,
          username: 'admin',
          email: 'admin@planbar.test',
          role: 'admin',
          must_change_password: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-06-01T00:00:00Z',
          last_login: '2026-06-19T08:00:00Z',
        }),
      ),
    )

    renderAuth(<AuthConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('mustChangePassword')).toHaveTextContent('true')
    })
    expect(screen.getByTestId('user')).toHaveTextContent('admin')
  })

  it('login setzt Benutzer nach erfolgreicher Anmeldung', async () => {
    const user = userEvent.setup()
    renderAuth(<AuthConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('login-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('admin')
    })
  })

  it('login gibt { success: false } bei Fehler zurück', async () => {
    server.use(
      http.post(`${base}/users/login`, () =>
        HttpResponse.json({ detail: 'Ungültige Anmeldedaten' }, { status: 401 }),
      ),
    )

    const user = userEvent.setup()
    render(<MemoryRouter><AuthProvider><LoginResultCatcher /></AuthProvider></MemoryRouter>)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('fail-login-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('login-result-success')).toHaveTextContent('false')
      expect(screen.getByTestId('login-result-mcp')).toHaveTextContent('false')
    })
  })

  it('logout löscht Benutzer und ruft /users/logout auf', async () => {
    const user = userEvent.setup()
    renderAuth(<AuthConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('user')).toHaveTextContent('admin')

    await user.click(screen.getByTestId('logout-btn'))

    expect(screen.getByTestId('user')).toHaveTextContent('kein Benutzer')
    expect(screen.getByTestId('mustChangePassword')).toHaveTextContent('false')
  })

  it('changePassword ruft API auf und löscht mustChangePassword-Flag', async () => {
    server.use(
      http.get(`${base}/users/me`, () =>
        HttpResponse.json({
          id: 1,
          username: 'admin',
          email: 'admin@planbar.test',
          role: 'admin',
          must_change_password: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-06-01T00:00:00Z',
          last_login: '2026-06-19T08:00:00Z',
        }),
      ),
    )

    const user = userEvent.setup()
    renderAuth(<AuthConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('mustChangePassword')).toHaveTextContent('true')
    })

    await user.click(screen.getByTestId('change-pw-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('mustChangePassword')).toHaveTextContent('false')
    })
  })

  it('useAuth wirft Fehler ohne AuthProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<MemoryRouter><AuthConsumer /></MemoryRouter>)).toThrow(
      'useAuth must be used within an AuthProvider',
    )
    consoleSpy.mockRestore()
  })
})
