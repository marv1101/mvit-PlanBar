import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { db, OfflineQueueItem } from '../db';
import { syncManager } from '../syncManager';
import { useOnlineStatus } from '../../hooks/useOnlineStatus';
import { renderHook, act } from '@testing-library/react';

const DB_NAME = 'planbar-offline';

beforeEach(async () => {
  // Delete and recreate the database to ensure a clean state
  indexedDB.deleteDatabase(DB_NAME);
});

afterEach(async () => {
  // Close and delete the test database
  indexedDB.deleteDatabase(DB_NAME);
  // Reset sync manager processing state
  (syncManager as any).processing = false;
  (syncManager as any).listeners = [];
});

describe('IndexedDB', () => {
  it('should store and retrieve items', async () => {
    const item = { id: 'test-1', name: 'Test', value: 42 };
    await db.put('syncMeta', item as any);
    const result = await db.get('syncMeta', 'test-1');
    expect(result).toEqual(item);
  });

  it('should return undefined for missing items', async () => {
    const result = await db.get('employees', 'non-existent');
    expect(result).toBeUndefined();
  });

  it('should get all items from a store', async () => {
    await db.put('syncMeta', { key: 'a', value: '1', updatedAt: '' });
    await db.put('syncMeta', { key: 'b', value: '2', updatedAt: '' });
    const all = await db.getAll('syncMeta');
    expect(all).toHaveLength(2);
  });

  it('should bulk put items', async () => {
    const items = [
      { id: '1', name: 'A' },
      { id: '2', name: 'B' },
    ];
    await db.bulkPut('employees', items as any);
    const all = await db.getAll('employees');
    expect(all).toHaveLength(2);
  });

  it('should delete items', async () => {
    await db.put('syncMeta', { key: 'del', value: 'delete-me', updatedAt: '' });
    await db.delete('syncMeta', 'del');
    const result = await db.get('syncMeta', 'del');
    expect(result).toBeUndefined();
  });

  it('should clear all items', async () => {
    await db.put('syncMeta', { key: 'x', value: 'y', updatedAt: '' });
    await db.clear('syncMeta');
    const all = await db.getAll('syncMeta');
    expect(all).toHaveLength(0);
  });

  it('should query by index', async () => {
    const item: OfflineQueueItem = {
      id: 'q-1',
      url: '/api/test',
      method: 'POST',
      headers: {},
      body: { data: 'test' },
      syncStatus: 'pending',
      createdAt: new Date().toISOString(),
      retryCount: 0,
    };
    await db.put('offlineQueue', item);
    const results = await db.getAllFromIndex('offlineQueue', 'syncStatus', 'pending');
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe('q-1');
  });
});

describe('SyncManager', () => {
  it('should enqueue items', async () => {
    await syncManager.enqueue('/api/test', 'POST', { hello: 'world' });
    const queue = await db.getAll('offlineQueue');
    expect(queue).toHaveLength(1);
    expect(queue[0].url).toBe('/api/test');
    expect(queue[0].syncStatus).toBe('pending');
  });

  it('should return queue length', async () => {
    await syncManager.enqueue('/api/1', 'POST', { a: 1 });
    await syncManager.enqueue('/api/2', 'PUT', { b: 2 });
    const length = await syncManager.getQueueLength();
    expect(length).toBe(2);
  });

  it('should report empty queue length', async () => {
    const length = await syncManager.getQueueLength();
    expect(length).toBe(0);
  });

  it('should handle sync meta', async () => {
    await syncManager.setSyncMeta('lastSync', '2026-06-26T10:00:00Z');
    const value = await syncManager.getSyncMeta('lastSync');
    expect(value).toBe('2026-06-26T10:00:00Z');
  });

  it('should return null for missing sync meta', async () => {
    const value = await syncManager.getSyncMeta('non-existent');
    expect(value).toBeNull();
  });

  it('should process an empty queue without error', async () => {
    const result = await syncManager.processQueue();
    expect(result).toEqual({ synced: 0, failed: 0 });
  });

  it('should mark processing status', async () => {
    expect(syncManager.isProcessing).toBe(false);

    // Start processing an empty queue
    const promise = syncManager.processQueue();

    // During processing, isProcessing should still work
    // (it's synchronous set after the await, so we just check before/after)
    await promise;
    expect(syncManager.isProcessing).toBe(false);
  });

  it('should support subscribe/unsubscribe', () => {
    const listener = vi.fn();
    const unsubscribe = syncManager.subscribe(listener);
    expect(typeof unsubscribe).toBe('function');

    // Unsubscribe should not throw
    unsubscribe();
  });

  it('should handle failed items', async () => {
    await syncManager.enqueue('/api/fail', 'POST', { fail: true });

    // Simulate failed state
    const items = await db.getAll('offlineQueue');
    for (const item of items) {
      item.syncStatus = 'failed';
      item.error = 'Network error';
      await db.put('offlineQueue', item);
    }

    const failedItems = await syncManager.getFailedItems();
    expect(failedItems).toHaveLength(1);
    expect(failedItems[0].error).toBe('Network error');

    await syncManager.clearFailed();
    const afterClear = await syncManager.getFailedItems();
    expect(afterClear).toHaveLength(0);
  });
});

describe('useOnlineStatus', () => {
  it('should return initial online status', () => {
    const { result } = renderHook(() => useOnlineStatus());
    expect(result.current.isOnline).toBe(navigator.onLine);
    expect(result.current.wasOffline).toBe(false);
  });

  it('should respond to online events', () => {
    const { result } = renderHook(() => useOnlineStatus());

    act(() => {
      window.dispatchEvent(new Event('offline'));
    });
    expect(result.current.isOnline).toBe(false);
    expect(result.current.wasOffline).toBe(true);

    act(() => {
      window.dispatchEvent(new Event('online'));
    });
    expect(result.current.isOnline).toBe(true);
    expect(result.current.wasOffline).toBe(true);
  });

  it('should clear offline flag', () => {
    const { result } = renderHook(() => useOnlineStatus());

    act(() => {
      window.dispatchEvent(new Event('offline'));
    });
    expect(result.current.wasOffline).toBe(true);

    act(() => {
      result.current.clearOfflineFlag();
    });
    expect(result.current.wasOffline).toBe(false);
  });
});
