import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { AuthContext } from '../../context/AuthContext'
import { Routes, Route } from 'react-router'
import { Home } from '../Home'
import { describe, it, expect, vi } from 'vitest'
import { mockAdminUser, mockEmployeeUser, mockPlanerUser } from '../../../test/test-utils'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

function renderHome(user = mockAdminUser) {
  const authValue = {
    user,
    login: vi.fn(),
    logout: vi.fn(),
    isLoading: false,
    mustChangePassword: false,
    changePassword: vi.fn(),
  }
  return render(
    <MemoryRouter initialEntries={['/home']}>
      <AuthContext.Provider value={authValue as any}>
        <Routes>
          <Route path="/home" element={<Home />} />
          <Route path="/" element={<div data-testid="root-page" />} />
          <Route path="/dashboard" element={<div data-testid="dashboard-page" />} />
          <Route path="/employee-view" element={<div data-testid="employee-view-page" />} />
          <Route path="/schedule" element={<div data-testid="schedule-page" />} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  )
}

describe('Home', () => {
  it('leitet Admin-Benutzer zum Dashboard weiter', () => {
    renderHome(mockAdminUser)
    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument()
  })

  it('leitet Mitarbeiter-Benutzer zur Mitarbeiteransicht weiter', () => {
    renderHome(mockEmployeeUser)
    expect(screen.getByTestId('employee-view-page')).toBeInTheDocument()
  })

  it('leitet Planer zum Schichtplan weiter', () => {
    renderHome(mockPlanerUser)
    expect(screen.getByTestId('schedule-page')).toBeInTheDocument()
  })

  it('leitet ohne Benutzer zur Startseite weiter', () => {
    renderHome(null)
    expect(screen.getByTestId('root-page')).toBeInTheDocument()
  })
})
