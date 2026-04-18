import { apiClient } from './client';
import type { RoleItem } from '@/types';

export const listRolesRequest = async (): Promise<RoleItem[]> => {
  const response = await apiClient.get<{ items: RoleItem[] }>('/roles');
  return response.data.items;
};

export const createRoleRequest = async (payload: { nombre: string; descripcion?: string }): Promise<RoleItem> => {
  const response = await apiClient.post<RoleItem>('/roles', payload);
  return response.data;
};

export const updateRoleRequest = async (roleId: number, payload: { nombre?: string; descripcion?: string }): Promise<RoleItem> => {
  const response = await apiClient.put<RoleItem>(`/roles/${roleId}`, payload);
  return response.data;
};
