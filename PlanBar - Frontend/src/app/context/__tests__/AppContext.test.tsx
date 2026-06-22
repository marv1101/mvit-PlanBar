import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../test/msw-handlers'
import { AppProvider, useApp } from '../AppContext'
import { AuthProvider } from '../AuthContext'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router'
import type { Employee, Request, Schedule, Role, WorkingHours } from '../../types'
import type { EmployeeResponseDTO } from '../../services/employeeService'
import type { RoleResponseDTO } from '../../services/roleService'
import type { ShiftWishResponseDTO } from '../../services/requestService'
import type { ScheduleResponseDTO } from '../../services/scheduleService'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const base = '/api/v1'

// ---------------------------------------------------------------------------
// Testdaten – DTOs für MSW-Overrides
// ---------------------------------------------------------------------------

const employeeDTOs: EmployeeResponseDTO[] = [
  { id: 1, first_name: 'Max', last_name: 'Müller', email: 'max@example.com', color: '#3b82f6', working_hours_json: null, break_start: '12:00', break_end: '13:00', max_work_hours: 40, user_id: 2, role_ids: [1], created_at: '2026-01-15T00:00:00Z', updated_at: '2026-05-20T00:00:00Z' },
  { id: 2, first_name: 'Anna', last_name: 'Schmidt', email: 'anna@example.com', color: '#ef4444', working_hours_json: null, break_start: '12:00', break_end: '12:30', max_work_hours: 40, user_id: null, role_ids: [2], created_at: '2026-02-01T00:00:00Z', updated_at: '2026-05-10T00:00:00Z' },
]

const roleDTOs: RoleResponseDTO[] = [
  { id: 1, name: 'Koch', color: '#3b82f6', permissions: null },
  { id: 2, name: 'Service', color: '#ef4444', permissions: null },
]

const requestDTOs: ShiftWishResponseDTO[] = [
  { id: 1, employee_id: 1, date: '2026-06-18', week: 1, type: 'preferred', note: 'Bitte Frühschicht', status: 'pending', reviewed_by: null, reviewed_at: null, rejection_reason: null },
  { id: 2, employee_id: 2, date: '2026-06-19', week: 1, type: 'unavailable', note: 'Arzttermin', status: 'pending', reviewed_by: null, reviewed_at: null, rejection_reason: null },
]

const scheduleDTOs: ScheduleResponseDTO[] = [
  { id: 1, name: 'KW 25', status: 'draft', week_type: 'A', start_date: '2026-06-15', end_date: '2026-06-21', role_requirements: null, shift_templates: null, tito_job_id: null, metadata_json: null, metrics_json: null, diagnostics_json: null, shiftplans: [], created_at: '2026-06-10T00:00:00Z', updated_at: '2026-06-10T00:00:00Z' },
]

// ---------------------------------------------------------------------------
// Testdaten – Frontend-Typen für CRUD-Operationen
// ---------------------------------------------------------------------------

const workingHoursDefault: WorkingHours = {
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
}

const newEmployee: Employee = {
  id: '', name: 'Neuer Mitarbeiter', email: 'neu@example.com', roles: ['1'],
  workingHours: workingHoursDefault,
  breakTime: { start: '12:00', end: '13:00', duration: 60 },
  color: '#ff0000', maxWorkHours: 40,
}

const updatedEmployee: Employee = {
  ...newEmployee, id: '1', name: 'Geänderter Mitarbeiter',
}

const newRequest: Request = {
  id: '', employeeId: '1', date: '2026-06-25', week: 'A',
  type: 'urlaubswunsch', notes: 'Testwunsch',
}

const updatedRequest: Request = {
  id: '1', employeeId: '1', date: '2026-06-18', week: 'A',
  type: 'bevorzugt', notes: 'Aktualisierter Wunsch',
}

const newSchedule: Schedule = {
  id: '', name: 'Neuer Schichtplan', status: 'draft',
  startDate: '2026-07-01', endDate: '2026-07-07', shifts: [],
}

const updatedSchedule: Schedule = {
  id: '1', name: 'Aktualisierter Schichtplan', status: 'submitted',
  startDate: '2026-06-15', endDate: '2026-06-21', shifts: [],
}

