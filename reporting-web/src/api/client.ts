import axios, { type InternalAxiosRequestConfig } from 'axios';
import { storage } from '@/utils/storage';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = storage.getToken();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Si el backend rechaza por token vencido/invalido, limpiamos sesion y mandamos
// al login. No tocamos los 403 (permiso insuficiente): esos los maneja la UI
// para mostrar el mensaje del backend.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const path = window.location.pathname;
      if (!path.startsWith('/login')) {
        storage.clearSession();
        window.location.assign('/login');
      }
    }
    return Promise.reject(error);
  },
);
