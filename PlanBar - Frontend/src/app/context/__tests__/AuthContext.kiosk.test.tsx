import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { MemoryRouter } from 'react-router'
import { server } from '../../../test/msw-handlers'
import { AuthProvider, useAuth } from '../AuthContext'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const base = '/api/v1'

function RoleProbe() {
  const auth = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(auth.isLoading)}</span>
      <span data-testid="user-role">{auth.user?.role ?? '—'}</span>
      <span data-testid="user-name">{auth.user?.name ?? '—'}</span>
    </div>
  )
}

function renderAuth(ui: React.ReactElement) {
  return render(<MemoryRouter><AuthProvider>{ui}</AuthProvider></MemoryRouter>)
}

describe('AuthContext – kiosk-Rolle', () => {
  beforeEach(() => {
    server.resetHandlers()
  })

  it('mappt die Backend-Rolle kiosk auf kiosk (nicht employee)', async () => {
    server.use(
      http.get(`${base}/users/me`, () =>
        HttpResponse.json({
          id: 10,
          username: 'kiosk-display',
          email: 'kiosk@example.com',
          role: 'kiosk',
          must_change_password: false,
          employee_id: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-06-01T00:00:00Z',
          last_login: null,
        }),
      ),
    )

    renderAuth(<RoleProbe />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })
    expect(screen.getByTestId('user-role')).toHaveTextContent('kiosk')
    expect(screen.getByTestId('user-name')).toHaveTextContent('kiosk-display')
  })
})
