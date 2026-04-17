import { useMemo } from 'react';
import { storage } from '@/utils/storage';

export const useAuth = () => {
  const token = storage.getToken();

  return useMemo(
    () => ({
      isAuthenticated: Boolean(token),
      login: () => storage.setToken('demo-token'),
      logout: () => storage.clearToken(),
    }),
    [token],
  );
};
