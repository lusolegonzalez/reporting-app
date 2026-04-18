import { apiClient } from './client';
import type { ReportItem, ReportVisibility } from '@/types';

export const listReportsRequest = async (): Promise<ReportItem[]> => {
  const response = await apiClient.get<{ items: ReportItem[] }>('/reports');
  return response.data.items;
};

export const listVisibleReportsRequest = async (): Promise<ReportItem[]> => {
  const response = await apiClient.get<{ items: ReportItem[] }>('/reports/visible/me');
  return response.data.items;
};

export const createReportRequest = async (payload: {
  codigo: string;
  nombre: string;
  descripcion?: string;
  activo: boolean;
}): Promise<ReportItem> => {
  const response = await apiClient.post<ReportItem>('/reports', payload);
  return response.data;
};

export const updateReportRequest = async (
  reportId: number,
  payload: Partial<{ codigo: string; nombre: string; descripcion: string; activo: boolean }>,
): Promise<ReportItem> => {
  const response = await apiClient.put<ReportItem>(`/reports/${reportId}`, payload);
  return response.data;
};

export const getReportVisibilityRequest = async (reportId: number): Promise<ReportVisibility[]> => {
  const response = await apiClient.get<{ report_id: number; visibility: ReportVisibility[] }>(`/reports/${reportId}/visibility`);
  return response.data.visibility;
};

export const updateReportVisibilityRequest = async (
  reportId: number,
  visibility: Array<{ role_id: number; puede_ver: boolean }>,
): Promise<void> => {
  await apiClient.put(`/reports/${reportId}/visibility`, { visibility });
};
