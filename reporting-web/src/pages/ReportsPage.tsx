import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';

import {
  createReportRequest,
  getReportVisibilityRequest,
  listReportsRequest,
  listRolesRequest,
  listVisibleReportsRequest,
  updateReportRequest,
  updateReportVisibilityRequest,
} from '@/api';
import { PageHeader } from '@/components/PageHeader';
import type { ReportItem, ReportVisibility, RoleItem } from '@/types';

export const ReportsPage = () => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [visibleReports, setVisibleReports] = useState<ReportItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [visibility, setVisibility] = useState<ReportVisibility[]>([]);
  const [editForm, setEditForm] = useState({ codigo: '', nombre: '', descripcion: '', activo: true });
  const [newReport, setNewReport] = useState({ codigo: '', nombre: '', descripcion: '', activo: true });
  const [error, setError] = useState<string | null>(null);

  const selectedReport = useMemo(() => reports.find((item) => item.id === selectedReportId) ?? null, [reports, selectedReportId]);

  const refreshAll = async () => {
    const [loadedReports, loadedRoles, loadedVisible] = await Promise.all([
      listReportsRequest(),
      listRolesRequest(),
      listVisibleReportsRequest(),
    ]);
    setReports(loadedReports);
    setRoles(loadedRoles);
    setVisibleReports(loadedVisible);

    if (loadedReports.length > 0) {
      const selected = loadedReports.find((item) => item.id === selectedReportId) ?? loadedReports[0];
      setSelectedReportId(selected.id);
      setEditForm({
        codigo: selected.codigo,
        nombre: selected.nombre,
        descripcion: selected.descripcion ?? '',
        activo: selected.activo,
      });

      const reportVisibility = await getReportVisibilityRequest(selected.id);
      setVisibility(reportVisibility);
    } else {
      setSelectedReportId(null);
      setVisibility([]);
    }
  };

  useEffect(() => {
    const run = async () => {
      try {
        setError(null);
        await refreshAll();
      } catch (requestError) {
        if (axios.isAxiosError(requestError)) {
          setError(requestError.response?.data?.message ?? 'No se pudieron cargar reportes.');
        } else {
          setError('No se pudieron cargar reportes.');
        }
      }
    };

    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async () => {
    try {
      await createReportRequest(newReport);
      setNewReport({ codigo: '', nombre: '', descripcion: '', activo: true });
      setError(null);
      await refreshAll();
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo crear reporte.');
      } else {
        setError('No se pudo crear reporte.');
      }
    }
  };

  const handleSave = async () => {
    if (!selectedReport) return;

    try {
      await updateReportRequest(selectedReport.id, editForm);
      await updateReportVisibilityRequest(
        selectedReport.id,
        visibility.map((item) => ({ role_id: item.role_id, puede_ver: item.puede_ver })),
      );
      setError(null);
      await refreshAll();
    } catch (requestError) {
      if (axios.isAxiosError(requestError)) {
        setError(requestError.response?.data?.message ?? 'No se pudo editar reporte.');
      } else {
        setError('No se pudo editar reporte.');
      }
    }
  };

  return (
    <section>
      <PageHeader title="Reportes" subtitle="CRUD básico + visibilidad por rol + reportes visibles del usuario." />
      {error && <p className="message error">{error}</p>}

      <div className="card section-block">
        <h3>Mis reportes visibles</h3>
        <ul>
          {visibleReports.map((report) => (
            <li key={report.id}>
              {report.codigo} - {report.nombre}
            </li>
          ))}
          {visibleReports.length === 0 && <li>No hay reportes visibles para tu usuario.</li>}
        </ul>
      </div>

      <div className="card section-block">
        <h3>Crear reporte</h3>
        <div className="inline-form-grid">
          <input value={newReport.codigo} onChange={(e) => setNewReport((v) => ({ ...v, codigo: e.target.value }))} placeholder="Código" />
          <input value={newReport.nombre} onChange={(e) => setNewReport((v) => ({ ...v, nombre: e.target.value }))} placeholder="Nombre" />
          <input
            value={newReport.descripcion}
            onChange={(e) => setNewReport((v) => ({ ...v, descripcion: e.target.value }))}
            placeholder="Descripción"
          />
          <button onClick={handleCreate}>Crear</button>
        </div>
      </div>

      <div className="card">
        <h3>Editar reporte y visibilidad</h3>
        <div className="editor-grid">
          <select
            size={8}
            value={selectedReportId ?? ''}
            onChange={async (e) => {
              const id = Number(e.target.value);
              const report = reports.find((item) => item.id === id);
              if (!report) return;

              setSelectedReportId(id);
              setEditForm({ codigo: report.codigo, nombre: report.nombre, descripcion: report.descripcion ?? '', activo: report.activo });
              const reportVisibility = await getReportVisibilityRequest(id);
              setVisibility(reportVisibility);
            }}
          >
            {reports.map((report) => (
              <option key={report.id} value={report.id}>
                {report.codigo} - {report.nombre}
              </option>
            ))}
          </select>

          {selectedReport && (
            <div className="form-grid">
              <input value={editForm.codigo} onChange={(e) => setEditForm((v) => ({ ...v, codigo: e.target.value }))} placeholder="Código" />
              <input value={editForm.nombre} onChange={(e) => setEditForm((v) => ({ ...v, nombre: e.target.value }))} placeholder="Nombre" />
              <input
                value={editForm.descripcion}
                onChange={(e) => setEditForm((v) => ({ ...v, descripcion: e.target.value }))}
                placeholder="Descripción"
              />
              <label>
                <input
                  type="checkbox"
                  checked={editForm.activo}
                  onChange={(e) => setEditForm((v) => ({ ...v, activo: e.target.checked }))}
                  style={{ marginRight: '0.5rem' }}
                />
                Reporte activo
              </label>

              <strong>Visibilidad por rol</strong>
              <div className="checkbox-grid">
                {roles.map((role) => {
                  const current = visibility.find((item) => item.role_id === role.id);
                  return (
                    <label key={role.id}>
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
                        style={{ marginRight: '0.5rem' }}
                      />
                      {role.nombre}
                    </label>
                  );
                })}
              </div>

              <button onClick={handleSave}>Guardar cambios</button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
