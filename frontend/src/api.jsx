import api from './api/http'; 

export const registerUser = async (userData) => {
  const response = await api.post('/api/members/', userData);
  return response.data;
};

export const loginUser = async (email, password) => {
  try {
    const response = await api.post('/api/token/', {
      email: String(email),
      password: String(password),
    });

    const { access, refresh, name, email: userEmail, role } = response.data;

    localStorage.setItem('accessToken', access);
    localStorage.setItem('refreshToken', refresh);
    localStorage.setItem('userName', name);
    localStorage.setItem('userEmail', userEmail);
    localStorage.setItem('userRole', role);

    api.defaults.headers.common['Authorization'] = `Bearer ${access}`;
    return response.data;

  } catch (error) {
    localStorage.clear();
    delete api.defaults.headers.common['Authorization'];
    throw error;
  }
};

export const logoutUser = () => {
  localStorage.clear();
  delete api.defaults.headers.common['Authorization'];
};

export default api;