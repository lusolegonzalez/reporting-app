import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useNavigate, useParams } from 'react-router-dom';

import {
  createReportRequest,
  getReportVisibilityRequest,
  listReportsRequest,
  listRolesRequest,
  updateReportRequest,
  updateReportVisibilityRequest,
} from '@/api';
import { PageHeader } from '@/components/PageHeader';
import { ReportForm } from '@/components/ReportForm';
import { ReportsBreadcrumbs } from '@/components/ReportsBreadcrumbs';
import type { ReportItem, ReportVisibility, RoleItem } from '@/types';

type ReportFormValues = {
  codigo: string;
  nombre: string;
  descripcion: string;
  activo: boolean;
};

const emptyForm: ReportFormValues = { codigo: '', nombre: '', descripcion: '', activo: true };

export const ReportFormPage = () => {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const reportId = Number(id);
  const navigate = useNavigate();

  const [reports, setReports] = useState<ReportItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [visibility, setVisibility] = useState<ReportVisibility[]>([]);
  const [form, setForm] = useState<ReportFormValues>(emptyForm);
  const [isLoading, setIsLoading] = useState(isEdit);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedReport = useMemo(() => reports.find((report) => report.id === reportId) ?? null, [reports, reportId]);

  useEffect(() => {
    const run = async () => {
      if (!isEdit) return;

      try {
        setError(null);
        setIsLoading(true);
        const [loadedReports, loadedRoles] = await Promise.all([listReportsRequest(), listRolesRequest()]);
        setReports(loadedReports);
        setRoles(loadedRoles);

        const report = loadedReports.find((item) => item.id === reportId);
        if (!report) {
          setError('No se encontró el reporte solicitado.');
          return;
        }

        setForm({
          codigo: report.codigo,
          nombre: report.nombre,
          descripcion: report.descripcion ?? '',
          activo: report.activo,
        });

        const reportVisibility = await getReportVisibilityRequest(report.id);
        setVisibility(reportVisibility);
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudo cargar la información del reporte.');
        } else {
          setError('No se pudo cargar la información del reporte.');
        }
      } finally {
        setIsLoading(false);
      }
    };

    void run();
  }, [isEdit, reportId]);

  const validate = () => {
    if (!form.codigo.trim()) return 'El código es obligatorio.';
    if (!form.nombre.trim()) return 'El nombre es obligatorio.';
    return null;
  };

  const handleSubmit = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setError(null);
      setIsSubmitting(true);

      if (isEdit && selectedReport) {
        await updateReportRequest(selectedReport.id, {
          codigo: form.codigo,
          nombre: form.nombre,
          descripcion: form.descripcion,
          activo: form.activo,
        });

        await updateReportVisibilityRequest(
          selectedReport.id,
          visibility.map((item) => ({ role_id: item.role_id, puede_ver: item.puede_ver })),
        );
      }

      if (!isEdit) {
        await createReportRequest({
          codigo: form.codigo,
          nombre: form.nombre,
          descripcion: form.descripcion,
          activo: form.activo,
        });
      }

      navigate('/reportes');
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo guardar el reporte.');
      } else {
        setError('No se pudo guardar el reporte.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section>
      <ReportsBreadcrumbs
        items={[
          { label: 'Reportes', to: '/reportes' },
          { label: isEdit ? 'Editar reporte' : 'Nuevo reporte' },
        ]}
      />
      <PageHeader
        title={isEdit ? 'Editar reporte' : 'Nuevo reporte'}
        subtitle={
          isEdit
            ? 'Actualizá los datos base y la visibilidad por rol del reporte.'
            : 'Completá los datos para dar de alta un nuevo reporte.'
        }
      />

      {error && <p className="message error">{error}</p>}

      {isLoading ? (
        <div className="card">
          <p>Cargando...</p>
        </div>
      ) : (
        <>
          <ReportForm
            values={form}
            onChange={(updater) => setForm((current) => updater(current))}
            onSubmit={() => void handleSubmit()}
            isSubmitting={isSubmitting}
            submitLabel={isEdit ? 'Guardar cambios' : 'Guardar'}
          />

          {isEdit && (
            <div className="card report-visibility-card">
              <h3>Visibilidad por rol</h3>
              <p className="section-note">Definí qué roles pueden visualizar este reporte.</p>
              {roles.length === 0 ? (
                <p className="empty-state">No hay roles disponibles para configurar visibilidad.</p>
              ) : (
                <div className="checkbox-grid">
                  {roles.map((role) => {
                    const current = visibility.find((item) => item.role_id === role.id);
                    return (
                      <label key={role.id} className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={current?.puede_ver ?? false}
                          onChange={(e) => {
                            const canView = e.target.checked;
                            setVisibility((currentVisibility) => {
                              const existing = currentVisibility.find((item) => item.role_id === role.id);
                              if (!existing) {
                                return [...currentVisibility, { role_id: role.id, rol: role.nombre, puede_ver: canView }];
                              }

                              return currentVisibility.map((item) =>
                                item.role_id === role.id ? { ...item, puede_ver: canView } : item,
                              );
                            });
                          }}
                        />
                        {role.nombre}
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
};
