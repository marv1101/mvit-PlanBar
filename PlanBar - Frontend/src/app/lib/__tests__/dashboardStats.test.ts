import { describe, it, expect } from 'vitest';
import { normalizeList, computeDashboardStats } from '../dashboardStats';
import { mockSchedule } from '../../../test/test-utils';

describe('normalizeList', () => {
  it('übergibt Arrays unverändert durch', () => {
    const arr = [1, 2];
    expect(normalizeList(arr)).toBe(arr);
  });

  it('konvertiert null/undefined/Objekte zu leeren Arrays statt zu crashen', () => {
    expect(normalizeList(null)).toEqual([]);
    expect(normalizeList(undefined)).toEqual([]);
    expect(normalizeList({})).toEqual([]);
    expect(normalizeList('nope' as unknown as never)).toEqual([]);
  });
});

describe('computeDashboardStats', () => {
  it('berechnet die Kennzahlen für normale Daten', () => {
    const stats = computeDashboardStats([mockSchedule], [], [], []);
    expect(stats.totalShifts).toBe(mockSchedule.shifts.length);
  });

  it('ist robust gegen null/undefined/Objekt statt Array (kein Crash, leere Kennzahlen)', () => {
    expect(() =>
      computeDashboardStats(
        mockSchedule as unknown as never,
        null as unknown as never,
        { roleA: 1 } as unknown as never,
        undefined as unknown as never,
      ),
    ).not.toThrow();

    const stats = computeDashboardStats(
      mockSchedule as unknown as never,
      null as unknown as never,
      { roleA: 1 } as unknown as never,
      undefined as unknown as never,
    );
    expect(stats.totalShifts).toBe(0);
    expect(stats.requestsByType).toEqual({});
    expect(stats.roleShiftCounts).toEqual({});
  });
});
