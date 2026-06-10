import { useEffect, useMemo, useRef, useState } from 'react';
import { Navigate } from 'react-router-dom';
import axios from 'axios';

import { runEtlRequest, getEtlEjecucionEstadoRequest, getEtlEjecucionRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import { useAuth } from '@/hooks/useAuth';
import type { EtlRunResponse, EtlEjecucionDetalle, EtlSource } from '@/types';

const todayIso = () => new Date().toISOString().slice(0, 10);

export const EtlPage = () => {
  const { currentUser } = useAuth();
  const isAdmin = (currentUser?.roles ?? []).includes('ADMIN');

  const [desde, setDesde] = useState<string>(todayIso());
  const [hasta, setHasta] = useState<string>(todayIso());
  const [source, setSource] = useState<EtlSource>('mssql');
  const [origen, setOrigen] = useState<string>('TwinsDbQuatro045');
  const [running, setRunning] = useState(false);
  const [pollingId, setPollingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [result, setResult] = useState<EtlRunResponse | null>(null);
  const [detalle, setDetalle] = useState<EtlEjecucionDetalle | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const totales = useMemo(() => {
    const pasos = detalle?.tablas ?? result?.pasos ?? [];
    if (!pasos.length) return null;
    return pasos.reduce(
      (acc, p) => ({
        leidas: acc.leidas + p.filas_leidas,
        insertadas: acc.insertadas + p.filas_insertadas,
        actualizadas: acc.actualizadas + p.filas_actualizadas,
        descartadas: acc.descartadas + p.filas_descartadas,
        errores: acc.errores + (('errores' in p) ? (p as { errores: unknown[] }).errores.length : 0),
      }),
      { leidas: 0, insertadas: 0, actualizadas: 0, descartadas: 0, errores: 0 },
    );
  }, [result, detalle]);

  // Polling: cuando el ETL queda en queued/running, esperamos hasta que termine
  useEffect(() => {
    if (pollingId === null) return;

    const interval = setInterval(async () => {
      try {
        const estado = await getEtlEjecucionEstadoRequest(pollingId);
        if (estado.terminada) {
          clearInterval(interval);
          pollRef.current = null;
          setRunning(false);
          setPollingId(null);
          // Cargar detalle completo con tablas
          const d = await getEtlEjecucionRequest(pollingId);
          setDetalle(d);
          setResult((prev) => prev ? { ...prev, estado: d.estado } : null);
          if (d.estado === 'error') {
            const obs = d.observaciones ?? 'El ETL terminó con error.';
            setError(obs);
          }
        }
      } catch {
        // Error de red transitorio — seguimos intentando
      }
    }, 3000);

    pollRef.current = interval;
    return () => clearInterval(interval);
  }, [pollingId]);

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setErrorDetail(null);
    setResult(null);
    setDetalle(null);
    setPollingId(null);

    if (!desde || !hasta) {
      setError('Indicá fechas desde y hasta (YYYY-MM-DD).');
      return;
    }
    if (desde > hasta) {
      setError('"Desde" debe ser menor o igual a "hasta".');
      return;
    }

    setRunning(true);
    try {
      const data = await runEtlRequest({
        desde,
        hasta,
        origen: origen.trim() || undefined,
        source,
      });
      setResult(data);
      // Si el backend lo encoló en background, arrancamos polling
      if (data.estado === 'queued' || data.estado === 'running') {
        setPollingId(data.ejecucion_id);
        // setRunning se apaga cuando el polling detecte terminada=true
      } else {
        setRunning(false);
      }
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        const data = requestError.response?.data as
          | { message?: string; detail?: string; ejecucion_id?: number }
          | undefined;
        const status = requestError.response?.status;
        const baseMsg =
          data?.message ??
          (status ? `HTTP ${status}: ${requestError.message}` : requestError.message) ??
          'No se pudo ejecutar el ETL.';
        setError(`No se pudo ejecutar el ETL: ${baseMsg}`);
        const detailParts: string[] = [];
        if (data?.detail) detailParts.push(data.detail);
        if (data?.ejecucion_id !== undefined) {
          detailParts.push(`Ejecución id: ${data.ejecucion_id}`);
        }
        setErrorDetail(detailParts.length > 0 ? detailParts.join('\n') : null);
      } else {
        const msg = requestError instanceof Error ? requestError.message : String(requestError);
        setError(`No se pudo ejecutar el ETL: ${msg}`);
        setErrorDetail(null);
      }
    } finally {
      setRunning(false);
    }
  };

  return (
    <section>
      <PageHeader
        title="ETL"
        subtitle="Ejecución manual del proceso de importación desde SQL Server hacia la base intermedia."
      />

      <div className="card">
        <form onSubmit={handleSubmit} className="form-grid">
          <label>
            <span>Desde</span>
            <input
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              disabled={running}
              required
            />
          </label>
          <label>
            <span>Hasta</span>
            <input
              type="date"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              disabled={running}
              required
            />
          </label>
          <label>
            <span>Origen (DB)</span>
            <input
              type="text"
              value={origen}
              onChange={(e) => setOrigen(e.target.value)}
              disabled={running}
              placeholder="TwinsDbQuatro045"
            />
          </label>
          <label>
            <span>Source</span>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as EtlSource)}
              disabled={running}
            >
              <option value="mssql">SQL Server (Twins)</option>
              <option value="empty">Vacío (validación)</option>
            </select>
          </label>
          <div className="form-actions">
            <button type="submit" disabled={running}>
              {running ? 'Ejecutando…' : 'Ejecutar ETL'}
            </button>
          </div>
        </form>
      </div>

      {error && (
        <div className="message error">
          <p>{error}</p>
          {errorDetail && (
            <details>
              <summary>Detalle técnico</summary>
              <pre className="error-detail">{errorDetail}</pre>
            </details>
          )}
        </div>
      )}

      {result && (
        <div className="card">
          <h3>
            Ejecución #{result.ejecucion_id} —{' '}
            <span>
              {result.estado === 'queued' || result.estado === 'running'
                ? 'Ejecutando…'
                : result.estado}
            </span>
          </h3>

          {(result.estado === 'queued' || result.estado === 'running') && (
            <p className="text-muted">Procesando datos, esto puede tardar varios minutos…</p>
          )}

          {totales && (
            <ul className="kpi-list">
              <li><strong>Leídas:</strong> {totales.leidas}</li>
              <li><strong>Insertadas:</strong> {totales.insertadas}</li>
              <li><strong>Actualizadas:</strong> {totales.actualizadas}</li>
              <li><strong>Descartadas:</strong> {totales.descartadas}</li>
              <li><strong>Errores:</strong> {totales.errores}</li>
            </ul>
          )}

          {(detalle?.tablas ?? result.pasos).length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>Tabla destino</th>
                <th>Leídas</th>
                <th>Insertadas</th>
                <th>Actualizadas</th>
                <th>Descartadas</th>
                <th>Duración (ms)</th>
                <th>Errores</th>
              </tr>
            </thead>
            <tbody>
              {(detalle?.tablas ?? result.pasos).map((p) => (
                <tr key={p.tabla_destino}>
                  <td>{p.tabla_destino}</td>
                  <td>{p.filas_leidas}</td>
                  <td>{p.filas_insertadas}</td>
                  <td>{p.filas_actualizadas}</td>
                  <td>{p.filas_descartadas}</td>
                  <td>{p.duracion_ms}</td>
                  <td>{'errores' in p ? (p as { errores: unknown[] }).errores.length : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          )}

          {detalle && detalle.errores.length > 0 && (
            <details className="card-inner">
              <summary>Detalle de errores</summary>
              <ul>
                {detalle.errores.map((err, idx) => (
                  <li key={idx}>
                    <strong>{err.tabla_destino}</strong>
                    {err.source_pk ? ` [${err.source_pk}]` : ''}: {err.mensaje}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </section>
  );
};
