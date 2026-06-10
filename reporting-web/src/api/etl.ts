import { apiClient } from './client';
import type { EtlRunRequest, EtlRunResponse, EtlEjecucionEstado, EtlEjecucionDetalle } from '@/types';

export const runEtlRequest = async (payload: EtlRunRequest): Promise<EtlRunResponse> => {
  const response = await apiClient.post<EtlRunResponse>('/etl/run', payload);
  return response.data;
};

export const getEtlEjecucionEstadoRequest = async (
  ejecucionId: number,
): Promise<EtlEjecucionEstado> => {
  const response = await apiClient.get<EtlEjecucionEstado>(
    `/etl/ejecuciones/${ejecucionId}/estado`,
  );
  return response.data;
};

export const getEtlEjecucionRequest = async (
  ejecucionId: number,
): Promise<EtlEjecucionDetalle> => {
  const response = await apiClient.get<EtlEjecucionDetalle>(`/etl/ejecuciones/${ejecucionId}`);
  return response.data;
};
