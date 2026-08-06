import type { Shift } from '../../../types';

// Shared calendar constants
export const ITEM_TYPE = 'SHIFT';
export const EMPLOYEE_ITEM_TYPE = 'EMPLOYEE';
export const BREAK_START_ITEM_TYPE = 'BREAK_START';
export const BREAK_END_ITEM_TYPE = 'BREAK_END';
export const START_HOUR = 6;
export const END_HOUR = 22;
export const SNAP_MINUTES_SHIFT = 30;
export const SNAP_MINUTES_BREAK = 15;

export const HOURS = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);

// Shared drag item types
export interface DragItem {
  shift: Shift;
  fromDate: string;
}

export interface EmployeeDragItem {
  employeeId: string;
}

export interface BreakDragItem {
  shift: Shift;
  breakType: 'start' | 'end';
}

// Shared utility functions
export function toMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

export function formatTime(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function snapMinutes(rawMinutes: number, snap: number): number {
  return Math.round(rawMinutes / snap) * snap;
}
