import React, { createContext, useContext, useState, useEffect } from 'react';
import api from './api/http';


const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const accessToken = localStorage.getItem('accessToken');
    const userName = localStorage.getItem('userName');
    const userEmail = localStorage.getItem('userEmail');

    if (accessToken && userName && userEmail) {
      setIsLoggedIn(true);
      setUser({ name: userName, email: userEmail });
      api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
    }
  }, []);


  const login = (data) => {
    localStorage.setItem('accessToken', data.access);
    localStorage.setItem('refreshToken', data.refresh);
    localStorage.setItem('userName', data.name);
    localStorage.setItem('userEmail', data.email);

    api.defaults.headers.common['Authorization'] = `Bearer ${data.access}`;

    setIsLoggedIn(true);
    setUser({ name: data.name, email: data.email });
  };

  const logout = () => {
    localStorage.clear(); 
    delete api.defaults.headers.common['Authorization']; 
    setIsLoggedIn(false);
    setUser(null);
  };

  const value = {
    isLoggedIn,
    user,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  return useContext(AuthContext);
};