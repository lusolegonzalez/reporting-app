import { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

import { listReportsRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import { ReportsBreadcrumbs } from '@/components/ReportsBreadcrumbs';
import type { ReportItem } from '@/types';

export const ReportsListPage = () => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        setError(null);
        setIsLoading(true);
        const data = await listReportsRequest();
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
  }, []);

  return (
    <section>
      <ReportsBreadcrumbs items={[{ label: 'Reportes' }]} />
      <PageHeader
        title="Reportes"
        subtitle="Listado de reportes configurados en el portal."
        actions={
          <Link to="/reportes/nuevo" className="button-link">
            Nuevo reporte
          </Link>
        }
      />

      {error && <p className="message error">{error}</p>}

      <div className="card">
        {isLoading ? (
          <p>Cargando reportes...</p>
        ) : reports.length === 0 ? (
          <p className="empty-state">Todavía no hay reportes cargados.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Código</th>
                <th>Descripción</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id}>
                  <td>{report.nombre}</td>
                  <td>{report.codigo}</td>
                  <td>{report.descripcion || '-'}</td>
                  <td>{report.activo ? 'Activo' : 'Inactivo'}</td>
                  <td>
                    <div className="table-actions">
                      <Link to={`/reportes/${report.id}`} className="button-link secondary">
                        Ver
                      </Link>
                      <Link to={`/reportes/${report.id}/editar`} className="button-link secondary">
                        Editar
                      </Link>
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
