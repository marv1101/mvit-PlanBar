import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EmployeeForm } from '../EmployeeForm'
import { renderWithProviders, mockAppContext } from '../../../test/test-utils'
import { AppContext } from '../../context/AppContext'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Employee } from '../../types'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const baseProps = {
  employee: null,
  onClose: vi.fn(),
}

const existingEmployee: Employee = {
  id: '42',
  name: 'Bestehender MA',
  email: 'bestehend@test.de',
  roles: [],
  workingHours: {
    weekA: {
      monday: { start: '08:00', end: '18:00', enabled: true },
      tuesday: { start: '08:00', end: '18:00', enabled: true },
      wednesday: { start: '08:00', end: '18:00', enabled: true },
      thursday: { start: '08:00', end: '18:00', enabled: true },
      friday: { start: '08:00', end: '18:00', enabled: true },
      saturday: { start: '08:00', end: '14:00', enabled: true },
      sunday: { start: '09:00', end: '13:00', enabled: false },
    },
    weekB: {
      monday: { start: '08:00', end: '18:00', enabled: true },
      tuesday: { start: '08:00', end: '18:00', enabled: true },
      wednesday: { start: '08:00', end: '18:00', enabled: true },
      thursday: { start: '08:00', end: '18:00', enabled: true },
      friday: { start: '08:00', end: '18:00', enabled: true },
      saturday: { start: '08:00', end: '14:00', enabled: true },
      sunday: { start: '09:00', end: '13:00', enabled: false },
    },
  },
  breakTime: { start: '12:00', end: '13:00', duration: 60 },
  color: '#3b82f6',
  maxWorkHours: 40,
}

describe('EmployeeForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('rendert alle Formularfelder', () => {
    renderWithProviders(<EmployeeForm {...baseProps} />)

    expect(screen.getByLabelText('Name')).toBeInTheDocument()
    expect(screen.getByLabelText('E-Mail')).toBeInTheDocument()
    expect(screen.getByText('Rollen / Fähigkeiten')).toBeInTheDocument()
    expect(screen.getByLabelText('Farbe auswählen')).toBeInTheDocument()
    expect(screen.getByLabelText('Pause Start')).toBeInTheDocument()
    expect(screen.getByLabelText('Pause Ende')).toBeInTheDocument()
    expect(screen.getByLabelText('Dauer (Min.)')).toBeInTheDocument()
    expect(screen.getByLabelText('Maximale Arbeitszeit pro Woche (Stunden)')).toBeInTheDocument()
    expect(screen.getByText('Arbeitszeiten')).toBeInTheDocument()
  })

  it('zeigt Hinzufügen-Button im Create-Modus', () => {
    renderWithProviders(<EmployeeForm {...baseProps} />)

    expect(screen.getByRole('button', { name: 'Hinzufügen' })).toBeInTheDocument()
  })

  it('zeigt Speichern-Button im Edit-Modus', () => {
    renderWithProviders(
      <EmployeeForm {...baseProps} employee={existingEmployee} />,
    )

    expect(screen.getByRole('button', { name: 'Speichern' })).toBeInTheDocument()
  })

  it('zeigt Mitarbeitername im Edit-Modus', () => {
    renderWithProviders(
      <EmployeeForm {...baseProps} employee={existingEmployee} />,
    )

    const nameInput = screen.getByLabelText('Name') as HTMLInputElement
    expect(nameInput.value).toBe('Bestehender MA')
  })

  it('ruft onClose beim Klick auf Abbrechen auf', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    renderWithProviders(
      <EmployeeForm {...baseProps} onClose={onClose} />,
    )

    await user.click(screen.getByRole('button', { name: 'Abbrechen' }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('ruft addEmployee beim Absenden im Create-Modus auf', async () => {
    const user = userEvent.setup()
    const addEmployee = vi.fn()

    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, addEmployee } as any}>
        <EmployeeForm {...baseProps} />
      </AppContext.Provider>,
    )

    await user.type(screen.getByLabelText('Name'), 'Neuer MA')
    await user.type(screen.getByLabelText('E-Mail'), 'neu@test.de')

    await user.click(screen.getByRole('button', { name: 'Hinzufügen' }))

    expect(addEmployee).toHaveBeenCalledOnce()
    expect(addEmployee).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Neuer MA', email: 'neu@test.de' }),
    )
  })

  it('ruft updateEmployee beim Absenden im Edit-Modus auf', async () => {
    const user = userEvent.setup()
    const updateEmployee = vi.fn()

    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, updateEmployee } as any}>
        <EmployeeForm {...baseProps} employee={existingEmployee} />
      </AppContext.Provider>,
    )

    const nameInput = screen.getByLabelText('Name')
    await user.clear(nameInput)
    await user.type(nameInput, 'Geänderter MA')

    await user.click(screen.getByRole('button', { name: 'Speichern' }))

    expect(updateEmployee).toHaveBeenCalledOnce()
    expect(updateEmployee).toHaveBeenCalledWith(
      '42',
      expect.objectContaining({ name: 'Geänderter MA' }),
    )
  })

  it('ruft onClose nach erfolgreichem Submit auf', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    renderWithProviders(
      <EmployeeForm {...baseProps} onClose={onClose} />,
    )

    await user.type(screen.getByLabelText('Name'), 'Test')
    await user.type(screen.getByLabelText('E-Mail'), 'test@test.de')
    await user.click(screen.getByRole('button', { name: 'Hinzufügen' }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('zeigt Rollen-Checkboxen wenn Rollen verfügbar sind', () => {
    const roles = [
      { id: 'koch', name: 'Koch', color: '#3b82f6' },
      { id: 'service', name: 'Service', color: '#ef4444' },
    ]

    renderWithProviders(
      <AppContext.Provider value={{ ...mockAppContext, roles } as any}>
        <EmployeeForm {...baseProps} />
      </AppContext.Provider>,
    )

    expect(screen.getByText('Koch')).toBeInTheDocument()
    expect(screen.getByText('Service')).toBeInTheDocument()
  })
})
