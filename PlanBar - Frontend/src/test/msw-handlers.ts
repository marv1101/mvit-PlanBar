import { http, HttpResponse } from 'msw'
import type {
  EmployeeResponseDTO,
  TimeAccountResponseDTO,
  TimeAccountAdjustDTO,
} from '../app/services/employeeService'
import type {
  RoleResponseDTO,
} from '../app/services/roleService'
import type {
  UserResponseDTO,
  AdminUserCreateResponseDTO,
  UnlinkedEmployeeDTO,
} from '../app/services/userService'
import type {
  ScheduleResponseDTO,
  ScheduleSummaryDTO,
  ShiftplanResponseDTO,
} from '../app/services/scheduleService'
import type {
  ShiftWishResponseDTO,
} from '../app/services/requestService'
import type {
  ThreadResponseDTO,
  ThreadDetailResponseDTO,
  MessageResponseDTO,
} from '../app/services/pinboardService'
import type { PaginatedResponse } from '../app/types'

const base = '/api/v1'

// ---------------------------------------------------------------------------
// Mock data stores
// ---------------------------------------------------------------------------

let nextId = 100

const mockUsers: UserResponseDTO[] = [
  { id: 1, username: 'admin', email: 'admin@planbar.test', role: 'admin', must_change_password: false, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-06-01T00:00:00Z', last_login: '2026-06-19T08:00:00Z' },
  { id: 2, username: 'mmueller', email: 'max@example.com', role: 'user', must_change_password: false, created_at: '2026-01-15T00:00:00Z', updated_at: '2026-05-20T00:00:00Z', last_login: '2026-06-18T07:30:00Z' },
]

const mockEmployees: EmployeeResponseDTO[] = [
  { id: 1, first_name: 'Max', last_name: 'Müller', email: 'max@example.com', color: '#3b82f6', working_hours_json: null, break_start: '12:00', break_end: '13:00', max_work_hours: 40, user_id: 2, role_ids: [1], created_at: '2026-01-15T00:00:00Z', updated_at: '2026-05-20T00:00:00Z' },
  { id: 2, first_name: 'Anna', last_name: 'Schmidt', email: 'anna@example.com', color: '#ef4444', working_hours_json: null, break_start: '12:00', break_end: '12:30', max_work_hours: 40, user_id: null, role_ids: [2], created_at: '2026-02-01T00:00:00Z', updated_at: '2026-05-10T00:00:00Z' },
]

const mockRoles: RoleResponseDTO[] = [
  { id: 1, name: 'Koch', color: '#3b82f6', permissions: null },
  { id: 2, name: 'Service', color: '#ef4444', permissions: null },
]

const mockSchedules: ScheduleResponseDTO[] = [
  {
    id: 1, name: 'KW 25', status: 'draft', week_type: 'A',
    start_date: '2026-06-15', end_date: '2026-06-21',
    role_requirements: null, shift_templates: null,
    tito_job_id: null,
    metadata_json: null, metrics_json: null, diagnostics_json: null,
    shiftplans: [],
    created_at: '2026-06-10T00:00:00Z', updated_at: '2026-06-10T00:00:00Z',
  },
]

const mockShiftplans: ShiftplanResponseDTO[] = []

const mockRequests: ShiftWishResponseDTO[] = [
  { id: 1, employee_id: 1, date: '2026-06-18', week: 1, type: 'preferred', note: 'Bitte Frühschicht', status: 'pending', reviewed_by: null, reviewed_at: null, rejection_reason: null },
  { id: 2, employee_id: 2, date: '2026-06-19', week: 1, type: 'unavailable', note: 'Arzttermin', status: 'pending', reviewed_by: null, reviewed_at: null, rejection_reason: null },
]

const mockThreads: ThreadResponseDTO[] = [
  { id: 1, title: 'Allgemeines', author_id: 1, author_name: 'admin', is_pinned: true, message_count: 3, last_message_at: '2026-06-18T10:00:00Z', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-06-18T10:00:00Z' },
]

const mockMessages: Record<number, MessageResponseDTO[]> = {
  1: [
    { id: 1, thread_id: 1, author_id: 1, author_name: 'admin', content: 'Willkommen im PlanBar Pinboard!', documents: [], created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
  ],
}

const mockTimeAccounts: TimeAccountResponseDTO[] = [
  {
    employee_id: 1, employee_name: 'Max Müller', current_balance: 12.5,
    history: [
      { week: 25, year: 2026, scheduled_hours: 40, contract_hours: 38, delta: 2, balance: 12.5, manual_adjustment: 0, adjustment_reason: null, total_change: 2 },
    ],
    projected: { from_schedule: 40, expected_balance_after: 14.5 },
  },
  {
    employee_id: 2, employee_name: 'Anna Schmidt', current_balance: 5.0,
    history: [
      { week: 25, year: 2026, scheduled_hours: 35, contract_hours: 38, delta: -3, balance: 5.0, manual_adjustment: 0, adjustment_reason: null, total_change: -3 },
    ],
    projected: { from_schedule: 35, expected_balance_after: 2.0 },
  },
]

let loginUser: UserResponseDTO | null = null

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function findEmployee(id: number) {
  return mockEmployees.find(e => e.id === id) ?? null
}

function findSchedule(id: number) {
  return mockSchedules.find(s => s.id === id) ?? null
}

function findThread(id: number) {
  return mockThreads.find(t => t.id === id) ?? null
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

export const handlers = [
  // -- Auth ----------------------------------------------------------------

  http.post(`${base}/users/login`, async ({ request }) => {
    const body = await request.json() as { email?: string; password?: string }
    const user = mockUsers.find(u => u.email === body.email)
    if (!user || body.password !== 'password') {
      return HttpResponse.json({ detail: 'Ungültige Anmeldedaten' }, { status: 401 })
    }
    loginUser = user
    return HttpResponse.json({ must_change_password: user.must_change_password })
  }),

  http.post(`${base}/users/logout`, () => {
    loginUser = null
    return HttpResponse.json({})
  }),

  http.post(`${base}/users/change-password`, async ({ request }) => {
    const body = await request.json() as { old_password?: string; new_password?: string }
    if (!body.old_password || !body.new_password) {
      return HttpResponse.json({ detail: 'Altes und neues Passwort erforderlich' }, { status: 400 })
    }
    const user = loginUser ?? mockUsers[0]
    user.must_change_password = false
    return HttpResponse.json(user satisfies UserResponseDTO)
  }),

  http.get(`${base}/users/me`, () => {
    const user = loginUser ?? mockUsers[0]
    return HttpResponse.json(user satisfies UserResponseDTO)
  }),

  // -- Users ---------------------------------------------------------------

  http.get(`${base}/users`, () => {
    const res: PaginatedResponse<UserResponseDTO> = { items: mockUsers, total: mockUsers.length, offset: 0, limit: 50 }
    return HttpResponse.json(res)
  }),

  http.post(`${base}/users/admin-create`, async ({ request }) => {
    const body = await request.json() as { username: string; email: string; role: string; employee_id?: number }
    const id = ++nextId
    const newUser: AdminUserCreateResponseDTO = {
      id, username: body.username, email: body.email, role: body.role,
      must_change_password: true,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      last_login: null, initial_password: 'geheim123',
    }
    mockUsers.push(newUser)
    return HttpResponse.json(newUser, { status: 201 })
  }),

  http.delete(`${base}/users/:id`, ({ params }) => {
    const idx = mockUsers.findIndex(u => u.id === Number(params.id))
    if (idx !== -1) mockUsers.splice(idx, 1)
    return HttpResponse.json({})
  }),

  http.get(`${base}/users/employees/unlinked`, () => {
    const unlinked: UnlinkedEmployeeDTO[] = mockEmployees
      .filter(e => e.user_id === null)
      .map(e => ({ id: e.id, first_name: e.first_name, last_name: e.last_name, email: e.email }))
    return HttpResponse.json(unlinked)
  }),

  // -- Employees -----------------------------------------------------------

  http.get(`${base}/employees`, () => {
    const res: PaginatedResponse<EmployeeResponseDTO> = { items: mockEmployees, total: mockEmployees.length, offset: 0, limit: 50 }
    return HttpResponse.json(res)
  }),

  http.get(`${base}/employees/time-accounts`, () => {
    return HttpResponse.json(mockTimeAccounts satisfies TimeAccountResponseDTO[])
  }),

  http.get(`${base}/employees/:id`, ({ params }) => {
    const emp = findEmployee(Number(params.id))
    if (!emp) return HttpResponse.json({ detail: 'Mitarbeiter nicht gefunden' }, { status: 404 })
    return HttpResponse.json(emp satisfies EmployeeResponseDTO)
  }),

  http.post(`${base}/employees`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    const id = ++nextId
    const emp: EmployeeResponseDTO = {
      id, first_name: body.first_name as string, last_name: body.last_name as string,
      email: (body.email as string) ?? null, color: (body.color as string) ?? null,
      working_hours_json: (body.working_hours_json as string) ?? null,
      break_start: (body.break_start as string) ?? null,
      break_end: (body.break_end as string) ?? null,
      max_work_hours: (body.max_work_hours as number) ?? null,
      user_id: null,
      role_ids: (body.role_ids as number[]) ?? [],
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }
    mockEmployees.push(emp)
    return HttpResponse.json(emp, { status: 201 })
  }),

  http.put(`${base}/employees/:id`, async ({ params, request }) => {
    const idx = mockEmployees.findIndex(e => e.id === Number(params.id))
    if (idx === -1) return HttpResponse.json({ detail: 'Mitarbeiter nicht gefunden' }, { status: 404 })
    const body = await request.json() as Partial<EmployeeResponseDTO>
    mockEmployees[idx] = { ...mockEmployees[idx], ...body, updated_at: new Date().toISOString() }
    return HttpResponse.json(mockEmployees[idx] satisfies EmployeeResponseDTO)
  }),

  http.delete(`${base}/employees/:id`, ({ params }) => {
    const idx = mockEmployees.findIndex(e => e.id === Number(params.id))
    if (idx !== -1) mockEmployees.splice(idx, 1)
    return HttpResponse.json({})
  }),

  // -- Time Accounts -------------------------------------------------------

  http.get(`${base}/employees/:id/time-account`, ({ params }) => {
    const ta = mockTimeAccounts.find(t => t.employee_id === Number(params.id))
    if (!ta) return HttpResponse.json({ detail: 'Zeitkonto nicht gefunden' }, { status: 404 })
    return HttpResponse.json(ta satisfies TimeAccountResponseDTO)
  }),

  http.post(`${base}/employees/:id/time-account/adjust`, async ({ params, request }) => {
    const body = await request.json() as TimeAccountAdjustDTO
    const ta = mockTimeAccounts.find(t => t.employee_id === Number(params.id))
    if (!ta) return HttpResponse.json({ detail: 'Zeitkonto nicht gefunden' }, { status: 404 })
    const delta = body.delta_hours
    const now = new Date()
    const startOfYear = new Date(now.getFullYear(), 0, 1)
    const week = Math.ceil((((now.getTime() - startOfYear.getTime()) / 86400000) + startOfYear.getDay() + 1) / 7)
    const entry = {
      week, year: now.getFullYear(),
      scheduled_hours: 0, contract_hours: 0, delta, balance: ta.current_balance + delta,
      manual_adjustment: delta, adjustment_reason: body.reason ?? null, total_change: delta,
    }
    ta.history.push(entry)
    ta.current_balance += delta
    return HttpResponse.json(ta satisfies TimeAccountResponseDTO)
  }),

  // -- Roles ---------------------------------------------------------------

  http.get(`${base}/roles`, () => {
    return HttpResponse.json(mockRoles satisfies RoleResponseDTO[])
  }),

  http.post(`${base}/roles`, async ({ request }) => {
    const body = await request.json() as { name: string; color?: string; permissions?: string }
    const id = ++nextId
    const role: RoleResponseDTO = {
      id, name: body.name, color: body.color ?? null, permissions: body.permissions ?? null,
    }
    mockRoles.push(role)
    return HttpResponse.json(role, { status: 201 })
  }),

  http.put(`${base}/roles/:id`, async ({ params, request }) => {
    const idx = mockRoles.findIndex(r => r.id === Number(params.id))
    if (idx === -1) return HttpResponse.json({ detail: 'Rolle nicht gefunden' }, { status: 404 })
    const body = await request.json() as Partial<RoleResponseDTO>
    mockRoles[idx] = { ...mockRoles[idx], ...body }
    return HttpResponse.json(mockRoles[idx] satisfies RoleResponseDTO)
  }),

  http.delete(`${base}/roles/:id`, ({ params }) => {
    const idx = mockRoles.findIndex(r => r.id === Number(params.id))
    if (idx !== -1) mockRoles.splice(idx, 1)
    return HttpResponse.json({})
  }),

  // -- Requests / Wishes ---------------------------------------------------

  http.get(`${base}/requests`, () => {
    const res: PaginatedResponse<ShiftWishResponseDTO> = { items: mockRequests, total: mockRequests.length, offset: 0, limit: 50 }
    return HttpResponse.json(res)
  }),

  http.post(`${base}/requests`, async ({ request }) => {
    const body = await request.json() as { employee_id: number; date: string; week?: number; type: string; note?: string }
    const id = ++nextId
    const wish: ShiftWishResponseDTO = {
      id, employee_id: body.employee_id, date: body.date, week: body.week ?? null,
      type: body.type, note: body.note ?? null, status: 'pending',
      reviewed_by: null, reviewed_at: null, rejection_reason: null,
    }
    mockRequests.push(wish)
    return HttpResponse.json(wish, { status: 201 })
  }),

  http.put(`${base}/requests/:id`, async ({ params, request }) => {
    const idx = mockRequests.findIndex(r => r.id === Number(params.id))
    if (idx === -1) return HttpResponse.json({ detail: 'Wunsch nicht gefunden' }, { status: 404 })
    const body = await request.json() as Partial<ShiftWishResponseDTO>
    mockRequests[idx] = { ...mockRequests[idx], ...body }
    return HttpResponse.json(mockRequests[idx] satisfies ShiftWishResponseDTO)
  }),

  http.delete(`${base}/requests/:id`, ({ params }) => {
    const idx = mockRequests.findIndex(r => r.id === Number(params.id))
    if (idx !== -1) mockRequests.splice(idx, 1)
    return HttpResponse.json({})
  }),

  http.put(`${base}/requests/:id/approve`, ({ params }) => {
    const idx = mockRequests.findIndex(r => r.id === Number(params.id))
    if (idx === -1) return HttpResponse.json({ detail: 'Wunsch nicht gefunden' }, { status: 404 })
    mockRequests[idx].status = 'approved'
    mockRequests[idx].reviewed_by = loginUser?.id ?? 1
    mockRequests[idx].reviewed_at = new Date().toISOString()
    return HttpResponse.json(mockRequests[idx] satisfies ShiftWishResponseDTO)
  }),

  http.put(`${base}/requests/:id/reject`, async ({ params, request }) => {
    const idx = mockRequests.findIndex(r => r.id === Number(params.id))
    if (idx === -1) return HttpResponse.json({ detail: 'Wunsch nicht gefunden' }, { status: 404 })
    const body = await request.json() as { rejection_reason?: string | null } | null
    mockRequests[idx].status = 'rejected'
    mockRequests[idx].reviewed_by = loginUser?.id ?? 1
    mockRequests[idx].reviewed_at = new Date().toISOString()
    mockRequests[idx].rejection_reason = body?.rejection_reason ?? null
    return HttpResponse.json(mockRequests[idx] satisfies ShiftWishResponseDTO)
  }),

  http.get(`${base}/schedules/:id/wishes/pending`, () => {
    const wishes = mockRequests.filter(r => r.status === 'pending')
    return HttpResponse.json(wishes satisfies ShiftWishResponseDTO[])
  }),

  // -- Schedules -----------------------------------------------------------

  http.get(`${base}/schedules`, () => {
    const res: PaginatedResponse<ScheduleResponseDTO> = { items: mockSchedules, total: mockSchedules.length, offset: 0, limit: 50 }
    return HttpResponse.json(res)
  }),

  http.post(`${base}/schedules`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    const id = ++nextId
    const incomingShiftplans = (body.shiftplans as Array<Record<string, unknown>>) ?? []
    const shiftplans: ShiftplanResponseDTO[] = incomingShiftplans.map((sp) => ({
      id: ++nextId, schedule_id: id,
      employee_id: sp.employee_id as number, date: sp.date as string,
      shift_id: sp.shift_id as string,
      start_time: sp.start_time as string, end_time: sp.end_time as string,
      week: (sp.week as string) ?? null,
      break_start: (sp.break_start as string) ?? null,
      break_end: (sp.break_end as string) ?? null,
      label: (sp.label as string) ?? null, notes: (sp.notes as string) ?? null,
      metadata_json: null, metrics_json: null, diagnostics_json: null,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }))
    mockShiftplans.push(...shiftplans)
    const schedule: ScheduleResponseDTO = {
      id, name: body.name as string, status: 'draft',
      week_type: (body.week_type as string) ?? null,
      start_date: (body.start_date as string) ?? null,
      end_date: (body.end_date as string) ?? null,
      role_requirements: (body.role_requirements as Record<string, number>) ?? null,
      shift_templates: (body.shift_templates as ScheduleResponseDTO['shift_templates']) ?? null,
      tito_job_id: null, metadata_json: null, metrics_json: null, diagnostics_json: null,
      shiftplans,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }
    mockSchedules.push(schedule)
    return HttpResponse.json(schedule, { status: 201 })
  }),

  http.put(`${base}/schedules/:id`, async ({ params, request }) => {
    const idx = mockSchedules.findIndex(s => s.id === Number(params.id))
    if (idx === -1) return HttpResponse.json({ detail: 'Schichtplan nicht gefunden' }, { status: 404 })
    const body = await request.json() as { name?: string; week_type?: string; status?: string }
    mockSchedules[idx] = { ...mockSchedules[idx], ...body, updated_at: new Date().toISOString() }
    return HttpResponse.json(mockSchedules[idx] satisfies ScheduleResponseDTO)
  }),

  http.delete(`${base}/schedules/:id`, ({ params }) => {
    const idx = mockSchedules.findIndex(s => s.id === Number(params.id))
    if (idx !== -1) mockSchedules.splice(idx, 1)
    return HttpResponse.json({})
  }),

  http.get(`${base}/schedules/:id`, ({ params }) => {
    const sched = findSchedule(Number(params.id))
    if (!sched) return HttpResponse.json({ detail: 'Schichtplan nicht gefunden' }, { status: 404 })
    return HttpResponse.json(sched satisfies ScheduleResponseDTO)
  }),

  http.post(`${base}/schedules/:id/submit`, ({ params }) => {
    const idx = mockSchedules.findIndex(s => s.id === Number(params.id))
    if (idx === -1) return HttpResponse.json({ detail: 'Schichtplan nicht gefunden' }, { status: 404 })
    mockSchedules[idx].status = 'submitted'
    mockSchedules[idx].tito_job_id = 42
    mockSchedules[idx].updated_at = new Date().toISOString()
    return HttpResponse.json(mockSchedules[idx] satisfies ScheduleResponseDTO)
  }),

  http.post(`${base}/schedules/:id/retry`, ({ params }) => {
    const idx = mockSchedules.findIndex(s => s.id === Number(params.id))
    if (idx === -1) return HttpResponse.json({ detail: 'Schichtplan nicht gefunden' }, { status: 404 })
    mockSchedules[idx].status = 'submitted'
    mockSchedules[idx].tito_job_id = 43
    mockSchedules[idx].updated_at = new Date().toISOString()
    return HttpResponse.json(mockSchedules[idx] satisfies ScheduleResponseDTO)
  }),

  http.get(`${base}/schedules/:id/summary`, ({ params }) => {
    const sched = findSchedule(Number(params.id))
    if (!sched) return HttpResponse.json({ detail: 'Schichtplan nicht gefunden' }, { status: 404 })
    const summary: ScheduleSummaryDTO = {
      id: sched.id, name: sched.name, status: sched.status,
      total_shifts: sched.shiftplans.length,
      total_employees: [...new Set(sched.shiftplans.map(sp => sp.employee_id))].length,
      date_range: sched.start_date && sched.end_date ? [sched.start_date, sched.end_date] : null,
    }
    return HttpResponse.json(summary satisfies ScheduleSummaryDTO)
  }),

  http.get(`${base}/schedules/:id/shifts`, ({ params }) => {
    const shifts = mockShiftplans.filter(sp => sp.schedule_id === Number(params.id))
    return HttpResponse.json(shifts satisfies ShiftplanResponseDTO[])
  }),

  http.put(`${base}/schedules/:id/shifts`, async ({ params, request }) => {
    const body = await request.json() as { shiftplans: Array<Record<string, unknown>> }
    const scheduleId = Number(params.id)
    const existing = mockShiftplans.filter(sp => sp.schedule_id !== scheduleId)
    const newShifts: ShiftplanResponseDTO[] = (body.shiftplans ?? []).map((s) => ({
      id: ++nextId, schedule_id: scheduleId,
      employee_id: s.employee_id as number, date: s.date as string,
      shift_id: s.shift_id as string,
      start_time: s.start_time as string, end_time: s.end_time as string,
      week: (s.week as string) ?? null,
      break_start: (s.break_start as string) ?? null,
      break_end: (s.break_end as string) ?? null,
      label: (s.label as string) ?? null,
      notes: (s.notes as string) ?? null,
      metadata_json: null, metrics_json: null, diagnostics_json: null,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }))
    mockShiftplans.length = 0
    mockShiftplans.push(...existing, ...newShifts)
    const sched = findSchedule(scheduleId)
    if (sched) {
      sched.shiftplans = newShifts
      sched.updated_at = new Date().toISOString()
    }
    return HttpResponse.json(sched ?? ({ id: scheduleId } as ScheduleResponseDTO))
  }),

  http.put(`${base}/schedules/:scheduleId/shifts/:shiftplanId`, async ({ params, request }) => {
    const scheduleId = Number(params.scheduleId)
    const shiftplanId = Number(params.shiftplanId)
    const body = await request.json() as Record<string, unknown>
    let sp = mockShiftplans.find(s => s.id === shiftplanId && s.schedule_id === scheduleId)
    if (!sp) {
      const id = ++nextId
      sp = {
        id, schedule_id: scheduleId,
        employee_id: (body.employee_id as number) ?? 0,
        date: (body.date as string) ?? '',
        shift_id: (body.shift_id as string) ?? '',
        start_time: (body.start_time as string) ?? '',
        end_time: (body.end_time as string) ?? '',
        week: (body.week as string) ?? null,
        break_start: (body.break_start as string) ?? null,
        break_end: (body.break_end as string) ?? null,
        label: (body.label as string) ?? null,
        notes: (body.notes as string) ?? null,
        metadata_json: null, metrics_json: null, diagnostics_json: null,
        created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
      }
      mockShiftplans.push(sp)
    } else {
      Object.assign(sp, body, { updated_at: new Date().toISOString() })
    }
    return HttpResponse.json(sp satisfies ShiftplanResponseDTO)
  }),

  // -- Pinboard ------------------------------------------------------------

  http.get(`${base}/pinboard/threads`, () => {
    return HttpResponse.json(mockThreads satisfies ThreadResponseDTO[])
  }),

  http.post(`${base}/pinboard/threads`, async ({ request }) => {
    const body = await request.json() as { title: string }
    const id = ++nextId
    const thread: ThreadResponseDTO = {
      id, title: body.title, author_id: loginUser?.id ?? 1,
      author_name: loginUser?.username ?? 'admin',
      is_pinned: false, message_count: 0, last_message_at: null,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }
    mockThreads.push(thread)
    mockMessages[id] = []
    return HttpResponse.json(thread, { status: 201 })
  }),

  http.get(`${base}/pinboard/threads/:id`, ({ params }) => {
    const thread = findThread(Number(params.id))
    if (!thread) return HttpResponse.json({ detail: 'Thread nicht gefunden' }, { status: 404 })
    const detail: ThreadDetailResponseDTO = {
      ...thread, messages: mockMessages[thread.id] ?? [],
    }
    return HttpResponse.json(detail satisfies ThreadDetailResponseDTO)
  }),

  http.delete(`${base}/pinboard/threads/:id`, ({ params }) => {
    const idx = mockThreads.findIndex(t => t.id === Number(params.id))
    if (idx !== -1) {
      delete mockMessages[mockThreads[idx].id]
      mockThreads.splice(idx, 1)
    }
    return HttpResponse.json({})
  }),

  http.delete(`${base}/pinboard/messages/:id`, ({ params }) => {
    const msgId = Number(params.id)
    for (const tid of Object.keys(mockMessages)) {
      const arr = mockMessages[Number(tid)]
      const idx = arr.findIndex(m => m.id === msgId)
      if (idx !== -1) { arr.splice(idx, 1); break }
    }
    return HttpResponse.json({})
  }),

  http.post(`${base}/pinboard/threads/:id/messages`, async ({ params, request }) => {
    const body = await request.json() as { content: string }
    const threadId = Number(params.id)
    const thread = findThread(threadId)
    if (!thread) return HttpResponse.json({ detail: 'Thread nicht gefunden' }, { status: 404 })
    const id = ++nextId
    const msg: MessageResponseDTO = {
      id, thread_id: threadId,
      author_id: loginUser?.id ?? 1, author_name: loginUser?.username ?? 'admin',
      content: body.content, documents: [],
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    }
    if (!mockMessages[threadId]) mockMessages[threadId] = []
    mockMessages[threadId].push(msg)
    thread.message_count += 1
    thread.last_message_at = msg.created_at
    return HttpResponse.json(msg, { status: 201 })
  }),

  http.get(`${base}/pinboard/documents/:id`, () => {
    return new HttpResponse(null, {
      status: 200,
      headers: { 'Content-Type': 'application/octet-stream' },
    })
  }),
]

// ---------------------------------------------------------------------------
// Server instance
// ---------------------------------------------------------------------------

import { setupServer } from 'msw/node'

export const server = setupServer(...handlers)
