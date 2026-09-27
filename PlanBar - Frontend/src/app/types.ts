export interface ArbZgWarning {
  rule: string;
  message: string;
  employee_id: number;
  shift_date: string | null;
  details?: unknown;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

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
  teamIds?: number[];
}

export type RequestType = 'urlaubswunsch' | 'bevorzugt' | 'nicht-verfügbar';

export type WishStatus = 'approved' | 'pending' | 'rejected';

export interface Request {
  id: string;
  employeeId: string;
  date: string; // ISO date string
  week: WeekType;
  type: RequestType;
  notes?: string;
  status?: WishStatus;
  reviewedBy?: number | null;
  reviewedAt?: string | null;
  rejectionReason?: string | null;
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
  label?: string;
}

export interface TiTOViolation {
  type: string;
  severity: string;
  message: string;
  details?: unknown;
}

export interface TiTODiagnostics {
  isOptimal: boolean;
  info: string;
  aggregatedMessages?: TiTOAggregatedMessage[];
  infeasibilityReasons?: string[];
}

export interface TiTOAggregatedMessage {
  severity: string;
  skill: string;
  message: string;
  totalMissingShifts: number;
  totalMissingHours: number;
  affectedDays: number;
}

export interface EmployeeFairnessEntry {
  currentBalanceHours: number;
  scheduledHours: number;
  contractHours: number;
  targetHours: number;
  projectedBalance: number;
  fairnessDeviation: number;
}

export interface TiTOMetrics {
  wishFulfillmentRate: number;
  totalObjectiveScore: number;
  violations?: TiTOViolation[];
  employeeFairness?: Record<string, EmployeeFairnessEntry>;
}

export interface Team {
  id: string;
  name: string;
  color?: string;
  description?: string;
  employee_ids?: number[];
  created_at: string;
  updated_at: string;
}

export interface AppUser {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'planer' | 'employee' | 'kiosk';
  mustChangePassword: boolean;
  lastLogin: string | null;
  employeeId?: number | null;
}

export interface ShiftTemplateEntry {
  id: string;
  name: string;
  startTime: string;
  endTime: string;
  requirements: Record<string, number>;
  maxRequirements?: Record<string, number>;
  saturday?: boolean;
  sunday?: boolean;
}

export interface Schedule {
  id: string;
  name: string;
  status: string;
  startDate: string;
  endDate: string;
  shifts: Shift[];
  roleRequirements?: Record<EmployeeRole, number>;
  shiftTemplates?: ShiftTemplateEntry[];
  weekType?: WeekType | null;
  titoJobId?: number | null;
  diagnostics?: TiTODiagnostics | null;
  metrics?: TiTOMetrics | null;
}

export interface TimeAccountEntry {
  week: number;
  year: number;
  scheduledHours: number;
  contractHours: number;
  delta: number;
  balance: number;
  manualAdjustment: number;
  adjustmentReason: string | null;
  totalChange: number;
}

export interface TimeAccountProjected {
  fromSchedule: number;
  expectedBalanceAfter: number;
}

export interface EmployeeTimeAccount {
  employeeId: number;
  employeeName: string;
  currentBalance: number;
  history: TimeAccountEntry[];
  projected: TimeAccountProjected | null;
}

export interface PinboardDocument {
  id: string;
  messageId: string;
  fileName: string;
  fileSize: number;
  mimeType: string;
  createdAt: string;
}

export interface PinboardMessage {
  id: string;
  threadId: string;
  authorId: string;
  authorName: string;
  content: string;
  documents: PinboardDocument[];
  createdAt: string;
  updatedAt: string;
}

export interface PinboardThread {
  id: string;
  title: string;
  authorId: string;
  authorName: string;
  isPinned: boolean;
  messageCount: number;
  lastMessageAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface PinboardThreadDetail {
  id: string;
  title: string;
  authorId: string;
  authorName: string;
  isPinned: boolean;
  messages: PinboardMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface ShiftSwap {
  id: string;
  employeeId: string;
  requesterShiftId: string;
  targetEmployeeId: string;
  targetShiftId: string;
  status: 'pending' | 'approved' | 'rejected';
  note?: string;
  rejectionReason?: string | null;
  createdAt: string;
}

export interface AvailabilityEntry {
  dayOfWeek: number;
  available: boolean;
  note?: string;
}

export interface AvailabilityRecord extends AvailabilityEntry {
  id: string;
  employeeId: string;
}

export type SelfServiceTab = 'schedule' | 'shift-swap' | 'vacation' | 'availability';