import api from '../lib/api';

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
}

export async function getShiftWishes(): Promise<ShiftWishResponseDTO[]> {
  const { data } = await api.get('/requests');
  return data;
}

export async function getShiftWish(id: number): Promise<ShiftWishResponseDTO> {
  const { data } = await api.get(`/requests/${id}`);
  return data;
}

export async function createShiftWish(dto: ShiftWishCreateDTO): Promise<ShiftWishResponseDTO> {
  const { data } = await api.post('/requests', dto);
  return data;
}

export async function updateShiftWish(id: number, dto: ShiftWishUpdateDTO): Promise<ShiftWishResponseDTO> {
  const { data } = await api.put(`/requests/${id}`, dto);
  return data;
}

export async function deleteShiftWish(id: number): Promise<void> {
  await api.delete(`/requests/${id}`);
}
