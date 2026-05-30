import { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';

import {
  getReportMetadataRequest,
  runReportRequest,
  exportReportRequest,
  getEtlEjecucionEstadoRequest,
} from '@/api';
import type {
  ReportAlerta,
  ReportMetadata,
  ReportParameterDef,
  ReportResponse,
  ReportSection,
} from '@/types';
import type { ReportPreparingPayload } from '@/api/reports';
import { formatDateDisplay } from '@/utils/date';

type FormatoExport = 'excel' | 'pdf';

type ReportRunnerProps = {
  codigo: string;
};

const formatValue = (value: unknown): string => {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') return value.toLocaleString('es-AR');
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  return String(value);
};

const initialValueFor = (parametro: ReportParameterDef): string | boolean => {
  if (parametro.valor_por_defecto !== null && parametro.valor_por_defecto !== undefined) {
    if (parametro.tipo === 'bool') return Boolean(parametro.valor_por_defecto);
    return String(parametro.valor_por_defecto);
  }
  if (parametro.tipo === 'bool') return false;
  return '';
};

const buildPayload = (
  parametros: ReportParameterDef[],
  values: Record<string, string | boolean>,
): Record<string, unknown> => {
  const payload: Record<string, unknown> = {};
  parametros.forEach((p) => {
    const raw = values[p.nombre];
    if (p.tipo === 'bool') {
      payload[p.nombre] = Boolean(raw);
      return;
    }
    if (raw === '' || raw === undefined || raw === null) {
      if (!p.requerido) return;
      payload[p.nombre] = null;
      return;
    }
    if (p.tipo === 'int') {
      payload[p.nombre] = Number(raw);
    } else {
      payload[p.nombre] = raw;
    }
  });
  return payload;
};

const formatNumber = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '-';
  const num = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(num)) return formatValue(value);
  return num.toLocaleString('es-AR', { maximumFractionDigits: 3 });
};

type Tropa = { numero_tropa?: unknown; cabezas?: unknown };

const extractTropas = (totales: Record<string, unknown>): Tropa[] => {
  const raw = totales['tropas'];
  if (!Array.isArray(raw)) return [];
  return raw.filter((t): t is Tropa => typeof t === 'object' && t !== null);
};

const KPI_KEYS: Array<{ key: string; titulo: string }> = [
  { key: 'cabezas_faenadas', titulo: 'Cabezas faenadas' },
  { key: 'cajas', titulo: 'Cajas' },
  { key: 'kg_neto', titulo: 'Kg. Neto' },
];

const SectionTotales = ({ totales }: { totales: Record<string, unknown> }) => {
  const items = KPI_KEYS.filter((k) => totales[k.key] !== undefined && totales[k.key] !== null);
  if (items.length === 0) return null;
  return (
    <ul className="kpi-list report-section-kpis">
      {items.map((k) => (
        <li key={k.key}>
          <strong>{k.titulo}:</strong> {formatNumber(totales[k.key])}
        </li>
      ))}
    </ul>
  );
};

