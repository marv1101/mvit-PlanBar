import { describe, it, expect, vi } from 'vitest';
import { server } from '../../../test/msw-handlers';
import { http, HttpResponse } from 'msw';
import {
  getThreads,
  createThread,
  getThread as getThreadDetail,
  deleteThread,
  deleteMessage,
  createMessage,
  getDocumentUrl,
  uploadDocument,
} from '../pinboardService';
import type { ThreadCreateDTO, MessageCreateDTO } from '../pinboardService';

const base = '/api/v1';

describe('pinboardService', () => {
  describe('getThreads', () => {
    it('ruft GET /pinboard/threads auf und gibt eine paginierte Liste zurück', async () => {
      const result = await getThreads();
      expect(result).toHaveProperty('items');
      expect(Array.isArray(result.items)).toBe(true);
      expect(result.items.length).toBeGreaterThan(0);
      expect(result).toHaveProperty('total');
      expect(result).toHaveProperty('offset');
      expect(result).toHaveProperty('limit');
      expect(result.items[0]).toHaveProperty('id');
      expect(result.items[0]).toHaveProperty('title');
      expect(result.items[0]).toHaveProperty('author_name');
    });
  });

  describe('createThread', () => {
    it('sendet POST /pinboard/threads mit CreateDTO und gibt den neuen Thread zurück', async () => {
      const dto: ThreadCreateDTO = {
        title: 'Neuer Thread',
      };
      const result = await createThread(dto);
      expect(result).toHaveProperty('id');
      expect(result.title).toBe('Neuer Thread');
    });
  });

  describe('getThreadDetail', () => {
    it('ruft GET /pinboard/threads/:id auf und gibt Thread-Detail mit Nachrichten zurück', async () => {
      const result = await getThreadDetail(1);
      expect(result).toHaveProperty('id', 1);
      expect(result).toHaveProperty('title');
      expect(result).toHaveProperty('messages');
      expect(Array.isArray(result.messages)).toBe(true);
    });

    it('wirft einen Fehler bei 404 (Thread nicht gefunden)', async () => {
      await expect(getThreadDetail(999)).rejects.toThrow();
    });
  });

  describe('createMessage', () => {
    it('sendet POST /pinboard/threads/:id/messages mit Inhalt und gibt die neue Nachricht zurück', async () => {
      const dto: MessageCreateDTO = {
        content: 'Testnachricht',
      };
      const result = await createMessage(1, dto);
      expect(result).toHaveProperty('id');
      expect(result.content).toBe('Testnachricht');
      expect(result).toHaveProperty('thread_id', 1);
    });
  });

  describe('deleteMessage', () => {
    it('sendet DELETE /pinboard/messages/:id und gibt void zurück', async () => {
      const result = await deleteMessage(1);
      expect(result).toBeUndefined();
    });
  });

  describe('deleteThread', () => {
    it('sendet DELETE /pinboard/threads/:id und gibt void zurück', async () => {
      const result = await deleteThread(1);
      expect(result).toBeUndefined();
    });
  });

  describe('getDocumentUrl', () => {
    it('gibt den korrekten URL-Pfad für ein Dokument zurück', async () => {
      const url = await getDocumentUrl(42);
      expect(url).toBe('/api/v1/pinboard/documents/42');
    });
  });

  describe('uploadDocument', () => {
    it('sendet POST /pinboard/messages/:id/documents mit FormData', async () => {
      let capturedContentType: string | null = null;

      server.use(
        http.post(`${base}/pinboard/messages/:messageId/documents`, async ({ request, params }) => {
          capturedContentType = request.headers.get('Content-Type') || null;

          return HttpResponse.json({
            id: 100,
            message_id: Number(params.messageId),
            file_name: 'dokument.pdf',
            file_size: 12,
            mime_type: 'application/pdf',
            created_at: new Date().toISOString(),
          });
        })
      );

      const file = new File(['test content'], 'dokument.pdf', { type: 'application/pdf' });
      const result = await uploadDocument(1, file);

      expect(capturedContentType).toContain('multipart/form-data');
      expect(result).toHaveProperty('id', 100);
      expect(result).toHaveProperty('file_name');
      expect(result).toHaveProperty('file_size');
      expect(result).toHaveProperty('mime_type', 'application/pdf');
    });
  });

  describe('Fehlerbehandlung', () => {
    it('behandelt Netzwerkfehler (abgelehntes Promise)', async () => {
      server.use(
        http.get(`${base}/pinboard/threads`, () => HttpResponse.error())
      );
      await expect(getThreads()).rejects.toThrow();
    }, 15000);
  });
});
