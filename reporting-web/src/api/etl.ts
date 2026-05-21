import { apiClient } from './client';
import type { EtlRunRequest, EtlRunResponse } from '@/types';

export const runEtlRequest = async (payload: EtlRunRequest): Promise<EtlRunResponse> => {
  const response = await apiClient.post<EtlRunResponse>('/etl/run', payload);
  return response.data;
};
