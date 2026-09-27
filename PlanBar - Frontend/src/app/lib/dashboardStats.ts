import { Shift, Schedule, Employee, Role, Request } from '../types';

/** Stellt sicher, dass ein (potentiell defekter) API-Wert ein Array ist. */
export function normalizeList<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

export interface DashboardStats {
  totalShifts: number;
  todayShifts: number;
  upcomingShifts: number;
  avgShiftsPerEmployee: string;
  employeeShiftCounts: Record<string, number>;
  roleShiftCounts: Record<string, number>;
  requestsByType: Record<string, number>;
}

/**
 * Berechnet die Dashboard-Kennzahlen. Robust gegen nicht-Array-Daten
 * (z.B. unerwartete API-/Cache-Shapes): diese werden als leer behandelt.
 */
export function computeDashboardStats(
  schedulesInput: Schedule[] | unknown,
  employeesInput: Employee[] | unknown,
  rolesInput: Role[] | unknown,
  requestsInput: Request[] | unknown,
): DashboardStats {
  const schedules = normalizeList<Schedule>(schedulesInput);
  const employees = normalizeList<Employee>(employeesInput);
  const roles = normalizeList<Role>(rolesInput);
  const requests = normalizeList<Request>(requestsInput);

  const now = new Date();
  const todayStr = now.toISOString().split('T')[0];

  let totalShifts = 0;
  let todayShifts = 0;
  let upcomingShifts = 0;
  const employeeShiftCounts: Record<string, number> = {};
  const roleShiftCounts: Record<string, number> = {};

  schedules.forEach(schedule => {
    if (!schedule || !Array.isArray(schedule.shifts)) return;
    totalShifts += schedule.shifts.length;

    schedule.shifts.forEach(shift => {
      if (!shift) return;
      employeeShiftCounts[shift.employeeId] = (employeeShiftCounts[shift.employeeId] || 0) + 1;

      const employee = employees.find(e => e.id === shift.employeeId);
      if (employee && Array.isArray(employee.roles)) {
        employee.roles.forEach(roleId => {
          roleShiftCounts[roleId] = (roleShiftCounts[roleId] || 0) + 1;
        });
      }

      if (shift.date === todayStr) todayShifts++;

      const shiftDate = new Date(shift.date);
      const daysUntilShift = Math.ceil((shiftDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
      if (daysUntilShift >= 0 && daysUntilShift <= 7) upcomingShifts++;
    });
  });

  const avgShiftsPerEmployee = employees.length > 0
    ? (totalShifts / employees.length).toFixed(1)
    : '0';

  const requestsByType = requests.reduce((acc, req) => {
    acc[req.type] = (acc[req.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return {
    totalShifts,
    todayShifts,
    upcomingShifts,
    avgShiftsPerEmployee,
    employeeShiftCounts,
    roleShiftCounts,
    requestsByType,
  };
}
