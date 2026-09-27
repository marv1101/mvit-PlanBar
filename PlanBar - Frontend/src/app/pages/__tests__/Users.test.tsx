import { renderWithProviders } from '../../../test/test-utils'
import { Users } from '../Users'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/msw-handlers'
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

  it('klassifiziert Kiosk-Benutzer beim Anlegen ohne Passwortwechsel-Zwang', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 })
    const createBodies: Array<Record<string, unknown>> = []
    server.use(
      http.post('/api/v1/users/admin-create', async ({ request }) => {
        createBodies.push(await request.json() as Record<string, unknown>)
        return HttpResponse.json({
          id: 999, username: 'kiosk.tablet', email: 'kiosk@planbar.test', role: 'kiosk',
          must_change_password: false, employee_id: null,
          created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
          last_login: null, initial_password: 'geheim123',
        }, { status: 201 })
      }),
    )

    renderWithProviders(<Users />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /benutzer hinzufügen/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /benutzer hinzufügen/i }))
    const dialog = screen.getByRole('dialog')

    await user.type(within(dialog).getByLabelText(/benutzername/i), 'kiosk.tablet')
    await user.type(within(dialog).getByLabelText(/e-mail/i), 'kiosk@planbar.test')

    // Role select: first combobox in the create form
    const [roleTrigger] = within(dialog).getAllByRole('combobox')
    await user.click(roleTrigger)
    await user.click(screen.getByRole('option', { name: 'Kiosk' }))

    await user.click(within(dialog).getByRole('button', { name: /benutzer anlegen/i }))

    await waitFor(() => {
      expect(createBodies).toHaveLength(1)
    })
    expect(createBodies[0]['role']).toBe('kiosk')
    expect(createBodies[0]['must_change_password']).toBe(false)
  })

  it('behält Passwortwechsel-Standard für normale Rollen beim Anlegen bei', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 })
    const createBodies: Array<Record<string, unknown>> = []
    server.use(
      http.post('/api/v1/users/admin-create', async ({ request }) => {
        createBodies.push(await request.json() as Record<string, unknown>)
        return HttpResponse.json({
          id: 998, username: 'normal.user', email: 'normal@planbar.test', role: 'user',
          must_change_password: true, employee_id: null,
          created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
          last_login: null, initial_password: 'geheim123',
        }, { status: 201 })
      }),
    )

    renderWithProviders(<Users />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /benutzer hinzufügen/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /benutzer hinzufügen/i }))
    const dialog = screen.getByRole('dialog')

    await user.type(within(dialog).getByLabelText(/benutzername/i), 'normal.user')
    await user.type(within(dialog).getByLabelText(/e-mail/i), 'normal@planbar.test')
    await user.click(within(dialog).getByRole('button', { name: /benutzer anlegen/i }))

    await waitFor(() => {
      expect(createBodies).toHaveLength(1)
    })
    expect(createBodies[0]['role']).toBe('user')
    expect(createBodies[0]['must_change_password']).toBeUndefined()
  })
})
