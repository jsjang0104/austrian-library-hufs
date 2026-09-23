const AUTH_KEYS = ['accessToken', 'refreshToken', 'userName', 'userSid', 'userRole'];
export const AUTH_CHANGED = 'library-auth-changed';
let sessionVersion = 0;

// Previously stored tokens must not survive a browser restart after this upgrade.
export function removeLegacyAuth() {
  AUTH_KEYS.forEach((key) => localStorage.removeItem(key));
}

export function getAuth() {
  removeLegacyAuth();
  return {
    access: sessionStorage.getItem('accessToken'),
    refresh: sessionStorage.getItem('refreshToken'),
    name: sessionStorage.getItem('userName'),
    sid: sessionStorage.getItem('userSid'),
    role: sessionStorage.getItem('userRole'),
  };
}

export const getSessionVersion = () => sessionVersion;

export function saveAuth(data) {
  clearAuth();
  const values = [data.access, data.refresh, data.name, data.sid, data.role];
  AUTH_KEYS.forEach((key, index) => {
    if (values[index] != null) sessionStorage.setItem(key, values[index]);
  });
  window.dispatchEvent(new Event(AUTH_CHANGED));
}

export function updateTokens(data, expectedVersion) {
  if (sessionVersion !== expectedVersion || !getAuth().refresh) return false;
  sessionStorage.setItem('accessToken', data.access);
  if (data.refresh) sessionStorage.setItem('refreshToken', data.refresh);
  window.dispatchEvent(new Event(AUTH_CHANGED));
  return true;
}

export function clearAuth() {
  sessionVersion += 1;
  removeLegacyAuth();
  AUTH_KEYS.forEach((key) => sessionStorage.removeItem(key));
  window.dispatchEvent(new Event(AUTH_CHANGED));
}
