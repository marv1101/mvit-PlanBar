import { Shift } from '../../types';
import { toMinutes, START_HOUR } from './shared/CalendarUtils';

export const HOUR_HEIGHT = 52;

export interface ShiftLaned {
  shift: Shift;
  lane: number;
  totalLanes: number;
}

export interface ShiftStyle {
  top: string;
  height: string;
  left: string;
  width: string;
}

export interface BreakStyle {
  top: number;
  height: number;
}

export function assignLanes(shifts: Shift[]): ShiftLaned[] {
  const sorted = [...shifts].sort((a, b) => toMinutes(a.startTime) - toMinutes(b.startTime));
  const lanes: number[] = [];
  const result: { shift: Shift; lane: number }[] = [];

  for (const shift of sorted) {
    const start = toMinutes(shift.startTime);
    const end = toMinutes(shift.endTime);
    let assigned = false;

    for (let i = 0; i < lanes.length; i++) {
      if (lanes[i] <= start) {
        lanes[i] = end;
        result.push({ shift, lane: i });
        assigned = true;
        break;
      }
    }

    if (!assigned) {
      lanes.push(end);
      result.push({ shift, lane: lanes.length - 1 });
    }
  }

  return result.map(r => ({ ...r, totalLanes: lanes.length }));
}

export function getShiftStyle(shift: Shift, lane: number, totalLanes: number): ShiftStyle {
  const startMin = toMinutes(shift.startTime);
  const endMin = toMinutes(shift.endTime);
  const rangeStart = START_HOUR * 60;
  const top = ((startMin - rangeStart) / 60) * HOUR_HEIGHT;
  const height = Math.max(((endMin - startMin) / 60) * HOUR_HEIGHT, 24);
  const width = 100 / totalLanes;
  const left = lane * width;

  return {
    top: `${top}px`,
    height: `${height}px`,
    left: `${left}%`,
    width: `${width}%`,
  };
}

export function getBreakStyle(shift: Shift): BreakStyle | null {
  if (!shift.breakStart || !shift.breakEnd) return null;
  const shiftStart = toMinutes(shift.startTime);
  const breakStart = toMinutes(shift.breakStart);
  const breakEnd = toMinutes(shift.breakEnd);
  if (breakStart <= shiftStart || breakEnd <= breakStart || breakEnd > toMinutes(shift.endTime)) return null;
  const top = ((breakStart - shiftStart) / 60) * HOUR_HEIGHT;
  const height = Math.max(((breakEnd - breakStart) / 60) * HOUR_HEIGHT, 16);
  return { top, height };
}
