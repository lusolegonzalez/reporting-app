import { apiClient } from './client';
import type { ReportItem, ReportMetadata, ReportResponse, ReportVisibility } from '@/types';

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
  visibility: Array<{ role_id: number; puede_ver: boolean; puede_exportar: boolean }>,
): Promise<void> => {
  await apiClient.put(`/reports/${reportId}/visibility`, { visibility });
};

export const getReportMetadataRequest = async (codigo: string): Promise<ReportMetadata> => {
  const response = await apiClient.get<ReportMetadata>(
    `/reports/by-codigo/${encodeURIComponent(codigo)}/metadata`,
  );
  return response.data;
};

export const runReportRequest = async (
  codigo: string,
  payload: { parametros: Record<string, unknown>; formato?: 'json' | 'excel' | 'pdf' },
): Promise<ReportResponse> => {
  const response = await apiClient.post<ReportResponse>(
    `/reports/by-codigo/${encodeURIComponent(codigo)}/run`,
    { parametros: payload.parametros, formato: payload.formato ?? 'json' },
  );
  return response.data;
};
