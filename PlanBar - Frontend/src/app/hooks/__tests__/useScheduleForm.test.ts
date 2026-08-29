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

  it('should initialize with maximizeStaffing false', () => {
    const { result } = renderHook(() => useScheduleForm());
    expect(result.current.maximizeStaffing).toBe(false);
  });

  it('should toggle maximizeStaffing', () => {
    const { result } = renderHook(() => useScheduleForm());
    expect(result.current.maximizeStaffing).toBe(false);

    act(() => {
      result.current.setMaximizeStaffing(true);
    });

    expect(result.current.maximizeStaffing).toBe(true);
  });

  it('should update maxRequirements via updateMaxRequirement', () => {
    const { result } = renderHook(() => useScheduleForm());

    act(() => {
      result.current.addShiftTemplate();
    });
    expect(result.current.shiftTemplates[0].maxRequirements).toBeUndefined();

    act(() => {
      result.current.updateMaxRequirement(0, 'nurse', 5);
    });

    expect(result.current.shiftTemplates[0].maxRequirements).toEqual({ nurse: 5 });
  });

  it('should validate that max >= min', () => {
    const { result } = renderHook(() => useScheduleForm());

    act(() => {
      result.current.setScheduleName('Test');
      result.current.setStartDate('2026-08-01');
      result.current.setEndDate('2026-08-31');
      result.current.addShiftTemplate();
      result.current.updateShiftTemplate(0, 'name', 'Morning');
      result.current.updateRequirement(0, 'nurse', 3);
      result.current.updateMaxRequirement(0, 'nurse', 2);
    });

    let isValid = false;
    act(() => {
      isValid = result.current.validateForm();
    });
    expect(isValid).toBe(false);
    expect(result.current.error).toContain('Max');
  });

  it('should include maxRequirements in shift templates', () => {
    const { result } = renderHook(() => useScheduleForm());

    act(() => {
      result.current.addShiftTemplate();
    });

    act(() => {
      result.current.updateMaxRequirement(0, 'nurse', 4);
    });

    const template = result.current.shiftTemplates[0];
    expect(template).toHaveProperty('maxRequirements');
    expect(template.maxRequirements).toEqual({ nurse: 4 });
  });
});
