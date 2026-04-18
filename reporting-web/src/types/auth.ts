export type AuthUser = {
  id: number;
  nombre: string;
  email: string;
  roles: string[];
};

export type LoginResponse = {
  access_token: string;
  user: AuthUser;
};

export type SessionState = {
  token: string | null;
  user: AuthUser | null;
};
