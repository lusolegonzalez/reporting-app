export type EtlSource = 'empty' | 'mssql';

export type EtlRunRequest = {
  desde: string;
  hasta: string;
  origen?: string;
  source?: EtlSource;
};

export type EtlStepError = {
  source_pk: string | null;
  mensaje: string;
};

export type EtlStepResult = {
  tabla_destino: string;
  filas_leidas: number;
  filas_insertadas: number;
  filas_actualizadas: number;
  filas_descartadas: number;
  duracion_ms: number;
  errores: EtlStepError[];
};

export type EtlRunResponse = {
  ejecucion_id: number;
  estado: string;
  pasos: EtlStepResult[];
};
