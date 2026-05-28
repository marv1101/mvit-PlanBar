import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { clearTokens } from './auth';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

let isRefreshing = false;
let pendingRequests: Array<() => void> = [];

function onRefreshed(): void {
  pendingRequests.forEach(cb => cb());
  pendingRequests = [];
}

api.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise(resolve => {
        pendingRequests.push(() => {
          resolve(api(originalRequest));
        });
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      await axios.post('/api/v1/users/refresh-token', {}, { withCredentials: true });
      onRefreshed();
      return api(originalRequest);
    } catch {
      clearTokens();
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      return Promise.reject(error);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;
