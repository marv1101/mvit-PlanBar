import api from '../lib/api';

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
  created_at: string;
  updated_at: string;
}

export async function getEmployees(): Promise<EmployeeResponseDTO[]> {
  const { data } = await api.get('/employees');
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
