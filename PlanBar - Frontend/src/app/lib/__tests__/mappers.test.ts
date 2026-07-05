import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  employeeFromResponse,
  employeeToCreate,
  roleFromResponse,
  roleToCreate,
  requestFromResponse,
  requestToCreate,
  shiftplanToShift,
  shiftToShiftplanCreate,
  scheduleFromResponse,
  scheduleToCreate,
  userFromResponse,
  pinboardDocumentFromResponse,
  pinboardMessageFromResponse,
  pinboardThreadFromResponse,
  pinboardThreadDetailFromResponse,
  timeAccountFromResponse,
} from '../mappers';

const defaultWorkingHours = {
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
};

describe('employeeFromResponse', () => {
  const baseDto = {
    id: 1,
    first_name: 'Max',
    last_name: 'Mustermann',
    email: 'max@example.com',
    color: '#ff0000',
    working_hours_json: JSON.stringify(defaultWorkingHours),
    break_start: '12:00',
    break_end: '13:00',
    max_work_hours: 35,
    user_id: 10,
    role_ids: [1, 2],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  it('bildet ein vollständiges DTO auf Employee ab', () => {
    const result = employeeFromResponse(baseDto);
    expect(result.id).toBe('1');
    expect(result.name).toBe('Max Mustermann');
    expect(result.email).toBe('max@example.com');
    expect(result.roles).toEqual(['1', '2']);
    expect(result.workingHours).toEqual(defaultWorkingHours);
    expect(result.breakTime).toEqual({ start: '12:00', end: '13:00', duration: 60 });
    expect(result.color).toBe('#ff0000');
    expect(result.maxWorkHours).toBe(35);
  });

  it('setzt email auf leeren String bei null', () => {
    const dto = { ...baseDto, email: null };
    const result = employeeFromResponse(dto);
    expect(result.email).toBe('');
  });

  it('verwendet Fallback-Farbe bei null', () => {
    const dto = { ...baseDto, color: null };
    const result = employeeFromResponse(dto);
    expect(result.color).toBe('#3b82f6');
  });

  it('verwendet maxWorkHours=40 bei null', () => {
    const dto = { ...baseDto, max_work_hours: null };
    const result = employeeFromResponse(dto);
    expect(result.maxWorkHours).toBe(40);
  });

  it('setzt roles auf leeres Array bei leerem role_ids', () => {
    const dto = { ...baseDto, role_ids: [] };
    const result = employeeFromResponse(dto);
    expect(result.roles).toEqual([]);
  });

  it('parst working_hours_json korrekt', () => {
    const custom = {
      weekA: {
        monday: { start: '06:00', end: '14:00', enabled: true },
        tuesday: { start: '06:00', end: '14:00', enabled: true },
        wednesday: { start: '06:00', end: '14:00', enabled: true },
        thursday: { start: '06:00', end: '14:00', enabled: true },
        friday: { start: '06:00', end: '14:00', enabled: true },
        saturday: { start: '08:00', end: '12:00', enabled: true },
        sunday: { start: '09:00', end: '13:00', enabled: false },
      },
      weekB: {
        monday: { start: '06:00', end: '14:00', enabled: true },
        tuesday: { start: '06:00', end: '14:00', enabled: true },
        wednesday: { start: '06:00', end: '14:00', enabled: true },
        thursday: { start: '06:00', end: '14:00', enabled: true },
        friday: { start: '06:00', end: '14:00', enabled: true },
        saturday: { start: '08:00', end: '12:00', enabled: true },
        sunday: { start: '09:00', end: '13:00', enabled: false },
      },
    };
    const dto = { ...baseDto, working_hours_json: JSON.stringify(custom) };
    const result = employeeFromResponse(dto);
    expect(result.workingHours).toEqual(custom);
  });

  it('verwendet Default-Arbeitszeiten bei null working_hours_json', () => {
    const dto = { ...baseDto, working_hours_json: null };
    const result = employeeFromResponse(dto);
    expect(result.workingHours).toEqual(defaultWorkingHours);
  });

  it('verwendet Default-Arbeitszeiten bei defektem JSON (graceful fallback)', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const dto = { ...baseDto, working_hours_json: 'kein-json' };
    const result = employeeFromResponse(dto);
    expect(result.workingHours).toEqual(defaultWorkingHours);
    expect(consoleSpy).toHaveBeenCalledOnce();
    consoleSpy.mockRestore();
  });

  it('berechnet breakDuration = 60 bei fehlenden break_start/break_end', () => {
    const dto = { ...baseDto, break_start: null, break_end: null };
    const result = employeeFromResponse(dto);
    expect(result.breakTime).toEqual({ start: '12:00', end: '13:00', duration: 60 });
  });

  it('berechnet breakDuration korrekt bei vorhandenen break-Zeiten', () => {
    const dto = { ...baseDto, break_start: '11:30', break_end: '12:45' };
    const result = employeeFromResponse(dto);
    expect(result.breakTime).toEqual({ start: '11:30', end: '12:45', duration: 75 });
  });

  it('konvertiert id zu String', () => {
    const result = employeeFromResponse(baseDto);
    expect(result.id).toBe('1');
  });
});

