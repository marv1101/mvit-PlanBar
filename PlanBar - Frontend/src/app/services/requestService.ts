import api from '../lib/api';
import { getStoredEtag, setStoredEtag } from '../lib/api';
import type { PaginatedResponse } from '../types';

export type ShiftWishType = 'preferred' | 'unavailable' | 'vacation';

export interface ShiftWishCreateDTO {
  employee_id: number;
  date: string;
  week?: number;
  type: ShiftWishType;
  note?: string;
}

export interface ShiftWishUpdateDTO {
  employee_id?: number;
  date?: string;
  week?: number;
  type?: ShiftWishType;
  note?: string;
}

export interface ShiftWishResponseDTO {
  id: number;
  employee_id: number;
  date: string;
  week: number | null;
  type: string;
  note: string | null;
  status: string;
  reviewed_by: number | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
}

export async function getShiftWishes(offset?: number, limit?: number): Promise<PaginatedResponse<ShiftWishResponseDTO>> {
  const { data } = await api.get('/requests', { params: { offset, limit } });
  return data;
}

export async function getShiftWish(id: number): Promise<ShiftWishResponseDTO> {
  const response = await api.get(`/requests/${id}`);
  const etag = response.headers['etag'];
  if (etag) setStoredEtag(`/requests/${id}`, etag);
  return response.data;
}

export async function createShiftWish(dto: ShiftWishCreateDTO): Promise<ShiftWishResponseDTO> {
  const { data } = await api.post('/requests', dto);
  return data;
}

export async function updateShiftWish(id: number, dto: ShiftWishUpdateDTO): Promise<ShiftWishResponseDTO> {
  const url = `/requests/${id}`;
  const headers: Record<string, string> = {};
  const etag = getStoredEtag(url);
  if (etag) headers['If-Match'] = etag;
  const response = await api.put(url, dto, { headers });
  const newEtag = response.headers['etag'];
  if (newEtag) setStoredEtag(url, newEtag);
  return response.data;
}

export async function deleteShiftWish(id: number): Promise<void> {
  await api.delete(`/requests/${id}`);
}

export async function approveShiftWish(id: number): Promise<ShiftWishResponseDTO> {
  const { data } = await api.put(`/requests/${id}/approve`);
  return data;
}

export async function rejectShiftWish(id: number, rejectionReason?: string): Promise<ShiftWishResponseDTO> {
  const { data } = await api.put(`/requests/${id}/reject`, { rejection_reason: rejectionReason || null });
  return data;
}

export async function getPendingShiftWishes(scheduleId: number, offset?: number, limit?: number): Promise<PaginatedResponse<ShiftWishResponseDTO>> {
  const { data } = await api.get(`/schedules/${scheduleId}/wishes/pending`, { params: { offset, limit } });
  return data;
}

export async function getWishesByStatus(scheduleId: number, status: string = 'approved', offset?: number, limit?: number): Promise<PaginatedResponse<ShiftWishResponseDTO>> {
  const { data } = await api.get(`/schedules/${scheduleId}/wishes`, { params: { status, offset, limit } });
  return data;
}
