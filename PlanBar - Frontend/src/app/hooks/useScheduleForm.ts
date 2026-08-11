import { useState, useCallback } from 'react';
import { scheduleFromResponse } from '../lib/mappers';
import * as scheduleService from '../services/scheduleService';
import type { Schedule as ScheduleType, ShiftTemplateEntry } from '../types';
import { validateTitoSchedule, type TitoScheduleFormData } from '../schemas/scheduleForm';

export interface UseScheduleFormReturn {
  creationMode: 'tito' | 'manual';
  scheduleName: string;
  setScheduleName: (v: string) => void;
  startDate: string;
  setStartDate: (v: string) => void;
  endDate: string;
  setEndDate: (v: string) => void;
  shiftTemplates: ShiftTemplateEntry[];
  titoWeekType: string;
  setTitoWeekType: (v: string) => void;
  loading: boolean;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
  error: string | null;
  canSubmit: boolean;
  addShiftTemplate: () => void;
  removeShiftTemplate: (index: number) => void;
  updateShiftTemplate: (index: number, field: string, value: string | Record<string, number>) => void;
  updateRequirement: (templateIndex: number, roleId: string, count: number) => void;
  validateForm: () => boolean;
  reset: () => void;
  submit: () => Promise<ScheduleType | null>;
}

export function useScheduleForm(): UseScheduleFormReturn {
  const [scheduleName, setScheduleName] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [shiftTemplates, setShiftTemplates] = useState<ShiftTemplateEntry[]>([]);
  const [titoWeekType, setTitoWeekType] = useState('A');

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addShiftTemplate = useCallback(() => {
    const id = `shift_${Date.now()}`;
    setShiftTemplates(prev => [...prev, {
      id,
      name: '',
      startTime: '06:00',
      endTime: '14:00',
      requirements: {},
    }]);
  }, []);

  const removeShiftTemplate = useCallback((index: number) => {
    setShiftTemplates(prev => prev.filter((_, i) => i !== index));
  }, []);

  const updateShiftTemplate = useCallback((index: number, field: string, value: string | Record<string, number>) => {
    setShiftTemplates(prev => prev.map((st, i) =>
      i === index ? { ...st, [field]: value } : st
    ));
  }, []);

  const updateRequirement = useCallback((templateIndex: number, roleId: string, count: number) => {
    setShiftTemplates(prev => prev.map((st, i) =>
      i === templateIndex
        ? { ...st, requirements: { ...st.requirements, [roleId]: count } }
        : st
    ));
  }, []);

  const validateForm = useCallback((): boolean => {
    const formData: TitoScheduleFormData = {
      scheduleName,
      startDate,
      endDate,
      shiftTemplates,
      titoWeekType: titoWeekType as 'A' | 'B' | '',
    };

    const errors = validateTitoSchedule(formData);
    if (errors.length > 0) {
      setError(errors.map(e => e.message).join(', '));
      return false;
    }
    setError(null);
    return true;
  }, [scheduleName, startDate, endDate, shiftTemplates, titoWeekType]);

  const reset = useCallback(() => {
    setScheduleName('');
    setStartDate('');
    setEndDate('');
    setShiftTemplates([]);
    setTitoWeekType('A');
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
        name: scheduleName,
        start_date: startDate,
        end_date: endDate,
        week_type: titoWeekType || undefined,
        shift_templates: shiftTemplates.map(st => ({
          ...st,
          requirements: Object.fromEntries(
            Object.entries(st.requirements).filter(([, count]) => count > 0)
          ),
        })),
        shiftplans: [],
      });

      return scheduleFromResponse(result);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Fehler beim Erstellen';
      setError(message);
      throw e;
    } finally {
      setSubmitting(false);
      setLoading(false);
    }
  }, [scheduleName, startDate, endDate, shiftTemplates, titoWeekType, validateForm]);

  const canSubmit = !!scheduleName && !!startDate && !!endDate && shiftTemplates.length > 0 &&
    shiftTemplates.every(st => st.name && st.startTime && st.endTime);

  return {
    creationMode: 'tito',
    scheduleName,
    setScheduleName,
    startDate,
    setStartDate,
    endDate,
    setEndDate,
    shiftTemplates,
    titoWeekType,
    setTitoWeekType,
    loading,
    submitting,
    setSubmitting,
    error,
    canSubmit,
    addShiftTemplate,
    removeShiftTemplate,
    updateShiftTemplate,
    updateRequirement,
    validateForm,
    reset,
    submit,
  };
}