describe('employeeToCreate', () => {
  it('bildet Employee auf CreateDTO ab', () => {
    const emp = {
      id: '1',
      name: 'Max Mustermann',
      email: 'max@example.com',
      roles: ['1', '2'],
      workingHours: defaultWorkingHours,
      breakTime: { start: '12:00', end: '13:00', duration: 60 },
      color: '#ff0000',
      maxWorkHours: 35,
    };
    const result = employeeToCreate(emp);
    expect(result.first_name).toBe('Max');
    expect(result.last_name).toBe('Mustermann');
    expect(result.email).toBe('max@example.com');
    expect(result.color).toBe('#ff0000');
    expect(result.working_hours_json).toBe(JSON.stringify(defaultWorkingHours));
    expect(result.break_start).toBe('12:00');
    expect(result.break_end).toBe('13:00');
    expect(result.max_work_hours).toBe(35);
    expect(result.role_ids).toEqual([1, 2]);
  });

  it('behandelt Single-Word-Namen (last_name = first_name)', () => {
    const emp = {
      id: '2',
      name: 'Solo',
      email: 'solo@example.com',
      roles: [],
      workingHours: defaultWorkingHours,
      breakTime: { start: '12:00', end: '13:00', duration: 60 },
      color: '#00ff00',
    };
    const result = employeeToCreate(emp);
    expect(result.first_name).toBe('Solo');
    expect(result.last_name).toBe('Solo');
  });

  it('behandelt leeren Namen', () => {
    const emp = {
      id: '3',
      name: '',
      email: 'empty@example.com',
      roles: [],
      workingHours: defaultWorkingHours,
      breakTime: { start: '12:00', end: '13:00', duration: 60 },
      color: '#0000ff',
    };
    const result = employeeToCreate(emp);
    expect(result.first_name).toBe('');
    expect(result.last_name).toBe('');
  });

  it('setzt role_ids auf undefined bei leerem roles-Array', () => {
    const emp = {
      id: '4',
      name: 'Hans Wurst',
      email: 'hans@example.com',
      roles: [],
      workingHours: defaultWorkingHours,
      breakTime: { start: '12:00', end: '13:00', duration: 60 },
      color: '#ff00ff',
    };
    const result = employeeToCreate(emp);
    expect(result.role_ids).toBeUndefined();
  });

  it('trennt Vor- und Nachnamen bei mehreren Vornamen', () => {
    const emp = {
      id: '5',
      name: 'Hans Peter Müller',
      email: 'hpm@example.com',
      roles: [],
      workingHours: defaultWorkingHours,
      breakTime: { start: '12:00', end: '13:00', duration: 60 },
      color: '#fff',
    };
    const result = employeeToCreate(emp);
    expect(result.first_name).toBe('Hans Peter');
    expect(result.last_name).toBe('Müller');
  });
});

describe('roleFromResponse', () => {
  it('bildet RoleResponseDTO auf Role ab', () => {
    const dto = { id: 5, name: 'Schichtleiter', color: '#ff0000', permissions: null };
    const result = roleFromResponse(dto);
    expect(result.id).toBe('5');
    expect(result.name).toBe('Schichtleiter');
    expect(result.color).toBe('#ff0000');
  });

  it('verwendet Fallback-Farbe bei null', () => {
    const dto = { id: 6, name: 'Azubi', color: null, permissions: null };
    const result = roleFromResponse(dto);
    expect(result.color).toBe('#3b82f6');
  });
});

