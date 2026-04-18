import { useCallback } from 'react';
import { loginRequest, meRequest } from '@/api';
import type { AuthUser } from '@/types/auth';
import { storage } from '@/utils/storage';

export const useAuth = () => {
  const token = storage.getToken();

  const login = useCallback(async (email: string, password: string): Promise<AuthUser> => {
    const response = await loginRequest(email, password);
    storage.setToken(response.access_token);
    storage.setUser(response.user);
    return response.user;
  }, []);

  const logout = useCallback((): void => {
    storage.clearSession();
  }, []);

  const fetchCurrentUser = useCallback(async (): Promise<AuthUser> => {
    const user = await meRequest();
    storage.setUser(user);
    return user;
  }, []);

  return {
    isAuthenticated: Boolean(token),
    currentUser: storage.getUser(),
    login,
    logout,
    fetchCurrentUser,
  };
};
