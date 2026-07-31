import { useState, useCallback } from 'react';
import { scheduleFromResponse } from '../lib/mappers';
import * as scheduleService from '../services/scheduleService';
import type { Schedule as ScheduleType } from '../types';
import { validateManualSchedule, type ManualScheduleFormData } from '../schemas/scheduleForm';

export interface UseManualScheduleFormReturn {
  manualName: string;
  setManualName: (v: string) => void;
  manualStartDate: string;
  setManualStartDate: (v: string) => void;
  manualEndDate: string;
  setManualEndDate: (v: string) => void;
  manualWeekType: string;
  setManualWeekType: (v: string) => void;
  manuallyCreatedSchedule: ScheduleType | null;
  loading: boolean;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
  error: string | null;
  canSubmit: boolean;
  validateForm: () => boolean;
  reset: () => void;
  submit: () => Promise<ScheduleType | null>;
}

export function useManualScheduleForm(): UseManualScheduleFormReturn {
  const [manualName, setManualName] = useState('');
  const [manualStartDate, setManualStartDate] = useState('');
  const [manualEndDate, setManualEndDate] = useState('');
  const [manualWeekType, setManualWeekType] = useState('A');
  const [manuallyCreatedSchedule, setManuallyCreatedSchedule] = useState<ScheduleType | null>(null);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateForm = useCallback((): boolean => {
    const formData: ManualScheduleFormData = {
      manualName,
      manualStartDate,
      manualEndDate,
      manualWeekType: manualWeekType as 'A' | 'B' | '',
    };

    const errors = validateManualSchedule(formData);
    if (errors.length > 0) {
      setError(errors.map(e => e.message).join(', '));
      return false;
    }
    setError(null);
    return true;
  }, [manualName, manualStartDate, manualEndDate, manualWeekType]);

  const reset = useCallback(() => {
    setManualName('');
    setManualStartDate('');
    setManualEndDate('');
    setManualWeekType('A');
    setManuallyCreatedSchedule(null);
    setError(null);
  }, []);

  const submit = useCallback(async (): Promise<ScheduleType | null> => {
    if (!validateForm()) {
      return null;
    }

    setSubmitting(true);
    setLoading(true);
    setError(null);

    try {
      const result = await scheduleService.createSchedule({
        name: manualName,
        start_date: manualStartDate,
        end_date: manualEndDate,
        week_type: manualWeekType || undefined,
        shift_templates: [],
        shiftplans: [],
      });

      const schedule = scheduleFromResponse(result);
      setManuallyCreatedSchedule(schedule);
      return schedule;
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Fehler beim Erstellen';
      setError(message);
      throw e;
    } finally {
      setSubmitting(false);
      setLoading(false);
    }
  }, [manualName, manualStartDate, manualEndDate, manualWeekType, validateForm]);

  const canSubmit = !!manualName && !!manualStartDate && !!manualEndDate;

  return {
    manualName,
    setManualName,
    manualStartDate,
    setManualStartDate,
    manualEndDate,
    setManualEndDate,
    manualWeekType,
    setManualWeekType,
    manuallyCreatedSchedule,
    loading,
    submitting,
    setSubmitting,
    error,
    canSubmit,
    validateForm,
    reset,
    submit,
  };
}