describe('roleToCreate', () => {
  it('bildet Role auf RoleCreateDTO ab', () => {
    const role = { id: '7', name: 'Manager', color: '#00ff00' };
    const result = roleToCreate(role);
    expect(result.name).toBe('Manager');
    expect(result.color).toBe('#00ff00');
  });
});

describe('requestFromResponse', () => {
  const baseDto = {
    id: 10,
    employee_id: 3,
    date: '2024-06-15',
    week: 1,
    type: 'vacation',
    note: 'Urlaub',
    status: 'approved',
    reviewed_by: 1,
    reviewed_at: '2024-06-10T10:00:00Z',
    rejection_reason: null,
  };

  it('bildet einen vacation-Request (week=1 -> A) ab', () => {
    const result = requestFromResponse(baseDto);
    expect(result.id).toBe('10');
    expect(result.employeeId).toBe('3');
    expect(result.date).toBe('2024-06-15');
    expect(result.week).toBe('A');
    expect(result.type).toBe('urlaubswunsch');
    expect(result.notes).toBe('Urlaub');
    expect(result.status).toBe('approved');
    expect(result.reviewedBy).toBe(1);
    expect(result.reviewedAt).toBe('2024-06-10T10:00:00Z');
  });

  it('bildet preferred-Request ab', () => {
    const dto = { ...baseDto, type: 'preferred' };
    const result = requestFromResponse(dto);
    expect(result.type).toBe('bevorzugt');
  });

  it('bildet unavailable-Request ab', () => {
    const dto = { ...baseDto, type: 'unavailable' };
    const result = requestFromResponse(dto);
    expect(result.type).toBe('nicht-verfügbar');
  });

  it('setzt week=A bei week=2 -> B', () => {
    const dto = { ...baseDto, week: 2 };
    const result = requestFromResponse(dto);
    expect(result.week).toBe('B');
  });

  it('setzt week=A bei week=null', () => {
    const dto = { ...baseDto, week: null };
    const result = requestFromResponse(dto);
    expect(result.week).toBe('A');
  });

  it('setzt notes=undefined bei null', () => {
    const dto = { ...baseDto, note: null };
    const result = requestFromResponse(dto);
    expect(result.notes).toBeUndefined();
  });

  it('behandelt unbekannten type als Fallback', () => {
    const dto = { ...baseDto, type: 'unknown-type' };
    const result = requestFromResponse(dto);
    expect(result.type).toBe('unknown-type');
  });
});

describe('requestToCreate', () => {
  it('bildet Request mit type=urlaubswunsch auf ShiftWishCreateDTO ab', () => {
    const req = {
      id: '10',
      employeeId: '3',
      date: '2024-06-15',
      week: 'A' as const,
      type: 'urlaubswunsch' as const,
      notes: 'Bitte genehmigen',
    };
    const result = requestToCreate(req);
    expect(result.employee_id).toBe(3);
    expect(result.date).toBe('2024-06-15');
    expect(result.week).toBe(1);
    expect(result.type).toBe('vacation');
    expect(result.note).toBe('Bitte genehmigen');
  });

  it('bildet bevorzugt -> preferred ab', () => {
    const req = {
      id: '11',
      employeeId: '4',
      date: '2024-06-16',
      week: 'A' as const,
      type: 'bevorzugt' as const,
    };
    const result = requestToCreate(req);
    expect(result.type).toBe('preferred');
  });

  it('bildet nicht-verfügbar -> unavailable ab', () => {
    const req = {
      id: '12',
      employeeId: '5',
      date: '2024-06-17',
      week: 'A' as const,
      type: 'nicht-verfügbar' as const,
    };
    const result = requestToCreate(req);
    expect(result.type).toBe('unavailable');
  });

  it('setzt week=2 bei week=B', () => {
    const req = {
      id: '13',
      employeeId: '6',
      date: '2024-06-18',
      week: 'B' as const,
      type: 'urlaubswunsch' as const,
    };
    const result = requestToCreate(req);
    expect(result.week).toBe(2);
  });

  it('setzt week=1 bei week=A', () => {
    const req = {
      id: '14',
      employeeId: '7',
      date: '2024-06-19',
      week: 'A' as const,
      type: 'urlaubswunsch' as const,
    };
    const result = requestToCreate(req);
    expect(result.week).toBe(1);
  });
});

