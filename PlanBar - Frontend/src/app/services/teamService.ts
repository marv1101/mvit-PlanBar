import api from '../lib/api';
import { getStoredEtag, setStoredEtag } from '../lib/api';
import type { PaginatedResponse, Team } from '../types';

export interface TeamCreateDTO {
  name: string;
  color?: string;
  description?: string;
}

export interface TeamUpdateDTO {
  name?: string;
  color?: string;
  description?: string;
}

export interface TeamAssignmentDTO {
  employee_ids: number[];
}

export async function getTeams(offset?: number, limit?: number): Promise<PaginatedResponse<Team>> {
  const { data } = await api.get('/teams', { params: { offset, limit } });
  return data;
}

export async function getMyTeams(): Promise<Team[]> {
  const { data } = await api.get('/teams/mine');
  return data;
}

export async function createTeam(dto: TeamCreateDTO): Promise<Team> {
  const { data } = await api.post('/teams', dto);
  return data;
}

export async function updateTeam(id: number, dto: TeamUpdateDTO): Promise<Team> {
  const url = `/teams/${id}`;
  const headers: Record<string, string> = {};
  const etag = getStoredEtag(url);
  if (etag) headers['If-Match'] = etag;
  const response = await api.put(url, dto, { headers });
  const newEtag = response.headers['etag'];
  if (newEtag) setStoredEtag(url, newEtag);
  return response.data;
}

export async function deleteTeam(id: number): Promise<void> {
  await api.delete(`/teams/${id}`);
}

export async function assignTeamEmployees(id: number, dto: TeamAssignmentDTO): Promise<Team & { employee_ids: number[] }> {
  const { data } = await api.post(`/teams/${id}/employees`, dto);
  return data;
}

export async function getTeam(id: number): Promise<Team & { employee_ids: number[] }> {
  const response = await api.get(`/teams/${id}`);
  const etag = response.headers['etag'];
  if (etag) setStoredEtag(`/teams/${id}`, etag);
  return response.data;
}