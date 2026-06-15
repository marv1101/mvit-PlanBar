import { AppUser, Employee, Request, Role, Schedule, Shift, TiTODiagnostics, TiTOMetrics, WeekType, WishStatus } from '../types';
import type { EmployeeResponseDTO, EmployeeCreateDTO } from '../services/employeeService';
import type { RoleResponseDTO, RoleCreateDTO } from '../services/roleService';
import type { ShiftWishResponseDTO, ShiftWishCreateDTO, ShiftWishType } from '../services/requestService';
import type { ScheduleResponseDTO, ScheduleCreateDTO, ShiftplanResponseDTO, ShiftplanCreateDTO, ShiftTemplateEntryDTO } from '../services/scheduleService';

const FRONTEND_TYPE_TO_API: Record<string, ShiftWishType> = {
  urlaubswunsch: 'vacation',
  bevorzugt: 'preferred',
  'nicht-verfügbar': 'unavailable',
};

const API_TYPE_TO_FRONTEND: Record<string, string> = {
  vacation: 'urlaubswunsch',
  preferred: 'bevorzugt',
  unavailable: 'nicht-verfügbar',
};

function splitName(fullName: string): { first_name: string; last_name: string } {
  const idx = fullName.lastIndexOf(' ');
  if (idx === -1) return { first_name: fullName, last_name: fullName };
  return { first_name: fullName.slice(0, idx), last_name: fullName.slice(idx + 1) };
}

