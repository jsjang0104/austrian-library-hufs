import api from './api/http';
import { clearAuth, getAuth, getSessionVersion, saveAuth } from './api/authStorage';

export const registerUser = async (userData) => {
  const response = await api.post('/api/members/', userData);
  return response.data;
};

export const loginUser = async (sid, password) => {
  const version = getSessionVersion();
  const response = await api.post('/api/token/', {
    username: String(sid),
    password: String(password),
  });
  // A logout or another login while this request was pending takes precedence.
  if (version !== getSessionVersion()) throw new Error('Session changed');
  saveAuth(response.data);
  return response.data;
};

export const logoutUser = async () => {
  const { refresh } = getAuth();
  clearAuth();
  if (refresh) {
    try {
      await api.post('/api/token/logout/', { refresh }, { timeout: 10000 });
    } catch {
      // Local logout is immediate even when server-side revocation is offline.
    }
  }
};

export default api;
