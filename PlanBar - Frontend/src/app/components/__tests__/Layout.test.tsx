import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'
import { AuthContext } from '../../context/AuthContext'
import { Layout } from '../Layout'
import { mockAdminUser, mockEmployeeUser } from '../../../test/test-utils'
import { describe, it, expect, vi } from 'vitest'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

function renderLayout(user = mockAdminUser) {
  const authValue = {
    user,
    login: vi.fn(),
    logout: vi.fn(),
    isLoading: false,
    mustChangePassword: false,
    changePassword: vi.fn(),
  }
  return render(
    <MemoryRouter initialEntries={['/']}>
      <AuthContext.Provider value={authValue as any}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div data-testid="outlet-content" />} />
          </Route>
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  )
}

describe('Layout', () => {
  it('rendert den App-Titel', () => {
    renderLayout()
    expect(screen.getByText('MVIT PlanBar')).toBeInTheDocument()
  })

  it('zeigt Admin-Benutzerinfo an', () => {
    renderLayout(mockAdminUser)
    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getByText('(Administrator)')).toBeInTheDocument()
  })

  it('zeigt Mitarbeiter-Benutzerinfo an', () => {
    renderLayout(mockEmployeeUser)
    expect(screen.getByText('Max Müller')).toBeInTheDocument()
    expect(screen.getByText('(Mitarbeiter)')).toBeInTheDocument()
  })

  it('zeigt alle Admin-Navigationspunkte an', () => {
    renderLayout(mockAdminUser)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Rollen')).toBeInTheDocument()
    expect(screen.getByText('Mitarbeiter')).toBeInTheDocument()
    expect(screen.getByText('Benutzer')).toBeInTheDocument()
    expect(screen.getByText('Wünsche')).toBeInTheDocument()
    expect(screen.getByText('Schichtplan')).toBeInTheDocument()
    expect(screen.getByText('Zeitkonten')).toBeInTheDocument()
    expect(screen.getByText('Mitarbeiteransicht')).toBeInTheDocument()
    expect(screen.getByText('Pinnwand')).toBeInTheDocument()
  })

  it('zeigt eingeschränkte Navigationspunkte für Mitarbeiter', () => {
    renderLayout(mockEmployeeUser)
    expect(screen.getByText('Wünsche')).toBeInTheDocument()
    expect(screen.getByText('Mitarbeiteransicht')).toBeInTheDocument()
    expect(screen.getByText('Pinnwand')).toBeInTheDocument()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
    expect(screen.queryByText('Rollen')).not.toBeInTheDocument()
    expect(screen.queryByText('Mitarbeiter')).not.toBeInTheDocument()
    expect(screen.queryByText('Benutzer')).not.toBeInTheDocument()
    expect(screen.queryByText('Schichtplan')).not.toBeInTheDocument()
    expect(screen.queryByText('Zeitkonten')).not.toBeInTheDocument()
  })

  it('rendert den Outlet-Inhalt', () => {
    renderLayout()
    expect(screen.getByTestId('outlet-content')).toBeInTheDocument()
  })

  it('zeigt Abmelde-Button', () => {
    renderLayout()
    expect(screen.getByText('Abmelden')).toBeInTheDocument()
  })
})
