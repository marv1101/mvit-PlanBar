import api from '../lib/api';
import type { PaginatedResponse } from '../types';

export interface EmployeeCreateDTO {
  first_name: string;
  last_name: string;
  email?: string;
  color?: string;
  working_hours_json?: string;
  break_start?: string;
  break_end?: string;
  max_work_hours?: number;
  role_ids?: number[];
  team_ids?: number[];
}

export interface EmployeeUpdateDTO {
  first_name?: string;
  last_name?: string;
  email?: string;
  color?: string;
  working_hours_json?: string;
  break_start?: string;
  break_end?: string;
  max_work_hours?: number;
  role_ids?: number[];
  team_ids?: number[];
}

export interface EmployeeResponseDTO {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  color: string | null;
  working_hours_json: string | null;
  break_start: string | null;
  break_end: string | null;
  max_work_hours: number | null;
  user_id: number | null;
  role_ids: number[];
  team_ids: number[];
  created_at: string;
  updated_at: string;
}

export async function getEmployees(offset?: number, limit?: number): Promise<PaginatedResponse<EmployeeResponseDTO>> {
  const { data } = await api.get('/employees', { params: { offset, limit } });
  return data;
}

export async function getEmployee(id: number): Promise<EmployeeResponseDTO> {
  const { data } = await api.get(`/employees/${id}`);
  return data;
}

export async function createEmployee(dto: EmployeeCreateDTO): Promise<EmployeeResponseDTO> {
  const { data } = await api.post('/employees', dto);
  return data;
}

export async function updateEmployee(id: number, dto: EmployeeUpdateDTO): Promise<EmployeeResponseDTO> {
  const { data } = await api.put(`/employees/${id}`, dto);
  return data;
}

export async function deleteEmployee(id: number): Promise<void> {
  await api.delete(`/employees/${id}`);
}

export interface TimeAccountEntryDTO {
  week: number;
  year: number;
  scheduled_hours: number;
  contract_hours: number;
  delta: number;
  balance: number;
  manual_adjustment: number;
  adjustment_reason: string | null;
  total_change: number;
}

export interface TimeAccountProjectedDTO {
  from_schedule: number;
  expected_balance_after: number;
}

export interface TimeAccountResponseDTO {
  employee_id: number;
  employee_name: string;
  current_balance: number;
  history: TimeAccountEntryDTO[];
  projected: TimeAccountProjectedDTO | null;
}

export async function getEmployeeTimeAccount(id: number): Promise<TimeAccountResponseDTO> {
  const { data } = await api.get(`/employees/${id}/time-account`);
  return data;
}

export async function getAllTimeAccounts(offset?: number, limit?: number): Promise<PaginatedResponse<TimeAccountResponseDTO>> {
  const { data } = await api.get('/employees/time-accounts', { params: { offset, limit } });
  return data;
}

export interface TimeAccountAdjustDTO {
  delta_hours: number;
  reason?: string;
}

export async function adjustTimeAccount(id: number, dto: TimeAccountAdjustDTO): Promise<TimeAccountResponseDTO> {
  const { data } = await api.post(`/employees/${id}/time-account/adjust`, dto);
  return data;
}
