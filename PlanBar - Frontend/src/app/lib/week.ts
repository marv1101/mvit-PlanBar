import type { WeekType } from '../types';

const REFERENCE_DATE = Date.UTC(2024, 0, 1);

export function getWeekType(date: Date): WeekType {
  const dayOfWeek = date.getUTCDay();
  const monday = Date.UTC(
    date.getUTCFullYear(),
    date.getUTCMonth(),
    date.getUTCDate() - ((dayOfWeek + 6) % 7)
  );
  const weeksDiff = Math.floor(
    (monday - REFERENCE_DATE) / (7 * 24 * 60 * 60 * 1000)
  );
  return weeksDiff % 2 === 0 ? 'A' : 'B';
}
