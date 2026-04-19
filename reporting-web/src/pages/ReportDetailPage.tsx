import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Link, useParams } from 'react-router-dom';

import { listReportsRequest } from '@/api';
import { PageHeader } from '@/components/PageHeader';
import { ReportsBreadcrumbs } from '@/components/ReportsBreadcrumbs';
import type { ReportItem } from '@/types';

export const ReportDetailPage = () => {
  const { id } = useParams();
  const reportId = Number(id);

  const [reports, setReports] = useState<ReportItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const selectedReport = useMemo(() => reports.find((report) => report.id === reportId) ?? null, [reports, reportId]);

  useEffect(() => {
    const run = async () => {
      try {
        setError(null);
        setIsLoading(true);
        const data = await listReportsRequest();
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
  }, []);

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
        subtitle="Base preparada para incorporar la funcionalidad de reporting en próximas iteraciones."
        actions={
          selectedReport ? (
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
      ) : (
        <div className="report-detail-layout">
          <div className="card">
            <h3>Información general</h3>
            <dl className="detail-grid">
              <div>
                <dt>Nombre</dt>
                <dd>{selectedReport.nombre}</dd>
              </div>
              <div>
                <dt>Código</dt>
                <dd>{selectedReport.codigo}</dd>
              </div>
              <div>
                <dt>Estado</dt>
                <dd>{selectedReport.activo ? 'Activo' : 'Inactivo'}</dd>
              </div>
              <div>
                <dt>Descripción</dt>
                <dd>{selectedReport.descripcion || '-'}</dd>
              </div>
            </dl>
          </div>

          <div className="card report-placeholder-card">
            <h3>Módulo funcional en construcción</h3>
            <p className="section-note">
              Este espacio está preparado para incorporar filtros, resultados y acciones del reporte real en la próxima etapa.
            </p>
            <div className="placeholder-zone">
              <div className="placeholder-panel">
                <strong>Filtros</strong>
                <p>Área reservada para filtros del reporte.</p>
              </div>
              <div className="placeholder-panel">
                <strong>Resultados</strong>
                <p>Área reservada para la grilla, KPIs o visualizaciones futuras.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
