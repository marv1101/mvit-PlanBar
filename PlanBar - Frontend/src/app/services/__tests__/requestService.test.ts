import { describe, it, expect } from 'vitest';
import { server } from '../../../test/msw-handlers';
import { http, HttpResponse } from 'msw';
import {
  getShiftWishes,
  createShiftWish,
  updateShiftWish,
  deleteShiftWish,
  approveShiftWish,
  rejectShiftWish,
  getPendingShiftWishes,
} from '../requestService';
import type { ShiftWishCreateDTO, ShiftWishUpdateDTO } from '../requestService';

const base = '/api/v1';

describe('requestService', () => {
  describe('getShiftWishes', () => {
    it('ruft GET /requests auf und gibt eine paginierte Liste zurück', async () => {
      const result = await getShiftWishes();
      expect(result).toHaveProperty('items');
      expect(Array.isArray(result.items)).toBe(true);
      expect(result.items.length).toBeGreaterThan(0);
      expect(result).toHaveProperty('total');
      expect(result).toHaveProperty('offset');
      expect(result).toHaveProperty('limit');
      expect(result.items[0]).toHaveProperty('id');
      expect(result.items[0]).toHaveProperty('employee_id');
      expect(result.items[0]).toHaveProperty('date');
      expect(result.items[0]).toHaveProperty('type');
      expect(result.items[0]).toHaveProperty('status');
    });
  });

  describe('createShiftWish', () => {
    it('sendet POST /requests mit CreateDTO und gibt den neuen Wunsch zurück', async () => {
      const dto: ShiftWishCreateDTO = {
        employee_id: 1,
        date: '2026-07-01',
        type: 'vacation',
        note: 'Urlaub',
      };
      const result = await createShiftWish(dto);
      expect(result).toHaveProperty('id');
      expect(result.employee_id).toBe(1);
      expect(result.date).toBe('2026-07-01');
      expect(result.type).toBe('vacation');
      expect(result.status).toBe('pending');
    });
  });

  describe('updateShiftWish', () => {
    it('sendet PUT /requests/:id mit UpdateDTO und gibt den aktualisierten Wunsch zurück', async () => {
      const dto: ShiftWishUpdateDTO = {
        note: 'Aktualisierte Notiz',
      };
      const result = await updateShiftWish(1, dto);
      expect(result).toHaveProperty('id', 1);
      expect(result.note).toBe('Aktualisierte Notiz');
    });
  });

  describe('approveShiftWish', () => {
    it('ruft PUT /requests/:id/approve auf und gibt genehmigten Wunsch zurück', async () => {
      const result = await approveShiftWish(1);
      expect(result).toHaveProperty('id', 1);
      expect(result.status).toBe('approved');
      expect(result).toHaveProperty('reviewed_by');
      expect(result).toHaveProperty('reviewed_at');
    });
  });

  describe('rejectShiftWish', () => {
    it('sendet PUT /requests/:id/reject mit rejection_reason', async () => {
      const reason = 'Nicht verfügbar';
      const result = await rejectShiftWish(2, reason);
      expect(result).toHaveProperty('id', 2);
      expect(result.status).toBe('rejected');
      expect(result.rejection_reason).toBe(reason);
    });

    it('sendet rejection_reason als null wenn kein Grund angegeben wird', async () => {
      const result = await rejectShiftWish(2);
      expect(result).toHaveProperty('id', 2);
      expect(result.status).toBe('rejected');
      expect(result.rejection_reason).toBeNull();
    });
  });

  describe('deleteShiftWish', () => {
    it('sendet DELETE /requests/:id und gibt void zurück', async () => {
      const result = await deleteShiftWish(1);
      expect(result).toBeUndefined();
    });
  });

  describe('getPendingShiftWishes', () => {
    it('ruft GET /schedules/:scheduleId/wishes/pending auf und gibt paginierte offene Wünsche zurück', async () => {
      const result = await getPendingShiftWishes(1);
      expect(result).toHaveProperty('items');
      expect(Array.isArray(result.items)).toBe(true);
      for (const wish of result.items) {
        expect(wish.status).toBe('pending');
      }
    });
  });

  describe('Fehlerbehandlung', () => {
    it('behandelt Netzwerkfehler (abgelehntes Promise)', async () => {
      server.use(
        http.get(`${base}/requests`, () => HttpResponse.error())
      );
      await expect(getShiftWishes()).rejects.toThrow();
    }, 15000);
  });
});
