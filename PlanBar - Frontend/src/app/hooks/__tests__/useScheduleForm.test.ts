import { renderHook, act } from '@testing-library/react';
import { useScheduleForm } from '../useScheduleForm';

beforeEach(() => {
  vi.resetAllMocks();
});

describe('useScheduleForm', () => {
  it('should have correct default values', () => {
    const { result } = renderHook(() => useScheduleForm());
    expect(result.current.creationMode).toBe('tito');
    expect(result.current.scheduleName).toBe('');
    expect(result.current.startDate).toBe('');
    expect(result.current.endDate).toBe('');
    expect(result.current.shiftTemplates).toEqual([]);
    expect(result.current.titoWeekType).toBe('A');
    expect(result.current.loading).toBe(false);
    expect(result.current.submitting).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should validate form correctly', () => {
    const { result } = renderHook(() => useScheduleForm());
    
    expect(result.current.canSubmit).toBe(false);
    
    act(() => {
      result.current.setScheduleName('Test Schedule');
      result.current.setStartDate('2026-08-01');
      result.current.setEndDate('2026-08-31');
    });
    
    expect(result.current.canSubmit).toBe(false);
    
    act(() => {
      result.current.addShiftTemplate();
    });
    
    expect(result.current.canSubmit).toBe(false);
    
    act(() => {
      result.current.updateShiftTemplate(0, 'name', 'Morning Shift');
    });
    
    expect(result.current.canSubmit).toBe(true);
  });

  it('should reset form correctly', () => {
    const { result } = renderHook(() => useScheduleForm());
    act(() => {
      result.current.setScheduleName('Test Schedule');
      result.current.addShiftTemplate();
    });
    expect(result.current.scheduleName).toBe('Test Schedule');
    expect(result.current.shiftTemplates).toHaveLength(1);
    
    act(() => {
      result.current.reset();
    });
    
    expect(result.current.scheduleName).toBe('');
    expect(result.current.shiftTemplates).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});
