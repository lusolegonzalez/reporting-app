import { apiClient } from '@/api/client';
import type { AuthUser, LoginResponse } from '@/types/auth';

export const loginRequest = async (email: string, password: string): Promise<LoginResponse> => {
  const response = await apiClient.post<LoginResponse>('/auth/login', { email, password });
  return response.data;
};

export const meRequest = async (): Promise<AuthUser> => {
  const response = await apiClient.get<AuthUser>('/auth/me');
  return response.data;
};
