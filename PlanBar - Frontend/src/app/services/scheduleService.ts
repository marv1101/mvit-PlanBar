import api from '../lib/api';

export interface ShiftplanCreateDTO {
  employee_id: number;
  date: string;
  shift_id: string;
  start_time: string;
  end_time: string;
  week?: string;
  break_start?: string;
  break_end?: string;
  label?: string;
  notes?: string;
}

export interface ShiftplanResponseDTO {
  id: number;
  schedule_id: number;
  employee_id: number;
  date: string;
  shift_id: string;
  start_time: string;
  end_time: string;
  week: string | null;
  break_start: string | null;
  break_end: string | null;
  label: string | null;
  notes: string | null;
  metadata_json: unknown;
  metrics_json: unknown;
  diagnostics_json: unknown;
  created_at: string;
  updated_at: string;
}

export interface ShiftTemplateEntryDTO {
  id: string;
  name: string;
  startTime: string;
  endTime: string;
  requirements: Record<string, number>;
}

export interface ScheduleCreateDTO {
  name: string;
  week_type?: string;
  start_date?: string;
  end_date?: string;
  role_requirements?: Record<string, number>;
  shift_templates?: ShiftTemplateEntryDTO[];
  shiftplans: ShiftplanCreateDTO[];
}

export interface ScheduleUpdateDTO {
  name?: string;
  week_type?: string;
  status?: string;
}

export interface ScheduleResponseDTO {
  id: number;
  name: string;
  status: string;
  week_type: string | null;
  start_date: string | null;
  end_date: string | null;
  role_requirements: Record<string, number> | null;
  shift_templates: ShiftTemplateEntryDTO[] | null;
  tito_job_id: number | null;
  metadata_json: unknown;
  metrics_json: unknown;
  diagnostics_json: unknown;
  shiftplans: ShiftplanResponseDTO[];
  created_at: string;
  updated_at: string;
}

export interface ScheduleSummaryDTO {
  id: number;
  name: string;
  status: string;
  total_shifts: number;
  total_employees: number;
  date_range: [string, string] | null;
}

export async function getSchedules(): Promise<ScheduleResponseDTO[]> {
  const { data } = await api.get('/schedules');
  return data;
}

export async function getSchedule(id: number): Promise<ScheduleResponseDTO> {
  const { data } = await api.get(`/schedules/${id}`);
  return data;
}

export async function createSchedule(dto: ScheduleCreateDTO): Promise<ScheduleResponseDTO> {
  const { data } = await api.post('/schedules', dto);
  return data;
}

export async function updateSchedule(id: number, dto: ScheduleUpdateDTO): Promise<ScheduleResponseDTO> {
  const { data } = await api.put(`/schedules/${id}`, dto);
  return data;
}

export async function deleteSchedule(id: number): Promise<void> {
  await api.delete(`/schedules/${id}`);
}

export async function submitScheduleToTito(id: number): Promise<ScheduleResponseDTO> {
  const { data } = await api.post(`/schedules/${id}/submit`);
  return data;
}

export async function retrySchedule(id: number): Promise<ScheduleResponseDTO> {
  const { data } = await api.post(`/schedules/${id}/retry`);
  return data;
}

export async function getScheduleSummary(id: number): Promise<ScheduleSummaryDTO> {
  const { data } = await api.get(`/schedules/${id}/summary`);
  return data;
}

export async function getScheduleShifts(id: number): Promise<ShiftplanResponseDTO[]> {
  const { data } = await api.get(`/schedules/${id}/shifts`);
  return data;
}

export async function updateShiftplan(scheduleId: number, shiftplanId: number, dto: Partial<ShiftplanCreateDTO>): Promise<ShiftplanResponseDTO> {
  const { data } = await api.put(`/schedules/${scheduleId}/shifts/${shiftplanId}`, dto);
  return data;
}

export async function replaceAllShifts(scheduleId: number, shifts: ShiftplanCreateDTO[]): Promise<ScheduleResponseDTO> {
  const { data } = await api.put(`/schedules/${scheduleId}/shifts`, { shiftplans: shifts });
  return data;
}
