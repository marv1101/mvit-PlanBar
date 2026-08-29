export interface TitoScheduleFormData {
  scheduleName: string;
  startDate: string;
  endDate: string;
  shiftTemplates: ShiftTemplateEntry[];
  titoWeekType: 'A' | 'B' | '';
}

export interface ManualScheduleFormData {
  manualName: string;
  manualStartDate: string;
  manualEndDate: string;
  manualWeekType: 'A' | 'B' | '';
}

export interface ShiftTemplateEntry {
  id: string;
  name: string;
  startTime: string;
  endTime: string;
  requirements: Record<string, number>;
  maxRequirements?: Record<string, number>;
}

export interface ValidationError {
  field: string;
  message: string;
}

export function validateTitoSchedule(data: TitoScheduleFormData): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!data.scheduleName.trim()) {
    errors.push({ field: 'scheduleName', message: 'Name ist erforderlich' });
  }
  if (!data.startDate) {
    errors.push({ field: 'startDate', message: 'Startdatum ist erforderlich' });
  }
  if (!data.endDate) {
    errors.push({ field: 'endDate', message: 'Enddatum ist erforderlich' });
  }
  if (data.shiftTemplates.length === 0) {
    errors.push({ field: 'shiftTemplates', message: 'Mindestens ein Schicht-Template ist erforderlich' });
  }
  data.shiftTemplates.forEach((st, i) => {
    if (!st.name.trim()) {
      errors.push({ field: `shiftTemplates[${i}].name`, message: 'Name ist erforderlich' });
    }
    if (!st.startTime) {
      errors.push({ field: `shiftTemplates[${i}].startTime`, message: 'Startzeit ist erforderlich' });
    }
    if (!st.endTime) {
      errors.push({ field: `shiftTemplates[${i}].endTime`, message: 'Endzeit ist erforderlich' });
    }
    if (st.maxRequirements) {
      for (const [roleId, maxVal] of Object.entries(st.maxRequirements)) {
        const minVal = st.requirements[roleId] || 0;
        if (maxVal > 0 && maxVal < minVal) {
          errors.push({
            field: `shiftTemplates[${i}].maxRequirements.${roleId}`,
            message: `Max. Belegung (${maxVal}) muss >= Min. Belegung (${minVal}) sein`,
          });
        }
      }
    }
  });

  return errors;
}

export function validateManualSchedule(data: ManualScheduleFormData): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!data.manualName.trim()) {
    errors.push({ field: 'manualName', message: 'Name ist erforderlich' });
  }
  if (!data.manualStartDate) {
    errors.push({ field: 'manualStartDate', message: 'Startdatum ist erforderlich' });
  }
  if (!data.manualEndDate) {
    errors.push({ field: 'manualEndDate', message: 'Enddatum ist erforderlich' });
  }

  return errors;
}
