import api from '../lib/api';
import type { PaginatedResponse } from '../types';

export interface AdminUserCreateDTO {
  username: string;
  email: string;
  role: string;
  employee_id?: number;
  team_ids?: number[];
}

export interface UserUpdateDTO {
  username?: string;
  email?: string;
  password?: string;
  role?: string;
  employee_id?: number | null;
}

export interface UserResponseDTO {
  id: number;
  username: string;
  email: string;
  role: string;
  must_change_password: boolean;
  employee_id: number | null;
  created_at: string;
  updated_at: string;
  last_login: string | null;
}

export interface AdminUserCreateResponseDTO extends UserResponseDTO {
  initial_password: string;
}

export interface UnlinkedEmployeeDTO {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
}

export async function getUsers(offset?: number, limit?: number): Promise<PaginatedResponse<UserResponseDTO>> {
  const { data } = await api.get('/users', { params: { offset, limit } });
  return data;
}

export async function adminCreateUser(dto: AdminUserCreateDTO): Promise<AdminUserCreateResponseDTO> {
  const { data } = await api.post('/users/admin-create', dto);
  return data;
}

export async function updateUser(id: number, dto: UserUpdateDTO): Promise<UserResponseDTO> {
  const { data } = await api.put(`/users/${id}`, dto);
  return data;
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<UserResponseDTO> {
  const { data } = await api.post('/users/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  });
  return data;
}

export async function getUnlinkedEmployees(): Promise<UnlinkedEmployeeDTO[]> {
  const { data } = await api.get('/users/employees/unlinked');
  return data;
}

export async function getAllEmployees(): Promise<Array<{ id: number; first_name: string; last_name: string; email: string | null; user_id: number | null }>> {
  const { data } = await api.get('/employees', { params: { limit: 1000 } });
  return data.items;
}

export async function deleteUser(id: number): Promise<void> {
  await api.delete(`/users/${id}`);
}
