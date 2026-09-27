import React from 'react'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider, type Query } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/msw-handlers'
import { KIOSK_REFETCH_INTERVAL_MS, type KioskBoardDTO } from '../../services/kioskService'
import { useKioskBoard } from '../useKioskBoard'
import { describe, it, expect, beforeAll, beforeEach } from 'vitest'

const base = '/api/v1'

const mockBoard = {
  window_start: '2026-09-21',
  window_end: '2026-10-04',
  team: { id: 3, name: 'Pflege' },
  employees: [{ id: 1, name: 'Anna Schmidt', color: '#ef4444' }],
  shifts: [
    {
      employee_id: 1, date: '2026-09-22',
      start_time: '08:00:00', end_time: '16:00:00',
      break_start: null, break_end: null,
      label: 'Frueh', schedule_name: 'KW 38',
    },
  ],
}

let boardRequest: Request | null = null

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return { Wrapper, queryClient }
}

describe('useKioskBoard', () => {
  beforeAll(() => {
    server.use(
      http.get(`${base}/kiosk/board`, ({ request }) => {
        boardRequest = request
        return HttpResponse.json(mockBoard)
      }),
    )
  })

  beforeEach(() => {
    boardRequest = null
    server.resetHandlers()
    // Handler muss nach resetHandlers erneut installiert werden
    server.use(
      http.get(`${base}/kiosk/board`, ({ request }) => {
        boardRequest = request
        return HttpResponse.json(mockBoard)
      }),
    )
  })

  it('exportiert KIOSK_REFETCH_INTERVAL_MS = 3.600.000 ms (1 Stunde)', () => {
    expect(KIOSK_REFETCH_INTERVAL_MS).toBe(60 * 60 * 1000)
    expect(KIOSK_REFETCH_INTERVAL_MS).toBe(3600000)
  })

  it('konfiguriert refetchInterval des Query auf KIOSK_REFETCH_INTERVAL_MS', async () => {
    const { Wrapper, queryClient } = createWrapper()
    const { result } = renderHook(() => useKioskBoard(), { wrapper: Wrapper })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    const query = queryClient.getQueryCache().find({
      queryKey: ['kiosk-board', null],
    }) as Query<KioskBoardDTO, Error, KioskBoardDTO, ReadonlyArray<string | number | null>> | undefined
    expect(query).toBeDefined()
    const options = query!.options as unknown as {
      refetchInterval?: number | ((query: Query) => number | false)
      refetchOnWindowFocus?: boolean
      retry?: number | boolean | ((failureCount: number, error: Error) => boolean)
    }
    expect(options.refetchInterval).toBe(KIOSK_REFETCH_INTERVAL_MS)
    expect(options.refetchOnWindowFocus).toBe(false)
    expect(options.retry).toBe(1)
  })

  it('ruft /kiosk/board ab und gibt das Board zurück', async () => {
    const { Wrapper } = createWrapper()
    const { result } = renderHook(() => useKioskBoard(), { wrapper: Wrapper })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })
    expect(result.current.data?.team?.name).toBe('Pflege')
    expect(result.current.data?.employees[0].name).toBe('Anna Schmidt')
    expect(boardRequest).not.toBeNull()
    expect(boardRequest!.credentials).toBe('include')
  })

  it('übergibt team_id als Query-Parameter', async () => {
    const { Wrapper, queryClient } = createWrapper()
    const { result } = renderHook(() => useKioskBoard(3), { wrapper: Wrapper })

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })
    expect(new URL(boardRequest!.url).searchParams.get('team_id')).toBe('3')
    expect(queryKeyOf(queryClient)).toEqual(['kiosk-board', 3])
  })
})

function queryKeyOf(queryClient: QueryClient) {
  const queries = queryClient.getQueryCache().getAll()
  return queries[queries.length - 1]?.queryKey
}
