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
  puede_exportar: boolean;
};

export type ReportParameterDef = {
  nombre: string;
  tipo: 'date' | 'bool' | 'string' | 'int';
  requerido: boolean;
  descripcion: string | null;
  valor_por_defecto: unknown;
  etiqueta?: string | null;
};

export type ReportMetadata = {
  codigo: string;
  nombre: string;
  descripcion: string;
  parametros: ReportParameterDef[];
  permisos: {
    puede_ver: boolean;
    puede_exportar: boolean;
  };
  formatos_disponibles: {
    json: boolean;
    excel: boolean;
    pdf: boolean;
  };
};

export type ReportAlerta = {
  nivel: 'info' | 'warning' | 'error';
  codigo: string;
  mensaje: string;
};

export type ReportSection = {
  codigo: string;
  titulo: string;
  columnas: Array<{ key: string; titulo: string; tipo: string }>;
  filas: Array<Record<string, unknown>>;
  totales: Record<string, unknown>;
};

export type ReportResponse = {
  codigo_reporte: string;
  nombre_reporte: string;
  parametros: Record<string, unknown>;
  secciones: ReportSection[];
  alertas: ReportAlerta[];
  export_permitido: { excel: boolean; pdf: boolean };
  generado_en: string;
  es_placeholder: boolean;
};