describe('shiftplanToShift', () => {
  it('bildet vollständigen Shiftplan auf Shift ab', () => {
    const sp = {
      id: 20,
      schedule_id: 1,
      employee_id: 5,
      date: '2024-07-01',
      shift_id: 's1',
      start_time: '08:00',
      end_time: '16:00',
      week: 'A',
      break_start: '12:00',
      break_end: '12:30',
      label: 'Frühschicht',
      notes: null,
      metadata_json: null,
      metrics_json: null,
      diagnostics_json: null,
      created_at: '',
      updated_at: '',
    };
    const result = shiftplanToShift(sp);
    expect(result.id).toBe('20');
    expect(result.employeeId).toBe('5');
    expect(result.date).toBe('2024-07-01');
    expect(result.week).toBe('A');
    expect(result.startTime).toBe('08:00');
    expect(result.endTime).toBe('16:00');
    expect(result.breakStart).toBe('12:00');
    expect(result.breakEnd).toBe('12:30');
    expect(result.label).toBe('Frühschicht');
  });

  it('behandelt fehlende break-Zeiten', () => {
    const sp = {
      id: 21,
      schedule_id: 1,
      employee_id: 6,
      date: '2024-07-02',
      shift_id: 's2',
      start_time: '14:00',
      end_time: '22:00',
      week: 'B',
      break_start: null,
      break_end: null,
      label: null,
      notes: null,
      metadata_json: null,
      metrics_json: null,
      diagnostics_json: null,
      created_at: '',
      updated_at: '',
    };
    const result = shiftplanToShift(sp);
    expect(result.breakStart).toBeUndefined();
    expect(result.breakEnd).toBeUndefined();
    expect(result.label).toBeUndefined();
  });

  it('behandelt nur break_start (ohne break_end)', () => {
    const sp = {
      id: 22,
      schedule_id: 1,
      employee_id: 7,
      date: '2024-07-03',
      shift_id: 's3',
      start_time: '06:00',
      end_time: '14:00',
      week: 'A',
      break_start: '10:00',
      break_end: null,
      label: null,
      notes: null,
      metadata_json: null,
      metrics_json: null,
      diagnostics_json: null,
      created_at: '',
      updated_at: '',
    };
    const result = shiftplanToShift(sp);
    expect(result.breakStart).toBe('10:00');
    expect(result.breakEnd).toBeUndefined();
  });

  it('berechnet week aus Datum bei week=null', () => {
    // 2024-07-04 ist ein Donnerstag in Woche A (referenced from Jan 1, 2024 = Week A Monday)
    const sp = {
      id: 23,
      schedule_id: 1,
      employee_id: 8,
      date: '2024-07-04',
      shift_id: 's4',
      start_time: '08:00',
      end_time: '16:00',
      week: null,
      break_start: null,
      break_end: null,
      label: null,
      notes: null,
      metadata_json: null,
      metrics_json: null,
      diagnostics_json: null,
      created_at: '',
      updated_at: '',
    };
    const result = shiftplanToShift(sp);
    // 2024-07-04 falls in Week A based on the reference date logic (matches backend)
    expect(result.week).toBe('A');
  });
});

describe('shiftToShiftplanCreate', () => {
  it('bildet Shift auf ShiftplanCreateDTO ab', () => {
    const shift = {
      id: '20',
      employeeId: '5',
      date: '2024-07-01',
      week: 'A' as const,
      startTime: '08:00',
      endTime: '16:00',
      breakStart: '12:00',
      breakEnd: '12:30',
      label: 'Frühschicht',
    };
    const result = shiftToShiftplanCreate(1, shift);
    expect(result.employee_id).toBe(5);
    expect(result.date).toBe('2024-07-01');
    expect(result.shift_id).toBe('20');
    expect(result.start_time).toBe('08:00');
    expect(result.end_time).toBe('16:00');
    expect(result.week).toBe('A');
    expect(result.break_start).toBe('12:00');
    expect(result.break_end).toBe('12:30');
    expect(result.label).toBe('Frühschicht');
  });

  it('behandelt Shift ohne break und label', () => {
    const shift = {
      id: '21',
      employeeId: '6',
      date: '2024-07-02',
      week: 'B' as const,
      startTime: '14:00',
      endTime: '22:00',
    };
    const result = shiftToShiftplanCreate(2, shift);
    expect(result.break_start).toBeUndefined();
    expect(result.break_end).toBeUndefined();
    expect(result.label).toBeUndefined();
  });
});

