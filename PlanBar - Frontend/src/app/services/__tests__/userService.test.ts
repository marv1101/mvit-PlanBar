import { describe, it, expect } from 'vitest';
import { server } from '../../../test/msw-handlers';
import { http, HttpResponse } from 'msw';
import {
  getUsers,
  adminCreateUser,
  changePassword,
  deleteUser,
  getUnlinkedEmployees,
} from '../userService';
import type { AdminUserCreateDTO } from '../userService';

const base = '/api/v1';

describe('userService', () => {
  describe('getUsers', () => {
    it('ruft GET /users auf und gibt eine Liste zurück', async () => {
      const result = await getUsers();
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0]).toHaveProperty('id');
      expect(result[0]).toHaveProperty('username');
      expect(result[0]).toHaveProperty('email');
      expect(result[0]).toHaveProperty('role');
    });
  });

  describe('adminCreateUser', () => {
    it('sendet POST /users/admin-create mit CreateDTO und gibt neuen Benutzer mit initial_password zurück', async () => {
      const dto: AdminUserCreateDTO = {
        username: 'newuser',
        email: 'new@example.com',
        role: 'user',
      };
      const result = await adminCreateUser(dto);
      expect(result).toHaveProperty('id');
      expect(result.username).toBe('newuser');
      expect(result.email).toBe('new@example.com');
      expect(result.role).toBe('user');
      expect(result).toHaveProperty('initial_password');
    });
  });

  describe('changePassword', () => {
    it('sendet POST /users/change-password mit altem und neuem Passwort', async () => {
      const result = await changePassword('old123', 'new456');
      expect(result).toHaveProperty('id');
      expect(result).toHaveProperty('username');
      expect(result.must_change_password).toBe(false);
    });
  });

  describe('deleteUser', () => {
    it('sendet DELETE /users/:id und gibt void zurück', async () => {
      const result = await deleteUser(1);
      expect(result).toBeUndefined();
    });
  });

  describe('getUnlinkedEmployees', () => {
    it('ruft GET /users/employees/unlinked auf und gibt eine Liste zurück', async () => {
      const result = await getUnlinkedEmployees();
      expect(Array.isArray(result)).toBe(true);
      if (result.length > 0) {
        expect(result[0]).toHaveProperty('id');
        expect(result[0]).toHaveProperty('first_name');
        expect(result[0]).toHaveProperty('last_name');
      }
    });
  });

  describe('Fehlerbehandlung', () => {
    it('behandelt Netzwerkfehler (abgelehntes Promise)', async () => {
      server.use(
        http.get(`${base}/users`, () => HttpResponse.error())
      );
      await expect(getUsers()).rejects.toThrow();
    }, 15000);
  });
});
