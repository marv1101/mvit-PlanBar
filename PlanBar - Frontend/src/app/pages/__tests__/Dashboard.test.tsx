import { renderWithProviders } from '../../../test/test-utils'
import { Dashboard } from '../Dashboard'
import { screen, waitFor } from '@testing-library/react'
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

  it('rendert Dashboard-Inhalt', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })
  })
})
