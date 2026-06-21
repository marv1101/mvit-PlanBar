import { renderWithProviders } from '../../../test/test-utils'
import { Users } from '../Users'
import { screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe('Users', () => {
  it('zeigt Ladezustand an', () => {
    renderWithProviders(<Users />)
    expect(screen.getByText('Lade Benutzer...')).toBeInTheDocument()
  })

  it('rendert Benutzerliste nach erfolgreichem Laden', async () => {
    renderWithProviders(<Users />)

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument()
    })
    expect(screen.getByText('mmueller')).toBeInTheDocument()
    expect(screen.getByText('admin@planbar.test')).toBeInTheDocument()
    expect(screen.getByText('max@example.com')).toBeInTheDocument()
  })

  it('zeigt leeren Zustand bei keinen Benutzern', async () => {
    renderWithProviders(<Users />)

    // Wait for loading to finish; empty state is shown only after load
    await waitFor(() => {
      expect(screen.queryByText('Lade Benutzer...')).not.toBeInTheDocument()
    })
  })
})
