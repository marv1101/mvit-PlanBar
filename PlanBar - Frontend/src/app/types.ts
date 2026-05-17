export type WeekType = 'A' | 'B';

export interface Role {
  id: string;
  name: string;
  color: string;
}

export type EmployeeRole = string;

export interface WorkingHours {
  weekA: {
    monday: { start: string; end: string; enabled: boolean };
    tuesday: { start: string; end: string; enabled: boolean };
    wednesday: { start: string; end: string; enabled: boolean };
    thursday: { start: string; end: string; enabled: boolean };
    friday: { start: string; end: string; enabled: boolean };
    saturday: { start: string; end: string; enabled: boolean };
    sunday: { start: string; end: string; enabled: boolean };
  };
  weekB: {
    monday: { start: string; end: string; enabled: boolean };
    tuesday: { start: string; end: string; enabled: boolean };
    wednesday: { start: string; end: string; enabled: boolean };
    thursday: { start: string; end: string; enabled: boolean };
    friday: { start: string; end: string; enabled: boolean };
    saturday: { start: string; end: string; enabled: boolean };
    sunday: { start: string; end: string; enabled: boolean };
  };
}

export interface BreakTime {
  start: string;
  end: string;
  duration: number; // in minutes
}

export interface Employee {
  id: string;
  name: string;
  email: string;
  roles: EmployeeRole[];
  workingHours: WorkingHours;
  breakTime: BreakTime;
  color: string; // for calendar display
  maxWorkHours?: number; // maximum work hours per week
}

export type RequestType = 'urlaubswunsch' | 'bevorzugt' | 'nicht-verfügbar';

export interface Request {
  id: string;
  employeeId: string;
  date: string; // ISO date string
  week: WeekType;
  type: RequestType;
  notes?: string;
}

export interface Shift {
  id: string;
  employeeId: string;
  date: string; // ISO date string
  week: WeekType;
  startTime: string;
  endTime: string;
  breakStart?: string;
  breakEnd?: string;
}

export interface Schedule {
  id: string;
  name: string;
  startDate: string;
  endDate: string;
  shifts: Shift[];
  roleRequirements?: Record<EmployeeRole, number>;
}