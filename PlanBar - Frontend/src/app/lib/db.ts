const DB_NAME = 'planbar-offline';
const DB_VERSION = 1;

type StoreName = 'employees' | 'schedules' | 'shifts' | 'requests' | 'roles' | 'offlineQueue' | 'syncMeta';

const STORES: Record<StoreName, { keyPath: string; indexes?: string[] }> = {
  employees: { keyPath: 'id', indexes: ['email'] },
  schedules: { keyPath: 'id', indexes: ['status'] },
  shifts: { keyPath: 'id', indexes: ['scheduleId', 'employeeId', 'date'] },
  requests: { keyPath: 'id', indexes: ['employeeId', 'status', 'date'] },
  roles: { keyPath: 'id', indexes: ['name'] },
  offlineQueue: { keyPath: 'id', indexes: ['syncStatus', 'createdAt'] },
  syncMeta: { keyPath: 'key' },
};

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      for (const [name, config] of Object.entries(STORES)) {
        if (!db.objectStoreNames.contains(name)) {
          const store = db.createObjectStore(name, { keyPath: config.keyPath });
          for (const idx of config.indexes || []) {
            store.createIndex(idx, idx, { unique: false });
          }
        }
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function withStore<T>(name: StoreName, mode: IDBTransactionMode, callback: (store: IDBObjectStore) => IDBRequest<T> | IDBRequest<T>[]): Promise<T> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(name, mode);
    const store = tx.objectStore(name);
    const result = callback(store);

    tx.oncomplete = () => {
      if (Array.isArray(result)) {
        Promise.all(result.map(r => new Promise((res, rej) => {
          r.onsuccess = () => res(r.result);
          r.onerror = () => rej(r.error);
        }))).then(r => resolve(r as T)).catch(reject);
      } else {
        result.onsuccess = () => resolve(result.result);
        result.onerror = () => reject(result.error);
      }
      db.close();
    };
    tx.onerror = () => {
      reject(tx.error);
      db.close();
    };
  });
}

type StoreItem<S extends StoreName> = S extends 'offlineQueue' ? OfflineQueueItem
  : S extends 'syncMeta' ? SyncMetaEntry
  : Record<string, unknown>;

export interface OfflineQueueItem {
  id: string;
  url: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
  syncStatus: 'pending' | 'syncing' | 'failed';
  createdAt: string;
  retryCount: number;
  error?: string;
}

export interface SyncMetaEntry {
  key: string;
  value: string;
  updatedAt: string;
}

export const db = {
  async getAll<S extends StoreName>(store: S): Promise<StoreItem<S>[]> {
    return withStore<StoreItem<S>[]>(store, 'readonly', (s) => {
      const request = s.getAll();
      return request as IDBRequest<StoreItem<S>[]>;
    });
  },

  async get<S extends StoreName>(store: S, id: string | number): Promise<StoreItem<S> | undefined> {
    return withStore<StoreItem<S> | undefined>(store, 'readonly', (s) => {
      return s.get(id) as IDBRequest<StoreItem<S> | undefined>;
    });
  },

  async put<S extends StoreName>(store: S, item: StoreItem<S>): Promise<void> {
    return withStore<void>(store, 'readwrite', (s) => {
      return s.put(item) as IDBRequest<void>;
    });
  },

  async delete(store: StoreName, id: string | number): Promise<void> {
    return withStore<void>(store, 'readwrite', (s) => s.delete(id) as IDBRequest<void>);
  },

  async clear(store: StoreName): Promise<void> {
    return withStore<void>(store, 'readwrite', (s) => s.clear() as IDBRequest<void>);
  },

  async getAllFromIndex<S extends StoreName>(store: S, indexName: string, value: unknown): Promise<StoreItem<S>[]> {
    return withStore<StoreItem<S>[]>(store, 'readonly', (s) => {
      const idx = s.index(indexName);
      return idx.getAll(value) as IDBRequest<StoreItem<S>[]>;
    });
  },

  async getByIndex<S extends StoreName>(store: S, indexName: string, value: unknown): Promise<StoreItem<S> | undefined> {
    const results = await db.getAllFromIndex(store, indexName, value);
    return results[0];
  },

  async bulkPut<S extends StoreName>(store: S, items: StoreItem<S>[]): Promise<void> {
    const dbConn = await openDB();
    return new Promise((resolve, reject) => {
      const tx = dbConn.transaction(store, 'readwrite');
      const objStore = tx.objectStore(store);
      for (const item of items) {
        objStore.put(item);
      }
      tx.oncomplete = () => { resolve(); dbConn.close(); };
      tx.onerror = () => { reject(tx.error); dbConn.close(); };
    });
  },

  async getAllFromIndexRange<S extends StoreName>(store: S, indexName: string, lower: unknown, upper: unknown): Promise<StoreItem<S>[]> {
    return withStore<StoreItem<S>[]>(store, 'readonly', (s) => {
      const idx = s.index(indexName);
      const range = IDBKeyRange.bound(lower, upper);
      return idx.getAll(range) as IDBRequest<StoreItem<S>[]>;
    });
  },
};
