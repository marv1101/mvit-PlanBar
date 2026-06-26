class MockIDBRequest<T = unknown> {
  result: T = undefined as T;
  error: DOMException | null = null;
  source: unknown = null;
  transaction: IDBTransaction | null = null;
  readyState: 'pending' | 'done' = 'pending';
  onsuccess: ((this: IDBRequest<T>, ev: Event) => void) | null = null;
  onerror: ((this: IDBRequest<T>, ev: Event) => void) | null = null;
  onupgradeneeded: ((this: IDBRequest<T>, ev: IDBVersionChangeEvent) => void) | null = null;

  private _listeners: Record<string, Array<(ev: Event) => void>> = {};

  addEventListener(type: string, listener: (ev: Event) => void): void {
    if (!this._listeners[type]) this._listeners[type] = [];
    this._listeners[type].push(listener);
  }

  removeEventListener(type: string, listener: (ev: Event) => void): void {
    const arr = this._listeners[type];
    if (arr) {
      const idx = arr.indexOf(listener);
      if (idx !== -1) arr.splice(idx, 1);
    }
  }

  dispatchEvent(event: Event): boolean {
    const handlers = this._listeners[event.type] || [];
    for (const h of handlers) h.call(this, event);

    if (event.type === 'upgradeneeded' && this.onupgradeneeded) {
      this.onupgradeneeded.call(this, event as IDBVersionChangeEvent);
    }
    if (event.type === 'success' && this.onsuccess) this.onsuccess.call(this, event);
    if (event.type === 'error' && this.onerror) this.onerror.call(this, event);
    return true;
  }

  _resolve(result: T): void {
    this.result = result;
    this.readyState = 'done';
    setTimeout(() => this.dispatchEvent(new Event('success')), 0);
  }

  _reject(error: DOMException): void {
    this.error = error;
    this.readyState = 'done';
    setTimeout(() => this.dispatchEvent(new Event('error')), 0);
  }

  _fireUpgrade(dbResult: T): void {
    this.result = dbResult;
    this.readyState = 'done';
    setTimeout(() => {
      this.dispatchEvent(new Event('upgradeneeded'));
      this.dispatchEvent(new Event('success'));
    }, 0);
  }
}

interface MockObjectStore {
  name: string;
  keyPath: string | null;
  data: Map<string | number, unknown>;
  indexes: Map<string, { name: string; keyPath: string; unique: boolean; data: Map<string | number, unknown[]> }>;
}

class MockIDBObjectStore {
  private store: MockObjectStore;
  private _transaction: MockIDBTransaction;
  private _autoIncrement = 0;

  constructor(store: MockObjectStore, transaction: MockIDBTransaction) {
    this.store = store;
    this._transaction = transaction;
  }

  get name(): string { return this.store.name; }
  get keyPath(): string | null { return this.store.keyPath; }
  get transaction(): IDBTransaction { return this._transaction as unknown as IDBTransaction; }
  get autoIncrement(): boolean { return false; }

  put(value: unknown): IDBRequest {
    const req = new MockIDBRequest();
    const key = (value as Record<string, unknown>)[this.store.keyPath as string];
    if (key !== undefined && key !== null) {
      this.store.data.set(String(key), value);
    } else {
      const id = ++this._autoIncrement;
      this.store.data.set(String(id), value);
    }
    req._resolve(undefined as never);
    return req as unknown as IDBRequest;
  }

  get(key: string | number): IDBRequest {
    const req = new MockIDBRequest();
    const value = this.store.data.get(String(key));
    req._resolve(value as never);
    return req as unknown as IDBRequest;
  }

  getAll(query?: IDBValidKey | IDBKeyRange | null, count?: number): IDBRequest {
    const req = new MockIDBRequest();
    const values = Array.from(this.store.data.values());
    req._resolve(values.slice(0, count ?? values.length) as never);
    return req as unknown as IDBRequest;
  }

  delete(key: string | number): IDBRequest {
    const req = new MockIDBRequest();
    this.store.data.delete(String(key));
    req._resolve(undefined as never);
    return req as unknown as IDBRequest;
  }

  clear(): IDBRequest {
    const req = new MockIDBRequest();
    this.store.data.clear();
    req._resolve(undefined as never);
    return req as unknown as IDBRequest;
  }

  index(name: string): IDBIndex {
    const idx = this.store.indexes.get(name);
    if (!idx) throw new Error(`Index not found: ${name}`);
    return {
      name: idx.name,
      keyPath: idx.keyPath,
      unique: idx.unique,
      multiEntry: false,
      objectStore: this as unknown as IDBObjectStore,
      getAll: (query?: IDBValidKey | IDBKeyRange | null, count?: number) => {
        const req = new MockIDBRequest();
        if (query !== null && query !== undefined && typeof query !== 'object') {
          const results = idx.data.get(String(query)) || [];
          req._resolve(results.slice(0, count ?? results.length) as never);
        } else {
          const all = Array.from(idx.data.values()).flat();
          req._resolve(all.slice(0, count ?? all.length) as never);
        }
        return req as unknown as IDBRequest;
      },
      get: (key: IDBValidKey | IDBKeyRange) => {
        const req = new MockIDBRequest();
        const results = idx.data.get(String(key)) || [];
        req._resolve((results[0]) as never);
        return req as unknown as IDBRequest;
      },
      getAllKeys: () => { const r = new MockIDBRequest(); r._resolve([] as never); return r as unknown as IDBRequest; },
      getKey: () => { const r = new MockIDBRequest(); r._resolve(undefined as never); return r as unknown as IDBRequest; },
      count: () => { const r = new MockIDBRequest(); r._resolve(0 as never); return r as unknown as IDBRequest; },
      openCursor: () => { const r = new MockIDBRequest(); r._resolve(null as never); return r as unknown as IDBRequest; },
      openKeyCursor: () => { const r = new MockIDBRequest(); r._resolve(null as never); return r as unknown as IDBRequest; },
    } as unknown as IDBIndex;
  }

