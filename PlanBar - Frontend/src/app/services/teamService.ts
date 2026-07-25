import api from '../lib/api';
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
  const { data } = await api.put(`/teams/${id}`, dto);
  return data;
}

export async function deleteTeam(id: number): Promise<void> {
  await api.delete(`/teams/${id}`);
}

export async function assignTeamEmployees(id: number, dto: TeamAssignmentDTO): Promise<Team> {
  const { data } = await api.post(`/teams/${id}/employees`, dto);
  return data;
}

export async function getTeam(id: number): Promise<Team> {
  const { data } = await api.get(`/teams/${id}`);
  return data;
}