describe('scheduleFromResponse', () => {
  const baseDto = {
    id: 1,
    name: 'Testplan',
    status: 'active',
    week_type: 'A',
    start_date: '2024-01-01',
    end_date: '2024-01-31',
    role_requirements: { Schichtleiter: 2, Mitarbeiter: 5 },
    shift_templates: null,
    tito_job_id: 42,
    metadata_json: null,
    metrics_json: null,
    diagnostics_json: null,
    shiftplans: [],
    created_at: '',
    updated_at: '',
  };

  it('bildet ScheduleResponseDTO auf Schedule ab', () => {
    const result = scheduleFromResponse(baseDto);
    expect(result.id).toBe('1');
    expect(result.name).toBe('Testplan');
    expect(result.status).toBe('active');
    expect(result.startDate).toBe('2024-01-01');
    expect(result.endDate).toBe('2024-01-31');
    expect(result.shifts).toEqual([]);
    expect(result.roleRequirements).toEqual({ Schichtleiter: 2, Mitarbeiter: 5 });
    expect(result.shiftTemplates).toBeUndefined();
    expect(result.weekType).toBe('A');
    expect(result.titoJobId).toBe(42);
    expect(result.diagnostics).toBeNull();
    expect(result.metrics).toBeNull();
  });

  it('bildet Shiftplans auf Shifts ab', () => {
    const dto = {
      ...baseDto,
      shiftplans: [
        {
          id: 10,
          schedule_id: 1,
          employee_id: 3,
          date: '2024-07-01',
          shift_id: 's1',
          start_time: '08:00',
          end_time: '16:00',
          week: 'A',
          break_start: null,
          break_end: null,
          label: null,
          notes: null,
          metadata_json: null,
          metrics_json: null,
          diagnostics_json: null,
          created_at: '',
          updated_at: '',
        },
      ],
    };
    const result = scheduleFromResponse(dto);
    expect(result.shifts).toHaveLength(1);
    expect(result.shifts[0].id).toBe('10');
    expect(result.shifts[0].employeeId).toBe('3');
  });

  it('setzt startDate/endDate auf leeren String bei null', () => {
    const dto = { ...baseDto, start_date: null, end_date: null };
    const result = scheduleFromResponse(dto);
    expect(result.startDate).toBe('');
    expect(result.endDate).toBe('');
  });

  it('setzt weekType=undefined bei null', () => {
    const dto = { ...baseDto, week_type: null };
    const result = scheduleFromResponse(dto);
    expect(result.weekType).toBeUndefined();
  });

  it('gibt diagnostics/metrics als null weiter', () => {
    const dto = { ...baseDto, diagnostics_json: null, metrics_json: null };
    const result = scheduleFromResponse(dto);
    expect(result.diagnostics).toBeNull();
    expect(result.metrics).toBeNull();
  });

  it('gibt diagnostics/metrics als Objekt weiter', () => {
    const diagnostics = { isOptimal: true, info: 'Alles gut' };
    const metrics = { wishFulfillmentRate: 0.85, totalObjectiveScore: 90 };
    const dto = {
      ...baseDto,
      diagnostics_json: diagnostics,
      metrics_json: metrics,
    };
    const result = scheduleFromResponse(dto);
    expect(result.diagnostics).toEqual(diagnostics);
    expect(result.metrics).toEqual(metrics);
  });
});

describe('scheduleToCreate', () => {
  it('bildet Schedule auf ScheduleCreateDTO ab', () => {
    const schedule = {
      id: '1',
      name: 'Neuer Plan',
      status: 'draft',
      startDate: '2024-02-01',
      endDate: '2024-02-28',
      shifts: [],
      roleRequirements: { Chef: 1 },
      shiftTemplates: [{ id: 't1', name: 'Früh', startTime: '08:00', endTime: '16:00', requirements: {} }],
      weekType: 'A' as const,
    };
    const shiftplans: any[] = [];
    const result = scheduleToCreate(schedule, shiftplans);
    expect(result.name).toBe('Neuer Plan');
    expect(result.start_date).toBe('2024-02-01');
    expect(result.end_date).toBe('2024-02-28');
    expect(result.role_requirements).toEqual({ Chef: 1 });
    expect(result.shift_templates).toHaveLength(1);
    expect(result.shiftplans).toEqual([]);
  });

  it('lässt optionale Felder weg bei undefined/leerem String', () => {
    const schedule = {
      id: '2',
      name: 'Minimalplan',
      status: 'draft',
      startDate: '',
      endDate: '',
      shifts: [],
    };
    const result = scheduleToCreate(schedule, []);
    expect(result.name).toBe('Minimalplan');
    expect(result.start_date).toBeUndefined();
    expect(result.end_date).toBeUndefined();
    expect(result.role_requirements).toBeUndefined();
    expect(result.shift_templates).toBeUndefined();
  });
});

