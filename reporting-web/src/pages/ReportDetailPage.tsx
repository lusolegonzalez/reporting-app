import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Link, useParams } from 'react-router-dom';

import { listReportsRequest, listVisibleReportsRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import { ReportRunner } from '@/components/ReportRunner';
import { ReportsBreadcrumbs } from '@/components/ReportsBreadcrumbs';
import { storage } from '@/utils/storage';
import type { ReportItem } from '@/types';

export const ReportDetailPage = () => {
  const { id } = useParams();
  const reportId = Number(id);

  const [reports, setReports] = useState<ReportItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const user = storage.getUser();
  const isAdmin = (user?.roles ?? []).includes('ADMIN');

  const selectedReport = useMemo(() => reports.find((report) => report.id === reportId) ?? null, [reports, reportId]);

  useEffect(() => {
    const run = async () => {
      try {
        setError(null);
        setIsLoading(true);
        const data = isAdmin ? await listReportsRequest() : await listVisibleReportsRequest();
        setReports(data);
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudo cargar el detalle del reporte.');
        } else {
          setError('No se pudo cargar el detalle del reporte.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    void run();
  }, [isAdmin]);

  return (
    <section>
      <ReportsBreadcrumbs
        items={[
          { label: 'Reportes', to: '/reportes' },
          { label: selectedReport?.nombre ?? 'Detalle' },
        ]}
      />
      <PageHeader
        title={selectedReport?.nombre ?? 'Detalle de reporte'}
        subtitle={selectedReport?.descripcion ?? 'Configurá los parámetros y consultá los resultados.'}
        actions={
          isAdmin && selectedReport ? (
            <Link to={`/reportes/${selectedReport.id}/editar`} className="button-link secondary">
              Editar reporte
            </Link>
          ) : undefined
        }
      />

      {error && <p className="message error">{error}</p>}

      {isLoading ? (
        <div className="card">
          <p>Cargando...</p>
        </div>
      ) : !selectedReport ? (
        <div className="card">
          <p className="empty-state">No se encontró el reporte solicitado.</p>
        </div>
      ) : !selectedReport.activo ? (
        <div className="card">
          <p className="empty-state">El reporte se encuentra inactivo.</p>
        </div>
      ) : (
        <div className="report-detail-layout">
          <ReportRunner codigo={selectedReport.codigo} />
        </div>
      )}
    </section>
  );
};
