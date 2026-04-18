import type { AuthUser } from '@/types/auth';

const TOKEN_KEY = 'reporting_token';
const USER_KEY = 'reporting_user';

export const storage = {
  getToken: (): string | null => localStorage.getItem(TOKEN_KEY),
  setToken: (token: string): void => localStorage.setItem(TOKEN_KEY, token),
  clearToken: (): void => localStorage.removeItem(TOKEN_KEY),
  getUser: (): AuthUser | null => {
    const rawUser = localStorage.getItem(USER_KEY);

    if (!rawUser) {
      return null;
    }

    try {
      return JSON.parse(rawUser) as AuthUser;
    } catch {
      localStorage.removeItem(USER_KEY);
      return null;
    }
  },
  setUser: (user: AuthUser): void => localStorage.setItem(USER_KEY, JSON.stringify(user)),
  clearUser: (): void => localStorage.removeItem(USER_KEY),
  clearSession: (): void => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};