describe('userFromResponse', () => {
  const baseDto = {
    id: 1,
    username: 'maxmustermann',
    email: 'max@example.com',
    role: 'employee',
    must_change_password: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    last_login: '2024-06-01T08:00:00Z',
  };

  it('bildet UserResponseDTO auf AppUser (employee-Rolle) ab', () => {
    const result = userFromResponse(baseDto);
    expect(result.id).toBe('1');
    expect(result.username).toBe('maxmustermann');
    expect(result.email).toBe('max@example.com');
    expect(result.role).toBe('employee');
    expect(result.mustChangePassword).toBe(false);
    expect(result.lastLogin).toBe('2024-06-01T08:00:00Z');
  });

  it('erkennt admin-Rolle', () => {
    const dto = { ...baseDto, role: 'admin' };
    const result = userFromResponse(dto);
    expect(result.role).toBe('admin');
  });

  it('behandelt mustChangePassword=true', () => {
    const dto = { ...baseDto, must_change_password: true };
    const result = userFromResponse(dto);
    expect(result.mustChangePassword).toBe(true);
  });

  it('behandelt last_login=null', () => {
    const dto = { ...baseDto, last_login: null };
    const result = userFromResponse(dto);
    expect(result.lastLogin).toBeNull();
  });

  it('behandelt unbekannte Rolle als employee', () => {
    const dto = { ...baseDto, role: 'superadmin' };
    const result = userFromResponse(dto);
    expect(result.role).toBe('employee');
  });
});

describe('pinboardDocumentFromResponse', () => {
  it('bildet DocumentResponseDTO auf PinboardDocument ab', () => {
    const dto = {
      id: 1,
      message_id: 10,
      file_name: 'dokument.pdf',
      file_size: 1024,
      mime_type: 'application/pdf',
      created_at: '2024-01-01T00:00:00Z',
    };
    const result = pinboardDocumentFromResponse(dto);
    expect(result.id).toBe('1');
    expect(result.messageId).toBe('10');
    expect(result.fileName).toBe('dokument.pdf');
    expect(result.fileSize).toBe(1024);
    expect(result.mimeType).toBe('application/pdf');
    expect(result.createdAt).toBe('2024-01-01T00:00:00Z');
  });
});

describe('pinboardMessageFromResponse', () => {
  it('bildet MessageResponseDTO auf PinboardMessage mit Dokumenten ab', () => {
    const dto = {
      id: 5,
      thread_id: 2,
      author_id: 3,
      author_name: 'Max Mustermann',
      content: 'Hallo Welt',
      documents: [
        { id: 1, message_id: 5, file_name: 'bild.png', file_size: 2048, mime_type: 'image/png', created_at: '2024-01-01T00:00:00Z' },
      ],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T01:00:00Z',
    };
    const result = pinboardMessageFromResponse(dto);
    expect(result.id).toBe('5');
    expect(result.threadId).toBe('2');
    expect(result.authorId).toBe('3');
    expect(result.authorName).toBe('Max Mustermann');
    expect(result.content).toBe('Hallo Welt');
    expect(result.documents).toHaveLength(1);
    expect(result.documents[0].fileName).toBe('bild.png');
    expect(result.createdAt).toBe('2024-01-01T00:00:00Z');
    expect(result.updatedAt).toBe('2024-01-01T01:00:00Z');
  });

  it('behandelt leeres documents-Array', () => {
    const dto = {
      id: 6,
      thread_id: 2,
      author_id: 4,
      author_name: 'Anna Schmidt',
      content: 'Keine Dokumente',
      documents: [],
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    };
    const result = pinboardMessageFromResponse(dto);
    expect(result.documents).toEqual([]);
  });
});

