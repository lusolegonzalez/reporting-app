import { apiClient } from './client';
import type { ReportItem, ReportMetadata, ReportResponse, ReportVisibility } from '@/types';

export type ReportPreparingPayload = {
  status: 'preparing_data' | 'etl_dispatch_error';
  ejecucion_id?: number;
  estado?: string;
  origen?: string;
  rango_faltante?: { desde: string; hasta: string };
  huecos?: Array<{ desde: string; hasta: string }>;
  reusada?: boolean;
  message?: string;
};

export type RunReportResult =
  | { kind: 'ready'; data: ReportResponse }
  | { kind: 'preparing'; data: ReportPreparingPayload };

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
): Promise<RunReportResult> => {
  const response = await apiClient.post<ReportResponse | ReportPreparingPayload>(
    `/reports/by-codigo/${encodeURIComponent(codigo)}/run`,
    { parametros: payload.parametros, formato: payload.formato ?? 'json' },
    { validateStatus: (status) => status === 200 || status === 202 },
  );
  if (response.status === 202) {
    return { kind: 'preparing', data: response.data as ReportPreparingPayload };
  }
  return { kind: 'ready', data: response.data as ReportResponse };
};

/**
 * Solicita la exportación del reporte en formato binario (Excel o PDF)
 * y dispara la descarga en el navegador automáticamente.
 */
export const exportReportRequest = async (
  codigo: string,
  payload: { parametros: Record<string, unknown>; formato: 'excel' | 'pdf' },
): Promise<void> => {
  const response = await apiClient.post(
    `/reports/by-codigo/${encodeURIComponent(codigo)}/run`,
    { parametros: payload.parametros, formato: payload.formato },
    { responseType: 'blob' },
  );

  // Extraer nombre de archivo del header Content-Disposition si está presente
  const disposition = response.headers['content-disposition'] as string | undefined;
  const ext = payload.formato === 'excel' ? 'xlsx' : 'pdf';
  let filename = `reporte.${ext}`;
  if (disposition) {
    const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
    if (match?.[1]) {
      filename = match[1].replace(/['"]/g, '').trim();
    }
  }

  // Crear enlace temporal y disparar descarga
  const url = URL.createObjectURL(response.data as Blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};
