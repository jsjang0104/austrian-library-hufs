import React, { createContext, useContext, useState, useEffect } from 'react';
import { AUTH_CHANGED, getAuth } from './api/authStorage';
import { logoutUser } from './api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(getAuth);

  useEffect(() => {
    const update = () => setAuth(getAuth());
    window.addEventListener(AUTH_CHANGED, update);
    return () => window.removeEventListener(AUTH_CHANGED, update);
  }, []);

  const value = {
    isLoggedIn: Boolean(auth.access && auth.name && auth.sid),
    user: auth.access ? { name: auth.name, sid: auth.sid } : null,
    logout: logoutUser,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
