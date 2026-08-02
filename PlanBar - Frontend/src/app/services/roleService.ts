import api from '../lib/api';
import { getStoredEtag, setStoredEtag } from '../lib/api';
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

export async function getRole(id: number): Promise<RoleResponseDTO> {
  const response = await api.get(`/roles/${id}`);
  const etag = response.headers['etag'];
  if (etag) setStoredEtag(`/roles/${id}`, etag);
  return response.data;
}

export async function updateRole(id: number, dto: RoleUpdateDTO): Promise<RoleResponseDTO> {
  const url = `/roles/${id}`;
  const headers: Record<string, string> = {};
  const etag = getStoredEtag(url);
  if (etag) headers['If-Match'] = etag;
  const response = await api.put(url, dto, { headers });
  const newEtag = response.headers['etag'];
  if (newEtag) setStoredEtag(url, newEtag);
  return response.data;
}

export async function deleteRole(id: number): Promise<void> {
  await api.delete(`/roles/${id}`);
}
