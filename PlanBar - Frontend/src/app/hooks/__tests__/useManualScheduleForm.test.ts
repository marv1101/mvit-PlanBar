import { renderHook, act } from '@testing-library/react';
import { useManualScheduleForm } from '../useManualScheduleForm';

beforeEach(() => {
  vi.resetAllMocks();
});

describe('useManualScheduleForm', () => {
  it('should have correct default values', () => {
    const { result } = renderHook(() => useManualScheduleForm());
    expect(result.current.manualName).toBe('');
    expect(result.current.manualStartDate).toBe('');
    expect(result.current.manualEndDate).toBe('');
    expect(result.current.manualWeekType).toBe('');
    expect(result.current.manuallyCreatedSchedule).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(result.current.submitting).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should validate form correctly', () => {
    const { result } = renderHook(() => useManualScheduleForm());
    
    expect(result.current.canSubmit).toBe(false);
    
    act(() => {
      result.current.setManualName('Test Schedule');
      result.current.setManualStartDate('2026-08-01');
      result.current.setManualEndDate('2026-08-31');
    });
    
    expect(result.current.canSubmit).toBe(true);
  });

  it('should reset form correctly', () => {
    const { result } = renderHook(() => useManualScheduleForm());
    act(() => {
      result.current.setManualName('Test Schedule');
      result.current.setManualStartDate('2026-08-01');
    });
    expect(result.current.manualName).toBe('Test Schedule');
    
    act(() => {
      result.current.reset();
    });
    
    expect(result.current.manualName).toBe('');
    expect(result.current.manualStartDate).toBe('');
    expect(result.current.error).toBeNull();
  });
});
