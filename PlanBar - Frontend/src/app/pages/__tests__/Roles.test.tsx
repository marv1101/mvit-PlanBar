import { renderWithProviders } from '../../../test/test-utils'
import { Roles } from '../Roles'
import { screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AppContext } from '../../context/AppContext'
import { mockAppContext } from '../../../test/test-utils'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const rolesWithData = [
  { id: '1', name: 'Koch', color: '#3b82f6' },
  { id: '2', name: 'Service', color: '#ef4444' },
]

describe('Roles', () => {
  it('zeigt Ladezustand an', () => {
    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, loading: true, roles: [] } as any}>
        <Roles />
      </AppContext.Provider>,
    )
    expect(screen.getByText('Lade Rollen...')).toBeInTheDocument()
  })

  it('rendert Rollen-Karten', () => {
    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, roles: rolesWithData } as any}>
        <Roles />
      </AppContext.Provider>,
    )
    expect(screen.getByText('Koch')).toBeInTheDocument()
    expect(screen.getByText('Service')).toBeInTheDocument()
  })

  it('zeigt leeren Zustand bei keinen Rollen', () => {
    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, roles: [] } as any}>
        <Roles />
      </AppContext.Provider>,
    )
    expect(screen.getByText('Keine Rollen vorhanden')).toBeInTheDocument()
  })
})
