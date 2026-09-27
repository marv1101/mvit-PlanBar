import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { MemoryRouter, Routes, Route, useLocation } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { server } from '../../../test/msw-handlers'
import { AuthContext } from '../../context/AuthContext'
import { Kiosk } from '../Kiosk'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mockKioskUser } from '../../../test/test-utils'
import type { KioskBoardDTO } from '../../services/kioskService'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const base = '/api/v1'

const mockBoard: KioskBoardDTO = {
  window_start: '2026-09-21',
  window_end: '2026-10-04',
  team: { id: 3, name: 'Pflege' },
  employees: [
    { id: 1, name: 'Anna Schmidt', color: '#ef4444' },
    { id: 2, name: 'Max Müller', color: null },
  ],
  shifts: [
    {
      employee_id: 1, date: '2026-09-22',
      start_time: '08:00:00', end_time: '16:00:00',
      break_start: '12:00:00', break_end: '12:30:00',
      label: 'Frueh', schedule_name: 'KW 38',
    },
    {
      employee_id: 2, date: '2026-09-22',
      start_time: '09:00:00', end_time: '17:00:00',
      break_start: null, break_end: null,
      label: null, schedule_name: 'KW 38',
    },
  ],
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function LocationProbe() {
  const { pathname } = useLocation()
  return <span data-testid="location">{pathname}</span>
}

type AuthUser = typeof mockKioskUser | null

interface RenderOptions {
  initialEntries?: string[]
  user?: AuthUser
}

function renderKiosk({ initialEntries = ['/kiosk'], user = null as AuthUser }: RenderOptions = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  const authValue = {
    user,
    login: vi.fn(),
    logout: vi.fn(),
    isLoading: false,
    mustChangePassword: false,
    changePassword: vi.fn(),
  }

  function Harness() {
    return (
      <MemoryRouter initialEntries={initialEntries}>
        <AuthContext.Provider value={authValue as any}>
          <QueryClientProvider client={queryClient}>
            <Routes>
              <Route path="/kiosk" element={<Kiosk />} />
              <Route path="/login" element={<div data-testid="login-page" />} />
              <Route path="/" element={<div data-testid="root-page" />} />
            </Routes>
            <LocationProbe />
          </QueryClientProvider>
        </AuthContext.Provider>
      </MemoryRouter>
    )
  }

  const rerenderHarness = (nextUser: AuthUser) => {
    authValue.user = nextUser
    rerender(<Harness />)
  }

  const rendered = render(<Harness />)
  const rerender = (ui: React.ReactElement) => rendered.rerender(ui)

  return { ...rendered, rerender, rerenderHarness }
}

// ---------------------------------------------------------------------------
// Request spies
// ---------------------------------------------------------------------------

let loginBody: { email?: string; password?: string } | null = null
let boardRequests: Request[] = []

function installKioskHandlers(board: KioskBoardDTO | { status: number }) {
  server.use(
    http.post(`${base}/users/login`, async ({ request }) => {
      loginBody = await request.json() as { email?: string; password?: string }
      return HttpResponse.json(
        { access_token: 'a', refresh_token: 'r', token_type: 'bearer', must_change_password: true },
        { status: 200 },
      )
    }),
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
    http.get(`${base}/kiosk/board`, ({ request }) => {
      boardRequests.push(request)
      if ('status' in board) {
        return HttpResponse.json({ detail: 'Serverfehler' }, { status: board.status })
      }
      return HttpResponse.json(board)
    }),
  )
}

describe('Kiosk', () => {
  beforeEach(() => {
    server.resetHandlers()
    loginBody = null
    boardRequests = []
  })

  it('zeigt ein Login-Formular für nicht angemeldete Benutzer', () => {
    renderKiosk({ user: null })

    expect(screen.getByLabelText('E-Mail')).toBeInTheDocument()
    expect(screen.getByLabelText('Passwort')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Anmelden' })).toBeInTheDocument()
    expect(screen.queryByTestId('kiosk-board')).not.toBeInTheDocument()
  })

  it('POST /users/login bei Submit, kein Passwort-ändern-Dialog trotz must_change_password, Board nach Neuaufruf', async () => {
    installKioskHandlers(mockBoard)
    const { rerenderHarness } = renderKiosk({ user: null })

    const user = userEvent.setup()
    await user.type(screen.getByLabelText('E-Mail'), 'kiosk@example.com')
    await user.type(screen.getByLabelText('Passwort'), 'geheim')
    await user.click(screen.getByRole('button', { name: 'Anmelden' }))

    await waitFor(() => {
      expect(loginBody).toEqual({ email: 'kiosk@example.com', password: 'geheim' })
    })

    // must_change_password=true in der Login-Antwort darf KEINEN
    // Passwort-ändern-Dialog auslösen
    expect(screen.queryByText(/Passwort ändern/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    // "Reload" simulieren: AuthProvider sucht /users/me erneut und findet
    // den kiosk-Benutzer → Board wird gerendert
    rerenderHarness(mockKioskUser)

    expect(await screen.findByTestId('kiosk-board')).toBeInTheDocument()
    expect(screen.getByText('Pflege')).toBeInTheDocument()
    expect(screen.getByText('Anna Schmidt')).toBeInTheDocument()
  })

  it('lädt das Board mit Credentials, Team-Name und ?team=3 → team_id=3', async () => {
    installKioskHandlers(mockBoard)
    renderKiosk({ user: mockKioskUser, initialEntries: ['/kiosk?team=3'] })

    expect(await screen.findByTestId('kiosk-board')).toBeInTheDocument()
    expect(screen.getByText('Pflege')).toBeInTheDocument()
    expect(screen.getByText('Anna Schmidt')).toBeInTheDocument()

    await waitFor(() => {
      expect(boardRequests.length).toBeGreaterThan(0)
    })
    const req = boardRequests[0]
    expect(new URL(req.url).searchParams.get('team_id')).toBe('3')
    expect(req.credentials).toBe('include')
  })

  it('sendet kein team_id ohne Team-Parameter', async () => {
    installKioskHandlers(mockBoard)
    renderKiosk({ user: mockKioskUser, initialEntries: ['/kiosk'] })

    expect(await screen.findByTestId('kiosk-board')).toBeInTheDocument()
    await waitFor(() => {
      expect(boardRequests.length).toBeGreaterThan(0)
    })
    expect(new URL(boardRequests[0].url).searchParams.get('team_id')).toBeNull()
  })

  it('zeigt ein Fehler-Banner bei Board-Fehler und leitet NICHT auf /login weiter', async () => {
    installKioskHandlers({ status: 500 })
    renderKiosk({ user: mockKioskUser, initialEntries: ['/kiosk'] })

    expect(
      await screen.findByTestId('kiosk-error', {}, { timeout: 3000 }),
    ).toBeInTheDocument()
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument()
    expect(screen.getByTestId('location')).toHaveTextContent('/kiosk')
  })

  it('zeigt "Kein Dienstplan" bei leerem Board', async () => {
    installKioskHandlers({
      window_start: '2026-09-21',
      window_end: '2026-10-04',
      team: null,
      employees: [],
      shifts: [],
    })
    renderKiosk({ user: mockKioskUser, initialEntries: ['/kiosk'] })

    expect(await screen.findByText(/Kein Dienstplan/)).toBeInTheDocument()
  })

  it('zeigt eine Ladeanzeige, solange der Benutzer geprüft wird', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const authValue = {
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
      isLoading: true,
      mustChangePassword: false,
      changePassword: vi.fn(),
    }
    render(
      <MemoryRouter initialEntries={['/kiosk']}>
        <AuthContext.Provider value={authValue as any}>
          <QueryClientProvider client={queryClient}>
            <Kiosk />
          </QueryClientProvider>
        </AuthContext.Provider>
      </MemoryRouter>,
    )

    expect(screen.getByTestId('kiosk-loading')).toBeInTheDocument()
  })
})
