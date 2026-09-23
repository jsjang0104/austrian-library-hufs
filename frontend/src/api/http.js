import axios from 'axios';
import { clearAuth, getAuth, getSessionVersion, updateTokens } from './authStorage';

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

const AUTH_ENDPOINTS = ['/api/token/', '/api/token/refresh/', '/api/token/logout/'];
const isAuthRequest = (config) => AUTH_ENDPOINTS.includes(config?.url);

http.interceptors.request.use((config) => {
  // Defaults or retry headers must never outlive the session that created them.
  delete config.headers.Authorization;
  if (!isAuthRequest(config)) {
    if (config._sessionVersion !== undefined && config._sessionVersion !== getSessionVersion()) {
      throw new axios.CanceledError('Session changed');
    }
    config._sessionVersion = getSessionVersion();
    const { access } = getAuth();
    if (access) config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

let refreshInFlight = null;

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry || isAuthRequest(originalRequest)) {
      return Promise.reject(error);
    }

    const version = originalRequest._sessionVersion;
    if (version !== getSessionVersion()) return Promise.reject(error);
    const { refresh } = getAuth();
    if (!refresh) {
      clearAuth();
      window.location.href = '/#/login';
      return Promise.reject(error);
    }
    originalRequest._retry = true;

    if (!refreshInFlight || refreshInFlight.version !== version) {
      const pending = { version };
      pending.promise = (async () => {
        try {
          const { data } = await http.post('/api/token/refresh/', { refresh });
          if (!updateTokens(data, version)) {
            // A concurrent logout can race with token rotation. Revoke the newly
            // issued refresh token as well, without restoring local credentials.
            if (data.refresh) {
              await http.post('/api/token/logout/', { refresh: data.refresh }, { timeout: 10000 }).catch(() => {});
            }
            throw new axios.CanceledError('Session changed');
          }
        } catch (refreshError) {
          if (version === getSessionVersion()) {
            clearAuth();
            window.location.href = '/#/login';
          }
          throw refreshError;
        } finally {
          if (refreshInFlight === pending) refreshInFlight = null;
        }
      })();
      refreshInFlight = pending;
    }
    await refreshInFlight.promise;
    return http(originalRequest);
  }
);

export default http;
