import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'
import { AuthContext } from '../../context/AuthContext'
import { ProtectedRoute } from '../ProtectedRoute'
import { mockAdminUser, mockEmployeeUser } from '../../../test/test-utils'
import { describe, it, expect, vi } from 'vitest'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

function renderProtectedRoute(
  ui: React.ReactElement,
  { user = null }: { user?: typeof mockAdminUser | null } = {},
) {
  const authValue = {
    user,
    login: vi.fn(),
    logout: vi.fn(),
    isLoading: false,
    mustChangePassword: false,
    changePassword: vi.fn(),
  }
  return render(
    <MemoryRouter initialEntries={['/protected']}>
      <AuthContext.Provider value={authValue as any}>
        <Routes>
          <Route path="/protected" element={ui} />
          <Route path="/" element={<div data-testid="home-page" />} />
          <Route path="/employee-view" element={<div data-testid="employee-view-page" />} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('leitet zur Startseite weiter wenn kein Benutzer angemeldet ist', () => {
    renderProtectedRoute(
      <ProtectedRoute allowedRoles={['admin']}>
        <div data-testid="protected-content" />
      </ProtectedRoute>,
    )

    expect(screen.getByTestId('home-page')).toBeInTheDocument()
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })

  it('rendert Kinder wenn der Benutzer die erforderliche Rolle hat', () => {
    renderProtectedRoute(
      <ProtectedRoute allowedRoles={['admin']}>
        <div data-testid="protected-content" />
      </ProtectedRoute>,
      { user: mockAdminUser },
    )

    expect(screen.getByTestId('protected-content')).toBeInTheDocument()
    expect(screen.queryByTestId('home-page')).not.toBeInTheDocument()
  })

  it('leitet Mitarbeiter zur Mitarbeiteransicht weiter wenn Admin-Route aufgerufen wird', () => {
    renderProtectedRoute(
      <ProtectedRoute allowedRoles={['admin']}>
        <div data-testid="protected-content" />
      </ProtectedRoute>,
      { user: mockEmployeeUser },
    )

    expect(screen.getByTestId('employee-view-page')).toBeInTheDocument()
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })
})
