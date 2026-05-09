import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';

import { getReportMetadataRequest, runReportRequest } from '@/api';
import type {
  ReportAlerta,
  ReportMetadata,
  ReportParameterDef,
  ReportResponse,
  ReportSection,
} from '@/types';

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

const AlertaItem = ({ alerta }: { alerta: ReportAlerta }) => (
  <li className={`report-alerta report-alerta-${alerta.nivel}`}>
    <strong>{alerta.codigo}:</strong> {alerta.mensaje}
  </li>
);

const SectionTable = ({ section }: { section: ReportSection }) => {
  const tieneFilas = section.filas.length > 0;
  return (
    <div className="card report-section-card">
      <div className="report-section-header">
        <h4>{section.titulo}</h4>
        {!tieneFilas && <span className="section-note">Sin datos para los parámetros indicados.</span>}
      </div>
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
                    <td key={col.key}>{formatValue(fila[col.key])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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

  const updateValue = (nombre: string, value: string | boolean) => {
    setValues((current) => ({ ...current, [nombre]: value }));
  };

  const handleRun = async () => {
    if (!metadata) return;
    setIsRunning(true);
    setRunError(null);
    setExportNotice(null);
    try {
      const payload = buildPayload(metadata.parametros, values);
      const response = await runReportRequest(codigo, { parametros: payload, formato: 'json' });
      setResult(response);
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

  const handleExport = async (formato: FormatoExport) => {
    if (!metadata) return;
    setExportingFormato(formato);
    setExportNotice(null);
    try {
      const payload = buildPayload(metadata.parametros, values);
      await runReportRequest(codigo, { parametros: payload, formato });
      setExportNotice(`Exportación ${formato.toUpperCase()} completada.`);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const status = err.response?.status;
        const message = err.response?.data?.message;
        if (status === 501) {
          setExportNotice(message ?? `La exportación a ${formato.toUpperCase()} aún no está disponible.`);
        } else {
          setExportNotice(message ?? `No se pudo exportar el reporte a ${formato.toUpperCase()}.`);
        }
      } else {
        setExportNotice(`No se pudo exportar el reporte a ${formato.toUpperCase()}.`);
      }
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
              const label = `${p.nombre}${p.requerido ? ' *' : ''}`;
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
                    .map(([k, v]) => `${k}: ${formatValue(v)}`)
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
