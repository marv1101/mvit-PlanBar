import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { clearTokens } from './auth';

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
