import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { clearTokens } from './auth';
import { syncManager } from './syncManager';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
  timeout: 15000,
});

// --- CSRF double-submit cookie helper ----------------------------------------

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

const CSRF_METHODS = new Set(['post', 'put', 'patch', 'delete']);

api.interceptors.request.use((config) => {
  const method = (config.method || '').toLowerCase();
  if (CSRF_METHODS.has(method)) {
    const token = getCsrfToken();
    if (token) {
      config.headers.set('X-CSRF-Token', token);
    }
  }
  return config;
});

// --- Existing interceptors -------------------------------------------------

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null): void {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  failedQueue = [];
}

api.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
      _retryCount?: number;
    };

    // Queue mutating requests for offline sync if we're offline
    if (!error.response && error.code === 'ERR_NETWORK') {
      const method = (originalRequest.method || '').toLowerCase();
      if (['post', 'put', 'patch', 'delete'].includes(method)) {
        const mutateMethods = new Set(['post', 'put', 'patch', 'delete']);
        if (mutateMethods.has(method)) {
          syncManager.enqueue(
            originalRequest.url || '',
            method,
            originalRequest.data,
            undefined
          ).catch(() => {});
          return Promise.reject(error);
        }
      }
    }

    // Retry on network error or timeout (up to 3 times)
    if (!error.response) {
      const retryCount = originalRequest._retryCount || 0;
      if (retryCount < 3) {
        originalRequest._retryCount = retryCount + 1;
        await new Promise(r => setTimeout(r, 1000 * (retryCount + 1)));
        return api(originalRequest);
      }
    }

    // Token refresh on 401
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(() => api(originalRequest));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      await axios.post('/api/v1/users/refresh-token', {}, { withCredentials: true });
      processQueue(null);
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError);
      clearTokens();
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;

// --- ETag Store for optimistic concurrency control ---------------------------

const etagStore = new Map<string, string>();

export function getStoredEtag(url: string): string | undefined {
  return etagStore.get(url);
}

export function setStoredEtag(url: string, etag: string): void {
  etagStore.set(url, etag);
}

export function clearStoredEtag(url: string): void {
  etagStore.delete(url);
}

// --- ETag interceptors -------------------------------------------------------

const MUTATING_METHODS = new Set(['put', 'patch', 'delete']);
const SINGLE_RESOURCE_RE = /\/\d+$/;

api.interceptors.request.use((config) => {
  const method = (config.method || '').toLowerCase();
  if (MUTATING_METHODS.has(method) && SINGLE_RESOURCE_RE.test(config.url || '')) {
    const etag = etagStore.get(config.url || '');
    if (etag) {
      config.headers.set('If-Match', etag);
    }
  }
  return config;
});

api.interceptors.response.use((response) => {
  const etag = response.headers['etag'];
  if (etag) {
    etagStore.set(response.config.url || '', etag);
  }
  return response;
});
