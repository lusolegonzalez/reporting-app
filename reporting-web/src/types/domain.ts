export type UserItem = {
  id: number;
  nombre: string;
  email: string;
  activo: boolean;
  roles: string[];
};

export type RoleItem = {
  id: number;
  nombre: string;
  descripcion: string | null;
};

export type ReportItem = {
  id: number;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
};

export type ReportVisibility = {
  role_id: number;
  rol: string;
  puede_ver: boolean;
};
