import { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

import { listReportsRequest, listVisibleReportsRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import { ReportsBreadcrumbs } from '@/components/ReportsBreadcrumbs';
import { storage } from '@/utils/storage';
import type { ReportItem } from '@/types';

export const ReportsListPage = () => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const user = storage.getUser();
  const isAdmin = (user?.roles ?? []).includes('ADMIN');

  useEffect(() => {
    const run = async () => {
      try {
        setError(null);
        setIsLoading(true);
        const data = isAdmin ? await listReportsRequest() : await listVisibleReportsRequest();
        setReports(data);
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudieron cargar los reportes.');
        } else {
          setError('No se pudieron cargar los reportes.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    void run();
  }, [isAdmin]);

  return (
    <section>
      <ReportsBreadcrumbs items={[{ label: 'Reportes' }]} />
      <PageHeader
        title="Reportes"
        subtitle={
          isAdmin
            ? 'Listado de reportes configurados en el portal.'
            : 'Reportes disponibles para tu rol.'
        }
        actions={
          isAdmin ? (
            <Link to="/reportes/nuevo" className="button-link">
              Nuevo reporte
            </Link>
          ) : undefined
        }
      />

      {error && <p className="message error">{error}</p>}

      <div className="card">
        {isLoading ? (
          <p>Cargando reportes...</p>
        ) : reports.length === 0 ? (
          <p className="empty-state">
            {isAdmin ? 'Todavía no hay reportes cargados.' : 'No tenés reportes disponibles asignados a tu rol.'}
          </p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Código</th>
                <th>Descripción</th>
                {isAdmin && <th>Estado</th>}
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id}>
                  <td>{report.nombre}</td>
                  <td>{report.codigo}</td>
                  <td>{report.descripcion || '-'}</td>
                  {isAdmin && <td>{report.activo ? 'Activo' : 'Inactivo'}</td>}
                  <td>
                    <div className="table-actions">
                      <Link to={`/reportes/${report.id}`} className="button-link secondary">
                        Ver
                      </Link>
                      {isAdmin && (
                        <Link to={`/reportes/${report.id}/editar`} className="button-link secondary">
                          Editar
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
};
