import { useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import axios from 'axios';

import { runEtlRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import { useAuth } from '@/hooks/useAuth';
import type { EtlRunResponse, EtlSource } from '@/types';

const todayIso = () => new Date().toISOString().slice(0, 10);

export const EtlPage = () => {
  const { currentUser } = useAuth();
  const isAdmin = (currentUser?.roles ?? []).includes('ADMIN');

  const [desde, setDesde] = useState<string>(todayIso());
  const [hasta, setHasta] = useState<string>(todayIso());
  const [source, setSource] = useState<EtlSource>('mssql');
  const [origen, setOrigen] = useState<string>('TwinsDbQuatro045');
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [result, setResult] = useState<EtlRunResponse | null>(null);

  const totales = useMemo(() => {
    if (!result) return null;
    return result.pasos.reduce(
      (acc, p) => ({
        leidas: acc.leidas + p.filas_leidas,
        insertadas: acc.insertadas + p.filas_insertadas,
        actualizadas: acc.actualizadas + p.filas_actualizadas,
        descartadas: acc.descartadas + p.filas_descartadas,
        errores: acc.errores + p.errores.length,
      }),
      { leidas: 0, insertadas: 0, actualizadas: 0, descartadas: 0, errores: 0 },
    );
  }, [result]);

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setErrorDetail(null);
    setResult(null);

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
            Ejecución #{result.ejecucion_id} — <span>{result.estado}</span>
          </h3>

          {totales && (
            <ul className="kpi-list">
              <li><strong>Leídas:</strong> {totales.leidas}</li>
              <li><strong>Insertadas:</strong> {totales.insertadas}</li>
              <li><strong>Actualizadas:</strong> {totales.actualizadas}</li>
              <li><strong>Descartadas:</strong> {totales.descartadas}</li>
              <li><strong>Errores:</strong> {totales.errores}</li>
            </ul>
          )}

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
              {result.pasos.map((p) => (
                <tr key={p.tabla_destino}>
                  <td>{p.tabla_destino}</td>
                  <td>{p.filas_leidas}</td>
                  <td>{p.filas_insertadas}</td>
                  <td>{p.filas_actualizadas}</td>
                  <td>{p.filas_descartadas}</td>
                  <td>{p.duracion_ms}</td>
                  <td>{p.errores.length}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {result.pasos.some((p) => p.errores.length > 0) && (
            <details className="card-inner">
              <summary>Detalle de errores</summary>
              <ul>
                {result.pasos.flatMap((p) =>
                  p.errores.map((err, idx) => (
                    <li key={`${p.tabla_destino}-${idx}`}>
                      <strong>{p.tabla_destino}</strong>
                      {err.source_pk ? ` [${err.source_pk}]` : ''}: {err.mensaje}
                    </li>
                  )),
                )}
              </ul>
            </details>
          )}
        </div>
      )}
    </section>
  );
};
