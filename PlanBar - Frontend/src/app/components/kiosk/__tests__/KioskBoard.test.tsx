import React from 'react'
import { render, screen, within } from '@testing-library/react'
import { KioskBoard } from '../KioskBoard'
import { describe, it, expect } from 'vitest'
import type { KioskBoardDTO } from '../../../services/kioskService'

const mockBoard: KioskBoardDTO = {
  window_start: '2026-09-21',
  window_end: '2026-10-04',
  team: { id: 3, name: 'Pflege' },
  employees: [
    { id: 1, name: 'Anna Schmidt', color: '#ef4444' },
    { id: 2, name: 'Max Müller', color: null },
  ],
  shifts: [
    {
      employee_id: 1, date: '2026-09-22',
      start_time: '08:00:00', end_time: '16:00:00',
      break_start: '12:00:00', break_end: '12:30:00',
      label: 'Frueh', schedule_name: 'KW 38',
    },
    {
      employee_id: 2, date: '2026-09-27',
      start_time: '09:00:00', end_time: '17:00:00',
      break_start: null, break_end: null,
      label: null, schedule_name: 'KW 38',
    },
  ],
}

function windowDays(): string[] {
  const days: string[] = []
  const start = new Date('2026-09-21T00:00:00Z')
  const end = new Date('2026-10-04T00:00:00Z')
  for (let d = start; d <= end; d = new Date(d.getTime() + 86400000)) {
    days.push(d.toISOString().slice(0, 10))
  }
  return days
}

describe('KioskBoard', () => {
  it('rendert eine Zeile pro Mitarbeiter mit Namen und Farbpunkt', () => {
    render(<KioskBoard board={mockBoard} today="2026-09-22" />)

    const annaRow = screen.getByTestId('kiosk-row-1')
    expect(annaRow).toHaveTextContent('Anna Schmidt')
    const annaDot = within(annaRow).getByTestId('kiosk-dot-1')
    expect(annaDot).toHaveStyle({ backgroundColor: '#ef4444' })

    const maxRow = screen.getByTestId('kiosk-row-2')
    expect(maxRow).toHaveTextContent('Max Müller')
    const maxDot = within(maxRow).getByTestId('kiosk-dot-2')
    expect(maxDot).toHaveStyle({ backgroundColor: '#9ca3af' })
  })

  it('rendert Schicht-Blöcke mit Label und Start-Ende-Zeit', () => {
    render(<KioskBoard board={mockBoard} today="2026-09-22" />)

    const annaRow = screen.getByTestId('kiosk-row-1')
    expect(annaRow).toHaveTextContent('Frueh')
    expect(annaRow).toHaveTextContent('08:00–16:00')

    const maxRow = screen.getByTestId('kiosk-row-2')
    expect(maxRow).toHaveTextContent('09:00–17:00')
  })

  it('rendert alle 14 Tages-Spalten des Zeitraums', () => {
    render(<KioskBoard board={mockBoard} today="2026-09-22" />)

    for (const iso of windowDays()) {
      expect(screen.getByTestId(`kiosk-col-${iso}`)).toBeInTheDocument()
    }
    expect(screen.getByTestId('kiosk-col-2026-09-21')).toHaveTextContent('21.09.')
    expect(windowDays()).toHaveLength(14)
  })

  it('hebt die heutige Spalte hervor', () => {
    render(<KioskBoard board={mockBoard} today="2026-09-22" />)

    expect(screen.getByTestId('kiosk-col-2026-09-22')).toHaveAttribute(
      'aria-current',
      'date',
    )
    expect(screen.getByTestId('kiosk-col-2026-09-23')).not.toHaveAttribute(
      'aria-current',
    )
  })

  it('hebt Wochenenden visuell ab', () => {
    render(<KioskBoard board={mockBoard} today="2026-09-22" />)

    expect(screen.getByTestId('kiosk-col-2026-09-26')).toHaveAttribute(
      'data-weekend',
      'true',
    )
    expect(screen.getByTestId('kiosk-col-2026-09-23')).toHaveAttribute(
      'data-weekend',
      'false',
    )
  })

  it('ordnet Schichten der richtigen Tages-Spalte zu', () => {
    render(<KioskBoard board={mockBoard} today="2026-09-22" />)

    const annaRow = screen.getByTestId('kiosk-row-1')
    expect(
      within(annaRow).getByTestId('kiosk-cell-1-2026-09-22'),
    ).toHaveTextContent('Frueh')
    expect(
      within(annaRow).getByTestId('kiosk-cell-1-2026-09-23'),
    ).not.toHaveTextContent('Frueh')

    const maxRow = screen.getByTestId('kiosk-row-2')
    expect(
      within(maxRow).getByTestId('kiosk-cell-2-2026-09-27'),
    ).toHaveTextContent('09:00–17:00')
  })

  it('zeigt "Zuletzt aktualisiert" mit Uhrzeit, wenn lastUpdated gesetzt ist', () => {
    render(
      <KioskBoard
        board={mockBoard}
        today="2026-09-22"
        lastUpdated={new Date('2026-09-22T14:30:00').getTime()}
      />,
    )
    expect(screen.getByText(/Zuletzt aktualisiert: 14:30/)).toBeInTheDocument()
  })

  it('zeigt den Leerzustand bei leeren shifts', () => {
    render(
      <KioskBoard
        board={{ ...mockBoard, shifts: [] }}
        today="2026-09-22"
      />,
    )
    expect(screen.getByText('Kein Dienstplan für den Zeitraum')).toBeInTheDocument()
  })
})
