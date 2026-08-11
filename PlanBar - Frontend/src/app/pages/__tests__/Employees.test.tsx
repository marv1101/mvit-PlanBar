import { renderWithProviders } from '../../../test/test-utils'
import { Employees } from '../Employees'
import { screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AppContext } from '../../context/AppContext'
import { mockAppContext } from '../../../test/test-utils'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe('Employees', () => {
  it('zeigt Ladezustand an', () => {
    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, loading: true, employees: [] } as any}>
        <Employees />
      </AppContext.Provider>,
    )
    expect(screen.getByText('Lade Mitarbeiter...')).toBeInTheDocument()
  })

  it('rendert Mitarbeiter-Karten mit Namen', () => {
    renderWithProviders(<Employees />)
    expect(screen.getByText('Max Müller')).toBeInTheDocument()
    expect(screen.getByText('Anna Schmidt')).toBeInTheDocument()
    expect(screen.getByText('max@example.com')).toBeInTheDocument()
    expect(screen.getByText('anna@example.com')).toBeInTheDocument()
  })

  it('zeigt leeren Zustand bei keiner Mitarbeiter', () => {
    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, employees: [] } as any}>
        <Employees />
      </AppContext.Provider>,
    )
    expect(screen.getByText('Noch keine Mitarbeiter hinzugefügt')).toBeInTheDocument()
  })
})
