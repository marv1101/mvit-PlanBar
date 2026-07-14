import { db, OfflineQueueItem } from './db';
import api from './api';
import { toast } from 'sonner';

class SyncManager {
  private processing = false;
  private listeners: Array<(status: SyncStatus) => void> = [];

  get isProcessing(): boolean {
    return this.processing;
  }

  subscribe(listener: (status: SyncStatus) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  private notify(status: SyncStatus): void {
    for (const listener of this.listeners) {
      listener(status);
    }
  }

  async enqueue(url: string, method: string, body: unknown, headers?: Record<string, string>): Promise<void> {
    const item: OfflineQueueItem = {
      id: crypto.randomUUID(),
      url,
      method,
      headers: headers || {},
      body,
      syncStatus: 'pending',
      createdAt: new Date().toISOString(),
      retryCount: 0,
    };
    await db.put('offlineQueue', item);

    if ('serviceWorker' in navigator && 'sync' in navigator.serviceWorker) {
      try {
        const registration = await navigator.serviceWorker.ready;
        await registration.sync.register('sync-offline-actions');
      } catch {
        // Background sync not available, will be processed on next online event
      }
    }
  }

  async processQueue(): Promise<{ synced: number; failed: number }> {
    if (this.processing) return { synced: 0, failed: 0 };
    this.processing = true;
    this.notify({ type: 'syncing' });

    const items = await db.getAll('offlineQueue');
    const pending = items.filter(i => i.syncStatus !== 'syncing');

    if (pending.length === 0) {
      this.processing = false;
      this.notify({ type: 'idle' });
      return { synced: 0, failed: 0 };
    }

    let synced = 0;
    let failed = 0;

    for (const item of pending) {
      item.syncStatus = 'syncing';
      await db.put('offlineQueue', item);

      try {
        const config: Record<string, unknown> = {
          method: item.method,
          url: item.url,
          data: item.body,
          headers: item.headers,
          timeout: 30000,
        };

        await api(config);
        await db.delete('offlineQueue', item.id);
        synced++;
      } catch (err: unknown) {
        item.retryCount++;
        item.syncStatus = item.retryCount >= 5 ? 'failed' : 'pending';
        item.error = err instanceof Error ? err.message : 'Unknown error';
        await db.put('offlineQueue', item);
        failed++;
      }
    }

    this.processing = false;
    this.notify({ type: synced > 0 ? 'completed' : 'idle' });

    if (synced > 0) {
      toast.success(`${synced} ${synced === 1 ? 'Änderung' : 'Änderungen'} synchronisiert`);
    }
    if (failed > 0) {
      toast.error(`${failed} ${failed === 1 ? 'Änderung konnte' : 'Änderungen konnten'} nicht synchronisiert werden`);
    }

    return { synced, failed };
  }

  getQueueLength(): Promise<number> {
    return db.getAll('offlineQueue').then(items =>
      items.filter(i => i.syncStatus === 'pending').length
    );
  }

  async getFailedItems(): Promise<OfflineQueueItem[]> {
    const items = await db.getAll('offlineQueue');
    return items.filter(i => i.syncStatus === 'failed');
  }

  async clearFailed(): Promise<void> {
    const items = await db.getAll('offlineQueue');
    const failed = items.filter(i => i.syncStatus === 'failed');
    for (const item of failed) {
      await db.delete('offlineQueue', item.id);
    }
  }

  async getSyncMeta(key: string): Promise<string | null> {
    const entry = await db.get('syncMeta', key);
    return entry?.value as string || null;
  }

  async setSyncMeta(key: string, value: string): Promise<void> {
    await db.put('syncMeta', { key, value, updatedAt: new Date().toISOString() });
  }
}

export interface SyncStatus {
  type: 'idle' | 'syncing' | 'completed' | 'error';
  details?: string;
}

export const syncManager = new SyncManager();

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    setTimeout(() => syncManager.processQueue(), 1000);
  });

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'PROCESS_OFFLINE_QUEUE') {
        syncManager.processQueue();
      }
      if (event.data?.type === 'SYNC_INITIAL_DATA') {
        syncManager.processQueue();
      }
    });
  }
}