const newRole: Role = { id: '', name: 'Neue Rolle', color: '#00ff00' }

const updatedRole: Role = { id: '1', name: 'Geänderte Rolle', color: '#3b82f6' }

// ---------------------------------------------------------------------------
// Testkomponente
// ---------------------------------------------------------------------------

function AppConsumer() {
  const app = useApp()
  return (
    <div>
      <span data-testid="loading">{String(app.loading)}</span>
      <span data-testid="employees-count">{app.employees.length}</span>
      <span data-testid="employee-names">{app.employees.map(e => e.name).join(',')}</span>
      <span data-testid="roles-count">{app.roles.length}</span>
      <span data-testid="role-names">{app.roles.map(r => r.name).join(',')}</span>
      <span data-testid="requests-count">{app.requests.length}</span>
      <span data-testid="request-details">{app.requests.map(r => `${r.id}:${r.notes || ''}`).join(';')}</span>
      <span data-testid="schedules-count">{app.schedules.length}</span>
      <span data-testid="schedule-names">{app.schedules.map(s => s.name).join(',')}</span>
      <span data-testid="currentWeek">{app.currentWeek}</span>

      <button data-testid="add-employee-btn" onClick={() => app.addEmployee(newEmployee)} />
      <button data-testid="update-employee-btn" onClick={() => app.updateEmployee('1', updatedEmployee)} />
      <button data-testid="delete-employee-btn" onClick={() => app.deleteEmployee('1')} />
      <button data-testid="add-request-btn" onClick={() => app.addRequest(newRequest)} />
      <button data-testid="update-request-btn" onClick={() => app.updateRequest('1', updatedRequest)} />
      <button data-testid="delete-request-btn" onClick={() => app.deleteRequest('1')} />
      <button data-testid="add-schedule-btn" onClick={() => app.addSchedule(newSchedule)} />
      <button data-testid="update-schedule-btn" onClick={() => app.updateSchedule('1', updatedSchedule)} />
      <button data-testid="delete-schedule-btn" onClick={() => app.deleteSchedule('1')} />
      <button data-testid="add-role-btn" onClick={() => app.addRole(newRole)} />
      <button data-testid="update-role-btn" onClick={() => app.updateRole('1', updatedRole)} />
      <button data-testid="delete-role-btn" onClick={() => app.deleteRole('1')} />
      <button data-testid="refresh-btn" onClick={() => app.refresh()} />
    </div>
  )
}

function AppConsumerStandalone() {
  const app = useApp()
  return <span>{String(app.loading)}</span>
}

