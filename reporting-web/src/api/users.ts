import { apiClient } from './client';
import type { RoleItem, UserItem } from '@/types';

export const listUsersRequest = async (): Promise<UserItem[]> => {
  const response = await apiClient.get<{ items: UserItem[] }>('/users');
  return response.data.items;
};

export const createUserRequest = async (payload: {
  nombre: string;
  email: string;
  password: string;
  activo: boolean;
}): Promise<UserItem> => {
  const response = await apiClient.post<UserItem>('/users', payload);
  return response.data;
};

export const updateUserRequest = async (userId: number, payload: Partial<{ nombre: string; email: string; password: string; activo: boolean }>): Promise<UserItem> => {
  const response = await apiClient.put<UserItem>(`/users/${userId}`, payload);
  return response.data;
};

export const assignUserRolesRequest = async (userId: number, roleIds: number[]): Promise<UserItem> => {
  const response = await apiClient.put<UserItem>(`/users/${userId}/roles`, { role_ids: roleIds });
  return response.data;
};

export const getUserRolesRequest = async (userId: number): Promise<RoleItem[]> => {
  const response = await apiClient.get<{ user_id: number; roles: RoleItem[] }>(`/users/${userId}/roles`);
  return response.data.roles;
};
