import { render, screen, waitFor } from '@testing-library/react'
import { TimeAccountCard } from '../TimeAccountCard'
import { renderWithProviders } from '../../../test/test-utils'
import { describe, it, expect, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/msw-handlers'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const base = '/api/v1'

describe('TimeAccountCard', () => {
  it('zeigt Ladezustand beim Start an', () => {
    renderWithProviders(<TimeAccountCard employeeId="1" />)

    expect(screen.getByText('Lade Zeitkonto...')).toBeInTheDocument()
  })

  it('rendert den aktuellen Saldo nach erfolgreichem Laden', async () => {
    renderWithProviders(<TimeAccountCard employeeId="1" />)

    await waitFor(() => {
      expect(screen.getByText('Aktueller Saldo')).toBeInTheDocument()
    })

    const balanceElements = screen.getAllByText(/12\.5/)
    expect(balanceElements.length).toBeGreaterThanOrEqual(1)
  })

  it('rendert Chart-Titel', async () => {
    renderWithProviders(<TimeAccountCard employeeId="1" />)

    await waitFor(() => {
      expect(screen.getByText('Zeitkonto')).toBeInTheDocument()
    })
  })

  it('zeigt Projektion wenn vorhanden', async () => {
    renderWithProviders(<TimeAccountCard employeeId="1" />)

    await waitFor(() => {
      expect(screen.getByText(/Prognose/)).toBeInTheDocument()
    })

    expect(screen.getByText(/Geplant: 40.0h/)).toBeInTheDocument()
  })

  it('zeigt Wochen-Historie wenn vorhanden', async () => {
    renderWithProviders(<TimeAccountCard employeeId="1" />)

    await waitFor(() => {
      expect(screen.getByText('Wochen-Historie')).toBeInTheDocument()
    })

    expect(screen.getByText('25/2026')).toBeInTheDocument()
  })

  it('zeigt leeren Zustand bei fehlender Historie', async () => {
    server.use(
      http.get(`${base}/employees/:id/time-account`, () =>
        HttpResponse.json({
          employee_id: 3,
          employee_name: 'Test MA',
          current_balance: 0,
          history: [],
          projected: null,
        }),
      ),
    )

    renderWithProviders(<TimeAccountCard employeeId="3" />)

    await waitFor(() => {
      expect(
        screen.getByText('Noch keine Zeitkonten-Historie vorhanden'),
      ).toBeInTheDocument()
    })
  })

  it('zeigt Fehlerzustand bei fehlgeschlagener API-Anfrage', async () => {
    server.use(
      http.get(`${base}/employees/:id/time-account`, () =>
        HttpResponse.json({ detail: 'Zeitkonto nicht gefunden' }, { status: 404 }),
      ),
    )

    renderWithProviders(<TimeAccountCard employeeId="999" />)

    await waitFor(() => {
      expect(
        screen.getByText('Fehler beim Laden des Zeitkontos'),
      ).toBeInTheDocument()
    })
  })
})
