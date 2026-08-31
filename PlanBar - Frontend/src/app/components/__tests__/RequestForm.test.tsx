import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RequestForm } from '../RequestForm'
import { renderWithProviders, mockAppContext, mockEmployees } from '../../../test/test-utils'
import { AppContext } from '../../context/AppContext'
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const baseProps = {
  request: null,
  onClose: vi.fn(),
  currentEmployeeId: undefined,
  isAdmin: true,
}

describe('RequestForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('rendert alle Formularfelder (Woche wird aus dem Datum abgeleitet)', () => {
    renderWithProviders(<RequestForm {...baseProps} />)

    expect(screen.getByText('Mitarbeiter')).toBeInTheDocument()
    expect(screen.getByLabelText('Datum')).toBeInTheDocument()
    expect(screen.getByText('Art des Wunsches')).toBeInTheDocument()
    expect(screen.getByLabelText('Notizen (optional)')).toBeInTheDocument()
    expect(screen.queryByText('Woche')).not.toBeInTheDocument()
  })

  it('zeigt Mitarbeiter-Auswahl für Admin', () => {
    renderWithProviders(<RequestForm {...baseProps} />)

    const items = screen.getAllByText('Max Müller')
    expect(items.length).toBeGreaterThanOrEqual(1)
  })

  it('zeigt deaktivierten Mitarbeiter-Namen für Employee', () => {
    renderWithProviders(
      <RequestForm
        request={null}
        onClose={vi.fn()}
        currentEmployeeId="1"
        isAdmin={false}
      />,
    )

    const input = screen.getByDisplayValue('Max Müller')
    expect(input).toBeDisabled()
  })

  it('zeigt Hinzufügen-Button im Create-Modus', () => {
    renderWithProviders(<RequestForm {...baseProps} />)

    expect(screen.getByRole('button', { name: 'Hinzufügen' })).toBeInTheDocument()
  })

  it('zeigt Speichern-Button im Edit-Modus', () => {
    const request = {
      id: '123',
      employeeId: '1',
      date: '2026-06-18',
      week: 'A' as const,
      type: 'urlaubswunsch' as const,
      notes: '',
    }

    renderWithProviders(
      <RequestForm {...baseProps} request={request} />,
    )

    expect(screen.getByRole('button', { name: 'Speichern' })).toBeInTheDocument()
  })

  it('ruft onClose beim Klick auf Abbrechen auf', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    renderWithProviders(
      <RequestForm {...baseProps} onClose={onClose} />,
    )

    await user.click(screen.getByRole('button', { name: 'Abbrechen' }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('ruft addRequest beim Absenden im Create-Modus auf', async () => {
    const user = userEvent.setup()
    const addRequest = vi.fn()

    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, addRequest } as any}>
        <RequestForm {...baseProps} />
      </AppContext.Provider>,
    )

    await user.type(screen.getByLabelText('Notizen (optional)'), 'Testnotiz')

    await user.click(screen.getByRole('button', { name: 'Hinzufügen' }))

    expect(addRequest).toHaveBeenCalledOnce()
    expect(addRequest).toHaveBeenCalledWith(
      expect.objectContaining({ notes: 'Testnotiz' }),
    )
  })

  it('ruft updateRequest beim Absenden im Edit-Modus auf', async () => {
    const user = userEvent.setup()
    const updateRequest = vi.fn()
    const request = {
      id: '123',
      employeeId: '1',
      date: '2026-06-18',
      week: 'A' as const,
      type: 'urlaubswunsch' as const,
      notes: 'Alte Notiz',
    }

    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, updateRequest } as any}>
        <RequestForm {...baseProps} request={request} />
      </AppContext.Provider>,
    )

    const notesInput = screen.getByLabelText('Notizen (optional)')
    await user.clear(notesInput)
    await user.type(notesInput, 'Aktualisierte Notiz')

    await user.click(screen.getByRole('button', { name: 'Speichern' }))

    expect(updateRequest).toHaveBeenCalledOnce()
    expect(updateRequest).toHaveBeenCalledWith(
      '123',
      expect.objectContaining({ notes: 'Aktualisierte Notiz' }),
    )
  })

  it('ruft onClose nach erfolgreichem Submit auf', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    renderWithProviders(
      <RequestForm {...baseProps} onClose={onClose} />,
    )

    await user.click(screen.getByRole('button', { name: 'Hinzufügen' }))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
