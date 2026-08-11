import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ShiftListView } from '../ShiftListView'
import { describe, it, expect, vi } from 'vitest'
import type { Shift, Employee } from '../../types'

const employees: Employee[] = [
  {
    id: '1',
    name: 'Max Müller',
    email: 'max@test.de',
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
  },
  {
    id: '2',
    name: 'Anna Schmidt',
    email: 'anna@test.de',
    roles: [],
    workingHours: {
      weekA: {
        monday: { start: '09:00', end: '17:00', enabled: true },
        tuesday: { start: '09:00', end: '17:00', enabled: true },
        wednesday: { start: '09:00', end: '17:00', enabled: true },
        thursday: { start: '09:00', end: '17:00', enabled: true },
        friday: { start: '09:00', end: '17:00', enabled: true },
        saturday: { start: '09:00', end: '17:00', enabled: false },
        sunday: { start: '09:00', end: '17:00', enabled: false },
      },
      weekB: {
        monday: { start: '09:00', end: '17:00', enabled: true },
        tuesday: { start: '09:00', end: '17:00', enabled: true },
        wednesday: { start: '09:00', end: '17:00', enabled: true },
        thursday: { start: '09:00', end: '17:00', enabled: true },
        friday: { start: '09:00', end: '17:00', enabled: true },
        saturday: { start: '09:00', end: '17:00', enabled: false },
        sunday: { start: '09:00', end: '17:00', enabled: false },
      },
    },
    breakTime: { start: '12:00', end: '12:30', duration: 30 },
    color: '#ef4444',
  },
]

const baseShift: Shift = {
  id: 'shift-1',
  employeeId: '1',
  date: '2026-06-15',
  week: 'A',
  startTime: '08:00',
  endTime: '18:00',
  breakStart: '12:00',
  breakEnd: '13:00',
  label: 'Backoffice',
}

describe('ShiftListView', () => {
  it('zeigt leeren Zustand wenn keine Schichten vorhanden sind', () => {
    render(
      <ShiftListView
        shifts={[]}
        employees={[]}
        weekLabel="KW 25"
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(screen.getByText(/Keine Schichten/)).toBeInTheDocument()
    expect(screen.getByText(/KW 25/)).toBeInTheDocument()
  })

  it('gruppiert Schichten nach Datum', () => {
    const shifts: Shift[] = [
      baseShift,
      {
        ...baseShift,
        id: 'shift-2',
        employeeId: '2',
        startTime: '09:00',
        endTime: '17:00',
      },
    ]

    render(
      <ShiftListView
        shifts={shifts}
        employees={employees}
        weekLabel="KW 25"
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(screen.getByText('Max Müller')).toBeInTheDocument()
    expect(screen.getByText('Anna Schmidt')).toBeInTheDocument()
    expect(screen.getByText('08:00 – 18:00')).toBeInTheDocument()
    expect(screen.getByText('09:00 – 17:00')).toBeInTheDocument()
  })

  it('zeigt verschiedene Daten als separate Gruppen an', () => {
    const shifts: Shift[] = [
      baseShift,
      {
        ...baseShift,
        id: 'shift-2',
        date: '2026-06-16',
        startTime: '09:00',
        endTime: '17:00',
      },
    ]

    render(
      <ShiftListView
        shifts={shifts}
        employees={employees}
        weekLabel="KW 25"
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(screen.getAllByRole('button').length).toBeGreaterThanOrEqual(2)
  })

  it('zeigt Schicht-Label wenn vorhanden', () => {
    render(
      <ShiftListView
        shifts={[baseShift]}
        employees={employees}
        weekLabel="KW 25"
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(screen.getByText('Backoffice')).toBeInTheDocument()
  })

  it('ruft onEdit beim Klick auf Bearbeiten-Button auf', async () => {
    const user = userEvent.setup()
    const onEdit = vi.fn()

    render(
      <ShiftListView
        shifts={[baseShift]}
        employees={employees}
        weekLabel="KW 25"
        onEdit={onEdit}
        onDelete={vi.fn()}
      />,
    )

    const editButton = screen.getByLabelText(/Schicht.*bearbeiten/)
    await user.click(editButton)
    expect(onEdit).toHaveBeenCalledWith(baseShift)
  })

  it('ruft onDelete beim Klick auf Löschen-Button auf', async () => {
    const user = userEvent.setup()
    const onDelete = vi.fn()

    render(
      <ShiftListView
        shifts={[baseShift]}
        employees={employees}
        weekLabel="KW 25"
        onEdit={vi.fn()}
        onDelete={onDelete}
      />,
    )

    const deleteButton = screen.getByLabelText(/Schicht.*löschen/)
    await user.click(deleteButton)
    expect(onDelete).toHaveBeenCalledWith(baseShift)
  })

  it('zeigt Unbekannt wenn Mitarbeiter nicht gefunden wird', () => {
    const shifts: Shift[] = [
      { ...baseShift, employeeId: '999' },
    ]

    render(
      <ShiftListView
        shifts={shifts}
        employees={employees}
        weekLabel="KW 25"
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(screen.getByText('Unbekannt')).toBeInTheDocument()
  })
})
