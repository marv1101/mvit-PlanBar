import api from '../lib/api';

export interface AdminUserCreateDTO {
  username: string;
  email: string;
  role: string;
  employee_id?: number;
}

export interface UserResponseDTO {
  id: number;
  username: string;
  email: string;
  role: string;
  must_change_password: boolean;
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

export async function getUsers(): Promise<UserResponseDTO[]> {
  const { data } = await api.get('/users');
  return data;
}

export async function adminCreateUser(dto: AdminUserCreateDTO): Promise<AdminUserCreateResponseDTO> {
  const { data } = await api.post('/users/admin-create', dto);
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

export async function deleteUser(id: number): Promise<void> {
  await api.delete(`/users/${id}`);
}