  createIndex(name: string, keyPath: string | string[], _options?: IDBIndexParameters): IDBIndex {
    if (!this.store.indexes.has(name)) {
      this.store.indexes.set(name, { name, keyPath: Array.isArray(keyPath) ? keyPath[0] : keyPath, unique: false, data: new Map() });
    }
    return { name, keyPath, unique: false, multiEntry: false, objectStore: this as unknown as IDBObjectStore } as unknown as IDBIndex;
  }

  count(): IDBRequest {
    const r = new MockIDBRequest();
    r._resolve(this.store.data.size as never);
    return r as unknown as IDBRequest;
  }
}

class MockIDBTransaction {
  private _db: MockIDBDatabase;
  private _store: string;
  private _mode: IDBTransactionMode;
  oncomplete: ((this: IDBTransaction, ev: Event) => void) | null = null;
  onerror: ((this: IDBTransaction, ev: Event) => void) | null = null;
  onabort: ((this: IDBTransaction, ev: Event) => void) | null = null;
  error: DOMException | null = null;

  constructor(db: MockIDBDatabase, store: string, mode: IDBTransactionMode) {
    this._db = db;
    this._store = store;
    this._mode = mode;
  }

  get mode(): IDBTransactionMode { return this._mode; }
  get objectStoreNames(): DOMStringList { return [this._store] as unknown as DOMStringList; }
  get db(): IDBDatabase { return this._db as unknown as IDBDatabase; }

  objectStore(name: string): IDBObjectStore {
    const store = this._db._stores.get(name);
    if (!store) throw new Error(`Store not found: ${name}`);
    return new MockIDBObjectStore(store, this) as unknown as IDBObjectStore;
  }

  commit(): void {
    setTimeout(() => {
      if (this.oncomplete) this.oncomplete.call(this, new Event('complete'));
    }, 0);
  }

  abort(): void {
    setTimeout(() => {
      if (this.onabort) this.onabort.call(this, new Event('abort'));
    }, 0);
  }
}

class MockIDBDatabase {
  name: string;
  version: number;
  onclose: ((this: IDBDatabase, ev: Event) => void) | null = null;
  onerror: ((this: IDBDatabase, ev: Event) => void) | null = null;
  onversionchange: ((this: IDBDatabase, ev: Event) => void) | null = null;
  _stores: Map<string, MockObjectStore>;
  private _closed = false;

  constructor(name: string, version: number) {
    this.name = name;
    this.version = version;
    this._stores = new Map();
  }

  get objectStoreNames(): DOMStringList {
    return Array.from(this._stores.keys()) as unknown as DOMStringList;
  }

  createObjectStore(name: string, options?: IDBObjectStoreParameters): IDBObjectStore {
    const store: MockObjectStore = {
      name,
      keyPath: options?.keyPath as string || null,
      data: new Map(),
      indexes: new Map(),
    };
    this._stores.set(name, store);
    const tx = new MockIDBTransaction(this, name, 'versionchange');
    return new MockIDBObjectStore(store, tx) as unknown as IDBObjectStore;
  }

  deleteObjectStore(name: string): void {
    this._stores.delete(name);
  }

  transaction(storeNames: string | string[], mode?: IDBTransactionMode): IDBTransaction {
    const name = Array.isArray(storeNames) ? storeNames[0] : storeNames;
    const tx = new MockIDBTransaction(this, name, mode || 'readonly');
    setTimeout(() => {
      if (tx.oncomplete) tx.oncomplete.call(tx, new Event('complete'));
    }, 0);
    return tx as unknown as IDBTransaction;
  }

  close(): void {
    this._closed = true;
  }
}

// In-memory database registry
const databases = new Map<string, MockIDBDatabase>();

function mockOpenDB(name: string, version: number): IDBRequest<IDBDatabase> {
  const existing = databases.get(name);
  const db = existing || new MockIDBDatabase(name, version);
  if (!existing) {
    databases.set(name, db);
  }

  const req = new MockIDBRequest<IDBDatabase>();

  if (!existing) {
    req._fireUpgrade(db as unknown as IDBDatabase);
  } else {
    req._resolve(db as unknown as IDBDatabase);
  }

  return req as unknown as IDBRequest<IDBDatabase>;
}

function mockDeleteDatabase(name: string): IDBRequest<undefined> {
  databases.delete(name);
  const req = new MockIDBRequest<undefined>();
  req._resolve(undefined as never);
  return req as unknown as IDBRequest<undefined>;
}

export function setupIndexedDBMock(): void {
  (globalThis as Record<string, unknown>).indexedDB = {
    open: mockOpenDB,
    deleteDatabase: mockDeleteDatabase,
    databases: databases,
    cmp: (_a: unknown, _b: unknown) => 0,
  } as unknown as IDBFactory;
}

export function teardownIndexedDBMock(): void {
  databases.clear();
  delete (globalThis as Record<string, unknown>).indexedDB;
}
