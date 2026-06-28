import React from 'react'
import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter, createMemoryRouter } from 'react-router'
import { DndProvider } from 'react-dnd'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { TouchBackend } from 'react-dnd-touch-backend'
import { AuthContext } from '../app/context/AuthContext'
import { AppContext } from '../app/context/AppContext'
import type { Employee, Schedule, WeekType } from '../app/types'

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

export const mockEmployees: Employee[] = [
  {
    id: '1',
    name: 'Max Müller',
    email: 'max@example.com',
    roles: ['Koch'],
    workingHours: {
      weekA: {
        monday: { start: '08:00', end: '18:00', enabled: true },
        tuesday: { start: '08:00', end: '18:00', enabled: true },
        wednesday: { start: '08:00', end: '18:00', enabled: true },
        thursday: { start: '08:00', end: '18:00', enabled: true },
        friday: { start: '08:00', end: '18:00', enabled: true },
        saturday: { start: '08:00', end: '18:00', enabled: false },
        sunday: { start: '08:00', end: '18:00', enabled: false },
      },
      weekB: {
        monday: { start: '08:00', end: '18:00', enabled: true },
        tuesday: { start: '08:00', end: '18:00', enabled: true },
        wednesday: { start: '08:00', end: '18:00', enabled: true },
        thursday: { start: '08:00', end: '18:00', enabled: true },
        friday: { start: '08:00', end: '18:00', enabled: true },
        saturday: { start: '08:00', end: '18:00', enabled: false },
        sunday: { start: '08:00', end: '18:00', enabled: false },
      },
    },
    breakTime: { start: '12:00', end: '13:00', duration: 60 },
    color: '#3b82f6',
  },
  {
    id: '2',
    name: 'Anna Schmidt',
    email: 'anna@example.com',
    roles: ['Service'],
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

export const mockSchedule: Schedule = {
  id: '1',
  name: 'Test Woche',
  status: 'draft',
  startDate: '2026-06-15',
  endDate: '2026-06-21',
  shifts: [
    {
      id: 'shift-1', employeeId: '1', date: '2026-06-15', week: 'A',
      startTime: '08:00', endTime: '18:00', breakStart: '12:00', breakEnd: '13:00', label: 'Backoffice',
    },
    {
      id: 'shift-2', employeeId: '2', date: '2026-06-15', week: 'A',
      startTime: '09:00', endTime: '17:00', breakStart: '12:00', breakEnd: '12:30',
    },
  ],
}

// ---------------------------------------------------------------------------
// Mock users
// ---------------------------------------------------------------------------

export const mockAdminUser = {
  id: '1',
  name: 'admin',
  email: 'admin@planbar.test',
  role: 'admin' as const,
  employeeId: undefined,
}

export const mockEmployeeUser = {
  id: '2',
  name: 'Max Müller',
  email: 'max@example.com',
  role: 'employee' as const,
  employeeId: '1',
}

export const mockUser = mockAdminUser

// ---------------------------------------------------------------------------
// Mock context values
// ---------------------------------------------------------------------------

export const mockAuthContext = {
  user: mockUser,
  login: vi.fn().mockResolvedValue({ success: true, mustChangePassword: false }),
  logout: vi.fn(),
  isLoading: false,
  mustChangePassword: false,
  changePassword: vi.fn().mockResolvedValue(true),
}

export const mockAppContext = {
  employees: mockEmployees,
  addEmployee: vi.fn(),
  updateEmployee: vi.fn(),
  deleteEmployee: vi.fn(),
  requests: [],
  addRequest: vi.fn(),
  updateRequest: vi.fn(),
  deleteRequest: vi.fn(),
  schedules: [mockSchedule],
  addSchedule: vi.fn(),
  updateSchedule: vi.fn(),
  deleteSchedule: vi.fn(),
  currentSchedule: null,
  setCurrentSchedule: vi.fn(),
  currentWeek: 'A' as WeekType,
  setCurrentWeek: vi.fn(),
  roles: [],
  addRole: vi.fn(),
  updateRole: vi.fn(),
  deleteRole: vi.fn(),
  loading: false,
  refresh: vi.fn().mockResolvedValue(undefined),
}

// ---------------------------------------------------------------------------
// Wrappers
// ---------------------------------------------------------------------------

export function AuthTestWrapper({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter>
      <AuthContext.Provider value={mockAuthContext as any}>
        {children}
      </AuthContext.Provider>
    </MemoryRouter>
  )
}

const testQueryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false, gcTime: 0 },
  },
})

export function AppAndAuthTestWrapper({
  children,
  initialEntries = ['/'],
}: {
  children: React.ReactNode
  initialEntries?: string[]
}) {
  return (
    <MemoryRouter initialEntries={initialEntries}>
      <AuthContext.Provider value={mockAuthContext as any}>
        <AppContext.Provider value={mockAppContext as any}>
          <QueryClientProvider client={testQueryClient}>
            <DndProvider backend={TouchBackend} options={{ enableMouseEvents: true }}>
              {children}
            </DndProvider>
          </QueryClientProvider>
        </AppContext.Provider>
      </AuthContext.Provider>
    </MemoryRouter>
  )
}

// ---------------------------------------------------------------------------
// Router helper
// ---------------------------------------------------------------------------

export function createMockRouter(entries: string[] = ['/']) {
  return createMemoryRouter([{ path: '*', element: null }], { initialEntries: entries })
}

// @deprecated Use AppAndAuthTestWrapper instead
export const TestWrapper = AppAndAuthTestWrapper

// ---------------------------------------------------------------------------
// Render helpers
// ---------------------------------------------------------------------------

export function renderWithProviders(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & { initialEntries?: string[] },
) {
  const { initialEntries = ['/'], ...renderOptions } = options ?? {}

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <AppAndAuthTestWrapper initialEntries={initialEntries}>{children}</AppAndAuthTestWrapper>
  }

  return { ...render(ui, { wrapper: Wrapper, ...renderOptions }) }
}

export function renderWithAuth(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & { initialEntries?: string[] },
) {
  const { initialEntries = ['/'], ...renderOptions } = options ?? {}

  function Wrapper({ children }: { children: React.ReactNode }) {
    return <AuthTestWrapper>{children}</AuthTestWrapper>
  }

  return { ...render(ui, { wrapper: Wrapper, ...renderOptions }) }
}

export * from '@testing-library/react'
