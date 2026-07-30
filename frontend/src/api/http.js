import axios from 'axios';

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// 로그인/토큰 갱신 요청 자체의 401 은 "세션 만료"가 아니라 "자격 증명 오류"다.
// 이 요청까지 아래 재발급·리다이렉트 로직을 태우면, 비밀번호를 틀렸을 뿐인데
// 로그인 페이지로 강제 이동해버린다.
const AUTH_ENDPOINTS = ['/api/token/', '/api/token/refresh/'];
const isAuthRequest = (config) =>
  AUTH_ENDPOINTS.some((path) => config?.url?.includes(path));

// HashRouter 를 쓰므로 라우트는 /#/login 이다. '/login' 으로 보내면 호스팅에
// 해당 경로의 파일이 없어 404 가 뜬다.
const redirectToLogin = () => {
  localStorage.clear();
  window.location.href = '/#/login';
};

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !isAuthRequest(originalRequest)
    ) {
      const refreshToken = localStorage.getItem('refreshToken');

      if (!refreshToken) {
        redirectToLogin();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers['Authorization'] = `Bearer ${token}`;
          return http(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post(
          `${http.defaults.baseURL}/api/token/refresh/`,
          { refresh: refreshToken }
        );
        localStorage.setItem('accessToken', data.access);
        http.defaults.headers.common['Authorization'] = `Bearer ${data.access}`;
        processQueue(null, data.access);
        originalRequest.headers['Authorization'] = `Bearer ${data.access}`;
        return http(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        redirectToLogin();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default http;