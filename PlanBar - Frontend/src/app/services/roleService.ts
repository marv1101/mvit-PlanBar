import api from '../lib/api';
import type { PaginatedResponse } from '../types';

export interface RoleCreateDTO {
  name: string;
  color?: string;
  permissions?: string;
}

export interface RoleUpdateDTO {
  name?: string;
  color?: string;
  permissions?: string;
}

export interface RoleResponseDTO {
  id: number;
  name: string;
  color: string | null;
  permissions: string | null;
}

export async function getRoles(offset?: number, limit?: number): Promise<PaginatedResponse<RoleResponseDTO>> {
  const { data } = await api.get('/roles', { params: { offset, limit } });
  return data;
}

export async function createRole(dto: RoleCreateDTO): Promise<RoleResponseDTO> {
  const { data } = await api.post('/roles', dto);
  return data;
}

export async function updateRole(id: number, dto: RoleUpdateDTO): Promise<RoleResponseDTO> {
  const { data } = await api.put(`/roles/${id}`, dto);
  return data;
}

export async function deleteRole(id: number): Promise<void> {
  await api.delete(`/roles/${id}`);
}