export function employeeFromResponse(dto: EmployeeResponseDTO): Employee {
  let workingHours = undefined;
  try {
    if (dto.working_hours_json) {
      workingHours = JSON.parse(dto.working_hours_json);
    }
  } catch (e) {
    console.error('[Mapper] working_hours_json parse failed:', e);
  }

  const breakDuration = dto.break_start && dto.break_end
    ? (() => {
        const [sh, sm] = dto.break_start!.split(':').map(Number);
        const [eh, em] = dto.break_end!.split(':').map(Number);
        return (eh * 60 + em) - (sh * 60 + sm);
      })()
    : 60;

  return {
    id: String(dto.id),
    name: `${dto.first_name} ${dto.last_name}`,
    email: dto.email || '',
    roles: dto.role_ids.map(String),
    workingHours: workingHours || {
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
    breakTime: {
      start: dto.break_start || '12:00',
      end: dto.break_end || '13:00',
      duration: breakDuration,
    },
    color: dto.color || '#3b82f6',
    maxWorkHours: dto.max_work_hours ?? 40,
  };
}

export function employeeToCreate(emp: Employee): EmployeeCreateDTO {
  const { first_name, last_name } = splitName(emp.name);
  return {
    first_name,
    last_name,
    email: emp.email,
    color: emp.color,
    working_hours_json: JSON.stringify(emp.workingHours),
    break_start: emp.breakTime.start,
    break_end: emp.breakTime.end,
    max_work_hours: emp.maxWorkHours,
    role_ids: emp.roles.length > 0 ? emp.roles.map(Number) : undefined,
  };
}

export function roleFromResponse(dto: RoleResponseDTO): Role {
  return {
    id: String(dto.id),
    name: dto.name,
    color: dto.color || '#3b82f6',
  };
}

export function roleToCreate(role: Role): RoleCreateDTO {
  return {
    name: role.name,
    color: role.color,
  };
}

export function requestFromResponse(dto: ShiftWishResponseDTO): Request {
  return {
    id: String(dto.id),
    employeeId: String(dto.employee_id),
    date: dto.date,
    week: dto.week === 2 ? 'B' : 'A' as WeekType,
    type: (API_TYPE_TO_FRONTEND[dto.type] || dto.type) as Request['type'],
    notes: dto.note || undefined,
    status: dto.status as WishStatus | undefined,
    reviewedBy: dto.reviewed_by,
    reviewedAt: dto.reviewed_at,
    rejectionReason: dto.rejection_reason,
  };
}

export function requestToCreate(req: Request): ShiftWishCreateDTO {
  return {
    employee_id: Number(req.employeeId),
    date: req.date,
    week: req.week === 'B' ? 2 : 1,
    type: FRONTEND_TYPE_TO_API[req.type] || (req.type as ShiftWishType),
    note: req.notes,
  };
}

export function shiftplanToShift(sp: ShiftplanResponseDTO): Shift {
  return {
    id: String(sp.id),
    employeeId: String(sp.employee_id),
    date: sp.date,
    week: (sp.week || 'A') as WeekType,
    startTime: sp.start_time,
    endTime: sp.end_time,
    breakStart: sp.break_start || undefined,
    breakEnd: sp.break_end || undefined,
  };
}

export function shiftToShiftplanCreate(scheduleId: number, shift: Shift): ShiftplanCreateDTO {
  return {
    employee_id: Number(shift.employeeId),
    date: shift.date,
    shift_id: shift.id,
    start_time: shift.startTime,
    end_time: shift.endTime,
    week: shift.week,
    break_start: shift.breakStart,
    break_end: shift.breakEnd,
  };
}

export function scheduleFromResponse(dto: ScheduleResponseDTO): Schedule {
  return {
    id: String(dto.id),
    name: dto.name,
    status: dto.status,
    startDate: dto.start_date || '',
    endDate: dto.end_date || '',
    shifts: (dto.shiftplans || []).map(shiftplanToShift),
    roleRequirements: dto.role_requirements || undefined,
    shiftTemplates: dto.shift_templates || undefined,
    weekType: dto.week_type ? (dto.week_type as WeekType) : undefined,
    titoJobId: dto.tito_job_id,
    diagnostics: dto.diagnostics_json as TiTODiagnostics | null | undefined,
    metrics: dto.metrics_json as TiTOMetrics | null | undefined,
  };
}

export function scheduleToCreate(schedule: Schedule, shiftplans: ShiftplanCreateDTO[]): ScheduleCreateDTO {
  return {
    name: schedule.name,
    start_date: schedule.startDate || undefined,
    end_date: schedule.endDate || undefined,
    role_requirements: schedule.roleRequirements,
    shift_templates: schedule.shiftTemplates,
    shiftplans,
  };
}

import type { UserResponseDTO } from '../services/userService';
import type {
  ThreadResponseDTO,
  ThreadDetailResponseDTO,
  MessageResponseDTO,
  DocumentResponseDTO,
} from '../services/pinboardService';
import {
  PinboardThread,
  PinboardThreadDetail,
  PinboardMessage,
  PinboardDocument,
  EmployeeTimeAccount,
  TimeAccountEntry,
  TimeAccountProjected,
} from '../types';

export function userFromResponse(dto: UserResponseDTO): AppUser {
  return {
    id: String(dto.id),
    username: dto.username,
    email: dto.email,
    role: dto.role === 'admin' ? 'admin' : 'employee',
    mustChangePassword: dto.must_change_password,
    lastLogin: dto.last_login,
  };
}

export function pinboardDocumentFromResponse(dto: DocumentResponseDTO): PinboardDocument {
  return {
    id: String(dto.id),
    messageId: String(dto.message_id),
    fileName: dto.file_name,
    fileSize: dto.file_size,
    mimeType: dto.mime_type,
    createdAt: dto.created_at,
  };
}

export function pinboardMessageFromResponse(dto: MessageResponseDTO): PinboardMessage {
  return {
    id: String(dto.id),
    threadId: String(dto.thread_id),
    authorId: String(dto.author_id),
    authorName: dto.author_name,
    content: dto.content,
    documents: (dto.documents || []).map(pinboardDocumentFromResponse),
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function pinboardThreadFromResponse(dto: ThreadResponseDTO): PinboardThread {
  return {
    id: String(dto.id),
    title: dto.title,
    authorId: String(dto.author_id),
    authorName: dto.author_name,
    isPinned: dto.is_pinned,
    messageCount: dto.message_count,
    lastMessageAt: dto.last_message_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function pinboardThreadDetailFromResponse(dto: ThreadDetailResponseDTO): PinboardThreadDetail {
  return {
    id: String(dto.id),
    title: dto.title,
    authorId: String(dto.author_id),
    authorName: dto.author_name,
    isPinned: dto.is_pinned,
    messages: (dto.messages || []).map(pinboardMessageFromResponse),
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}


export function timeAccountFromResponse(dto: TimeAccountResponseDTO): EmployeeTimeAccount {
  return {
    employeeId: dto.employee_id,
    employeeName: dto.employee_name,
    currentBalance: dto.current_balance,
    history: dto.history.map(e => ({
      week: e.week,
      year: e.year,
      scheduledHours: e.scheduled_hours,
      contractHours: e.contract_hours,
      delta: e.delta,
      balance: e.balance,
      manualAdjustment: e.manual_adjustment,
      adjustmentReason: e.adjustment_reason,
    })),
    projected: dto.projected ? {
      fromSchedule: dto.projected.from_schedule,
      expectedBalanceAfter: dto.projected.expected_balance_after,
    } : null,
  };
}