function renderApp(ui: React.ReactElement) {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <AppProvider>{ui}</AppProvider>
      </AuthProvider>
    </MemoryRouter>,
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AppContext', () => {
  beforeEach(() => {
    server.resetHandlers()
    server.use(
      http.get(`${base}/employees`, () => HttpResponse.json({ items: employeeDTOs, total: employeeDTOs.length, offset: 0, limit: 50 })),
      http.get(`${base}/roles`, () => HttpResponse.json(roleDTOs)),
      http.get(`${base}/requests`, () => HttpResponse.json({ items: requestDTOs, total: requestDTOs.length, offset: 0, limit: 50 })),
      http.get(`${base}/schedules`, () => HttpResponse.json({ items: scheduleDTOs, total: scheduleDTOs.length, offset: 0, limit: 50 })),
    )
  })

  it('lädt Mitarbeiter, Rollen, Wünsche und Schichtpläne beim Mounten', async () => {
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('employees-count')).toHaveTextContent('2')
    expect(screen.getByTestId('roles-count')).toHaveTextContent('2')
    expect(screen.getByTestId('requests-count')).toHaveTextContent('2')
    expect(screen.getByTestId('schedules-count')).toHaveTextContent('1')
  })

  it('kartiert Antworten durch Mapper', async () => {
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    expect(screen.getByTestId('employee-names')).toHaveTextContent(/Max Müller/)
    expect(screen.getByTestId('employee-names')).toHaveTextContent(/Anna Schmidt/)
    expect(screen.getByTestId('role-names')).toHaveTextContent(/Koch/)
    expect(screen.getByTestId('role-names')).toHaveTextContent(/Service/)
    expect(screen.getByTestId('schedule-names')).toHaveTextContent(/KW 25/)
  })

  it('durchläuft Ladezustände', () => {
    renderApp(<AppConsumer />)

    // initial loading true
    expect(screen.getByTestId('loading')).toHaveTextContent('true')
  })

  it('addEmployee erstellt Mitarbeiter und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('add-employee-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('employees-count')).toHaveTextContent('3')
    })
    expect(screen.getByTestId('employee-names')).toHaveTextContent(/Neuer Mitarbeiter/)
  })

  it('updateEmployee ruft API auf und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('update-employee-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('employee-names')).toHaveTextContent(/Geänderter Mitarbeiter/)
    })
    expect(screen.getByTestId('employee-names')).not.toHaveTextContent(/Max Müller/)
  })

  it('deleteEmployee ruft API auf und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('delete-employee-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('employees-count')).toHaveTextContent('1')
    })
    // Auch zugehörige Anfragen werden gelöscht
    expect(screen.getByTestId('requests-count')).toHaveTextContent('1')
  })

  it('addRequest erstellt Wunsch und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('add-request-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('requests-count')).toHaveTextContent('3')
    })
  })

  it('updateRequest ruft API auf und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('update-request-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('request-details')).toHaveTextContent(/Aktualisierter Wunsch/)
    })
  })

  it('deleteRequest ruft API auf und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('delete-request-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('requests-count')).toHaveTextContent('1')
    })
    expect(screen.getByTestId('request-details')).not.toHaveTextContent(/Bitte Frühschicht/)
  })

  it('addSchedule (optimistisch) fügt Schichtplan zum State hinzu', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })
    expect(screen.getByTestId('schedules-count')).toHaveTextContent('1')

    await user.click(screen.getByTestId('add-schedule-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('schedules-count')).toHaveTextContent('2')
    })
    expect(screen.getByTestId('schedule-names')).toHaveTextContent(/Neuer Schichtplan/)
  })

  it('updateSchedule ruft API auf und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('update-schedule-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('schedule-names')).toHaveTextContent(/Aktualisierter Schichtplan/)
    })
    expect(screen.getByTestId('schedule-names')).not.toHaveTextContent(/KW 25/)
  })

  it('deleteSchedule ruft API auf und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('delete-schedule-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('schedules-count')).toHaveTextContent('0')
    })
  })

  it('addRole erstellt Rolle und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('add-role-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('roles-count')).toHaveTextContent('3')
    })
    expect(screen.getByTestId('role-names')).toHaveTextContent(/Neue Rolle/)
  })

  it('updateRole ruft API auf und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('update-role-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('role-names')).toHaveTextContent(/Geänderte Rolle/)
    })
    expect(screen.getByTestId('role-names')).not.toHaveTextContent(/Koch/)
  })

  it('deleteRole ruft API auf und aktualisiert State', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    await user.click(screen.getByTestId('delete-role-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('roles-count')).toHaveTextContent('1')
    })
  })

  it('currentWeek initialisiert von getWeekType', async () => {
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })

    const week = screen.getByTestId('currentWeek').textContent
    expect(week === 'A' || week === 'B').toBe(true)
  })

  it('refresh lädt alle Daten neu', async () => {
    const user = userEvent.setup()
    renderApp(<AppConsumer />)

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false')
    })
    expect(screen.getByTestId('employees-count')).toHaveTextContent('2')

    server.use(
      http.get(`${base}/employees`, () => HttpResponse.json({ items: [employeeDTOs[0]], total: 1, offset: 0, limit: 50 })),
    )

    await user.click(screen.getByTestId('refresh-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('employees-count')).toHaveTextContent('1')
    })
    expect(screen.getByTestId('employee-names')).toHaveTextContent(/Max Müller/)
    expect(screen.getByTestId('employee-names')).not.toHaveTextContent(/Anna Schmidt/)
  })

  it('useApp wirft Fehler ohne AppProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<AppConsumerStandalone />)).toThrow(
      'useApp must be used within an AppProvider',
    )
    consoleSpy.mockRestore()
  })
})
