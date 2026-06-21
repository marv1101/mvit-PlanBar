import { describe, it, expect } from 'vitest';
import { server } from '../../../test/msw-handlers';
import { http, HttpResponse } from 'msw';
import {
  getRoles,
  createRole,
  updateRole,
  deleteRole,
} from '../roleService';
import type { RoleCreateDTO, RoleUpdateDTO } from '../roleService';

const base = '/api/v1';

describe('roleService', () => {
  describe('getRoles', () => {
    it('ruft GET /roles auf und gibt eine Liste zurück', async () => {
      const result = await getRoles();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0]).toHaveProperty('id');
      expect(result[0]).toHaveProperty('name');
    });
  });

  describe('createRole', () => {
    it('sendet POST /roles mit CreateDTO und gibt die neue Rolle zurück', async () => {
      const dto: RoleCreateDTO = {
        name: 'Test-Rolle',
        color: '#ff00ff',
      };
      const result = await createRole(dto);
      expect(result).toHaveProperty('id');
      expect(result.name).toBe('Test-Rolle');
      expect(result.color).toBe('#ff00ff');
    });
  });

  describe('updateRole', () => {
    it('sendet PUT /roles/:id mit UpdateDTO und gibt die aktualisierte Rolle zurück', async () => {
      const dto: RoleUpdateDTO = {
        name: 'Geänderte Rolle',
        color: '#00ff00',
      };
      const result = await updateRole(1, dto);
      expect(result).toHaveProperty('id', 1);
      expect(result.name).toBe('Geänderte Rolle');
      expect(result.color).toBe('#00ff00');
    });
  });

  describe('deleteRole', () => {
    it('sendet DELETE /roles/:id und gibt void zurück', async () => {
      const result = await deleteRole(1);
      expect(result).toBeUndefined();
    });
  });

  describe('Fehlerbehandlung', () => {
    it('behandelt Netzwerkfehler (abgelehntes Promise)', async () => {
      server.use(
        http.get(`${base}/roles`, () => HttpResponse.error())
      );
      await expect(getRoles()).rejects.toThrow();
    }, 15000);
  });
});
