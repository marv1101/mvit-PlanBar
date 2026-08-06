import { describe, it, expect } from 'vitest';
import { Shift } from '../../../types';
import { assignLanes, getShiftStyle, getBreakStyle } from '../calendarLayout';

const mockShiftA: Shift = {
  id: '1',
  employeeId: 'emp1',
  date: '2024-06-17',
  week: 'A',
  startTime: '08:00',
  endTime: '12:00',
  breakStart: '10:00',
  breakEnd: '11:00',
  label: 'Morning Shift',
};

const mockShiftB: Shift = {
  id: '2',
  employeeId: 'emp2',
  date: '2024-06-17',
  week: 'B',
  startTime: '12:00',
  endTime: '17:00',
  breakStart: '14:00',
  breakEnd: '15:00',
};

const mockShiftC: Shift = {
  id: '3',
  employeeId: 'emp3',
  date: '2024-06-17',
  week: 'A',
  startTime: '08:00',
  endTime: '10:00',
};
void mockShiftC;

describe('assignLanes', () => {
  it('weist nicht-überlappende Schichten korrekt zu (mockShiftA 8-12, mockShiftB 12-17)', () => {
    // mockShiftA endet 12:00, mockShiftB startet 12:00 → kein Overlap → gleiche Lane
    const shifts = [mockShiftA, mockShiftB];
    const result = assignLanes(shifts);

    expect(result).toHaveLength(2);
    expect(result[0].shift.id).toBe('1');
    expect(result[0].lane).toBe(0);
    expect(result[0].totalLanes).toBe(1);
    expect(result[1].shift.id).toBe('2');
    expect(result[1].lane).toBe(0);
    expect(result[1].totalLanes).toBe(1);
  });

  it('weist überlappende Schichten verschiedenen Lanes zu', () => {
    // Beide Schichten überlappen sich (8-12 und 9-11)
    const shift1: Shift = {
      id: '1',
      employeeId: 'emp1',
      date: '2024-06-17',
      week: 'A',
      startTime: '08:00',
      endTime: '12:00',
    };
    const shift2: Shift = {
      id: '2',
      employeeId: 'emp2',
      date: '2024-06-17',
      week: 'A',
      startTime: '09:00',
      endTime: '11:00',
    };
    const result = assignLanes([shift1, shift2]);

    expect(result).toHaveLength(2);
    expect(result[0].shift.id).toBe('1');
    expect(result[0].lane).toBe(0);
    expect(result[1].shift.id).toBe('2');
    expect(result[1].lane).toBe(1);
    expect(result[0].totalLanes).toBe(2);
    expect(result[1].totalLanes).toBe(2);
  });

  it('weist nicht-überlappende Schichten in gleiche Lane zu', () => {
    // shift1 endet 12:00, shift2 startet 12:00 → keine Überlappung → gleiche Lane
    const shift1: Shift = {
      id: '1',
      employeeId: 'emp1',
      date: '2024-06-17',
      week: 'A',
      startTime: '08:00',
      endTime: '12:00',
    };
    const shift2: Shift = {
      id: '2',
      employeeId: 'emp2',
      date: '2024-06-17',
      week: 'A',
      startTime: '12:00',
      endTime: '16:00',
    };
    const result = assignLanes([shift1, shift2]);

    expect(result).toHaveLength(2);
    expect(result[0].lane).toBe(0);
    expect(result[1].lane).toBe(0);
    expect(result[1].totalLanes).toBe(1);
  });

  it('weist leere Liste von Schichten zurück', () => {
    const result = assignLanes([]);
    expect(result).toHaveLength(0);
  });

  it('weist exakt überlappende Schichten in gleiche Lane zu', () => {
    const shift1: Shift = {
      id: '1',
      employeeId: 'emp1',
      date: '2024-06-17',
      week: 'A',
      startTime: '08:00',
      endTime: '12:00',
    };
    const shift2: Shift = {
      id: '2',
      employeeId: 'emp2',
      date: '2024-06-17',
      week: 'A',
      startTime: '08:00',
      endTime: '12:00',
    };
    const shifts = [shift1, shift2];
    const result = assignLanes(shifts);
    
    expect(result).toHaveLength(2);
    expect(result[0].lane).toBe(0);
    expect(result[1].lane).toBe(1);
  });
});

describe('getShiftStyle', () => {
  it('berechnet korrekte Höhen und Positionen für einfache Schicht', () => {
    const style = getShiftStyle(mockShiftA, 0, 2);
    
    expect(style.top).toBe('104px'); // (8 - 6) * 52 = 2h * 52
    expect(style.height).toBe('208px'); // 4h * 52
    expect(style.left).toBe('0%');
    expect(style.width).toBe('50%');
  });

  it('behandelt Schichten mit minimaler Höhe (unter 24px)', () => {
    const shortShift: Shift = {
      id: '1',
      employeeId: 'emp1',
      date: '2024-06-17',
      week: 'A',
      startTime: '10:00',
      endTime: '10:05',
    };
    const style = getShiftStyle(shortShift, 1, 3);
    
    expect(style.height).toBe('24px');
  });

  it('plaziert mehrere Schichten in verschiedenen Lanes', () => {
    const style1 = getShiftStyle(mockShiftA, 0, 2);
    const style2 = getShiftStyle(mockShiftB, 1, 2);
    
    expect(style1.left).toBe('0%');
    expect(style2.left).toBe('50%');
    expect(style1.width).toBe('50%');
    expect(style2.width).toBe('50%');
  });
});

describe('getBreakStyle', () => {
  it('berechnet korrekte Break-Position für normale Pause', () => {
    const style = getBreakStyle(mockShiftA);
    
    expect(style).not.toBeNull();
    const s = style as { top: number; height: number };
    expect(s.top).toBe(104); // (600 - 480) * 52 / 60 = 2h * 52 = 104px
    expect(s.height).toBe(52); // 1h * 52 = 52px (above min 16)
  });

  it('rückt null zurück, wenn BreakStart nicht gesetzt', () => {
    const shiftNoBreak = { ...mockShiftA, breakStart: undefined, breakEnd: undefined };
    const style = getBreakStyle(shiftNoBreak);
    
    expect(style).toBeNull();
  });

  it('rückt null zurück, wenn BreakStart/Ende ungültig', () => {
    const invalidShift: Shift = {
      id: '1',
      employeeId: 'emp1',
      date: '2024-06-17',
      week: 'A',
      startTime: '08:00',
      endTime: '12:00',
      breakStart: '13:00',
      breakEnd: '14:00',
    };
    const style = getBreakStyle(invalidShift);
    
    expect(style).toBeNull();
  });

  it('verhindert Break-Position nach Schicht-Ende', () => {
    const shift: Shift = {
      id: '1',
      employeeId: 'emp1',
      date: '2024-06-17',
      week: 'A',
      startTime: '08:00',
      endTime: '12:00',
      breakStart: '11:30',
      breakEnd: '12:30',
    };
    const style = getBreakStyle(shift);
    
    expect(style).toBeNull();
  });
});
