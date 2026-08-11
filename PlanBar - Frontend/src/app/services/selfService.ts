import api from '../lib/api';
import type { EmployeeResponseDTO } from './employeeService';

export interface MyShiftDTO {
  id: number;
  schedule_id: number;
  schedule_name: string;
  employee_id: number;
  date: string;
  start_time: string;
  end_time: string;
  week: string | null;
  break_start: string | null;
  break_end: string | null;
  label: string | null;
}

export interface MyOvertimeDTO {
  current_balance: number;
  scheduled_hours: number;
  contract_hours: number;
  week: number | null;
  year: number | null;
}

export interface ShiftSwapCreateDTO {
  requester_shift_id: number;
  target_employee_id: number;
  target_shift_id: number;
  note?: string;
}

export interface ShiftSwapResponseDTO {
  id: number;
  employee_id: number;
  requester_shift_id: number;
  target_employee_id: number;
  target_shift_id: number;
  status: string;
  note: string | null;
  approved_by: number | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface AvailabilityEntryDTO {
  day_of_week: number;
  available: boolean;
  note?: string;
}

export interface AvailabilityUpdateDTO {
  entries: AvailabilityEntryDTO[];
}

export interface AvailabilityResponseDTO {
  id: number;
  employee_id: number;
  day_of_week: number;
  available: boolean;
  note: string | null;
}

export async function getMySchedule(): Promise<MyShiftDTO[]> {
  const { data } = await api.get('/my/schedule');
  return data;
}

export async function getMyOvertime(): Promise<MyOvertimeDTO> {
  const { data } = await api.get('/my/overtime');
  return data;
}

export async function createShiftSwap(dto: ShiftSwapCreateDTO): Promise<ShiftSwapResponseDTO> {
  const { data } = await api.post('/shift-swaps', dto);
  return data;
}

export async function getMyShiftSwaps(): Promise<ShiftSwapResponseDTO[]> {
  const { data } = await api.get('/shift-swaps/me');
  return data;
}

export async function updateMyAvailability(dto: AvailabilityUpdateDTO): Promise<AvailabilityResponseDTO[]> {
  const { data } = await api.put('/my/availability', dto);
  return data;
}

export async function getMyAvailability(): Promise<AvailabilityResponseDTO[]> {
  const { data } = await api.get('/my/availability');
  return data;
}

export async function getMyTeamSchedule(scheduleId: number): Promise<MyShiftDTO[]> {
  const { data } = await api.get('/my/team-schedule', { params: { schedule_id: scheduleId } });
  return data;
}

export async function getMyTeamEmployees(): Promise<EmployeeResponseDTO[]> {
  const { data } = await api.get('/my/team-employees');
  return data;
}