describe('pinboardThreadFromResponse', () => {
  it('bildet ThreadResponseDTO auf PinboardThread ab', () => {
    const dto = {
      id: 1,
      title: 'Willkommen',
      author_id: 1,
      author_name: 'Admin',
      is_pinned: true,
      message_count: 5,
      last_message_at: '2024-06-01T12:00:00Z',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-06-01T12:00:00Z',
    };
    const result = pinboardThreadFromResponse(dto);
    expect(result.id).toBe('1');
    expect(result.title).toBe('Willkommen');
    expect(result.authorId).toBe('1');
    expect(result.authorName).toBe('Admin');
    expect(result.isPinned).toBe(true);
    expect(result.messageCount).toBe(5);
    expect(result.lastMessageAt).toBe('2024-06-01T12:00:00Z');
    expect(result.createdAt).toBe('2024-01-01T00:00:00Z');
    expect(result.updatedAt).toBe('2024-06-01T12:00:00Z');
  });
});

describe('pinboardThreadDetailFromResponse', () => {
  it('bildet ThreadDetailResponseDTO auf PinboardThreadDetail mit Messages ab', () => {
    const dto = {
      id: 1,
      title: 'Diskussion',
      author_id: 2,
      author_name: 'Max',
      is_pinned: false,
      messages: [
        {
          id: 10,
          thread_id: 1,
          author_id: 2,
          author_name: 'Max',
          content: 'Erste Nachricht',
          documents: [],
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T01:00:00Z',
    };
    const result = pinboardThreadDetailFromResponse(dto);
    expect(result.id).toBe('1');
    expect(result.title).toBe('Diskussion');
    expect(result.authorId).toBe('2');
    expect(result.messages).toHaveLength(1);
    expect(result.messages[0].content).toBe('Erste Nachricht');
    expect(result.messages[0].documents).toEqual([]);
  });

  it('behandelt leeres messages-Array', () => {
    const dto = {
      id: 2,
      title: 'Leerer Thread',
      author_id: 3,
      author_name: 'Anna',
      is_pinned: false,
      messages: [],
      created_at: '2024-02-01T00:00:00Z',
      updated_at: '2024-02-01T00:00:00Z',
    };
    const result = pinboardThreadDetailFromResponse(dto);
    expect(result.messages).toEqual([]);
  });
});

describe('timeAccountFromResponse', () => {
  it('bildet TimeAccountResponseDTO mit projected und history ab', () => {
    const dto = {
      employee_id: 1,
      employee_name: 'Max Mustermann',
      current_balance: 12.5,
      history: [
        {
          week: 1,
          year: 2024,
          scheduled_hours: 40,
          contract_hours: 38.5,
          delta: 1.5,
          balance: 1.5,
          manual_adjustment: 0,
          adjustment_reason: null,
          total_change: 1.5,
        },
      ],
      projected: {
        from_schedule: 38,
        expected_balance_after: 14,
      },
    };
    const result = timeAccountFromResponse(dto);
    expect(result.employeeId).toBe(1);
    expect(result.employeeName).toBe('Max Mustermann');
    expect(result.currentBalance).toBe(12.5);
    expect(result.history).toHaveLength(1);
    expect(result.history[0].week).toBe(1);
    expect(result.history[0].year).toBe(2024);
    expect(result.history[0].scheduledHours).toBe(40);
    expect(result.history[0].contractHours).toBe(38.5);
    expect(result.history[0].delta).toBe(1.5);
    expect(result.history[0].balance).toBe(1.5);
    expect(result.history[0].manualAdjustment).toBe(0);
    expect(result.history[0].adjustmentReason).toBeNull();
    expect(result.history[0].totalChange).toBe(1.5);
    expect(result.projected).toEqual({ fromSchedule: 38, expectedBalanceAfter: 14 });
  });

  it('behandelt projected=null', () => {
    const dto = {
      employee_id: 2,
      employee_name: 'Anna Schmidt',
      current_balance: 5,
      history: [],
      projected: null,
    };
    const result = timeAccountFromResponse(dto);
    expect(result.projected).toBeNull();
  });

  it('behandelt leeres history-Array', () => {
    const dto = {
      employee_id: 3,
      employee_name: 'John Doe',
      current_balance: 0,
      history: [],
      projected: null,
    };
    const result = timeAccountFromResponse(dto);
    expect(result.history).toEqual([]);
  });
});
