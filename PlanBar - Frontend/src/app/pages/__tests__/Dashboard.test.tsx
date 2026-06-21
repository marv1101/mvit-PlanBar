import { renderWithProviders } from '../../../test/test-utils'
import { Dashboard } from '../Dashboard'
import { screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AppContext } from '../../context/AppContext'
import { mockAppContext } from '../../../test/test-utils'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe('Dashboard', () => {
  it('zeigt Ladezustand an', () => {
    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, loading: true } as any}>
        <Dashboard />
      </AppContext.Provider>,
    )
    expect(screen.getByText('Lade Daten...')).toBeInTheDocument()
  })

  it('rendert Dashboard-Inhalt', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Überblick über Ihre Schichtplanung')).toBeInTheDocument()
    expect(screen.getAllByText('Mitarbeiter').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Heutige Schichten')).toBeInTheDocument()
    expect(screen.getByText('Offene Wünsche')).toBeInTheDocument()
    expect(screen.getByText('Schichtpläne')).toBeInTheDocument()
  })

  it('rendert Schnellstart-Buttons', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Schnellstart')).toBeInTheDocument()
    expect(screen.getByText('Schichtplan')).toBeInTheDocument()
    expect(screen.getByText('Mitarbeiteransicht')).toBeInTheDocument()
  })
})
