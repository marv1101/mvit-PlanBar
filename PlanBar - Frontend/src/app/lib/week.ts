import type { WeekType } from '../types';

const REFERENCE_DATE = new Date('2024-01-01');

export function getWeekType(date: Date): WeekType {
  const dayOfWeek = date.getDay();
  const monday = new Date(date);
  monday.setDate(date.getDate() - ((dayOfWeek + 6) % 7));
  const weeksDiff = Math.floor(
    (monday.getTime() - REFERENCE_DATE.getTime()) / (7 * 24 * 60 * 60 * 1000)
  );
  return weeksDiff % 2 === 0 ? 'A' : 'B';
}
