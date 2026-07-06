import { describe, it, expect } from 'vitest';
import { server } from '../../../test/msw-handlers';
import { http, HttpResponse } from 'msw';
import {
  getEmployees,
  getEmployee,
  createEmployee,
  updateEmployee,
  deleteEmployee,
  getEmployeeTimeAccount,
  getAllTimeAccounts,
  adjustTimeAccount,
} from '../employeeService';
import type { EmployeeCreateDTO, EmployeeUpdateDTO, TimeAccountAdjustDTO } from '../employeeService';

const base = '/api/v1';

describe('employeeService', () => {
  describe('getEmployees', () => {
    it('ruft GET /employees auf und gibt eine paginierte Liste zurück', async () => {
      const result = await getEmployees();
      expect(result).toHaveProperty('items');
      expect(Array.isArray(result.items)).toBe(true);
      expect(result.items.length).toBeGreaterThan(0);
      expect(result).toHaveProperty('total');
      expect(result).toHaveProperty('offset');
      expect(result).toHaveProperty('limit');
      expect(result.items[0]).toHaveProperty('id');
      expect(result.items[0]).toHaveProperty('first_name');
      expect(result.items[0]).toHaveProperty('last_name');
      expect(result.items[0]).toHaveProperty('email');
    });
  });

  describe('getEmployee', () => {
    it('ruft GET /employees/:id auf und gibt den Mitarbeiter zurück', async () => {
      const result = await getEmployee(1);
      expect(result).toHaveProperty('id', 1);
      expect(result).toHaveProperty('first_name');
      expect(result).toHaveProperty('last_name');
    });
  });

  describe('createEmployee', () => {
    it('sendet POST /employees mit CreateDTO und gibt den neuen Mitarbeiter zurück', async () => {
      const dto: EmployeeCreateDTO = {
        first_name: 'Test',
        last_name: 'User',
        email: 'test@example.com',
        role_ids: [1],
      };
      const result = await createEmployee(dto);
      expect(result).toHaveProperty('id');
      expect(result.first_name).toBe('Test');
      expect(result.last_name).toBe('User');
      expect(result.email).toBe('test@example.com');
    });
  });

  describe('updateEmployee', () => {
    it('sendet PUT /employees/:id mit UpdateDTO und gibt aktualisierten Mitarbeiter zurück', async () => {
      const dto: EmployeeUpdateDTO = {
        first_name: 'Updated',
        email: 'updated@example.com',
      };
      const result = await updateEmployee(1, dto);
      expect(result).toHaveProperty('id', 1);
      expect(result.first_name).toBe('Updated');
      expect(result.email).toBe('updated@example.com');
    });
  });

  describe('deleteEmployee', () => {
    it('sendet DELETE /employees/:id und gibt void zurück', async () => {
      const result = await deleteEmployee(1);
      expect(result).toBeUndefined();
    });
  });

  describe('getEmployeeTimeAccount', () => {
    it('ruft GET /employees/:id/time-account auf und gibt das Zeitkonto zurück', async () => {
      const result = await getEmployeeTimeAccount(1);
      expect(result).toHaveProperty('employee_id', 1);
      expect(result).toHaveProperty('employee_name');
      expect(result).toHaveProperty('current_balance');
      expect(result).toHaveProperty('history');
      expect(result).toHaveProperty('projected');
      expect(Array.isArray(result.history)).toBe(true);
    });
  });

  describe('getAllTimeAccounts', () => {
    it('ruft GET /employees/time-accounts auf und gibt eine paginierte Liste zurück', async () => {
      const result = await getAllTimeAccounts();
      expect(result).toHaveProperty('items');
      expect(Array.isArray(result.items)).toBe(true);
      expect(result.items.length).toBeGreaterThan(0);
      expect(result).toHaveProperty('total');
      expect(result).toHaveProperty('offset');
      expect(result).toHaveProperty('limit');
      expect(result.items[0]).toHaveProperty('employee_id');
      expect(result.items[0]).toHaveProperty('current_balance');
    });
  });

  describe('adjustTimeAccount', () => {
    it('sendet POST /employees/:id/time-account/adjust mit delta_hours und reason', async () => {
      const dto: TimeAccountAdjustDTO = {
        delta_hours: 5,
        reason: 'Korrektur',
      };
      const result = await adjustTimeAccount(1, dto);
      expect(result).toHaveProperty('employee_id', 1);
      expect(result).toHaveProperty('current_balance');
    });
  });

  describe('Fehlerbehandlung', () => {
    it('wirft einen Fehler bei 404 (Mitarbeiter nicht gefunden)', async () => {
      await expect(getEmployee(999)).rejects.toThrow();
    });

    it('wirft einen Fehler bei 404 (Zeitkonto nicht gefunden)', async () => {
      await expect(getEmployeeTimeAccount(999)).rejects.toThrow();
    });

    it('behandelt Netzwerkfehler (abgelehntes Promise)', async () => {
      server.use(
        http.get(`${base}/employees`, () => HttpResponse.error())
      );
      await expect(getEmployees()).rejects.toThrow();
    }, 15000);
  });
});
