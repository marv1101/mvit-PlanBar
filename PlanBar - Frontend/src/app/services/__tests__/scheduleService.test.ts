import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { Mock } from 'vitest';
import { server } from '../../../test/msw-handlers';
import { http, HttpResponse } from 'msw';
import {
  getSchedules,
  getSchedule,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  submitScheduleToTito,
  retrySchedule,
  getScheduleSummary,
  getScheduleShifts,
  updateShiftplan,
  replaceAllShifts,
  downloadSchedulePdf,
  downloadScheduleIcal,
} from '../scheduleService';
import type { ScheduleCreateDTO, ScheduleUpdateDTO, ShiftplanCreateDTO } from '../scheduleService';

const base = '/api/v1';

describe('scheduleService', () => {
  describe('getSchedules', () => {
    it('ruft GET /schedules auf und gibt eine paginierte Liste zurück', async () => {
      const result = await getSchedules();
      expect(result).toHaveProperty('items');
      expect(Array.isArray(result.items)).toBe(true);
      expect(result.items.length).toBeGreaterThan(0);
      expect(result).toHaveProperty('total');
      expect(result).toHaveProperty('offset');
      expect(result).toHaveProperty('limit');
      expect(result.items[0]).toHaveProperty('id');
      expect(result.items[0]).toHaveProperty('name');
      expect(result.items[0]).toHaveProperty('status');
    });
  });

  describe('getSchedule', () => {
    it('ruft GET /schedules/:id auf und gibt den Schichtplan zurück', async () => {
      const result = await getSchedule(1);
      expect(result).toHaveProperty('id', 1);
      expect(result).toHaveProperty('name');
      expect(result).toHaveProperty('status');
    });
  });

  describe('createSchedule', () => {
    it('sendet POST /schedules mit CreateDTO und gibt den neuen Schichtplan zurück', async () => {
      const dto: ScheduleCreateDTO = {
        name: 'Test-Plan',
        week_type: 'A',
        shiftplans: [],
      };
      const result = await createSchedule(dto);
      expect(result).toHaveProperty('id');
      expect(result.name).toBe('Test-Plan');
      expect(result.status).toBe('draft');
    });
  });

  describe('updateSchedule', () => {
    it('sendet PUT /schedules/:id mit UpdateDTO und gibt aktualisierten Schichtplan zurück', async () => {
      const dto: ScheduleUpdateDTO = {
        name: 'Updated-Plan',
        status: 'draft',
      };
      const result = await updateSchedule(1, dto);
      expect(result).toHaveProperty('id', 1);
      expect(result.name).toBe('Updated-Plan');
    });
  });

  describe('submitScheduleToTito', () => {
    it('ruft POST /schedules/:id/submit auf und gibt aktualisierten Schichtplan zurück', async () => {
      const result = await submitScheduleToTito(1);
      expect(result).toHaveProperty('id', 1);
      expect(result.status).toBe('submitted');
      expect(result).toHaveProperty('tito_job_id');
    });
  });

  describe('retrySchedule', () => {
    it('ruft POST /schedules/:id/retry auf und gibt aktualisierten Schichtplan zurück', async () => {
      const result = await retrySchedule(1);
      expect(result).toHaveProperty('id', 1);
      expect(result.status).toBe('submitted');
      expect(result).toHaveProperty('tito_job_id');
    });
  });

  describe('getScheduleSummary', () => {
    it('ruft GET /schedules/:id/summary auf und gibt die Zusammenfassung zurück', async () => {
      const result = await getScheduleSummary(1);
      expect(result).toHaveProperty('id', 1);
      expect(result).toHaveProperty('name');
      expect(result).toHaveProperty('status');
      expect(result).toHaveProperty('total_shifts');
      expect(result).toHaveProperty('total_employees');
    });
  });

  describe('getScheduleShifts', () => {
    it('ruft GET /schedules/:id/shifts auf und gibt paginierte Schichten zurück', async () => {
      const result = await getScheduleShifts(1);
      expect(result).toHaveProperty('items');
      expect(Array.isArray(result.items)).toBe(true);
      expect(result).toHaveProperty('total');
      expect(result).toHaveProperty('offset');
      expect(result).toHaveProperty('limit');
    });
  });

  describe('replaceAllShifts', () => {
    it('sendet PUT /schedules/:id/shifts mit shiftplans-Array', async () => {
      const shifts: ShiftplanCreateDTO[] = [
        {
          employee_id: 1,
          date: '2026-06-22',
          shift_id: 's1',
          start_time: '08:00',
          end_time: '16:00',
        },
      ];
      const result = await replaceAllShifts(1, shifts);
      expect(result).toHaveProperty('id', 1);
    });
  });

  describe('updateShiftplan', () => {
    it('sendet PUT /schedules/:scheduleId/shifts/:shiftplanId mit Teil-Update', async () => {
      const result = await updateShiftplan(1, 1, { label: 'Frühschicht' });
      expect(result).toHaveProperty('id');
      expect(result).toHaveProperty('schedule_id', 1);
      expect(result).toHaveProperty('employee_id');
    });
  });

  describe('deleteSchedule', () => {
    it('sendet DELETE /schedules/:id und gibt void zurück', async () => {
      const result = await deleteSchedule(1);
      expect(result).toBeUndefined();
    });
  });

  describe('Fehlerbehandlung', () => {
    it('wirft einen Fehler bei 404 (Schichtplan nicht gefunden)', async () => {
      await expect(getSchedule(999)).rejects.toThrow();
    });

    it('behandelt Netzwerkfehler (abgelehntes Promise)', async () => {
      server.use(
        http.get(`${base}/schedules`, () => HttpResponse.error())
      );
      await expect(getSchedules()).rejects.toThrow();
    }, 15000);
  });

  describe('downloadSchedulePdf', () => {
    let clickSpy: ReturnType<typeof vi.spyOn>;
    let capturedUrls: string[];

    beforeEach(() => {
      URL.createObjectURL = vi.fn(() => 'blob:mock-url') as any;
      URL.revokeObjectURL = vi.fn() as any;
      clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      capturedUrls = [];
    });

    afterEach(() => {
      vi.restoreAllMocks();
      delete (URL as any).createObjectURL;
      delete (URL as any).revokeObjectURL;
    });

    it('ruft GET /exports/schedule/:id/pdf auf und lädt die Datei als schichtplan-<name>.pdf herunter', async () => {
      server.use(
        http.get(`${base}/exports/schedule/1/pdf`, ({ request }) => {
          capturedUrls.push(request.url);
          return new HttpResponse(new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d]), {
            headers: { 'Content-Type': 'application/pdf' },
          });
        })
      );

      await downloadSchedulePdf(1, 'KW 25');

      expect(capturedUrls[0]).toContain('/api/v1/exports/schedule/1/pdf');
      expect((URL.createObjectURL as Mock).mock.calls.length).toBe(1);
      const pdfBlob = (URL.createObjectURL as Mock).mock.calls[0][0] as Blob;
      expect(pdfBlob).toBeInstanceOf(Blob);
      expect(pdfBlob.type).toBe('application/pdf');
      expect((URL.revokeObjectURL as Mock).mock.calls.length).toBe(1);
      expect((URL.revokeObjectURL as Mock).mock.calls[0][0]).toContain('blob:mock-url');
      expect(clickSpy).toHaveBeenCalledTimes(1);
      const anchor = clickSpy.mock.contexts[0] as HTMLAnchorElement;
      expect(anchor.download).toBe('schichtplan-KW 25.pdf');
      expect(anchor.href).toContain('blob:mock-url');
    });

    it('gibt Fehler bei 404 weiter', async () => {
      server.use(
        http.get(`${base}/exports/schedule/999/pdf`, () =>
          HttpResponse.json({ detail: 'Schedule not found' }, { status: 404 })
        )
      );

      await expect(downloadSchedulePdf(999, 'X')).rejects.toMatchObject({
        response: { status: 404 },
      });
    });
  });

  describe('downloadScheduleIcal', () => {
    let clickSpy: ReturnType<typeof vi.spyOn>;
    let capturedUrls: string[];

    beforeEach(() => {
      URL.createObjectURL = vi.fn(() => 'blob:mock-url') as any;
      URL.revokeObjectURL = vi.fn() as any;
      clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      capturedUrls = [];
    });

    afterEach(() => {
      vi.restoreAllMocks();
      delete (URL as any).createObjectURL;
      delete (URL as any).revokeObjectURL;
    });

    it('ruft GET /exports/schedule/:id/ical auf und lädt die Datei als schichtplan-<name>.ics herunter', async () => {
      server.use(
        http.get(`${base}/exports/schedule/1/ical`, ({ request }) => {
          capturedUrls.push(request.url);
          return new HttpResponse('BEGIN:VCALENDAR', {
            headers: { 'Content-Type': 'text/calendar' },
          });
        })
      );

      await downloadScheduleIcal(1, 'KW 25');

      expect(capturedUrls[0]).toContain('/api/v1/exports/schedule/1/ical');
      expect((URL.createObjectURL as Mock).mock.calls.length).toBe(1);
      const icalBlob = (URL.createObjectURL as Mock).mock.calls[0][0] as Blob;
      expect(icalBlob).toBeInstanceOf(Blob);
      expect(icalBlob.type).toBe('text/calendar');
      expect((URL.revokeObjectURL as Mock).mock.calls.length).toBe(1);
      expect((URL.revokeObjectURL as Mock).mock.calls[0][0]).toContain('blob:mock-url');
      expect(clickSpy).toHaveBeenCalledTimes(1);
      const anchor = clickSpy.mock.contexts[0] as HTMLAnchorElement;
      expect(anchor.download).toBe('schichtplan-KW 25.ics');
      expect(anchor.href).toContain('blob:mock-url');
    });

    it('gibt Fehler bei 404 weiter', async () => {
      server.use(
        http.get(`${base}/exports/schedule/999/ical`, () =>
          HttpResponse.json({ detail: 'Schedule not found' }, { status: 404 })
        )
      );

      await expect(downloadScheduleIcal(999, 'X')).rejects.toMatchObject({
        response: { status: 404 },
      });
    });
  });
});