const SectionTropas = ({ tropas }: { tropas: Tropa[] }) => {
  if (tropas.length === 0) return null;
  return (
    <div className="report-section-tropas">
      <h5>Tropas del día</h5>
      <table className="data-table data-table-compact">
        <thead>
          <tr>
            <th>Número de tropa</th>
            <th>Cabezas</th>
          </tr>
        </thead>
        <tbody>
          {tropas.map((t, idx) => (
            <tr key={idx}>
              <td>{formatValue(t.numero_tropa)}</td>
              <td>{formatNumber(t.cabezas)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const AlertaItem = ({ alerta }: { alerta: ReportAlerta }) => (
  <li className={`report-alerta report-alerta-${alerta.nivel}`}>
    <span className="report-alerta-nivel">{alerta.nivel.toUpperCase()}</span>
    <strong>{alerta.codigo}:</strong> {alerta.mensaje}
  </li>
);

const SectionTable = ({ section }: { section: ReportSection }) => {
  const tieneFilas = section.filas.length > 0;
  const tropas = extractTropas(section.totales ?? {});
  const tieneTotales =
    section.totales &&
    KPI_KEYS.some((k) => section.totales[k.key] !== undefined && section.totales[k.key] !== null);

  return (
    <div className="card report-section-card">
      <div className="report-section-header">
        <h4>{section.titulo}</h4>
        {!tieneFilas && <span className="section-note">Sin datos para los parámetros indicados.</span>}
      </div>

      {tieneTotales && <SectionTotales totales={section.totales} />}

      {tieneFilas && (
        <div className="report-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                {section.columnas.map((col) => (
                  <th key={col.key}>{col.titulo}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {section.filas.map((fila, idx) => (
                <tr key={idx}>
                  {section.columnas.map((col) => (
                    <td key={col.key}>
                      {col.tipo === 'number'
                        ? formatNumber(fila[col.key])
                        : col.tipo === 'date'
                          ? formatDateDisplay(fila[col.key])
                          : formatValue(fila[col.key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <SectionTropas tropas={tropas} />
    </div>
  );
};

export const ReportRunner = ({ codigo }: ReportRunnerProps) => {
  const [metadata, setMetadata] = useState<ReportMetadata | null>(null);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState(true);

  const [values, setValues] = useState<Record<string, string | boolean>>({});

  const [result, setResult] = useState<ReportResponse | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const [exportNotice, setExportNotice] = useState<string | null>(null);
  const [exportingFormato, setExportingFormato] = useState<FormatoExport | null>(null);

  const [etlPreparing, setEtlPreparing] = useState<ReportPreparingPayload | null>(null);
  const [etlElapsedSec, setEtlElapsedSec] = useState(0);
  const pollTimerRef = useRef<number | null>(null);
  const pollAbortRef = useRef<boolean>(false);

  const clearPolling = () => {
    pollAbortRef.current = true;
    if (pollTimerRef.current !== null) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  useEffect(() => () => clearPolling(), []);

  useEffect(() => {
    const run = async () => {
      try {
        setIsLoadingMetadata(true);
        setMetadataError(null);
        const data = await getReportMetadataRequest(codigo);
        setMetadata(data);
        const initial: Record<string, string | boolean> = {};
        data.parametros.forEach((p) => {
          initial[p.nombre] = initialValueFor(p);
        });
        setValues(initial);
      } catch (err) {
        if (axios.isAxiosError(err)) {
          setMetadataError(err.response?.data?.message ?? 'No se pudo cargar la configuración del reporte.');
        } else {
          setMetadataError('No se pudo cargar la configuración del reporte.');
        }
      } finally {
        setIsLoadingMetadata(false);
      }
    };
    void run();
  }, [codigo]);

  const puedeExportar = useMemo(() => Boolean(metadata?.permisos?.puede_exportar), [metadata]);
  const formatos = metadata?.formatos_disponibles ?? { json: true, excel: false, pdf: false };
  const dateParamNames = useMemo(
    () => new Set((metadata?.parametros ?? []).filter((p) => p.tipo === 'date').map((p) => p.nombre)),
    [metadata],
  );

  const updateValue = (nombre: string, value: string | boolean) => {
    setValues((current) => ({ ...current, [nombre]: value }));
  };

  const handleRun = async () => {
    if (!metadata) return;
    clearPolling();
    pollAbortRef.current = false;
    setIsRunning(true);
    setRunError(null);
    setExportNotice(null);
    setEtlPreparing(null);
    setEtlElapsedSec(0);
    try {
      const payload = buildPayload(metadata.parametros, values);
      const response = await runReportRequest(codigo, { parametros: payload, formato: 'json' });
      if (response.kind === 'ready') {
        setResult(response.data);
      } else {
        setResult(null);
        setEtlPreparing(response.data);
        if (response.data.status === 'preparing_data' && response.data.ejecucion_id) {
          void startEtlPolling(response.data.ejecucion_id, payload);
        }
      }
    } catch (err) {
      setResult(null);
      if (axios.isAxiosError(err)) {
        const data = err.response?.data;
        if (data?.errors && Array.isArray(data.errors)) {
          setRunError(data.errors.map((e: { mensaje?: string; message?: string }) => e.mensaje ?? e.message).join(' | '));
        } else {
          setRunError(data?.message ?? 'No se pudo ejecutar el reporte.');
        }
      } else {
        setRunError('No se pudo ejecutar el reporte.');
      }
    } finally {
      setIsRunning(false);
    }
  };

  const startEtlPolling = async (
    ejecucionId: number,
    paramsPayload: Record<string, unknown>,
  ) => {
    const startedAt = Date.now();
    const POLL_MS = 3000;
    const MAX_MS = 10 * 60 * 1000; // 10 minutos de seguridad

    const tick = async () => {
      if (pollAbortRef.current) return;
      try {
        const estado = await getEtlEjecucionEstadoRequest(ejecucionId);
        setEtlElapsedSec(Math.floor((Date.now() - startedAt) / 1000));
        if (!estado.terminada) {
          if (Date.now() - startedAt > MAX_MS) {
            setRunError('La carga ETL esta tardando mas de lo esperado. Reintente manualmente.');
            setEtlPreparing(null);
            return;
          }
          pollTimerRef.current = window.setTimeout(() => void tick(), POLL_MS);
          return;
        }
        // Terminado: si quedo en error, mostrar; sino, reintentar el reporte.
        if (estado.estado === 'error') {
          const detalle = (estado.observaciones ?? '').trim();
          setRunError(
            detalle
              ? `La carga ETL fallo: ${detalle}`
              : 'La carga ETL fallo. Revise la pantalla de ETL para mas detalle.',
          );
          setEtlPreparing(null);
          return;
        }
        setEtlPreparing(null);
        const response = await runReportRequest(codigo, {
          parametros: paramsPayload,
          formato: 'json',
        });
        if (response.kind === 'ready') {
          setResult(response.data);
        } else {
          // Caso raro: termino ok pero todavia faltan rangos (otro hueco).
          setEtlPreparing(response.data);
          if (response.data.status === 'preparing_data' && response.data.ejecucion_id) {
            void startEtlPolling(response.data.ejecucion_id, paramsPayload);
          }
        }
      } catch (err) {
        if (axios.isAxiosError(err)) {
          setRunError(err.response?.data?.message ?? 'Error consultando estado del ETL.');
        } else {
          setRunError('Error consultando estado del ETL.');
        }
        setEtlPreparing(null);
      }
    };

    pollTimerRef.current = window.setTimeout(() => void tick(), POLL_MS);
  };

  const handleExport = async (formato: FormatoExport) => {
    if (!metadata) return;
    setExportingFormato(formato);
    setExportNotice(null);
    try {
      const payload = buildPayload(metadata.parametros, values);
      await exportReportRequest(codigo, { parametros: payload, formato });
      // La descarga se dispara automáticamente dentro de exportReportRequest
    } catch (err) {
      let message = `No se pudo exportar el reporte a ${formato.toUpperCase()}.`;
      if (axios.isAxiosError(err)) {
        const data = err.response?.data;
        if (data instanceof Blob) {
          // responseType: 'blob' hace que los errores también lleguen como Blob
          try {
            const text = await data.text();
            const parsed = JSON.parse(text) as { message?: string };
            message = parsed.message ?? message;
          } catch {
            // ignorar error de parseo
          }
        } else if (typeof data === 'object' && data !== null) {
          message = (data as { message?: string }).message ?? message;
        }
      }
      setExportNotice(message);
    } finally {
      setExportingFormato(null);
    }
  };

  if (isLoadingMetadata) {
    return (
      <div className="card">
        <p>Cargando configuración del reporte...</p>
      </div>
    );
  }

  if (metadataError || !metadata) {
    return (
      <div className="card">
        <p className="message error">{metadataError ?? 'No se pudo cargar la configuración del reporte.'}</p>
      </div>
    );
  }

  return (
    <div className="report-runner">
      <div className="card form-card">
        <h3>Parámetros</h3>
        {metadata.parametros.length === 0 ? (
          <p className="section-note">Este reporte no requiere parámetros.</p>
        ) : (
          <div className="form-grid report-parameters-grid">
            {metadata.parametros.map((p) => {
              const label = `${p.etiqueta ?? p.nombre}${p.requerido ? ' *' : ''}`;
              if (p.tipo === 'bool') {
                return (
                  <label key={p.nombre} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={Boolean(values[p.nombre])}
                      onChange={(e) => updateValue(p.nombre, e.target.checked)}
                    />
                    {label}
                  </label>
                );
              }
              return (
                <label key={p.nombre}>
                  {label}
                  <input
                    type={p.tipo === 'date' ? 'date' : p.tipo === 'int' ? 'number' : 'text'}
                    value={String(values[p.nombre] ?? '')}
                    onChange={(e) => updateValue(p.nombre, e.target.value)}
                  />
                  {p.descripcion && <small className="section-note">{p.descripcion}</small>}
                </label>
              );
            })}
          </div>
        )}

        <div className="form-actions">
          <button type="button" onClick={() => void handleRun()} disabled={isRunning}>
            {isRunning ? 'Consultando...' : 'Consultar'}
          </button>
          {puedeExportar && formatos.excel && (
            <button
              type="button"
              className="secondary"
              onClick={() => void handleExport('excel')}
              disabled={exportingFormato !== null}
            >
              {exportingFormato === 'excel' ? 'Exportando...' : 'Exportar Excel'}
            </button>
          )}
          {puedeExportar && formatos.pdf && (
            <button
              type="button"
              className="secondary"
              onClick={() => void handleExport('pdf')}
              disabled={exportingFormato !== null}
            >
              {exportingFormato === 'pdf' ? 'Exportando...' : 'Exportar PDF'}
            </button>
          )}
        </div>

        {runError && <p className="message error">{runError}</p>}
        {exportNotice && <p className="message">{exportNotice}</p>}
        {etlPreparing && (
          <div className="message" role="status" aria-live="polite">
            <p>
              <strong>Preparando datos…</strong>{' '}
              {etlPreparing.message ??
                'Faltan datos del rango solicitado. Se esta cargando la informacion necesaria.'}
            </p>
            {etlPreparing.rango_faltante && (
              <p className="section-note">
                Rango en carga: {formatDateDisplay(etlPreparing.rango_faltante.desde)} a {formatDateDisplay(etlPreparing.rango_faltante.hasta)}
                {etlPreparing.ejecucion_id ? ` · Ejecución #${etlPreparing.ejecucion_id}` : ''}
                {etlPreparing.reusada ? ' · reusando carga en curso' : ''}
                {etlElapsedSec > 0 ? ` · ${etlElapsedSec}s` : ''}
              </p>
            )}
          </div>
        )}
      </div>

      {result && (
        <>
          <div className="card report-summary-card">
            <h3>Resumen</h3>
            <dl className="detail-grid">
              <div>
                <dt>Reporte</dt>
                <dd>{result.nombre_reporte}</dd>
              </div>
              <div>
                <dt>Generado</dt>
                <dd>{new Date(result.generado_en).toLocaleString('es-AR')}</dd>
              </div>
              <div>
                <dt>Parámetros</dt>
                <dd>
                  {Object.entries(result.parametros)
                    .map(([k, v]) => `${k}: ${dateParamNames.has(k) ? formatDateDisplay(v) : formatValue(v)}`)
                    .join(' · ') || '-'}
                </dd>
              </div>
            </dl>
            {result.es_placeholder && (
              <p className="section-note">
                El resultado es un esqueleto preliminar: aún no está conectado a la fuente de datos definitiva.
              </p>
            )}
          </div>

          {result.alertas.length > 0 && (
            <div className="card">
              <h3>Alertas y validaciones</h3>
              <ul className="report-alertas">
                {result.alertas.map((a, idx) => (
                  <AlertaItem key={`${a.codigo}-${idx}`} alerta={a} />
                ))}
              </ul>
            </div>
          )}

          {result.secciones.map((section) => (
            <SectionTable key={section.codigo} section={section} />
          ))}
        </>
      )}
    </div>
  );
};
